# CHANGELOG.md — AI-driven changes

All meaningful code changes made by AI (Antigravity) are logged here.

## 2026-09-11 — P6-Style Project Controls Interface & Part C Endpoints

**Session summary**: Rebuilt the entire frontend into a dense, high-performance Primavera P6 project controls interface consuming real database actuals (51 activities, 153 events) with white/near-white palette (`#FFFFFF`, `#FAFAFA`, `#F4F4F5`) and restrained slate-blue accents. Delivered 7 core MVPs, 5 new backend APIs, and end-to-end automated test validation.

### Part C Backend Endpoints
- Implemented `GET /api/v1/schedule/gantt` in `backend/api/v1/schedule.py` returning nested WBS hierarchy, dependencies, dual baseline/actual dates, float, and critical-path flags.
- Implemented `GET /api/v1/updates/feed` in `backend/api/v1/updates.py` generating a unified attention feed with stable IDs (`rev_*`, `dq_*`, `sched_*`, `doc_*`, `alias_*`) and verified no double-counting between review queue and update center.
- Implemented `GET /api/v1/analysis/delays` with server-side filters (discipline, contractor, location, cause, date range), returning KPIs, monthly accumulation trends, 12 root cause categories, contractor delay ratios, and major delay register.
- Implemented `POST /api/v1/search/parse-filter` in `backend/api/v1/search.py` providing grounded natural language to structured filter translation with route suggestions.
- Implemented `GET /api/v1/schedule/activities/{activity_id}/detail` returning a unified 6-section payload (Identity, Schedule, Progress, Intelligence with Evidence Breadcrumb, Risk with Explainability Strip, and Audit).

### Frontend P6 Architecture & 7 MVPs
- **MVP 1: Project Overview (`app/page.tsx`)**: Planned vs Actual S-Curve (Recharts Line), Activity Status Donut, Discipline Progress Bars, Delay Watchlist, and `WhatChangedRibbon`.
- **MVP 2: P6 Gantt & Schedule (`app/schedule/page.tsx`, `components/P6Gantt.tsx`)**: High-density SVG/HTML dual-bar timeline with expandable WBS hierarchy, 4-level zoom (day/week/month/quarter), SVG dependency arrows, critical-path highlighting, XER export, and XER import modal.
- **MVP 3: Activity Detail Drawer (`components/ActivityDetailDrawer.tsx`)**: 6 tabs (Identity, Schedule, Progress history, Intelligence with 4-level Evidence Breadcrumb `Activity → Progress Event → Document → Original Message`, Risk with Prediction Explainability Strip, and Audit trail with planner re-editing).
- **MVP 4: Review Queue (`app/review/page.tsx`)**: Keyboard-accelerated triage (`A`/`E`/`R`/`J`/`K`), confidence tiers, match re-assignment, confirm-new activity, and terminology proposals tab.
- **MVP 5: Update Center (`app/updates/page.tsx`)**: Attention feed with category tabs, severity filter, and direct route linking.
- **MVP 6: Delay Analysis (`app/analysis/delays/page.tsx`)**: Delay KPIs, accumulation trend, 12 standardized root causes, contractor delay rankings, bottleneck locations, and major delay register.
- **MVP 7: Command Palette (`components/CommandPalette.tsx`)**: Spotlight `⌘K` search with parsed filter pills and direct jump links.

### Verification & Testing
- Automated backend tests: `tests/test_p6_frontend_endpoints.py` (5/5 passing) and `tests/test_intelligence_layer.py` (5/5 passing).
- Production build: `npm run build` in `frontend/` passed with 0 TypeScript errors and static page generation.

---

## 2026-09-05 — Initial Full Build (Session 2)

**Session summary**: Completed the full implementation of all 14 layers.

### Layer 0 (Foundation)
- Created `backend/requirements.txt` with full dependency stack
- Created `.env.example` with all required env var templates
- Created `backend/logging_config.py` — structured JSON logging with structlog
- Created `backend/core/config.py` — Pydantic BaseSettings with all app config

### Layer 1 (Database)
- Created `backend/db/models.py` — 7 SQLAlchemy ORM tables with all relationships, indexes, FK constraints, JSONB fields
- Created `backend/db/session.py` — async session factory, FastAPI get_db dependency
- Created `backend/alembic/env.py` — reads DATABASE_URL_SYNC, imports Base for autogenerate
- Created `backend/alembic/versions/001_initial_schema.py` — initial migration (all tables + enums)

### Layer 2 (Ingestion)
- Created `backend/security/hmac.py` — constant-time HMAC-SHA256 verification
- Created `backend/services/ingestion/whatsapp.py` — typed WAMessage Pydantic models for all message types
- Created `backend/services/ingestion/media.py` — download from Meta CDN, upload to MinIO
- Created `backend/api/v1/webhook.py` — HMAC verify, idempotency, immediate 200, fire-and-forget Celery
- Created `backend/workers/celery_app.py` — Redis broker, late ACK, time limits, prefetch=1

### Layer 3 (Extraction)
- Created `backend/services/extraction/asr.py` — faster-whisper singleton, VAD filter, temp file management
- Created `backend/services/extraction/ocr.py` — PaddleOCR (printed) + Groq vision (handwritten) + pdfplumber + pandas
- Created `backend/services/extraction/llm_extractor.py` — few-shot system prompt, Groq primary + Ollama fallback, tenacity retry, JSON parse
- Created `backend/services/extraction/normalizer.py` — enum aliases, dateutil parsing, IST timezone assumption, audit enrichment

### Layer 4 (Matching)
- Created `backend/services/matching/fuzzy_matcher.py` — RapidFuzz token_sort + partial_ratio, 0.6/0.4 weighting
- Created `backend/services/matching/semantic_matcher.py` — all-MiniLM-L6-v2, numpy embedding matrix, cosine dot product
- Created `backend/services/matching/confidence.py` — merge, LLM re-rank, 0.3/0.3/0.4 fusion, threshold routing (0.85/0.55)

### Layer 5 (Scheduling)
- Created `backend/services/scheduling/xer_parser.py` — PyP6XER wrapper with discipline keyword inference
- Created `backend/services/scheduling/xer_writer.py` — applies only actual_start/finish/pct, preserves all P6 structure
- Created `backend/services/scheduling/schedule_service.py` — async write-back, confirm_new with immediate embedding

