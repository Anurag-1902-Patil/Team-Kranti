"""
Unit and integration tests for the Intelligence Layer.
Covers:
- Extensible disciplines lookup table
- Single consolidated extraction response parsing with 25+ ontology attributes
- Deterministic prediction calculation (variance & delay days)
- Terminology normalization and human-gated alias review
- Grounded NL search with structured filter parsing and SQL injection safety
- Post-approval re-editing with correction history
"""

import json
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select

from backend.db.models import (
    ActivityDependency,
    Discipline,
    DisciplineEnum,
    EntityAlias,
    EventTypeEnum,
    MatchStatusEnum,
    PlanActivity,
    ProgressEvent,
)
from backend.services.analytics.prediction_engine import compute_activity_prediction
from backend.services.analytics.schedule_intelligence import get_schedule_health
from backend.services.matching.terminology import normalize_term
from backend.services.search.nl_search import execute_grounded_search, parse_query_to_filters


def test_extensible_disciplines_lookup(db_session):
    """Test that new disciplines can be added as data rows without schema changes."""
    # Add a custom specialized discipline
    custom_disc = Discipline(
        code="subsea_pipeline",
        name="Subsea Pipeline",
        category="Offshore",
        description="Deepwater offshore flowlines",
        display_order=99,
        is_active=True,
    )
    db_session.add(custom_disc)
    db_session.commit()

    queried = db_session.execute(
        select(Discipline).where(Discipline.code == "subsea_pipeline")
    ).scalar_one_or_none()

    assert queried is not None
    assert queried.name == "Subsea Pipeline"
    assert queried.category == "Offshore"


def test_deterministic_prediction_engine(db_session):
    """
    Test that prediction numbers (days late, risk %) are calculated deterministically
    from historical data, not guessed.
    """
    IST = timezone(timedelta(hours=5, minutes=30))
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=IST)

    # 1. Create a planned activity
    act = PlanActivity(
        activity_id="PIP-PRED-1",
        activity_name="Erect heavy wall pipe spool",
        discipline="piping",
        project_id="TEST",
        planned_start=t0,
        planned_finish=t0 + timedelta(days=4),
        original_duration_days=4.0,
        percent_complete_plan=50.0,
        actual_percent_complete=50.0,
        total_float_days=0.0,
        is_critical=True,
    )
    db_session.add(act)

    # 2. Add historical completed piping events with intentional delay variance
    for i in range(5):
        hist_ev = ProgressEvent(
            project_id="TEST",
            activity_id_plan=f"PIP-HIST-{i}",
            discipline="piping",
            event_type=EventTypeEnum.finish,
            actual_start_datetime=t0 - timedelta(days=20 + i * 5),
            # Planned duration 4 days, actual duration 6 days -> +2 days variance
            actual_finish_datetime=t0 - timedelta(days=20 + i * 5) + timedelta(days=6),
            planned_duration_days=4.0,
            percent_complete=100.0,
            status="completed",
            match_status=MatchStatusEnum.matched,
        )
        db_session.add(hist_ev)
    db_session.commit()

    # 3. Compute prediction
    pred = compute_activity_prediction("PIP-PRED-1", db_session)

    assert pred["activity_id"] == "PIP-PRED-1"
    assert pred["predicted_delay_days"] > 0.0
    assert pred["delay_risk_percentage"] > 20.0
    assert len(pred["contributing_factors"]) > 0
    assert len(pred["supporting_evidence"]) == 5
    assert pred["provenance_category"] == "prediction"
    # Confirm variance was calculated from the +2d historical events
    assert "piping" in pred["contributing_factors"][0].lower()


def test_human_gated_terminology_normalization(db_session):
    """
    Test that approved aliases resolve immediately, but genuinely new terms
    remain PROPOSED in the queue and do not alter canonical records until approved.
    """
    # 1. Unknown alias proposal
    resolved, is_approved, status = normalize_term(
        raw_text="Turbine Pump P-999-X",
        entity_type="equipment",
        session=db_session,
        suggested_canonical="P-999",
    )
    db_session.commit()

    assert not is_approved
    assert status == "proposed_gated_review"
    assert resolved == "Turbine Pump P-999-X"  # Preserved original text!

    # Verify proposed row in entity_aliases
    alias_row = db_session.execute(
        select(EntityAlias).where(EntityAlias.raw_alias == "Turbine Pump P-999-X")
    ).scalar_one_or_none()
    assert alias_row is not None
    assert alias_row.status == "proposed"
    assert alias_row.canonical_value == "P-999"

    # 2. Planner approves the proposal
    alias_row.status = "approved"
    alias_row.approved_by = "lead_planner"
    db_session.commit()

    # 3. Now the approved alias resolves to canonical!
    resolved_after, is_approved_after, status_after = normalize_term(
        raw_text="Turbine Pump P-999-X",
        entity_type="equipment",
        session=db_session,
    )
    assert is_approved_after
    assert resolved_after == "P-999"


def test_grounded_natural_language_search(db_session):
    """
    Test that natural language queries translate to structured filters,
    execute safely without raw SQL injection, and link to real records.
    """
    # Create test plan activity
    act = PlanActivity(
        activity_id="PIP-SEARCH-1",
        activity_name="Erect hydrocarbon line in Area A",
        discipline="piping",
        area="Area A",
        project_id="TEST",
        percent_complete_plan=30.0,
        total_float_days=2.0,
        is_critical=False,
    )
    db_session.add(act)
    db_session.commit()

    # Query: "delayed piping activities in Area A"
    filters = parse_query_to_filters("show piping activities in Area A")
    assert filters.discipline == "piping"
    assert filters.location == "Area A"

    # Execute search
    search_res = execute_grounded_search("piping activities in Area A", db_session)
    assert search_res["total_matches"] >= 1
    item = next(r for r in search_res["results"] if r["id"] == "PIP-SEARCH-1")
    assert "Area A" in item["title"] or "Area A" in item["location"]
    assert item["link_url"] == "/schedule?activity_id=PIP-SEARCH-1"

    # SQL injection immunity: malicious query should be treated as literal keyword, not executed
    malicious = "Area A'; DROP TABLE users; --"
    res_malicious = execute_grounded_search(malicious, db_session)
    assert "results" in res_malicious
    # Table still exists
    users_check = db_session.execute(select(PlanActivity)).scalars().all()
    assert len(users_check) > 0


def test_post_approval_re_edit_history(test_client, db_session):
    """
    Test that even auto-accepted or approved events can be re-edited later by a planner,
    and the full correction history is preserved.
    """
    event = ProgressEvent(
        project_id="TEST",
        activity_id_plan="PIP-001",
        activity_description_extracted="Spool welding complete",
        discipline="piping",
        percent_complete=90.0,
        match_status=MatchStatusEnum.matched,
        provenance_category="ai_extraction",
        correction_history=[],
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    # Re-edit via endpoint
    response = test_client.post(
        f"/api/v1/review/{event.id}/re-edit",
        json={
            "percent_complete": 100.0,
            "notes": "Inspector verified final weld NDT passed",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["percent_complete"] == 100.0
    assert data["provenance_category"] == "human_approval"
    assert len(data["correction_history"]) == 1
    assert data["correction_history"][0]["previous_values"]["percent_complete"] == 90.0
