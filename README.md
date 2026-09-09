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
NVIDIA_API_KEY=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
NVIDIA_NIM_MODEL=nvidia/nemotron-3-super-120b-a12b

# Meta WhatsApp Cloud API (Pre-configured for prototype testing)
WHATSAPP_APP_SECRET=e6b830d0566502f879aa7247416de708
WHATSAPP_VERIFY_TOKEN=sih122teamkranti
WHATSAPP_PHONE_NUMBER_ID=1288956324303210
WHATSAPP_ACCESS_TOKEN=EAANpJ2ZBZA0CUBSWtWPXNgHIp...

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

### B. Live Real WhatsApp via Mobile Phone
To receive real text and voice notes from your smartphone:
1. Expose your backend port with a tunnel:
   ```bash
   ngrok http 8000
   # or: cloudflared tunnel --url http://localhost:8000
   ```
2. In [Meta Developer Console](https://developers.facebook.com/) under **WhatsApp → Configuration**:
   - **Callback URL**: `https://<your-tunnel-url>/api/v1/webhook/whatsapp`
   - **Verify Token**: `sih122teamkranti`
   - Subscribe to the **`messages`** webhook field.
3. Send a WhatsApp voice note or text message from your phone to your registered test number. The Celery worker will download the audio, transcribe via `faster-whisper`, extract structured ontology attributes, and update the review queue!

---

## 🌐 Step 7: Hosting & Sharing Your Project

### 1. Local Wi-Fi Sharing (Same Room / Hackathon Table)
Share your running dashboard with anyone on the same Wi-Fi router (no internet tunnel needed):
1. Find your machine's local IP:
   - **Windows**: `ipconfig` (Look for `IPv4 Address`, e.g. `192.168.1.45`)
   - **Linux/Mac**: `ip addr` or `ifconfig`
2. Anyone on the same Wi-Fi can open:
   ```
   http://192.168.1.45:3000
   ```

### 2. Worldwide Public Link (Free via Cloudflare Tunnel)
Generate a 100% free, secure public HTTPS link with no account setup:
1. Install `cloudflared`:
   - **Windows**: `winget install --id Cloudflare.cloudflared`
   - **Ubuntu**: `sudo dpkg -i cloudflared.deb`
   - **macOS**: `brew install cloudflared`
2. Start the tunnel for the frontend:
   ```bash
   cloudflared tunnel --url http://localhost:3000
   ```
3. Cloudflare outputs a public link (e.g. `https://team-kranti-demo.trycloudflare.com`). Share this URL with judges or evaluators anywhere in the world!

### 3. Permanent Cloud VPS Deployment (Ubuntu 22.04 / 24.04)
To host 24/7 on a cloud server (DigitalOcean, AWS EC2, GCP, Hetzner):
1. SSH into the server: `ssh root@<SERVER_IP>`
2. Install Docker: `curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh`
3. Clone the repo and execute **Steps 1 through 4**.
4. Set up a reverse proxy like Caddy or Nginx with Let's Encrypt for custom domain SSL.

---

## 🧪 Running Automated Tests

The test suite validates the intelligence layer, normalizer, matching engine, and security without requiring external services (uses SQLite in-memory):

```bash
# In your local Python environment:
pip install pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v

# Or run tests directly inside the Docker backend container:
docker compose exec backend pytest tests/ -v
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
