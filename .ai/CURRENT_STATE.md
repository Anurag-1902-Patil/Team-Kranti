# CURRENT_STATE.md — Build state

**Last updated**: 2026-09-05 (after final change request)
**Overall status**: ✅ COMPLETE — all layers built, final stack applied

---

## Final Confirmed Tech Stack

| Component | Technology | Notes |
|---|---|---|
| ASR (voice) | faster-whisper (SYSTRAN) | Unchanged |
| OCR — typed/printed | **Tesseract** (`pytesseract`) | Replaces PaddleOCR for this path |
| OCR — handwritten diaries | **PP-OCRv5** (via PaddleOCR, CPU-only, 0.07B) | Replaces Groq vision — no GPU needed |
| LLM primary | **Qwen3-8B** via Ollama | `ollama pull qwen3:8b` |
| LLM fallback | Groq `qwen/qwen3-32b` (`GROQ_MODEL_FALLBACK`) | Fallback for *both* extraction + re-ranking |
| Vector DB | **Qdrant** | Two collections: plan_activities + progress_events (ADR-012) |
| Spreadsheet | pandas + openpyxl | Unchanged |
| Schedule | PyP6XER | XER round-trip only, no P6 API |
| Database | PostgreSQL 16 + SQLAlchemy 2 async | Unchanged |
| Queue | Celery 5 + Redis 7 | Unchanged |
| Storage | MinIO (S3-compatible) | Unchanged |
| Frontend | Next.js 15, TypeScript, Tailwind | Named-token auth added |

---

## Layer Status

| Layer | What | Status |
|---|---|---|
| 0 | Foundation (config, logging, requirements, .env) | ✅ Done |
| 1 | DB models (SQLAlchemy), session factory, Alembic migration | ✅ Done |
| 2 | WhatsApp webhook (HMAC verify, idempotency, 200-first) | ✅ Done |
| 2 | Media download/upload (MinIO) | ✅ Done |
| 2 | Celery app config | ✅ Done |
| 3 | ASR (faster-whisper) | ✅ Done |
| 3 | OCR — Tesseract (typed) | ✅ Done (final stack) |
| 3 | OCR — PP-OCRv5 (handwritten) | ✅ Done (final stack) |
| 3 | LLM extractor — Qwen3-8B primary / Groq fallback | ✅ Done (final stack) |
| 3 | Schema normalizer | ✅ Done |
| 4 | Fuzzy matcher (RapidFuzz) | ✅ Done |
| 4 | Semantic matcher (Sentence-Transformers, in-memory matrix) | ✅ Done |
| 4 | Confidence scorer + LLM re-ranker — Qwen3-8B primary / Groq fallback | ✅ Done (final stack) |
| 5 | XER parser (PyP6XER) | ✅ Done |
| 5 | XER writer (actuals apply) | ✅ Done |
| 5 | Schedule service (write-back, confirm-new, index reload) | ✅ Done |
| 6 | Qdrant store (plan_activities + progress_events — two collections) | ✅ Done (final stack) |
| 6 | Dataset exporter (Parquet + CSV + SCHEMA.md) | ✅ Done |
| 7 | Celery task (full 10-step pipeline orchestration) | ✅ Done |
| 7 | API: events list/detail | ✅ Done |
| 7 | API: review queue + 4 actions | ✅ Done |
| 7 | API: schedule activities + XER export | ✅ Done |
| 7 | API: memory query + export + stats | ✅ Done |
| 7 | API: auth login/logout (named tokens) | ✅ Done (A6) |
| 8 | Schemas (Pydantic event/review/schedule) | ✅ Done |
| 8 | FastAPI deps (get_db, get_current_user — named + legacy tokens) | ✅ Done |
| 9 | Synthetic data (XER skeleton, sender profiles, messages) | ✅ Done |
| 9 | SCHEMA.md data dictionary | ✅ Done |
| 10 | Seed script (seed_schedule.py) | ✅ Done |
| 10 | Demo script (run_demo.py) | ✅ Done |
| 11 | Tests (normalizer, matching, webhook security, reranker fallback) | ✅ Done (A7 added) |
| 12 | Docker (compose + Qdrant service + tesseract in images) | ✅ Done (final stack) |
| 13 | Next.js frontend (dashboard, events, review, schedule, memory, login) | ✅ Done (A6) |
| 14 | `prompts/` versioned prompt templates | ✅ Done (A8) |
| 15 | Memory docs updated (.ai/*) | ✅ Done |

---

## Functional Gaps Closed (vs. original plan)

| Gap | Status |
|---|---|
| A1: confirm_new + immediate embedding | ✅ Was already implemented |
| A2: Webhook idempotency (IntegrityError catch) | ✅ Already in tasks.py; verified in code review |
| A3: discipline_hint source | ✅ Already implemented (sender_profiles lookup) |
| A4: CORS + NEXT_PUBLIC_API_URL | ✅ Was already correct |
| A5: /health endpoint | ✅ Already existed; enhanced with Qdrant status |
| A6: Named reviewer identity (audit trail) | ✅ Done — POST /auth/login, login page, sidebar identity |
| A7: Re-ranker fallback test | ✅ Done — TestRerankerFallback (2 tests) |
| A8: prompts/ versioned templates | ✅ Done — extractor_v1.txt + reranker_v1.txt |

---

## Open Items (post-demo hardening, not needed for SIH)

- [ ] Real WhatsApp Cloud API phone number registration (requires Meta Business verification)
- [ ] Ollama auto-pull in docker-compose (currently: manual `ollama pull qwen3:8b`)
- [ ] pytest GitHub Actions CI
- [ ] Production CORS tightening
- [ ] Rate limiting on webhook endpoint
- [ ] Validate XER round-trip against a live P6 import (requires P6 license)
- [ ] LoRA fine-tuning on labeled (description → activity_id) pairs (stretch goal)
