# Architecture Decisions — SIH26122

All decisions are append-only. Log the date, the options considered, the choice, and the rationale. Never delete old decisions — add a follow-up entry if a decision is reversed.

---

## ADR-001: AI Project Memory Tool
**Date**: 2026-09-05
**Options**: Alcove (Rust MCP server), OpenWiki (Deep-Agents CLI), Custom `.ai/` folder
**Decision**: Custom `.ai/` folder
**Rationale**: Alcove is a Rust binary — installation on Windows is not verified for this environment and would block the build. OpenWiki has no confirmed native Antigravity integration. The custom `.ai/` folder is guaranteed to work, is zero-dependency, and is portable. Upgrade path: install Alcove if/when verified on this machine and point it at the `.ai/` directory.
**Logged by**: AI (Antigravity)

---

## ADR-002: Frontend Framework
**Date**: 2026-09-05
**Options**: Streamlit, Next.js
**Decision**: Next.js (React + TypeScript)
**Rationale**: Streamlit is single-threaded and server-rendered — it conflicts with the async FastAPI backend and would make real-time reviewer actions (Accept/Edit/Decline) awkward. Next.js gives a proper async client → REST API architecture, better state management, and a more credible demo. Streamlit is legitimate for hackathons but not the right fit when the backend is already a full async FastAPI service.
**Logged by**: AI (Antigravity)

---

## ADR-003: LLM Stack
**Date**: 2026-09-05 (original) | **Revised**: 2026-09-05
**Options**: Groq API only, Ollama local only, Qwen3-8B local + Groq cloud fallback
**Decision**: Qwen3-8B via Ollama (PRIMARY) + Groq `qwen/qwen3-32b` (FALLBACK)
**Rationale**: Original plan had Groq as primary with Ollama as fallback. Reversed in the final change request. Qwen3-8B runs reliably on a single consumer GPU (~8-10 GB VRAM at Q4/Q5) and is the right weight class for a live hackathon demo — the newer Qwen3.8-27B line was explicitly ruled out as too heavy for reliable single-GPU local inference during a live demo. Groq (`qwen/qwen3-32b`) remains wired as a reliability fallback in case local inference is slow or unavailable under demo load.
**Model config**: `LOCAL_LLM_MODEL=qwen3:8b` (Ollama primary), `GROQ_MODEL_FALLBACK=qwen/qwen3-32b`.
**`GROQ_MODEL_FALLBACK` naming**: Deliberately NOT named `GROQ_MODEL_RERANK` — this one Groq model serves as fallback for two different call sites (structured extraction in `llm_extractor.py` AND candidate re-ranking in `confidence.py`). One model, two jobs, one config key.
**Qwen3 parsing**: Qwen3 may emit `<think>...</think>` reasoning blocks before JSON output. The parser in `_parse_llm_response()` and `_llm_rerank()` strips these blocks before JSON parse. Tested against synthetic WhatsApp messages.
**Logged by**: AI (Antigravity), per final user change request

---

## ADR-004: Vector Database
**Date**: 2026-09-05 (original) | **Revised**: 2026-09-05
**Options**: ChromaDB (in-process), Qdrant (Docker), pgvector (Postgres extension)
**Original decision**: ChromaDB
**Revised decision**: **Qdrant** (see ADR-011 for the full substitution log)
**Logged by**: AI (Antigravity)

---

## ADR-005: `discipline_hint` Source
**Date**: 2026-09-05
**Options**: (a) Sender_id → discipline lookup table, (b) LLM infers from content alone
**Decision**: `sender_profiles` table (sender_id → discipline), with LLM-infers fallback when no profile exists
**Rationale**: Supervisors at Oil India sites typically operate within a single discipline. A lookup table (seeded at demo startup with synthetic profiles) gives consistent, low-latency discipline tagging without adding an extra LLM call. When no profile exists (new sender), the LLM infers discipline from message content — this gracefully degrades. The table also serves as a useful sender identity layer for the reviewer dashboard.
**Logged by**: AI (Antigravity), flagged by user review

---

