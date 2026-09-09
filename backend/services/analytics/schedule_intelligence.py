"""
Schedule intelligence analytics — critical path, float consumption, variance, milestone health.
Computes on-demand with short-lived caching.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import MatchStatusEnum, PlanActivity, ProgressEvent


def get_schedule_health(session: Session) -> dict[str, Any]:
    """
    Compute comprehensive project schedule health metrics.
    """
    activities = session.execute(select(PlanActivity)).scalars().all()
    events = session.execute(select(ProgressEvent)).scalars().all()

    total_activities = len(activities)
    if total_activities == 0:
        return {
            "total_activities": 0,
            "overall_progress_pct": 0.0,
            "completed_count": 0,
            "in_progress_count": 0,
            "not_started_count": 0,
            "delayed_count": 0,
            "critical_count": 0,
            "critical_delayed_count": 0,
            "mean_schedule_variance_days": 0.0,
            "milestone_health": [],
            "top_at_risk_activities": [],
            "discipline_health": {},
        }

    completed = 0
    in_progress = 0
    not_started = 0
    delayed = 0
    critical_count = 0
    critical_delayed = 0
    variances: list[float] = []

    discipline_stats: dict[str, dict[str, float]] = {}

    milestones: list[dict[str, Any]] = []
    at_risk: list[dict[str, Any]] = []

    now = datetime.now(tz=timezone.utc)

    for act in activities:
        pct = act.actual_percent_complete if act.actual_percent_complete is not None else act.percent_complete_plan
        disc = act.discipline or "General"
        if disc not in discipline_stats:
            discipline_stats[disc] = {"total": 0, "completed": 0, "sum_pct": 0.0, "delayed": 0}
        discipline_stats[disc]["total"] += 1
        discipline_stats[disc]["sum_pct"] += pct

        is_critical = act.is_critical or (act.total_float_days is not None and act.total_float_days <= 0.0)
        if is_critical:
            critical_count += 1

        is_milestone = "MIL" in act.activity_id or "milestone" in act.activity_name.lower() or act.original_duration_days == 0
        if is_milestone:
            status_label = "On Track"
            if pct < 100 and act.planned_finish and act.planned_finish < now:
                status_label = "Delayed"
            elif pct >= 100:
                status_label = "Completed"
            milestones.append({
                "activity_id": act.activity_id,
                "name": act.activity_name,
                "target_date": act.planned_finish.strftime("%Y-%m-%d") if act.planned_finish else "N/A",
                "status": status_label,
                "progress_pct": round(pct, 1),
            })

        # Variance calculation
        act_var = 0.0
        if act.actual_finish and act.planned_finish:
            act_var = (act.actual_finish - act.planned_finish).total_seconds() / 86400.0
            variances.append(act_var)
        elif act.planned_finish and act.planned_finish < now and pct < 100:
            act_var = (now - act.planned_finish).total_seconds() / 86400.0
            variances.append(act_var)

        if pct >= 100:
            completed += 1
            discipline_stats[disc]["completed"] += 1
        elif pct > 0:
            in_progress += 1
        else:
            not_started += 1

        if act_var > 0.5:
            delayed += 1
            discipline_stats[disc]["delayed"] += 1
            if is_critical:
                critical_delayed += 1
            at_risk.append({
                "activity_id": act.activity_id,
                "name": act.activity_name,
                "discipline": disc,
                "variance_days": round(act_var, 1),
                "total_float": act.total_float_days or 0.0,
                "is_critical": is_critical,
                "progress_pct": round(pct, 1),
            })

    at_risk.sort(key=lambda x: (x["is_critical"], x["variance_days"]), reverse=True)

    avg_progress = sum(
        (a.actual_percent_complete if a.actual_percent_complete is not None else a.percent_complete_plan)
        for a in activities
    ) / total_activities

    mean_var = sum(variances) / len(variances) if variances else 0.0

    # Discipline summaries
    disc_summary = {}
    for d, s in discipline_stats.items():
        disc_summary[d] = {
            "total_activities": int(s["total"]),
            "completed": int(s["completed"]),
            "avg_progress_pct": round(s["sum_pct"] / max(s["total"], 1), 1),
            "delayed_activities": int(s["delayed"]),
        }

    return {
        "total_activities": total_activities,
        "overall_progress_pct": round(avg_progress, 1),
        "completed_count": completed,
        "in_progress_count": in_progress,
        "not_started_count": not_started,
        "delayed_count": delayed,
        "critical_count": critical_count,
        "critical_delayed_count": critical_delayed,
        "mean_schedule_variance_days": round(mean_var, 1),
        "milestone_health": milestones,
        "top_at_risk_activities": at_risk[:6],
        "discipline_health": disc_summary,
    }
