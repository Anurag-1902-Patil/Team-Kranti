"""
conftest.py — Shared fixtures for all tests.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite in-memory for tests — no Postgres required to run tests
TEST_DB_URL = "sqlite:///./test_sih26122.db"


@pytest.fixture(scope="session", autouse=True)
def set_test_env(monkeypatch=None):
    """Set test environment variables before importing the app."""
    import os
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_sih26122.db")
    os.environ.setdefault("DATABASE_URL_SYNC", TEST_DB_URL)
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
    os.environ.setdefault("REVIEWER_TOKEN", "test-token")
    os.environ.setdefault("WHATSAPP_APP_SECRET", "test-secret")
    os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify")
    os.environ.setdefault("GROQ_API_KEY", "")  # Tests mock LLM calls
    os.environ.setdefault("MATCH_AUTO_ACCEPT_THRESHOLD", "0.85")
    os.environ.setdefault("MATCH_REVIEW_THRESHOLD", "0.55")
    os.environ.setdefault("QDRANT_URL", ":memory:")
    os.environ.setdefault("LOCAL_LLM_MODEL", "qwen3:8b")
    os.environ.setdefault("GROQ_MODEL_FALLBACK", "qwen/qwen3-32b")


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh SQLite database for each test."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from sqlalchemy import create_engine
    from backend.db.models import Base

    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Return a SQLAlchemy session for a test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_client():
    """Return a FastAPI TestClient with test token header."""
    from backend.main import app
    client = TestClient(app, headers={"Authorization": "Bearer test-token"})
    return client


@pytest.fixture
def sample_plan_activities(db_session):
    """Insert a set of synthetic plan activities into the test DB."""
    from backend.db.models import PlanActivity
    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    activities = [
        PlanActivity(activity_id="PIP-001", activity_name="Fabricate spool SP-247 (Line 24\"-XX)", discipline="piping", project_id="TEST", planned_start=datetime(2026,8,1,tzinfo=IST), planned_finish=datetime(2026,8,4,tzinfo=IST), original_duration_days=3),
        PlanActivity(activity_id="PIP-002", activity_name="Erect Line 24\"-XX at chainage 12+450", discipline="piping", project_id="TEST", planned_start=datetime(2026,8,4,tzinfo=IST), planned_finish=datetime(2026,8,9,tzinfo=IST), original_duration_days=5),
        PlanActivity(activity_id="CIV-001", activity_name="Excavate foundation pit for Pump P-101 (Area A)", discipline="civil", project_id="TEST", planned_start=datetime(2026,8,1,tzinfo=IST), planned_finish=datetime(2026,8,3,tzinfo=IST), original_duration_days=2),
        PlanActivity(activity_id="ELE-001", activity_name="Pull 3Cx150mm² cable from MCC-1 to Pump P-101 (Route R-12)", discipline="electrical", project_id="TEST", planned_start=datetime(2026,8,8,tzinfo=IST), planned_finish=datetime(2026,8,10,tzinfo=IST), original_duration_days=2),
    ]
    for a in activities:
        db_session.add(a)
    db_session.commit()
    return activities
