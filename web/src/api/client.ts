import type {
  AiRun,
  IncidentDetail,
  IncidentListItem,
  IncidentStatus,
  KbArticle,
  KbStatus,
  Priority,
  Problem,
  Stats,
  TriageProposal,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "helix_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  status: number;

  constructor(code: string, message: string, status: number, details: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let code = "INTERNAL";
    let message = `Request failed with status ${res.status}`;
    let details: Record<string, unknown> = {};
    try {
      const body = await res.json();
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
      details = body.error?.details ?? {};
    } catch {
      // non-JSON error body, fall back to defaults above
    }
    throw new ApiError(code, message, res.status, details);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------- auth

export function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function me() {
  return request<{ id: number; email: string; display_name: string; team: string | null }>("/api/auth/me");
}

// ---------------------------------------------------------------- incidents

export interface IncidentFilters {
  status?: IncidentStatus;
  priority?: Priority;
  team?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export function listIncidents(filters: IncidentFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") params.set(k, String(v));
  });
  const qs = params.toString();
  return request<IncidentListItem[]>(`/api/incidents${qs ? `?${qs}` : ""}`);
}

export function getIncident(id: number) {
  return request<IncidentDetail>(`/api/incidents/${id}`);
}

export function createIncident(payload: { title: string; description: string; reporter: string }) {
  return request<IncidentDetail>("/api/incidents", { method: "POST", body: JSON.stringify(payload) });
}

export function updateIncident(
  id: number,
  payload: Partial<{
    status: IncidentStatus;
    priority: Priority;
    category_id: number;
    assigned_team: string;
    assigned_agent_id: number;
    updated_at: string;
  }>
) {
  return request<IncidentDetail>(`/api/incidents/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function addComment(id: number, payload: { author: string; body: string; is_internal: boolean }) {
  return request(`/api/incidents/${id}/comments`, { method: "POST", body: JSON.stringify(payload) });
}

export function resolveIncident(id: number, payload: { resolution_note: string; updated_at?: string }) {
  return request<IncidentDetail>(`/api/incidents/${id}/resolve`, { method: "POST", body: JSON.stringify(payload) });
}

export function triageIncident(id: number) {
  return request<TriageProposal>(`/api/incidents/${id}/triage`, { method: "POST" });
}

export function applyTriage(id: number, payload: TriageProposal) {
  return request<IncidentDetail>(`/api/incidents/${id}/apply-triage`, {
    method: "POST",
    body: JSON.stringify({
      category: payload.category,
      impact: payload.impact,
      urgency: payload.urgency,
      suggested_team: payload.suggested_team,
      priority: payload.priority,
    }),
  });
}

export function similarIncidents(id: number) {
  return request(`/api/incidents/${id}/similar`);
}

export function confirmLink(linkId: number, confirmed: boolean) {
  return request(`/api/incident-links/${linkId}/confirm`, { method: "POST", body: JSON.stringify({ confirmed }) });
}

export function groundUrl(id: number): string {
  return `${BASE_URL}/api/incidents/${id}/ground`;
}

// ---------------------------------------------------------------- kb

export function listKb(status?: KbStatus) {
  const qs = status ? `?status=${status}` : "";
  return request<KbArticle[]>(`/api/kb${qs}`);
}

export function getKbArticle(id: number) {
  return request<KbArticle>(`/api/kb/${id}`);
}

export function updateKbArticle(id: number, payload: Partial<KbArticle>) {
  return request<KbArticle>(`/api/kb/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function publishKbArticle(id: number) {
  return request<KbArticle>(`/api/kb/${id}/publish`, { method: "POST" });
}

export function rejectKbArticle(id: number) {
  return request<KbArticle>(`/api/kb/${id}/reject`, { method: "POST" });
}

// ---------------------------------------------------------------- problems

export function listProblems() {
  return request<Problem[]>("/api/problems");
}

// ---------------------------------------------------------------- ai / stats

export function listAiRuns(entityType?: string, entityId?: number) {
  const params = new URLSearchParams();
  if (entityType) params.set("entity_type", entityType);
  if (entityId !== undefined) params.set("entity_id", String(entityId));
  const qs = params.toString();
  return request<AiRun[]>(`/api/ai-runs${qs ? `?${qs}` : ""}`);
}

export function getStats() {
  return request<Stats>("/api/stats");
}

export function health() {
  return request<{ status: string; db: boolean; ai_enabled: boolean }>("/health");
}
