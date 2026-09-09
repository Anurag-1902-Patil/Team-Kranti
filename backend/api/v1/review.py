"""
Review API — human-in-the-loop decision endpoints.

Actions:
  POST /review/{event_id}/accept         — accept the matched activity
  POST /review/{event_id}/edit           — correct to a different activity
  POST /review/{event_id}/decline        — decline (mark as not valid)
  POST /review/{event_id}/confirm_new    — confirm as a genuinely new field activity
  GET  /review/queue                     — events awaiting human review

All decisions are append-only — no existing decision is overwritten.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.db.models import (
    MatchStatusEnum,
    PlanActivity,
    ProgressEvent,
    ReviewDecision,
    ReviewDecisionEnum,
)
from backend.schemas.event import ProgressEventListOut, ProgressEventOut
from backend.schemas.review import (
    ReviewAcceptRequest,
    ReviewConfirmNewRequest,
    ReviewDecisionOut,
    ReviewDeclineRequest,
    ReviewEditRequest,
)
from backend.schemas.schedule import PlanActivityCreate
from backend.services.institutional_memory.qdrant_store import index_progress_event
from backend.services.scheduling.schedule_service import (
    apply_actuals_to_db,
    create_new_plan_activity,
)

router = APIRouter()
log = structlog.get_logger(__name__)


async def _get_event_or_404(event_id: uuid.UUID, db: AsyncSession) -> ProgressEvent:
    result = await db.execute(
        select(ProgressEvent).where(ProgressEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return event


@router.get("/queue", response_model=ProgressEventListOut)
async def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> ProgressEventListOut:
    """
    Events awaiting planner review, ordered by confidence ascending
    (lowest confidence first — these need the most attention).
    """
    from sqlalchemy import func

    review_statuses = [
        MatchStatusEnum.low_confidence_review,
        MatchStatusEnum.unmatched_new,
    ]

    query = select(ProgressEvent).where(
        ProgressEvent.match_status.in_(review_statuses),
        ProgressEvent.reviewed_by_planner == False,  # noqa: E712
    )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(ProgressEvent.confidence_score.asc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    events = result.scalars().all()

    return ProgressEventListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[ProgressEventOut.model_validate(e) for e in events],
    )


@router.post("/{event_id}/accept", response_model=ReviewDecisionOut)
async def accept_event(
    event_id: uuid.UUID,
    body: ReviewAcceptRequest,
    db: AsyncSession = Depends(get_db),
    reviewer_token: str = Depends(get_current_user),
) -> ReviewDecisionOut:
    """Accept the matched activity — triggers schedule write-back."""
    event = await _get_event_or_404(event_id, db)

    decision = ReviewDecision(
        event_id=event.id,
        decision=ReviewDecisionEnum.accepted,
        notes=body.notes,
    )
    db.add(decision)

    # Update event
    await db.execute(
        update(ProgressEvent)
        .where(ProgressEvent.id == event_id)
        .values(
            reviewed_by_planner=True,
            planner_notes=body.notes,
            match_status=MatchStatusEnum.matched,
        )
    )

    # Schedule write-back
    if event.activity_id_plan and event.actual_start_datetime:
        await apply_actuals_to_db(
            db,
            activity_id=event.activity_id_plan,
            actual_start=event.actual_start_datetime,
            actual_finish=event.actual_finish_datetime,
            percent_complete=event.percent_complete,
        )

    # Index to ChromaDB
    try:
        index_progress_event(
            event_id=str(event.id),
            activity_description=event.activity_description_extracted or "",
            activity_name_plan=event.activity_name_plan,
            discipline=event.discipline.value if event.discipline else "unknown",
            project_id=event.project_id,
            confidence_score=event.confidence_score,
            actual_start=str(event.actual_start_datetime) if event.actual_start_datetime else None,
            actual_finish=str(event.actual_finish_datetime) if event.actual_finish_datetime else None,
        )
    except Exception as exc:
        log.warning("review.chroma_index_failed", event_id=str(event_id), error=str(exc))

    await db.commit()

    log.info("review.accepted", event_id=str(event_id), reviewer="token_auth")
    return ReviewDecisionOut.model_validate(decision)


@router.post("/{event_id}/edit", response_model=ReviewDecisionOut)
async def edit_event(
    event_id: uuid.UUID,
    body: ReviewEditRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> ReviewDecisionOut:
    """Correct the matched activity to a different plan activity."""
    event = await _get_event_or_404(event_id, db)

    # Verify corrected activity exists
    pa_result = await db.execute(
        select(PlanActivity).where(
            PlanActivity.activity_id == body.corrected_activity_id
        )
    )
    corrected_pa = pa_result.scalar_one_or_none()
    if corrected_pa is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Activity '{body.corrected_activity_id}' not found in plan.",
        )

    decision = ReviewDecision(
        event_id=event.id,
        decision=ReviewDecisionEnum.edited,
        corrected_activity_id=body.corrected_activity_id,
        corrected_fields=body.corrected_fields,
        notes=body.notes,
    )
    db.add(decision)

    # Update event with corrected match
    update_vals = {
        "reviewed_by_planner": True,
        "planner_notes": body.notes,
        "match_status": MatchStatusEnum.matched,
        "activity_id_plan": body.corrected_activity_id,
        "plan_activity_id": corrected_pa.id,
        "activity_name_plan": corrected_pa.activity_name,
    }
    if body.corrected_fields:
        for field, value in body.corrected_fields.items():
            if hasattr(ProgressEvent, field):
                update_vals[field] = value

    await db.execute(
        update(ProgressEvent).where(ProgressEvent.id == event_id).values(**update_vals)
    )

    # Schedule write-back with corrected activity
    if event.actual_start_datetime:
        await apply_actuals_to_db(
            db,
            activity_id=body.corrected_activity_id,
            actual_start=event.actual_start_datetime,
            actual_finish=event.actual_finish_datetime,
            percent_complete=event.percent_complete,
        )

    await db.commit()

    log.info(
        "review.edited",
        event_id=str(event_id),
        corrected_to=body.corrected_activity_id,
    )
    return ReviewDecisionOut.model_validate(decision)


@router.post("/{event_id}/decline", response_model=ReviewDecisionOut)
async def decline_event(
    event_id: uuid.UUID,
    body: ReviewDeclineRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> ReviewDecisionOut:
    """Decline — mark event as not valid. Event is never deleted."""
    event = await _get_event_or_404(event_id, db)

    decision = ReviewDecision(
        event_id=event.id,
        decision=ReviewDecisionEnum.declined,
        notes=body.notes,
    )
    db.add(decision)

    await db.execute(
        update(ProgressEvent)
        .where(ProgressEvent.id == event_id)
        .values(
            reviewed_by_planner=True,
            planner_notes=body.notes,
            match_status=MatchStatusEnum.declined,
        )
    )

    await db.commit()

    log.info("review.declined", event_id=str(event_id))
    return ReviewDecisionOut.model_validate(decision)


@router.post("/{event_id}/confirm_new", response_model=ReviewDecisionOut)
async def confirm_new_activity(
    event_id: uuid.UUID,
    body: ReviewConfirmNewRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> ReviewDecisionOut:
    """
    Confirm that this event represents a genuinely new field activity not in the plan.

    Per ADR-007: creates a new plan_activity, embeds it immediately in the matching
    index so future messages can match against it (the "learning system" narrative).
    """
    event = await _get_event_or_404(event_id, db)

    # Create new plan activity
    new_activity = await create_new_plan_activity(
        db=db,
        create_data=PlanActivityCreate(
            project_id=event.project_id,
            activity_name=body.activity_name,
            discipline=body.discipline,
            planned_start=body.planned_start,
            planned_finish=body.planned_finish,
        ),
    )

    decision = ReviewDecision(
        event_id=event.id,
        decision=ReviewDecisionEnum.confirmed_new,
        new_activity_id=new_activity.activity_id,
        notes=body.notes,
    )
    db.add(decision)

    # Update the event to point to the new activity
    await db.execute(
        update(ProgressEvent)
        .where(ProgressEvent.id == event_id)
        .values(
            reviewed_by_planner=True,
            planner_notes=body.notes,
            match_status=MatchStatusEnum.matched,
            activity_id_plan=new_activity.activity_id,
            plan_activity_id=new_activity.id,
            activity_name_plan=new_activity.activity_name,
            confidence_score=1.0,  # Human-confirmed = full confidence
            provenance_category="human_approval",
        )
    )

    # Index the event to ChromaDB
    try:
        index_progress_event(
            event_id=str(event.id),
            activity_description=event.activity_description_extracted or "",
            activity_name_plan=new_activity.activity_name,
            discipline=body.discipline,
            project_id=event.project_id,
            confidence_score=1.0,
            actual_start=str(event.actual_start_datetime) if event.actual_start_datetime else None,
            actual_finish=str(event.actual_finish_datetime) if event.actual_finish_datetime else None,
        )
    except Exception as exc:
        log.warning("review.confirm_new_chroma_failed", error=str(exc))

    await db.commit()

    log.info(
        "review.confirmed_new",
        event_id=str(event_id),
        new_activity_id=new_activity.activity_id,
        activity_name=body.activity_name,
    )

    return ReviewDecisionOut.model_validate(decision)


class AliasDecisionRequest(BaseModel):
    decision: str  # approved or rejected
    notes: str | None = None


@router.post("/alias/{alias_id}/decide")
async def decide_alias(
    alias_id: uuid.UUID,
    body: AliasDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Human planner decision on AI-proposed terminology alias."""
    from backend.db.models import EntityAlias

    result = await db.execute(select(EntityAlias).where(EntityAlias.id == alias_id))
    alias = result.scalar_one_or_none()
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")

    alias.status = "approved" if body.decision.lower() == "approved" else "rejected"
    alias.approved_by = getattr(current_user, "username", "planner")
    alias.reviewed_at = datetime.now(tz=timezone.utc)
    await db.commit()

    log.info("review.alias_decided", alias_id=str(alias_id), status=alias.status)
    return {"status": "ok", "alias_id": str(alias_id), "decision": alias.status}


