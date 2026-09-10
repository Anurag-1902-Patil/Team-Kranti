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
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...apiHeaders(),
      ...options.headers,
    },
  });

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

