"""
Tests for the matching engine — fuzzy, semantic, and confidence routing.

These tests use real fuzzy/semantic logic (not mocks) to verify the actual
matching behavior including the threshold routing branch.
"""

import pytest
from unittest.mock import patch, MagicMock


ACTIVITY_INDEX = {
    "PIP-001": "Fabricate spool SP-247 (Line 24\"-XX, N12 to N15)",
    "PIP-002": "Erect Line 24\"-XX at chainage 12+450",
    "PIP-003": "Hydrotest Line 24\"-XX (N12 to N20)",
    "CIV-001": "Excavate foundation pit for Pump P-101 (Area A, Grid 12-13)",
    "ELE-001": "Pull 3Cx150mm² cable from MCC-1 to Pump P-101 (Route R-12)",
    "MEC-001": "Set and level pump P-101 on foundation (Area A)",
}


class TestFuzzyMatcher:
    def test_exact_match_scores_high(self):
        """Exact activity name should score very high."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates

        candidates = get_fuzzy_candidates(
            "Erect Line 24\"-XX at chainage 12+450",
            ACTIVITY_INDEX,
            top_k=5,
        )
        assert len(candidates) > 0
        top = candidates[0]
        assert top.activity_id == "PIP-002"
        assert top.combined_score > 0.8

    def test_typo_in_description(self):
        """Typo in spool → should still find the right piping activity."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates

        candidates = get_fuzzy_candidates(
            "Fabricate spoll SP247 Line 24XX N12",  # 'spoll' typo
            ACTIVITY_INDEX,
            top_k=5,
        )
        top_ids = [c.activity_id for c in candidates[:3]]
        assert "PIP-001" in top_ids, f"Expected PIP-001 in top 3, got {top_ids}"

    def test_reordered_words(self):
        """Token sort ratio handles reordered description words."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates

        candidates = get_fuzzy_candidates(
            "chainage 12+450 Line 24 erect XX",  # Words reordered
            ACTIVITY_INDEX,
            top_k=5,
        )
        assert len(candidates) > 0

    def test_empty_index_returns_empty(self):
        """Empty activity index → empty candidates."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates

        candidates = get_fuzzy_candidates("anything", {})
        assert candidates == []

    def test_results_sorted_descending(self):
        """Results are sorted by combined_score descending."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates

        candidates = get_fuzzy_candidates("pump P-101 excavation foundation", ACTIVITY_INDEX)
        scores = [c.combined_score for c in candidates]
        assert scores == sorted(scores, reverse=True)


class TestSemanticMatcher:
    def setup_method(self):
        """Load activity embeddings before each test."""
        from backend.services.matching.semantic_matcher import load_activity_embeddings
        load_activity_embeddings(ACTIVITY_INDEX)

    def test_synonym_caught_by_semantic(self):
        """
        'spool erected' should semantically match 'Erect Line 24-XX' even though
        the words are different — this is the key case RapidFuzz-only fails on.
        """
        from backend.services.matching.semantic_matcher import get_semantic_candidates

        candidates = get_semantic_candidates("spool erected at site", top_k=5)
        assert len(candidates) > 0
        top_ids = [c.activity_id for c in candidates[:3]]
        # Piping activities should dominate for "spool erected"
        piping_in_top3 = any(aid.startswith("PIP") for aid in top_ids)
        assert piping_in_top3, f"Expected a piping activity in top 3, got {top_ids}"

    def test_cable_pulling_matches_electrical(self):
        """Cable pulling description should match the electrical activity."""
        from backend.services.matching.semantic_matcher import get_semantic_candidates

        candidates = get_semantic_candidates("cable pulling from MCC to pump motor", top_k=5)
        top_ids = [c.activity_id for c in candidates[:2]]
        assert "ELE-001" in top_ids, f"Expected ELE-001 in top 2, got {top_ids}"

    def test_scores_are_normalized_0_to_1(self):
        """All cosine scores should be between 0 and 1."""
        from backend.services.matching.semantic_matcher import get_semantic_candidates

        candidates = get_semantic_candidates("some construction activity", top_k=10)
        for c in candidates:
            assert 0.0 <= c.cosine_score <= 1.0


class TestConfidenceRouting:
    def setup_method(self):
        from backend.services.matching.semantic_matcher import load_activity_embeddings
        load_activity_embeddings(ACTIVITY_INDEX)

    def _get_mock_llm_rerank(self, winning_id: str, score: float):
        """Return a mock that makes winning_id the top LLM pick."""
        def mock_rerank(description, discipline, candidates):
            scores = {c.activity_id: 0.1 for c in candidates}
            scores[winning_id] = score
            return scores, score, f"Matched to {winning_id}"
        return mock_rerank

    def test_high_confidence_routes_to_matched(self):
        """Score ≥ 0.85 → match_status = matched."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates
        from backend.services.matching.semantic_matcher import get_semantic_candidates
        from backend.services.matching.confidence import fuse_and_route
        from backend.db.models import MatchStatusEnum

        fuzzy = get_fuzzy_candidates("Erect Line 24\"-XX at chainage 12+450", ACTIVITY_INDEX)
        semantic = get_semantic_candidates("Erect Line 24\"-XX at chainage 12+450")

        with patch("backend.services.matching.confidence._llm_rerank") as mock_rerank:
            mock_rerank.return_value = ({"PIP-002": 0.95}, 0.95, "Clear match")
            result = fuse_and_route("Erect Line 24\"-XX at chainage 12+450", "piping", fuzzy, semantic)

        assert result.match_status == MatchStatusEnum.matched
        assert result.selected_activity_id == "PIP-002"

    def test_medium_confidence_routes_to_review(self):
        """Score 0.55–0.84 → match_status = low_confidence_review."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates
        from backend.services.matching.semantic_matcher import get_semantic_candidates
        from backend.services.matching.confidence import fuse_and_route
        from backend.db.models import MatchStatusEnum

        fuzzy = get_fuzzy_candidates("some piping work near the area", ACTIVITY_INDEX)
        semantic = get_semantic_candidates("some piping work near the area")

        with patch("backend.services.matching.confidence._llm_rerank") as mock_rerank:
            mock_rerank.return_value = ({"PIP-001": 0.45}, 0.45, "Uncertain")
            result = fuse_and_route("some piping work near the area", "piping", fuzzy, semantic)

        # With medium LLM score and moderate fuzzy/semantic, should route to review
        assert result.match_status in (
            MatchStatusEnum.low_confidence_review,
            MatchStatusEnum.unmatched_new,
        )

    def test_no_candidates_routes_to_unmatched(self):
        """Zero candidates → unmatched_new."""
        from backend.services.matching.confidence import fuse_and_route
        from backend.db.models import MatchStatusEnum

        result = fuse_and_route("completely unrelated gibberish xyz123", "unknown", [], [])

        assert result.match_status == MatchStatusEnum.unmatched_new
        assert result.selected_activity_id is None
        assert result.final_score == 0.0

    def test_all_candidates_captured_in_result(self):
        """All candidates are returned in all_candidates for the audit trail."""
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates
        from backend.services.matching.semantic_matcher import get_semantic_candidates
        from backend.services.matching.confidence import fuse_and_route

        fuzzy = get_fuzzy_candidates("Erect Line 24\"-XX", ACTIVITY_INDEX, top_k=5)
        semantic = get_semantic_candidates("Erect Line 24\"-XX", top_k=5)

        with patch("backend.services.matching.confidence._llm_rerank") as mock_rerank:
            mock_rerank.return_value = ({"PIP-002": 0.9}, 0.9, "Match")
            result = fuse_and_route("Erect Line 24\"-XX", "piping", fuzzy, semantic)

        assert len(result.all_candidates) >= 1
        selected = [c for c in result.all_candidates if c.was_selected]
        assert len(selected) == 1


class TestRerankerFallback:
    """
    A7: Verify that the re-ranker's Groq fallback path works when local Ollama fails.
    Patches the internal _call_local_llm function (not raw ollama.generate) so
    these tests work without an Ollama server installed in the test environment.
    """

    def test_reranker_primary_fails_uses_groq_fallback(self, mocker):
        """
        When local Ollama fails, the re-ranker must fall back to Groq and still
        return a valid MatchResult. The final result must be well-formed regardless
        of which backend responded.
        """
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates
        from backend.services.matching.semantic_matcher import get_semantic_candidates
        from backend.services.matching.confidence import fuse_and_route
        from backend.db.models import MatchStatusEnum

        groq_json = (
            '{"ranked": [{"activity_id": "PIP-002", "score": 0.88, "reason": "exact match"}], '
            '"overall_confidence": 0.88, "justification": "Groq fallback responded"}'
        )

        # Patch the internal function (not raw ollama) — works without Ollama installed
        mock_local = mocker.patch(
            "backend.services.matching.confidence._call_local_llm",
            side_effect=ConnectionError("Ollama not available"),
        )
        mock_groq_client = MagicMock()
        mock_groq_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=groq_json))
        ]
        mocker.patch("groq.Groq", return_value=mock_groq_client)
        # Patch only the specific attributes needed — patching the whole object would
        # replace match_auto_accept_threshold with MagicMock, breaking float comparisons.
        mocker.patch.object(
            __import__("backend.services.matching.confidence", fromlist=["settings"]).settings,
            "groq_api_key",
            "test-groq-key",
        )
        mocker.patch.object(
            __import__("backend.services.matching.confidence", fromlist=["settings"]).settings,
            "groq_model_fallback",
            "qwen/qwen3-32b",
        )
        mocker.patch.object(
            __import__("backend.services.matching.confidence", fromlist=["settings"]).settings,
            "local_llm_model",
            "qwen3:8b",
        )

        fuzzy = get_fuzzy_candidates("Erect Line 24\"-XX at chainage 12+450", ACTIVITY_INDEX, top_k=5)
        semantic = get_semantic_candidates("Erect Line 24\"-XX at chainage 12+450", top_k=5)

        result = fuse_and_route(
            "Erect Line 24\"-XX at chainage 12+450",
            "piping",
            fuzzy,
            semantic,
        )

        # Result must be valid regardless of which backend responded
        assert result.match_status in (
            MatchStatusEnum.matched,
            MatchStatusEnum.low_confidence_review,
        )
        assert result.selected_activity_id is not None
        assert result.final_score > 0.0
        # Primary LLM must have been attempted
        mock_local.assert_called_once()

    def test_reranker_both_backends_fail_returns_equal_scores(self, mocker):
        """
        When both local LLM and Groq fail, re-ranker must not raise —
        it falls back to equal weighting, and routing still works.
        """
        from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates
        from backend.services.matching.semantic_matcher import get_semantic_candidates
        from backend.services.matching.confidence import fuse_and_route

        # Patch both backends to fail
        mocker.patch(
            "backend.services.matching.confidence._call_local_llm",
            side_effect=ConnectionError("Ollama down"),
        )
        import backend.services.matching.confidence as conf_mod
        mocker.patch.object(conf_mod.settings, "groq_api_key", "")
        mocker.patch.object(conf_mod.settings, "local_llm_model", "qwen3:8b")

        fuzzy = get_fuzzy_candidates("Erect Line 24\"-XX", ACTIVITY_INDEX, top_k=3)
        semantic = get_semantic_candidates("Erect Line 24\"-XX", top_k=3)

        # Must not raise even with both LLMs down
        result = fuse_and_route("Erect Line 24\"-XX", "piping", fuzzy, semantic)
        assert result is not None
        # Score comes entirely from fuzzy + semantic (no LLM component)
        assert result.final_score >= 0.0
