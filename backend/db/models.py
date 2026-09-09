"""
SQLAlchemy ORM models for SIH26122 — Intelligence Layer & Project Controls.

Tables:
  - users                 (reviewer/planner/admin identity)
  - sender_profiles       (WhatsApp sender → discipline mapping)
  - disciplines           (lookup table for extensible ontology disciplines)
  - organizations         (clients, EPC contractors, vendors)
  - contractors           (field contractors, specialties, POCs)
  - people                (supervisors, engineers, managers)
  - equipment             (tagged equipment, status, area)
  - materials             (catalog items, specs, UOM)
  - locations             (areas, units, chainages, grid refs)
  - activity_dependencies (P6 predecessor/successor network)
  - entity_aliases        (controlled vocabulary & human-gated terminology proposals)
  - plan_activities       (Primavera P6 schedule activities & WBS index)
  - documents             (raw ingested messages/files)
  - progress_events       (normalized §3.4 progress events + full ontology + audit)
  - extracted_entities    (granular linked entities with confidence & evidence)
  - matches               (candidates considered during matching)
  - review_decisions      (append-only planner decisions — never overwritten)
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
    JSON,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DisciplineEnum(str, PyEnum):
    civil = "civil"
    structural = "structural"
    piping = "piping"
    mechanical = "mechanical"
    static_equipment = "static_equipment"
    rotating_equipment = "rotating_equipment"
    electrical = "electrical"
    instrumentation = "instrumentation"
    telecom = "telecom"
    hvac = "hvac"
    fire_and_safety = "fire_and_safety"
    hse = "hse"
    qa_qc = "qa_qc"
    procurement = "procurement"
    engineering = "engineering"
    planning = "planning"
    commissioning = "commissioning"
    construction = "construction"
    logistics = "logistics"
    material_management = "material_management"
    administration = "administration"
    unknown = "unknown"


class DisciplineValue(str):
    """String subclass with .value property for backward compatibility."""

    @property
    def value(self) -> str:
        return str(self)


class DisciplineType(TypeDecorator):
    """Stores discipline as VARCHAR(50) in DB, wraps in DisciplineValue in Python."""

    impl = String(50)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is None:
            return DisciplineValue("unknown")
        return DisciplineValue(value)

    def process_bind_param(self, value, dialect):
        if value is None:
            return "unknown"
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)


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


class ProvenanceCategoryEnum(str, PyEnum):
    source_fact = "source_fact"
    ai_extraction = "ai_extraction"
    ai_inference = "ai_inference"
    prediction = "prediction"
    human_approval = "human_approval"


class ConfidenceTierEnum(str, PyEnum):
    high = "high"
    medium = "medium"
    low = "low"


class AliasStatusEnum(str, PyEnum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"


class DelayCategoryEnum(str, PyEnum):
    material = "material"
    manpower = "manpower"
    equipment = "equipment"
    design = "design"
    approval = "approval"
    weather = "weather"
    access = "access"
    safety = "safety"
    quality_rework = "quality_rework"
    dependency = "dependency"
    contractor = "contractor"
    logistics = "logistics"
    unknown = "unknown"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    """Reviewer and planner identity."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.reviewer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review_decisions = relationship("ReviewDecision", back_populates="reviewer")


