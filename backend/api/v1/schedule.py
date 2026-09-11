"""Schedule API — activity index, actuals view, XER export, and new activity creation."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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


@router.post("/import")
async def import_schedule(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Import schedule activities from a Primavera P6 .XER file or spreadsheet (.csv, .xlsx, .xls).
    - Parses activities and metadata.
    - Saves active XER file to data/synthetic/sample_schedule.xer for subsequent exports.
    - Upserts into plan_activities table.
    - Reloads semantic embeddings in matching engine.
    - Re-indexes into Qdrant institutional memory.
    """
    from backend.core.config import get_settings
    from backend.services.scheduling.xer_parser import (
        _infer_discipline,
        _parse_p6_datetime,
        load_xer,
    )
    from backend.services.scheduling.schedule_service import reload_matching_index

    settings = get_settings()
    filename = file.filename or "uploaded_schedule"
    ext = Path(filename).suffix.lower()

    if ext not in [".xer", ".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: .xer, .csv, .xlsx, .xls",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    activities = []
    if ext == ".xer":
        xer_dir = Path("data/synthetic")
        xer_dir.mkdir(parents=True, exist_ok=True)
        active_xer_path = xer_dir / "sample_schedule.xer"
        active_xer_path.write_bytes(content)

        try:
            activities = load_xer(active_xer_path, project_id=settings.project_id)
        except Exception as exc:
            log.error("schedule.import_xer_parse_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse XER file: {str(exc)}",
            )
    elif ext in [".csv", ".xlsx", ".xls"]:
        import io
        import pandas as pd

        try:
            if ext == ".csv":
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse spreadsheet: {str(exc)}",
            )

        col_map = {str(c).strip().lower().replace(" ", "_").replace("-", "_"): c for c in df.columns}

        def get_col_val(row, *candidates):
            for cand in candidates:
                if cand in col_map:
                    val = row[col_map[cand]]
                    if pd.notna(val):
                        return val
            return None

        for _, row in df.iterrows():
            act_id = get_col_val(row, "activity_id", "task_code", "id", "activity_code", "task_id")
            act_name = get_col_val(row, "activity_name", "task_name", "name", "description")
            if not act_id and not act_name:
                continue
            act_id = str(act_id if act_id is not None else uuid.uuid4())
            act_name = str(act_name if act_name is not None else act_id)

            wbs = get_col_val(row, "wbs_code", "wbs", "wbs_name")
            disc = get_col_val(row, "discipline", "trade", "dept")
            if not disc:
                disc = _infer_discipline(act_name)

            p_start = get_col_val(row, "planned_start", "target_start_date", "start_date", "start")
            p_finish = get_col_val(row, "planned_finish", "target_end_date", "finish_date", "finish", "end")
            duration = get_col_val(row, "original_duration_days", "duration", "duration_days", "target_drtn_hr_cnt")

            parsed_start = _parse_p6_datetime(str(p_start)) if p_start else None
            parsed_finish = _parse_p6_datetime(str(p_finish)) if p_finish else None
            dur_float = None
            if duration is not None:
                try:
                    dur_float = float(duration)
                except (ValueError, TypeError):
                    pass

            activities.append(
                {
                    "activity_id": act_id,
                    "activity_name": act_name,
                    "wbs_code": str(wbs) if wbs else None,
                    "discipline": str(disc).lower(),
                    "planned_start": parsed_start,
                    "planned_finish": parsed_finish,
                    "original_duration_days": dur_float,
                    "percent_complete_plan": 0.0,
                    "project_id": settings.project_id,
                    "is_field_confirmed": False,
                }
            )

    if not activities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid activities found in the uploaded file.",
        )

    inserted = 0
    updated = 0
    for act_data in activities:
        act_id = act_data["activity_id"]
        existing = (
            await db.execute(select(PlanActivity).where(PlanActivity.activity_id == act_id))
        ).scalar_one_or_none()

        if existing:
            for k, v in act_data.items():
                if k != "id" and hasattr(existing, k) and v is not None:
                    setattr(existing, k, v)
            updated += 1
        else:
            new_act = PlanActivity(**act_data)
            db.add(new_act)
            inserted += 1

    await db.commit()

    # Reload matching index
    await reload_matching_index(db)

    # Index into Qdrant store
    try:
        from backend.services.institutional_memory.qdrant_store import index_plan_activity

        for act in activities:
            index_plan_activity(
                activity_id=act["activity_id"],
                activity_name=act["activity_name"],
                discipline=act.get("discipline") or "unknown",
                project_id=settings.project_id,
            )
    except Exception as exc:
        log.warning("schedule.import_qdrant_warn", error=str(exc))

    log.info("schedule.imported", filename=filename, total=len(activities), inserted=inserted, updated=updated)

    return {
        "status": "success",
        "filename": filename,
        "total": len(activities),
        "inserted": inserted,
        "updated": updated,
        "message": f"Successfully imported {len(activities)} activities ({inserted} new, {updated} updated) from {filename}.",
    }


