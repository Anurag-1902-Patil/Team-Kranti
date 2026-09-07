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
| `v1/review.py` | POST /review/{id}/accept|edit|decline|confirm_new, GET /review/queue |
| `v1/schedule.py` | GET /schedule/activities, POST /schedule/activities, GET /schedule/export-xer |
| `v1/memory.py` | GET /memory/query, GET /memory/export (ZIP), GET /memory/stats |

### Schemas (`backend/schemas/`)
| File | Purpose |
|---|---|
| `event.py` | ProgressEventCreate, ProgressEventOut, ProgressEventListOut, MatchCandidateSchema |
| `review.py` | ReviewAcceptRequest, ReviewEditRequest, ReviewDeclineRequest, ReviewConfirmNewRequest, ReviewDecisionOut |
| `schedule.py` | PlanActivityOut, PlanActivityCreate, PlanActivityListOut, XERExportOut |

### Services (`backend/services/`)

**ingestion/**
| File | Purpose |
|---|---|
| `whatsapp.py` | Parses Meta webhook payloads → typed WAMessage models |
| `media.py` | Downloads from WhatsApp CDN, uploads to MinIO, generates presigned URLs |

**extraction/**
| File | Purpose |
|---|---|
| `asr.py` | faster-whisper ASR — audio bytes → transcript (lazy model load singleton) |
| `ocr.py` | PaddleOCR (printed), Groq vision (handwritten), pdfplumber/pdf2image (PDFs), pandas (XLSX/CSV) |
| `llm_extractor.py` | Groq primary / Ollama fallback LLM extractor with few-shot prompt, retry, JSON parsing |
| `normalizer.py` | Maps ExtractedActivity → ProgressEventCreate with enum validation, datetime parsing |

**matching/**
| File | Purpose |
|---|---|
| `fuzzy_matcher.py` | RapidFuzz token_sort_ratio + partial_ratio, top-k candidates |
| `semantic_matcher.py` | Sentence-Transformers all-MiniLM-L6-v2, in-memory embedding matrix, cosine similarity |
| `confidence.py` | Merge fuzzy+semantic, LLM re-rank (Groq/Ollama), score fusion 0.3/0.3/0.4, threshold routing |

**scheduling/**
| File | Purpose |
|---|---|
| `xer_parser.py` | PyP6XER → plan_activities dicts with discipline inference |
| `xer_writer.py` | Apply actual_start/finish/pct to XER, write output file |
| `schedule_service.py` | DB write-back, new activity creation (confirm_new), index reload |

**institutional_memory/**
| File | Purpose |
|---|---|
| `chroma_store.py` | ChromaDB persistent client — progress_events + plan_activities collections |
| `exporter.py` | Postgres → Parquet + CSV + SCHEMA.md + summary_stats.json |

### Workers (`backend/workers/`)
| File | Purpose |
|---|---|
| `celery_app.py` | Celery config — Redis broker, late ACK, time limits |
| `tasks.py` | process_whatsapp_message — full 10-step pipeline, 3-attempt retry with exponential backoff |

### Security (`backend/security/`)
| File | Purpose |
|---|---|
| `hmac.py` | HMAC-SHA256 constant-time verification for Meta webhook |

### Alembic (`backend/alembic/`)
| File | Purpose |
|---|---|
| `env.py` | Reads DATABASE_URL_SYNC, imports Base for autogenerate |
| `versions/001_initial_schema.py` | Creates all 7 tables, indexes, enums |

## Frontend (`frontend/`)
| File | Purpose |
|---|---|
| `app/layout.tsx` | Root layout — dark theme, Inter font, sidebar |
| `app/globals.css` | Tailwind + custom CSS: glass-card, badge colors, chip colors, gradient |
| `app/page.tsx` | Dashboard — stats cards, review queue preview, recent events |
| `app/events/page.tsx` | Events list — status/discipline filters, confidence bars, pagination |
| `app/review/page.tsx` | Review queue — split view with all 4 actions |
| `app/schedule/page.tsx` | Plan activities + XER export button |
| `app/memory/page.tsx` | Semantic query, stats, results, dataset export |
| `components/Sidebar.tsx` | Navigation sidebar with active state |
| `components/ConfidenceBadge.tsx` | ConfidenceBadge, DisciplineChip, ConfidenceBar |
| `lib/api.ts` | API client helpers — base URL, auth headers, typed fetch |
| `lib/types.ts` | TypeScript interfaces for all API entities |
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
