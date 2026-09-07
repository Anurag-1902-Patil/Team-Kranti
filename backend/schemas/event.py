"""
Pydantic schemas for ProgressEvent — request/response validation.
These map to the §3.4 normalized schema from the project context.
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
    activity_description_extracted: str | None = None
    discipline: DisciplineEnum = DisciplineEnum.unknown
    event_type: EventTypeEnum | None = None
    actual_start_datetime: datetime | None = None
    actual_finish_datetime: datetime | None = None
    percent_complete: float | None = Field(default=None, ge=0, le=100)
    quantity_completed: float | None = None
    quantity_unit: str | None = None
    location_reference: str | None = None
    source_type: SourceTypeEnum | None = None
    source_document_id: str | None = None
    extracted_by: str = "time_agent_v1"
    extraction_timestamp: datetime | None = None
    audit_trail: dict[str, Any] | None = None


class ProgressEventOut(BaseModel):
    """API response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: str
    document_id: uuid.UUID | None = None
    activity_id_plan: str | None = None
    activity_name_plan: str | None = None
    activity_description_extracted: str | None = None
    discipline: DisciplineEnum
    event_type: EventTypeEnum | None = None
    actual_start_datetime: datetime | None = None
    actual_finish_datetime: datetime | None = None
    percent_complete: float | None = None
    quantity_completed: float | None = None
    quantity_unit: str | None = None
    location_reference: str | None = None
    confidence_score: float | None = None
    match_status: MatchStatusEnum
    source_type: SourceTypeEnum | None = None
    source_document_id: str | None = None
    extracted_by: str
    extraction_timestamp: datetime | None = None
    reviewed_by_planner: bool
    planner_notes: str | None = None
    audit_trail: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    # Hydrated on detail endpoint
    match_candidates: list[MatchCandidateSchema] = []


class ProgressEventListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProgressEventOut]
