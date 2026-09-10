# SIH26122 — Intelligent Data Capture & Schedule-Linking Layer
**Team Kranti | Smart India Hackathon 2026**

> **What this is**: Field supervisors send progress updates via WhatsApp (text, voice notes, photos, or spreadsheets). This system extracts structured activity events with full engineering ontology, fuzzy-matches them to Primavera P6 L5/L6 activities, confidence-gates them through human review, and writes validated actuals back into the schedule via XER.

---

## 🏛️ Architecture at a Glance

```
WhatsApp Cloud API
       │
       ▼ webhook (HMAC-verified, 200-first)
 FastAPI Backend ──► Celery Worker
       │                   │
       │         ┌─────────┼─────────────┐
       │         ▼         ▼             ▼
       │     ASR (Whisper) OCR (Tesseract LLM Extractor (NVIDIA NIM
       │                   & PP-OCRv5)     Nemotron-3-Super-120B)
       │                       │
       │                       ▼
       │               Normalizer (§3.4 Extended Ontology)
       │                       │
       │        ┌──────────────┼──────────────┐
       │        ▼              ▼              ▼
       │   RapidFuzz     Sentence-Xformers  LLM Re-ranker
       │   (fuzzy)       (semantic 384d)   (context-aware)
       │        └──────────── ▼ ─────────────┘
       │              Confidence Router
       │             (≥0.85→auto / 0.55-0.84→review / <0.55→new)
       │                       │
       ├── PostgreSQL 16 ◄─────┤
       ├── Qdrant Vector DB ◄──┘ (2 collections: plan_activities + progress_events)
       ├── MinIO S3 (raw media & transcripts)
       │
       ▼
 Next.js 16 PM Dashboard
  ├── P6-Style Gantt Timeline & Predecessor Float Tracking
  ├── 5-Tier Provenance Badges (Fact, AI Extract, AI Infer, Predict, Approved)
  ├── Review Queue (Rapid Action Table + Controlled Vocabulary Proposals)
  ├── Delay & Bottleneck Intelligence (12 standard causes, contractor rankings)
  └── Grounded Natural-Language Search
       │
       ▼ (POST /review/{id}/accept|edit|decline|confirm_new)
 Schedule Write-back ──► Native Primavera P6 .XER Export
```

> **Non-negotiable Constraint**: **No P6 API.** Round-trip is: `P6 export .XER → our platform → updated .XER → planner re-imports into Primavera P6`.

---

## 📋 System Requirements & Prerequisites

