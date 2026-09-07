# DATA_MODEL.md — Database tables and columns

All tables use UUID primary keys. All datetimes are timezone-aware (UTC stored in Postgres).

---

## users

Minimal reviewer identity — shared token auth for prototype.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `username` | VARCHAR(100) | UNIQUE NOT NULL | |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt (not used in token-auth mode) |
| `role` | ENUM(reviewer, planner, admin) | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL | server_default=now() |

---

## sender_profiles

WhatsApp sender_id → discipline mapping. Seeded at demo startup. The Celery task checks this before calling the LLM for discipline inference, saving tokens.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `sender_id` | VARCHAR(50) | UNIQUE NOT NULL | WhatsApp phone number (no +) |
| `display_name` | VARCHAR(200) | nullable | |
| `discipline` | VARCHAR(50) | nullable | piping/civil/etc. — NULL means LLM infers |
| `project_id` | VARCHAR(200) | nullable | |
| `created_at` | TIMESTAMPTZ | | |

---

## plan_activities

Activities sourced from the P6 XER export. This is the matching target index. Both XER-loaded and field-confirmed (is_field_confirmed=true) activities live here.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `project_id` | VARCHAR(200) | NOT NULL, indexed | |
| `activity_id` | VARCHAR(100) | UNIQUE NOT NULL, indexed | P6 task_code |
| `activity_name` | TEXT | NOT NULL | Full P6 activity name |
| `wbs_code` | VARCHAR(200) | nullable | |
| `discipline` | VARCHAR(50) | nullable, indexed | Inferred from name keywords |
| `planned_start` | TIMESTAMPTZ | nullable | From XER target_start_date |
| `planned_finish` | TIMESTAMPTZ | nullable | From XER target_end_date |
| `original_duration_days` | FLOAT | nullable | XER hours / 8 |
| `percent_complete_plan` | FLOAT | default 0.0 | From XER phys_complete_pct |
| `actual_start` | TIMESTAMPTZ | nullable | Written back by our system |
| `actual_finish` | TIMESTAMPTZ | nullable | Written back by our system |
| `actual_percent_complete` | FLOAT | nullable | Written back by our system |
| `embedding_id` | VARCHAR(200) | nullable | ChromaDB document ID |
| `is_field_confirmed` | BOOLEAN | NOT NULL, default false | True if created via confirm_new |
| `created_at` | TIMESTAMPTZ | | |
| `updated_at` | TIMESTAMPTZ | | onupdate=now() |

---

## documents

