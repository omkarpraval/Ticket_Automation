"""Duplicate detection and storm clustering. Both are pure math over embeddings
already computed at incident-creation time - no LLM call. Using an LLM to compute
similarity when a cosine distance is one index lookup away would be slower,
costlier, and non-reproducible (identical inputs could get different answers), so
this stays deterministic Python + SQL. The one LLM call in this module is the
one-line problem summary, which is genuinely generative (not a similarity judgement).
"""

from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import storm_summary_prompt
from app.ai.provider import AIProvider, ProviderRateLimited, ProviderUnavailable
from app.config import settings
from app.models import Incident, IncidentLink, LinkType, Problem

_NEIGHBORS_SQL = text(
    """
    SELECT id, reference, title, category_id, created_at, problem_id,
           1 - (embedding <=> (:qe)::vector) AS similarity
    FROM incidents
    WHERE embedding IS NOT NULL AND id != :exclude_id AND created_at >= :window_start
    ORDER BY similarity DESC
    LIMIT 25
    """
)


async def detect_duplicates(db: AsyncSession, incident: Incident) -> list[IncidentLink]:
    """Nearest neighbours among all incidents; similarity above DUPLICATE_THRESHOLD
    becomes an unconfirmed duplicate_of suggestion the UI can dismiss or confirm."""
    if incident.embedding is None:
        return []

    rows = (
        await db.execute(
            _NEIGHBORS_SQL,
            {"qe": str(incident.embedding), "exclude_id": incident.id, "window_start": incident.created_at - timedelta(days=3650)},
        )
    ).all()

    created: list[IncidentLink] = []
    for row in rows:
        if row.similarity < settings.duplicate_threshold:
            continue
        stmt = (
            pg_insert(IncidentLink)
            .values(
                from_incident_id=incident.id,
                to_incident_id=row.id,
                link_type=LinkType.duplicate_of,
                similarity=float(row.similarity),
                confirmed=False,
            )
            .on_conflict_do_nothing(index_elements=["from_incident_id", "to_incident_id", "link_type"])
            .returning(IncidentLink)
        )
        result = await db.execute(stmt)
        link = result.scalar_one_or_none()
        if link is not None:
            created.append(link)
    if created:
        await db.flush()
    return created


async def detect_storm(db: AsyncSession, incident: Incident, provider: AIProvider | None) -> Problem | None:
    """Counts incidents created within STORM_WINDOW_MINUTES whose similarity to the
    new incident exceeds 0.80. At STORM_MIN_INCIDENTS, groups them into a Problem
    (reusing an existing open one if any member already belongs to one)."""
    if incident.embedding is None:
        return None

    window_start = incident.created_at - timedelta(minutes=settings.storm_window_minutes)
    rows = (
        await db.execute(
            _NEIGHBORS_SQL, {"qe": str(incident.embedding), "exclude_id": incident.id, "window_start": window_start}
        )
    ).all()
    members = [row for row in rows if row.similarity > 0.80]
    if len(members) + 1 < settings.storm_min_incidents:
        return None

    existing_problem_id = next((row.problem_id for row in members if row.problem_id), None)
    member_ids = [row.id for row in members] + [incident.id]

    if existing_problem_id:
        problem = await db.get(Problem, existing_problem_id)
    else:
        titles = [incident.title] + [row.title for row in members]
        summary = await _summarize_storm(provider, titles, incident.category_id, db)
        reference = await _next_problem_reference(db)
        problem = Problem(
            reference=reference,
            title=summary.splitlines()[0][:200] if summary else f"Related incident cluster ({len(member_ids)})",
            summary="\n".join(summary.splitlines()[1:]).strip() or "Automatically detected cluster of similar incidents.",
            incident_count=0,
        )
        db.add(problem)
        await db.flush()

    await db.execute(
        Incident.__table__.update().where(Incident.id.in_(member_ids)).values(problem_id=problem.id)
    )
    count_result = await db.execute(select(Incident.id).where(Incident.problem_id == problem.id))
    problem.incident_count = len(count_result.all())
    await db.flush()
    return problem


async def _summarize_storm(provider: AIProvider | None, titles: list[str], category_id: int | None, db: AsyncSession) -> str:
    if provider is None or not settings.ai_enabled:
        return f"Related incident cluster\n{len(titles)} similar incidents arrived in a short window."
    category_name = None
    if category_id is not None:
        from app.models import Category

        category = await db.get(Category, category_id)
        category_name = category.name if category else None
    prompt = storm_summary_prompt(incident_titles=titles, shared_category=category_name)
    try:
        result = await provider.complete_text(prompt=prompt, temperature=0.3)
        return result.text
    except (ProviderRateLimited, ProviderUnavailable):
        return f"Related incident cluster\n{len(titles)} similar incidents arrived in a short window."


async def _next_problem_reference(db: AsyncSession) -> str:
    count = (await db.execute(select(Problem.id))).all()
    return f"PRB-{len(count) + 1:03d}"
