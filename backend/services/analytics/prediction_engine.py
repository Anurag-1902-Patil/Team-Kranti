"""
Deterministic Prediction Engine for Activity Delays and Completion Dates.
Reference: SIH26122 Architecture §1.5.

HARD RULE: All numbers (predicted delay days, completion date, risk percentage, variance)
are computed mathematically over historical progress_events data. The LLM's role
is strictly limited to narrative summarization of contributing factors without altering numbers.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import ActivityDependency, PlanActivity, ProgressEvent

log = structlog.get_logger(__name__)
settings = get_settings()


def compute_activity_prediction(
    activity_id: str,
    session: Session,
    use_llm_narrative: bool = True,
) -> dict[str, Any]:
    """
    Compute deterministic schedule prediction for an activity.

    Returns:
        {
            "activity_id": str,
            "activity_name": str,
            "discipline": str,
            "planned_start": str,
            "planned_finish": str,
            "predicted_finish": str,
            "predicted_delay_days": float,
            "delay_risk_percentage": float,
            "confidence": float,
            "variance_factor": float,
            "contributing_factors": list[str],
            "supporting_evidence": list[dict],
            "narrative": str,
            "provenance_category": "prediction"
        }
    """
    # 1. Fetch target plan activity
    act = session.execute(
        select(PlanActivity).where(PlanActivity.activity_id == activity_id)
    ).scalar_one_or_none()

    if not act:
        raise ValueError(f"Plan activity '{activity_id}' not found")

    discipline = act.discipline or "general"
    orig_duration = act.original_duration_days or 3.0
    total_float = act.total_float_days or 0.0

    # 2. Historical analysis for this discipline
    hist_events = session.execute(
        select(ProgressEvent).where(
            ProgressEvent.discipline == discipline,
            ProgressEvent.actual_start_datetime.is_not(None),
            ProgressEvent.actual_finish_datetime.is_not(None),
        )
    ).scalars().all()

    variances: list[float] = []
    supporting_evidence: list[dict[str, Any]] = []

    for ev in hist_events[:25]:
        start = ev.actual_start_datetime
        finish = ev.actual_finish_datetime
        if start and finish and finish >= start:
            duration_days = (finish - start).total_seconds() / 86400.0
            planned = ev.planned_duration_days or orig_duration
            var = duration_days - planned
            variances.append(var)
            supporting_evidence.append({
                "event_id": str(ev.id),
                "activity_id_plan": ev.activity_id_plan or "FIELD",
                "actual_duration_days": round(duration_days, 1),
                "planned_duration_days": round(planned, 1),
                "variance_days": round(var, 1),
                "date": finish.strftime("%Y-%m-%d"),
            })

    # Historical average variance
    if variances:
        avg_variance = sum(variances) / len(variances)
        delay_count = sum(1 for v in variances if v > 0.2)
        delay_frequency = delay_count / len(variances)
    else:
        avg_variance = 0.5  # default conservative prior
        delay_frequency = 0.35

    variance_factor = avg_variance / max(orig_duration, 1.0)
    variance_factor = max(-0.2, min(1.5, variance_factor))

    # 3. Check predecessor dependencies
    dep_records = session.execute(
        select(ActivityDependency).where(
            ActivityDependency.successor_activity_id == activity_id
        )
    ).scalars().all()

    predecessor_delay_days = 0.0
    pred_factors: list[str] = []

    for dep in dep_records:
        pred_act = session.execute(
            select(PlanActivity).where(
                PlanActivity.activity_id == dep.predecessor_activity_id
            )
        ).scalar_one_or_none()
        if pred_act and pred_act.planned_finish:
            actual_or_est_finish = pred_act.actual_finish or (
                pred_act.planned_finish + timedelta(days=1.5 if pred_act.percent_complete_plan < 100 else 0)
            )
            p_delay = max(0.0, (actual_or_est_finish - pred_act.planned_finish).total_seconds() / 86400.0)
            if p_delay > 0:
                net_impact = max(0.0, p_delay + dep.lag_days - total_float)
                if net_impact > predecessor_delay_days:
                    predecessor_delay_days = net_impact
                pred_factors.append(
                    f"Predecessor [{pred_act.activity_id}] '{pred_act.activity_name[:40]}' delayed by {round(p_delay, 1)}d (consumed {min(total_float, p_delay)}d float)"
                )

    # 4. Check active blockers from field progress events
    active_blockers = session.execute(
        select(ProgressEvent.blocker_description).where(
            ProgressEvent.activity_id_plan == activity_id,
            ProgressEvent.blocker_description.is_not(None),
        )
    ).scalars().all()

    blocker_penalty_days = 1.5 if active_blockers else 0.0

    # 5. Deterministic calculation of Predicted Finish and Delay Days
    pct = act.actual_percent_complete or act.percent_complete_plan or 0.0
    base_planned_finish = act.planned_finish or datetime.now(tz=timezone.utc) + timedelta(days=orig_duration)
    base_planned_start = act.planned_start or datetime.now(tz=timezone.utc)

    if pct >= 100.0 and act.actual_finish:
        # Already complete
        predicted_finish = act.actual_finish
        predicted_delay_days = max(0.0, (predicted_finish - base_planned_finish).total_seconds() / 86400.0)
        delay_risk = 0.0
    else:
        # Remaining duration with variance & delays applied
        remaining_ratio = max(0.0, (100.0 - pct) / 100.0)
        expected_remaining = orig_duration * remaining_ratio * (1.0 + max(0.0, avg_variance / max(orig_duration, 1.0)))
        total_delay = max(0.0, predecessor_delay_days + (avg_variance * remaining_ratio) + blocker_penalty_days)
        predicted_delay_days = round(total_delay, 1)

        ref_start = act.actual_start or base_planned_start
        predicted_finish = ref_start + timedelta(days=orig_duration + predicted_delay_days)

        # Risk score calculation (0 to 100%)
        risk_score = 15.0
        risk_score += predicted_delay_days * 12.0
        if active_blockers:
            risk_score += 25.0
        if total_float <= 0.0:
            risk_score += 20.0
        elif total_float < 3.0:
            risk_score += 10.0
        risk_score += delay_frequency * 20.0
        delay_risk = round(max(5.0, min(95.0, risk_score)), 1)

    # Confidence calculation based on historical sample size
    n_samples = len(variances)
    confidence = round(min(0.92, 0.60 + 0.04 * min(8, n_samples)), 2)

    # 6. Contributing factors list
    contributing_factors: list[str] = []
    if variances:
        contributing_factors.append(
            f"Discipline '{discipline}' averages {round(avg_variance, 1)}d variance against baseline ({round(delay_frequency * 100)}% historical delay frequency across {n_samples} past events)."
        )
    if pred_factors:
        contributing_factors.extend(pred_factors)
    if active_blockers:
        contributing_factors.append(f"Active site blocker: '{active_blockers[0]}'.")
    if total_float <= 0:
        contributing_factors.append("Critical path activity with zero float protection.")
    elif total_float < 3:
        contributing_factors.append(f"Low total float ({round(total_float, 1)} days remaining).")

    if not contributing_factors:
        contributing_factors.append("Nominal schedule progress aligned with historical baselines.")

    # 7. Professional plain-language narrative
    narrative = (
        f"Activity {act.activity_id} is forecast to finish on {predicted_finish.strftime('%Y-%m-%d')} "
        f"with an estimated {predicted_delay_days} days variance (Delay Risk: {delay_risk}%). "
        f"Primary drivers: {'; '.join(contributing_factors[:2])}."
    )

    return {
        "activity_id": act.activity_id,
        "activity_name": act.activity_name,
        "discipline": discipline,
        "planned_start": base_planned_start.strftime("%Y-%m-%d"),
        "planned_finish": base_planned_finish.strftime("%Y-%m-%d"),
        "predicted_finish": predicted_finish.strftime("%Y-%m-%d"),
        "predicted_delay_days": predicted_delay_days,
        "delay_risk_percentage": delay_risk,
        "confidence": confidence,
        "variance_factor": round(variance_factor, 2),
        "contributing_factors": contributing_factors,
        "supporting_evidence": supporting_evidence[:5],
        "narrative": narrative,
        "provenance_category": "prediction",
    }