Raw ingested WhatsApp message — one row per message. Idempotency guard: `message_id` is UNIQUE.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `message_id` | VARCHAR(200) | UNIQUE NOT NULL, indexed | Meta's message ID |
| `sender_id` | VARCHAR(50) | NOT NULL, indexed | WhatsApp phone number |
| `source_type` | ENUM | | free_text_dpr / spreadsheet / scanned_diary / voice_log / image_annotation |
| `raw_text` | TEXT | nullable | Extracted text (for audio/image: transcript/OCR output) |
| `mime_type` | VARCHAR(100) | nullable | |
| `s3_key` | VARCHAR(500) | nullable | MinIO object key for raw file |
| `extracted_text_s3_key` | VARCHAR(500) | nullable | MinIO key for OCR/ASR output text |
| `processing_status` | VARCHAR(50) | NOT NULL, default 'queued' | queued/processing/completed/no_text/no_activities/processing_failed |
| `processing_error` | TEXT | nullable | Error message if processing_failed |
| `received_at` | TIMESTAMPTZ | NOT NULL | From WhatsApp message timestamp |
| `processed_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | | |

---

## progress_events

Normalized §3.4 progress event — one row per extracted activity event. One document may produce multiple events.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `project_id` | VARCHAR(200) | NOT NULL, indexed | |
| `document_id` | UUID | FK→documents.id, indexed | nullable (e.g. from demo script) |
| `activity_id_plan` | VARCHAR(100) | nullable, indexed | Matched P6 task_code |
| `plan_activity_id` | UUID | FK→plan_activities.id, indexed | nullable until matched |
| `activity_name_plan` | TEXT | nullable | Denormalized for display |
| `activity_description_extracted` | TEXT | nullable | LLM output verbatim |
| `discipline` | ENUM(DisciplineEnum) | NOT NULL | piping/civil/electrical/instrumentation/hse/structural/mechanical/unknown |
| `event_type` | ENUM(EventTypeEnum) | nullable | start/finish/partial_complete |
| `actual_start_datetime` | TIMESTAMPTZ | nullable | |
| `actual_finish_datetime` | TIMESTAMPTZ | nullable | |
| `percent_complete` | FLOAT | nullable | 0–100 |
| `quantity_completed` | FLOAT | nullable | Physical quantity |
| `quantity_unit` | VARCHAR(100) | nullable | meters/welds/joints/etc. |
| `location_reference` | VARCHAR(500) | nullable | Chainage/grid/area |
| `confidence_score` | FLOAT | nullable | 0–1, fused from 3 scorers |
| `match_status` | ENUM(MatchStatusEnum) | NOT NULL, indexed | pending_match/matched/low_confidence_review/unmatched_new/declined/processing_failed |
| `source_type` | ENUM | nullable | Same as documents.source_type |
| `source_document_id` | VARCHAR(500) | nullable | MinIO key |
| `extracted_by` | VARCHAR(100) | NOT NULL | "time_agent_v1" |
| `extraction_timestamp` | TIMESTAMPTZ | nullable, indexed | |
| `reviewed_by_planner` | BOOLEAN | NOT NULL, default false | |
| `planner_notes` | TEXT | nullable | |
| `audit_trail` | JSONB | nullable | original_text, llm_prompt, llm_response, alternatives_considered, match_justification |
| `embedding_id` | VARCHAR(200) | nullable | ChromaDB document ID |
| `created_at` | TIMESTAMPTZ | | |
| `updated_at` | TIMESTAMPTZ | | |

---

## matches

Every candidate activity considered during matching — not just the winner. Full audit trail.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `event_id` | UUID | FK→progress_events.id NOT NULL, indexed | |
| `candidate_activity_id` | VARCHAR(100) | NOT NULL | P6 task_code |
| `plan_activity_id` | UUID | FK→plan_activities.id | nullable |
| `fuzzy_score` | FLOAT | nullable | 0–1 from RapidFuzz combined |
| `semantic_score` | FLOAT | nullable | 0–1 cosine similarity |
| `llm_score` | FLOAT | nullable | 0–1 from LLM re-ranker |
| `final_score` | FLOAT | nullable | 0.3·fuzzy + 0.3·semantic + 0.4·llm |
| `rank` | INTEGER | nullable | 1=best |
| `was_selected` | BOOLEAN | NOT NULL, default false | |
| `created_at` | TIMESTAMPTZ | | |

---

## review_decisions

**Append-only** — never overwrite. Latest row per event_id wins. Preserved for audit trail.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `event_id` | UUID | FK→progress_events.id NOT NULL, indexed | |
| `reviewer_id` | UUID | FK→users.id, nullable | |
| `decision` | ENUM(ReviewDecisionEnum) | NOT NULL | accepted/edited/declined/confirmed_new |
| `corrected_activity_id` | VARCHAR(100) | nullable | Populated for 'edited' decisions |
| `corrected_fields` | JSONB | nullable | Field overrides for edited decisions |
| `new_activity_id` | VARCHAR(100) | nullable | Populated for 'confirmed_new' decisions (FIELD-XXXXXXXX format) |
| `notes` | TEXT | nullable | Planner free-text notes |
| `decided_at` | TIMESTAMPTZ | NOT NULL | server_default=now() |

---

## ChromaDB Collections (not Postgres)

### progress_events
- **ID**: event UUID
- **Document**: `{activity_description_extracted} [Plan: {activity_name_plan}]`
- **Metadata**: event_id, discipline, project_id, confidence_score, actual_start, actual_finish, activity_name_plan
- **Only** indexed for events with match_status=matched or reviewed_by_planner=true

### plan_activities
- **ID**: activity_id (P6 task_code or FIELD-XXXXXXXX)
- **Document**: activity_name
- **Metadata**: activity_id, discipline, project_id
- **All** activities indexed (both XER-loaded and field-confirmed)
