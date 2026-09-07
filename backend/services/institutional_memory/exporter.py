"""
Dataset exporter — materializes the institutional memory into portable artifacts.

Exports:
  - progress_events.parquet   (typed, efficient, ML-ready)
  - progress_events.csv       (human/LLM-readable)
  - SCHEMA.md                 (data dictionary — field names, types, descriptions)
  - summary_stats.json        (aggregate metrics: planned vs actual by discipline)

Per §7 of the project context: this export step is explicitly required —
"institutional memory becomes a real artifact, not just a database table."
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

SCHEMA_MD_SOURCE = Path(__file__).parent.parent.parent.parent / "data" / "SCHEMA.md"


def export_dataset(
    output_dir: str | Path,
    db_url_sync: str,
) -> dict[str, Any]:
    """
    Export all matched/accepted progress events from Postgres to Parquet + CSV + SCHEMA.md.

    Args:
        output_dir: Directory to write export files.
        db_url_sync: Synchronous DB URL (psycopg2) for pandas read_sql.

    Returns:
        Dict with file paths and summary statistics.
    """
    import pandas as pd
    import sqlalchemy

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    log.info("exporter.starting", output_dir=str(output))

    engine = sqlalchemy.create_engine(db_url_sync)

    # Query: all matched + accepted + edited events
    query = """
        SELECT
            pe.id::text AS event_id,
            pe.project_id,
            pe.activity_id_plan,
            pe.activity_name_plan,
            pe.activity_description_extracted,
            pe.discipline::text,
            pe.event_type::text,
            pe.actual_start_datetime,
            pe.actual_finish_datetime,
            pe.percent_complete,
            pe.quantity_completed,
            pe.quantity_unit,
            pe.location_reference,
            pe.confidence_score,
            pe.match_status::text,
            pe.source_type::text,
            pe.source_document_id,
            pe.extracted_by,
            pe.extraction_timestamp,
            pe.reviewed_by_planner,
            pe.planner_notes,
            pe.created_at,
            -- Join planned duration from plan_activities
            pa.original_duration_days AS planned_duration_days,
            pa.planned_start,
            pa.planned_finish,
            -- Compute actual duration in days
            EXTRACT(EPOCH FROM (pe.actual_finish_datetime - pe.actual_start_datetime)) / 86400.0
                AS actual_duration_days
        FROM progress_events pe
        LEFT JOIN plan_activities pa ON pe.plan_activity_id = pa.id
        WHERE pe.match_status IN ('matched', 'low_confidence_review')
           OR pe.reviewed_by_planner = true
        ORDER BY pe.extraction_timestamp DESC
    """

    df = pd.read_sql(query, engine)
    engine.dispose()

    if df.empty:
        log.warning("exporter.no_events_found")
        return {"event_count": 0, "files": []}

    # --- Write Parquet ---
    parquet_path = output / "progress_events.parquet"
    df.to_parquet(parquet_path, index=False, engine="pyarrow")

    # --- Write CSV ---
    csv_path = output / "progress_events.csv"
    df.to_csv(csv_path, index=False)

    # --- Copy SCHEMA.md ---
    schema_dest = output / "SCHEMA.md"
    if SCHEMA_MD_SOURCE.exists():
        shutil.copy2(SCHEMA_MD_SOURCE, schema_dest)
    else:
        # Write a minimal schema doc if source not found
        schema_dest.write_text(_generate_schema_md(df))

    # --- Summary statistics ---
    summary = _compute_summary(df)
    summary_path = output / "summary_stats.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    files = [str(parquet_path), str(csv_path), str(schema_dest), str(summary_path)]

    log.info(
        "exporter.done",
        event_count=len(df),
        files=files,
    )

    return {
        "event_count": len(df),
        "files": files,
        "summary": summary,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _compute_summary(df) -> dict[str, Any]:
    """Compute aggregate statistics for judges."""
    import numpy as np

    summary: dict[str, Any] = {
        "total_events": len(df),
        "events_by_discipline": df["discipline"].value_counts().to_dict(),
        "events_by_status": df["match_status"].value_counts().to_dict(),
        "reviewed_by_planner": int(df["reviewed_by_planner"].sum()),
        "avg_confidence_score": float(df["confidence_score"].mean()) if "confidence_score" in df else None,
    }

    # Planned vs Actual duration by discipline
    duration_df = df.dropna(subset=["planned_duration_days", "actual_duration_days"])
    if not duration_df.empty:
        by_discipline = (
            duration_df.groupby("discipline")
            .agg(
                avg_planned_days=("planned_duration_days", "mean"),
                avg_actual_days=("actual_duration_days", "mean"),
                event_count=("event_id", "count"),
            )
            .round(2)
        )
        by_discipline["ratio_actual_to_planned"] = (
            by_discipline["avg_actual_days"] / by_discipline["avg_planned_days"]
        ).round(2)
        summary["duration_by_discipline"] = by_discipline.to_dict(orient="index")

    return summary


def _generate_schema_md(df) -> str:
    """Generate a minimal SCHEMA.md from the DataFrame columns if the source file is missing."""
    lines = [
        "# Progress Events Dataset — Schema\n",
        "Auto-generated from export. See `data/SCHEMA.md` for the canonical version.\n\n",
        "| Column | Type | Description |\n",
        "|---|---|---|\n",
    ]
    for col in df.columns:
        dtype = str(df[col].dtype)
        lines.append(f"| `{col}` | {dtype} | |\n")
    return "".join(lines)
