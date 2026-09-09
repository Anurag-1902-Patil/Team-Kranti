"""Intelligence layer schema expansion — disciplines, entities, aliases, dependencies, ontology attributes.

Revision ID: 002_intelligence_layer
Revises: 001_initial_schema
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_intelligence_layer"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. disciplines lookup table
    op.create_table(
        "disciplines",
        sa.Column("code", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), default=0, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("org_type", sa.String(50), default="contractor", nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_organizations_code", "organizations", ["code"])

    # 3. contractors
    op.create_table(
        "contractors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("trade_specialty", sa.String(100), nullable=True),
        sa.Column("contact_person", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contractors_name", "contractors", ["name"])

    # 4. people
    op.create_table(
        "people",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("contractor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contractors.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_people_name", "people", ["name"])
    op.create_index("ix_people_phone", "people", ["phone"])

    # 5. equipment
    op.create_table(
        "equipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tag", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("equipment_type", sa.String(100), nullable=True),
        sa.Column("system_code", sa.String(100), nullable=True),
        sa.Column("area", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), default="planned", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_equipment_tag", "equipment", ["tag"])

    # 6. materials
    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("material_code", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("uom", sa.String(50), nullable=True),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_materials_material_code", "materials", ["material_code"])

    # 7. locations
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("area", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(100), nullable=True),
        sa.Column("chainage_start", sa.String(50), nullable=True),
        sa.Column("chainage_end", sa.String(50), nullable=True),
        sa.Column("grid_reference", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_locations_code", "locations", ["code"])

    # 8. activity_dependencies
    op.create_table(
        "activity_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("predecessor_activity_id", sa.String(100), nullable=False),
        sa.Column("successor_activity_id", sa.String(100), nullable=False),
        sa.Column("dependency_type", sa.String(10), default="FS", nullable=False),
        sa.Column("lag_days", sa.Float(), default=0.0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activity_dependencies_pred", "activity_dependencies", ["predecessor_activity_id"])
    op.create_index("ix_activity_dependencies_succ", "activity_dependencies", ["successor_activity_id"])

    # 9. entity_aliases
    op.create_table(
        "entity_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("raw_alias", sa.String(200), nullable=False),
        sa.Column("canonical_value", sa.String(200), nullable=False),
        sa.Column("confidence", sa.Float(), default=1.0, nullable=False),
        sa.Column("status", sa.String(20), default="proposed", nullable=False),
        sa.Column("proposed_by", sa.String(100), default="ai", nullable=False),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_entity_aliases_entity_type", "entity_aliases", ["entity_type"])
    op.create_index("ix_entity_aliases_raw_alias", "entity_aliases", ["raw_alias"])
    op.create_index("ix_entity_aliases_status", "entity_aliases", ["status"])

    # 10. extracted_entities
    op.create_table(
        "extracted_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("progress_events.id"), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("raw_text", sa.String(500), nullable=False),
        sa.Column("normalized_value", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), default=0.8, nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("extraction_method", sa.String(50), default="llm_v2", nullable=False),
        sa.Column("model_version", sa.String(100), default="nemotron-3-super-120b-a12b", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extracted_entities_event_id", "extracted_entities", ["event_id"])
    op.create_index("ix_extracted_entities_document_id", "extracted_entities", ["document_id"])
    op.create_index("ix_extracted_entities_type", "extracted_entities", ["entity_type"])

    # 11. Add columns to plan_activities
    op.add_column("plan_activities", sa.Column("wbs_name", sa.String(200), nullable=True))
    op.add_column("plan_activities", sa.Column("contractor_name", sa.String(200), nullable=True))
    op.add_column("plan_activities", sa.Column("area", sa.String(100), nullable=True))
    op.add_column("plan_activities", sa.Column("unit", sa.String(100), nullable=True))
    op.add_column("plan_activities", sa.Column("total_float_days", sa.Float(), default=0.0, nullable=False, server_default="0.0"))
    op.add_column("plan_activities", sa.Column("is_critical", sa.Boolean(), default=False, nullable=False, server_default="false"))
    op.add_column("plan_activities", sa.Column("delay_risk_score", sa.Float(), default=0.0, nullable=False, server_default="0.0"))

    # 12. Add columns to progress_events
    op.add_column("progress_events", sa.Column("activity_description_raw", sa.Text(), nullable=True))
    op.add_column("progress_events", sa.Column("activity_description_normalized", sa.Text(), nullable=True))
    op.add_column("progress_events", sa.Column("sub_discipline", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("activity_type", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("work_package", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("wbs_code", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("construction_phase", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("execution_stage", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("planned_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("progress_events", sa.Column("planned_finish", sa.DateTime(timezone=True), nullable=True))
    op.add_column("progress_events", sa.Column("planned_duration_days", sa.Float(), nullable=True))
    op.add_column("progress_events", sa.Column("actual_duration_days", sa.Float(), nullable=True))
    op.add_column("progress_events", sa.Column("remaining_duration_days", sa.Float(), nullable=True))
    op.add_column("progress_events", sa.Column("location_area", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("location_unit", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("equipment_tag", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("line_number", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("tag_number", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("drawing_reference", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("material_reference", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("contractor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contractors.id"), nullable=True))
    op.add_column("progress_events", sa.Column("contractor_name", sa.String(200), nullable=True))
    op.add_column("progress_events", sa.Column("supervisor_name", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("engineer_name", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("crew_name", sa.String(100), nullable=True))
    op.add_column("progress_events", sa.Column("status", sa.String(50), default="in_progress", nullable=True, server_default="in_progress"))
    op.add_column("progress_events", sa.Column("delay_status", sa.String(50), nullable=True))
    op.add_column("progress_events", sa.Column("delay_category", sa.String(50), nullable=True))
    op.add_column("progress_events", sa.Column("delay_reason", sa.Text(), nullable=True))
    op.add_column("progress_events", sa.Column("blocker_description", sa.Text(), nullable=True))
    op.add_column("progress_events", sa.Column("priority", sa.String(50), default="medium", nullable=True, server_default="medium"))
    op.add_column("progress_events", sa.Column("is_critical_path", sa.Boolean(), default=False, nullable=False, server_default="false"))
    op.add_column("progress_events", sa.Column("total_float_days", sa.Float(), default=0.0, nullable=False, server_default="0.0"))
    op.add_column("progress_events", sa.Column("confidence_tier", sa.String(20), default="medium", nullable=False, server_default="medium"))
    op.add_column("progress_events", sa.Column("provenance_category", sa.String(50), default="ai_extraction", nullable=False, server_default="ai_extraction"))
    op.add_column("progress_events", sa.Column("ontology_payload", postgresql.JSONB, nullable=True))
    op.add_column("progress_events", sa.Column("correction_history", postgresql.JSONB, nullable=True))

    # Convert discipline column to varchar(50) if necessary
    try:
        op.alter_column(
            "progress_events",
            "discipline",
            type_=sa.String(50),
            existing_type=sa.Enum("piping", "civil", "electrical", "instrumentation", "hse", "structural", "mechanical", "unknown", name="disciplineenum"),
            postgresql_using="discipline::text",
        )
    except Exception:
        pass


def downgrade() -> None:
    op.drop_table("extracted_entities")
    op.drop_table("entity_aliases")
    op.drop_table("activity_dependencies")
    op.drop_table("locations")
    op.drop_table("materials")
    op.drop_table("equipment")
    op.drop_table("people")
    op.drop_table("contractors")
    op.drop_table("organizations")
    op.drop_table("disciplines")
