"""
Schedule service — business logic for plan activity operations.

Responsibilities:
  - Write-back of validated actuals to plan_activities table
  - Creation of new plan_activities (from confirm_new review action)
  - Building the activity index for the matching engine
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PlanActivity, ProgressEvent
from backend.schemas.schedule import PlanActivityCreate
from backend.services.institutional_memory.chroma_store import index_plan_activity
from backend.services.matching.semantic_matcher import (
    embed_text,
    load_activity_embeddings,
)

log = structlog.get_logger(__name__)


async def get_activity_index(db: AsyncSession) -> dict[str, str]:
    """
    Return {activity_id: activity_name} for all plan activities.
    Used to build the fuzzy/semantic matching index.
    """
    result = await db.execute(select(PlanActivity.activity_id, PlanActivity.activity_name))
    return {row.activity_id: row.activity_name for row in result}


async def reload_matching_index(db: AsyncSession) -> None:
    """
    Reload the in-memory semantic embedding matrix from current plan_activities.
    Call after inserting new activities (XER seed or confirm_new).
    """
    index = await get_activity_index(db)
    load_activity_embeddings(index)
    log.info("schedule_service.index_reloaded", count=len(index))


async def apply_actuals_to_db(
    db: AsyncSession,
    activity_id: str,
    actual_start: datetime | None,
    actual_finish: datetime | None,
    percent_complete: float | None,
) -> None:
    """Update actual_start/finish/pct on a plan_activity row."""
    values: dict = {"updated_at": datetime.now(tz=timezone.utc)}
    if actual_start is not None:
        values["actual_start"] = actual_start
    if actual_finish is not None:
        values["actual_finish"] = actual_finish
    if percent_complete is not None:
        values["actual_percent_complete"] = percent_complete

    await db.execute(
        update(PlanActivity)
        .where(PlanActivity.activity_id == activity_id)
        .values(**values)
    )
    log.info(
        "schedule_service.actuals_written",
        activity_id=activity_id,
        actual_start=str(actual_start),
        actual_finish=str(actual_finish),
    )


async def create_new_plan_activity(
    db: AsyncSession,
    create_data: PlanActivityCreate,
) -> PlanActivity:
    """
    Create a new plan activity from a confirmed-new field event (ADR-007).
    - Inserts into plan_activities
    - Embeds immediately in ChromaDB
    - Reloads the semantic matching index so future messages can match against it

    Args:
        db: Async DB session.
        create_data: PlanActivityCreate schema from the confirm_new request.

    Returns:
        The newly created PlanActivity ORM object.
    """
    # Generate a unique activity_id for field-confirmed activities
    new_id = f"FIELD-{str(uuid.uuid4())[:8].upper()}"

    activity = PlanActivity(
        project_id=create_data.project_id,
        activity_id=new_id,
        activity_name=create_data.activity_name,
        discipline=create_data.discipline,
        wbs_code=create_data.wbs_code,
        planned_start=create_data.planned_start,
        planned_finish=create_data.planned_finish,
        original_duration_days=create_data.original_duration_days,
        is_field_confirmed=True,
    )

    db.add(activity)
    await db.flush()  # Get the generated id before commit

    # Embed immediately in ChromaDB
    try:
        embedding_id = index_plan_activity(
            activity_id=new_id,
            activity_name=create_data.activity_name,
            discipline=create_data.discipline,
            project_id=create_data.project_id,
        )
        activity.embedding_id = embedding_id
    except Exception as exc:
        log.warning("schedule_service.embedding_failed", error=str(exc), activity_id=new_id)

    await db.commit()

    # Reload matching index so new activity is immediately matchable
    await reload_matching_index(db)

    log.info(
        "schedule_service.new_activity_created",
        activity_id=new_id,
        name=create_data.activity_name,
        discipline=create_data.discipline,
        is_field_confirmed=True,
    )

    return activity
