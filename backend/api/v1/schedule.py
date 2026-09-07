"""Schedule API — activity index, actuals view, XER export, and new activity creation."""

import uuid
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.db.models import PlanActivity, ProgressEvent
from backend.schemas.schedule import (
    PlanActivityCreate,
    PlanActivityListOut,
    PlanActivityOut,
    XERExportOut,
)
from backend.services.scheduling.schedule_service import create_new_plan_activity

router = APIRouter()
log = structlog.get_logger(__name__)


@router.get("/activities", response_model=PlanActivityListOut)
async def list_activities(
    discipline: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> PlanActivityListOut:
    """List plan activities with optional discipline/search filters."""
    query = select(PlanActivity)

    if discipline:
        query = query.where(PlanActivity.discipline == discipline)

    if search:
        query = query.where(PlanActivity.activity_name.ilike(f"%{search}%"))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(PlanActivity.planned_start.asc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    activities = result.scalars().all()

    return PlanActivityListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[PlanActivityOut.model_validate(a) for a in activities],
    )


@router.post("/activities", response_model=PlanActivityOut, status_code=status.HTTP_201_CREATED)
async def create_activity(
    body: PlanActivityCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> PlanActivityOut:
    """
    Create a new plan activity (used by the confirm_new review action — ADR-007).
    The activity is immediately embedded in the matching index.
    """
    new_activity = await create_new_plan_activity(db=db, create_data=body)
    return PlanActivityOut.model_validate(new_activity)


@router.get("/export-xer")
async def export_xer(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Generate an updated XER file with validated actuals applied.
    Returns the file as a download.

    Per ADR-008: validated against synthetic XER only.
    """
    from backend.core.config import get_settings
    from backend.services.scheduling.xer_writer import apply_actuals_to_xer

    settings = get_settings()
    xer_source = Path("data/synthetic/sample_schedule.xer")

    if not xer_source.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source XER file not found. Run seed_schedule.py first.",
        )

    # Gather all validated events with actuals
    result = await db.execute(
        select(
            ProgressEvent.activity_id_plan,
            ProgressEvent.actual_start_datetime,
            ProgressEvent.actual_finish_datetime,
            ProgressEvent.percent_complete,
        ).where(
            ProgressEvent.match_status == "matched",
            ProgressEvent.activity_id_plan.is_not(None),
        )
    )
    events = result.all()

    validated_events = [
        {
            "activity_id": row.activity_id_plan,
            "actual_start": row.actual_start_datetime,
            "actual_finish": row.actual_finish_datetime,
            "percent_complete": row.percent_complete,
        }
        for row in events
    ]

    # Generate updated XER
    output_path = apply_actuals_to_xer(
        input_xer_path=xer_source,
        validated_events=validated_events,
    )

    log.info("schedule.xer_export", events_applied=len(validated_events))

    return FileResponse(
        path=str(output_path),
        filename="sih26122_updated_schedule.xer",
        media_type="application/octet-stream",
    )
