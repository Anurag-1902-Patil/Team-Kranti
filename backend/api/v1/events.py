"""Events API — list and detail endpoints for progress events."""

import uuid
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.deps import get_current_user, get_db
from backend.db.models import Match, MatchStatusEnum, ProgressEvent
from backend.schemas.event import MatchCandidateSchema, ProgressEventListOut, ProgressEventOut

router = APIRouter()
log = structlog.get_logger(__name__)


@router.get("", response_model=ProgressEventListOut)
async def list_events(
    status_filter: str | None = Query(None, alias="status"),
    discipline: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> ProgressEventListOut:
    """
    List progress events with optional filtering.
    Ordered by extraction_timestamp descending (newest first).
    """
    query = select(ProgressEvent)

    if status_filter:
        try:
            status_enum = MatchStatusEnum(status_filter)
            query = query.where(ProgressEvent.match_status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    if discipline:
        query = query.where(ProgressEvent.discipline == discipline)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = (
        query.order_by(ProgressEvent.extraction_timestamp.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    events = result.scalars().all()

    return ProgressEventListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[ProgressEventOut.model_validate(e) for e in events],
    )


@router.get("/{event_id}", response_model=ProgressEventOut)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> ProgressEventOut:
    """
    Get a single event with full audit trail and match candidates.
    """
    result = await db.execute(
        select(ProgressEvent)
        .options(selectinload(ProgressEvent.matches))
        .where(ProgressEvent.id == event_id)
    )
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    out = ProgressEventOut.model_validate(event)

    # Hydrate match candidates
    from backend.db.models import PlanActivity

    candidates = []
    for m in sorted(event.matches, key=lambda x: x.rank or 999):
        name = None
        if m.plan_activity_id:
            pa_result = await db.execute(
                select(PlanActivity.activity_name).where(PlanActivity.id == m.plan_activity_id)
            )
            name = pa_result.scalar_one_or_none()
        candidates.append(
            MatchCandidateSchema(
                candidate_activity_id=m.candidate_activity_id,
                activity_name=name,
                fuzzy_score=m.fuzzy_score,
                semantic_score=m.semantic_score,
                llm_score=m.llm_score,
                final_score=m.final_score,
                rank=m.rank,
                was_selected=m.was_selected,
            )
        )

    out.match_candidates = candidates
    return out
