"""
RapidFuzz-based fuzzy string matching against the plan_activities index.

Used as the fast first pass in the matching pipeline.
Returns the top-k candidates with token_sort_ratio and partial_ratio scores.
"""

from dataclasses import dataclass

import structlog
from rapidfuzz import fuzz, process

log = structlog.get_logger(__name__)


@dataclass
class FuzzyCandidate:
    activity_id: str
    activity_name: str
    token_sort_score: float  # 0–100
    partial_score: float     # 0–100
    combined_score: float    # Normalized 0–1


def get_fuzzy_candidates(
    description: str,
    activity_index: dict[str, str],  # {activity_id: activity_name}
    top_k: int = 10,
) -> list[FuzzyCandidate]:
    """
    Find the top-k activities in the index most similar to the description.

    Args:
        description: Extracted activity description from the field message.
        activity_index: Dict mapping activity_id → activity_name.
        top_k: Number of candidates to return.

    Returns:
        List of FuzzyCandidate sorted by combined_score descending.
    """
    if not description or not activity_index:
        return []

    names = list(activity_index.values())
    ids = list(activity_index.keys())

    # Token sort ratio — good for reordered words ("erected spool" vs "spool erected")
    token_sort_results = process.extract(
        description,
        names,
        scorer=fuzz.token_sort_ratio,
        limit=top_k * 2,
        score_cutoff=30,  # Skip very poor matches early
    )

    # Partial ratio — good for descriptions that are substrings of plan names
    partial_results = process.extract(
        description,
        names,
        scorer=fuzz.partial_ratio,
        limit=top_k * 2,
        score_cutoff=30,
    )

    # Merge scores per candidate name
    scores: dict[str, dict] = {}
    for name, score, idx in token_sort_results:
        scores.setdefault(name, {"token_sort": 0.0, "partial": 0.0})
        scores[name]["token_sort"] = max(scores[name]["token_sort"], score)

    for name, score, idx in partial_results:
        scores.setdefault(name, {"token_sort": 0.0, "partial": 0.0})
        scores[name]["partial"] = max(scores[name]["partial"], score)

    candidates = []
    name_to_id = {v: k for k, v in activity_index.items()}

    for name, s in scores.items():
        activity_id = name_to_id.get(name)
        if not activity_id:
            continue
        ts = s["token_sort"]
        ps = s["partial"]
        combined = (0.6 * ts + 0.4 * ps) / 100.0  # Normalize to 0–1
        candidates.append(
            FuzzyCandidate(
                activity_id=activity_id,
                activity_name=name,
                token_sort_score=ts,
                partial_score=ps,
                combined_score=combined,
            )
        )

    candidates.sort(key=lambda c: c.combined_score, reverse=True)
    result = candidates[:top_k]

    log.debug(
        "fuzzy_matcher.done",
        description=description[:80],
        candidates=len(result),
        top_score=result[0].combined_score if result else 0,
    )

    return result
