export type IncidentStatus = "new" | "triaged" | "in_progress" | "resolved" | "closed";
export type Priority = "P1" | "P2" | "P3" | "P4";
export type KbStatus = "draft" | "published" | "rejected";
export type KbSource = "seed" | "ai" | "human";
export type LinkType = "duplicate_of" | "related";
export type ProblemStatus = "open" | "resolved";
export type AiStage = "triage" | "ground" | "synthesize" | "embed";

export interface Category {
  id: number;
  name: string;
  description: string | null;
}

export interface Agent {
  id: number;
  name: string;
  team: string | null;
}

export interface Comment {
  id: number;
  author: string;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface IncidentLink {
  id: number;
  from_incident_id: number;
  to_incident_id: number;
  link_type: LinkType;
  similarity: number;
  confirmed: boolean;
}

export interface AiRun {
  id: number;
  stage: AiStage;
  entity_type: string;
  entity_id: number | null;
  model: string;
  prompt_version: string;
  input_summary: string | null;
  retrieved_ids: string[];
  parsed_ok: boolean;
  retry_count: number;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  error: string | null;
  created_at: string;
}

export interface IncidentListItem {
  id: number;
  reference: string;
  title: string;
  status: IncidentStatus;
  priority: Priority | null;
  assigned_team: string | null;
  reporter: string;
  created_at: string;
  updated_at: string;
}

export interface IncidentDetail extends IncidentListItem {
  description: string;
  impact: number | null;
  urgency: number | null;
  category: Category | null;
  assigned_agent: Agent | null;
  resolution_note: string | null;
  resolved_at: string | null;
  problem_id: number | null;
  comments: Comment[];
  links: IncidentLink[];
  ai_runs: AiRun[];
}

export interface KbArticle {
  id: number;
  reference: string;
  title: string;
  symptom: string;
  cause: string;
  resolution_steps: string;
  verification: string;
  tags: string[];
  status: KbStatus;
  source_incident_id: number | null;
  created_by: KbSource;
  created_at: string;
  updated_at: string;
}

export interface Problem {
  id: number;
  reference: string;
  title: string;
  summary: string;
  status: ProblemStatus;
  detected_at: string;
  incident_count: number;
  incidents: IncidentListItem[];
}

export interface TriageProposal {
  category: string;
  affected_system: string;
  impact: number;
  urgency: number;
  suggested_team: string;
  entities: { error_codes: string[]; applications: string[]; platforms: string[] };
  summary: string;
  rationale: { category: string; impact: string; urgency: string; team: string };
  priority: Priority;
}

export interface GroundedAnswer {
  has_sufficient_evidence: boolean;
  diagnosis: string;
  recommended_steps: string[];
  citations: string[];
  confidence_reason: string;
  escalate_to: string | null;
  degraded: boolean;
}

export interface GroundSource {
  id: number;
  reference: string;
  kind: "KB" | "INC";
  title: string;
  fused_score: number;
  vector_rank: number | null;
  lexical_rank: number | null;
}

export interface Stats {
  open_incidents: number;
  p1_incidents: number;
  kb_published: number;
  kb_draft: number;
  resolution_rate: number;
  abstain_rate: number;
  ai_enabled: boolean;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, unknown> };
}
