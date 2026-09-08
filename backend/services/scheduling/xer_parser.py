"""
PyP6XER-based XER parser.
Reads a Primavera P6 .XER file and extracts plan activities
into the plan_activities table and the semantic embedding index.

Also handles the seeding path for synthetic XER files during demo setup.
"""

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# Discipline inference heuristics — map keywords in activity names to disciplines
DISCIPLINE_KEYWORDS = {
    "piping": ["piping", "pipe", "spool", "hydrotest", "hydro test", "weld", "flange", "valve", "line"],
    "civil": ["excavat", "foundation", "concrete", "formwork", "backfill", "grout", "civil", "earthwork"],
    "electrical": ["electrical", "cable", "mcc", "panel", "conduit", "termination", "electric"],
    "instrumentation": ["instrument", "calibrat", "transmitter", "sensor", "loop", "control"],
    "hse": ["hse", "safety", "audit", "inspection", "toolbox", "permit"],
    "structural": ["structural", "steel", "fabricat", "erect", "column", "beam", "structure"],
    "mechanical": ["pump", "compressor", "vessel", "equipment", "mechanical", "rotating", "static"],
}


def _infer_discipline(activity_name: str) -> str:
    """Infer discipline from activity name using keyword heuristics."""
    name_lower = activity_name.lower()
    for discipline, keywords in DISCIPLINE_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return discipline
    return "unknown"


def _parse_p6_datetime(date_str: str | None) -> datetime | None:
    """Parse P6 date format (YYYY-MM-DD HH:MM) to timezone-aware datetime."""
    if not date_str or not date_str.strip():
        return None
    from datetime import timedelta

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        except ValueError:
            continue
    log.warning("xer_parser.date_parse_failed", raw=date_str)
    return None


def load_xer(
    xer_path: str | Path,
    project_id: str,
) -> list[dict[str, Any]]:
    """
    Parse a Primavera P6 .XER file and return a list of activity dicts
    ready for upserting into plan_activities.

    Returns:
        List of dicts with keys matching PlanActivity columns.
    """
    path = Path(xer_path)
    if not path.exists():
        raise FileNotFoundError(f"XER file not found: {path}")

    log.info("xer_parser.loading", path=str(path))

    # Try PyP6Xer if available; fallback to native TSV parser
    try:
        from PyP6Xer.reader import Reader
        reader = Reader(str(path))
        use_native = False
    except Exception as exc:
        log.info("xer_parser.using_native_parser", reason=str(exc))
        use_native = True

    if use_native:
        return _parse_xer_native(path, project_id)

    activities = []

    for project in reader.projects:
        for activity in project.activities:
            activity_id = getattr(activity, "task_code", None) or str(uuid.uuid4())
            activity_name = getattr(activity, "task_name", "") or ""
            wbs_code = None

            # Resolve WBS
            try:
                wbs = activity.wbs
                wbs_code = getattr(wbs, "wbs_short_name", None)
            except Exception:
                pass

            # Planned dates
            planned_start = _parse_p6_datetime(
                str(getattr(activity, "target_start_date", "") or "")
            )
            planned_finish = _parse_p6_datetime(
                str(getattr(activity, "target_end_date", "") or "")
            )

            # Duration in hours → days
            orig_duration = getattr(activity, "target_drtn_hr_cnt", None)
            duration_days = float(orig_duration) / 8.0 if orig_duration else None

            pct_complete = getattr(activity, "phys_complete_pct", 0.0) or 0.0

            discipline = _infer_discipline(activity_name)

            activities.append(
                {
                    "activity_id": str(activity_id),
                    "activity_name": str(activity_name),
                    "wbs_code": wbs_code,
                    "discipline": discipline,
                    "planned_start": planned_start,
                    "planned_finish": planned_finish,
                    "original_duration_days": duration_days,
                    "percent_complete_plan": float(pct_complete),
                    "project_id": project_id,
                    "is_field_confirmed": False,
                }
            )

    log.info(
        "xer_parser.done",
        path=str(path),
        activity_count=len(activities),
    )
    return activities


def _parse_xer_native(path: Path, project_id: str) -> list[dict[str, Any]]:
    """
    Native Primavera P6 .XER parser.
    Parses tab-separated tables (%T, %F, %R) without external library dependencies.
    """
    activities = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    current_table = None
    fields: list[str] = []

    for line in lines:
        line = line.strip("\r\n")
        if not line:
            continue
        parts = line.split("\t")
        tag = parts[0]

        if tag == "%T":
            current_table = parts[1] if len(parts) > 1 else None
            fields = []
        elif tag == "%F":
            fields = parts[1:]
        elif tag == "%R" and current_table == "TASK":
            row_vals = parts[1:]
            row_dict = {f: v for f, v in zip(fields, row_vals)}

            task_code = row_dict.get("task_code") or str(uuid.uuid4())
            task_name = row_dict.get("task_name") or ""
            wbs_code = row_dict.get("wbs_id") or row_dict.get("wbs_code")
            planned_start = _parse_p6_datetime(row_dict.get("target_start_date"))
            planned_finish = _parse_p6_datetime(row_dict.get("target_end_date"))
            orig_duration = row_dict.get("target_drtn_hr_cnt")
            duration_days = float(orig_duration) / 8.0 if orig_duration else None
            pct_complete = float(row_dict.get("phys_complete_pct") or 0.0)
            discipline = _infer_discipline(task_name)

            activities.append(
                {
                    "activity_id": str(task_code),
                    "activity_name": str(task_name),
                    "wbs_code": str(wbs_code) if wbs_code else None,
                    "discipline": discipline,
                    "planned_start": planned_start,
                    "planned_finish": planned_finish,
                    "original_duration_days": duration_days,
                    "percent_complete_plan": pct_complete,
                    "project_id": project_id,
                    "is_field_confirmed": False,
                }
            )

    log.info(
        "xer_parser.native_done",
        path=str(path),
        activity_count=len(activities),
    )
    return activities