class ReEditRequest(BaseModel):
    actual_start: datetime | None = None
    actual_finish: datetime | None = None
    percent_complete: float | None = None
    activity_id_plan: str | None = None
    notes: str | None = None


@router.post("/{event_id}/re-edit", response_model=ProgressEventOut)
async def re_edit_event(
    event_id: uuid.UUID,
    body: ReEditRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> ProgressEventOut:
    """
    Post-approval / post-auto-accept re-edit by planner.
    Original AI value is retained in correction_history; actuals are updated.
    """
    event = await _get_event_or_404(event_id, db)

    history_entry = {
        "edited_at": datetime.now(tz=timezone.utc).isoformat(),
        "edited_by": getattr(current_user, "username", "planner"),
        "previous_values": {
            "actual_start": event.actual_start_datetime.isoformat() if event.actual_start_datetime else None,
            "actual_finish": event.actual_finish_datetime.isoformat() if event.actual_finish_datetime else None,
            "percent_complete": event.percent_complete,
            "activity_id_plan": event.activity_id_plan,
        },
        "notes": body.notes,
    }

    current_history = event.correction_history or []
    current_history.append(history_entry)

    if body.actual_start is not None:
        event.actual_start_datetime = body.actual_start
    if body.actual_finish is not None:
        event.actual_finish_datetime = body.actual_finish
    if body.percent_complete is not None:
        event.percent_complete = body.percent_complete
    if body.activity_id_plan is not None:
        event.activity_id_plan = body.activity_id_plan

    event.correction_history = current_history
    event.provenance_category = "human_approval"
    event.reviewed_by_planner = True
    event.planner_notes = body.notes or event.planner_notes

    # Update linked plan activity actuals if available
    if event.plan_activity_id:
        update_vals = {}
        if body.actual_start is not None:
            update_vals["actual_start"] = body.actual_start
        if body.actual_finish is not None:
            update_vals["actual_finish"] = body.actual_finish
        if body.percent_complete is not None:
            update_vals["actual_percent_complete"] = body.percent_complete

        if update_vals:
            await db.execute(
                update(PlanActivity)
                .where(PlanActivity.id == event.plan_activity_id)
                .values(**update_vals)
            )

    await db.commit()
    await db.refresh(event)
    return ProgressEventOut.model_validate(event)