### Layer 6 (Institutional Memory)
- Created `backend/services/institutional_memory/chroma_store.py` — persistent ChromaDB, progress_events + plan_activities collections
- Created `backend/services/institutional_memory/exporter.py` — Postgres → Parquet + CSV + SCHEMA.md + summary_stats.json

### Layer 7 (Pipeline + API)
- Created `backend/workers/tasks.py` — full 10-step Celery task: idempotency → media → ASR/OCR → LLM extract → normalize → fuzzy → semantic → LLM rerank → store → ChromaDB index
- Created `backend/api/v1/events.py` — list/detail with match candidates hydration
- Created `backend/api/v1/review.py` — 4 actions (accept/edit/decline/confirm_new) + queue endpoint
- Created `backend/api/v1/schedule.py` — activities list, new activity creation, XER export
- Created `backend/api/v1/memory.py` — semantic query, ZIP export, stats

### Layer 8 (Schemas + Deps)
- Created `backend/schemas/event.py`, `review.py`, `schedule.py`
- Created `backend/api/deps.py` — Bearer token auth, get_db re-export

### Layer 9–10 (Data + Scripts)
- Created `data/SCHEMA.md` — 19-column data dictionary with analysis guidance
- Created `data/synthetic/sender_profiles.json` — 5 sender profiles
- Created `data/synthetic/whatsapp_messages.json` — 5 synthetic webhook payloads (3 formats)
- Created `scripts/seed_schedule.py` — XER load → DB, embedding index, ChromaDB, sender profiles
- Created `scripts/run_demo.py` — 3-format end-to-end demo with pipeline trace

### Layer 11 (Tests)
- Created `tests/conftest.py` — SQLite in-memory, fixtures
- Created `tests/test_extraction_normalizer.py` — 8 normalizer tests + 3 extractor tests
- Created `tests/test_matching.py` — 9 matching tests (fuzzy/semantic/routing)
- Created `tests/test_webhook_security.py` — 6 HMAC tests + 4 webhook endpoint tests

### Layer 12 (Docker)
- Created `docker-compose.yml` — Postgres + Redis + MinIO + backend + worker + frontend
- Created `Dockerfile.backend`, `Dockerfile.worker`

### Layer 13 (Frontend)
- Initialized Next.js 15 app with TypeScript + Tailwind
- Created 5 pages: Dashboard, Events, Review Queue, Schedule, Memory
- Created `Sidebar`, `ConfidenceBadge`, `DisciplineChip`, `ConfidenceBar` components
- Created `lib/api.ts`, `lib/types.ts`

### Layer 14 (Memory docs)
- Created/updated: `REPO_MAP.md`, `DATA_MODEL.md`, `CURRENT_STATE.md`, `CHANGELOG.md`

---

## 2026-09-05 — Final Change Request (Session 3)

**Session summary**: Applied final stack migration and all functional gap closures. All 34 tests now pass.

### Stack changes
- **OCR stack** (`backend/services/extraction/ocr.py`): Replaced single PaddleOCR engine with two deliberate engines — Tesseract (`pytesseract`) for typed/printed content, PP-OCRv5 (via PaddleOCR, CPU-only) for handwritten site diary photos. Documented in ARCHITECTURE.md with explicit table.
- **LLM flip** (`backend/services/extraction/llm_extractor.py`, `backend/services/matching/confidence.py`): Local Qwen3-8B via Ollama is now PRIMARY; Groq `qwen/qwen3-32b` is FALLBACK for both extraction and re-ranking. Qwen3 `<think>` block stripping added to both parsers.
- **Config rename**: `GROQ_MODEL_RERANK` → `GROQ_MODEL_FALLBACK` everywhere (config.py, .env.example, both call sites) — name reflects its dual-use role.
- **Qdrant** (`backend/services/institutional_memory/qdrant_store.py`): New file replacing ChromaDB. Two separate collections — `plan_activities` (matching index) and `progress_events` (institutional memory) — with ADR-012 explaining why they must stay separate.
- **Qdrant in compose**: `docker-compose.yml` updated with `qdrant` service, healthcheck, persistent volume, `QDRANT_URL` env injected into backend + worker.
- **Dockerfiles**: Tesseract (`tesseract-ocr`, `tesseract-ocr-eng`) added to both `Dockerfile.backend` and `Dockerfile.worker`.

### Functional gaps closed
- **A6 (Named reviewer identity)**: Added `POST /auth/login`, `POST /auth/logout` (`backend/api/v1/auth.py`). Frontend: new `/login` page (`frontend/app/login/page.tsx`), `Sidebar.tsx` updated to show reviewer name + sign-out button, `lib/api.ts` reads named token from localStorage with 401 auto-redirect.
- **A7 (Re-ranker fallback test)**: Added `TestRerankerFallback` class with 2 tests to `tests/test_matching.py`. Added `_call_local_llm` helper to `confidence.py` for testability.
- **A8 (Versioned prompt templates)**: Created `prompts/extractor_v1.txt` and `prompts/reranker_v1.txt` with headers documenting model, version, fusion weights, and Qwen3 handling notes.

### Config / infra
- `.env.example` fully updated: old Groq/Chroma/llama vars replaced with Qwen3/Qdrant/groq_fallback vars.
- `tests/conftest.py`: replaced stale `CHROMA_PERSIST_DIR` with `QDRANT_URL=:memory:`, `LOCAL_LLM_MODEL`, `GROQ_MODEL_FALLBACK`.

### Test fixes
- `test_normalize_percent_clamped_over_100`: uses `model_construct()` to bypass Pydantic `le=100` at construction — tests normalizer clamping, not schema validation.
- `test_groq_failure_triggers_ollama_fallback` → renamed `test_local_llm_failure_triggers_groq_fallback`, updated to patch `_call_local_llm`/`_call_groq_fallback` and new setting names.
- Reranker fallback tests: patches `_call_local_llm` directly (not raw `ollama.generate`) + uses `mocker.patch.object` for individual settings attributes (not whole object) to avoid MagicMock on float thresholds.
- Webhook "200-first" test: now sends valid HMAC signature + mocks `process_whatsapp_message.delay` (no live Redis needed in test env).

