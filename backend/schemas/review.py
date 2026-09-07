"""Pydantic schemas for human review decisions."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.db.models import ReviewDecisionEnum


class ReviewAcceptRequest(BaseModel):
    notes: str | None = None


class ReviewEditRequest(BaseModel):
    corrected_activity_id: str
    corrected_fields: dict[str, Any] | None = None
    notes: str | None = None


class ReviewDeclineRequest(BaseModel):
    notes: str | None = None


class ReviewConfirmNewRequest(BaseModel):
    """Body for confirming a genuinely new field activity not in the plan."""

    activity_name: str
    discipline: str
    planned_start: datetime | None = None
    planned_finish: datetime | None = None
    notes: str | None = None


class ReviewDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    reviewer_id: uuid.UUID | None = None
    decision: ReviewDecisionEnum
    corrected_activity_id: str | None = None
    corrected_fields: dict[str, Any] | None = None
    new_activity_id: str | None = None
    notes: str | None = None
    decided_at: datetime
