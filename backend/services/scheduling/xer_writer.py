"""
XER writer — applies validated actuals from our database back into a P6 XER file.

Only modifies: actual_start_date, actual_end_date, phys_complete_pct.
Preserves ALL other fields: relationships, calendars, resources, baselines,
constraints, codes, roles, WBS structure, project-level data.

Per ADR-008: validated against synthetic XER only — not verified against live P6.
This is the correct and expected scope for the prototype.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

P6_DATE_FORMAT = "%Y-%m-%d %H:%M"


def _format_p6_date(dt: datetime | None) -> str:
    """Format a datetime to P6's expected string format."""
    if dt is None:
        return ""
    # Convert to naive local time (P6 stores naive datetimes)
    naive = dt.replace(tzinfo=None)
    return naive.strftime(P6_DATE_FORMAT)


def apply_actuals_to_xer(
    input_xer_path: str | Path,
    validated_events: list[dict[str, Any]],
    output_path: str | Path | None = None,
) -> Path:
    """
    Read the input XER, apply actual_start/finish/pct_complete for matched activities,
    and write to output_path (or a new temp file).

    Args:
        input_xer_path: Path to the original XER file.
        validated_events: List of dicts with keys:
            - activity_id: str (P6 task_code)
            - actual_start: datetime | None
            - actual_finish: datetime | None
            - percent_complete: float | None
        output_path: Where to write the updated XER. Defaults to a temp file.

    Returns:
        Path to the generated XER file.

    Raises:
        FileNotFoundError, ValueError on parse failure.
    """
    from PyP6Xer.reader import Reader

    input_path = Path(input_xer_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input XER not found: {input_path}")

    # Build a lookup: activity_id → actuals
    actuals_by_id: dict[str, dict] = {
        e["activity_id"]: e for e in validated_events if e.get("activity_id")
    }

    if not actuals_by_id:
        log.info("xer_writer.no_actuals_to_apply")

    # Parse the XER
    reader = Reader(str(input_path))
    updated_count = 0

    for project in reader.projects:
        for activity in project.activities:
            task_code = str(getattr(activity, "task_code", "") or "")
            if task_code not in actuals_by_id:
                continue

            actuals = actuals_by_id[task_code]

            if actuals.get("actual_start"):
                activity.act_start_date = _format_p6_date(actuals["actual_start"])
                log.debug(
                    "xer_writer.set_actual_start",
                    activity_id=task_code,
                    value=activity.act_start_date,
                )

            if actuals.get("actual_finish"):
                activity.act_end_date = _format_p6_date(actuals["actual_finish"])
                log.debug(
                    "xer_writer.set_actual_finish",
                    activity_id=task_code,
                    value=activity.act_end_date,
                )

            if actuals.get("percent_complete") is not None:
                activity.phys_complete_pct = float(actuals["percent_complete"])

            updated_count += 1

    # Determine output path
    if output_path is None:
        tmp = tempfile.mktemp(suffix=".xer", prefix="sih26122_updated_")
        output_path = Path(tmp)
    else:
        output_path = Path(output_path)

    # Write the modified XER
    # PyP6Xer's Reader.write() serializes back to XER format
    reader.write(str(output_path))

    log.info(
        "xer_writer.done",
        input=str(input_path),
        output=str(output_path),
        updated_activities=updated_count,
    )

    return output_path
