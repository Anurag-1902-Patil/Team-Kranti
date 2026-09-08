"""
run_demo.py — End-to-end demo script for SIH26122.

Injects all 3 input formats directly (bypassing WhatsApp webhook for demo convenience),
traces the pipeline at each stage, and shows the reviewer queue at the end.

Run:
    cd backend
    python ../scripts/run_demo.py

What it does:
  1. Injects 3 synthetic messages: free text, XLSX spreadsheet, scanned diary image
  2. For each: runs the full extraction + matching pipeline
  3. Prints a pipeline trace showing what happened at each stage
  4. Shows the review queue with confidence scores
  5. Demonstrates accept, edit, and confirm_new actions
  6. Exports the institutional memory dataset
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
Session = sessionmaker(bind=engine)


def banner(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")
def step(msg): print(f"\n  ► {msg}")
def ok(msg): print(f"  [OK] {msg}")
def warn(msg): print(f"  [WARN] {msg}")


def run_demo():
    banner("SIH26122 — End-to-End Demo")

    session = Session()

    # -------------------------------------------------------------------------
    # Check seed state
    # -------------------------------------------------------------------------
    from backend.db.models import PlanActivity, SenderProfile

    activity_count = session.execute(
        __import__("sqlalchemy", fromlist=["func"]).func.count(PlanActivity.id)
        if False else select(PlanActivity)
    )
    pa_rows = session.execute(select(PlanActivity)).scalars().all()
    if not pa_rows:
        print("ERROR: No plan activities found. Run seed_schedule.py first.")
        sys.exit(1)

    ok(f"Found {len(pa_rows)} plan activities")

    # Load embedding index
    activity_index = {pa.activity_id: pa.activity_name for pa in pa_rows}
    from backend.services.matching.semantic_matcher import load_activity_embeddings
    load_activity_embeddings(activity_index)
    ok("Semantic embedding index loaded")

    # -------------------------------------------------------------------------
    # Format 1: Free-text WhatsApp message
    # -------------------------------------------------------------------------
    banner("Format 1: Free-text WhatsApp Message")
    step("Input: 'Spool erection for Line 24\"-XX started today at chainage 12+450, 09:30 AM'")

    _run_text_demo(
        session=session,
        sender_id="919876543210",
        text="Spool erection for Line 24\"-XX started today at chainage 12+450, 09:30 AM. Team of 8 welders deployed.",
        source_label="whatsapp_text",
    )

    # -------------------------------------------------------------------------
    # Format 2: Spreadsheet
    # -------------------------------------------------------------------------
    banner("Format 2: XLSX Daily Progress Report")
    dpr_path = ROOT / "data" / "synthetic" / "sample_dpr.xlsx"

    if dpr_path.exists():
        step(f"Input: {dpr_path.name}")
        from backend.services.extraction.ocr import extract_text_from_spreadsheet

        xlsx_bytes = dpr_path.read_bytes()
        extracted_text = extract_text_from_spreadsheet(xlsx_bytes, dpr_path.name)
        ok(f"Spreadsheet extracted: {len(extracted_text)} chars")

        _run_text_demo(
            session=session,
            sender_id="919876543210",
            text=extracted_text,
            source_label="spreadsheet",
        )
    else:
        warn(f"sample_dpr.xlsx not found at {dpr_path}. Creating synthetic one...")
        _create_synthetic_xlsx(dpr_path)
        step("Retrying with created XLSX...")
        from backend.services.extraction.ocr import extract_text_from_spreadsheet
        xlsx_bytes = dpr_path.read_bytes()
        extracted_text = extract_text_from_spreadsheet(xlsx_bytes, dpr_path.name)
        _run_text_demo(session=session, sender_id="919876543210", text=extracted_text, source_label="spreadsheet")

    # -------------------------------------------------------------------------
    # Format 3: Scanned diary (text simulation — image requires running system)
    # -------------------------------------------------------------------------
    banner("Format 3: Scanned/Handwritten Site Diary")
    step("Simulating OCR output from a handwritten site diary")
    step("(In the live demo: send a photo to WhatsApp → Groq vision extracts text)")

    simulated_diary_text = """
    Date: 29 Aug 2026
    Civil Works - Daily Diary
    
    Pump P101 Foundation:
    - Excavation complete (Area A, Grid 12-13)
    - PCC laid @ 8:30 AM
    - Formwork erected by 2 PM
    - Rebar placed 75% done, continuing tomorrow
    
    Access Road:
    - Gravel compaction started CH 0+000 to CH 0+200
    - 100% done for first 200m stretch
    
    Site In-charge: Suresh Nair
    """

    _run_text_demo(
        session=session,
        sender_id="919876543211",
        text=simulated_diary_text,
        source_label="scanned_diary",
    )

    # -------------------------------------------------------------------------
    # Show review queue
    # -------------------------------------------------------------------------
    banner("Review Queue")
    from backend.db.models import MatchStatusEnum, ProgressEvent

    all_events = session.execute(select(ProgressEvent)).scalars().all()
    print(f"\n  Total events created: {len(all_events)}")
    print(f"\n  {'Event ID':<12} {'Match Status':<25} {'Confidence':<12} {'Discipline':<15} {'Description'}")
    print("  " + "-" * 100)
    for ev in all_events:
        desc = (ev.activity_description_extracted or "")[:50]
        score = f"{ev.confidence_score:.3f}" if ev.confidence_score else "N/A"
        print(f"  {str(ev.id)[:8]:<12} {ev.match_status.value:<25} {score:<12} {ev.discipline.value:<15} {desc}")

    # -------------------------------------------------------------------------
    # Demo: Accept a matched event
    # -------------------------------------------------------------------------
    matched_events = [e for e in all_events if e.match_status == MatchStatusEnum.matched]
    if matched_events:
        ev = matched_events[0]
        banner(f"Demo Action: Accept matched event {str(ev.id)[:8]}")
        print(f"  Activity: {ev.activity_description_extracted}")
        print(f"  Matched to: {ev.activity_name_plan}")
        print(f"  Confidence: {ev.confidence_score:.3f}")
        ok("Event would be accepted via POST /api/v1/review/{id}/accept")
        ok("Schedule write-back would update actual_start/finish in plan_activities table")
        ok("Event would be indexed to ChromaDB for institutional memory")

    # -------------------------------------------------------------------------
    # Demo: Institutional memory query
    # -------------------------------------------------------------------------
    banner("Institutional Memory Query")
    step("Querying: 'piping spool erection duration'")

    from backend.services.institutional_memory.qdrant_store import query_institutional_memory, get_events_collection_count

    count = get_events_collection_count()
    ok(f"Indexed events in ChromaDB: {count}")

    if count > 0:
        results = query_institutional_memory("piping spool erection duration", n_results=3)
        for i, r in enumerate(results):
            print(f"\n  Result {i+1}: (similarity: {r['similarity_score']})")
            print(f"    Text: {r['text'][:100]}")
            print(f"    Metadata: {r['metadata']}")

    # -------------------------------------------------------------------------
    # Done
    # -------------------------------------------------------------------------
    banner("Demo Complete")
    print("Next steps for judges:")
    print("  1. Open http://localhost:3000 — reviewer dashboard")
    print("  2. Navigate to Review Queue — see events with confidence scores")
    print("  3. Accept one, edit one (pick different activity), confirm one as new")
    print("  4. Navigate to Schedule — see actuals applied to plan activities")
    print("  5. Click 'Export XER' — download updated Primavera XER file")
    print("  6. Navigate to Memory — query 'piping delays' or similar")
    print("  7. Click 'Export Dataset' — download Parquet + CSV + SCHEMA.md bundle")
    print()

    session.close()


def _run_text_demo(session, sender_id: str, text: str, source_label: str):
    """Run the extraction + matching pipeline on a text input."""
    from backend.db.models import PlanActivity, SenderProfile, Document, ProgressEvent, Match, MatchStatusEnum
    from backend.services.extraction.llm_extractor import extract_activities, ExtractionError
    from backend.services.extraction.normalizer import normalize
    from backend.services.matching.fuzzy_matcher import get_fuzzy_candidates
    from backend.services.matching.semantic_matcher import get_semantic_candidates
    from backend.services.matching.confidence import fuse_and_route
    from sqlalchemy import select
    import uuid
    from datetime import datetime, timezone

    # Discipline hint
    profile = session.execute(
        select(SenderProfile).where(SenderProfile.sender_id == sender_id)
    ).scalar_one_or_none()
    discipline_hint = profile.discipline if profile else None
    step(f"Discipline hint: {discipline_hint or 'none (LLM will infer)'}")

    # Extract
    try:
        step("Calling LLM extractor (Groq primary / Ollama fallback)...")
        extracted_activities, audit = extract_activities(text, discipline_hint, source_label)
        ok(f"Extracted {len(extracted_activities)} activity events")
    except ExtractionError as exc:
        warn(f"Extraction failed: {exc}")
        return

    # Activity index
    pa_rows = session.execute(select(PlanActivity)).scalars().all()
    activity_index = {pa.activity_id: pa.activity_name for pa in pa_rows}

    for i, extracted in enumerate(extracted_activities):
        print(f"\n  Activity {i+1}: '{extracted.activity_description}'")

        # Match
        fuzzy = get_fuzzy_candidates(extracted.activity_description, activity_index)
        semantic = get_semantic_candidates(extracted.activity_description)
        match_result = fuse_and_route(
            extracted.activity_description,
            extracted.discipline,
            fuzzy,
            semantic,
        )

        print(f"    Status: {match_result.match_status.value}")
        print(f"    Confidence: {match_result.final_score:.3f}")
        if match_result.selected_activity_id:
            print(f"    Matched to: [{match_result.selected_activity_id}] {match_result.selected_activity_name}")
        if match_result.all_candidates:
            top3 = match_result.all_candidates[:3]
            print(f"    Top 3 candidates: {[(c.activity_id, round(c.final_score,3)) for c in top3]}")

        # Normalize and store
        event_create = normalize(
            extracted=extracted,
            document_id=None,
            project_id=settings.project_id,
            source_type=source_label,
            source_document_id=None,
            audit_trail=audit,
        )

        plan_activity_id = None
        activity_name_plan = None
        if match_result.selected_activity_id:
            pa = session.execute(
                select(PlanActivity).where(PlanActivity.activity_id == match_result.selected_activity_id)
            ).scalar_one_or_none()
            if pa:
                plan_activity_id = pa.id
                activity_name_plan = pa.activity_name

        from backend.db.models import ProgressEvent, Match

        event = ProgressEvent(
            project_id=settings.project_id,
            activity_id_plan=match_result.selected_activity_id,
            plan_activity_id=plan_activity_id,
            activity_name_plan=activity_name_plan,
            activity_description_extracted=event_create.activity_description_extracted,
            discipline=event_create.discipline,
            event_type=event_create.event_type,
            actual_start_datetime=event_create.actual_start_datetime,
            actual_finish_datetime=event_create.actual_finish_datetime,
            percent_complete=event_create.percent_complete,
            confidence_score=match_result.final_score,
            match_status=match_result.match_status,
            source_type=event_create.source_type,
            extracted_by="time_agent_v1",
            extraction_timestamp=datetime.now(tz=timezone.utc),
            audit_trail=audit,
        )
        session.add(event)
        session.flush()

        # Index to ChromaDB if matched
        if match_result.match_status == MatchStatusEnum.matched:
            try:
                from backend.services.institutional_memory.qdrant_store import index_progress_event
                index_progress_event(
                    event_id=str(event.id),
                    activity_description=extracted.activity_description,
                    activity_name_plan=activity_name_plan,
                    discipline=event_create.discipline.value,
                    project_id=settings.project_id,
                    confidence_score=match_result.final_score,
                    actual_start=str(event.actual_start_datetime) if event.actual_start_datetime else None,
                    actual_finish=str(event.actual_finish_datetime) if event.actual_finish_datetime else None,
                )
                ok("Indexed to ChromaDB")
            except Exception as exc:
                warn(f"ChromaDB indexing failed: {exc}")

    session.commit()


def _create_synthetic_xlsx(path: Path):
    """Create a synthetic XLSX daily progress report."""
    import openpyxl

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Daily Progress Report"

    headers = ["Date", "Activity ID", "Activity Description", "Discipline", "% Complete", "Actual Start", "Actual Finish", "Location", "Remarks"]
    ws.append(headers)

    rows = [
        ["2026-08-29", "PIP-002", "Erect Line 24-XX spool at chainage 12+450", "Piping", 60, "2026-08-27 09:30", "", "Chainage 12+450", "6 joints completed out of 10"],
        ["2026-08-29", "PIP-003", "Hydrotest Line 24-XX section N12 to N15", "Piping", 0, "", "", "N12-N15", "Scheduled for 2026-09-02"],
        ["2026-08-29", "CIV-002", "Concrete pour for Pump P-101 foundation", "Civil", 100, "2026-08-28 07:00", "2026-08-28 16:00", "Area A Grid 12-13", "Completed as per plan"],
        ["2026-08-29", "ELE-001", "Cable pulling MCC-1 to P-101 Route R-12", "Electrical", 40, "2026-08-27 08:00", "", "Route R-12", "240m of 360m complete"],
        ["2026-08-29", "MEC-001", "Set pump P-101 on foundation", "Mechanical", 100, "2026-08-29 09:00", "2026-08-29 14:00", "Area A", "Leveled and grouted"],
    ]

    for row in rows:
        ws.append(row)

    wb.save(path)
    print(f"  ✓ Created synthetic XLSX at {path}")


if __name__ == "__main__":
    run_demo()
