import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db import Base

EMBEDDING_DIM = settings.embedding_dim


class IncidentStatus(str, enum.Enum):
    new = "new"
    triaged = "triaged"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Priority(str, enum.Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class KbStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    rejected = "rejected"


class KbSource(str, enum.Enum):
    seed = "seed"
    ai = "ai"
    human = "human"


class LinkType(str, enum.Enum):
    duplicate_of = "duplicate_of"
    related = "related"


class ProblemStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class AiStage(str, enum.Enum):
    triage = "triage"
    ground = "ground"
    synthesize = "synthesize"
    embed = "embed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    team: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    team: Mapped[str | None] = mapped_column(String(120))


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index(
            "ix_incidents_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_incidents_search_tsv", "search_tsv", postgresql_using="gin"),
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_priority", "priority"),
        Index("ix_incidents_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        default=IncidentStatus.new, server_default=IncidentStatus.new.value, nullable=False
    )
    priority: Mapped[Priority | None] = mapped_column(nullable=True)
    impact: Mapped[int | None] = mapped_column(Integer)
    urgency: Mapped[int | None] = mapped_column(Integer)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    assigned_team: Mapped[str | None] = mapped_column(String(120))
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    reporter: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))", persisted=True),
    )

    category: Mapped[Category | None] = relationship()
    assigned_agent: Mapped[Agent | None] = relationship()
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="Comment.created_at"
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    author: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped[Incident] = relationship(back_populates="comments")


class KbArticle(Base):
    __tablename__ = "kb_articles"
    __table_args__ = (
        Index(
            "ix_kb_articles_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_kb_articles_search_tsv", "search_tsv", postgresql_using="gin"),
        Index("ix_kb_articles_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    symptom: Mapped[str] = mapped_column(Text, nullable=False)
    cause: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_steps: Mapped[str] = mapped_column(Text, nullable=False)
    verification: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    status: Mapped[KbStatus] = mapped_column(default=KbStatus.draft, server_default=KbStatus.draft.value)
    source_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"))
    created_by: Mapped[KbSource] = mapped_column(default=KbSource.human)
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(symptom, '') || ' ' "
            "|| coalesce(cause, '') || ' ' || coalesce(resolution_steps, ''))",
            persisted=True,
        ),
    )


class IncidentLink(Base):
    __tablename__ = "incident_links"
    __table_args__ = (UniqueConstraint("from_incident_id", "to_incident_id", "link_type", name="uq_incident_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    to_incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    link_type: Mapped[LinkType] = mapped_column(nullable=False)
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ProblemStatus] = mapped_column(default=ProblemStatus.open, server_default=ProblemStatus.open.value)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    incident_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stage: Mapped[AiStage] = mapped_column(nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_summary: Mapped[str | None] = mapped_column(Text)
    retrieved_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    raw_output: Mapped[str | None] = mapped_column(Text)
    parsed_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    content_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
