"""
seed_schedule.py — Load synthetic XER and sender profiles into the database.

Run this once after `docker-compose up -d` and `alembic upgrade head`:

    cd backend
    python ../scripts/seed_schedule.py

What it does:
  1. Parses data/synthetic/sample_schedule.xer → inserts plan_activities rows
  2. Pre-computes sentence-transformer embeddings and loads into semantic_matcher
  3. Indexes all activities into ChromaDB
  4. Inserts sender_profiles from data/synthetic/sender_profiles.json
"""

import json
import sys
import os
from pathlib import Path

# Ensure backend is on the Python path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Load env
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.core.config import get_settings
from backend.db.models import Base, PlanActivity, SenderProfile

settings = get_settings()


def main():
    print("=" * 60)
    print("SIH26122 — Schedule Seed Script")
    print("=" * 60)

    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    # -------------------------------------------------------------------------
    # 1. Create tables if not already created (Alembic should have done this)
    # -------------------------------------------------------------------------
    Base.metadata.create_all(engine)
    print("✓ Tables verified")

    # -------------------------------------------------------------------------
    # 2. Load synthetic XER
    # -------------------------------------------------------------------------
    xer_path = ROOT / "data" / "synthetic" / "sample_schedule.xer"

    if not xer_path.exists():
        print(f"⚠ XER file not found at {xer_path}")
        print("  Creating a synthetic XER file now...")
        _create_synthetic_xer(xer_path)

    try:
        from backend.services.scheduling.xer_parser import load_xer

        activities = load_xer(xer_path, project_id=settings.project_id)
        print(f"✓ Parsed {len(activities)} activities from XER")
    except Exception as exc:
        print(f"⚠ XER parse failed ({exc}). Using hardcoded synthetic activities.")
        activities = _get_hardcoded_activities(settings.project_id)

    # Upsert into plan_activities
    inserted = 0
    skipped = 0
    for act_data in activities:
        existing = session.execute(
            select(PlanActivity).where(
                PlanActivity.activity_id == act_data["activity_id"]
            )
        ).scalar_one_or_none()

        if existing:
            skipped += 1
            continue

        activity = PlanActivity(**act_data)
        session.add(activity)
        inserted += 1

    session.commit()
    print(f"✓ Inserted {inserted} activities, skipped {skipped} existing")

    # -------------------------------------------------------------------------
    # 3. Build semantic embedding index
    # -------------------------------------------------------------------------
    print("  Loading sentence-transformer model (first run downloads ~90MB)...")
    all_activities = session.execute(
        select(PlanActivity.activity_id, PlanActivity.activity_name)
    ).all()
    activity_index = {row.activity_id: row.activity_name for row in all_activities}

    from backend.services.matching.semantic_matcher import load_activity_embeddings
    load_activity_embeddings(activity_index)
    print(f"✓ Embedding index loaded ({len(activity_index)} activities)")

    # -------------------------------------------------------------------------
    # 4. Index plan activities in ChromaDB
    # -------------------------------------------------------------------------
    from backend.services.institutional_memory.qdrant_store import index_plan_activity

    for row in all_activities:
        pa = session.execute(
            select(PlanActivity).where(PlanActivity.activity_id == row.activity_id)
        ).scalar_one()
        try:
            embedding_id = index_plan_activity(
                activity_id=row.activity_id,
                activity_name=row.activity_name,
                discipline=pa.discipline or "unknown",
                project_id=settings.project_id,
            )
            pa.embedding_id = embedding_id
        except Exception as exc:
            print(f"  ⚠ ChromaDB index failed for {row.activity_id}: {exc}")

    session.commit()
    print(f"✓ ChromaDB indexed {len(all_activities)} activities")

    # -------------------------------------------------------------------------
    # 5. Load sender profiles
    # -------------------------------------------------------------------------
    profiles_path = ROOT / "data" / "synthetic" / "sender_profiles.json"
    if profiles_path.exists():
        profiles = json.loads(profiles_path.read_text())
        for p in profiles:
            existing = session.execute(
                select(SenderProfile).where(SenderProfile.sender_id == p["sender_id"])
            ).scalar_one_or_none()
            if not existing:
                session.add(SenderProfile(**p))
        session.commit()
        print(f"✓ Loaded {len(profiles)} sender profiles")
    else:
        print("⚠ sender_profiles.json not found — skipping")

    session.close()

    print()
    print("=" * 60)
    print("Seed complete! System is ready for demo.")
    print(f"  Plan activities: {len(all_activities)}")
    print("  Run: python scripts/run_demo.py")
    print("=" * 60)


