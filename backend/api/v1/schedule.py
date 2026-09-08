"""Schedule API — activity index, actuals view, XER export, and new activity creation."""

import uuid
from datetime import datetime
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
