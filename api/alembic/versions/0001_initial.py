"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-14
"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("team", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("team", sa.String(120)),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text),
    )

    op.create_table(
        "problems",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "resolved", name="problemstatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("incident_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Enum("new", "triaged", "in_progress", "resolved", "closed", name="incidentstatus"),
            nullable=False,
            server_default="new",
        ),
        sa.Column("priority", sa.Enum("P1", "P2", "P3", "P4", name="priority"), nullable=True),
        sa.Column("impact", sa.Integer),
        sa.Column("urgency", sa.Integer),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id")),
        sa.Column("assigned_team", sa.String(120)),
        sa.Column("assigned_agent_id", sa.Integer, sa.ForeignKey("agents.id")),
        sa.Column("reporter", sa.String(255), nullable=False),
        sa.Column("resolution_note", sa.Text),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by_user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("problem_id", sa.Integer, sa.ForeignKey("problems.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "search_tsv",
            TSVECTOR,
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))", persisted=True
            ),
        ),
    )
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_priority", "incidents", ["priority"])
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])
    op.create_index("ix_incidents_search_tsv", "incidents", ["search_tsv"], postgresql_using="gin")
    op.execute(
        "CREATE INDEX ix_incidents_embedding_hnsw ON incidents USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("incident_id", sa.Integer, sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_internal", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "kb_articles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("symptom", sa.Text, nullable=False),
        sa.Column("cause", sa.Text, nullable=False),
        sa.Column("resolution_steps", sa.Text, nullable=False),
        sa.Column("verification", sa.Text, nullable=False),
        sa.Column("tags", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column(
            "status", sa.Enum("draft", "published", "rejected", name="kbstatus"), nullable=False, server_default="draft"
        ),
        sa.Column("source_incident_id", sa.Integer, sa.ForeignKey("incidents.id")),
        sa.Column("created_by", sa.Enum("seed", "ai", "human", name="kbsource"), nullable=False, server_default="human"),
        sa.Column("approved_by_user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "search_tsv",
            TSVECTOR,
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(symptom, '') || ' ' "
                "|| coalesce(cause, '') || ' ' || coalesce(resolution_steps, ''))",
                persisted=True,
            ),
        ),
    )
    op.create_index("ix_kb_articles_status", "kb_articles", ["status"])
    op.create_index("ix_kb_articles_search_tsv", "kb_articles", ["search_tsv"], postgresql_using="gin")
    op.execute(
        "CREATE INDEX ix_kb_articles_embedding_hnsw ON kb_articles USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    op.create_table(
        "incident_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("from_incident_id", sa.Integer, sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_incident_id", sa.Integer, sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_type", sa.Enum("duplicate_of", "related", name="linktype"), nullable=False),
        sa.Column("similarity", sa.Float, nullable=False),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("from_incident_id", "to_incident_id", "link_type", name="uq_incident_link"),
    )

    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("stage", sa.Enum("triage", "ground", "synthesize", "embed", name="aistage"), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Integer),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("input_summary", sa.Text),
        sa.Column("retrieved_ids", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("raw_output", sa.Text),
        sa.Column("parsed_ok", sa.Boolean, nullable=False),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("input_tokens", sa.Integer),
        sa.Column("output_tokens", sa.Integer),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_runs_entity", "ai_runs", ["entity_type", "entity_id"])

    op.create_table(
        "embedding_cache",
        sa.Column("content_hash", sa.String(64), primary_key=True),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("embedding_cache")
    op.drop_table("ai_runs")
    op.drop_table("incident_links")
    op.drop_table("kb_articles")
    op.drop_table("comments")
    op.drop_table("incidents")
    op.drop_table("problems")
    op.drop_table("categories")
    op.drop_table("agents")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS aistage")
    op.execute("DROP TYPE IF EXISTS linktype")
    op.execute("DROP TYPE IF EXISTS kbsource")
    op.execute("DROP TYPE IF EXISTS kbstatus")
    op.execute("DROP TYPE IF EXISTS priority")
    op.execute("DROP TYPE IF EXISTS incidentstatus")
    op.execute("DROP TYPE IF EXISTS problemstatus")
