export type MatchStatus =
  | "pending_match"
  | "matched"
  | "low_confidence_review"
  | "unmatched_new"
  | "declined"
  | "processing_failed";

export type ProvenanceCategory =
  | "source_fact"
  | "ai_extraction"
  | "ai_inference"
  | "prediction"
  | "human_approval";

export type ConfidenceTier = "high" | "medium" | "low";

export type Discipline =
  | "piping"
  | "civil"
  | "electrical"
  | "instrumentation"
  | "mechanical"
  | "structural"
  | "static_equipment"
  | "rotating_equipment"
  | "telecom"
  | "hvac"
  | "fire_and_safety"
  | "hse"
  | "qa_qc"
  | "procurement"
  | "engineering"
  | "planning"
  | "commissioning"
  | "construction"
  | "logistics"
  | "material_management"
  | "administration"
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

export interface ExtractedEntity {
  id: string;
  event_id?: string | null;
  document_id?: string | null;
  entity_type: string;
  raw_text: string;
  normalized_value: string | null;
  confidence: number;
  evidence: string | null;
  extraction_method: string;
  model_version: string;
  created_at: string;
}

export interface ProgressEvent {
  id: string;
  project_id: string;
  document_id: string | null;
  activity_id_plan: string | null;
  activity_name_plan: string | null;
  activity_description_extracted: string | null;
  activity_description_raw?: string | null;
  activity_description_normalized?: string | null;
  discipline: Discipline | string;
  sub_discipline?: string | null;
  event_type: EventType | null;
  activity_type?: string | null;
  work_package?: string | null;
  wbs_code?: string | null;
  construction_phase?: string | null;
  execution_stage?: string | null;
  actual_start_datetime: string | null;
  actual_finish_datetime: string | null;
  planned_start?: string | null;
  planned_finish?: string | null;
  planned_duration_days?: number | null;
  actual_duration_days?: number | null;
  remaining_duration_days?: number | null;
  percent_complete: number | null;
  quantity_completed: number | null;
  quantity_unit: string | null;
  location_reference: string | null;
  location_area?: string | null;
  location_unit?: string | null;
  equipment_tag?: string | null;
  line_number?: string | null;
  tag_number?: string | null;
  drawing_reference?: string | null;
  material_reference?: string | null;
  contractor_name?: string | null;
  supervisor_name?: string | null;
  engineer_name?: string | null;
  crew_name?: string | null;
  status?: string | null;
  delay_status?: string | null;
  delay_category?: string | null;
  delay_reason?: string | null;
  blocker_description?: string | null;
  priority?: string | null;
  is_critical_path?: boolean;
  total_float_days?: number | null;
  confidence_score: number | null;
  confidence_tier?: ConfidenceTier;
  match_status: MatchStatus;
  provenance_category: ProvenanceCategory;
  source_type: string | null;
  source_document_id: string | null;
  extracted_by: string;
  extraction_timestamp: string | null;
  reviewed_by_planner: boolean;
  planner_notes: string | null;
  audit_trail: Record<string, unknown> | null;
  ontology_payload?: Record<string, unknown> | null;
  correction_history?: Array<{
    editor: string;
    edited_at: string;
    changes: Record<string, { old: unknown; new: unknown }>;
    notes?: string;
  }> | null;
  created_at: string;
  updated_at: string;
  match_candidates: MatchCandidate[];
  extracted_entities?: ExtractedEntity[];
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
  wbs_path?: string | null;
  discipline: string | null;
  planned_start: string | null;
  planned_finish: string | null;
  original_duration_days: number | null;
  percent_complete_plan: number;
  actual_start: string | null;
  actual_finish: string | null;
  actual_percent_complete: number | null;
  remaining_duration_days?: number | null;
  total_float_days?: number | null;
  free_float_days?: number | null;
  is_critical?: boolean;
  area?: string | null;
  contractor_code?: string | null;
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

export interface EntityAlias {
  id: string;
  entity_type: string;
  raw_alias: string;
  canonical_name: string;
  status: "approved" | "proposed" | "rejected";
  frequency: number;
  sample_text: string | null;
  proposed_by: string;
  reviewed_by?: string | null;
  created_at: string;
}

export interface MilestoneItem {
  activity_id: string;
  name: string;
  target_date: string;
  status: string;
  progress_pct: number;
}

export interface AtRiskActivityItem {
  activity_id: string;
  name: string;
  discipline: string;
  variance_days: number;
  total_float: number;
  is_critical: boolean;
  progress_pct: number;
}

export interface DisciplineHealthItem {
  total_activities: number;
  completed: number;
  avg_progress_pct: number;
  delayed_activities: number;
}

export interface ScheduleHealth {
  project_id?: string;
  total_activities: number;
  overall_progress_pct: number;
  completed_count: number;
  in_progress_count: number;
  not_started_count: number;
  delayed_count: number;
  critical_count: number;
  critical_delayed_count: number;
  mean_schedule_variance_days: number;
  milestone_health: MilestoneItem[];
  top_at_risk_activities: AtRiskActivityItem[];
  discipline_health: Record<string, DisciplineHealthItem>;
  // Backwards compatibility fields
  started_activities?: number;
  completed_activities?: number;
  not_started_activities?: number;
  planned_progress_pct?: number;
  progress_variance_pct?: number;
  critical_activities_count?: number;
  delayed_activities_count?: number;
  at_risk_activities_count?: number;
  average_float_days?: number;
  critical_path_slippage_days?: number;
  active_blockers_count?: number;
  pending_reviews_count?: number;
  planned_project_finish?: string | null;
  forecast_project_finish?: string | null;
  health_status?: "on_track" | "minor_delay" | "critical_slippage";
}

export interface DelayIntelligence {
  total_delay_events: number;
  cause_breakdown: Array<{
    cause: string;
    label: string;
    event_count: number;
    percentage: number;
  }>;
  bottlenecks: Array<{
    area: string;
    delayed_events: number;
    active_blockers: number;
  }>;
  contractor_rankings: Array<{
    contractor: string;
    total_events: number;
    delay_events: number;
    delay_ratio: number;
    avg_variance_factor: number;
  }>;
  recurring_blockers: Array<{
    description: string;
    occurrences: number;
    latest_reported: string;
  }>;
}

export interface ResourceIntelligence {
  total_records: number;
  observed_manpower: {
    total_crew_headcount: number;
    reporting_events: number;
  };
  inferred_manpower: {
    estimated_headcount: number;
    basis: string;
  };
  equipment_utilization: Array<{
    equipment_tag: string;
    name: string;
    status: string;
    assigned_activity: string | null;
    area: string | null;
  }>;
}

export interface ActivityPrediction {
  activity_id: string;
  activity_name: string;
  discipline: string;
  is_critical: boolean;
  planned_finish: string | null;
  predicted_finish: string | null;
  predicted_delay_days: number;
  historical_variance_factor: number;
  predecessor_float_consumed_days: number;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  factors: string[];
  plain_language_narrative: string;
}

export interface NLSearchResult {
  query: string;
  parsed_filters: {
    target_type: string;
    discipline?: string | null;
    location?: string | null;
    status?: string | null;
    is_delayed: boolean;
    is_critical: boolean;
    equipment_tag?: string | null;
    has_blocker: boolean;
    keyword?: string | null;
  };
  total_matches: number;
  results: Array<{
    id: string;
    record_type: string;
    title: string;
    discipline: string;
    status: string;
    progress_pct: number | null;
    location: string;
    is_critical: boolean;
    link_url: string;
    provenance: string;
    summary: string;
  }>;
}

export interface DisciplineLookup {
  code: string;
  name: string;
  category: string | null;
  description: string | null;
  display_order: number;
  is_active: boolean;
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

// ---------------------------------------------------------------------------
// Part C & MVP P6 Frontend Types
// ---------------------------------------------------------------------------

export interface GanttActivity {
  id: string;
  activity_id: string;
  activity_name: string;
  wbs_code: string;
  wbs_name: string;
  discipline: string;
  contractor_name: string;
  area: string;
  unit: string;
  planned_start: string | null;
  planned_finish: string | null;
  original_duration_days: number;
  percent_complete_plan: number;
  actual_start: string | null;
  actual_finish: string | null;
  actual_percent_complete: number;
  total_float_days: number;
  is_critical: boolean;
  delay_risk_score: number;
  status: "completed" | "in_progress" | "not_started" | "delayed";
  predecessors: string[];
  predecessors_detail?: Array<{ activity_id: string; type: string; lag: number }>;
  successors: string[];
}

export interface WBSNode {
  wbs_code: string;
  wbs_name: string;
  activities: GanttActivity[];
  planned_start: string | null;
  planned_finish: string | null;
  actual_start: string | null;
  actual_finish: string | null;
  percent_complete: number;
  is_critical: boolean;
}

export interface DependencyEdge {
  id: string;
  predecessor: string;
  successor: string;
  type: string;
  lag: number;
}

export interface GanttDataResponse {
  total: number;
  activities: GanttActivity[];
  wbs_tree: WBSNode[];
  dependencies: DependencyEdge[];
  summary: {
    total_activities: number;
    filtered_count: number;
    completed_count: number;
    in_progress_count: number;
    not_started_count: number;
    delayed_count: number;
    critical_count: number;
    min_date: string | null;
    max_date: string | null;
  };
}

export interface UpdateFeedItem {
  id: string;
  source_type: "review_queue" | "data_quality" | "schedule_change" | "document" | "entity_alias";
  severity: "critical" | "warning" | "info";
  title: string;
  detected_change: string;
  affected_activity_id: string | null;
  affected_activity_name: string | null;
  current_value: any;
  proposed_value: any;
  confidence: number | null;
  timestamp: string;
  source_info: string | null;
  action_label: string;
  target_route: string;
}

export interface UpdateCenterSummary {
  total_items: number;
  pending_reviews: number;
  data_quality_flags: number;
  schedule_changes: number;
  pending_documents: number;
  pending_aliases: number;
}

export interface UpdateCenterFeedResponse {
  summary: UpdateCenterSummary;
  items: UpdateFeedItem[];
}

export interface DelayKPIs {
  total_delayed_activities: number;
  total_delay_days: number;
  average_delay_days: number;
  max_delay_days: number;
  critical_delayed_count: number;
}

export interface MajorDelayRecord {
  event_id: string;
  activity_id: string;
  activity_name: string;
  discipline: string;
  contractor: string;
  date: string;
  delay_days: number;
  cause: string;
  reason: string;
  source: string;
  confidence: number;
  impact: string;
  recommended_action: string;
}

export interface DelayAnalyticsResponse {
  kpis: DelayKPIs;
  total_delay_events: number;
  cause_breakdown: Array<{
    cause: string;
    category: string;
    label: string;
    display_name: string;
    count: number;
    percentage: number;
    delay_days: number;
    estimated_days_lost: number;
  }>;
  categories: Array<{
    cause: string;
    label: string;
    count: number;
    percentage: number;
    delay_days: number;
  }>;
  by_discipline: Array<{
    discipline: string;
    count: number;
    delay_days: number;
    percentage: number;
  }>;
  by_contractor: Array<{
    contractor: string;
    total_events: number;
    delay_events: number;
    delayed_activities: number;
    delay_ratio: number;
    avg_variance_factor: number;
    delay_days: number;
    primary_delay_cause: string;
  }>;
  by_location: Array<{
    area: string;
    location: string;
    delayed_events: number;
    active_blockers: number;
    sample_blockers: string[];
  }>;
  bottlenecks: Array<{
    area: string;
    location: string;
    delayed_events: number;
    active_blockers: number;
    sample_blockers: string[];
  }>;
  recurring_blockers: Array<{
    description: string;
    occurrences: number;
    latest_reported: string;
  }>;
  trend: Array<{
    month: string;
    delay_days: number;
    event_count: number;
  }>;
  major_delays: MajorDelayRecord[];
}

export interface ParsedFilterResponse {
  query: string;
  filters: {
    target_type: string;
    discipline: string | null;
    location: string | null;
    status: string | null;
    is_delayed: boolean;
    is_critical: boolean;
    equipment_tag: string | null;
    has_blocker: boolean;
    keyword: string | null;
  };
  explanation: string;
  suggested_route: string;
  results_preview: Array<{
    id: string;
    record_type: string;
    title: string;
    discipline: string;
    status: string;
    progress_pct: number | null;
    location: string;
    is_critical: boolean;
    link_url: string;
    provenance: string;
    summary: string;
  }>;
  total_matches: number;
}

export interface ActivityDetailAggregate {
  identity: {
    id: string;
    activity_id: string;
    activity_name: string;
    wbs_code: string;
    wbs_name: string;
    discipline: string;
    contractor_name: string;
    area: string;
    unit: string;
    is_critical: boolean;
  };
  schedule: {
    planned_start: string | null;
    planned_finish: string | null;
    original_duration_days: number;
    percent_complete_plan: number;
    actual_start: string | null;
    actual_finish: string | null;
    actual_percent_complete: number;
    total_float_days: number;
    status: "completed" | "in_progress" | "not_started" | "delayed";
    predecessors: Array<{ activity_id: string; type: string; lag: number }>;
    successors: Array<{ activity_id: string; type: string; lag: number }>;
  };
  progress: {
    percent_complete: number;
    history: Array<{
      event_id: string;
      timestamp: string;
      extracted_description: string;
      percent_complete: number | null;
      actual_start: string | null;
      actual_finish: string | null;
      blocker_description: string | null;
      delay_category: string | null;
      confidence_score: number | null;
      provenance_category: string;
    }>;
  };
  intelligence: {
    latest_event_id: string | null;
    extracted_description: string | null;
    confidence_score: number | null;
    confidence_tier: string;
    extracted_by: string;
    match_candidates: Array<{
      candidate_activity_id: string;
      fuzzy_score: number | null;
      semantic_score: number | null;
      llm_score: number | null;
      final_score: number | null;
      rank: number | null;
      was_selected: boolean;
    }>;
    source_document: {
      document_id: string;
      sender_id: string;
      source_type: string;
      received_at: string | null;
      raw_text_excerpt: string | null;
      mime_type: string | null;
    } | null;
    evidence_breadcrumb: Array<{
      level: string;
      id: string;
      label: string;
    }>;
  };
  risk: {
    delay_risk_score: number;
    predicted_finish: string | null;
    predicted_delay_days: number;
    delay_risk_percentage: number;
    confidence: number;
    variance_factor: number;
    contributing_factors: string[];
    narrative: string;
    explainability_strip: Array<{
      event_id: string;
      activity_id_plan: string;
      actual_duration_days: number;
      planned_duration_days: number;
      variance_days: number;
      date: string;
    }>;
  };
  audit: {
    decisions: Array<{
      decision_id: string;
      decision: string;
      reviewer: string;
      notes: string | null;
      decided_at: string | null;
      corrected_fields: any;
    }>;
    correction_history: any[];
    planner_notes: string | null;
    created_at: string | null;
    updated_at: string | null;
  };
}
