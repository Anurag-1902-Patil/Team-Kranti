# SIH26122 — Intelligent Data Capture & Schedule-Linking Layer
**Team Kranti | Smart India Hackathon 2026**

> Field supervisors send progress updates via WhatsApp (text/photo/voice/spreadsheet).  
> This system extracts structured activity events, fuzzy-matches them to Primavera P6 L5/L6 activities, confidence-gates them through human review, and writes validated actuals back into the schedule via XER.

---

## Architecture at a Glance

```
WhatsApp Cloud API
      │
      ▼ webhook (HMAC-verified)
 FastAPI Backend ──► Celery Worker
      │                   │
      │         ┌─────────┼─────────────┐
      │         ▼         ▼             ▼
      │     ASR (Whisper) OCR (Paddle/  LLM Extractor
      │                   Groq Vision)  (Groq → Ollama)
      │                       │
      │                       ▼
      │               Normalizer (§3.4)
      │                       │
      │        ┌──────────────┼──────────────┐
      │        ▼              ▼              ▼
      │   RapidFuzz     Sentence-Xformers  Groq LLM
      │   (fuzzy)       (semantic)         (re-rank)
      │        └──────────── ▼ ─────────────┘
      │              Confidence Router
      │             (0.85→auto / 0.55→review / else→new)
      │                       │
      ├── PostgreSQL ◄─────────┤
      ├── ChromaDB  ◄─────────┘
      │
      ▼
 Next.js Reviewer Dashboard
      │
      ▼ (POST /review/{id}/accept|edit|decline|confirm_new)
 Schedule Write-back → P6 XER Export
```

**No P6 API.** Round-trip is: `P6 export .XER → our platform → updated .XER → planner re-imports`.

---

## Quick Start

### Prerequisites
- Docker Desktop
- A Groq API key (free tier at console.groq.com)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY at minimum
```

### 2. Start services

```bash
docker-compose up -d
```

Services started:
| Service | URL |
|---|---|
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| MinIO Console | http://localhost:9001 (admin/minioadmin) |
| FastAPI Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Next.js Dashboard | http://localhost:3000 |

### 3. Initialize the database

```bash
# In the backend container (or with Python + venv):
cd backend
alembic upgrade head
```

### 4. Seed synthetic schedule

```bash
python scripts/seed_schedule.py
```

This loads 20 synthetic L5/L6 plan activities, builds the semantic embedding index, and seeds sender profiles.

### 5. Run the end-to-end demo

```bash
python scripts/run_demo.py
```

Injects 3 synthetic messages (free text, XLSX, scanned diary simulation), runs the full pipeline, and shows the review queue output.

### 6. Open the reviewer dashboard

Navigate to **http://localhost:3000** → Review Queue.

---

## Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Start FastAPI
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A backend.workers.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

---

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v
```

Tests use SQLite in-memory — no Postgres/Redis needed.

Key test files:
- `tests/test_extraction_normalizer.py` — LLM extractor parsing and normalization
- `tests/test_matching.py` — Fuzzy + semantic + confidence routing
- `tests/test_webhook_security.py` — HMAC validation

---

## Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/webhooks/whatsapp` | Meta verification challenge |
| `POST` | `/webhooks/whatsapp` | Receive WhatsApp messages |
| `GET` | `/api/v1/events` | List progress events |
| `GET` | `/api/v1/events/{id}` | Event detail + match candidates |
| `GET` | `/api/v1/review/queue` | Events pending review |
| `POST` | `/api/v1/review/{id}/accept` | Accept match |
| `POST` | `/api/v1/review/{id}/edit` | Correct to different activity |
| `POST` | `/api/v1/review/{id}/decline` | Decline event |
| `POST` | `/api/v1/review/{id}/confirm_new` | Confirm as new field activity |
| `GET` | `/api/v1/schedule/activities` | List plan activities |
| `POST` | `/api/v1/schedule/activities` | Create new plan activity |
| `GET` | `/api/v1/schedule/export-xer` | Download updated XER |
| `GET` | `/api/v1/memory/query?q=...` | Semantic memory search |
| `GET` | `/api/v1/memory/export` | Export Parquet + CSV + SCHEMA.md |

Full interactive docs at `http://localhost:8000/docs`.

---

## Repository Structure

```
c:\coding\Team Kranti\
├── backend/
│   ├── main.py                     # FastAPI app
│   ├── core/config.py              # Pydantic settings
│   ├── db/
│   │   ├── models.py               # SQLAlchemy ORM (7 tables)
│   │   └── session.py              # Async session factory
│   ├── api/v1/
│   │   ├── webhook.py              # WhatsApp webhook
│   │   ├── events.py               # Events list/detail
│   │   ├── review.py               # Human review actions
│   │   ├── schedule.py             # Schedule + XER export
│   │   └── memory.py               # Institutional memory
│   ├── services/
│   │   ├── ingestion/              # WhatsApp parser, media download/upload
│   │   ├── extraction/             # ASR, OCR, LLM extractor, normalizer
│   │   ├── matching/               # Fuzzy, semantic, confidence scoring
│   │   ├── scheduling/             # XER parser/writer, schedule service
│   │   └── institutional_memory/   # ChromaDB store, dataset exporter
│   ├── workers/
│   │   ├── celery_app.py           # Celery configuration
│   │   └── tasks.py                # Pipeline orchestration task
│   ├── security/hmac.py            # HMAC-SHA256 validation
│   └── alembic/                    # DB migrations
├── frontend/                       # Next.js 15 reviewer dashboard
│   └── app/
│       ├── page.tsx                # Dashboard
│       ├── events/                 # Event list
│       ├── review/                 # Review queue (all 4 actions)
│       ├── schedule/               # Plan activities + XER export
│       └── memory/                 # Semantic search + dataset export
├── data/
│   ├── SCHEMA.md                   # Dataset data dictionary
│   └── synthetic/                  # Synthetic XER, messages, sender profiles
├── scripts/
│   ├── seed_schedule.py            # Load XER + build embedding index
│   └── run_demo.py                 # End-to-end demo runner
├── tests/                          # pytest test suite
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.worker
├── .env.example
└── .ai/                            # Project memory (architecture docs)
```

---

## Confidence Threshold Logic

| Score | Routing |
|---|---|
| ≥ 0.85 | Auto-accepted → schedule write-back + ChromaDB |
| 0.55 – 0.84 | Sent to review queue for planner decision |
| < 0.55 | Flagged as `unmatched_new` — planner confirms or creates new activity |

Thresholds configurable via `MATCH_AUTO_ACCEPT_THRESHOLD` and `MATCH_REVIEW_THRESHOLD` env vars.

---

## Notes for Judges

1. **No P6 API** — XER round-trip per problem statement constraints
2. **Real LLM pipeline** — Groq (llama-3.1-70b) primary, Ollama (llama3.2:3b) local fallback
3. **3 input formats** — free text DPR, XLSX spreadsheet, scanned diary (OCR/vision)
4. **Audit trail** — every matching decision stored (all candidates + scores + LLM justification)
5. **Institutional memory** — validated events → ChromaDB → semantic search → Parquet export
6. **Security** — HMAC-SHA256 webhook validation, idempotency via `ON CONFLICT` guards
7. **Confirm-new loop** — unmatched activities promoted to plan, immediately embeddable for future matching

All data is synthetic. No real Oil India project data was used.
