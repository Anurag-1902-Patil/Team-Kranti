# Progress Events Dataset — Data Dictionary (SCHEMA.md)
# SIH26122 — Team Kranti, Smart India Hackathon 2026

This file describes the schema of the exported institutional memory dataset.
Every row represents one extracted activity progress event that has been:
  - Ingested from a field message (WhatsApp text, spreadsheet, or scanned diary)
  - Extracted by the AI Time Agent LLM pipeline
  - Fuzzy/semantically matched to a Primavera P6 L5/L6 plan activity
  - Validated (either auto-accepted at high confidence, or reviewed by a planner)

The dataset is the "institutional memory" product of the project —
the structured record of what actually happened on site, linked to the plan.
An LLM reading this dataset for the first time should read this SCHEMA.md
first to understand the column semantics before interpreting the data.

---

## File Inventory

| File | Format | Description |
|---|---|---|
| `progress_events.parquet` | Parquet (pyarrow) | Full dataset, typed, ML-ready |
| `progress_events.csv` | CSV | Human/LLM-readable flat version |
| `summary_stats.json` | JSON | Aggregate metrics by discipline |
| `SCHEMA.md` | Markdown | This file |

---

## Column Definitions

| Column | Type | Description | Example |
|---|---|---|---|
| `event_id` | string (UUID) | Unique identifier for the progress event | `7f3a9b2c-...` |
| `project_id` | string | Project identifier | `OIL_Pipeline_2026_Demo` |
| `activity_id_plan` | string | L5/L6 activity ID from the baseline P6 schedule | `ACT-2456-L5` |
| `activity_name_plan` | string | Original activity name from the plan | `Erect Line 24"-XX` |
| `activity_description_extracted` | string | Description as reported by the field supervisor | `spool erected at chainage 12+450` |
| `discipline` | string (enum) | Engineering discipline | `piping`, `civil`, `electrical`, `instrumentation`, `hse`, `structural`, `mechanical`, `unknown` |
| `event_type` | string (enum) | Type of progress event | `start`, `finish`, `partial_complete` |
| `actual_start_datetime` | timestamp (UTC) | Actual start timestamp (ISO 8601) | `2026-08-27T08:30:00+05:30` |
| `actual_finish_datetime` | timestamp (UTC) | Actual finish timestamp (ISO 8601) | `2026-08-27T16:45:00+05:30` |
| `percent_complete` | float (0–100) | Completion percentage if partial event | `75.0` |
| `quantity_completed` | float | Physical quantity completed | `120.5` |
| `quantity_unit` | string | Unit of measurement | `meters`, `welds`, `cubic_meters`, `joints` |
| `location_reference` | string | Site location (chainage, grid, area) | `Chainage 12+450, Grid B-4` |
| `confidence_score` | float (0–1) | AI confidence in the activity match | `0.87` |
| `match_status` | string (enum) | Final match status | `matched`, `low_confidence_review`, `unmatched_new`, `declined` |
| `source_type` | string (enum) | Original input format | `free_text_dpr`, `spreadsheet`, `scanned_diary`, `voice_log`, `image_annotation` |
| `source_document_id` | string | Reference to original input file (MinIO key) | `raw/2026-08-27/MSG123/report.xlsx` |
| `extracted_by` | string | AI agent identifier and version | `time_agent_v1` |
| `extraction_timestamp` | timestamp (UTC) | When extraction occurred | `2026-08-27T18:00:00Z` |
| `reviewed_by_planner` | boolean | Whether a planner reviewed this entry | `true` |
| `planner_notes` | string | Planner's comments or corrections | `Matched to ACT-2457 instead` |
| `planned_duration_days` | float | Planned duration from the P6 baseline (days) | `3.0` |
| `planned_start` | timestamp | Planned activity start from P6 | `2026-08-25T00:00:00+05:30` |
| `planned_finish` | timestamp | Planned activity finish from P6 | `2026-08-28T00:00:00+05:30` |
| `actual_duration_days` | float | Computed actual duration (actual_finish - actual_start in days) | `2.35` |
| `created_at` | timestamp (UTC) | When the event record was created in our system | `2026-08-27T18:00:05Z` |

---

## Key Analytical Questions This Dataset Supports

1. **Recurring delay causes by discipline** — `GROUP BY discipline ORDER BY AVG(actual_duration_days - planned_duration_days) DESC`
2. **Productivity benchmarks** — `AVG(actual_duration_days) / AVG(planned_duration_days)` by `discipline` and `event_type`
3. **Terminology mapping** — `activity_description_extracted` → `activity_name_plan` pairs with `confidence_score ≥ 0.85` are high-quality training examples for future LLM fine-tuning (§5 Approach 2)
4. **Match confidence trends** — does the system need less human review over time? Track `reviewed_by_planner` rate over `extraction_timestamp`
5. **Field activities not in plan** — `WHERE match_status = 'unmatched_new' AND reviewed_by_planner = true` — these are the activities that exist on site but weren't in the P6 baseline

---

## Data Quality Notes

- All data in this export is **synthetic** — generated to match the structure of real Oil India project data but containing no actual project information (per NDA compliance)
- `actual_duration_days` is NULL when either `actual_start_datetime` or `actual_finish_datetime` is NULL (partial events where only start was reported)
- `confidence_score` of exactly 1.0 indicates human-confirmed events (planner accepted or confirmed-new)
- Events with `reviewed_by_planner = false` in this export were auto-accepted at ≥0.85 confidence threshold (configurable via MATCH_AUTO_ACCEPT_THRESHOLD)
