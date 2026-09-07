"""
Confidence scoring, LLM re-ranking, and threshold-gated routing.

Pipeline:
  1. Receive top-k fuzzy candidates + top-k semantic candidates
  2. Merge by activity_id, deduplicate, normalize scores
  3. LLM re-ranker (primary: local Qwen3-8B; fallback: Groq qwen/qwen3-32b):
     given description + top-5 candidates, output ranked list with scores
  4. Fuse: 0.3 * fuzzy_norm + 0.3 * semantic_norm + 0.4 * llm_score
  5. Route by threshold: matched / low_confidence_review / unmatched_new

The fused score and all intermediate scores are persisted to the matches table
for full audit trail.
"""

import json
from dataclasses import dataclass, field
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import get_settings
from backend.db.models import MatchStatusEnum
from backend.services.matching.fuzzy_matcher import FuzzyCandidate
from backend.services.matching.semantic_matcher import SemanticCandidate

log = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class MatchCandidate:
    """Merged candidate with all scoring dimensions."""
    activity_id: str
    activity_name: str
    fuzzy_score: float = 0.0      # 0–1
    semantic_score: float = 0.0   # 0–1
    llm_score: float = 0.0        # 0–1 (from LLM re-ranker)
    final_score: float = 0.0      # Fused
    rank: int = 0
    was_selected: bool = False


@dataclass
class MatchResult:
    """Output of the full matching pipeline."""
    selected_activity_id: str | None
    selected_activity_name: str | None
    final_score: float
    match_status: MatchStatusEnum
    all_candidates: list[MatchCandidate] = field(default_factory=list)
    llm_justification: str | None = None


def _merge_candidates(
    fuzzy: list[FuzzyCandidate],
    semantic: list[SemanticCandidate],
) -> dict[str, MatchCandidate]:
    """Merge fuzzy and semantic candidates by activity_id."""
    merged: dict[str, MatchCandidate] = {}

    for fc in fuzzy:
        merged[fc.activity_id] = MatchCandidate(
            activity_id=fc.activity_id,
            activity_name=fc.activity_name,
            fuzzy_score=fc.combined_score,
        )

    for sc in semantic:
        if sc.activity_id in merged:
            merged[sc.activity_id].semantic_score = sc.cosine_score
        else:
            merged[sc.activity_id] = MatchCandidate(
                activity_id=sc.activity_id,
                activity_name=sc.activity_name,
                semantic_score=sc.cosine_score,
            )

    return merged


LLM_RERANK_PROMPT = """You are helping match a construction site activity report to the correct planned activity.

Field description (what the supervisor reported):
"{description}"

Discipline: {discipline}

Candidate planned activities (top candidates by string and semantic similarity):
{candidates_text}

Rank these candidates from most to least likely match.
For each, assign a confidence score from 0.0 to 1.0 (1.0 = certain match).
Consider: same physical work, same location/equipment, same discipline.

Return JSON:
{{
  "ranked": [
    {{"activity_id": "...", "score": 0.0, "reason": "brief reason"}},
    ...
  ],
  "overall_confidence": 0.0,
  "justification": "brief explanation of your top choice"
}}"""


