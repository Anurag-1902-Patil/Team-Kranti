"""
Delay & Bottleneck Intelligence Service.
Reference: SIH26122 §1.10.

Analyzes delay causes across 12 standard categories:
material, manpower, equipment, design, approval, weather, access, safety,
quality_rework, dependency, contractor, logistics, unknown.
"""

from typing import Any
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import PlanActivity, ProgressEvent


STANDARD_DELAY_CATEGORIES = [
    "material", "manpower", "equipment", "design", "approval",
    "weather", "access", "safety", "quality_rework", "dependency",
    "contractor", "logistics", "unknown"
]


def get_delay_analytics(session: Session) -> dict[str, Any]:
    """
    Compute delay category breakdown, bottleneck areas, recurring blockers,
    and impacted contractor rankings.
    """
    events = session.execute(select(ProgressEvent)).scalars().all()
    activities = session.execute(select(PlanActivity)).scalars().all()

    category_counts: dict[str, int] = {cat: 0 for cat in STANDARD_DELAY_CATEGORIES}
    category_duration_impact: dict[str, float] = {cat: 0.0 for cat in STANDARD_DELAY_CATEGORIES}

    discipline_delays: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    contractor_delays: dict[str, dict[str, Any]] = defaultdict(lambda: {"event_count": 0, "total_days": 0.0, "primary_cause": "unknown"})
    bottleneck_locations: dict[str, dict[str, Any]] = defaultdict(lambda: {"delayed_events": 0, "blockers": []})
    blocker_frequencies: dict[str, int] = defaultdict(int)

    for ev in events:
        delay_cat = ev.delay_category or ("unknown" if (ev.delay_status == "delayed" or ev.delay_reason) else None)
        if not delay_cat and ev.blocker_description:
            # Infer category from blocker text keywords
            b_lower = ev.blocker_description.lower()
            if any(k in b_lower for k in ["gasket", "spool", "material", "cement", "pipe", "cable", "steel"]):
                delay_cat = "material"
            elif any(k in b_lower for k in ["manpower", "welder", "crew", "absent", "strike", "labor"]):
                delay_cat = "manpower"
            elif any(k in b_lower for k in ["crane", "rig", "pump", "generator", "equipment", "breakdown"]):
                delay_cat = "equipment"
            elif any(k in b_lower for k in ["rain", "monsoon", "weather", "flood"]):
                delay_cat = "weather"
            elif any(k in b_lower for k in ["permit", "approval", "clearance", "noc"]):
                delay_cat = "approval"
            else:
                delay_cat = "unknown"

        if delay_cat:
            cat_key = delay_cat.lower().replace(" ", "_")
            if cat_key not in category_counts:
                cat_key = "unknown"
            category_counts[cat_key] += 1

            # Estimate duration impact
            impact_days = 2.0
            if ev.actual_finish_datetime and ev.actual_start_datetime:
                dur = (ev.actual_finish_datetime - ev.actual_start_datetime).total_seconds() / 86400.0
                planned = ev.planned_duration_days or 1.0
                impact_days = max(1.0, dur - planned)
            category_duration_impact[cat_key] += round(impact_days, 1)

            # Discipline breakdown
            disc = str(ev.discipline.value if hasattr(ev.discipline, "value") else ev.discipline)
            discipline_delays[disc][cat_key] += 1

            # Contractor breakdown
            c_name = ev.contractor_name or "Internal Direct Crew"
            contractor_delays[c_name]["event_count"] += 1
            contractor_delays[c_name]["total_days"] += round(impact_days, 1)
            contractor_delays[c_name]["primary_cause"] = cat_key

            # Bottleneck location
            loc = ev.location_area or ev.location_reference or "General Right of Way"
            bottleneck_locations[loc]["delayed_events"] += 1
            if ev.blocker_description and ev.blocker_description not in bottleneck_locations[loc]["blockers"]:
                bottleneck_locations[loc]["blockers"].append(ev.blocker_description)

        if ev.blocker_description:
            blocker_frequencies[ev.blocker_description] += 1

    # Format category breakdown
    total_delayed_events = sum(category_counts.values())
    categories_formatted = []
    for cat, count in category_counts.items():
        pct = round((count / max(total_delayed_events, 1)) * 100, 1)
        categories_formatted.append({
            "cause": cat,
            "category": cat,
            "label": cat.replace("_", " ").title(),
            "display_name": cat.replace("_", " ").title(),
            "count": count,
            "event_count": count,
            "percentage": pct,
            "estimated_days_lost": round(category_duration_impact[cat], 1),
        })
    categories_formatted.sort(key=lambda x: x["count"], reverse=True)

    # Top recurring blockers
    recurring_blockers = [
        {
            "description": b,
            "blocker": b,
            "occurrences": count,
            "frequency": count,
            "latest_reported": "Active",
        }
        for b, count in sorted(blocker_frequencies.items(), key=lambda x: x[1], reverse=True)[:8]
    ]

    # Bottleneck areas
    bottleneck_list = [
        {
            "area": loc,
            "location": loc,
            "delayed_events": data["delayed_events"],
            "delayed_events_count": data["delayed_events"],
            "active_blockers": len(data["blockers"]),
            "sample_blockers": data["blockers"][:3],
        }
        for loc, data in sorted(bottleneck_locations.items(), key=lambda x: x[1]["delayed_events"], reverse=True)[:6]
    ]

    # Contractor rankings
    contractor_totals = defaultdict(int)
    for ev in events:
        c_name = ev.contractor_name or "Internal Direct Crew"
        contractor_totals[c_name] += 1

    contractor_rankings = [
        {
            "contractor": c,
            "total_events": contractor_totals.get(c, data["event_count"]),
            "delay_events": data["event_count"],
            "delayed_activities": data["event_count"],
            "delay_ratio": round(data["event_count"] / max(contractor_totals.get(c, data["event_count"]), 1), 2),
            "avg_variance_factor": round(1.0 + (data["total_days"] / max(data["event_count"], 1) / 10.0), 2),
            "total_impact_days": round(data["total_days"], 1),
            "primary_delay_cause": data["primary_cause"].replace("_", " ").title(),
        }
        for c, data in sorted(contractor_delays.items(), key=lambda x: x[1]["total_days"], reverse=True)[:6]
    ]

    return {
        "total_delay_events": total_delayed_events,
        "cause_breakdown": categories_formatted,
        "categories": categories_formatted,
        "bottlenecks": bottleneck_list,
        "bottleneck_locations": bottleneck_list,
        "recurring_blockers": recurring_blockers,
        "contractor_rankings": contractor_rankings,
        "discipline_delays": dict(discipline_delays),
    }
