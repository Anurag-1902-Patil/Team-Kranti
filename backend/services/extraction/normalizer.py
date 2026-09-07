"""
Schema normalizer — converts LLM ExtractedActivity output into ProgressEventCreate
(the §3.4 canonical schema).

Validates: discipline enum, event_type enum, datetime parsing, percent_complete range.
Maps unknown/invalid values to safe defaults rather than crashing — all assumptions
are recorded in the audit trail.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from dateutil import parser as dateutil_parser

from backend.db.models import DisciplineEnum, EventTypeEnum, SourceTypeEnum
from backend.schemas.event import ProgressEventCreate
from backend.services.extraction.llm_extractor import ExtractedActivity

log = structlog.get_logger(__name__)

DISCIPLINE_ALIASES: dict[str, DisciplineEnum] = {
    "pipe": DisciplineEnum.piping,
    "piping": DisciplineEnum.piping,
    "civil": DisciplineEnum.civil,
    "civils": DisciplineEnum.civil,
    "electrical": DisciplineEnum.electrical,
    "electric": DisciplineEnum.electrical,
    "elec": DisciplineEnum.electrical,
    "instrumentation": DisciplineEnum.instrumentation,
    "instrument": DisciplineEnum.instrumentation,
    "inst": DisciplineEnum.instrumentation,
    "hse": DisciplineEnum.hse,
    "safety": DisciplineEnum.hse,
    "structural": DisciplineEnum.structural,
    "structure": DisciplineEnum.structural,
    "mechanical": DisciplineEnum.mechanical,
    "mech": DisciplineEnum.mechanical,
    "unknown": DisciplineEnum.unknown,
}

EVENT_TYPE_ALIASES: dict[str, EventTypeEnum] = {
    "start": EventTypeEnum.start,
    "started": EventTypeEnum.start,
    "begin": EventTypeEnum.start,
    "finish": EventTypeEnum.finish,
    "finished": EventTypeEnum.finish,
    "complete": EventTypeEnum.finish,
    "completed": EventTypeEnum.finish,
    "done": EventTypeEnum.finish,
    "partial_complete": EventTypeEnum.partial_complete,
    "partial": EventTypeEnum.partial_complete,
    "in_progress": EventTypeEnum.partial_complete,
}


def _parse_discipline(raw: str | None) -> DisciplineEnum:
    if not raw:
        return DisciplineEnum.unknown
    normalized = raw.strip().lower()
    return DISCIPLINE_ALIASES.get(normalized, DisciplineEnum.unknown)


def _parse_event_type(raw: str | None) -> EventTypeEnum | None:
    if not raw:
        return None
    normalized = raw.strip().lower()
    return EVENT_TYPE_ALIASES.get(normalized)


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        # Ensure timezone-aware
        if dt.tzinfo is None:
            # Assume IST (UTC+5:30) for India-based projects
            from datetime import timedelta

            dt = dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        return dt
    except (ValueError, OverflowError) as exc:
        log.warning("normalizer.datetime_parse_failed", raw=raw, error=str(exc))
        return None


def normalize(
    extracted: ExtractedActivity,
    document_id: uuid.UUID | None,
    project_id: str,
    source_type: str | None,
    source_document_id: str | None,
    audit_trail: dict[str, Any],
) -> ProgressEventCreate:
    """
    Convert a single ExtractedActivity into a ProgressEventCreate.
    All parsing errors produce safe defaults and are logged — never crash.
    """
    discipline = _parse_discipline(extracted.discipline)
    event_type = _parse_event_type(extracted.event_type)
    actual_start = _parse_datetime(extracted.actual_start)
    actual_finish = _parse_datetime(extracted.actual_finish)

    # Validate percent_complete range
    pct = extracted.percent_complete
    if pct is not None and not (0 <= pct <= 100):
        log.warning("normalizer.pct_out_of_range", value=pct)
        pct = max(0.0, min(100.0, pct))

    # Source type normalization
    try:
        src_type = SourceTypeEnum(source_type) if source_type else SourceTypeEnum.unknown
    except ValueError:
        src_type = SourceTypeEnum.unknown

    # Merge extraction_notes into audit trail
    enriched_audit = {
        **audit_trail,
        "extraction_notes": extracted.extraction_notes,
        "normalizer_discipline_raw": extracted.discipline,
        "normalizer_discipline_mapped": discipline.value,
    }

    return ProgressEventCreate(
        project_id=project_id,
        document_id=document_id,
        activity_description_extracted=extracted.activity_description,
        discipline=discipline,
        event_type=event_type,
        actual_start_datetime=actual_start,
        actual_finish_datetime=actual_finish,
        percent_complete=pct,
        quantity_completed=extracted.quantity_completed,
        quantity_unit=extracted.quantity_unit,
        location_reference=extracted.location_reference,
        source_type=src_type,
        source_document_id=source_document_id,
        extracted_by="time_agent_v1",
        extraction_timestamp=datetime.now(tz=timezone.utc),
        audit_trail=enriched_audit,
    )
