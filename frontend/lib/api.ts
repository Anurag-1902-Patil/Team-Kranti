import type {
  ActivityPrediction,
  DelayIntelligence,
  DisciplineLookup,
  EntityAlias,
  NLSearchResult,
  PlanActivity,
  ProgressEvent,
  ProgressEventList,
  ResourceIntelligence,
  ScheduleHealth,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Get the auth token — named token from localStorage takes priority. */
export function getAuthToken(): string {
  if (typeof window !== "undefined") {
    const named = localStorage.getItem("reviewer_token");
    if (named) return named;
  }
  // Fallback: env var (used in Docker/CI where there's no login UI)
  return process.env.NEXT_PUBLIC_REVIEWER_TOKEN || "dev-insecure-token";
}

export function clearAuthToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("reviewer_token");
    localStorage.removeItem("reviewer_name");
    localStorage.removeItem("reviewer_role");
  }
}

// Legacy export kept for pages that haven't migrated yet
export const AUTH_TOKEN = "";

export function apiHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getAuthToken()}`,
  };
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = {
    ...apiHeaders(),
    ...options.headers,
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });
  } catch (err) {
    // If localhost connection failed (common Windows IPv6 ::1 resolution issue), try 127.0.0.1
    if (API_BASE.includes("localhost")) {
      const fallbackBase = API_BASE.replace("localhost", "127.0.0.1");
      try {
        res = await fetch(`${fallbackBase}${path}`, {
          ...options,
          headers,
        });
      } catch {
        throw new Error(
          `Unable to reach backend at ${API_BASE} or ${fallbackBase}. Ensure Uvicorn is running on port 8000.`
        );
      }
    } else {
      throw err;
    }
  }

  if (res.status === 401) {
    // Token expired or invalid — redirect to login
    if (typeof window !== "undefined") {
      localStorage.removeItem("reviewer_token");
      localStorage.removeItem("reviewer_name");
      localStorage.removeItem("reviewer_role");
      window.location.href = "/login";
    }
    throw new Error("Unauthorized — please log in again.");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Typed API Endpoints
// ---------------------------------------------------------------------------

export async function fetchScheduleHealth(projectId: string = "TEST"): Promise<ScheduleHealth> {
  return apiFetch<ScheduleHealth>(`/api/v1/analysis/schedule-health?project_id=${encodeURIComponent(projectId)}`);
}

export async function fetchDelayIntelligence(projectId: string = "TEST"): Promise<DelayIntelligence> {
  return apiFetch<DelayIntelligence>(`/api/v1/analysis/delays?project_id=${encodeURIComponent(projectId)}`);
}

export async function fetchResourceIntelligence(projectId: string = "TEST"): Promise<ResourceIntelligence> {
  return apiFetch<ResourceIntelligence>(`/api/v1/analysis/resources?project_id=${encodeURIComponent(projectId)}`);
}

export async function fetchActivityPrediction(activityId: string): Promise<ActivityPrediction> {
  return apiFetch<ActivityPrediction>(`/api/v1/analysis/predictions/${encodeURIComponent(activityId)}`);
}

export async function fetchPlanActivities(projectId: string = "TEST"): Promise<PlanActivity[]> {
  return apiFetch<PlanActivity[]>(`/api/v1/schedule/activities?project_id=${encodeURIComponent(projectId)}`);
}

export async function fetchProgressEvents(
  page: number = 1,
  pageSize: number = 20,
  matchStatus?: string
): Promise<ProgressEventList> {
  let url = `/api/v1/events?page=${page}&page_size=${pageSize}`;
  if (matchStatus) url += `&match_status=${encodeURIComponent(matchStatus)}`;
  return apiFetch<ProgressEventList>(url);
}

export async function fetchEventDetail(eventId: string): Promise<ProgressEvent> {
  return apiFetch<ProgressEvent>(`/api/v1/events/${eventId}`);
}

export async function reEditProgressEvent(
  eventId: string,
  payload: {
    corrected_fields: Record<string, unknown>;
    notes?: string;
  }
): Promise<{ status: string; event_id: string; total_edits: number }> {
  return apiFetch(`/api/v1/review/${eventId}/re-edit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitReviewDecision(
  eventId: string,
  decision: "accepted" | "edited" | "declined" | "confirmed_new",
  payload: {
    corrected_activity_id?: string;
    notes?: string;
  }
): Promise<{ status: string; decision_id: string }> {
  return apiFetch(`/api/v1/review/${eventId}/decide`, {
    method: "POST",
    body: JSON.stringify({
      decision,
      ...payload,
    }),
  });
}

