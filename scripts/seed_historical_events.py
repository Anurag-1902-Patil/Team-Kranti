"""
seed_historical_events.py — Generates 3-6 months of rich backdated progress events
and relational entities for SIH26122.

Reference: SIH26122 §1.11.

Generates:
  - Organizations & Contractors (NorthEast PetroWorks, Brahmaputra Infratech, etc.)
  - Equipment records (P-101, P-102, FT-501, MCC-1)
  - Location records (Area A, Area B, CH 12+450, Substation 1)
  - Schedule Activity Dependencies (FS network across Civil, Mechanical, Piping, Electrical)
  - 60+ realistic backdated ProgressEvents with duration variance, delay categories,
    recurring blockers, observed manpower, and full field-level provenance.
  - EntityAliases (approved vocabulary + proposed aliases for reviewer queue).

Run:
    python scripts/seed_historical_events.py
"""

import json
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.core.config import get_settings
from backend.db.models import (
    ActivityDependency,
    Contractor,
    Discipline,
    EntityAlias,
    Equipment,
    EventTypeEnum,
    Location,
    MatchStatusEnum,
    Organization,
    Person,
    PlanActivity,
    ProgressEvent,
    SourceTypeEnum,
)

settings = get_settings()
IST = timezone(timedelta(hours=5, minutes=30))


