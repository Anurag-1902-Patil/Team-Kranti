"""
ChromaDB institutional memory store.

Stores finalized progress events and plan activities as searchable embeddings.
Uses ChromaDB in-process with persistence to disk (CHROMA_PERSIST_DIR env var).

Collections:
  - "progress_events": finalized actual-progress events (matched + accepted)
  - "plan_activities": plan activity index (for the matching engine's vector search)

Per ADR-004: ChromaDB is the primary; Qdrant is noted as a production upgrade.
"""

import uuid
from typing import Any

import structlog

from backend.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

_chroma_client = None
_events_collection = None
_activities_collection = None


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
        )
        log.info("chroma_store.client_ready", path=settings.chroma_persist_dir)
    return _chroma_client


def _get_events_collection():
    global _events_collection
    if _events_collection is None:
        client = _get_client()
        _events_collection = client.get_or_create_collection(
            name="progress_events",
            metadata={"hnsw:space": "cosine"},
        )
    return _events_collection


def _get_activities_collection():
    global _activities_collection
    if _activities_collection is None:
        client = _get_client()
        _activities_collection = client.get_or_create_collection(
            name="plan_activities",
            metadata={"hnsw:space": "cosine"},
        )
    return _activities_collection


def _embed(text: str) -> list[float]:
    """Embed text using the shared sentence-transformers model."""
    from backend.services.matching.semantic_matcher import embed_text

    return embed_text(text).tolist()


# ---------------------------------------------------------------------------
# Progress Event Indexing
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
    Embed and index a finalized progress event.
    Only call for events that are 'matched' or 'accepted' (not raw/pending).

    Returns: ChromaDB document ID (same as event_id for traceability).
    """
    collection = _get_events_collection()

    # Build the text to embed: description + plan name gives the richest signal
    embed_text_content = f"{activity_description}"
    if activity_name_plan:
        embed_text_content += f" [Plan: {activity_name_plan}]"

    embedding = _embed(embed_text_content)

    doc_id = str(event_id)

    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[embed_text_content],
        metadatas=[
            {
                "event_id": doc_id,
                "discipline": discipline,
                "project_id": project_id,
                "confidence_score": float(confidence_score or 0),
                "actual_start": actual_start or "",
                "actual_finish": actual_finish or "",
                "activity_name_plan": activity_name_plan or "",
            }
        ],
    )

    log.debug("chroma_store.event_indexed", event_id=doc_id, discipline=discipline)
    return doc_id


def query_institutional_memory(
    query_text: str,
    discipline: str | None = None,
    n_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Semantic search over finalized progress events.

    Args:
        query_text: Natural language query (e.g. "piping spool erection duration")
        discipline: Optional discipline filter.
        n_results: Number of results to return.

    Returns:
        List of result dicts with document text and metadata.
    """
    collection = _get_events_collection()

    if collection.count() == 0:
        return []

    query_embedding = _embed(query_text)

    where = {}
    if discipline:
        where["discipline"] = {"$eq": discipline}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        where=where if where else None,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append(
            {
                "text": doc,
                "metadata": meta,
                "similarity_score": round(1 - dist, 4),  # Convert distance to similarity
            }
        )

    log.info(
        "chroma_store.query_done",
        query=query_text[:80],
        discipline=discipline,
        results=len(output),
    )

    return output


# ---------------------------------------------------------------------------
# Plan Activity Indexing
# ---------------------------------------------------------------------------


def index_plan_activity(
    activity_id: str,
    activity_name: str,
    discipline: str,
    project_id: str,
) -> str:
    """
    Embed and index a plan activity for semantic search.
    Used both during initial XER seeding and on confirm_new.

    Returns: ChromaDB document ID.
    """
    collection = _get_activities_collection()

    embedding = _embed(activity_name)

    collection.upsert(
        ids=[activity_id],
        embeddings=[embedding],
        documents=[activity_name],
        metadatas=[
            {
                "activity_id": activity_id,
                "discipline": discipline,
                "project_id": project_id,
            }
        ],
    )

    return activity_id


def get_activity_collection_count() -> int:
    """Return number of indexed plan activities."""
    return _get_activities_collection().count()


def get_events_collection_count() -> int:
    """Return number of indexed progress events."""
    return _get_events_collection().count()