## ADR-006: Webhook Idempotency
**Date**: 2026-09-05
**Options**: (a) Let DB unique constraint surface as 500, (b) Explicit ON CONFLICT skip in task
**Decision**: Explicit ON CONFLICT skip in Celery task + webhook handler
**Rationale**: Meta retries webhook delivery on any non-200 or timeout. The `documents.message_id` UNIQUE constraint is the database-level guard, but we must catch the resulting unique-violation at the application layer, log "idempotent skip" with the message_id, and return early — never let it surface as an unhandled error. The webhook endpoint itself also checks for existing message_id before enqueueing (fast path to avoid even queuing a duplicate).
**Logged by**: AI (Antigravity), flagged by user review

---

## ADR-007: Promote `unmatched_new` to Plan
**Date**: 2026-09-05
**Options**: (a) Planners manually add activities to P6 and re-import XER, (b) Direct creation via review UI
**Decision**: `POST /review/{event_id}/confirm_new` → `POST /schedule/activities` with immediate embedding
**Rationale**: The problem statement explicitly requires "flag unmatched/new activities for planner review — don't drop them." This implies planners must be able to act on them. Forcing planners back to P6 just to register a new activity breaks the real-time flow. Our platform maintains its own Schedule DB as the near-real-time actuals store (per §3.1.1); adding activities there and embedding them immediately enables the "learning system" narrative (coverage improves over time as planners confirm new activities).
**Logged by**: AI (Antigravity), flagged by user review

---

## ADR-008: XER Round-Trip Scope
**Date**: 2026-09-05
**Decision**: Synthetic XER only — not validated against a live P6 import
**Rationale**: Per §3.1.1 and §9 of Project Context — "Validate the XER round-trip thoroughly" is listed as an open question specifically because it requires a P6 license and representative files, neither of which are available to the team during the hackathon. We use PyP6XER to parse and write XER, and we validate that our changes are structurally correct (right sections, right field names, right data types) against the PyP6XER schema — but we do not claim verified P6 re-import. This is stated explicitly in the demo script and README.
**Logged by**: AI (Antigravity)

---

## ADR-009: OCR for Handwritten Diaries
**Date**: 2026-09-05 (original) | **Revised**: 2026-09-05
**Original decision**: Groq vision API for handwritten content
**Revised decision**: **PP-OCRv5 via PaddleOCR (CPU-only, 0.07B params)**
**Rationale for revision**: PP-OCRv5 is specifically trained for handwritten text recognition. Baidu's own benchmarks claim it outperforms Qwen2.5-VL and GPT-4o specifically on handwritten-text OCR. Critically, it runs CPU-only at 0.07B params — no GPU service needed, simplifying docker-compose.yml. The earlier Groq vision approach consumed API quota and required network for a task that is arguably simpler than general VLM tasks.
**Typed OCR**: Tesseract (`pytesseract`) was added simultaneously for typed/printed content (typed DPRs, spreadsheet-rendered images, printed forms). This is intentionally a different engine from PP-OCRv5.
**Logged by**: AI (Antigravity), per final user change request

---

## ADR-010: Confidence Thresholds
**Date**: 2026-09-05
**Decision**: ≥0.85 → auto-accept (`matched`), 0.55–0.84 → `low_confidence_review`, <0.55 → `unmatched_new`
**Rationale**: Chosen as reasonable starting values for a prototype with synthetic data. Both thresholds are configurable via env vars (`MATCH_AUTO_ACCEPT_THRESHOLD`, `MATCH_REVIEW_THRESHOLD`) so they can be tuned without code changes. The fused score is `0.3 * fuzzy_norm + 0.3 * semantic_norm + 0.4 * llm_score`.
**Logged by**: AI (Antigravity)

---

## ADR-011: Qdrant Replaces ChromaDB
**Date**: 2026-09-05
**Options**: ChromaDB (in-process), Qdrant (Docker service)
**Decision**: Qdrant
**Rationale**: Per final user change request. ChromaDB was chosen initially for zero-infrastructure overhead, but Qdrant was explicitly requested as the final stack. Qdrant runs as a Docker service (`qdrant/qdrant:latest`, port 6333), persists to a named volume, and exposes a healthcheck that integrates with docker-compose `depends_on`. Tests use `QdrantClient(":memory:")` — no Docker needed for the test suite. `chromadb` removed from `requirements.txt`; `qdrant-client>=1.9` added.
**Logged by**: AI (Antigravity), per final user change request

---

