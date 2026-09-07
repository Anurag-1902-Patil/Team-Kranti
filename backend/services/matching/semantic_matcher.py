"""
Sentence-Transformers semantic matching against pre-computed activity embeddings.

Uses all-MiniLM-L6-v2 (fast, CPU-friendly, good semantic quality for short sentences).
Activity embeddings are computed once during schedule seeding and stored as a
numpy matrix for O(1) cosine similarity lookup.

The embedding matrix is loaded as a module-level singleton per process — it's
small enough (~20 activities × 384 dims × 4 bytes = ~30KB for typical demo scale).
"""

from dataclasses import dataclass

import numpy as np
import structlog

log = structlog.get_logger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
_embedder = None
_embedding_matrix: np.ndarray | None = None
_activity_ids: list[str] = []
_activity_names: list[str] = []


def get_embedder():
    """Lazy-load and return the SentenceTransformer model singleton."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        log.info("semantic_matcher.loading_model", model=MODEL_NAME)
        _embedder = SentenceTransformer(MODEL_NAME)
        log.info("semantic_matcher.model_ready")
    return _embedder


def load_activity_embeddings(
    activity_index: dict[str, str],  # {activity_id: activity_name}
) -> None:
    """
    Pre-compute embeddings for all plan activities and store them in the
    module-level matrix. Call this once at worker/app startup after seeding.

    Args:
        activity_index: Dict mapping activity_id → activity_name.
    """
    global _embedding_matrix, _activity_ids, _activity_names

    if not activity_index:
        log.warning("semantic_matcher.empty_activity_index")
        return

    model = get_embedder()
    ids = list(activity_index.keys())
    names = list(activity_index.values())

    log.info("semantic_matcher.computing_embeddings", count=len(names))
    embeddings = model.encode(names, convert_to_numpy=True, normalize_embeddings=True)

    _activity_ids = ids
    _activity_names = names
    _embedding_matrix = embeddings.astype(np.float32)

    log.info(
        "semantic_matcher.embeddings_ready",
        count=len(ids),
        dims=_embedding_matrix.shape[1],
    )


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string. Returns a normalized 1D float32 array."""
    model = get_embedder()
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
    return vec[0].astype(np.float32)


@dataclass
class SemanticCandidate:
    activity_id: str
    activity_name: str
    cosine_score: float  # 0–1 (already normalized)


def get_semantic_candidates(
    description: str,
    top_k: int = 10,
    score_cutoff: float = 0.2,
) -> list[SemanticCandidate]:
    """
    Find the top-k semantically similar activities.

    Requires load_activity_embeddings() to have been called first.
    Falls back to empty list gracefully if embeddings aren't loaded.

    Args:
        description: Extracted activity description.
        top_k: Number of candidates to return.
        score_cutoff: Minimum cosine similarity to include.

    Returns:
        List of SemanticCandidate sorted by cosine_score descending.
    """
    if _embedding_matrix is None or len(_activity_ids) == 0:
        log.warning("semantic_matcher.embeddings_not_loaded")
        return []

    query_vec = embed_text(description)

    # Cosine similarity = dot product (both are already L2-normalized)
    scores = (_embedding_matrix @ query_vec).tolist()

    candidates = []
    for idx, (score, act_id, act_name) in enumerate(
        zip(scores, _activity_ids, _activity_names)
    ):
        if score >= score_cutoff:
            candidates.append(
                SemanticCandidate(
                    activity_id=act_id,
                    activity_name=act_name,
                    cosine_score=float(score),
                )
            )

    candidates.sort(key=lambda c: c.cosine_score, reverse=True)
    result = candidates[:top_k]

    log.debug(
        "semantic_matcher.done",
        description=description[:80],
        candidates=len(result),
        top_score=result[0].cosine_score if result else 0,
    )

    return result