### Docs
- `ARCHITECTURE.md`: full rewrite with two-engine OCR table, two-collection Qdrant table, updated pipeline diagram and tech stack.
- `DECISIONS.md`: ADR-003, ADR-004, ADR-009 revised; ADR-011 (Qdrant replaces ChromaDB) and ADR-012 (two separate collections, rationale) added as required by user.
- `CURRENT_STATE.md`: all 15 layers marked done, final confirmed tech stack table, all A1-A8 gaps closed.
- Added `scripts/smoke_test_qwen3_extraction.py` — validates Qwen3-8B JSON output against Pydantic schemas on 5 synthetic message types before full demo run.

### Final test result: **34/34 passed** ✅

---

## 2026-09-08 — NVIDIA NIM LLM Swap (ADR-013)

**Session summary**: Replaced the Qwen3 + Groq dual-backend LLM stack with NVIDIA NIM `nvidia/nemotron-3-super-120b-a12b` as the sole backend. No local GPU required.

### Code changes
- **`backend/core/config.py`**: Removed `ollama_base_url`, `local_llm_model`, `groq_api_key`, `groq_model_fallback`. Added `nvidia_api_key`, `nvidia_nim_model`, `nvidia_nim_base_url`.
- **`backend/services/extraction/llm_extractor.py`**: Removed `_call_local_llm` + `_call_groq_fallback`. Added `_call_nvidia_nim` (OpenAI-compatible client against NVIDIA NIM, `enable_thinking=False`, `temperature=1.0, top_p=0.95`). `extract_activities()` now has a single NIM path — failure raises `ExtractionError` immediately (no silent fallback).
- **`backend/services/matching/confidence.py`**: Removed `_call_local_llm` (Ollama) + inline Groq block. Added `_call_nvidia_nim`. `_llm_rerank()` now has a single NIM path — failure falls back to equal-weighting (same as before).
- **`backend/requirements.txt`**: Removed `groq==0.12.0` and `ollama==0.4.1`. Added `openai>=1.40.0`.
- **`.env.example`**: Replaced Ollama + Groq LLM block with NVIDIA NIM block.
- **`prompts/extractor_v1.txt`** and **`prompts/reranker_v1.txt`**: Updated LLM header comments.

### Test changes
- **`tests/conftest.py`**: Replaced `GROQ_API_KEY`, `LOCAL_LLM_MODEL`, `GROQ_MODEL_FALLBACK` env defaults with `NVIDIA_API_KEY`, `NVIDIA_NIM_MODEL`, `NVIDIA_NIM_BASE_URL`.
- **`tests/test_matching.py`**: Rewrote `TestRerankerFallback` → `TestRerankerNvidiaNIM` with 2 tests: NIM success path (mocks `_call_nvidia_nim`) and NIM failure → equal-weighting path.
- **`tests/test_extraction_normalizer.py`**: Replaced `test_local_llm_failure_triggers_groq_fallback` with `test_nim_success_extracts_activities` (mocks `_call_nvidia_nim`, asserts `audit["llm_used"]` starts with `nvidia-nim/`).

### Memory docs updated
- `DECISIONS.md`: ADR-013 appended.
- `CURRENT_STATE.md`: Tech stack table + layer status rows updated.

---

## 2026-09-09 — Pipeline Stabilization (Session 5)

**Session summary**: Full inspection of the entire pipeline. Fixed all concrete bugs preventing correct WhatsApp→PostgreSQL matching. No architectural changes.

### Files changed

#### `backend/services/matching/confidence.py`
- **Bug 1 — Prompt (NEW fix)**: Rewrote `LLM_RERANK_PROMPT` to explicitly instruct the model:  
  "The activity_id must be ONLY the code (e.g. PIP-003) — copy from between the brackets. Do NOT include the activity name. Do NOT include brackets."