def _call_local_llm(prompt: str) -> str:
    """Call local Qwen3-8B via Ollama. Separated for testability."""
    import ollama
    resp = ollama.generate(
        model=settings.local_llm_model,
        prompt=prompt,
        options={"temperature": 0.1},
    )
    return resp["response"]


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5), reraise=True)
def _llm_rerank(
    description: str,
    discipline: str,
    candidates: list[MatchCandidate],
) -> tuple[dict[str, float], float, str]:
    """
    Call LLM to re-rank candidates.

    Primary: local Qwen3-8B via Ollama (settings.local_llm_model)
    Fallback: Groq qwen/qwen3-32b (settings.groq_model_fallback)

    Returns: (activity_id → llm_score, overall_confidence, justification)
    """
    candidates_text = "\n".join(
        f"{i+1}. [{c.activity_id}] {c.activity_name}"
        for i, c in enumerate(candidates[:5])
    )

    prompt = LLM_RERANK_PROMPT.format(
        description=description,
        discipline=discipline,
        candidates_text=candidates_text,
    )

    raw_response = None

    # --- Primary: local Qwen3-8B via Ollama ---
    try:
        raw_response = _call_local_llm(prompt)
        log.debug("confidence.local_rerank_success", model=settings.local_llm_model)
    except Exception as exc:
        log.warning("confidence.local_rerank_failed", model=settings.local_llm_model, error=str(exc))

    # --- Fallback: Groq qwen/qwen3-32b ---
    if raw_response is None and settings.groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=settings.groq_api_key)
            resp = client.chat.completions.create(
                model=settings.groq_model_fallback,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,
            )
            raw_response = resp.choices[0].message.content
            log.info("confidence.groq_fallback_rerank_success", model=settings.groq_model_fallback)
        except Exception as exc:
            log.error("confidence.groq_rerank_failed", error=str(exc))

    # Last resort: equal weighting
    if raw_response is None:
        equal_score = 1.0 / max(len(candidates), 1)
        return (
            {c.activity_id: equal_score for c in candidates[:5]},
            equal_score,
            "LLM unavailable — equal weighting applied",
        )

    # Parse response — handle Qwen3 <think> blocks
    try:
        text = raw_response.strip()
        if "<think>" in text:
            end_think = text.rfind("</think>")
            if end_think != -1:
                text = text[end_think + len("</think>"):].strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1])
        data = json.loads(text)
        ranked = data.get("ranked", [])
        scores = {item["activity_id"]: float(item["score"]) for item in ranked}
        overall = float(data.get("overall_confidence", 0.0))
        justification = data.get("justification", "")
        return scores, overall, justification
    except Exception as exc:
        log.warning("confidence.rerank_parse_failed", error=str(exc))
        return {}, 0.0, ""


def fuse_and_route(
    description: str,
    discipline: str,
    fuzzy_candidates: list[FuzzyCandidate],
    semantic_candidates: list[SemanticCandidate],
) -> MatchResult:
    """
    Full matching pipeline: merge → LLM re-rank → fuse scores → threshold route.

    Args:
        description: Extracted activity description.
        discipline: Discipline enum value string.
        fuzzy_candidates: From fuzzy_matcher.get_fuzzy_candidates()
        semantic_candidates: From semantic_matcher.get_semantic_candidates()

    Returns:
        MatchResult with selected activity, final score, status, and all candidates.
    """
    if not fuzzy_candidates and not semantic_candidates:
        log.info("confidence.no_candidates", description=description[:80])
        return MatchResult(
            selected_activity_id=None,
            selected_activity_name=None,
            final_score=0.0,
            match_status=MatchStatusEnum.unmatched_new,
        )

    # Step 1: Merge
    merged = _merge_candidates(fuzzy_candidates, semantic_candidates)
    candidates = list(merged.values())

    # Sort by combined fuzzy+semantic for LLM input selection
    candidates.sort(key=lambda c: 0.5 * c.fuzzy_score + 0.5 * c.semantic_score, reverse=True)
    top_for_llm = candidates[:5]

    # Step 2: LLM re-rank
    try:
        llm_scores, overall_confidence, justification = _llm_rerank(
            description, discipline, top_for_llm
        )
    except Exception as exc:
        log.warning("confidence.rerank_error", error=str(exc))
        llm_scores = {}
        overall_confidence = 0.0
        justification = f"LLM re-rank failed: {exc}"

    # Step 3: Fuse scores
    for c in candidates:
        c.llm_score = llm_scores.get(c.activity_id, 0.0)
        c.final_score = (
            0.30 * c.fuzzy_score
            + 0.30 * c.semantic_score
            + 0.40 * c.llm_score
        )

    # Sort by final_score
    candidates.sort(key=lambda c: c.final_score, reverse=True)
    for i, c in enumerate(candidates):
        c.rank = i + 1

    best = candidates[0] if candidates else None
    best_score = best.final_score if best else 0.0

    # Step 4: Threshold routing (ADR-010)
    auto_threshold = settings.match_auto_accept_threshold
    review_threshold = settings.match_review_threshold

    if best_score >= auto_threshold:
        status = MatchStatusEnum.matched
    elif best_score >= review_threshold:
        status = MatchStatusEnum.low_confidence_review
    else:
        status = MatchStatusEnum.unmatched_new

    if best:
        best.was_selected = True

    log.info(
        "confidence.routing_decision",
        description=description[:80],
        best_activity=best.activity_id if best else None,
        final_score=round(best_score, 3),
        status=status.value,
    )

    return MatchResult(
        selected_activity_id=best.activity_id if best else None,
        selected_activity_name=best.activity_name if best else None,
        final_score=best_score,
        match_status=status,
        all_candidates=candidates,
        llm_justification=justification,
    )
