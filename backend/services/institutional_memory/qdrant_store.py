"""
Qdrant institutional memory store.

Replaces ChromaDB (see .ai/DECISIONS.md ADR-011).

Two collections with distinct purposes (ADR-012 — do NOT conflate):
  - progress_events (qdrant_collection_events):
      Finalized actual-progress events (matched + accepted/confirmed).
      Purpose: institutional memory — semantic recall of "what happened on site".
      Used by: GET /memory/query, dataset export.

  - plan_activities (qdrant_collection_activities):
      Plan activity index — the MATCHING ENGINE's vector search target.
      Purpose: cosine lookup during ingestion to find the closest plan activity.
      Used by: semantic_matcher.get_semantic_candidates() via embed + query.

These are two logically separate stores. plan_activities answers "which plan activity
matches this description?" and progress_events answers "what similar work has been done
on site historically?" Merging them would corrupt both use cases.

Public interface is identical to the old chroma_store — all callers import the same
function names, nothing else needs to change.

For tests: use QdrantClient(":memory:") — no Docker container needed.
"""

import uuid
from typing import Any

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from backend.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

_qdrant_client: QdrantClient | None = None

# Vector dimension for all-MiniLM-L6-v2
_VECTOR_DIM = 384


def _get_client() -> QdrantClient:
    """Return (cached) Qdrant client. Uses QDRANT_URL from settings."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=settings.qdrant_url)
        log.info("qdrant_store.client_ready", url=settings.qdrant_url)
        _ensure_collections()
    return _qdrant_client


def _ensure_collections() -> None:
    """Create collections if they don't exist."""
    client = _qdrant_client
    existing = {c.name for c in client.get_collections().collections}

    for col_name in [settings.qdrant_collection_events, settings.qdrant_collection_activities]:
        if col_name not in existing:
            client.create_collection(
                collection_name=col_name,
                vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
            )
            log.info("qdrant_store.collection_created", name=col_name)


def _embed(text: str) -> list[float]:
    """Embed text using the shared sentence-transformers model."""
    from backend.services.matching.semantic_matcher import embed_text
    return embed_text(text).tolist()


# ---------------------------------------------------------------------------
# Progress Event Indexing (institutional memory)
# ---------------------------------------------------------------------------


def index_progress_event(
    event_id: str,
    activity_description: str,
    activity_name_plan: str | None,
    discipline: str,
    project_id: str,
    confidence_score: float | None,
    actual_start: str | None,
    actual_finish: str | None,
) -> str:
    """
    Embed and upsert a finalized progress event into the progress_events collection.
    Only call for matched/accepted/confirmed events.

    Returns: event_id (used as Qdrant point ID).
    """
    client = _get_client()
    col = settings.qdrant_collection_events

    embed_text_content = activity_description
    if activity_name_plan:
        embed_text_content += f" [Plan: {activity_name_plan}]"

    embedding = _embed(embed_text_content)

    # Qdrant requires UUID-format IDs or unsigned ints; we use UUID string
    point_id = str(uuid.UUID(event_id)) if len(event_id) == 36 else str(uuid.uuid5(uuid.NAMESPACE_URL, event_id))

    client.upsert(
        collection_name=col,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "event_id": event_id,
                    "text": embed_text_content,
                    "discipline": discipline,
                    "project_id": project_id,
                    "confidence_score": float(confidence_score or 0),
                    "actual_start": actual_start or "",
                    "actual_finish": actual_finish or "",
                    "activity_name_plan": activity_name_plan or "",
                },
            )
        ],
    )

    log.debug("qdrant_store.event_indexed", event_id=event_id, discipline=discipline)
    return event_id


def query_institutional_memory(
    query_text: str,
    discipline: str | None = None,
    n_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Semantic search over finalized progress events.

    Args:
        query_text: Natural language query.
        discipline: Optional discipline filter.
        n_results: Number of results to return.

    Returns:
        List of result dicts with text, metadata, similarity_score.
    """
    client = _get_client()
    col = settings.qdrant_collection_events

    count = get_events_collection_count()
    if count == 0:
        return []

    query_embedding = _embed(query_text)

    query_filter = None
    if discipline:
        query_filter = Filter(
            must=[FieldCondition(key="discipline", match=MatchValue(value=discipline))]
        )

    results = client.search(
        collection_name=col,
        query_vector=query_embedding,
        limit=min(n_results, count),
        query_filter=query_filter,
        with_payload=True,
    )

    output = []
    for hit in results:
        payload = hit.payload or {}
        output.append(
            {
                "text": payload.get("text", ""),
                "metadata": {k: v for k, v in payload.items() if k != "text"},
                "similarity_score": round(hit.score, 4),
            }
        )

    log.info(
        "qdrant_store.query_done",
        query=query_text[:80],
        discipline=discipline,
        results=len(output),
    )
    return output


# ---------------------------------------------------------------------------
# Plan Activity Indexing (matching engine index)
# ---------------------------------------------------------------------------


def index_plan_activity(
    activity_id: str,
    activity_name: str,
    discipline: str,
    project_id: str,
) -> str:
    """
    Embed and upsert a plan activity into the plan_activities collection.
    Used during initial XER seeding AND on confirm_new (makes new activities
    immediately findable by the matching engine on the next message).

    Returns: activity_id.
    """
    client = _get_client()
    col = settings.qdrant_collection_activities

    embedding = _embed(activity_name)

    # Use a deterministic UUID from the activity_id string
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"activity:{activity_id}"))

    client.upsert(
        collection_name=col,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "activity_id": activity_id,
                    "activity_name": activity_name,
                    "discipline": discipline,
                    "project_id": project_id,
                },
            )
        ],
    )

    return activity_id


def get_activity_collection_count() -> int:
    """Return number of indexed plan activities."""
    try:
        return _get_client().get_collection(settings.qdrant_collection_activities).points_count or 0
    except Exception:
        return 0


def get_events_collection_count() -> int:
    """Return number of indexed progress events."""
    try:
        return _get_client().get_collection(settings.qdrant_collection_events).points_count or 0
    except Exception:
        return 0
