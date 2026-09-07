# Architecture — SIH26122

## System Purpose
Intelligent Data Capture & Schedule-Linking Layer. Field supervisors send daily progress updates via WhatsApp (text, photo, voice, spreadsheet). The system extracts structured activity start/finish events, fuzzy-matches them to Primavera P6 L5/L6 activities, confidence-gates them through a human review step, and writes validated actuals back as a Primavera-compatible XER file.

## Actor Boundaries (from Use Case Diagram)
- **Onsite Engineer / Supervisor**: sends messages via WhatsApp (text, image upload, voice)
- **AI Time Agent (System)**: automated pipeline — ingestion, extraction, matching, embedding, write-back
- **Project Manager / Planner**: reviews flagged entries, accepts/edits/declines, confirms new activities, queries institutional memory, views analytics

## Pipeline (in order)
```
[WhatsApp Cloud API]
    → HMAC-validated POST webhook (FastAPI)
    → 200 OK immediately + enqueue Celery task
    → Worker: branch by MIME type
        text    → LLM extractor
        audio   → faster-whisper → transcript → LLM extractor
        image   → OCR (see two-engine note below) → LLM extractor
        PDF     → pdfplumber / rasterize + Tesseract → LLM extractor
        XLSX    → pandas → structured text repr → LLM extractor
    → Schema Normalizer → ProgressEvent (§3.4 schema)
    → sender_profiles lookup → discipline_hint
    → Matching Engine:
        1. RapidFuzz (fuzzy string)
        2. Sentence-Transformers (semantic cosine)
        3. LLM re-ranker (Qwen3-8B local / Groq fallback)
        4. Score fusion → confidence-gated routing
    → Postgres write (event + matches + audit trail)
    → Qdrant index — plan_activities collection (for future matching)
    → Qdrant index — progress_events collection (institutional memory)
    → Schedule write-back (if matched)
[Human Review UI — Next.js]
    → Accept / Edit / Decline / Confirm-as-new
    → On confirm-new: new plan_activity created + embedded immediately
[Schedule Export]
    → PyP6XER writes updated .XER file
[Institutional Memory Export]
    → Parquet + CSV + SCHEMA.md bundle
```

## OCR — Two Deliberate Engines for Two Different Accuracy Profiles

**Tesseract handles typed/tabular OCR. PP-OCRv5 handles handwritten diary photos. These are deliberately different engines chosen for different accuracy profiles, not redundant.**

| Input type | Engine | Reason |
|---|---|---|
| Typed DPRs, spreadsheet renders, printed forms | **Tesseract** (`pytesseract`) | Fast, lightweight, excellent on clean printed text. No GPU needed. |
| Handwritten site diary photos | **PP-OCRv5** (via PaddleOCR, CPU-only) | 0.07B params, specifically tuned for handwritten text. Baidu benchmarks claim it outperforms Qwen2.5-VL and GPT-4o on handwritten OCR specifically. No GPU needed. |

Do not collapse these into a single engine. They are optimized for fundamentally different input distributions.

## Qdrant — Two Collections, Two Distinct Purposes

See ADR-012 in DECISIONS.md for the full rationale. In summary:

| Collection | Purpose | Used by |
|---|---|---|
| `plan_activities` | Matching engine index — "which plan activity does this description match?" | `semantic_matcher.get_semantic_candidates()` |
| `progress_events` | Institutional memory — "what similar work was done historically?" | `GET /memory/query`, dataset export |

**These must not be merged.** Merging them would corrupt both use cases. The distinction mirrors the real-world separation between "what is planned" and "what actually happened."

## Confidence Routing
| Score | Status | Action |
|---|---|---|
| ≥0.85 | `matched` | Auto-write actuals, index to Qdrant (progress_events) |
| 0.55–0.84 | `low_confidence_review` | Queue for planner review |
| <0.55 | `unmatched_new` | Flag for planner — confirm as new activity or decline |

## Key Constraints
- No P6 API. Schedule integration = XER → platform → XER.
- Excel is auxiliary only; XER is canonical.
- Local Qwen3-8B (Ollama) primary; Groq `qwen/qwen3-32b` is a coded fallback (not just documented).
- Real LLM calls, real OCR, real matching — no mocked outputs.
- Synthetic data only (no real Oil India data).

## Tech Stack Summary
See `REPO_MAP.md` for file-level detail. Key choices:
- FastAPI + SQLAlchemy 2 (async) + PostgreSQL 16
- Celery 5 + Redis 7 (background processing)
- MinIO (S3-compatible object storage)
- faster-whisper (ASR)
- Tesseract `pytesseract` (typed OCR) + PP-OCRv5 via PaddleOCR (handwritten OCR) — two engines, deliberate
- Qwen3-8B via Ollama (LLM primary) + Groq `qwen/qwen3-32b` (fallback for extraction + re-ranking)
- RapidFuzz + Sentence-Transformers + LLM re-ranker (matching)
- Qdrant (two collections: matching index + institutional memory — see ADR-012)
- PyP6XER (XER parse/write)
- Next.js 15 (reviewer dashboard) with named-token auth
