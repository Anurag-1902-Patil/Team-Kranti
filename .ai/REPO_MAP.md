# REPO_MAP.md — All files and what they do

## Backend (`backend/`)

| File | Purpose |
|---|---|
| `main.py` | FastAPI app factory, lifespan hooks, router registration |
| `core/config.py` | Pydantic Settings — reads all env vars |
| `logging_config.py` | Structured JSON logging via structlog |

### DB (`backend/db/`)
| File | Purpose |
|---|---|
| `models.py` | SQLAlchemy 2.0 ORM — 7 tables: users, sender_profiles, plan_activities, documents, progress_events, matches, review_decisions |
| `session.py` | Async session factory, FastAPI get_db dependency |

### API (`backend/api/`)
| File | Purpose |
|---|---|
| `deps.py` | Shared FastAPI dependencies — get_db, get_current_user (Bearer token) |
| `v1/webhook.py` | GET/POST /webhooks/whatsapp — HMAC verify, idempotency, Celery enqueue |
| `v1/events.py` | GET /events (list + filter), GET /events/{id} (detail + candidates) |
| `v1/review.py` | POST /review/{id}/accept|edit|decline|confirm_new, GET /review/queue, POST /review/alias/{id}/decide, POST /review/{id}/re-edit |
| `v1/schedule.py` | GET /schedule/activities, POST /schedule/activities, GET /schedule/export-xer, POST /schedule/import |
| `v1/analysis.py` | GET /analysis/schedule-health, /delays, /resources, /predictions/{activity_id} |
| `v1/entities.py` | GET /entities/disciplines, /contractors, /equipment, /locations, /aliases |
| `v1/search.py` | POST /search/natural (safe grounded parameterized search) |
| `v1/memory.py` | GET /memory/query, GET /memory/export (ZIP), GET /memory/stats |

### Services (`backend/services/`)

