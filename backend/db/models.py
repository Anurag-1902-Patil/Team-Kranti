"""
SQLAlchemy ORM models for SIH26122.

Tables:
  - users             (minimal reviewer identity)
  - sender_profiles   (WhatsApp sender → discipline mapping)
  - plan_activities   (sourced from P6 XER — the activity index)
  - documents         (raw ingested messages/files)
  - progress_events   (normalized §3.4 schema — one per extracted activity event)
  - matches           (all candidates considered during matching)
  - review_decisions  (append-only planner decisions — never overwritten)
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DisciplineEnum(str, PyEnum):
    piping = "piping"
    civil = "civil"
    electrical = "electrical"
    instrumentation = "instrumentation"
    hse = "hse"
    structural = "structural"
    mechanical = "mechanical"
    unknown = "unknown"


class EventTypeEnum(str, PyEnum):
    start = "start"
    finish = "finish"
    partial_complete = "partial_complete"


class SourceTypeEnum(str, PyEnum):
    free_text_dpr = "free_text_dpr"
    spreadsheet = "spreadsheet"
    scanned_diary = "scanned_diary"
    voice_log = "voice_log"
    image_annotation = "image_annotation"
    unknown = "unknown"


class MatchStatusEnum(str, PyEnum):
    pending_match = "pending_match"
    matched = "matched"
    low_confidence_review = "low_confidence_review"
    unmatched_new = "unmatched_new"
    declined = "declined"
    processing_failed = "processing_failed"


class ReviewDecisionEnum(str, PyEnum):
    accepted = "accepted"
    edited = "edited"
    declined = "declined"
    confirmed_new = "confirmed_new"


class UserRoleEnum(str, PyEnum):
    reviewer = "reviewer"
    planner = "planner"
    admin = "admin"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    """Minimal reviewer identity — single shared token for prototype."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.reviewer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review_decisions = relationship("ReviewDecision", back_populates="reviewer")


class SenderProfile(Base):
    """
    Maps WhatsApp sender_id to a discipline and display name.
    Seeded at demo startup. When no profile exists, the LLM infers discipline
    from message content (discipline_hint=None path).
    """

    __tablename__ = "sender_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=True)
    discipline = Column(String(50), nullable=True)
    project_id = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PlanActivity(Base):
    """
    Activities sourced from the Primavera P6 XER export (or synthetic equivalent).
    This is the index that the matching engine runs against.
    Embedding stored in ChromaDB; embedding_id links back to the ChromaDB doc.
    """

    __tablename__ = "plan_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(200), nullable=False, index=True)
    activity_id = Column(String(100), unique=True, nullable=False, index=True)
    activity_name = Column(Text, nullable=False)
    wbs_code = Column(String(200), nullable=True)
    discipline = Column(String(50), nullable=True, index=True)
    planned_start = Column(DateTime(timezone=True), nullable=True)
    planned_finish = Column(DateTime(timezone=True), nullable=True)
    original_duration_days = Column(Float, nullable=True)
    percent_complete_plan = Column(Float, default=0.0)
    # Actual progress (our system writes these)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_finish = Column(DateTime(timezone=True), nullable=True)
    actual_percent_complete = Column(Float, nullable=True)
    # Link to ChromaDB embedding
    embedding_id = Column(String(200), nullable=True)
    # Whether this was created by confirm_new (vs loaded from XER)
    is_field_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    matches = relationship("Match", back_populates="plan_activity")
    progress_events = relationship("ProgressEvent", back_populates="plan_activity")