class Discipline(Base):
    """
    Lookup table for disciplines (extensible without schema change).
    Replaces hardcoded enums for future disciplines.
    """

    __tablename__ = "disciplines"

    code = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)  # Engineering, Construction, Management, HSE
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Organization(Base):
    """Clients, contractors, subcontractors, and vendors."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    org_type = Column(String(50), nullable=False, default="contractor")  # client, contractor, vendor
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contractors = relationship("Contractor", back_populates="organization")


class Contractor(Base):
    """Construction and engineering contractors."""

    __tablename__ = "contractors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    trade_specialty = Column(String(100), nullable=True)
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="contractors")
    people = relationship("Person", back_populates="contractor")


class Person(Base):
    """Supervisors, engineers, inspectors, and crew leads."""

    __tablename__ = "people"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    role = Column(String(100), nullable=True)  # site_engineer, supervisor, inspector, pm
    phone = Column(String(50), nullable=True, index=True)
    email = Column(String(100), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contractor = relationship("Contractor", back_populates="people")


class Equipment(Base):
    """Major site equipment and tagged packages."""

    __tablename__ = "equipment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    equipment_type = Column(String(100), nullable=True)  # pump, vessel, crane, compressor
    system_code = Column(String(100), nullable=True)
    area = Column(String(100), nullable=True)
    status = Column(String(50), default="planned")  # planned, on_site, installed, tested, commissioned
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Material(Base):
    """Bill of materials, piping spools, bulk items."""

    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True)
    uom = Column(String(50), nullable=True)
    specification = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Location(Base):
    """Physical locations, areas, units, chainages, and grid lines."""

    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    area = Column(String(100), nullable=True)
    unit = Column(String(100), nullable=True)
    chainage_start = Column(String(50), nullable=True)
    chainage_end = Column(String(50), nullable=True)
    grid_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ActivityDependency(Base):
    """Predecessor / successor relationships between schedule activities."""

    __tablename__ = "activity_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    predecessor_activity_id = Column(String(100), nullable=False, index=True)
    successor_activity_id = Column(String(100), nullable=False, index=True)
    dependency_type = Column(String(10), default="FS", nullable=False)  # FS, SS, FF, SF
    lag_days = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EntityAlias(Base):
    """
    Controlled vocabulary & terminology aliases.
    Gated: newly discovered aliases remain 'proposed' until planner approval.
    """

    __tablename__ = "entity_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False, index=True)  # equipment, contractor, discipline, location
    raw_alias = Column(String(200), nullable=False, index=True)
    canonical_value = Column(String(200), nullable=False, index=True)
    confidence = Column(Float, default=1.0, nullable=False)
    status = Column(String(20), default="proposed", nullable=False, index=True)  # proposed, approved, rejected
    proposed_by = Column(String(100), default="ai", nullable=False)
    approved_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SenderProfile(Base):
    """Maps WhatsApp sender_id to a discipline and display name."""

    __tablename__ = "sender_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=True)
    discipline = Column(String(50), nullable=True)
    project_id = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PlanActivity(Base):
    """Activities sourced from Primavera P6 XER export or field-confirmed."""

    __tablename__ = "plan_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(200), nullable=False, index=True)
    activity_id = Column(String(100), unique=True, nullable=False, index=True)
    activity_name = Column(Text, nullable=False)
    wbs_code = Column(String(200), nullable=True)
    wbs_name = Column(String(200), nullable=True)
    discipline = Column(String(50), nullable=True, index=True)
    contractor_name = Column(String(200), nullable=True)
    area = Column(String(100), nullable=True)
    unit = Column(String(100), nullable=True)
    planned_start = Column(DateTime(timezone=True), nullable=True)
    planned_finish = Column(DateTime(timezone=True), nullable=True)
    original_duration_days = Column(Float, nullable=True)
    percent_complete_plan = Column(Float, default=0.0)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_finish = Column(DateTime(timezone=True), nullable=True)
    actual_percent_complete = Column(Float, nullable=True)
    total_float_days = Column(Float, default=0.0, nullable=False)
    is_critical = Column(Boolean, default=False, nullable=False)
    delay_risk_score = Column(Float, default=0.0, nullable=False)
    embedding_id = Column(String(200), nullable=True)
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
    """Raw ingested message or file."""

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
    s3_key = Column(String(500), nullable=True)
    extracted_text_s3_key = Column(String(500), nullable=True)
    processing_status = Column(String(50), default="queued", nullable=False, index=True)
    processing_error = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progress_events = relationship("ProgressEvent", back_populates="document")
    extracted_entities = relationship("ExtractedEntity", back_populates="document")


class ProgressEvent(Base):
    """
    Normalized §3.4 progress event + full ontology fields + provenance audit.
    Supports 5 categories: Source Fact, AI Extraction, AI Inference, Prediction, Human Approval.
    """

    __tablename__ = "progress_events"
    __table_args__ = (
        Index("ix_pe_activity_id_plan", "activity_id_plan"),
        Index("ix_pe_match_status", "match_status"),
        Index("ix_pe_project_id", "project_id"),
        Index("ix_pe_discipline", "discipline"),
        Index("ix_pe_extraction_timestamp", "extraction_timestamp"),
        Index("ix_pe_plan_activity_id", "plan_activity_id"),
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

    # Core Extracted attributes
    activity_description_extracted = Column(Text, nullable=True)
    activity_description_raw = Column(Text, nullable=True)
    activity_description_normalized = Column(Text, nullable=True)
    discipline = Column(DisciplineType, nullable=False, default=DisciplineValue("unknown"))
    sub_discipline = Column(String(100), nullable=True)
    event_type = Column(Enum(EventTypeEnum), nullable=True)
    activity_type = Column(String(100), nullable=True)
    work_package = Column(String(100), nullable=True)
    wbs_code = Column(String(100), nullable=True)
    construction_phase = Column(String(100), nullable=True)
    execution_stage = Column(String(100), nullable=True)

    # Schedule & Quantities
    actual_start_datetime = Column(DateTime(timezone=True), nullable=True)
    actual_finish_datetime = Column(DateTime(timezone=True), nullable=True)
    planned_start = Column(DateTime(timezone=True), nullable=True)
    planned_finish = Column(DateTime(timezone=True), nullable=True)
    planned_duration_days = Column(Float, nullable=True)
    actual_duration_days = Column(Float, nullable=True)
    remaining_duration_days = Column(Float, nullable=True)
    percent_complete = Column(Float, nullable=True)
    quantity_completed = Column(Float, nullable=True)
    quantity_unit = Column(String(100), nullable=True)

    # Location, Tagging & Engineering
    location_reference = Column(String(500), nullable=True)
    location_area = Column(String(100), nullable=True)
    location_unit = Column(String(100), nullable=True)
    equipment_tag = Column(String(100), nullable=True)
    line_number = Column(String(100), nullable=True)
    tag_number = Column(String(100), nullable=True)
    drawing_reference = Column(String(100), nullable=True)
    material_reference = Column(String(100), nullable=True)

    # Responsible Entities
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"), nullable=True)
    contractor_name = Column(String(200), nullable=True)
    supervisor_name = Column(String(100), nullable=True)
    engineer_name = Column(String(100), nullable=True)
    crew_name = Column(String(100), nullable=True)

    # Status, Delays & Blockers
    status = Column(String(50), default="in_progress", nullable=True)
    delay_status = Column(String(50), nullable=True)
    delay_category = Column(String(50), nullable=True)
    delay_reason = Column(Text, nullable=True)
    blocker_description = Column(Text, nullable=True)
    priority = Column(String(50), default="medium", nullable=True)
    is_critical_path = Column(Boolean, default=False, nullable=False)
    total_float_days = Column(Float, default=0.0, nullable=False)

    # Matching & routing
    confidence_score = Column(Float, nullable=True)
    confidence_tier = Column(String(20), default="medium", nullable=False)  # high, medium, low
    match_status = Column(
        Enum(MatchStatusEnum),
        nullable=False,
        default=MatchStatusEnum.pending_match,
        index=True,
    )

    # Provenance separation (Source Fact / AI Extraction / AI Inference / Prediction / Human Approval)
    provenance_category = Column(
        String(50), default="ai_extraction", nullable=False
    )
    source_type = Column(Enum(SourceTypeEnum), nullable=True)
    source_document_id = Column(String(500), nullable=True)

    # Extraction metadata
    extracted_by = Column(String(100), default="time_agent_v2", nullable=False)
    extraction_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Human review & auditable re-editing
    reviewed_by_planner = Column(Boolean, default=False, nullable=False)
    planner_notes = Column(Text, nullable=True)
    audit_trail = Column(JSONType, nullable=True)
    ontology_payload = Column(JSONType, nullable=True)
    correction_history = Column(JSONType, nullable=True)

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
    contractor = relationship("Contractor")
    matches = relationship("Match", back_populates="progress_event")
    review_decision = relationship(
        "ReviewDecision", back_populates="progress_event", uselist=False
    )
    extracted_entities = relationship("ExtractedEntity", back_populates="progress_event")


class ExtractedEntity(Base):
    """
    Granular extracted entities linked to an event/document.
    Each field carries value, confidence, evidence, extraction_method, model_version.
    """

    __tablename__ = "extracted_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("progress_events.id"), nullable=True, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # equipment_tag, line_number, contractor, person, location, quantity, blocker
    raw_text = Column(String(500), nullable=False)
    normalized_value = Column(String(500), nullable=True)
    confidence = Column(Float, default=0.8, nullable=False)
    evidence = Column(Text, nullable=True)
    extraction_method = Column(String(50), default="llm_v2", nullable=False)
    model_version = Column(String(100), default="nemotron-3-super-120b-a12b", nullable=False)
    metadata_json = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progress_event = relationship("ProgressEvent", back_populates="extracted_entities")
    document = relationship("Document", back_populates="extracted_entities")


class Match(Base):
    """All candidate activities considered during matching."""

    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True), ForeignKey("progress_events.id"), nullable=False, index=True
    )
    candidate_activity_id = Column(String(100), nullable=False)
    plan_activity_id = Column(
        UUID(as_uuid=True), ForeignKey("plan_activities.id"), nullable=True
    )

    fuzzy_score = Column(Float, nullable=True)
    semantic_score = Column(Float, nullable=True)
    llm_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    was_selected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progress_event = relationship("ProgressEvent", back_populates="matches")
    plan_activity = relationship("PlanActivity", back_populates="matches")


class ReviewDecision(Base):
    """Append-only human review decisions."""

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
    corrected_activity_id = Column(String(100), nullable=True)
    corrected_fields = Column(JSONType, nullable=True)
    new_activity_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    progress_event = relationship("ProgressEvent", back_populates="review_decision")
    reviewer = relationship("User", back_populates="review_decisions")