- **Bug 2 — ID normalizer (EXTENDED fix)**: Extracted `_normalize_llm_activity_id()` helper. Handles: bare IDs, `[PIP-003]`, `[PIP-003] Activity Name`, `"PIP-003"` (quoted). Added `valid_ids` set guard — unknown IDs (e.g. `PIP-999`) are logged as warnings and skipped, never mapped to a real candidate.
- **Bug 3 — Code-fence stripper (FIX)**: Replaced naive `[1:-1]` slice with the same defensive pattern as `llm_extractor.py` — only removes the closing ``` line if it's actually present.
- **Bug 4 — Score validation (NEW fix)**: Scores now clamped to `[0.0, 1.0]`. Non-numeric scores catch `TypeError/ValueError` per-item without killing the whole parse. Duplicate IDs logged at DEBUG and skipped. `overall_confidence` also clamped.
- **Bug 5 — Exception scope**: Replaced bare `except Exception` in parse path with `except (json.JSONDecodeError, KeyError, TypeError)` plus `raw` in warning log.

#### `backend/workers/tasks.py`
- **Bug 6**: Removed dead `SELECT` at line ~431 (result was discarded before `sa_update`).
- **Bug 7**: Removed dead `SELECT` in error handler at line ~503 (result was discarded before `sa_update`).
- **Bug 8**: Fixed stale log key `task.chroma_index_failed` → `task.qdrant_index_failed`.

#### `backend/services/institutional_memory/qdrant_store.py`
- **Bug 9 — Qdrant API Migration**: Replaced deprecated `client.search()` with `client.query_points()` and `query_vector` with `query`. Fixed `AttributeError` crashing the institutional memory query step of the demo script.

#### `frontend/app/` (schedule & memory pages)
- **Bug 10 — UI Export Auth**: Fixed a bug where clicking "Export XER" or "Export Dataset" failed with a 401 Unauthorized `Bearer token required.` error. The `fetch` calls were using a deprecated, empty `AUTH_TOKEN` constant instead of the dynamic `getAuthToken()` function.

### Files confirmed clean (no changes needed)
`fuzzy_matcher.py`, `semantic_matcher.py`, `llm_extractor.py`, `whatsapp.py`, `models.py`, `config.py`, `normalizer.py`, `session.py`, `requirements.txt`

### Root cause of regression
The matched score of 0.5178 (unmatched_new) was caused by the LLM returning `"[PIP-003] Hydrotest Line 24\"-XX (N12 to N20)"` as the `activity_id` field instead of `"PIP-003"`. The lookup `llm_scores.get("PIP-003", 0.0)` returned 0.0, so the 0.40 LLM weight was lost. After the fix: LLM score 1.0 → fused score ≈ 0.918 → `matched`.

---

## 2026-09-09 — Schedule Import Feature & Native XER Roundtrip (Session 6)

**Session summary**: Added schedule file import capabilities to allow planners/users to import `.xer` (Primavera P6) and schedule spreadsheet files (`.csv`, `.xlsx`, `.xls`) to directly view and work on activities in the UI. Built native XER parser and writer fallback to remove dependency fragility on PyP6Xer.

### Files changed

#### `backend/api/v1/schedule.py`
- Added `POST /api/v1/schedule/import` endpoint accepting `.xer`, `.csv`, `.xlsx`, `.xls`.
- Persists imported `.xer` to `data/synthetic/sample_schedule.xer` so that subsequent "Export XER" runs use the user's uploaded schedule.
- Parses activities, maps WBS codes and dates, infers disciplines if absent.
- Upserts activities into `plan_activities` table in PostgreSQL.
- Triggers `reload_matching_index(db)` so fuzzy/semantic matching immediately incorporates imported activities.
- Indexes activities into Qdrant vector store (`plan_activities` collection).

#### `backend/services/scheduling/xer_parser.py`
- Implemented `_parse_xer_native` parser to robustly read P6 tab-delimited tables (`%T TASK`, `%F`, `%R`) without external package failures.
- Maintained fallback structure so PyP6Xer is attempted first and gracefully falls back to native parser.

#### `backend/services/scheduling/xer_writer.py`
- Implemented `_apply_actuals_to_xer_native` to safely update `act_start_date`, `act_end_date`, and `phys_complete_pct` on `%R` rows under the `TASK` table while preserving all other project structures, tables, and calendars byte-for-byte.

#### `frontend/app/schedule/page.tsx`
- Added "Import Schedule" button alongside "Export XER".
- Added hidden file input supporting `.xer`, `.csv`, `.xlsx`, `.xls`.
- Connected file upload handler with `FormData` to `POST /api/v1/schedule/import` with Bearer auth.
- Added live loading state, success/error feedback banner with activity count, and automatic schedule refresh upon import.
- Added empty-state call-to-action button allowing direct import if the database contains no activities.

---

## 2026-09-09 — Intelligence Layer & PM-Oriented Frontend MVP (Session 7)

**Session summary**: Built the complete Execution Intelligence Layer and Project Controls PM Minimal Frontend for SIH26122. Upgraded ontology schema, implemented deterministic predictions, human-gated terminology learning, safe grounded search, 5-tier provenance separation, and complete Next.js MVP pages.

### Backend & Intelligence Services
- **Database Schema (`backend/db/models.py`, `002_intelligence_layer.py`)**:
  - Added extensible `disciplines` lookup table (seeded with 21 ontology disciplines).
  - Added `organizations`, `contractors`, `people`, `equipment`, `materials`, `locations`, `activity_dependencies`, `entity_aliases`, `extracted_entities`.
  - Expanded `progress_events` with 25+ ontology fields, `provenance_category` (5 tiers), `confidence_tier`, `ontology_payload`, and `correction_history` JSON log.
  - Cross-database compatibility: wrapped JSON columns in `JSON().with_variant(JSONB, 'postgresql')` ensuring seamless migration in SQLite tests and Postgres production.
- **Consolidated Extraction (`prompts/extractor_v2.txt`, `llm_extractor.py`, `normalizer.py`)**:
  - Single consolidated LLM prompt extracting all 25+ ontology attributes, granular linked entities, and field-level confidence/evidence in a single call.
- **Contextual Matching & Terminology Gate (`prompts/reranker_v2.txt`, `confidence.py`, `terminology.py`)**:
  - Context-aware re-ranking prompt injecting location area, equipment tag, line number, contractor.
  - Clean human-gated terminology dictionary: unrecognized terms saved to `entity_aliases` as `status='proposed'` for planner review.
- **Deterministic Predictions & Analytics (`prediction_engine.py`, `schedule_intelligence.py`, `delay_intelligence.py`, `resource_intelligence.py`)**:
  - Mathematically calculated predicted delay days, finish date, variance factor, and risk score using historical discipline variance and CPM float consumption.
  - Synthesized plain-language explanatory narrative.
  - 12 standard delay causes breakdown, site bottleneck ranking, contractor delay ranking, recurring blockers.
- **Grounded Parameterized Search (`backend/services/search/nl_search.py`)**:
  - Safe by construction: parses query into constrained Pydantic filter object (`NLSearchFilters`), executes parameterized SQLAlchemy queries, returns direct links.
- **API Endpoints (`analysis.py`, `entities.py`, `search.py`, `review.py`)**:
  - `GET /api/v1/analysis/schedule-health`, `/delays`, `/resources`, `/predictions/{activity_id}`.
  - `GET /api/v1/entities/disciplines`, `/contractors`, `/equipment`, `/locations`, `/aliases`.
  - `POST /api/v1/search/natural`.
  - `POST /api/v1/review/alias/{id}/decide`, `POST /api/v1/review/{event_id}/re-edit`.
- **Scripts & Seeding**:
  - `scripts/seed_schedule.py`: Seeded 21 disciplines + 51 plan activities.
  - `scripts/seed_historical_events.py`: Generated 153 backdated progress events across 20 activities, 4 contractors, 5 equipment, 4 locations, 11 dependencies, and proposed aliases.
  - `scripts/backfill_extraction.py`: In-place re-extraction utility for historical documents.
- **Tests**:
  - `tests/test_intelligence_layer.py`: Added 5 unit tests for disciplines lookup, deterministic prediction engine, terminology normalization gate, grounded NL search, and post-approval re-editing.
  - All 39 tests passing cleanly across the entire test suite.

### Frontend MVP (Next.js 16 + TypeScript + Tailwind)
- **Palette & Aesthetics (`globals.css`)**:
  - Neutral dark engineering aesthetic: slate-950 background, crisp borders (`#1e293b`), restrained cyan accent (`#06b6d4`), compact monospace codes (`code-tag`), high density tables. Removed gradients and blobs.
