# Team Kranti — SIH26122

**What this is**: Intelligent Data Capture & Schedule-Linking Layer for Oil India Limited's infrastructure projects. Field supervisors send progress updates (WhatsApp text/photo/voice/spreadsheet); this system extracts structured activity events, fuzzy-matches them to Primavera P6 L5/L6 activities, confidence-gates them through human review, and writes validated actuals back into the schedule via XER.

**Event**: Smart India Hackathon 2026 — Problem Statement SIH26122.

---

## Where memory lives

| What you need | Where to look |
|---|---|
| Architecture overview | `.ai/ARCHITECTURE.md` |
| All files and what they do | `.ai/REPO_MAP.md` |
| Database tables and columns | `.ai/DATA_MODEL.md` |
| API endpoint contracts | `.ai/API_CONTRACTS.md` |
| Pipeline workflow steps | `.ai/WORKFLOWS.md` |
| Architecture decisions and rationale | `.ai/DECISIONS.md` |
| Current build state (done/in-progress/next) | `.ai/CURRENT_STATE.md` |
| Changelog of AI-driven changes | `.ai/CHANGELOG.md` |

## How to update memory after a change

After any meaningful code change, update **only** the affected `.ai/` doc(s):
- New file added → update `REPO_MAP.md`
- Schema change → update `DATA_MODEL.md`
- New endpoint → update `API_CONTRACTS.md`
- Architecture decision → append to `DECISIONS.md`
- Build milestone reached → update `CURRENT_STATE.md`
- Any AI-driven change → append to `CHANGELOG.md`

Never regenerate all docs — only update what changed.

## Constraints (non-negotiable)
- **No P6 API** — schedule round-trip is XER → our platform → XER only.
- **Excel is not the canonical P6 format** — XER is.
- **Real pipeline** — no mocked LLM outputs, no TODO stubs on core logic.
- **Groq free tier** is the primary LLM; Ollama local is the coded fallback.
- **Synthetic data only** — no real Oil India data.
- See `.ai/DECISIONS.md` for full decision log.

## Quick start (once Docker is up)
```bash
docker-compose up -d
python scripts/seed_schedule.py   # load synthetic schedule
python scripts/run_demo.py        # inject all 3 input formats end-to-end
# open http://localhost:3000 for reviewer dashboard
```