def _is_past_due(dt: datetime | None, now: datetime) -> bool:
    if not dt:
        return False
    if dt.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    elif dt.tzinfo is None and now.tzinfo is not None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < now


@router.get("/gantt")
async def get_gantt_data(
    discipline: str | None = Query(None),
    status: str | None = Query(None),
    contractor: str | None = Query(None),
    critical_only: bool = Query(False),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Part C #1: Nested WBS -> activity structure in one call.
    Includes baseline, current, actual dates, float, critical-path flag,
    and dependency edges between activities.
    """
    from backend.db.models import ActivityDependency
    now = datetime.now(timezone.utc)

    # Base query
    query = select(PlanActivity)

    if discipline:
        query = query.where(PlanActivity.discipline == discipline.lower())
    if contractor:
        query = query.where(PlanActivity.contractor_name.ilike(f"%{contractor}%"))
    if critical_only:
        query = query.where(PlanActivity.is_critical == True)  # noqa: E712
    if search:
        query = query.where(
            (PlanActivity.activity_name.ilike(f"%{search}%"))
            | (PlanActivity.activity_id.ilike(f"%{search}%"))
            | (PlanActivity.wbs_code.ilike(f"%{search}%"))
        )

    res = await db.execute(query.order_by(PlanActivity.planned_start.asc().nullslast()))
    raw_activities = res.scalars().all()

    # Load dependencies for the project
    dep_res = await db.execute(select(ActivityDependency))
    all_deps = dep_res.scalars().all()

    predecessor_map: dict[str, list[dict[str, Any]]] = {}
    successor_map: dict[str, list[dict[str, Any]]] = {}
    dep_edges = []

    for d in all_deps:
        pred_id = d.predecessor_activity_id
        succ_id = d.successor_activity_id
        dep_edges.append({
            "id": str(d.id),
            "predecessor": pred_id,
            "successor": succ_id,
            "type": d.dependency_type or "FS",
            "lag": d.lag_days or 0.0,
        })
        if succ_id not in predecessor_map:
            predecessor_map[succ_id] = []
        predecessor_map[succ_id].append({"activity_id": pred_id, "type": d.dependency_type, "lag": d.lag_days})

        if pred_id not in successor_map:
            successor_map[pred_id] = []
        successor_map[pred_id].append({"activity_id": succ_id, "type": d.dependency_type, "lag": d.lag_days})

    # Format activities and compute status
    formatted_activities = []
    completed_cnt = 0
    in_progress_cnt = 0
    not_started_cnt = 0
    delayed_cnt = 0
    critical_cnt = 0

    all_dates = []

    for a in raw_activities:
        pct = a.actual_percent_complete if a.actual_percent_complete is not None else (a.percent_complete_plan or 0.0)
        is_crit = bool(a.is_critical or (a.total_float_days is not None and a.total_float_days <= 0.0))

        # Status computation
        if pct >= 100.0:
            act_status = "completed"
            completed_cnt += 1
        elif (_is_past_due(a.planned_finish, now) and pct < 100.0) or (a.total_float_days is not None and a.total_float_days < 0):
            act_status = "delayed"
            delayed_cnt += 1
            if pct > 0:
                in_progress_cnt += 1
            else:
                not_started_cnt += 1
        elif pct > 0.0:
            act_status = "in_progress"
            in_progress_cnt += 1
        else:
            act_status = "not_started"
            not_started_cnt += 1

        if is_crit:
            critical_cnt += 1

        if status and act_status != status:
            continue

        if a.planned_start:
            all_dates.append(a.planned_start)
        if a.planned_finish:
            all_dates.append(a.planned_finish)
        if a.actual_start:
            all_dates.append(a.actual_start)
        if a.actual_finish:
            all_dates.append(a.actual_finish)

        formatted_activities.append({
            "id": str(a.id),
            "activity_id": a.activity_id,
            "activity_name": a.activity_name,
            "wbs_code": a.wbs_code or "WBS-1.0",
            "wbs_name": a.wbs_name or a.wbs_code or "Main Project",
            "discipline": a.discipline or "general",
            "contractor_name": a.contractor_name or "OIL Field Crew",
            "area": a.area or "General Area",
            "unit": a.unit or "Unit 1",
            "planned_start": a.planned_start.isoformat() if a.planned_start else None,
            "planned_finish": a.planned_finish.isoformat() if a.planned_finish else None,
            "original_duration_days": a.original_duration_days or 1.0,
            "percent_complete_plan": a.percent_complete_plan or 0.0,
            "actual_start": a.actual_start.isoformat() if a.actual_start else None,
            "actual_finish": a.actual_finish.isoformat() if a.actual_finish else None,
            "actual_percent_complete": pct,
            "total_float_days": a.total_float_days or 0.0,
            "is_critical": is_crit,
            "delay_risk_score": a.delay_risk_score or 0.0,
            "status": act_status,
            "predecessors": [p["activity_id"] for p in predecessor_map.get(a.activity_id, [])],
            "predecessors_detail": predecessor_map.get(a.activity_id, []),
            "successors": [s["activity_id"] for s in successor_map.get(a.activity_id, [])],
        })

    # Group into WBS hierarchy tree
    wbs_groups: dict[str, dict[str, Any]] = {}
    for item in formatted_activities:
        code = item["wbs_code"]
        if code not in wbs_groups:
            wbs_groups[code] = {
                "wbs_code": code,
                "wbs_name": item["wbs_name"],
                "activities": [],
                "planned_start": None,
                "planned_finish": None,
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0.0,
                "is_critical": False,
            }
        group = wbs_groups[code]
        group["activities"].append(item)
        if item["is_critical"]:
            group["is_critical"] = True

    # Compute WBS rollups
    wbs_tree = []
    for code, group in wbs_groups.items():
        acts = group["activities"]
        starts = [a["planned_start"] for a in acts if a["planned_start"]]
        finishes = [a["planned_finish"] for a in acts if a["planned_finish"]]
        act_starts = [a["actual_start"] for a in acts if a["actual_start"]]
        act_finishes = [a["actual_finish"] for a in acts if a["actual_finish"]]

        group["planned_start"] = min(starts) if starts else None
        group["planned_finish"] = max(finishes) if finishes else None
        group["actual_start"] = min(act_starts) if act_starts else None
        group["actual_finish"] = max(act_finishes) if len(act_finishes) == len(acts) and acts else None
        group["percent_complete"] = round(sum(a["actual_percent_complete"] for a in acts) / max(len(acts), 1), 1)
        wbs_tree.append(group)

    min_date_str = min(all_dates).isoformat() if all_dates else None
    max_date_str = max(all_dates).isoformat() if all_dates else None

    return {
        "total": len(formatted_activities),
        "activities": formatted_activities,
        "wbs_tree": wbs_tree,
        "dependencies": dep_edges,
        "summary": {
            "total_activities": len(raw_activities),
            "filtered_count": len(formatted_activities),
            "completed_count": completed_cnt,
            "in_progress_count": in_progress_cnt,
            "not_started_count": not_started_cnt,
            "delayed_count": delayed_cnt,
            "critical_count": critical_cnt,
            "min_date": min_date_str,
            "max_date": max_date_str,
        }
    }


@router.get("/activities/{activity_id}/detail")
async def get_activity_detail_aggregate(
    activity_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Part C #5: Unified activity detail endpoint.
    Returns identity + schedule + progress + intelligence + risk + audit sections
    in one single call. Includes evidence breadcrumb chain and prediction explainability strip.
    """
    from backend.db.models import ActivityDependency, Document, Match, ProgressEvent, ReviewDecision
    from backend.services.analytics.prediction_engine import compute_activity_prediction

    # 1. Fetch PlanActivity
    res = await db.execute(
        select(PlanActivity).where(
            (PlanActivity.activity_id == activity_id) | (PlanActivity.id == activity_id if len(activity_id) == 36 else False)
        )
    )
    act = res.scalar_one_or_none()
    if not act:
        raise HTTPException(status_code=404, detail=f"Activity '{activity_id}' not found.")

    # 2. Dependencies
    dep_res = await db.execute(
        select(ActivityDependency).where(
            (ActivityDependency.predecessor_activity_id == act.activity_id)
            | (ActivityDependency.successor_activity_id == act.activity_id)
        )
    )
    deps = dep_res.scalars().all()
    predecessors = []
    successors = []
    for d in deps:
        if d.successor_activity_id == act.activity_id:
            predecessors.append({"activity_id": d.predecessor_activity_id, "type": d.dependency_type, "lag": d.lag_days})
        if d.predecessor_activity_id == act.activity_id:
            successors.append({"activity_id": d.successor_activity_id, "type": d.dependency_type, "lag": d.lag_days})

    # 3. Progress Events matching this activity
    ev_res = await db.execute(
        select(ProgressEvent)
        .where(
            (ProgressEvent.activity_id_plan == act.activity_id)
            | (ProgressEvent.plan_activity_id == act.id)
        )
        .order_by(ProgressEvent.extraction_timestamp.desc().nullslast())
    )
    events = ev_res.scalars().all()

    # 4. Intelligence and Evidence chain
    latest_event = events[0] if events else None
    evidence_breadcrumb = [
        {"level": "Activity", "id": act.activity_id, "label": f"{act.activity_id} ({act.activity_name[:30]})"},
    ]
    source_document = None
    match_candidates = []

    if latest_event:
        evidence_breadcrumb.append({
            "level": "Progress Event",
            "id": str(latest_event.id),
            "label": f"Event #{str(latest_event.id)[:8]} ({latest_event.event_type.value if latest_event.event_type else 'update'})",
        })

        if latest_event.document_id:
            doc_res = await db.execute(select(Document).where(Document.id == latest_event.document_id))
            doc = doc_res.scalar_one_or_none()
            if doc:
                source_document = {
                    "document_id": str(doc.id),
                    "sender_id": doc.sender_id,
                    "source_type": doc.source_type.value if hasattr(doc.source_type, "value") else doc.source_type,
                    "received_at": doc.received_at.isoformat() if doc.received_at else None,
                    "raw_text_excerpt": (doc.raw_text[:300] + "...") if doc.raw_text and len(doc.raw_text) > 300 else doc.raw_text,
                    "mime_type": doc.mime_type,
                }
                evidence_breadcrumb.append({
                    "level": "Document",
                    "id": str(doc.id),
                    "label": f"Doc ({doc.source_type.value if hasattr(doc.source_type, 'value') else doc.source_type})",
                })
                evidence_breadcrumb.append({
                    "level": "Original Message",
                    "id": doc.sender_id,
                    "label": f"WhatsApp: {doc.sender_id}",
                })

        # Match candidates
        m_res = await db.execute(select(Match).where(Match.event_id == latest_event.id).order_by(Match.rank.asc().nullslast()))
        matches = m_res.scalars().all()
        for m in matches:
            match_candidates.append({
                "candidate_activity_id": m.candidate_activity_id,
                "fuzzy_score": m.fuzzy_score,
                "semantic_score": m.semantic_score,
                "llm_score": m.llm_score,
                "final_score": m.final_score,
                "rank": m.rank,
                "was_selected": m.was_selected,
            })

    # 5. Deterministic Prediction & Explainability Strip
    def _run_pred(session):
        try:
            return compute_activity_prediction(act.activity_id, session)
        except Exception as exc:
            log.warning("schedule.detail_pred_fallback", error=str(exc))
            return {
                "predicted_finish": act.planned_finish.strftime("%Y-%m-%d") if act.planned_finish else None,
                "predicted_delay_days": 0.0,
                "delay_risk_percentage": 10.0,
                "confidence": 0.85,
                "variance_factor": 1.0,
                "contributing_factors": ["Normal progression within baseline float"],
                "supporting_evidence": [],
                "narrative": "Activity tracking within baseline schedule parameters.",
            }

    prediction_data = await db.run_sync(_run_pred)

    # 6. Audit Trail & Review Decisions
    dec_res = await db.execute(
        select(ReviewDecision)
        .join(ProgressEvent, ReviewDecision.event_id == ProgressEvent.id)
        .where(
            (ProgressEvent.activity_id_plan == act.activity_id)
            | (ProgressEvent.plan_activity_id == act.id)
        )
        .order_by(ReviewDecision.decided_at.desc())
    )
    decisions = dec_res.scalars().all()

    audit_records = []
    for d in decisions:
        audit_records.append({
            "decision_id": str(d.id),
            "decision": d.decision.value if hasattr(d.decision, "value") else str(d.decision),
            "reviewer": "Planner",
            "notes": d.notes,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            "corrected_fields": d.corrected_fields,
        })

    # Progress history
    progress_history = []
    for ev in events:
        progress_history.append({
            "event_id": str(ev.id),
            "timestamp": ev.extraction_timestamp.isoformat() if ev.extraction_timestamp else ev.created_at.isoformat(),
            "extracted_description": ev.activity_description_extracted or ev.activity_description_raw,
            "percent_complete": ev.percent_complete,
            "actual_start": ev.actual_start_datetime.isoformat() if ev.actual_start_datetime else None,
            "actual_finish": ev.actual_finish_datetime.isoformat() if ev.actual_finish_datetime else None,
            "blocker_description": ev.blocker_description,
            "delay_category": ev.delay_category,
            "confidence_score": ev.confidence_score,
            "provenance_category": ev.provenance_category,
        })

    pct = act.actual_percent_complete if act.actual_percent_complete is not None else (act.percent_complete_plan or 0.0)
    now = datetime.now(timezone.utc)
    status_label = "completed" if pct >= 100 else ("delayed" if (_is_past_due(act.planned_finish, now) and pct < 100) or (act.total_float_days and act.total_float_days < 0) else ("in_progress" if pct > 0 else "not_started"))

    return {
        "identity": {
            "id": str(act.id),
            "activity_id": act.activity_id,
            "activity_name": act.activity_name,
            "wbs_code": act.wbs_code or "WBS-1.0",
            "wbs_name": act.wbs_name or act.wbs_code or "Main Project",
            "discipline": act.discipline or "general",
            "contractor_name": act.contractor_name or "OIL Field Crew",
            "area": act.area or "General Area",
            "unit": act.unit or "Unit 1",
            "is_critical": bool(act.is_critical or (act.total_float_days is not None and act.total_float_days <= 0.0)),
        },
        "schedule": {
            "planned_start": act.planned_start.isoformat() if act.planned_start else None,
            "planned_finish": act.planned_finish.isoformat() if act.planned_finish else None,
            "original_duration_days": act.original_duration_days or 1.0,
            "percent_complete_plan": act.percent_complete_plan or 0.0,
            "actual_start": act.actual_start.isoformat() if act.actual_start else None,
            "actual_finish": act.actual_finish.isoformat() if act.actual_finish else None,
            "actual_percent_complete": pct,
            "total_float_days": act.total_float_days or 0.0,
            "status": status_label,
            "predecessors": predecessors,
            "successors": successors,
        },
        "progress": {
            "percent_complete": pct,
            "history": progress_history,
        },
        "intelligence": {
            "latest_event_id": str(latest_event.id) if latest_event else None,
            "extracted_description": latest_event.activity_description_extracted if latest_event else None,
            "confidence_score": latest_event.confidence_score if latest_event else None,
            "confidence_tier": latest_event.confidence_tier if latest_event else "medium",
            "extracted_by": latest_event.extracted_by if latest_event else "system",
            "match_candidates": match_candidates,
            "source_document": source_document,
            "evidence_breadcrumb": evidence_breadcrumb,
        },
        "risk": {
            "delay_risk_score": act.delay_risk_score or prediction_data.get("delay_risk_percentage", 0.0) / 100.0,
            "predicted_finish": prediction_data.get("predicted_finish"),
            "predicted_delay_days": prediction_data.get("predicted_delay_days", 0.0),
            "delay_risk_percentage": prediction_data.get("delay_risk_percentage", 0.0),
            "confidence": prediction_data.get("confidence", 0.8),
            "variance_factor": prediction_data.get("variance_factor", 1.0),
            "contributing_factors": prediction_data.get("contributing_factors", []),
            "narrative": prediction_data.get("narrative", ""),
            "explainability_strip": prediction_data.get("supporting_evidence", []),
        },
        "audit": {
            "decisions": audit_records,
            "correction_history": latest_event.correction_history if latest_event else [],
            "planner_notes": latest_event.planner_notes if latest_event else None,
            "created_at": act.created_at.isoformat() if act.created_at else None,
            "updated_at": act.updated_at.isoformat() if act.updated_at else None,
        }
    }