- **Provenance Separation (`ProvenanceBadge.tsx`)**:
  - Renders 5 distinct visual categories: Source Fact, AI Extraction, AI Inference, Prediction, Human Approval with confidence score and evidence tooltip.
- **Grounded Search Bar (`NLSearchBar.tsx`)**:
  - Persistent header search bar with keyboard shortcut, query presets, parsed structured filter badges, and direct record linking.
- **Navigation (`Sidebar.tsx`)**:
  - Grouped into Overview, Execution (Schedule Gantt, Review Queue, All Progress), Analysis (Delay & Bottlenecks, Institutional Memory).
- **Overview Page (`app/page.tsx`)**:
  - 5 real stat cards (Schedule Progress % vs Plan, Critical Path Slippage Days, Total Ingested Updates, Review Queue Pending, Active Delay Blockers).
  - Schedule Health & Forecast card with EVM progress bar.
  - Milestone Tracker with baseline vs forecast dates.
  - Live field progress feed with provenance badges.
- **Schedule & Gantt Page (`app/schedule/page.tsx`, `GanttChart.tsx`, `ActivityDetailPanel.tsx`)**:
  - P6-style table with visual timeline bars comparing baseline vs actual.
  - Slide-out drawer displaying Activity Summary, Deterministic Mathematical Prediction Card (delay days, historical variance factor, predecessor float consumption, narrative), Linked Field Events, and Inline Planner Re-editing form.
- **Review Queue Page (`app/review/page.tsx`)**:
  - Dual tabs: Field Events (rapid action table with missing fields as "Not reported", Quick Accept, Change Match, Reject) and Terminology Proposals (one-click Approve / Reject for human-gated vocabulary learning).
- **Delay & Bottleneck Analysis Page (`app/analysis/delays/page.tsx`, `DelayCharts.tsx`)**:
  - 12 standard delay causes horizontal bar breakdown, bottleneck locations ranking, contractor variance ranking, recurring blockers table.
- **All Events Page (`app/events/page.tsx`)**:
  - Ingested audit register with provenance filter, discipline filter, search, and full ontology details.
- **Static Validation**:
  - `npm run build` completed with zero TypeScript errors across all routes.

## 2026-09-09 — Full Docker Multi-Container Update & Deployment

- **Container Image Rebuilds**:
  - `teamkranti-frontend`: Rebuilt multi-stage Next.js 16 standalone image with static optimization, hydration fixes, and defensive delay charts.
  - `teamkranti-backend`: Rebuilt with complete extended ontology, asyncpg, sentence-transformers, PyP6XER, and resilient database connection probe.
  - `teamkranti-worker`: Rebuilt with Celery worker runtime and updated matching/prediction dependencies.
- **Volume & Database Provisioning**:
  - Reset Docker PostgreSQL and Qdrant volumes to align cleanly with the 16-table extended schema (`plan_activities`, `progress_events`, `activity_dependencies`, `contractors`, `equipment_records`, `locations`, `terminology_aliases`, etc.).
  - Executed `scripts/seed_schedule.py` within Docker worker container: parsed synthetic P6 XER, seeded 51 activities, initialized sentence-transformer embeddings (all-MiniLM-L6-v2), and indexed in Qdrant.
  - Executed `scripts/seed_historical_events.py` within Docker worker container: seeded 153 backdated historical progress events, 4 contractors, 5 equipment records, 4 locations, and 11 schedule dependencies.
- **Verification & Health**:
  - Backend API (`http://localhost:8000/health`): status "ok", Qdrant "ok".
  - Schedule API (`http://localhost:8000/api/v1/schedule/activities`): 51 activities verified.
  - Delay Analytics API (`http://localhost:8000/api/v1/analysis/delays`): 56 delay events across 13 causes.
  - Frontend (`http://localhost:3000`): all pages (Overview, Schedule Gantt, Delay Analysis, Review Queue) returning HTTP 200.

---
- **OCR stack** (`backend/services/extraction/ocr.py`): Replaced single PaddleOCR engine with two deliberate engines — Tesseract (`pytesseract`) for typed/printed content, PP-OCRv5 (via PaddleOCR, CPU-only) for handwritten site diary photos. Documented in ARCHITECTURE.md with explicit table.
- **LLM flip** (`backend/services/extraction/llm_extractor.py`, `backend/services/matching/confidence.py`): Local Qwen3-8B via Ollama is now PRIMARY; Groq `qwen/qwen3-32b` is FALLBACK for both extraction and re-ranking. Qwen3 `<think>` block stripping added to both parsers.
- **Config rename**: `GROQ_MODEL_RERANK` → `GROQ_MODEL_FALLBACK` everywhere (config.py, .env.example, both call sites) — name reflects its dual-use role.
- **Qdrant** (`backend/services/institutional_memory/qdrant_store.py`): New file replacing ChromaDB. Two separate collections — `plan_activities` (matching index) and `progress_events` (institutional memory) — with ADR-012 explaining why they must stay separate.
- **Qdrant in compose**: `docker-compose.yml` updated with `qdrant` service, healthcheck, persistent volume, `QDRANT_URL` env injected into backend + worker.
- **Dockerfiles**: Tesseract (`tesseract-ocr`, `tesseract-ocr-eng`) added to both `Dockerfile.backend` and `Dockerfile.worker`.

### Functional gaps closed
- **A6 (Named reviewer identity)**: Added `POST /auth/login`, `POST /auth/logout` (`backend/api/v1/auth.py`). Frontend: new `/login` page (`frontend/app/login/page.tsx`), `Sidebar.tsx` updated to show reviewer name + sign-out button, `lib/api.ts` reads named token from localStorage with 401 auto-redirect.
- **A7 (Re-ranker fallback test)**: Added `TestRerankerFallback` class with 2 tests to `tests/test_matching.py`. Added `_call_local_llm` helper to `confidence.py` for testability.
- **A8 (Versioned prompt templates)**: Created `prompts/extractor_v1.txt` and `prompts/reranker_v1.txt` with headers documenting model, version, fusion weights, and Qwen3 handling notes.