**analytics/**
| File | Purpose |
|---|---|
| `prediction_engine.py` | Computes deterministic delay days, finish date, variance factor, risk score, and narrative |
| `schedule_intelligence.py` | Computes schedule health, EVM progress, critical path float consumption |
| `delay_intelligence.py` | Analyzes 12 root cause delay categories, bottleneck areas, contractor delay rankings |
| `resource_intelligence.py` | Analyzes observed vs inferred manpower, equipment status |

**search/**
| File | Purpose |
|---|---|
| `nl_search.py` | Grounded search parser: free text → constrained Pydantic filter → parameterized SQLAlchemy |

**matching/**
| File | Purpose |
|---|---|
| `fuzzy_matcher.py` | RapidFuzz token_sort_ratio + partial_ratio, top-k candidates |
| `semantic_matcher.py` | Sentence-Transformers all-MiniLM-L6-v2, in-memory embedding matrix, cosine similarity |
| `confidence.py` | Contextual re-ranking prompt, LLM re-rank, 0.3/0.3/0.4 fusion, threshold routing |
| `terminology.py` | Human-gated entity alias lookup and proposed alias submission |

**extraction/**
| File | Purpose |
|---|---|
| `asr.py` | faster-whisper ASR — audio bytes → transcript (lazy model load singleton) |
| `ocr.py` | Tesseract (printed), PP-OCRv5 (handwritten), pdfplumber/pdf2image (PDFs), pandas (XLSX/CSV) |
| `llm_extractor.py` | NVIDIA NIM Nemotron single-pass consolidated extractor (25+ ontology fields) |
| `normalizer.py` | Maps 21 disciplines, constructs ProgressEventCreate with ontology payload & confidence tier |

### Alembic (`backend/alembic/`)
| File | Purpose |
|---|---|
| `env.py` | Reads DATABASE_URL_SYNC, imports Base for autogenerate |
| `versions/001_initial_schema.py` | Creates initial 7 tables, indexes, enums |
| `versions/002_intelligence_layer.py` | Adds 9 relational entity tables, expands progress_events with 25+ fields |

## Frontend (`frontend/`)
| File | Purpose |
|---|---|
| `app/layout.tsx` | Root layout with dark engineering theme, Sidebar, and top NLSearchBar header |
| `app/globals.css` | Neutral slate-950 palette, provenance badge tokens, compact table styles |
| `app/page.tsx` | Overview Dashboard MVP — 5 real stat cards, schedule health, milestone tracker, provenance feed |
| `app/schedule/page.tsx` | Primavera P6 schedule view with Gantt chart, activity detail slide-out, XER import/export |
| `app/review/page.tsx` | Planner Review Queue MVP — dual tabs for field events (rapid action) and terminology proposals |
| `app/analysis/delays/page.tsx` | Delay & Bottleneck Analysis MVP — 12 root causes, bottleneck locations, contractor ranking |
| `app/events/page.tsx` | All progress events audit register with provenance and discipline filters |
| `components/Sidebar.tsx` | Navigation grouped into Overview, Execution, and Analysis |
| `components/ProvenanceBadge.tsx` | 5-tier provenance visual badges (Source Fact, AI Extraction, Inference, Prediction, Approval) |
| `components/NLSearchBar.tsx` | Grounded natural language search input with parsed filter pills & direct record linking |
| `components/GanttChart.tsx` | High-density schedule table with visual baseline vs actual progress timeline bars |
| `components/ActivityDetailPanel.tsx` | Activity detail slide-out drawer with deterministic prediction card & inline planner re-editing |
| `components/DelayCharts.tsx` | 12 standard delay causes breakdown, site bottleneck ranking, recurring blockers |
| `lib/api.ts` | Typed client for all analysis, predictions, entities, search, and review endpoints |
| `lib/types.ts` | Complete TypeScript interfaces for the full ontology and intelligence layer |
| `Dockerfile` | Multi-stage build → minimal runtime |

## Data (`data/`)
| File | Purpose |
|---|---|
| `SCHEMA.md` | Dataset data dictionary (full column definitions) |
| `synthetic/sender_profiles.json` | 5 synthetic WhatsApp sender → discipline mappings |
| `synthetic/whatsapp_messages.json` | 5 synthetic webhook payloads (3 text + 1 XLSX + 1 image) |
| `synthetic/sample_schedule.xer` | Synthetic P6 XER with 20 L5/L6 activities (generated by seed script) |

## Scripts (`scripts/`)
| File | Purpose |
|---|---|
| `seed_schedule.py` | Load XER → DB, build embedding index, seed ChromaDB, seed sender profiles |
| `run_demo.py` | End-to-end demo — injects 3 formats, traces pipeline, shows queue |

## Tests (`tests/`)
| File | Purpose |
|---|---|
| `conftest.py` | SQLite in-memory DB fixtures, FastAPI test client |
| `test_extraction_normalizer.py` | Normalizer happy path + edge cases, LLM extractor parsing |
| `test_matching.py` | Fuzzy/semantic/confidence routing integration tests |
| `test_webhook_security.py` | HMAC validation (6 cases) + webhook endpoint tests |

## Infrastructure
| File | Purpose |
|---|---|
| `docker-compose.yml` | Postgres + Redis + MinIO + backend + worker + frontend |
| `Dockerfile.backend` | Python 3.11 slim + system deps (PaddleOCR, poppler, ffmpeg) |
| `Dockerfile.worker` | Same as backend, runs Celery |
| `.env.example` | All env var templates with documentation |

## Memory (`/.ai/`)
| File | Purpose |
|---|---|
| `ARCHITECTURE.md` | High-level system design |
| `DATA_MODEL.md` | Database tables and columns |
| `API_CONTRACTS.md` | Endpoint contracts |
| `WORKFLOWS.md` | Pipeline step-by-step |
| `DECISIONS.md` | Architecture decisions log |
| `CURRENT_STATE.md` | Build progress |
| `CHANGELOG.md` | AI-driven changes log |
| `REPO_MAP.md` | This file |
