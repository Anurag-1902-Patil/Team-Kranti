export type MatchStatus =
  | "pending_match"
  | "matched"
  | "low_confidence_review"
  | "unmatched_new"
  | "declined"
  | "processing_failed";

export type Discipline =
  | "piping"
  | "civil"
  | "electrical"
  | "instrumentation"
  | "hse"
  | "structural"
  | "mechanical"
  | "unknown";

export type EventType = "start" | "finish" | "partial_complete";

export interface MatchCandidate {
  candidate_activity_id: string;
  activity_name: string | null;
  fuzzy_score: number | null;
  semantic_score: number | null;
  llm_score: number | null;
  final_score: number | null;
  rank: number | null;
  was_selected: boolean;
}

export interface ProgressEvent {
  id: string;
  project_id: string;
  document_id: string | null;
  activity_id_plan: string | null;
  activity_name_plan: string | null;
  activity_description_extracted: string | null;
  discipline: Discipline;
  event_type: EventType | null;
  actual_start_datetime: string | null;
  actual_finish_datetime: string | null;
  percent_complete: number | null;
  quantity_completed: number | null;
  quantity_unit: string | null;
  location_reference: string | null;
  confidence_score: number | null;
  match_status: MatchStatus;
  source_type: string | null;
  source_document_id: string | null;
  extracted_by: string;
  extraction_timestamp: string | null;
  reviewed_by_planner: boolean;
  planner_notes: string | null;
  audit_trail: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  match_candidates: MatchCandidate[];
}

export interface ProgressEventList {
  total: number;
  page: number;
  page_size: number;
  items: ProgressEvent[];
}

export interface PlanActivity {
  id: string;
  project_id: string;
  activity_id: string;
  activity_name: string;
  wbs_code: string | null;
  discipline: string | null;
  planned_start: string | null;
  planned_finish: string | null;
  original_duration_days: number | null;
  percent_complete_plan: number;
  actual_start: string | null;
  actual_finish: string | null;
  actual_percent_complete: number | null;
  is_field_confirmed: boolean;
  created_at: string;
}

export interface ReviewDecision {
  id: string;
  event_id: string;
  reviewer_id: string | null;
  decision: "accepted" | "edited" | "declined" | "confirmed_new";
  corrected_activity_id: string | null;
  corrected_fields: Record<string, unknown> | null;
  new_activity_id: string | null;
  notes: string | null;
  decided_at: string;
}

export interface MemoryQueryResult {
  query: string;
  discipline_filter: string | null;
  result_count: number;
  total_indexed: number;
  results: Array<{
    text: string;
    metadata: Record<string, unknown>;
    similarity_score: number;
  }>;
}