## ADR-012: Two Separate Qdrant Collections for Two Distinct Purposes
**Date**: 2026-09-05
**Decision**: Maintain two separate Qdrant collections — `plan_activities` and `progress_events` — even though both hold embeddings.
**Rationale**: These two stores serve fundamentally different purposes and must NOT be conflated:

- **`plan_activities`** (matching engine index): holds embeddings of P6 plan activity names. Its purpose is to answer "which plan activity does this extracted description most resemble?" — used by `semantic_matcher.get_semantic_candidates()` during the ingestion pipeline. The query is: field description → nearest plan activity.

- **`progress_events`** (institutional memory): holds embeddings of finalized actual-progress event descriptions (only matched/accepted events). Its purpose is semantic recall — "what similar work has been done on site historically?" — used by `GET /memory/query` and the dataset export. The query is: a planner's natural language question → similar past site events.

Merging these would corrupt both use cases: plan-activity lookup results would be polluted with historical event noise, and memory queries would return plan activity stubs rather than real site history. Keep them separate. The two-collection structure also mirrors the real-world distinction between "what is planned" and "what actually happened."
**Logged by**: AI (Antigravity), explicitly required by user change request

---

## ADR-013: LLM Swap — NVIDIA NIM (nemotron-3-super-120b-a12b) Replaces Qwen3+Groq
**Date**: 2026-09-08
**Previous decision**: ADR-003 (Qwen3-8B via Ollama primary + Groq qwen/qwen3-32b fallback)
**New decision**: **NVIDIA NIM `nvidia/nemotron-3-super-120b-a12b`** as sole LLM backend (no Ollama, no Groq)
**Rationale**: User explicitly requested the swap. Nemotron-3-Super is served via NVIDIA NIM's OpenAI-compatible REST API (`https://integrate.api.nvidia.com/v1`) — no local GPU required. The model is a 120B total / 12B active MoE hybrid (Mamba-2 + Attention) with 1M token context, strong structured JSON extraction, and reasoning capabilities configurable via `enable_thinking`. NVIDIA recommends `temperature=1.0, top_p=0.95` across all tasks. Reasoning is disabled (`enable_thinking=False`) in both extraction and re-ranking call sites for lower latency on structured JSON tasks. The `<think>...</think>` block stripping in `_parse_llm_response()` and `_llm_rerank()` is retained since Nemotron emits the same format when thinking is on.
**Model config**: `NVIDIA_API_KEY`, `NVIDIA_NIM_MODEL=nvidia/nemotron-3-super-120b-a12b`, `NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1`.
**Dependencies**: `groq` and `ollama` removed from `requirements.txt`; `openai>=1.40.0` added (universal OpenAI-compatible client).
**Logged by**: AI (Antigravity), per user change request 2026-09-08

---

## ADR-014: Intelligence Layer & Project Controls Architecture
**Date**: 2026-09-09
**Decision**:
1. **Deterministic Predictions (No Generative Math)**: Delays, forecast completion dates, and risk scores are computed mathematically from historical discipline variance factors and predecessor CPM float consumption. The LLM is used only to synthesize explanatory factors into plain-language narrative without altering numeric values.
2. **Human-Gated Controlled Vocabulary**: Unrecognized site terminology detected in field updates is saved to `entity_aliases` with status `proposed`. It is never used in canonical matching dictionaries until explicitly approved by a human planner via the review queue.
3. **Strict 5-Tier Provenance Separation**: Visual and data separation across:
   - `source_fact`: Official P6 Schedule Plan or Equipment Master
   - `ai_extraction`: Extracted by model from raw supervisor message / photo
   - `ai_inference`: Deduced relationship or manpower estimate
   - `prediction`: Computed mathematically from historical actuals & float
   - `human_approval`: Verified and accepted/edited by a human planner
4. **Post-Approval Re-Editing**: Events accepted automatically or by planners remain editable in the schedule view, preserving an immutable `correction_history` JSON log.
5. **Safe Grounded Natural-Language Search**: Free-text queries are parsed into constrained Pydantic filter objects (`target_type`, `discipline`, `location`, `equipment_tag`, `is_delayed`, `is_critical`), and executed strictly via parameterized SQLAlchemy queries. No raw SQL execution.
**Logged by**: AI (Antigravity), per SIH26122 Intelligence Layer specification

