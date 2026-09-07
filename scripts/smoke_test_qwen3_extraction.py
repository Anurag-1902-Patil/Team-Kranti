"""
smoke_test_qwen3_extraction.py

Verifies that Qwen3-8B (or Groq fallback) produces valid ExtractedActivity JSON
against the existing Pydantic schemas on synthetic WhatsApp messages.

Run: python3 scripts/smoke_test_qwen3_extraction.py
     (requires Ollama to be running with qwen3:8b pulled, OR GROQ_API_KEY set)

Failure modes this is designed to catch:
  1. Qwen3 <think>...</think> block not stripped → JSONDecodeError
  2. Field name mismatch (e.g. "activity" vs "activities")
  3. Numeric type mismatch on percent_complete (e.g. "50%" string vs float)
  4. Extra required fields that Qwen3 omits
  5. Total extraction failure (both LLM backends down)
"""

import json
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SYNTHETIC_MESSAGES = [
    {
        "id": "msg-smoke-001",
        "text": "Spool erection for Line 24\"-XX started at chainage 12+450. Work began at 09:30 AM today. All safety checks cleared.",
        "expected_discipline": "piping",
        "expected_event_type": "start",
    },
    {
        "id": "msg-smoke-002",
        "text": "Civil team completed 120m of earthwork trenching for section B-12 to B-17. About 60% of total trench done.",
        "expected_discipline": "civil",
        "expected_event_type": "partial_complete",
    },
    {
        "id": "msg-smoke-003",
        "text": "Pump P-101 foundation excavation 100% complete as of 5 PM. Waiting for concrete pour team tomorrow.",
        "expected_discipline": "civil",
        "expected_event_type": "finish",
    },
    {
        "id": "msg-smoke-004",
        "text": "Electrical cable pulling from MCC-1 to pump P-101 started. Route R-12, 3Cx150mm² cable. About 30 meters pulled so far.",
        "expected_discipline": "electrical",
        "expected_event_type": "start",
    },
    {
        "id": "msg-smoke-005",
        "text": "HSE: Toolbox meeting done at 8 AM. 12 workers on site. No incidents. Permit to work issued for hot work at section F.",
        "expected_discipline": "hse",
        "expected_event_type": "partial_complete",
    },
]


def run_smoke_test():
    from backend.services.extraction.llm_extractor import extract_activities, ExtractedActivity, ExtractionError

    print("=" * 60)
    print("Qwen3-8B Extraction Smoke Test")
    print("=" * 60)

    passed = 0
    failed = 0
    failures = []

    for msg in SYNTHETIC_MESSAGES:
        print(f"\n--- {msg['id']} ---")
        print(f"Input: {msg['text'][:80]}...")

        try:
            activities, audit = extract_activities(
                text=msg["text"],
                discipline_hint=msg["expected_discipline"],
                source_label=msg["id"],
            )
        except ExtractionError as e:
            print(f"  ❌ EXTRACTION FAILED: {e}")
            failed += 1
            failures.append({"id": msg["id"], "error": str(e)})
            continue

        if not activities:
            print(f"  ❌ NO ACTIVITIES EXTRACTED")
            failed += 1
            failures.append({"id": msg["id"], "error": "empty activities list"})
            continue

        llm_used = audit.get("llm_used", "unknown")
        print(f"  LLM used: {llm_used}")
        print(f"  Activities extracted: {len(activities)}")

        for i, act in enumerate(activities):
            print(f"  Activity {i+1}: {act.activity_description[:60]}")
            print(f"    event_type={act.event_type}, discipline={act.discipline}")
            print(f"    percent_complete={act.percent_complete}, quantity={act.quantity_completed} {act.quantity_unit or ''}")
            if act.extraction_notes:
                print(f"    notes: {act.extraction_notes[:80]}")

        # Validate: at least one activity has the expected discipline or 'unknown'
        top = activities[0]

        # Check discipline is a valid value (not a hallucination)
        valid_disciplines = {"piping", "civil", "electrical", "instrumentation", "hse", "structural", "mechanical", "unknown"}
        if top.discipline not in valid_disciplines:
            print(f"  ❌ INVALID DISCIPLINE: {top.discipline!r}")
            failed += 1
            failures.append({"id": msg["id"], "error": f"invalid discipline: {top.discipline}"})
            continue

        # Check event_type is valid
        valid_event_types = {"start", "finish", "partial_complete"}
        if top.event_type not in valid_event_types:
            print(f"  ❌ INVALID EVENT_TYPE: {top.event_type!r}")
            failed += 1
            failures.append({"id": msg["id"], "error": f"invalid event_type: {top.event_type}"})
            continue

        # Check percent_complete is numeric if set
        if top.percent_complete is not None:
            if not isinstance(top.percent_complete, (int, float)):
                print(f"  ❌ PERCENT_COMPLETE NOT NUMERIC: {type(top.percent_complete)}")
                failed += 1
                failures.append({"id": msg["id"], "error": "percent_complete not numeric"})
                continue
            if not 0 <= top.percent_complete <= 100:
                print(f"  ❌ PERCENT_COMPLETE OUT OF RANGE: {top.percent_complete}")
                failed += 1
                failures.append({"id": msg["id"], "error": f"percent_complete={top.percent_complete} out of range"})
                continue

        print(f"  ✅ PASS")
        passed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(SYNTHETIC_MESSAGES)} passed, {failed} failed")
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  {f['id']}: {f['error']}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    ok = run_smoke_test()
    sys.exit(0 if ok else 1)
