"""
Tests for the LLM extractor and schema normalizer.

These tests mock the LLM calls so they run without a Groq API key.
They test the actual parsing, validation, and normalization logic — not just
that a mock was called.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

IST = timezone(timedelta(hours=5, minutes=30))


class TestNormalizerHappyPath:
    def test_normalize_piping_start_event(self):
        """Full normalization of a piping start event."""
        from backend.services.extraction.llm_extractor import ExtractedActivity
        from backend.services.extraction.normalizer import normalize
        from backend.db.models import DisciplineEnum, EventTypeEnum

        extracted = ExtractedActivity(
            activity_description="Spool erection for Line 24\"-XX",
            event_type="start",
            actual_start="2026-08-27T09:30:00+05:30",
            actual_finish=None,
            discipline="piping",
            location_reference="Chainage 12+450",
        )

        result = normalize(
            extracted=extracted,
            document_id=uuid.uuid4(),
            project_id="TEST",
            source_type="free_text_dpr",
            source_document_id=None,
            audit_trail={"original_text": "test", "llm_used": "groq"},
        )

        assert result.discipline == DisciplineEnum.piping
        assert result.event_type == EventTypeEnum.start
        assert result.actual_start_datetime is not None
        assert result.actual_start_datetime.hour == 9
        assert result.actual_start_datetime.minute == 30
        assert result.location_reference == "Chainage 12+450"
        assert result.project_id == "TEST"

    def test_normalize_finish_event_with_percent(self):
        """Finish event with 100% complete."""
        from backend.services.extraction.llm_extractor import ExtractedActivity
        from backend.services.extraction.normalizer import normalize
        from backend.db.models import DisciplineEnum, EventTypeEnum

        extracted = ExtractedActivity(
            activity_description="Excavation complete for Pump P-101",
            event_type="finish",
            actual_finish="2026-08-28T16:00:00+05:30",
            discipline="civil",
            percent_complete=100.0,
        )

        result = normalize(
            extracted=extracted,
            document_id=None,
            project_id="TEST",
            source_type="spreadsheet",
            source_document_id="DPR.xlsx",
            audit_trail={},
        )

        assert result.discipline == DisciplineEnum.civil
        assert result.event_type == EventTypeEnum.finish
        assert result.percent_complete == 100.0
        assert result.actual_finish_datetime is not None

    def test_normalize_partial_complete(self):
        """Partial complete event."""
        from backend.services.extraction.llm_extractor import ExtractedActivity
        from backend.services.extraction.normalizer import normalize
        from backend.db.models import EventTypeEnum

        extracted = ExtractedActivity(
            activity_description="Cable pulling 40% done",
            event_type="partial_complete",
            discipline="electrical",
            percent_complete=40.0,
        )

        result = normalize(extracted=extracted, document_id=None, project_id="TEST",
                           source_type=None, source_document_id=None, audit_trail={})

        assert result.event_type == EventTypeEnum.partial_complete
        assert result.percent_complete == 40.0


class TestNormalizerEdgeCases:
    def test_normalize_unknown_discipline(self):
        """Unknown discipline string maps to DisciplineEnum.unknown."""
        from backend.services.extraction.llm_extractor import ExtractedActivity
        from backend.services.extraction.normalizer import normalize
        from backend.db.models import DisciplineEnum

        extracted = ExtractedActivity(
            activity_description="Something happened",
            event_type="start",
            discipline="welding",  # not in enum
        )

        result = normalize(extracted=extracted, document_id=None, project_id="TEST",
                           source_type=None, source_document_id=None, audit_trail={})

        assert result.discipline == DisciplineEnum.unknown

    def test_normalize_missing_dates(self):
        """Missing dates produce None, not an error."""
        from backend.services.extraction.llm_extractor import ExtractedActivity
        from backend.services.extraction.normalizer import normalize

        extracted = ExtractedActivity(
            activity_description="Some activity",
            event_type="finish",
            discipline="piping",
            actual_start=None,
            actual_finish=None,
        )

        result = normalize(extracted=extracted, document_id=None, project_id="TEST",
                           source_type=None, source_document_id=None, audit_trail={})

        assert result.actual_start_datetime is None
        assert result.actual_finish_datetime is None

    def test_normalize_percent_clamped_over_100(self):
        """Percent > 100 passed through model_construct (bypassing schema validation) is clamped to 100 by the normalizer."""
        from backend.services.extraction.llm_extractor import ExtractedActivity
        from backend.services.extraction.normalizer import normalize

        # Use model_construct to bypass Pydantic field validation (ge/le) so we can
        # test that the normalizer itself clamps — not Pydantic.
        extracted = ExtractedActivity.model_construct(
            activity_description="Test",
            event_type="finish",
            discipline="civil",
            percent_complete=150.0,  # Deliberately out of range
            actual_start=None,
            actual_finish=None,
            quantity_completed=None,
            quantity_unit=None,
            location_reference=None,
            extraction_notes=None,
        )

        result = normalize(extracted=extracted, document_id=None, project_id="TEST",
                           source_type=None, source_document_id=None, audit_trail={})

        assert result.percent_complete == 100.0

    def test_normalize_malformed_datetime_produces_none(self):
        """Malformed datetime string → None (not a crash)."""
        from backend.services.extraction.llm_extractor import ExtractedActivity
        from backend.services.extraction.normalizer import normalize

        extracted = ExtractedActivity(
            activity_description="Test",
            event_type="start",
            discipline="civil",
            actual_start="not-a-date-at-all-###",
        )

        result = normalize(extracted=extracted, document_id=None, project_id="TEST",
                           source_type=None, source_document_id=None, audit_trail={})

        assert result.actual_start_datetime is None


class TestLLMExtractorParsing:
    """Tests for the JSON parsing and validation logic in llm_extractor."""

    def test_parse_valid_llm_response(self):
        """Valid JSON response from LLM is parsed into ExtractedActivity list."""
        from backend.services.extraction.llm_extractor import _parse_llm_response

        raw = json.dumps({
            "activities": [
                {
                    "activity_description": "Spool erection Line 24",
                    "event_type": "start",
                    "actual_start": "2026-08-27T09:30:00+05:30",
                    "actual_finish": None,
                    "percent_complete": None,
                    "quantity_completed": None,
                    "quantity_unit": None,
                    "location_reference": "CH 12+450",
                    "discipline": "piping",
                    "extraction_notes": None,
                }
            ]
        })

        activities = _parse_llm_response(raw)
        assert len(activities) == 1
        assert activities[0].activity_description == "Spool erection Line 24"
        assert activities[0].discipline == "piping"

    def test_parse_response_with_markdown_fences(self):
        """LLM response wrapped in code fences is handled."""
        from backend.services.extraction.llm_extractor import _parse_llm_response

        raw = """```json
{"activities": [{"activity_description": "Test", "event_type": "finish", "discipline": "civil", "actual_start": null, "actual_finish": null, "percent_complete": null, "quantity_completed": null, "quantity_unit": null, "location_reference": null, "extraction_notes": null}]}
```"""

        activities = _parse_llm_response(raw)
        assert len(activities) == 1

    def test_nim_success_extracts_activities(self):
        """When NVIDIA NIM succeeds, extract_activities returns valid results."""
        valid_response = json.dumps({
            "activities": [
                {
                    "activity_description": "Foundation work",
                    "event_type": "finish",
                    "actual_start": None,
                    "actual_finish": "2026-08-28T16:00:00+05:30",
                    "percent_complete": 100.0,
                    "quantity_completed": None,
                    "quantity_unit": None,
                    "location_reference": None,
                    "discipline": "civil",
                    "extraction_notes": None,
                }
            ]
        })

        # Patch the internal NIM call directly — no real API key needed in tests.
        with patch("backend.services.extraction.llm_extractor._call_nvidia_nim") as mock_nim:
            mock_nim.return_value = valid_response

            from backend.services.extraction.llm_extractor import extract_activities
            activities, audit = extract_activities(
                text="Foundation work complete",
                discipline_hint="civil",
                source_label="test",
            )

        assert len(activities) == 1
        assert activities[0].event_type == "finish"
        assert activities[0].discipline == "civil"
        # NIM must have been called once
        mock_nim.assert_called_once()
        assert "nvidia-nim" in audit["llm_used"]