def main():
    print("=" * 70)
    print("SIH26122 — Historical Synthetic Dataset Seeder")
    print("=" * 70)

    db_url = os.getenv("DATABASE_URL_SYNC", settings.database_url_sync)
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            pass
    except Exception as exc:
        print(f"⚠ Database at {db_url} unreachable ({exc}). Falling back to local SQLite: sqlite:///./sih26122.db")
        db_url = "sqlite:///./sih26122.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})

    from backend.db.models import Base
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Seed Organizations
    print("► Seeding Organizations...")
    org_oil = session.execute(select(Organization).where(Organization.code == "OIL")).scalar_one_or_none()
    if not org_oil:
        org_oil = Organization(code="OIL", name="Oil India Limited", org_type="client")
        session.add(org_oil)

    org_nep = session.execute(select(Organization).where(Organization.code == "NEP")).scalar_one_or_none()
    if not org_nep:
        org_nep = Organization(code="NEP", name="NorthEast PetroWorks Ltd", org_type="main_contractor")
        session.add(org_nep)

    org_bi = session.execute(select(Organization).where(Organization.code == "BIT")).scalar_one_or_none()
    if not org_bi:
        org_bi = Organization(code="BIT", name="Brahmaputra Infratech Pvt Ltd", org_type="subcontractor")
        session.add(org_bi)

    org_api = session.execute(select(Organization).where(Organization.code == "API")).scalar_one_or_none()
    if not org_api:
        org_api = Organization(code="API", name="Assam Power & Instrumentation", org_type="subcontractor")
        session.add(org_api)

    session.commit()
    print("✓ Organizations ready")

    # 2. Seed Contractors
    print("► Seeding Contractors...")
    contractors_data = [
        ("NorthEast PetroWorks", org_nep.id, "Piping & Mechanical Fabrication", "S. Saikia", "+919864011223"),
        ("Brahmaputra Infratech", org_bi.id, "Civil Earthworks & Foundations", "P. Gogoi", "+919864022334"),
        ("Assam Power & Instrumentation", org_api.id, "Electrical & Control Automation", "R. Hazarika", "+919864033445"),
        ("Duliajan Safety Services", org_oil.id, "HSE & Quality Inspection", "M. Baruah", "+919864044556"),
    ]
    contractor_map = {}
    for name, org_id, specialty, contact, phone in contractors_data:
        c_row = session.execute(select(Contractor).where(Contractor.name == name)).scalar_one_or_none()
        if not c_row:
            c_row = Contractor(
                name=name,
                organization_id=org_id,
                trade_specialty=specialty,
                contact_person=contact,
                phone=phone,
                is_active=True,
            )
            session.add(c_row)
            session.flush()
        contractor_map[name] = c_row.id
    session.commit()
    print(f"✓ {len(contractor_map)} Contractors ready")

    # 3. Seed Equipment
    print("► Seeding Equipment...")
    equipment_data = [
        ("P-101", "Crude Booster Pump #1", "pump", "SYS-10", "Area A", "installed"),
        ("P-102", "Crude Booster Pump #2 (Standby)", "pump", "SYS-10", "Area A", "planned"),
        ("FT-501", "Flow Transmitter Line 12\"-YY", "transmitter", "SYS-20", "Area B", "tested"),
        ("MCC-1", "415V Motor Control Center Unit 1", "electrical_panel", "SYS-30", "Substation 1", "installed"),
        ("TK-201", "Crude Surge Tank 5000bbl", "tank", "SYS-40", "Tank Farm", "planned"),
    ]
    for tag, name, eq_type, sys_code, area, status in equipment_data:
        existing_eq = session.execute(select(Equipment).where(Equipment.tag == tag)).scalar_one_or_none()
        if not existing_eq:
            session.add(Equipment(tag=tag, name=name, equipment_type=eq_type, system_code=sys_code, area=area, status=status))
    session.commit()
    print(f"✓ {len(equipment_data)} Equipment records ready")

    # 4. Seed Locations
    print("► Seeding Locations...")
    locations_data = [
        ("Area A", "Pump Station Manifold Area", "Area A", "Unit 1", "CH 0+000", "CH 0+500", "Grid 12-14"),
        ("Area B", "Process & Metering Skid Area", "Area B", "Unit 2", "CH 0+500", "CH 1+200", "Grid 15-18"),
        ("Chainage 12+450", "Pipeline Mainline Section 1", "ROW-1", "Section 1", "CH 12+000", "CH 13+000", "KP 12.45"),
        ("Substation 1", "Electrical Substation & Control Room", "Power Yard", "Substation", None, None, "Grid 01-04"),
    ]
    for code, name, area, unit, ch_start, ch_end, grid in locations_data:
        existing_loc = session.execute(select(Location).where(Location.code == code)).scalar_one_or_none()
        if not existing_loc:
            session.add(Location(code=code, name=name, area=area, unit=unit, chainage_start=ch_start, chainage_end=ch_end, grid_reference=grid))
    session.commit()
    print(f"✓ {len(locations_data)} Locations ready")

    # 5. Seed Activity Dependencies
    print("► Seeding Activity Dependencies (Primavera P6 network)...")
    dependencies_data = [
        ("CIV-001", "CIV-002", "FS", 0.0),  # Pit excavation -> Foundation concrete
        ("CIV-002", "MEC-001", "FS", 1.0),  # Concrete cure -> Set and level pump P-101
        ("MEC-001", "MEC-002", "FS", 0.0),  # Pump placement -> Alignment check
        ("MEC-002", "PIP-001", "SS", 0.0),  # Alignment -> Spool fab
        ("PIP-001", "PIP-002", "FS", 0.0),  # Spool fab -> Spool erection
        ("PIP-002", "PIP-004", "FS", 0.0),  # Erection -> Flange weld
        ("PIP-004", "PIP-003", "FS", 1.0),  # Flange weld -> Hydrotest Line 24"
        ("ELE-003", "ELE-001", "FS", 0.0),  # Conduit install -> Cable pull
        ("ELE-001", "ELE-002", "FS", 0.0),  # Cable pull -> Cable termination
        ("PIP-003", "MIL-001", "FS", 0.0),  # Hydrotest -> Mechanical completion
        ("ELE-002", "MIL-001", "FS", 0.0),  # Electrical termination -> Mechanical completion
    ]
    for pred, succ, dep_type, lag in dependencies_data:
        existing_dep = session.execute(
            select(ActivityDependency).where(
                ActivityDependency.predecessor_activity_id == pred,
                ActivityDependency.successor_activity_id == succ,
            )
        ).scalar_one_or_none()
        if not existing_dep:
            session.add(ActivityDependency(
                predecessor_activity_id=pred,
                successor_activity_id=succ,
                dependency_type=dep_type,
                lag_days=lag,
            ))
    session.commit()
    print(f"✓ {len(dependencies_data)} Schedule dependencies verified")

    # 6. Seed Entity Aliases (Controlled Vocabulary + Human-Gated Review Queue)
    print("► Seeding Terminology Aliases...")
    aliases_data = [
        # Approved
        ("equipment", "pump P101", "P-101", 0.98, "approved", "admin", "planner"),
        ("equipment", "P101", "P-101", 0.99, "approved", "admin", "planner"),
        ("equipment", "FT501", "FT-501", 0.99, "approved", "admin", "planner"),
        ("contractor", "NE PetroWorks", "NorthEast PetroWorks", 0.95, "approved", "admin", "planner"),
        ("contractor", "Brahmaputra Infra", "Brahmaputra Infratech", 0.95, "approved", "admin", "planner"),
        ("location", "Area A Grid 12", "Area A", 0.90, "approved", "admin", "planner"),
        # Proposed (pending planner review in Review Queue!)
        ("equipment", "P101-B pump", "P-102", 0.76, "proposed", "ai_extractor", None),
        ("equipment", "crude-meter-01", "FT-501", 0.72, "proposed", "ai_extractor", None),
        ("contractor", "Brahma Infratech Ltd", "Brahmaputra Infratech", 0.81, "proposed", "ai_extractor", None),
        ("contractor", "Assam Instrumentation Co", "Assam Power & Instrumentation", 0.78, "proposed", "ai_extractor", None),
        ("location", "Pump Pad Alpha", "Area A", 0.74, "proposed", "ai_extractor", None),
    ]
    for etype, raw, canon, conf, stat, prop, app in aliases_data:
        existing_alias = session.execute(
            select(EntityAlias).where(
                EntityAlias.entity_type == etype,
                EntityAlias.raw_alias == raw,
            )
        ).scalar_one_or_none()
        if not existing_alias:
            session.add(EntityAlias(
                entity_type=etype,
                raw_alias=raw,
                canonical_value=canon,
                confidence=conf,
                status=stat,
                proposed_by=prop,
                approved_by=app,
                reviewed_at=datetime.now(tz=timezone.utc) if stat == "approved" else None,
            ))
    session.commit()
    print(f"✓ {len(aliases_data)} Terminology aliases seeded (including pending proposals for human review)")

    # 7. Seed 3-6 Months of Rich Backdated ProgressEvents
    print("► Seeding 60+ Backdated Historical ProgressEvents (May 2026 – Aug 2026)...")

    # Activities to link
    activities = session.execute(select(PlanActivity)).scalars().all()
    act_by_code = {a.activity_id: a for a in activities}

    base_date = datetime(2026, 5, 1, 8, 30, tzinfo=IST)

    delay_scenarios = [
        ("material", "Vendor gasket consignment delayed at Guwahati hub", "Gasket delivery pending from supplier"),
        ("weather", "Heavy monsoon downpour caused trench water-logging", "Trench de-watering in progress"),
        ("equipment", "Mobile crane boom hydraulic seal leak during spool lift", "Crane maintenance team deployed"),
        ("approval", "Hot-work clearance permit delayed by client safety engineer", "Awaiting PTW sign-off"),
        ("manpower", "Welder crew absenteeism following local holiday", "Recruiting replacement argon welders"),
        ("contractor", "Subcontractor rebar bending machine breakdown", "Bending machine parts being replaced"),
        ("logistics", "Pipe trailer stuck at NH-37 road blockade", "Escort dispatched for rerouting"),
        ("access", "Right of Way culvert access restricted by village council", "Liaison officer resolving local access"),
    ]

    supervisors = ["Suresh Nair", "R. Sharma", "A. Barman", "Dipak Das", "B. Goswami"]
    crews = ["Piping Crew Alpha", "Civil Gang #2", "Electrical Team B", "Welding Gang 1", "Rigging Crew"]

    events_created = 0

    # Ensure each activity gets 2-4 realistic events over the past 90 days
    for act_code, act in act_by_code.items():
        disc = act.discipline or "piping"
        orig_dur = act.original_duration_days or 3.0

        contractor_choice = "NorthEast PetroWorks"
        if disc in ["civil", "structural"]:
            contractor_choice = "Brahmaputra Infratech"
        elif disc in ["electrical", "instrumentation"]:
            contractor_choice = "Assam Power & Instrumentation"
        elif disc == "hse":
            contractor_choice = "Duliajan Safety Services"

        # Generate 3 events: Early start, In-progress milestone, and either completion or delay
        for step_idx in range(3):
            day_offset = random.randint(1, 85)
            ev_date = base_date + timedelta(days=day_offset, hours=random.randint(0, 8))

            has_delay = random.random() < 0.35
            delay_cat, delay_reas, blocker = (None, None, None)
            if has_delay:
                delay_cat, delay_reas, blocker = random.choice(delay_scenarios)

            pct = min(100.0, (step_idx + 1) * 35.0 + random.randint(-5, 5))
            if step_idx == 2 and not has_delay:
                pct = 100.0

            dur_actual = orig_dur * (pct / 100.0) + (1.5 if has_delay else 0.0)

            conf_score = round(random.uniform(0.72, 0.98), 3)
            conf_tier = "high" if conf_score >= 0.90 else ("medium" if conf_score >= 0.70 else "low")
            prov_cat = random.choice(["source_fact", "ai_extraction", "human_approval"])

            ev = ProgressEvent(
                project_id=settings.project_id,
                activity_id_plan=act.activity_id,
                plan_activity_id=act.id,
                activity_name_plan=act.activity_name,
                activity_description_extracted=f"{act.activity_name} — stage {step_idx+1} ({round(pct)}% done)",
                activity_description_raw=f"Daily update: {act.activity_name}, progress reached {round(pct)}% with team deployed.",
                activity_description_normalized=act.activity_name,
                discipline=disc,
                sub_discipline="Process Facilities",
                event_type=EventTypeEnum.finish if pct >= 100 else EventTypeEnum.partial_complete,
                activity_type="erection" if "erect" in act.activity_name.lower() else "execution",
                work_package="WP-01-Mainline",
                wbs_code=act.wbs_code or "1.1.2",
                construction_phase="Execution",
                execution_stage="Active Site Work",
                actual_start_datetime=ev_date,
                actual_finish_datetime=ev_date + timedelta(days=dur_actual) if pct >= 100 else None,
                planned_start=ev_date - timedelta(days=1),
                planned_finish=ev_date + timedelta(days=orig_dur),
                planned_duration_days=orig_dur,
                actual_duration_days=round(dur_actual, 1),
                remaining_duration_days=round(max(0.0, orig_dur - dur_actual), 1),
                percent_complete=pct,
                quantity_completed=round(dur_actual * 12.5, 1),
                quantity_unit="meters" if disc == "piping" else "units",
                location_reference=act.area or "Area A",
                location_area="Area A" if "Area A" in act.activity_name else "Area B",
                equipment_tag="P-101" if "P-101" in act.activity_name else ("FT-501" if "FT-501" in act.activity_name else None),
                line_number="24\"-XX" if "24\"" in act.activity_name else None,
                contractor_id=contractor_map.get(contractor_choice),
                contractor_name=contractor_choice,
                supervisor_name=random.choice(supervisors),
                crew_name=random.choice(crews),
                status="completed" if pct >= 100 else ("delayed" if has_delay else "in_progress"),
                delay_status="delayed" if has_delay else "on_track",
                delay_category=delay_cat,
                delay_reason=delay_reas,
                blocker_description=blocker,
                priority="high" if (act.is_critical or has_delay) else "medium",
                is_critical_path=act.is_critical,
                total_float_days=act.total_float_days,
                confidence_score=conf_score,
                confidence_tier=conf_tier,
                match_status=MatchStatusEnum.matched,
                provenance_category=prov_cat,
                source_type=SourceTypeEnum.spreadsheet if prov_cat == "source_fact" else SourceTypeEnum.free_text_dpr,
                extracted_by="time_agent_v2",
                extraction_timestamp=ev_date,
                reviewed_by_planner=prov_cat == "human_approval",
                planner_notes="Verified against daily inspection report" if prov_cat == "human_approval" else None,
                audit_trail={
                    "model_version": "nvidia/nemotron-3-super-120b-a12b",
                    "synthetic_seed": True,
                    "confidence_tier": conf_tier,
                },
                ontology_payload={
                    "discipline": {"value": disc, "confidence": 0.95, "evidence": "reported discipline"},
                    "percent_complete": {"value": pct, "confidence": 0.92, "evidence": f"{round(pct)}% reported"},
                    "contractor": {"value": contractor_choice, "confidence": 0.90, "evidence": contractor_choice},
                },
                correction_history=[],
            )
            session.add(ev)
            events_created += 1

    session.commit()
    print(f"✓ Successfully seeded {events_created} rich backdated progress events across 20 activities!")
    print("=" * 70)
    print("Historical seeding complete. Delay analytics and prediction calculations are fully populated.")
    print("=" * 70)


if __name__ == "__main__":
    main()
