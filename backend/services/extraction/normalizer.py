"""
Schema normalizer — converts LLM ExtractedActivity output into ProgressEventCreate.
Validates disciplines against the project ontology, normalizes dates, ranges,
and structures full per-field provenance metadata.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from dateutil import parser as dateutil_parser

from backend.core.config import get_settings
from backend.db.models import DisciplineEnum, EventTypeEnum, SourceTypeEnum
from backend.schemas.event import ProgressEventCreate
from backend.services.extraction.llm_extractor import ExtractedActivity

log = structlog.get_logger(__name__)
settings = get_settings()

DISCIPLINE_ALIASES: dict[str, str] = {
    "pipe": "piping",
    "piping": "piping",
    "civil": "civil",
    "civils": "civil",
    "structural": "structural",
    "structure": "structural",
    "steel": "structural",
    "mechanical": "mechanical",
    "mech": "mechanical",
    "static equipment": "static_equipment",
    "static_equipment": "static_equipment",
    "static": "static_equipment",
    "rotating equipment": "rotating_equipment",
    "rotating_equipment": "rotating_equipment",
    "rotating": "rotating_equipment",
    "electrical": "electrical",
    "electric": "electrical",
    "elec": "electrical",
    "instrumentation": "instrumentation",
    "instrument": "instrumentation",
    "inst": "instrumentation",
    "telecom": "telecom",
    "telecommunication": "telecom",
    "hvac": "hvac",
    "fire & safety": "fire_and_safety",
    "fire and safety": "fire_and_safety",
    "fire_and_safety": "fire_and_safety",
    "hse": "hse",
    "safety": "hse",
    "qa/qc": "qa_qc",
    "qa_qc": "qa_qc",
    "qa": "qa_qc",
    "qc": "qa_qc",
    "quality": "qa_qc",
    "procurement": "procurement",
    "purchase": "procurement",
    "engineering": "engineering",
    "design": "engineering",
    "planning": "planning",
    "scheduling": "planning",
    "commissioning": "commissioning",
    "pre-commissioning": "commissioning",
    "construction": "construction",
    "logistics": "logistics",
    "material management": "material_management",
    "material_management": "material_management",
    "materials": "material_management",
    "administration": "administration",
    "admin": "administration",
    "unknown": "unknown",
}

EVENT_TYPE_ALIASES: dict[str, EventTypeEnum] = {
    "start": EventTypeEnum.start,
    "started": EventTypeEnum.start,
    "begin": EventTypeEnum.start,
    "began": EventTypeEnum.start,
    "finish": EventTypeEnum.finish,
    "finished": EventTypeEnum.finish,
    "complete": EventTypeEnum.finish,
    "completed": EventTypeEnum.finish,
    "done": EventTypeEnum.finish,
    "partial_complete": EventTypeEnum.partial_complete,
    "partial": EventTypeEnum.partial_complete,
    "in_progress": EventTypeEnum.partial_complete,
    "ongoing": EventTypeEnum.partial_complete,
}


def _parse_discipline(raw: str | None) -> str:
    if not raw:
        return DisciplineEnum.unknown.value
    normalized = raw.strip().lower()
    return DISCIPLINE_ALIASES.get(normalized, DisciplineEnum.unknown.value)


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
        if dt.tzinfo is None:
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
    Convert a single ExtractedActivity into a ProgressEventCreate with full ontology metadata.
    """
    discipline = _parse_discipline(extracted.discipline)
    event_type = _parse_event_type(extracted.event_type)
    actual_start = _parse_datetime(extracted.actual_start)
    actual_finish = _parse_datetime(extracted.actual_finish)
    planned_start = _parse_datetime(extracted.planned_start)
    planned_finish = _parse_datetime(extracted.planned_finish)

    pct = extracted.percent_complete
    if pct is not None and not (0 <= pct <= 100):
        log.warning("normalizer.pct_out_of_range", value=pct)
        pct = max(0.0, min(100.0, pct))

    try:
        src_type = SourceTypeEnum(source_type) if source_type else SourceTypeEnum.unknown
    except ValueError:
        src_type = SourceTypeEnum.unknown

    # Compute confidence tier
    avg_conf = 0.85
    if extracted.field_provenance:
        scores = [v.get("confidence", 0.8) for v in extracted.field_provenance.values() if isinstance(v, dict)]
        if scores:
            avg_conf = sum(scores) / len(scores)

    if avg_conf >= settings.confidence_high_threshold:
        confidence_tier = "high"
    elif avg_conf >= settings.confidence_medium_threshold:
        confidence_tier = "medium"
    else:
        confidence_tier = "low"

    # Build structured ontology payload
    model_ver = audit_trail.get("model_version", settings.nvidia_nim_model)
    ontology_payload = {}
    for k, v in extracted.field_provenance.items():
        if isinstance(v, dict):
            ontology_payload[k] = {
                "value": v.get("value"),
                "confidence": v.get("confidence", avg_conf),
                "evidence": v.get("evidence"),
                "extraction_method": "llm_v2",
                "model_version": model_ver,
            }

    # Add core field metadata if not present in field_provenance
    core_fields = {
        "activity_description": (extracted.activity_description, 0.95),
        "discipline": (discipline, 0.90),
        "percent_complete": (pct, 0.92 if pct is not None else None),
        "actual_start": (extracted.actual_start, 0.88 if extracted.actual_start else None),
        "actual_finish": (extracted.actual_finish, 0.88 if extracted.actual_finish else None),
        "location": (extracted.location_reference, 0.85 if extracted.location_reference else None),
        "equipment": (extracted.equipment_tag, 0.90 if extracted.equipment_tag else None),
        "delay_category": (extracted.delay_category, 0.85 if extracted.delay_category else None),
    }
    for field_name, (val, conf) in core_fields.items():
        if val is not None and field_name not in ontology_payload:
            ontology_payload[field_name] = {
                "value": val,
                "confidence": conf or avg_conf,
                "evidence": extracted.extraction_notes or "extracted from message",
                "extraction_method": "llm_v2",
                "model_version": model_ver,
            }

    enriched_audit = {
        **audit_trail,
        "extraction_notes": extracted.extraction_notes,
        "normalizer_discipline_raw": extracted.discipline,
        "normalizer_discipline_mapped": discipline,
        "confidence_tier": confidence_tier,
    }

    return ProgressEventCreate(
        project_id=project_id,
        document_id=document_id,
        activity_description_extracted=extracted.activity_description,
        activity_description_raw=extracted.activity_description,
        activity_description_normalized=extracted.activity_description_normalized or extracted.activity_description,
        discipline=discipline,
        sub_discipline=extracted.sub_discipline,
        event_type=event_type,
        activity_type=extracted.activity_type,
        work_package=extracted.work_package,
        wbs_code=extracted.wbs_code,
        construction_phase=extracted.construction_phase,
        execution_stage=extracted.execution_stage,
        actual_start_datetime=actual_start,
        actual_finish_datetime=actual_finish,
        planned_start=planned_start,
        planned_finish=planned_finish,
        planned_duration_days=extracted.planned_duration_days,
        actual_duration_days=extracted.actual_duration_days,
        remaining_duration_days=extracted.remaining_duration_days,
        percent_complete=pct,
        quantity_completed=extracted.quantity_completed,
        quantity_unit=extracted.quantity_unit,
        location_reference=extracted.location_reference,
        location_area=extracted.location_area,
        location_unit=extracted.location_unit,
        equipment_tag=extracted.equipment_tag,
        line_number=extracted.line_number,
        tag_number=extracted.tag_number,
        drawing_reference=extracted.drawing_reference,
        material_reference=extracted.material_reference,
        contractor_name=extracted.contractor_name,
        supervisor_name=extracted.supervisor_name,
        engineer_name=extracted.engineer_name,
        crew_name=extracted.crew_name,
        status=extracted.status or "in_progress",
        delay_status=extracted.delay_status,
        delay_category=extracted.delay_category,
        delay_reason=extracted.delay_reason,
        blocker_description=extracted.blocker_description,
        priority=extracted.priority or "medium",
        is_critical_path=False,
        total_float_days=0.0,
        confidence_score=avg_conf,
        confidence_tier=confidence_tier,
        provenance_category="ai_extraction",
        source_type=src_type,
        source_document_id=source_document_id,
        extracted_by="time_agent_v2",
        extraction_timestamp=datetime.now(tz=timezone.utc),
        audit_trail=enriched_audit,
        ontology_payload=ontology_payload,
        correction_history=[],
    )
