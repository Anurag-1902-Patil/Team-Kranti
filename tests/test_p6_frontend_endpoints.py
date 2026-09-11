"""
Integration tests for Part C P6-Style Frontend Backend Endpoints.
Covers:
1. GET /api/v1/schedule/gantt (WBS hierarchy, dependencies, float, critical path)
2. GET /api/v1/updates/feed (Update Center aggregated feed)
3. No double-counting verification (accepting a review item updates both review queue and update center feed)
4. GET /api/v1/analysis/delays (Filtered delay analytics, trend, major delay register)
5. POST /api/v1/search/parse-filter (Structured filter parsing & navigation suggestion)
6. GET /api/v1/schedule/activities/{id}/detail (Unified 6-section activity detail)
"""

import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db.models import (
    ActivityDependency,
    MatchStatusEnum,
    PlanActivity,
    ProgressEvent,
    SourceTypeEnum,
)

IST = timezone(timedelta(hours=5, minutes=30))


def test_gantt_endpoint(test_client: TestClient, db_session):
    """Test Part C #1: Gantt endpoint returns WBS tree and dependency edges."""
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=IST)

    act1 = PlanActivity(
        activity_id="GANTT-ACT-1",
        activity_name="Excavate foundation trench",
        discipline="civil",
        project_id="TEST",
        wbs_code="WBS-1.1",
        wbs_name="Civil Works",
        planned_start=t0,
        planned_finish=t0 + timedelta(days=5),
        original_duration_days=5.0,
        percent_complete_plan=100.0,
        actual_percent_complete=100.0,
        total_float_days=0.0,
        is_critical=True,
    )
    act2 = PlanActivity(
        activity_id="GANTT-ACT-2",
        activity_name="Pour lean concrete mudmat",
        discipline="civil",
        project_id="TEST",
        wbs_code="WBS-1.1",
        wbs_name="Civil Works",
        planned_start=t0 + timedelta(days=5),
        planned_finish=t0 + timedelta(days=8),
        original_duration_days=3.0,
        percent_complete_plan=50.0,
        actual_percent_complete=50.0,
        total_float_days=0.0,
        is_critical=True,
    )
    dep = ActivityDependency(
        predecessor_activity_id="GANTT-ACT-1",
        successor_activity_id="GANTT-ACT-2",
        dependency_type="FS",
        lag_days=0.0,
    )
    db_session.add_all([act1, act2, dep])
    db_session.commit()

    resp = test_client.get(
        "/api/v1/schedule/gantt",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] >= 2
    assert "wbs_tree" in data
    assert "dependencies" in data
    assert "summary" in data

    # Find GANTT-ACT-2
    item2 = next((a for a in data["activities"] if a["activity_id"] == "GANTT-ACT-2"), None)
    assert item2 is not None
    assert "GANTT-ACT-1" in item2["predecessors"]
    assert item2["is_critical"] is True


def test_updates_feed_and_no_double_counting(test_client: TestClient, db_session):
    """
    Test Part C #2 & User Adjustment #3:
    Verify Update Center feed aggregates items with stable IDs, and confirming an item
    synchronously removes it from both Review Queue and Update Center pending reviews (no double-counting).
    """
    t0 = datetime(2026, 8, 10, 10, 0, tzinfo=IST)
    event_id = uuid.uuid4()

    ev = ProgressEvent(
        id=event_id,
        project_id="TEST",
        activity_description_extracted="Installed 2-inch ball valve on line 102",
        discipline="piping",
        match_status=MatchStatusEnum.low_confidence_review,
        confidence_score=0.62,
        reviewed_by_planner=False,
        extraction_timestamp=t0,
        source_type=SourceTypeEnum.free_text_dpr,
    )
    db_session.add(ev)
    db_session.commit()

    # 1. Check Update Center feed
    resp1 = test_client.get(
        "/api/v1/updates/feed",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp1.status_code == 200
    feed1 = resp1.json()

    # Find the newly added item by its stable ID
    stable_id = f"rev_{event_id}"
    matched_item = next((i for i in feed1["items"] if i["id"] == stable_id), None)
    assert matched_item is not None
    assert matched_item["source_type"] == "review_queue"
    assert matched_item["target_route"] == f"/review?highlight={event_id}"
    initial_pending = feed1["summary"]["pending_reviews"]
    assert initial_pending >= 1

    # 2. Resolve the item in Review Queue via accept endpoint
    accept_resp = test_client.post(
        f"/api/v1/review/{event_id}/accept",
        headers={"Authorization": "Bearer test-token"},
        json={"notes": "Confirmed by site lead"},
    )
    assert accept_resp.status_code == 200

    # 3. Check Update Center feed again — MUST reflect resolution without double-counting
    resp2 = test_client.get(
        "/api/v1/updates/feed",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp2.status_code == 200
    feed2 = resp2.json()

    # The item MUST NOT be in review queue items anymore
    resolved_item = next((i for i in feed2["items"] if i["id"] == stable_id), None)
    assert resolved_item is None
    assert feed2["summary"]["pending_reviews"] == initial_pending - 1


def test_delay_analytics_filtered_endpoint(test_client: TestClient, db_session):
    """Test Part C #3: Delay analytics endpoint supports server-side filters and returns trend/register."""
    resp = test_client.get(
        "/api/v1/analysis/delays?discipline=piping",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "kpis" in data
    assert "trend" in data
    assert "major_delays" in data
    assert "cause_breakdown" in data
    assert data["kpis"]["total_delay_days"] >= 0


def test_search_parse_filter_endpoint(test_client: TestClient, db_session):
    """Test Part C #4: Search parse-filter returns inspectable filter object."""
    resp = test_client.post(
        "/api/v1/search/parse-filter",
        headers={"Authorization": "Bearer test-token"},
        json={"query": "delayed piping activities in Area B"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "filters" in data
    assert data["filters"]["discipline"] == "piping"
    assert data["filters"]["is_delayed"] is True
    assert "explanation" in data
    assert "suggested_route" in data
    assert "/schedule" in data["suggested_route"]


def test_activity_detail_aggregate_endpoint(test_client: TestClient, db_session):
    """Test Part C #5: Unified activity detail returns all 6 sections in one payload."""
    t0 = datetime(2026, 8, 1, 8, 0, tzinfo=IST)
    act = PlanActivity(
        activity_id="UNIFIED-ACT-101",
        activity_name="Install crude transfer pump P-101",
        discipline="mechanical",
        project_id="TEST",
        wbs_code="WBS-2.1",
        wbs_name="Mechanical Pumping Station",
        planned_start=t0,
        planned_finish=t0 + timedelta(days=7),
        original_duration_days=7.0,
        percent_complete_plan=60.0,
        actual_percent_complete=60.0,
        total_float_days=2.0,
        is_critical=False,
    )
    db_session.add(act)
    db_session.commit()

    resp = test_client.get(
        "/api/v1/schedule/activities/UNIFIED-ACT-101/detail",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "identity" in data
    assert data["identity"]["activity_id"] == "UNIFIED-ACT-101"
    assert "schedule" in data
    assert "progress" in data
    assert "intelligence" in data
    assert "risk" in data
    assert "explainability_strip" in data["risk"]
    assert "evidence_breadcrumb" in data["intelligence"]
    assert "audit" in data
