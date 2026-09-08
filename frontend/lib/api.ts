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
