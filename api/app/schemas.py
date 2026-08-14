from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import AiStage, IncidentStatus, KbSource, KbStatus, LinkType, Priority, ProblemStatus

# ---------------------------------------------------------------- auth

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    team: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- shared

class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class AgentOut(BaseModel):
    id: int
    name: str
    team: str | None = None

    model_config = {"from_attributes": True}


class CommentOut(BaseModel):
    id: int
    author: str
    body: str
    is_internal: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    author: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=5000)
    is_internal: bool = False


# ---------------------------------------------------------------- incidents

class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10_000)
    reporter: str = Field(min_length=1, max_length=255)


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    priority: Priority | None = None
    category_id: int | None = None
    assigned_team: str | None = None
    assigned_agent_id: int | None = None
    updated_at: datetime | None = Field(
        default=None, description="Client's last-seen updated_at, for optimistic concurrency."
    )


class IncidentResolve(BaseModel):
    resolution_note: str = Field(min_length=20, max_length=10_000)
    updated_at: datetime | None = None


class IncidentListItem(BaseModel):
    id: int
    reference: str
    title: str
    status: IncidentStatus
    priority: Priority | None
    assigned_team: str | None
    reporter: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentLinkOut(BaseModel):
    id: int
    from_incident_id: int
    to_incident_id: int
    link_type: LinkType
    similarity: float
    confirmed: bool

    model_config = {"from_attributes": True}


class IncidentDetail(BaseModel):
    id: int
    reference: str
    title: str
    description: str
    status: IncidentStatus
    priority: Priority | None
    impact: int | None
    urgency: int | None
    category: CategoryOut | None
    assigned_team: str | None
    assigned_agent: AgentOut | None
    reporter: str
    resolution_note: str | None
    resolved_at: datetime | None
    problem_id: int | None
    created_at: datetime
    updated_at: datetime
    comments: list[CommentOut]
    links: list["IncidentLinkOut"] = Field(default_factory=list)
    ai_runs: list["AiRunOut"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LinkConfirmRequest(BaseModel):
    confirmed: bool


# ---------------------------------------------------------------- kb

class KbArticleCreateFields(BaseModel):
    title: str
    symptom: str
    cause: str
    resolution_steps: str
    verification: str
    tags: list[str] = Field(default_factory=list)


class KbArticleUpdate(BaseModel):
    title: str | None = None
    symptom: str | None = None
    cause: str | None = None
    resolution_steps: str | None = None
    verification: str | None = None
    tags: list[str] | None = None


class KbArticleOut(BaseModel):
    id: int
    reference: str
    title: str
    symptom: str
    cause: str
    resolution_steps: str
    verification: str
    tags: list[str]
    status: KbStatus
    source_incident_id: int | None
    created_by: KbSource
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- problems

class ProblemOut(BaseModel):
    id: int
    reference: str
    title: str
    summary: str
    status: ProblemStatus
    detected_at: datetime
    incident_count: int
    incidents: list[IncidentListItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- ai

class TriageRationale(BaseModel):
    category: str
    impact: str
    urgency: str
    team: str


class TriageEntities(BaseModel):
    error_codes: list[str] = Field(default_factory=list)
    applications: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)


class TriageProposal(BaseModel):
    category: str
    affected_system: str
    impact: int = Field(ge=1, le=4)
    urgency: int = Field(ge=1, le=4)
    suggested_team: str
    entities: TriageEntities
    summary: str = Field(max_length=200)
    rationale: TriageRationale
    priority: Priority


class ApplyTriageRequest(BaseModel):
    category: str
    impact: int = Field(ge=1, le=4)
    urgency: int = Field(ge=1, le=4)
    suggested_team: str
    priority: Priority


class GroundedAnswer(BaseModel):
    has_sufficient_evidence: bool
    diagnosis: str
    recommended_steps: list[str]
    citations: list[str]
    confidence_reason: str
    escalate_to: str | None = None
    degraded: bool = False


class SynthesisDraft(BaseModel):
    action: str
    target_article_reference: str | None = None
    title: str
    symptom: str
    cause: str
    resolution_steps: list[str]
    verification: str
    tags: list[str]
    reasoning: str


class AiRunOut(BaseModel):
    id: int
    stage: AiStage
    entity_type: str
    entity_id: int | None
    model: str
    prompt_version: str
    input_summary: str | None
    retrieved_ids: list[str]
    parsed_ok: bool
    retry_count: int
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------- stats

class StatsOut(BaseModel):
    open_incidents: int
    p1_incidents: int
    kb_published: int
    kb_draft: int
    resolution_rate: float
    abstain_rate: float
    ai_enabled: bool


IncidentDetail.model_rebuild()
