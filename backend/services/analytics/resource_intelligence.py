"""
Resource Intelligence Service.
Reference: SIH26122 §1.10.

Explicitly categorizes resource reporting into:
- Observed: directly logged in field updates (crews, named supervisors, explicit equipment)
- Inferred: derived from active task concurrency & standard crew estimates
- Unknown: activities without reported manpower/crew data (incomplete reporting != poor performance)
"""

from typing import Any
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import PlanActivity, ProgressEvent


def get_resource_intelligence(session: Session) -> dict[str, Any]:
    """
    Compute resource workload, contractor mappings, and Observed vs Inferred vs Unknown breakdown.
    """
    events = session.execute(select(ProgressEvent)).scalars().all()
    activities = session.execute(select(PlanActivity)).scalars().all()

    observed_records: list[dict[str, Any]] = []
    inferred_records: list[dict[str, Any]] = []
    unknown_activities: list[dict[str, Any]] = []

    contractor_workforce: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "observed_crews": set(),
        "supervisors": set(),
        "active_activities": set(),
        "reported_delayed_tasks": 0,
    })

    discipline_crews: dict[str, int] = defaultdict(int)

    for ev in events:
        c_name = ev.contractor_name or "Direct Project Team"
        sup = ev.supervisor_name
        crew = ev.crew_name
        act_id = ev.activity_id_plan or "GENERAL"

        has_observed = bool(sup or crew)

        if has_observed:
            if sup:
                contractor_workforce[c_name]["supervisors"].add(sup)
            if crew:
                contractor_workforce[c_name]["observed_crews"].add(crew)
                contractor_workforce[c_name]["active_activities"].add(act_id)
            observed_records.append({
                "activity_id": act_id,
                "contractor": c_name,
                "supervisor": sup or "Field Lead",
                "crew": crew or "Standard Gang",
                "discipline": str(ev.discipline.value if hasattr(ev.discipline, "value") else ev.discipline),
                "date": ev.actual_start_datetime.strftime("%Y-%m-%d") if ev.actual_start_datetime else "Recent",
                "type": "Observed",
            })
            discipline_crews[str(ev.discipline.value if hasattr(ev.discipline, "value") else ev.discipline)] += 1

        if ev.delay_status == "delayed" or ev.delay_reason:
            contractor_workforce[c_name]["reported_delayed_tasks"] += 1

    # For active activities with no observed report, infer standard gang or flag unknown
    for act in activities:
        pct = act.actual_percent_complete or act.percent_complete_plan
        is_active = 0 < pct < 100
        if is_active:
            # Check if any event observed for this activity
            has_ev = any(e.activity_id_plan == act.activity_id and (e.supervisor_name or e.crew_name) for e in events)
            if not has_ev:
                disc = act.discipline or "General"
                inferred_records.append({
                    "activity_id": act.activity_id,
                    "activity_name": act.activity_name,
                    "discipline": disc,
                    "inferred_crew_size": 6 if disc.lower() == "piping" else (8 if disc.lower() == "civil" else 4),
                    "basis": "Standard engineering manhour estimate based on active status",
                    "type": "Inferred",
                })
        elif pct == 0:
            unknown_activities.append({
                "activity_id": act.activity_id,
                "activity_name": act.activity_name,
                "discipline": act.discipline or "General",
                "status": "Not Started / No Resource Reported",
                "type": "Unknown",
            })

    # Format contractor workforce summary
    contractor_summary = []
    for c, d in contractor_workforce.items():
        contractor_summary.append({
            "contractor_name": c,
            "supervisors": list(d["supervisors"]),
            "crews_observed": len(d["observed_crews"]) or (1 if d["supervisors"] else 0),
            "active_tasks_count": len(d["active_activities"]) or 1,
            "delayed_tasks_count": d["reported_delayed_tasks"],
        })

    return {
        "summary": {
            "total_observed_events": len(observed_records),
            "total_inferred_assignments": len(inferred_records),
            "total_unreported_activities": len(unknown_activities),
            "reporting_coverage_pct": round(
                (len(observed_records) / max(len(observed_records) + len(inferred_records), 1)) * 100, 1
            ),
        },
        "observed_resources": observed_records[:15],
        "inferred_resources": inferred_records[:10],
        "contractor_breakdown": contractor_summary,
        "discipline_crew_distribution": dict(discipline_crews),
    }
