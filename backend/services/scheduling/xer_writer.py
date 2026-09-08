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
    input_path = Path(input_xer_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input XER not found: {input_path}")

    # Determine output path
    if output_path is None:
        tmp = tempfile.mktemp(suffix=".xer", prefix="sih26122_updated_")
        output_path = Path(tmp)
    else:
        output_path = Path(output_path)

    # Try PyP6Xer if available; fallback to native TSV modifier
    try:
        from PyP6Xer.reader import Reader
        reader = Reader(str(input_path))
        use_native = False
    except Exception as exc:
        log.info("xer_writer.using_native_writer", reason=str(exc))
        use_native = True

    if use_native:
        return _apply_actuals_to_xer_native(input_path, validated_events, output_path)

    # Build a lookup: activity_id → actuals
    actuals_by_id: dict[str, dict] = {
        e["activity_id"]: e for e in validated_events if e.get("activity_id")
    }

    if not actuals_by_id:
        log.info("xer_writer.no_actuals_to_apply")

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


def _apply_actuals_to_xer_native(
    input_path: Path,
    validated_events: list[dict[str, Any]],
    output_path: Path,
) -> Path:
    """
    Native Primavera P6 XER actuals modifier.
    Updates actual start, actual finish, and phys_complete_pct on TASK table rows
    while preserving all other tables and lines.
    """
    actuals_by_id: dict[str, dict] = {
        str(e["activity_id"]): e for e in validated_events if e.get("activity_id")
    }

    lines = input_path.read_text(encoding="utf-8", errors="replace").splitlines()
    output_lines: list[str] = []
    current_table: str | None = None
    task_fields: list[str] = []
    updated_count = 0

    for line in lines:
        raw_line = line.rstrip("\r\n")
        if not raw_line:
            output_lines.append(line)
            continue

        parts = raw_line.split("\t")
        tag = parts[0]

        if tag == "%T":
            current_table = parts[1] if len(parts) > 1 else None
            output_lines.append(raw_line)
        elif tag == "%F" and current_table == "TASK":
            task_fields = parts[1:]
            # Ensure act_start_date, act_end_date, phys_complete_pct exist in task_fields
            for field in ["act_start_date", "act_end_date", "phys_complete_pct"]:
                if field not in task_fields:
                    task_fields.append(field)
            output_lines.append("%F\t" + "\t".join(task_fields))
        elif tag == "%R" and current_table == "TASK":
            vals = parts[1:]
            while len(vals) < len(task_fields):
                vals.append("")
            row_dict = {f: v for f, v in zip(task_fields, vals)}
            task_code = str(row_dict.get("task_code", "") or "")

            if task_code and task_code in actuals_by_id:
                act = actuals_by_id[task_code]
                if act.get("actual_start"):
                    row_dict["act_start_date"] = _format_p6_date(act["actual_start"])
                if act.get("actual_finish"):
                    row_dict["act_end_date"] = _format_p6_date(act["actual_finish"])
                if act.get("percent_complete") is not None:
                    row_dict["phys_complete_pct"] = str(act["percent_complete"])
                updated_count += 1

            new_row_vals = [str(row_dict.get(f, "")) for f in task_fields]
            output_lines.append("%R\t" + "\t".join(new_row_vals))
        else:
            output_lines.append(raw_line)

    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    log.info(
        "xer_writer.native_done",
        input=str(input_path),
        output=str(output_path),
        updated_activities=updated_count,
    )
    return output_path