export async function fetchAliases(status?: string): Promise<EntityAlias[]> {
  let url = "/api/v1/entities/aliases";
  if (status) url += `?status=${encodeURIComponent(status)}`;
  return apiFetch<EntityAlias[]>(url);
}

export async function decideAlias(
  aliasId: string,
  decision: "approve" | "reject",
  canonicalName?: string
): Promise<{ status: string; alias_id: string; decision: string }> {
  return apiFetch(`/api/v1/review/alias/${aliasId}/decide`, {
    method: "POST",
    body: JSON.stringify({
      decision,
      canonical_name: canonicalName,
    }),
  });
}

export async function searchNatural(query: string): Promise<NLSearchResult> {
  return apiFetch<NLSearchResult>("/api/v1/search/natural", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export async function fetchDisciplines(): Promise<DisciplineLookup[]> {
  return apiFetch<DisciplineLookup[]>("/api/v1/entities/disciplines");
}

// ---------------------------------------------------------------------------
// Part C & MVP API Methods
// ---------------------------------------------------------------------------

import type {
  ActivityDetailAggregate,
  DelayAnalyticsResponse,
  GanttDataResponse,
  ParsedFilterResponse,
  UpdateCenterFeedResponse,
} from "./types";

export async function fetchGanttData(params?: {
  discipline?: string;
  status?: string;
  contractor?: string;
  critical_only?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<GanttDataResponse> {
  const q = new URLSearchParams();
  if (params?.discipline) q.set("discipline", params.discipline);
  if (params?.status) q.set("status", params.status);
  if (params?.contractor) q.set("contractor", params.contractor);
  if (params?.critical_only) q.set("critical_only", "true");
  if (params?.search) q.set("search", params.search);
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));

  const qs = q.toString();
  return apiFetch<GanttDataResponse>(`/api/v1/schedule/gantt${qs ? `?${qs}` : ""}`);
}

export async function fetchUpdateCenterFeed(params?: {
  source_type?: string;
  severity?: string;
  page?: number;
  page_size?: number;
}): Promise<UpdateCenterFeedResponse> {
  const q = new URLSearchParams();
  if (params?.source_type) q.set("source_type", params.source_type);
  if (params?.severity) q.set("severity", params.severity);
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));

  const qs = q.toString();
  return apiFetch<UpdateCenterFeedResponse>(`/api/v1/updates/feed${qs ? `?${qs}` : ""}`);
}

export async function fetchDelayAnalyticsDetailed(params?: {
  discipline?: string;
  contractor?: string;
  location?: string;
  cause?: string;
  start_date?: string;
  end_date?: string;
}): Promise<DelayAnalyticsResponse> {
  const q = new URLSearchParams();
  if (params?.discipline) q.set("discipline", params.discipline);
  if (params?.contractor) q.set("contractor", params.contractor);
  if (params?.location) q.set("location", params.location);
  if (params?.cause) q.set("cause", params.cause);
  if (params?.start_date) q.set("start_date", params.start_date);
  if (params?.end_date) q.set("end_date", params.end_date);

  const qs = q.toString();
  return apiFetch<DelayAnalyticsResponse>(`/api/v1/analysis/delays${qs ? `?${qs}` : ""}`);
}

export async function parseSearchFilter(query: string): Promise<ParsedFilterResponse> {
  return apiFetch<ParsedFilterResponse>("/api/v1/search/parse-filter", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export async function fetchActivityDetailAggregate(activityId: string): Promise<ActivityDetailAggregate> {
  return apiFetch<ActivityDetailAggregate>(`/api/v1/schedule/activities/${encodeURIComponent(activityId)}/detail`);
}

export async function acceptReviewItem(eventId: string, notes?: string): Promise<{ decision_id: string; decision: string }> {
  return apiFetch(`/api/v1/review/${eventId}/accept`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export async function editReviewItem(eventId: string, correctedActivityId: string, notes?: string): Promise<{ decision_id: string; decision: string }> {
  return apiFetch(`/api/v1/review/${eventId}/edit`, {
    method: "POST",
    body: JSON.stringify({
      corrected_activity_id: correctedActivityId,
      notes,
    }),
  });
}

export async function declineReviewItem(eventId: string, notes?: string): Promise<{ decision_id: string; decision: string }> {
  return apiFetch(`/api/v1/review/${eventId}/decline`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export async function confirmNewActivity(
  eventId: string,
  payload: {
    activity_name: string;
    discipline: string;
    wbs_code?: string;
    planned_start?: string;
    planned_finish?: string;
    original_duration_days?: number;
    notes?: string;
  }
): Promise<{ decision_id: string; new_activity_id: string }> {
  return apiFetch(`/api/v1/review/${eventId}/confirm_new`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

