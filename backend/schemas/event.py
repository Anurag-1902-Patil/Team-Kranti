"""
Pydantic schemas for ProgressEvent — request/response validation.
Maps to the expanded §3.4 execution ontology with auditable provenance.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models import (
    DisciplineEnum,
    EventTypeEnum,
    MatchStatusEnum,
    SourceTypeEnum,
)


class MatchCandidateSchema(BaseModel):
    candidate_activity_id: str
    activity_name: str | None = None
    fuzzy_score: float | None = None
    semantic_score: float | None = None
    llm_score: float | None = None
    final_score: float | None = None
    rank: int | None = None
    was_selected: bool = False


class ProgressEventCreate(BaseModel):
    """Internal schema — created by the normalizer service."""

    project_id: str
    document_id: uuid.UUID | None = None
    activity_id_plan: str | None = None
    plan_activity_id: uuid.UUID | None = None
    activity_name_plan: str | None = None
    activity_description_extracted: str | None = None
    activity_description_raw: str | None = None
    activity_description_normalized: str | None = None
    discipline: str | DisciplineEnum = DisciplineEnum.unknown
    sub_discipline: str | None = None
    event_type: EventTypeEnum | None = None
    activity_type: str | None = None
    work_package: str | None = None
    wbs_code: str | None = None
    construction_phase: str | None = None
    execution_stage: str | None = None

    actual_start_datetime: datetime | None = None
    actual_finish_datetime: datetime | None = None
    planned_start: datetime | None = None
    planned_finish: datetime | None = None
    planned_duration_days: float | None = None
    actual_duration_days: float | None = None
    remaining_duration_days: float | None = None
    percent_complete: float | None = Field(default=None, ge=0, le=100)
    quantity_completed: float | None = None
    quantity_unit: str | None = None

    location_reference: str | None = None
    location_area: str | None = None
    location_unit: str | None = None
    equipment_tag: str | None = None
    line_number: str | None = None
    tag_number: str | None = None
    drawing_reference: str | None = None
    material_reference: str | None = None

    contractor_id: uuid.UUID | None = None
    contractor_name: str | None = None
    supervisor_name: str | None = None
    engineer_name: str | None = None
    crew_name: str | None = None

    status: str | None = "in_progress"
    delay_status: str | None = None
    delay_category: str | None = None
    delay_reason: str | None = None
    blocker_description: str | None = None
    priority: str | None = "medium"
    is_critical_path: bool = False
    total_float_days: float = 0.0

    confidence_score: float | None = None
    confidence_tier: str = "medium"
    match_status: MatchStatusEnum = MatchStatusEnum.pending_match
    provenance_category: str = "ai_extraction"
    source_type: SourceTypeEnum | None = None
    source_document_id: str | None = None
    extracted_by: str = "time_agent_v2"
    extraction_timestamp: datetime | None = None
    reviewed_by_planner: bool = False
    planner_notes: str | None = None
    audit_trail: dict[str, Any] | None = None
    ontology_payload: dict[str, Any] | None = None
    correction_history: list[dict[str, Any]] | None = None


class ProgressEventOut(BaseModel):
    """API response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: str
    document_id: uuid.UUID | None = None
    activity_id_plan: str | None = None
    plan_activity_id: uuid.UUID | None = None
    activity_name_plan: str | None = None
    activity_description_extracted: str | None = None
    activity_description_raw: str | None = None
    activity_description_normalized: str | None = None
    discipline: str
    sub_discipline: str | None = None
    event_type: EventTypeEnum | None = None
    activity_type: str | None = None
    work_package: str | None = None
    wbs_code: str | None = None
    construction_phase: str | None = None
    execution_stage: str | None = None

    actual_start_datetime: datetime | None = None
    actual_finish_datetime: datetime | None = None
    planned_start: datetime | None = None
    planned_finish: datetime | None = None
    planned_duration_days: float | None = None
    actual_duration_days: float | None = None
    remaining_duration_days: float | None = None
    percent_complete: float | None = None
    quantity_completed: float | None = None
    quantity_unit: str | None = None

    location_reference: str | None = None
    location_area: str | None = None
    location_unit: str | None = None
    equipment_tag: str | None = None
    line_number: str | None = None
    tag_number: str | None = None
    drawing_reference: str | None = None
    material_reference: str | None = None

    contractor_id: uuid.UUID | None = None
    contractor_name: str | None = None
    supervisor_name: str | None = None
    engineer_name: str | None = None
    crew_name: str | None = None

    status: str | None = "in_progress"
    delay_status: str | None = None
    delay_category: str | None = None
    delay_reason: str | None = None
    blocker_description: str | None = None
    priority: str | None = "medium"
    is_critical_path: bool = False
    total_float_days: float = 0.0

    confidence_score: float | None = None
    confidence_tier: str = "medium"
    match_status: MatchStatusEnum
    provenance_category: str = "ai_extraction"
    source_type: SourceTypeEnum | None = None
    source_document_id: str | None = None
    extracted_by: str
    extraction_timestamp: datetime | None = None
    reviewed_by_planner: bool
    planner_notes: str | None = None
    audit_trail: dict[str, Any] | None = None
    ontology_payload: dict[str, Any] | None = None
    correction_history: list[dict[str, Any]] | None = None
    created_at: datetime
    updated_at: datetime

    match_candidates: list[MatchCandidateSchema] = []


class ProgressEventListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProgressEventOut]