### Config / infra
- `.env.example` fully updated: old Groq/Chroma/llama vars replaced with Qwen3/Qdrant/groq_fallback vars.
- `tests/conftest.py`: replaced stale `CHROMA_PERSIST_DIR` with `QDRANT_URL=:memory:`, `LOCAL_LLM_MODEL`, `GROQ_MODEL_FALLBACK`.

### Test fixes
- `test_normalize_percent_clamped_over_100`: uses `model_construct()` to bypass Pydantic `le=100` at construction — tests normalizer clamping, not schema validation.
- `test_groq_failure_triggers_ollama_fallback` → renamed `test_local_llm_failure_triggers_groq_fallback`, updated to patch `_call_local_llm`/`_call_groq_fallback` and new setting names.
- Reranker fallback tests: patches `_call_local_llm` directly (not raw `ollama.generate`) + uses `mocker.patch.object` for individual settings attributes (not whole object) to avoid MagicMock on float thresholds.
- Webhook "200-first" test: now sends valid HMAC signature + mocks `process_whatsapp_message.delay` (no live Redis needed in test env).

### Docs
- `ARCHITECTURE.md`: full rewrite with two-engine OCR table, two-collection Qdrant table, updated pipeline diagram and tech stack.
- `DECISIONS.md`: ADR-003, ADR-004, ADR-009 revised; ADR-011 (Qdrant replaces ChromaDB) and ADR-012 (two separate collections, rationale) added as required by user.
- `CURRENT_STATE.md`: all 15 layers marked done, final confirmed tech stack table, all A1-A8 gaps closed.
- Added `scripts/smoke_test_qwen3_extraction.py` — validates Qwen3-8B JSON output against Pydantic schemas on 5 synthetic message types before full demo run.

### Final test result: **34/34 passed** ✅

---

## 2026-09-08 — NVIDIA NIM LLM Swap (ADR-013)

**Session summary**: Replaced the Qwen3 + Groq dual-backend LLM stack with NVIDIA NIM `nvidia/nemotron-3-super-120b-a12b` as the sole backend. No local GPU required.

### Code changes
- **`backend/core/config.py`**: Removed `ollama_base_url`, `local_llm_model`, `groq_api_key`, `groq_model_fallback`. Added `nvidia_api_key`, `nvidia_nim_model`, `nvidia_nim_base_url`.
- **`backend/services/extraction/llm_extractor.py`**: Removed `_call_local_llm` + `_call_groq_fallback`. Added `_call_nvidia_nim` (OpenAI-compatible client against NVIDIA NIM, `enable_thinking=False`, `temperature=1.0, top_p=0.95`). `extract_activities()` now has a single NIM path — failure raises `ExtractionError` immediately (no silent fallback).
- **`backend/services/matching/confidence.py`**: Removed `_call_local_llm` (Ollama) + inline Groq block. Added `_call_nvidia_nim`. `_llm_rerank()` now has a single NIM path — failure falls back to equal-weighting (same as before).
- **`backend/requirements.txt`**: Removed `groq==0.12.0` and `ollama==0.4.1`. Added `openai>=1.40.0`.
- **`.env.example`**: Replaced Ollama + Groq LLM block with NVIDIA NIM block.
- **`prompts/extractor_v1.txt`** and **`prompts/reranker_v1.txt`**: Updated LLM header comments.

### Test changes
- **`tests/conftest.py`**: Replaced `GROQ_API_KEY`, `LOCAL_LLM_MODEL`, `GROQ_MODEL_FALLBACK` env defaults with `NVIDIA_API_KEY`, `NVIDIA_NIM_MODEL`, `NVIDIA_NIM_BASE_URL`.
- **`tests/test_matching.py`**: Rewrote `TestRerankerFallback` → `TestRerankerNvidiaNIM` with 2 tests: NIM success path (mocks `_call_nvidia_nim`) and NIM failure → equal-weighting path.
- **`tests/test_extraction_normalizer.py`**: Replaced `test_local_llm_failure_triggers_groq_fallback` with `test_nim_success_extracts_activities` (mocks `_call_nvidia_nim`, asserts `audit["llm_used"]` starts with `nvidia-nim/`).

### Memory docs updated
- `DECISIONS.md`: ADR-013 appended.
- `CURRENT_STATE.md`: Tech stack table + layer status rows updated.

---

## 2026-09-09 — Pipeline Stabilization (Session 5)

**Session summary**: Full inspection of the entire pipeline. Fixed all concrete bugs preventing correct WhatsApp→PostgreSQL matching. No architectural changes.

### Files changed

#### `backend/services/matching/confidence.py`
- **Bug 1 — Prompt (NEW fix)**: Rewrote `LLM_RERANK_PROMPT` to explicitly instruct the model:  
  "The activity_id must be ONLY the code (e.g. PIP-003) — copy from between the brackets. Do NOT include the activity name. Do NOT include brackets."