class Document(Base):
    """
    Raw ingested message/file — one row per WhatsApp message.
    Idempotency guard: message_id is UNIQUE.
    """

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("message_id", name="uq_documents_message_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(200), unique=True, nullable=False, index=True)
    sender_id = Column(String(50), nullable=False, index=True)
    source_type = Column(
        Enum(SourceTypeEnum), nullable=False, default=SourceTypeEnum.unknown
    )
    raw_text = Column(Text, nullable=True)
    mime_type = Column(String(100), nullable=True)
    # MinIO object keys
    s3_key = Column(String(500), nullable=True)
    extracted_text_s3_key = Column(String(500), nullable=True)
    # Processing state
    processing_status = Column(String(50), default="queued", nullable=False, index=True)
    processing_error = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progress_events = relationship("ProgressEvent", back_populates="document")


class ProgressEvent(Base):
    """
    Normalized §3.4 progress event — one row per extracted activity event.
    audit_trail JSONB stores: original_text, llm_prompt, llm_response, alternatives_considered.
    """

    __tablename__ = "progress_events"
    __table_args__ = (
        Index("ix_pe_activity_id_plan", "activity_id_plan"),
        Index("ix_pe_match_status", "match_status"),
        Index("ix_pe_project_id", "project_id"),
        Index("ix_pe_discipline", "discipline"),
        Index("ix_pe_extraction_timestamp", "extraction_timestamp"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(200), nullable=False)

    # FK to source document
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True
    )

    # Matched plan activity (FK, nullable until matched)
    activity_id_plan = Column(String(100), nullable=True)
    plan_activity_id = Column(
        UUID(as_uuid=True), ForeignKey("plan_activities.id"), nullable=True, index=True
    )
    activity_name_plan = Column(Text, nullable=True)

    # Extracted fields
    activity_description_extracted = Column(Text, nullable=True)
    discipline = Column(
        Enum(DisciplineEnum), nullable=False, default=DisciplineEnum.unknown
    )
    event_type = Column(Enum(EventTypeEnum), nullable=True)
    actual_start_datetime = Column(DateTime(timezone=True), nullable=True)
    actual_finish_datetime = Column(DateTime(timezone=True), nullable=True)
    percent_complete = Column(Float, nullable=True)
    quantity_completed = Column(Float, nullable=True)
    quantity_unit = Column(String(100), nullable=True)
    location_reference = Column(String(500), nullable=True)

    # Matching & routing
    confidence_score = Column(Float, nullable=True)
    match_status = Column(
        Enum(MatchStatusEnum),
        nullable=False,
        default=MatchStatusEnum.pending_match,
        index=True,
    )

    # Source provenance
    source_type = Column(Enum(SourceTypeEnum), nullable=True)
    source_document_id = Column(String(500), nullable=True)

    # Extraction metadata
    extracted_by = Column(String(100), default="time_agent_v1", nullable=False)
    extraction_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Human review
    reviewed_by_planner = Column(Boolean, default=False, nullable=False)
    planner_notes = Column(Text, nullable=True)

    # Full audit trail — original text, prompts, alternatives
    audit_trail = Column(JSONB, nullable=True)

    # ChromaDB embedding ID (set after indexing)
    embedding_id = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    document = relationship("Document", back_populates="progress_events")
    plan_activity = relationship("PlanActivity", back_populates="progress_events")
    matches = relationship("Match", back_populates="progress_event")
    review_decision = relationship(
        "ReviewDecision", back_populates="progress_event", uselist=False
    )


class Match(Base):
    """
    Every candidate activity considered during matching — not just the winner.
    Preserves the full decision history for the audit trail.
    """

    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True), ForeignKey("progress_events.id"), nullable=False, index=True
    )
    candidate_activity_id = Column(String(100), nullable=False)
    plan_activity_id = Column(
        UUID(as_uuid=True), ForeignKey("plan_activities.id"), nullable=True
    )

    # Individual scorer outputs
    fuzzy_score = Column(Float, nullable=True)
    semantic_score = Column(Float, nullable=True)
    llm_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    # Rank among candidates (1 = best)
    rank = Column(Integer, nullable=True)
    was_selected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progress_event = relationship("ProgressEvent", back_populates="matches")
    plan_activity = relationship("PlanActivity", back_populates="matches")


class ReviewDecision(Base):
    """
    Append-only human review decision. Never overwrite — add a new row if the
    planner changes their mind after the fact. The latest row wins.
    """

    __tablename__ = "review_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("progress_events.id"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    decision = Column(Enum(ReviewDecisionEnum), nullable=False)

    # Populated for 'edited' decisions
    corrected_activity_id = Column(String(100), nullable=True)
    corrected_fields = Column(JSONB, nullable=True)

    # Populated for 'confirmed_new' decisions
    new_activity_id = Column(String(100), nullable=True)

    notes = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progress_event = relationship("ProgressEvent", back_populates="review_decision")
    reviewer = relationship("User", back_populates="review_decisions")
