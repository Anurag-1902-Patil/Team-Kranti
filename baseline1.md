# Baseline 1 — What the Code Actually Does

This baseline was written from implementation, test, deployment, prompt, and synthetic-data files only. Project instructions, READMEs, and other context documents were deliberately not read.

## In one sentence

This is a Python prototype that receives WhatsApp-style field-progress messages, turns their text/audio/image/document content into structured construction activity events, tries to link each event to a Primavera activity, routes uncertain cases to a reviewer, and can export accepted actuals back into a copy of a synthetic P6 XER schedule.

## Runtime shape

`docker-compose.yml` defines these services:

- PostgreSQL: durable records for messages, plan activities, events, match candidates, and review decisions.
- Redis: Celery broker and result backend.
- MinIO: raw media and extracted text storage.
- Qdrant: vector storage for plan activities and finalized progress events.
- FastAPI: HTTP API on port 8000.
- Celery worker: asynchronous message processing.
- A frontend service on port 3000 is declared, but there is no `frontend/` directory in this checkout, so that image cannot currently build.

The FastAPI process also tries to pre-load the `all-MiniLM-L6-v2` sentence-transformer model. Its health endpoint reports PostgreSQL-independent app metadata plus Qdrant connectivity.

## Data it keeps

The SQLAlchemy models define an audit-oriented data model:

- `sender_profiles`: a sender phone/identifier mapped to a discipline hint.
- `plan_activities`: imported schedule activities, their planned values, plus eventual actual start/finish/percent-complete fields.
- `documents`: one source message per unique WhatsApp message ID, raw/extracted text, media keys, and processing state.
- `progress_events`: each structured activity extracted from a source document; it retains source provenance, extracted dates/quantities/location, chosen plan activity, confidence, match status, and an LLM/audit payload.
- `matches`: up to ten ranked matching candidates per event with fuzzy, semantic, LLM, and fused scores.
- `review_decisions`: append-only accept/edit/decline/confirm-new decisions. The database model supports a reviewer ID, but the review endpoints do not set it.

## Ingestion and processing path

1. `GET /webhooks/whatsapp` performs Meta's verification-token challenge.
2. `POST /webhooks/whatsapp` reads the raw body, verifies Meta HMAC-SHA256 when an app secret is configured, parses supported WhatsApp payload entries, and dispatches one Celery job per message. With no configured app secret, it accepts unsigned messages for local/demo use.
3. The Celery task guards against a document whose message ID is already completed, creates/updates a `documents` row, and obtains plain text:
   - text messages: uses the message body;
   - audio: downloads via Meta, writes the bytes to MinIO, transcribes through faster-whisper, and saves the transcript to MinIO;
   - images: downloads/saves media and runs PaddleOCR for `image` messages (treated as handwritten) or Tesseract for other image documents;
   - PDFs: first extracts a text layer with pdfplumber, otherwise rasterizes pages and sends them through Tesseract;
   - spreadsheets/CSV: uses pandas to make a textual sheet/row representation.
4. It reads a sender's discipline from `sender_profiles` if available, then calls an LLM extractor. The implementation uses local Ollama/Qwen3 first and Groq Qwen as fallback, not a mock extraction response. JSON is parsed into activity descriptions, event types, dates, quantities, locations, disciplines, and notes.
5. The normalizer maps aliases to fixed database enums, parses dates (naive dates are assumed to be IST), clamps invalid percentages, and adds metadata to the audit record.
6. For every extracted activity, matching combines:
   - RapidFuzz token-sort and partial string scores against all database plan activity names;
   - cosine similarity from an in-process sentence-transformer embedding matrix;
   - an Ollama LLM re-rank of the five strongest combined candidates, falling back to Groq or equal scores if the LLM is unavailable.
   The fused score is 30% fuzzy + 30% semantic + 40% LLM. Defaults route scores of 0.85+ to `matched`, 0.55–0.849 to `low_confidence_review`, and the rest to `unmatched_new`.
7. The worker writes the event and candidate score history. A high-confidence match also updates actual values on the corresponding `plan_activities` row and indexes the event in Qdrant. The whole message is retried up to three times with exponential delay if processing fails.

## Human review and outputs

All `/api/v1/*` read/write endpoints except the webhook require a bearer token. Login is deliberately lightweight: it issues a process-memory token for a supplied name and one of `reviewer`, `planner`, or `admin`; there is no password check and tokens disappear on restart. The legacy configured shared token is also accepted.

- Events can be listed, filtered, paginated, and viewed with their candidate matches and audit trail.
- The review queue contains unreviewed low-confidence and unmatched events.
- A reviewer can accept, edit the selected activity, decline an event without deleting it, or confirm a new activity. Confirming new makes a `FIELD-XXXXXXXX` plan activity and reloads the in-process semantic index.
- Schedule endpoints list/create plan activities and generate a downloadable XER by taking `data/synthetic/sample_schedule.xer` and applying actual start, actual finish, and physical percent-complete from database events whose status is `matched`.
- Memory endpoints semantically query Qdrant, report vector counts, or generate a ZIP containing a PostgreSQL-derived CSV, Parquet file, schema file, and summary statistics.

The seed script creates tables, parses the synthetic XER (or substitutes a hardcoded synthetic schedule on parser failure), inserts activities/sender profiles, builds the in-process embedding matrix, and inserts plan activity embeddings in Qdrant. The demo script calls much of the same extraction/matching logic directly rather than submitting a genuine webhook.

## Important implementation realities and gaps

- The matching engine currently searches its per-process NumPy embedding matrix, not Qdrant's `plan_activities` collection. Qdrant stores the same activity vectors, but they are not used for candidate retrieval.
- There is stale ChromaDB code and imports. `create_new_plan_activity` imports `chroma_store.index_plan_activity`, even though ChromaDB is absent from requirements and deployment; confirming a new activity can therefore log an embedding failure. Other active indexing paths use Qdrant.
- The webhook creates a `BackgroundTasks` parameter and imports database types but does not use either. It also does not perform the endpoint-level duplicate query described in its comments; deduplication happens in the worker once a document is complete.
- Media downloads only occur when a WhatsApp access token is configured. Without one, non-text messages normally reach `no_text` rather than a local extraction path. Video is parsed as a message type but has no worker extraction branch.
- Review accept and edit write schedule values only when the pre-review event has an actual start date. A percent-only or finish-only report will be marked matched but may not update the plan activity's actuals. The edit path also writes schedule values from the originally loaded event, so values supplied in `corrected_fields` are not used for that write-back.
- Confirming a new activity links and indexes the event, but does not copy that event's actual fields into the new `plan_activities` row.
- `corrected_fields` accepts arbitrary keys that happen to be attributes of `ProgressEvent`; it is not schema-validated or type-normalized before the SQL update.
- XER export always starts from the repository's synthetic source XER; it does not preserve or locate an uploaded/source schedule. It writes a temporary generated file.
- The exporter includes `low_confidence_review` events despite its stated purpose of exporting finalized institutional memory, so the dataset can contain unresolved events.
- Authentication proves only possession of an in-memory demo token. Although roles are accepted on login, endpoint authorization does not enforce roles, and review decisions do not record the login identity in `reviewer_id`.
- CORS allows every origin with credentials enabled, appropriate only for a loose demo environment.

## Scope conclusion

The repository implements a substantial backend proof of concept for capture, extraction, matching, review, audit, and synthetic XER output. It does not currently contain the referenced frontend, production authentication/authorization, a persisted/vector-backed matching retrieval path, or a cleanly consistent vector-store implementation.