- **Bug 2 — ID normalizer (EXTENDED fix)**: Extracted `_normalize_llm_activity_id()` helper. Handles: bare IDs, `[PIP-003]`, `[PIP-003] Activity Name`, `"PIP-003"` (quoted). Added `valid_ids` set guard — unknown IDs (e.g. `PIP-999`) are logged as warnings and skipped, never mapped to a real candidate.
- **Bug 3 — Code-fence stripper (FIX)**: Replaced naive `[1:-1]` slice with the same defensive pattern as `llm_extractor.py` — only removes the closing ``` line if it's actually present.
- **Bug 4 — Score validation (NEW fix)**: Scores now clamped to `[0.0, 1.0]`. Non-numeric scores catch `TypeError/ValueError` per-item without killing the whole parse. Duplicate IDs logged at DEBUG and skipped. `overall_confidence` also clamped.
- **Bug 5 — Exception scope**: Replaced bare `except Exception` in parse path with `except (json.JSONDecodeError, KeyError, TypeError)` plus `raw` in warning log.

#### `backend/workers/tasks.py`
- **Bug 6**: Removed dead `SELECT` at line ~431 (result was discarded before `sa_update`).
- **Bug 7**: Removed dead `SELECT` in error handler at line ~503 (result was discarded before `sa_update`).
- **Bug 8**: Fixed stale log key `task.chroma_index_failed` → `task.qdrant_index_failed`.

#### `backend/services/institutional_memory/qdrant_store.py`
- **Bug 9 — Qdrant API Migration**: Replaced deprecated `client.search()` with `client.query_points()` and `query_vector` with `query`. Fixed `AttributeError` crashing the institutional memory query step of the demo script.

#### `frontend/app/` (schedule & memory pages)
- **Bug 10 — UI Export Auth**: Fixed a bug where clicking "Export XER" or "Export Dataset" failed with a 401 Unauthorized `Bearer token required.` error. The `fetch` calls were using a deprecated, empty `AUTH_TOKEN` constant instead of the dynamic `getAuthToken()` function.

### Files confirmed clean (no changes needed)
`fuzzy_matcher.py`, `semantic_matcher.py`, `llm_extractor.py`, `whatsapp.py`, `models.py`, `config.py`, `normalizer.py`, `session.py`, `requirements.txt`

### Root cause of regression
The matched score of 0.5178 (unmatched_new) was caused by the LLM returning `"[PIP-003] Hydrotest Line 24\"-XX (N12 to N20)"` as the `activity_id` field instead of `"PIP-003"`. The lookup `llm_scores.get("PIP-003", 0.0)` returned 0.0, so the 0.40 LLM weight was lost. After the fix: LLM score 1.0 → fused score ≈ 0.918 → `matched`.

---

## 2026-09-09 — Schedule Import Feature & Native XER Roundtrip (Session 6)

**Session summary**: Added schedule file import capabilities to allow planners/users to import `.xer` (Primavera P6) and schedule spreadsheet files (`.csv`, `.xlsx`, `.xls`) to directly view and work on activities in the UI. Built native XER parser and writer fallback to remove dependency fragility on PyP6Xer.

### Files changed

#### `backend/api/v1/schedule.py`
- Added `POST /api/v1/schedule/import` endpoint accepting `.xer`, `.csv`, `.xlsx`, `.xls`.
- Persists imported `.xer` to `data/synthetic/sample_schedule.xer` so that subsequent "Export XER" runs use the user's uploaded schedule.
- Parses activities, maps WBS codes and dates, infers disciplines if absent.
- Upserts activities into `plan_activities` table in PostgreSQL.
- Triggers `reload_matching_index(db)` so fuzzy/semantic matching immediately incorporates imported activities.
- Indexes activities into Qdrant vector store (`plan_activities` collection).

#### `backend/services/scheduling/xer_parser.py`
- Implemented `_parse_xer_native` parser to robustly read P6 tab-delimited tables (`%T TASK`, `%F`, `%R`) without external package failures.
- Maintained fallback structure so PyP6Xer is attempted first and gracefully falls back to native parser.

#### `backend/services/scheduling/xer_writer.py`
- Implemented `_apply_actuals_to_xer_native` to safely update `act_start_date`, `act_end_date`, and `phys_complete_pct` on `%R` rows under the `TASK` table while preserving all other project structures, tables, and calendars byte-for-byte.

#### `frontend/app/schedule/page.tsx`
- Added "Import Schedule" button alongside "Export XER".
- Added hidden file input supporting `.xer`, `.csv`, `.xlsx`, `.xls`.
- Connected file upload handler with `FormData` to `POST /api/v1/schedule/import` with Bearer auth.
- Added live loading state, success/error feedback banner with activity count, and automatic schedule refresh upon import.
- Added empty-state call-to-action button allowing direct import if the database contains no activities.

---

## 2026-09-09 — Intelligence Layer & PM-Oriented Frontend MVP (Session 7)

**Session summary**: Built the complete Execution Intelligence Layer and Project Controls PM Minimal Frontend for SIH26122. Upgraded ontology schema, implemented deterministic predictions, human-gated terminology learning, safe grounded search, 5-tier provenance separation, and complete Next.js MVP pages.

### Backend & Intelligence Services
- **Database Schema (`backend/db/models.py`, `002_intelligence_layer.py`)**:
  - Added extensible `disciplines` lookup table (seeded with 21 ontology disciplines).
  - Added `organizations`, `contractors`, `people`, `equipment`, `materials`, `locations`, `activity_dependencies`, `entity_aliases`, `extracted_entities`.
  - Expanded `progress_events` with 25+ ontology fields, `provenance_category` (5 tiers), `confidence_tier`, `ontology_payload`, and `correction_history` JSON log.
  - Cross-database compatibility: wrapped JSON columns in `JSON().with_variant(JSONB, 'postgresql')` ensuring seamless migration in SQLite tests and Postgres production.
- **Consolidated Extraction (`prompts/extractor_v2.txt`, `llm_extractor.py`, `normalizer.py`)**:
  - Single consolidated LLM prompt extracting all 25+ ontology attributes, granular linked entities, and field-level confidence/evidence in a single call.
- **Contextual Matching & Terminology Gate (`prompts/reranker_v2.txt`, `confidence.py`, `terminology.py`)**:
  - Context-aware re-ranking prompt injecting location area, equipment tag, line number, contractor.
  - Clean human-gated terminology dictionary: unrecognized terms saved to `entity_aliases` as `status='proposed'` for planner review.
- **Deterministic Predictions & Analytics (`prediction_engine.py`, `schedule_intelligence.py`, `delay_intelligence.py`, `resource_intelligence.py`)**:
  - Mathematically calculated predicted delay days, finish date, variance factor, and risk score using historical discipline variance and CPM float consumption.
  - Synthesized plain-language explanatory narrative.
  - 12 standard delay causes breakdown, site bottleneck ranking, contractor delay ranking, recurring blockers.
- **Grounded Parameterized Search (`backend/services/search/nl_search.py`)**:
  - Safe by construction: parses query into constrained Pydantic filter object (`NLSearchFilters`), executes parameterized SQLAlchemy queries, returns direct links.
- **API Endpoints (`analysis.py`, `entities.py`, `search.py`, `review.py`)**:
  - `GET /api/v1/analysis/schedule-health`, `/delays`, `/resources`, `/predictions/{activity_id}`.
  - `GET /api/v1/entities/disciplines`, `/contractors`, `/equipment`, `/locations`, `/aliases`.
  - `POST /api/v1/search/natural`.
  - `POST /api/v1/review/alias/{id}/decide`, `POST /api/v1/review/{event_id}/re-edit`.
- **Scripts & Seeding**:
  - `scripts/seed_schedule.py`: Seeded 21 disciplines + 51 plan activities.
  - `scripts/seed_historical_events.py`: Generated 153 backdated progress events across 20 activities, 4 contractors, 5 equipment, 4 locations, 11 dependencies, and proposed aliases.
  - `scripts/backfill_extraction.py`: In-place re-extraction utility for historical documents.
- **Tests**:
  - `tests/test_intelligence_layer.py`: Added 5 unit tests for disciplines lookup, deterministic prediction engine, terminology normalization gate, grounded NL search, and post-approval re-editing.
  - All 39 tests passing cleanly across the entire test suite.

### Frontend MVP (Next.js 16 + TypeScript + Tailwind)
- **Palette & Aesthetics (`globals.css`)**:
  - Neutral dark engineering aesthetic: slate-950 background, crisp borders (`#1e293b`), restrained cyan accent (`#06b6d4`), compact monospace codes (`code-tag`), high density tables. Removed gradients and blobs.
