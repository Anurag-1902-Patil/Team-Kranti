"""
seed_demo_events.py — Inserts realistic ProgressEvent records for demo purposes.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import random

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from backend.core.config import get_settings
from backend.db.models import PlanActivity, ProgressEvent, MatchStatusEnum, SourceTypeEnum

settings = get_settings()

def dt(days, hours=0):
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)

DEMO_DATA = [
    {
        "status": MatchStatusEnum.matched,
        "score": 0.94,
        "desc": "Excavation and foundation work completed for main control room building.",
        "sender": "Ramesh Kumar",
        "disc": "civil",
        "doc": "Site Diary - Section 1"
    },
    {
        "status": MatchStatusEnum.matched,
        "score": 0.88,
        "desc": "Spool 24-inch line stringing and welding completed at CH 12+450.",
        "sender": "Suresh Nair",
        "disc": "piping",
        "doc": "Daily Progress Report.xlsx"
    },
    {
        "status": MatchStatusEnum.pending_match,
        "score": 0.72,
        "desc": "Installed cable trays for area A process section.",
        "sender": "Amit Patel",
        "disc": "electrical",
        "doc": "WhatsApp Image"
    },
    {
        "status": MatchStatusEnum.pending_match,
        "score": 0.68,
        "desc": "Leveling and alignment done for Pump 101, but grouting pending.",
        "sender": "Raj Singh",
        "disc": "mechanical",
        "doc": "Voice Note Transcript"
    },
    {
        "status": MatchStatusEnum.low_confidence_review,
        "score": 0.45,
        "desc": "Painting touch ups done near the main gate.",
        "sender": "Vikram Das",
        "disc": "civil",
        "doc": "WhatsApp Text"
    },
    {
        "status": MatchStatusEnum.low_confidence_review,
        "score": 0.38,
        "desc": "Safety audit finished for block B scaffolding.",
        "sender": "Anil Verma",
        "disc": "hse",
        "doc": "Email Extract"
    },
    {
        "status": MatchStatusEnum.unmatched_new,
        "score": 0.21,
        "desc": "Temporary road constructed to bypass the waterlogged area.",
        "sender": "Manoj Tiwari",
        "disc": "civil",
        "doc": "WhatsApp Text"
    },
    {
        "status": MatchStatusEnum.matched,
        "score": 0.92,
        "desc": "Hydrotest completed successfully for line N12-N15.",
        "sender": "Suresh Nair",
        "disc": "piping",
        "doc": "Hydrotest Report.pdf"
    },
    {
        "status": MatchStatusEnum.pending_match,
        "score": 0.65,
        "desc": "Received 50 tons of rebar, unloading in progress.",
        "sender": "Logistics Team",
        "disc": "material_management",
        "doc": "WhatsApp Text"
    },
    {
        "status": MatchStatusEnum.unmatched_new,
        "score": 0.15,
        "desc": "Local strike delayed the concrete mixers by 4 hours.",
        "sender": "Site Security",
        "disc": "administration",
        "doc": "WhatsApp Text"
    },
]

def main():
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    session = Session()

    activities = session.execute(select(PlanActivity)).scalars().all()
    if not activities:
        print("No PlanActivities found. Run seed_schedule.py first.")
        return

    # Delete existing progress events
    session.query(ProgressEvent).delete()
    session.commit()

    import random

    for idx, item in enumerate(DEMO_DATA):
        # Pick a random activity if not unmatched
        pa = None
        if item["status"] != MatchStatusEnum.unmatched_new:
            pa = random.choice(activities)
        
        event = ProgressEvent(
            project_id=settings.project_id,
            activity_id_plan=pa.activity_id if pa else None,
            plan_activity_id=pa.id if pa else None,
            activity_name_plan=pa.activity_name if pa else None,
            activity_description_extracted=item["desc"],
            discipline=item["disc"],
            confidence_score=item["score"],
            match_status=item["status"],
            supervisor_name=item["sender"],
            extracted_by="time_agent_v2",
            extraction_timestamp=dt(days=idx % 3, hours=idx),
            source_type=SourceTypeEnum.free_text_dpr,
            reviewed_by_planner=False
        )
        session.add(event)

    session.commit()
    print(f"Seeded {len(DEMO_DATA)} synthetic ProgressEvent records for demo.")
    session.close()

if __name__ == "__main__":
    main()