Ensure your host machine or VM has:
* **Operating System**: Windows 10/11 (with WSL2 or Docker Desktop), macOS, or Ubuntu 22.04/24.04 LTS.
* **Git**: Installed ([git-scm.com](https://git-scm.com/)).
* **Docker & Docker Compose**: Installed and running ([docker.com](https://www.docker.com/)).
* **Recommended Specs**: 4 vCPU cores, 8 GB+ RAM.

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
docker-compose up -d --build
```
*(Note: If you are pulling new changes from a teammate's fork, ensure you include `--build` to rebuild the frontend UI container.)*

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

### 4. Seed synthetic schedule & demo data

```bash
python scratch/drop_tables.py      # Clears existing data
python scripts/seed_schedule.py    # Loads schedule & shifts dates
python scripts/seed_demo_events.py # Seeds review queue for UI demo
```

This loads synthetic L5/L6 plan activities (shifted to August 2026), builds the semantic embedding index, and populates the UI with realistic events.

### 5. Run the end-to-end simulation (Optional)

```bash
python scripts/run_demo.py
```

Injects 3 synthetic messages (free text, XLSX, scanned diary simulation), runs the full pipeline, and adds to the review queue.

### 6. Open the reviewer dashboard

Navigate to **http://localhost:3000** to view the unified dashboard.

---

## 🚀 Step-by-Step Setup Guide

### Step 1: Clone the Repository

Open your terminal (PowerShell, Bash, or Zsh) and run:

```bash
git clone https://github.com/Anurag-1902-Patil/Team-Kranti.git
cd Team-Kranti
```

---

### Step 2: Configure Environment Variables (`.env`)

Create your `.env` configuration file from the provided template:

* **On Linux / macOS / Ubuntu:**
  ```bash
  cp .env.example .env
  ```
* **On Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```

Open `.env` in any editor to verify the settings:
```env
# Database & Queues (Pre-configured for Docker out-of-the-box)
DATABASE_URL=postgresql+asyncpg://kranti:kranti_secret@localhost:5432/sih26122
DATABASE_URL_SYNC=postgresql+psycopg2://kranti:kranti_secret@localhost:5432/sih26122
REDIS_URL=redis://localhost:6379/0

# LLM Extraction: NVIDIA NIM (Primary)
NVIDIA_API_KEY=
NVIDIA_NIM_MODEL=
# Meta WhatsApp Cloud API (Pre-configured for prototype testing)
WHATSAPP_APP_SECRET=
WHATSAPP_VERIFY_TOKEN=s
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=

# Matching Thresholds
MATCH_AUTO_ACCEPT_THRESHOLD=0.85
MATCH_REVIEW_THRESHOLD=0.55
REVIEWER_TOKEN=dev-insecure-token
```

---

### Step 3: Build & Start All 7 Containers

Launch the full stack in detached mode:

```bash
docker compose up -d --build
```

#### Verify that all services are healthy:
```bash
docker compose ps
```
You should see all 7 containers in `Up` or `Up (healthy)` state:
| Container | Service | Port | Description |
|---|---|---|---|
| `sih26122-frontend` | Next.js 16 PM UI | `3000` | Reviewer Dashboard, P6 Gantt, Delay Analytics |
| `sih26122-backend` | FastAPI REST API | `8000` | Ingestion webhooks, prediction engine, matching |
| `sih26122-worker` | Celery Worker | Background | ASR (Whisper), NLP parsing, Qdrant indexing |
| `sih26122-postgres`| PostgreSQL 16 | `5432` | Relational store for schedules & progress events |
| `sih26122-qdrant` | Qdrant Vector DB | `6333`/`6334` | Semantic matching & Institutional memory |
| `sih26122-redis` | Redis 7 | `6379` | Queue broker for Celery tasks |
| `sih26122-minio` | MinIO Object Store| `9000`/`9001`| S3 storage for site photos, voice notes, & reports |

---

### Step 4: Seed the Schedule & Historical Intelligence (Mandatory)

Run these two commands to parse the synthetic Primavera P6 schedule (`sample_schedule.xer`), compute vector embeddings, and seed historical progress events:

```bash
# 1. Parse P6 XER, seed 21 disciplines & 51 activities, and index in Qdrant:
docker compose exec worker python scripts/seed_schedule.py

# 2. Seed 153 backdated historical progress events, contractors, equipment & delay data:
docker compose exec worker python scripts/seed_historical_events.py
```

---

### Step 5: Access the Web Interfaces

Open your browser:

| Interface | URL | What you can do |
|---|---|---|
| **Overview Dashboard** | [http://localhost:3000](http://localhost:3000) | Live schedule stats, EVM progress curve, slippage days |
| **P6 Gantt Schedule** | [http://localhost:3000/schedule](http://localhost:3000/schedule) | P6 timeline table, activity drawers, inline planner edit, XER import/export |
| **Review Queue** | [http://localhost:3000/review](http://localhost:3000/review) | Validate field updates, confidence scores, approve terminology proposals |
| **Delay Analysis** | [http://localhost:3000/analysis/delays](http://localhost:3000/analysis/delays) | 12 standard delay causes breakdown, contractor variance ranking |
| **Institutional Memory**| [http://localhost:3000/memory](http://localhost:3000/memory) | Grounded natural language search & Parquet/CSV dataset export |
| **Swagger API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive REST API documentation |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | S3 storage explorer (`minioadmin` / `minioadmin`) |

---

## 💬 Step 6: Testing WhatsApp Message & Voice Ingestion

### A. Instant Local Simulation (No phone/tunnel required)
You can test the entire pipeline right from your command line using the included simulator script:

* **Simulate a text progress update:**
  ```bash
  python scripts/simulate_whatsapp.py --text "Spool erection for Line 24-XX completed today at chainage 12+450 with 8 welders deployed by ABC Infra"
  ```
* **Simulate a voice note (.ogg, .mp3, .wav):**
  ```bash
  python scripts/simulate_whatsapp.py --audio "path/to/voice_update.ogg"
  ```
* **Interactive Terminal Chat Mode:**
  ```bash
  python scripts/simulate_whatsapp.py --interactive
  ```
Open [http://localhost:3000/review](http://localhost:3000/review) to see the update land live with provenance badges and match confidence!

> 💡 **Live Mobile Phone Integration**: To receive updates directly from a physical smartphone over the Meta WhatsApp Cloud API, see the webhook tunnel configuration in [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 🧪 Running Automated Tests

The test suite validates the intelligence layer, normalizer, matching engine, and security without requiring external services (uses SQLite in-memory):

```bash
# In your local Python environment:
pip install pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v

# Or run tests directly inside the Docker backend container:
docker compose exec backend pytest tests/ -v

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
│   ├── app/
│   │   ├── page.tsx                # Unified App Dashboard (Gantt, Review Queue, AI Ingestion)
│   │   ├── navigator/              # Project selection page
│   │   └── globals.css             # Main styling
│   └── components/                 # Shared UI elements
├── data/
│   ├── SCHEMA.md                   # Dataset data dictionary
│   └── synthetic/                  # Synthetic XER, messages, sender profiles
├── scripts/
│   ├── seed_schedule.py            # Load XER + build embedding index
│   ├── seed_demo_events.py         # Generate synthetic events for demo
│   └── run_demo.py                 # End-to-end demo runner
├── tests/                          # pytest test suite
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.worker
├── .env.example
└── .ai/                            # Project memory (architecture docs)
```

---

## 🛠️ Handy Docker Commands

```bash
# View live pipeline and extraction logs
docker compose logs -f worker

# View FastAPI backend logs
docker compose logs -f backend

# Stop all containers
docker compose stop

# Restart all containers
docker compose restart

# Complete reset (clears database volumes to fresh state)
docker compose down -v
docker compose up -d
docker compose exec worker python scripts/seed_schedule.py
docker compose exec worker python scripts/seed_historical_events.py
```

---

## 👥 Team Kranti
Smart India Hackathon 2026 — Problem Statement SIH26122  
*All synthetic schedules, progress events, and logs are for demonstration purposes only.*