- **Provenance Separation (`ProvenanceBadge.tsx`)**:
  - Renders 5 distinct visual categories: Source Fact, AI Extraction, AI Inference, Prediction, Human Approval with confidence score and evidence tooltip.
- **Grounded Search Bar (`NLSearchBar.tsx`)**:
  - Persistent header search bar with keyboard shortcut, query presets, parsed structured filter badges, and direct record linking.
- **Navigation (`Sidebar.tsx`)**:
  - Grouped into Overview, Execution (Schedule Gantt, Review Queue, All Progress), Analysis (Delay & Bottlenecks, Institutional Memory).
- **Overview Page (`app/page.tsx`)**:
  - 5 real stat cards (Schedule Progress % vs Plan, Critical Path Slippage Days, Total Ingested Updates, Review Queue Pending, Active Delay Blockers).
  - Schedule Health & Forecast card with EVM progress bar.
  - Milestone Tracker with baseline vs forecast dates.
  - Live field progress feed with provenance badges.
- **Schedule & Gantt Page (`app/schedule/page.tsx`, `GanttChart.tsx`, `ActivityDetailPanel.tsx`)**:
  - P6-style table with visual timeline bars comparing baseline vs actual.
  - Slide-out drawer displaying Activity Summary, Deterministic Mathematical Prediction Card (delay days, historical variance factor, predecessor float consumption, narrative), Linked Field Events, and Inline Planner Re-editing form.
- **Review Queue Page (`app/review/page.tsx`)**:
  - Dual tabs: Field Events (rapid action table with missing fields as "Not reported", Quick Accept, Change Match, Reject) and Terminology Proposals (one-click Approve / Reject for human-gated vocabulary learning).
- **Delay & Bottleneck Analysis Page (`app/analysis/delays/page.tsx`, `DelayCharts.tsx`)**:
  - 12 standard delay causes horizontal bar breakdown, bottleneck locations ranking, contractor variance ranking, recurring blockers table.
- **All Events Page (`app/events/page.tsx`)**:
  - Ingested audit register with provenance filter, discipline filter, search, and full ontology details.
- **Static Validation**:
  - `npm run build` completed with zero TypeScript errors across all routes.

## 2026-09-09 — Full Docker Multi-Container Update & Deployment

- **Container Image Rebuilds**:
  - `teamkranti-frontend`: Rebuilt multi-stage Next.js 16 standalone image with static optimization, hydration fixes, and defensive delay charts.
  - `teamkranti-backend`: Rebuilt with complete extended ontology, asyncpg, sentence-transformers, PyP6XER, and resilient database connection probe.
  - `teamkranti-worker`: Rebuilt with Celery worker runtime and updated matching/prediction dependencies.
- **Volume & Database Provisioning**:
  - Reset Docker PostgreSQL and Qdrant volumes to align cleanly with the 16-table extended schema (`plan_activities`, `progress_events`, `activity_dependencies`, `contractors`, `equipment_records`, `locations`, `terminology_aliases`, etc.).
  - Executed `scripts/seed_schedule.py` within Docker worker container: parsed synthetic P6 XER, seeded 51 activities, initialized sentence-transformer embeddings (all-MiniLM-L6-v2), and indexed in Qdrant.
  - Executed `scripts/seed_historical_events.py` within Docker worker container: seeded 153 backdated historical progress events, 4 contractors, 5 equipment records, 4 locations, and 11 schedule dependencies.
- **Verification & Health**:
  - Backend API (`http://localhost:8000/health`): status "ok", Qdrant "ok".
  - Schedule API (`http://localhost:8000/api/v1/schedule/activities`): 51 activities verified.
  - Delay Analytics API (`http://localhost:8000/api/v1/analysis/delays`): 56 delay events across 13 causes.
  - Frontend (`http://localhost:3000`): all pages (Overview, Schedule Gantt, Delay Analysis, Review Queue) returning HTTP 200.

---

## 2026-09-11 — Kranti UI Layout Refinements

**Session summary**: Implemented the "Kranti" vs "Legacy P6" dual-layout toggle and refined the Insights and Ingestion Feed sections on the frontend.

### Frontend UI Updates
- **Layout Switcher**: Added a top navigation toggle in `frontend/app/page.tsx` allowing users to switch between the original "Legacy P6" view and the new "Kranti" dashboard layout.
- **AI Insights Space**: Upgraded the Schedule Variance Trend graph to include 14 data points, descriptive Y-axis (+20d to 0d) and X-axis (Weeks 1-14) labels, hover tooltips for individual data points, and additional realistic key risk factors.
- **Ingestion Feed**: Updated parsing logic to display the complete raw message submitted by field engineers rather than truncating it with ellipsis.
- **Gantt Timeline**: Made timeline bars interactive — clicking a bar automatically highlights the corresponding activity and switches the view back to the Project Hierarchy. Added activity IDs to the hover tooltips.
- **Project Hierarchy**: Added 'Start' and 'End' date columns, seamlessly falling back from actual dates to planned dates as necessary.
