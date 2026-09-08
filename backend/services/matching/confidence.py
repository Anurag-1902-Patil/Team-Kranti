"""
Confidence scoring, LLM re-ranking, and threshold-gated routing.

Pipeline:
  1. Receive top-k fuzzy candidates + top-k semantic candidates
  2. Merge by activity_id, deduplicate, normalize scores
  3. LLM re-ranker (NVIDIA NIM — nvidia/nemotron-3-super-120b-a12b):
     given description + top-5 candidates, output ranked list with scores
  4. Fuse: 0.3 * fuzzy_norm + 0.3 * semantic_norm + 0.4 * llm_score
  5. Route by threshold: matched / low_confidence_review / unmatched_new

The fused score and all intermediate scores are persisted to the matches table
for full audit trail.
"""

import json
from dataclasses import dataclass, field

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


# ---------------------------------------------------------------------------
# Prompt — instructs Nemotron to return bare activity IDs, never full labels.
#
# Critical requirement: the model must copy the code (e.g. "PIP-003") exactly
# as it appears between the brackets in the candidate list, not the full label.
# The prompt makes this explicit to reduce bracket-echoing behaviour.
# ---------------------------------------------------------------------------
LLM_RERANK_PROMPT = """\
You are helping match a construction site activity report to the correct planned activity.

Field description (what the supervisor reported):
"{description}"

Discipline: {discipline}

Candidate planned activities (top candidates by string and semantic similarity):
{candidates_text}

Each candidate is shown as: [ACTIVITY_CODE] Activity Name

Rank these candidates from most to least likely match.
For each, assign a confidence score from 0.0 to 1.0 (1.0 = certain match).
Consider: same physical work, same location/equipment, same discipline.

IMPORTANT — activity_id rules:
- The "activity_id" value must be ONLY the code, e.g. PIP-003
- Copy it EXACTLY from between the brackets in the candidate list above
- Do NOT include brackets: write PIP-003, not [PIP-003]
- Do NOT include the activity name: write PIP-003, not "PIP-003 Hydrotest..."
- Do NOT invent or guess an activity_id that is not in the candidate list

Return ONLY valid JSON in this exact format:
{{
  "ranked": [
    {{"activity_id": "PIP-003", "score": 0.95, "reason": "brief reason"}},
    ...
  ],
  "overall_confidence": 0.95,
  "justification": "brief explanation of your top choice"
}}\
"""


def _normalize_llm_activity_id(raw: str) -> str:
    """
    Normalize an activity_id string as returned by the LLM.

    Handles all observed Nemotron output formats:
      - "PIP-003"                                         -> PIP-003
      - "[PIP-003]"                                       -> PIP-003
      - "[PIP-003] Hydrotest Line 24\"-XX (N12 to N20)"   -> PIP-003
      - '"PIP-003"'  (surrounding JSON-quote artifact)    -> PIP-003

    Does NOT guess or fuzzy-match — returns the normalized string as-is.
    The caller validates against the known candidate set.
    """
    s = raw.strip()
    # Strip surrounding single or double quotes (JSON string-escaping artifact)
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        s = s[1:-1].strip()
    # Extract code from "[CODE] Name..." or "[CODE]" patterns
    if s.startswith("[") and "]" in s:
        s = s[1:s.index("]")].strip()
    return s


def _call_nvidia_nim(prompt: str) -> str:
    """Call NVIDIA NIM (nemotron-3-super-120b-a12b) via OpenAI-compatible API. Separated for testability."""
    from openai import OpenAI
    client = OpenAI(
        base_url=settings.nvidia_nim_base_url,
        api_key=settings.nvidia_api_key,
    )
    resp = client.chat.completions.create(
        model=settings.nvidia_nim_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
        top_p=0.95,
        max_tokens=800,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return resp.choices[0].message.content


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5), reraise=True)
def _llm_rerank(
    description: str,
    discipline: str,
    candidates: list[MatchCandidate],
) -> tuple[dict[str, float], float, str]:
    """
    Call LLM to re-rank candidates.

    Backend: NVIDIA NIM (nvidia/nemotron-3-super-120b-a12b) via OpenAI-compatible API.

    Returns: (activity_id -> llm_score, overall_confidence, justification)
    """
    top5 = candidates[:5]
    # Build the valid-ID set from the candidates being sent to the LLM.
    # Only IDs present here can legitimately appear in the response.
    valid_ids: set[str] = {c.activity_id for c in top5}

    candidates_text = "\n".join(
        f"{i+1}. [{c.activity_id}] {c.activity_name}"
        for i, c in enumerate(top5)
    )

    prompt = LLM_RERANK_PROMPT.format(
        description=description,
        discipline=discipline,
        candidates_text=candidates_text,
    )

    raw_response = None

    # --- NVIDIA NIM ---
    try:
        raw_response = _call_nvidia_nim(prompt)
        log.debug("confidence.nim_rerank_success", model=settings.nvidia_nim_model)
    except Exception as exc:
        log.warning("confidence.nim_rerank_failed", model=settings.nvidia_nim_model, error=str(exc))

    # Last resort: equal weighting
    if raw_response is None:
        equal_score = 1.0 / max(len(candidates), 1)
        return (
            {c.activity_id: equal_score for c in candidates[:5]},
            equal_score,
            "LLM unavailable — equal weighting applied",
        )

    # Parse response — handle Nemotron <think> blocks
    try:
        text = raw_response.strip()
        if "<think>" in text:
            end_think = text.rfind("</think>")
            if end_think != -1:
                text = text[end_think + len("</think>"):].strip()

        # Strip markdown code fences — defensive pattern (same as llm_extractor.py)
        if text.startswith("```"):
            lines = text.split("\n")
            inner_lines = lines[1:]  # drop opening ```json line
            if inner_lines and inner_lines[-1].strip() == "```":
                inner_lines = inner_lines[:-1]  # drop closing ``` only if present
            text = "\n".join(inner_lines).strip()

        data = json.loads(text)
        ranked = data.get("ranked", [])
        scores: dict[str, float] = {}

        for item in ranked:
            try:
                raw_id = str(item.get("activity_id", "")).strip()
                if not raw_id:
                    log.warning("confidence.rerank_empty_id", item=str(item)[:100])
                    continue

                # Normalize all LLM formatting variants to a bare ID
                activity_id = _normalize_llm_activity_id(raw_id)

                # Guard: only accept IDs that were actually sent to the LLM
                if activity_id not in valid_ids:
                    log.warning(
                        "confidence.rerank_unknown_id",
                        raw_id=raw_id,
                        normalized=activity_id,
                        valid_ids=sorted(valid_ids),
                    )
                    continue

                # Guard: duplicate ID — keep first occurrence (highest rank position)
                if activity_id in scores:
                    log.debug(
                        "confidence.rerank_duplicate_id",
                        activity_id=activity_id,
                        kept_score=scores[activity_id],
                        discarded_score=item.get("score"),
                    )
                    continue

                # Validate and clamp score to [0.0, 1.0]
                score = float(item.get("score", 0.0))
                score = max(0.0, min(1.0, score))
                scores[activity_id] = score

            except (TypeError, ValueError) as item_exc:
                log.warning("confidence.rerank_item_parse_failed", item=str(item)[:100], error=str(item_exc))
                continue

        overall = max(0.0, min(1.0, float(data.get("overall_confidence", 0.0))))
        justification = str(data.get("justification", ""))
        return scores, overall, justification

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        log.warning(
            "confidence.rerank_parse_failed",
            error=str(exc),
            raw=raw_response[:300] if raw_response else None,
        )
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
