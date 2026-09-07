"""Pydantic schemas for plan activities and schedule operations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: str
    activity_id: str
    activity_name: str
    wbs_code: str | None = None
    discipline: str | None = None
    planned_start: datetime | None = None
    planned_finish: datetime | None = None
    original_duration_days: float | None = None
    percent_complete_plan: float = 0.0
    actual_start: datetime | None = None
    actual_finish: datetime | None = None
    actual_percent_complete: float | None = None
    is_field_confirmed: bool = False
    created_at: datetime


class PlanActivityCreate(BaseModel):
    """Used for POST /schedule/activities (confirm-new path)."""

    project_id: str
    activity_name: str = Field(..., min_length=2)
    discipline: str
    wbs_code: str | None = None
    planned_start: datetime | None = None
    planned_finish: datetime | None = None
    original_duration_days: float | None = None


class PlanActivityListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PlanActivityOut]


class XERExportOut(BaseModel):
    download_url: str
    filename: str
    activity_count: int
    generated_at: datetime
