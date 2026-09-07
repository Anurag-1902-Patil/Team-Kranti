"""Initial schema — create all tables for SIH26122.

Revision ID: 001_initial_schema
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    discipline_enum = sa.Enum(
        "piping", "civil", "electrical", "instrumentation", "hse",
        "structural", "mechanical", "unknown",
        name="disciplineenum",
    )
    event_type_enum = sa.Enum("start", "finish", "partial_complete", name="eventtypeenum")
    source_type_enum = sa.Enum(
        "free_text_dpr", "spreadsheet", "scanned_diary", "voice_log",
        "image_annotation", "unknown",
        name="sourcetypeenum",
    )
    match_status_enum = sa.Enum(
        "pending_match", "matched", "low_confidence_review",
        "unmatched_new", "declined", "processing_failed",
        name="matchstatusenum",
    )
    review_decision_enum = sa.Enum(
        "accepted", "edited", "declined", "confirmed_new",
        name="reviewdecisionenum",
    )
    user_role_enum = sa.Enum("reviewer", "planner", "admin", name="userroleenum")

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # sender_profiles
    op.create_table(
        "sender_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sender_id", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200)),
        sa.Column("discipline", sa.String(50)),
        sa.Column("project_id", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sender_profiles_sender_id", "sender_profiles", ["sender_id"])

    # plan_activities
    op.create_table(
        "plan_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.String(200), nullable=False),
        sa.Column("activity_id", sa.String(100), unique=True, nullable=False),
        sa.Column("activity_name", sa.Text, nullable=False),
        sa.Column("wbs_code", sa.String(200)),
        sa.Column("discipline", sa.String(50)),
        sa.Column("planned_start", sa.DateTime(timezone=True)),
        sa.Column("planned_finish", sa.DateTime(timezone=True)),
        sa.Column("original_duration_days", sa.Float),
        sa.Column("percent_complete_plan", sa.Float, default=0.0),
        sa.Column("actual_start", sa.DateTime(timezone=True)),
        sa.Column("actual_finish", sa.DateTime(timezone=True)),
        sa.Column("actual_percent_complete", sa.Float),
        sa.Column("embedding_id", sa.String(200)),
        sa.Column("is_field_confirmed", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_plan_activities_activity_id", "plan_activities", ["activity_id"])
    op.create_index("ix_plan_activities_project_id", "plan_activities", ["project_id"])
    op.create_index("ix_plan_activities_discipline", "plan_activities", ["discipline"])

    # documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", sa.String(200), unique=True, nullable=False),
        sa.Column("sender_id", sa.String(50), nullable=False),
        sa.Column("source_type", source_type_enum, default="unknown"),
        sa.Column("raw_text", sa.Text),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("s3_key", sa.String(500)),
        sa.Column("extracted_text_s3_key", sa.String(500)),
        sa.Column("processing_status", sa.String(50), default="queued", nullable=False),
        sa.Column("processing_error", sa.Text),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_message_id", "documents", ["message_id"])
    op.create_index("ix_documents_sender_id", "documents", ["sender_id"])
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"])

    # progress_events
    op.create_table(
        "progress_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.String(200), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id")),
        sa.Column("activity_id_plan", sa.String(100)),
        sa.Column("plan_activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plan_activities.id")),
        sa.Column("activity_name_plan", sa.Text),
        sa.Column("activity_description_extracted", sa.Text),
        sa.Column("discipline", discipline_enum, nullable=False),
        sa.Column("event_type", event_type_enum),
        sa.Column("actual_start_datetime", sa.DateTime(timezone=True)),
        sa.Column("actual_finish_datetime", sa.DateTime(timezone=True)),
        sa.Column("percent_complete", sa.Float),
        sa.Column("quantity_completed", sa.Float),
        sa.Column("quantity_unit", sa.String(100)),
        sa.Column("location_reference", sa.String(500)),
        sa.Column("confidence_score", sa.Float),
        sa.Column("match_status", match_status_enum, nullable=False, default="pending_match"),
        sa.Column("source_type", source_type_enum),
        sa.Column("source_document_id", sa.String(500)),
        sa.Column("extracted_by", sa.String(100), default="time_agent_v1"),
        sa.Column("extraction_timestamp", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by_planner", sa.Boolean, default=False),
        sa.Column("planner_notes", sa.Text),
        sa.Column("audit_trail", postgresql.JSONB),
        sa.Column("embedding_id", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pe_activity_id_plan", "progress_events", ["activity_id_plan"])
    op.create_index("ix_pe_match_status", "progress_events", ["match_status"])
    op.create_index("ix_pe_project_id", "progress_events", ["project_id"])
    op.create_index("ix_pe_discipline", "progress_events", ["discipline"])
    op.create_index("ix_pe_extraction_timestamp", "progress_events", ["extraction_timestamp"])
    op.create_index("ix_pe_plan_activity_id", "progress_events", ["plan_activity_id"])

    # matches
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("progress_events.id"), nullable=False),
        sa.Column("candidate_activity_id", sa.String(100), nullable=False),
        sa.Column("plan_activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plan_activities.id")),
        sa.Column("fuzzy_score", sa.Float),
        sa.Column("semantic_score", sa.Float),
        sa.Column("llm_score", sa.Float),
        sa.Column("final_score", sa.Float),
        sa.Column("rank", sa.Integer),
        sa.Column("was_selected", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_matches_event_id", "matches", ["event_id"])

    # review_decisions
    op.create_table(
        "review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("progress_events.id"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("decision", review_decision_enum, nullable=False),
        sa.Column("corrected_activity_id", sa.String(100)),
        sa.Column("corrected_fields", postgresql.JSONB),
        sa.Column("new_activity_id", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_review_decisions_event_id", "review_decisions", ["event_id"])


def downgrade() -> None:
    op.drop_table("review_decisions")
    op.drop_table("matches")
    op.drop_table("progress_events")
    op.drop_table("documents")
    op.drop_table("plan_activities")
    op.drop_table("sender_profiles")
    op.drop_table("users")

    for enum_name in [
        "disciplineenum", "eventtypeenum", "sourcetypeenum",
        "matchstatusenum", "reviewdecisionenum", "userroleenum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