def _create_synthetic_xer(path: Path) -> None:
    """
    Create a minimal synthetic XER file if the actual file is missing.
    This is a fallback — the real XER is committed to the repo.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write a minimal XER skeleton — PyP6XER can parse this format
    content = _SYNTHETIC_XER_CONTENT
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ Created synthetic XER at {path}")


def _get_hardcoded_activities(project_id: str) -> list[dict]:
    """
    Fallback: return hardcoded synthetic activities if XER parsing fails.
    These match the illustrative L5/L6 activities from §2.1 of the project context.
    """
    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    base = datetime(2026, 8, 1, tzinfo=IST)

    def dt(days): return base + timedelta(days=days)

    return [
        # Piping
        {"activity_id": "PIP-001", "activity_name": "Fabricate spool SP-247 (Line 24\"-XX, N12→N15)", "discipline": "piping", "planned_start": dt(0), "planned_finish": dt(3), "original_duration_days": 3, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "PIP-002", "activity_name": "Erect Line 24\"-XX at chainage 12+450", "discipline": "piping", "planned_start": dt(3), "planned_finish": dt(8), "original_duration_days": 5, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "PIP-003", "activity_name": "Hydrotest Line 24\"-XX (N12 to N20)", "discipline": "piping", "planned_start": dt(9), "planned_finish": dt(10), "original_duration_days": 1, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "PIP-004", "activity_name": "Weld joint at flange node N12", "discipline": "piping", "planned_start": dt(2), "planned_finish": dt(3), "original_duration_days": 1, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        # Civil
        {"activity_id": "CIV-001", "activity_name": "Excavate foundation pit for Pump P-101 (Area A, Grid 12-13)", "discipline": "civil", "planned_start": dt(0), "planned_finish": dt(2), "original_duration_days": 2, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "CIV-002", "activity_name": "Pour concrete foundation for Pump P-101", "discipline": "civil", "planned_start": dt(3), "planned_finish": dt(5), "original_duration_days": 2, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "CIV-003", "activity_name": "Backfill and compact around Pump P-101 foundation", "discipline": "civil", "planned_start": dt(10), "planned_finish": dt(11), "original_duration_days": 1, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "CIV-004", "activity_name": "Construct access road to Process Area B", "discipline": "civil", "planned_start": dt(0), "planned_finish": dt(5), "original_duration_days": 5, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        # Electrical
        {"activity_id": "ELE-001", "activity_name": "Pull 3Cx150mm² cable from MCC-1 to Pump P-101 (Route R-12)", "discipline": "electrical", "planned_start": dt(7), "planned_finish": dt(9), "original_duration_days": 2, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "ELE-002", "activity_name": "Terminate cables at MCC-1 and Motor terminal box", "discipline": "electrical", "planned_start": dt(10), "planned_finish": dt(11), "original_duration_days": 1, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "ELE-003", "activity_name": "Install conduit from MCC-1 along Route R-12", "discipline": "electrical", "planned_start": dt(5), "planned_finish": dt(7), "original_duration_days": 2, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        # Instrumentation
        {"activity_id": "INS-001", "activity_name": "Calibrate flow transmitter FT-501 (Line 12\"-YY)", "discipline": "instrumentation", "planned_start": dt(11), "planned_finish": dt(12), "original_duration_days": 0.5, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "INS-002", "activity_name": "Install pressure gauge at pump P-101 discharge", "discipline": "instrumentation", "planned_start": dt(8), "planned_finish": dt(9), "original_duration_days": 0.5, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        # HSE
        {"activity_id": "HSE-001", "activity_name": "Conduct weekly HSE audit for piping work in Process Area B", "discipline": "hse", "planned_start": dt(7), "planned_finish": dt(7), "original_duration_days": 0.5, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "HSE-002", "activity_name": "Toolbox talk for hot work permit compliance", "discipline": "hse", "planned_start": dt(0), "planned_finish": dt(0), "original_duration_days": 0.25, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        # Mechanical
        {"activity_id": "MEC-001", "activity_name": "Set and level pump P-101 on foundation (Area A)", "discipline": "mechanical", "planned_start": dt(6), "planned_finish": dt(7), "original_duration_days": 1, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "MEC-002", "activity_name": "Alignment check for pump P-101 motor coupling", "discipline": "mechanical", "planned_start": dt(8), "planned_finish": dt(8), "original_duration_days": 0.5, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        # Structural
        {"activity_id": "STR-001", "activity_name": "Erect structural steel framework for pipe support rack", "discipline": "structural", "planned_start": dt(0), "planned_finish": dt(4), "original_duration_days": 4, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "STR-002", "activity_name": "Paint structural steel anti-corrosion coating", "discipline": "structural", "planned_start": dt(5), "planned_finish": dt(6), "original_duration_days": 1, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
        {"activity_id": "MIL-001", "activity_name": "Mechanical Completion of Pump P-101 package", "discipline": "mechanical", "planned_start": dt(13), "planned_finish": dt(13), "original_duration_days": 0, "percent_complete_plan": 0, "project_id": project_id, "is_field_confirmed": False},
    ]


# Minimal synthetic XER content for PyP6XER
_SYNTHETIC_XER_CONTENT = """ERMHDR\t22.12\t2026-09-01\tProject\tadmin\tadmin\t\t\t\tChinese
%T\tOBSMEMO
%F\tobsmemo_id\tmemo_type\tobject_type\tobject_id\tmemo_text\tupdate_date
%T\tPROJECT
%F\tproj_id\tproj_short_name\tproj_name\tcreate_date\tplan_start_date
%R\t1\tSIH2026\tOIL India Pipeline Demo 2026\t2026-08-01 00:00\t2026-08-01 00:00
%T\tTASK
%F\ttask_id\tproj_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\ttarget_drtn_hr_cnt\tphys_complete_pct
%R\t101\t1\tPIP-001\tFabricate spool SP-247 (Line 24"-XX, N12->N15)\t2026-08-01 08:00\t2026-08-04 17:00\t24\t0
%R\t102\t1\tPIP-002\tErect Line 24"-XX at chainage 12+450\t2026-08-04 08:00\t2026-08-09 17:00\t40\t0
%R\t103\t1\tPIP-003\tHydrotest Line 24"-XX (N12 to N20)\t2026-08-10 08:00\t2026-08-11 17:00\t8\t0
%R\t104\t1\tPIP-004\tWeld joint at flange node N12\t2026-08-03 08:00\t2026-08-04 17:00\t8\t0
%R\t201\t1\tCIV-001\tExcavate foundation pit for Pump P-101 (Area A, Grid 12-13)\t2026-08-01 08:00\t2026-08-03 17:00\t16\t0
%R\t202\t1\tCIV-002\tPour concrete foundation for Pump P-101\t2026-08-04 08:00\t2026-08-06 17:00\t16\t0
%R\t203\t1\tCIV-003\tBackfill and compact around Pump P-101 foundation\t2026-08-11 08:00\t2026-08-12 17:00\t8\t0
%R\t204\t1\tCIV-004\tConstruct access road to Process Area B\t2026-08-01 08:00\t2026-08-06 17:00\t40\t0
%R\t301\t1\tELE-001\tPull 3Cx150mm2 cable from MCC-1 to Pump P-101 (Route R-12)\t2026-08-08 08:00\t2026-08-10 17:00\t16\t0
%R\t302\t1\tELE-002\tTerminate cables at MCC-1 and Motor terminal box\t2026-08-11 08:00\t2026-08-12 17:00\t8\t0
%R\t303\t1\tELE-003\tInstall conduit from MCC-1 along Route R-12\t2026-08-06 08:00\t2026-08-08 17:00\t16\t0
%R\t401\t1\tINS-001\tCalibrate flow transmitter FT-501 (Line 12"-YY)\t2026-08-12 08:00\t2026-08-12 12:00\t4\t0
%R\t402\t1\tINS-002\tInstall pressure gauge at pump P-101 discharge\t2026-08-09 08:00\t2026-08-09 12:00\t4\t0
%R\t501\t1\tHSE-001\tConduct weekly HSE audit for piping work in Process Area B\t2026-08-08 08:00\t2026-08-08 12:00\t4\t0
%R\t502\t1\tHSE-002\tToolbox talk for hot work permit compliance\t2026-08-01 07:00\t2026-08-01 09:00\t2\t0
%R\t601\t1\tMEC-001\tSet and level pump P-101 on foundation (Area A)\t2026-08-07 08:00\t2026-08-08 17:00\t8\t0
%R\t602\t1\tMEC-002\tAlignment check for pump P-101 motor coupling\t2026-08-09 08:00\t2026-08-09 12:00\t4\t0
%R\t701\t1\tSTR-001\tErect structural steel framework for pipe support rack\t2026-08-01 08:00\t2026-08-05 17:00\t32\t0
%R\t702\t1\tSTR-002\tPaint structural steel anti-corrosion coating\t2026-08-06 08:00\t2026-08-07 17:00\t8\t0
%R\t801\t1\tMIL-001\tMechanical Completion of Pump P-101 package\t2026-08-14 00:00\t2026-08-14 00:00\t0\t0
%E
"""


if __name__ == "__main__":
    main()
