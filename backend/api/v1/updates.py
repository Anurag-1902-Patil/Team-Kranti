"""
Update Center Feed API endpoint.
Part C #2: Aggregates 'things needing attention' across review queue, data quality flags,
schedule changes, document processing, and terminology proposals.
Each item carries a stable ID and target_route linking directly to the originating page
so the frontend links into Review Queue / Schedule without double-counting.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Literal
import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.db.models import (
    Document,
    EntityAlias,
    MatchStatusEnum,
    PlanActivity,
    ProgressEvent,
)

router = APIRouter()
log = structlog.get_logger(__name__)


class UpdateFeedItem(BaseModel):
    id: str = Field(..., description="Stable unique ID (e.g. rev_<uuid>, dq_<uuid>)")
    source_type: Literal["review_queue", "data_quality", "schedule_change", "document", "entity_alias"]
    severity: Literal["critical", "warning", "info"]
    title: str
    detected_change: str
    affected_activity_id: str | None = None
    affected_activity_name: str | None = None
    current_value: Any | None = None
    proposed_value: Any | None = None
    confidence: float | None = None
    timestamp: datetime
    source_info: str | None = None
    action_label: str
    target_route: str


class UpdateCenterSummary(BaseModel):
    total_items: int
    pending_reviews: int
    data_quality_flags: int
    schedule_changes: int
    pending_documents: int
    pending_aliases: int


class UpdateCenterFeedResponse(BaseModel):
    summary: UpdateCenterSummary
    items: list[UpdateFeedItem]


@router.get("/feed", response_model=UpdateCenterFeedResponse)
async def get_update_center_feed(
    source_type: str | None = Query(None, description="Filter by source_type"),
    severity: str | None = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> UpdateCenterFeedResponse:
    """
    Returns aggregated items requiring attention across the system.
    Strictly prevents double-counting by routing directly to originating workflows.
    """
    items: list[UpdateFeedItem] = []

    # 1. Review queue items (unreviewed events with low confidence or unmatched)
    rev_query = (
        select(ProgressEvent)
        .where(
            ProgressEvent.match_status.in_([
                MatchStatusEnum.low_confidence_review,
                MatchStatusEnum.unmatched_new,
            ]),
            ProgressEvent.reviewed_by_planner == False,  # noqa: E712
        )
        .order_by(ProgressEvent.extraction_timestamp.desc().nullslast())
        .limit(100)
    )
    rev_res = await db.execute(rev_query)
    rev_events = rev_res.scalars().all()
    pending_reviews_count = len(rev_events)

    for ev in rev_events:
        conf = ev.confidence_score or 0.0
        is_crit = ev.is_critical_path or conf < 0.55
        sev: Literal["critical", "warning", "info"] = "critical" if is_crit else "warning"
        items.append(
            UpdateFeedItem(
                id=f"rev_{ev.id}",
                source_type="review_queue",
                severity=sev,
                title=f"AI Match Review: {ev.activity_description_extracted or 'Field Update'}",
                detected_change=f"Extracted {ev.discipline.value if hasattr(ev.discipline, 'value') else ev.discipline} event matched with {int(conf * 100)}% confidence",
                affected_activity_id=ev.activity_id_plan,
                affected_activity_name=ev.activity_name_plan,
                current_value=None,
                proposed_value=ev.activity_name_plan or ev.activity_description_extracted,
                confidence=ev.confidence_score,
                timestamp=ev.extraction_timestamp or ev.created_at,
                source_info=f"{ev.source_type.value if hasattr(ev.source_type, 'value') else ev.source_type} (Doc #{str(ev.document_id)[:8] if ev.document_id else 'Direct'})",
                action_label="Review & Triage",
                target_route=f"/review?highlight={ev.id}",
            )
        )

    # 2. Data Quality Flags
    # A) Activities with 100% progress but no actual finish date
    dq_finish_query = select(PlanActivity).where(
        PlanActivity.actual_percent_complete >= 100.0,
        PlanActivity.actual_finish.is_(None),
    ).limit(30)
    dq_finish_res = await db.execute(dq_finish_query)
    dq_finish_acts = dq_finish_res.scalars().all()

    for act in dq_finish_acts:
        items.append(
            UpdateFeedItem(
                id=f"dq_fin_{act.id}",
                source_type="data_quality",
                severity="warning",
                title=f"Missing Actual Finish: {act.activity_id}",
                detected_change=f"Activity marked 100% complete but has no actual finish date recorded in schedule.",
                affected_activity_id=act.activity_id,
                affected_activity_name=act.activity_name,
                current_value="100% Complete",
                proposed_value="Set Actual Finish Date",
                confidence=1.0,
                timestamp=act.updated_at or act.created_at,
                source_info="Schedule Quality Gate",
                action_label="Update in Gantt",
                target_route=f"/schedule?highlight={act.activity_id}",
            )
        )

    # B) Negative float activities (Schedule delay risk)
    dq_float_query = select(PlanActivity).where(
        PlanActivity.total_float_days < 0.0,
    ).limit(30)
    dq_float_res = await db.execute(dq_float_query)
    dq_float_acts = dq_float_res.scalars().all()

    for act in dq_float_acts:
        items.append(
            UpdateFeedItem(
                id=f"dq_flt_{act.id}",
                source_type="data_quality",
                severity="critical",
                title=f"Negative Float Detected: {act.activity_id}",
                detected_change=f"Schedule float consumed ({act.total_float_days:.1f} days). Path is delaying project completion.",
                affected_activity_id=act.activity_id,
                affected_activity_name=act.activity_name,
                current_value=f"{act.total_float_days:.1f} days float",
                proposed_value="Requires Critical Path Re-leveling",
                confidence=1.0,
                timestamp=act.updated_at or act.created_at,
                source_info="Critical Path Engine",
                action_label="View in Schedule",
                target_route=f"/schedule?highlight={act.activity_id}",
            )
        )
    data_quality_count = len(dq_finish_acts) + len(dq_float_acts)

    # 3. Schedule Changes / Recent Validated Actuals
    sched_query = (
        select(ProgressEvent)
        .where(
            ProgressEvent.match_status == MatchStatusEnum.matched,
            ProgressEvent.actual_start_datetime.is_not(None),
        )
        .order_by(ProgressEvent.extraction_timestamp.desc().nullslast())
        .limit(20)
    )
    sched_res = await db.execute(sched_query)
    sched_events = sched_res.scalars().all()
    schedule_changes_count = len(sched_events)

    for ev in sched_events:
        items.append(
            UpdateFeedItem(
                id=f"sched_{ev.id}",
                source_type="schedule_change",
                severity="info",
                title=f"Schedule Actual Applied: {ev.activity_id_plan or 'Activity'}",
                detected_change=f"Progress updated to {ev.percent_complete or 0:.0f}% (Actual Start: {ev.actual_start_datetime.strftime('%Y-%m-%d') if ev.actual_start_datetime else '—'})",
                affected_activity_id=ev.activity_id_plan,
                affected_activity_name=ev.activity_name_plan,
                current_value=f"{ev.percent_complete or 0:.0f}%",
                proposed_value="Validated in Schedule",
                confidence=ev.confidence_score,
                timestamp=ev.extraction_timestamp or ev.created_at,
                source_info=f"Field Ingestion ({ev.extracted_by})",
                action_label="Inspect Gantt",
                target_route=f"/schedule?highlight={ev.activity_id_plan or ''}",
            )
        )

    # 4. Documents awaiting processing or with errors
    doc_query = (
        select(Document)
        .where(
            or_(
                Document.processing_status.in_(["queued", "processing", "failed"]),
            )
        )
        .order_by(Document.received_at.desc())
        .limit(20)
    )
    doc_res = await db.execute(doc_query)
    pending_docs = doc_res.scalars().all()
    pending_documents_count = len(pending_docs)

    for doc in pending_docs:
        sev: Literal["critical", "warning", "info"] = "critical" if doc.processing_status == "failed" else "info"
        items.append(
            UpdateFeedItem(
                id=f"doc_{doc.id}",
                source_type="document",
                severity=sev,
                title=f"Document {doc.processing_status.title()}: {doc.source_type.value if hasattr(doc.source_type, 'value') else doc.source_type}",
                detected_change=doc.processing_error or f"Received from sender {doc.sender_id}, awaiting completion.",
                affected_activity_id=None,
                affected_activity_name=None,
                current_value=doc.processing_status,
                proposed_value=None,
                confidence=None,
                timestamp=doc.received_at,
                source_info=f"Sender: {doc.sender_id}",
                action_label="View Queue",
                target_route="/review",
            )
        )

    # 5. Proposed Terminology Aliases
    alias_query = (
        select(EntityAlias)
        .where(EntityAlias.status == "proposed")
        .order_by(EntityAlias.created_at.desc())
        .limit(20)
    )
    alias_res = await db.execute(alias_query)
    proposed_aliases = alias_res.scalars().all()
    pending_aliases_count = len(proposed_aliases)

    for al in proposed_aliases:
        items.append(
            UpdateFeedItem(
                id=f"alias_{al.id}",
                source_type="entity_alias",
                severity="info",
                title=f"Proposed Terminology: \"{al.raw_alias}\" → \"{al.canonical_value}\"",
                detected_change=f"AI proposed entity mapping for {al.entity_type} (confidence {int(al.confidence * 100)}%).",
                affected_activity_id=None,
                affected_activity_name=None,
                current_value=al.raw_alias,
                proposed_value=al.canonical_value,
                confidence=al.confidence,
                timestamp=al.created_at,
                source_info=f"Proposed by {al.proposed_by}",
                action_label="Approve / Reject",
                target_route="/review?tab=aliases",
            )
        )

    # Filter if requested
    filtered = items
    if source_type:
        filtered = [i for i in filtered if i.source_type == source_type]
    if severity:
        filtered = [i for i in filtered if i.severity == severity]

    # Sort: Critical first, then Warning, then Info, then by timestamp desc
    sev_rank = {"critical": 0, "warning": 1, "info": 2}
    filtered.sort(
        key=lambda x: (
            sev_rank.get(x.severity, 3),
            -(x.timestamp.timestamp() if x.timestamp else 0),
        )
    )

    offset = (page - 1) * page_size
    paginated = filtered[offset : offset + page_size]

    summary = UpdateCenterSummary(
        total_items=len(items),
        pending_reviews=pending_reviews_count,
        data_quality_flags=data_quality_count,
        schedule_changes=schedule_changes_count,
        pending_documents=pending_documents_count,
        pending_aliases=pending_aliases_count,
    )

    return UpdateCenterFeedResponse(summary=summary, items=paginated)
