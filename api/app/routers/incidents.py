import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.ai.grounding import ground_incident
from app.ai.provider import AIProvider
from app.ai.synthesis import run_synthesis
from app.ai.triage import run_triage
from app.auth import get_current_user
from app.db import get_db
from app.deps import get_ai_provider
from app.errors import ai_unavailable, conflict, not_found, validation_error
from app.models import (
    AiRun,
    Category,
    Comment,
    Incident,
    IncidentLink,
    IncidentStatus,
    KbArticle,
    KbSource,
    KbStatus,
    User,
)
from app.schemas import (
    AiRunOut,
    ApplyTriageRequest,
    CommentCreate,
    CommentOut,
    IncidentCreate,
    IncidentDetail,
    IncidentLinkOut,
    IncidentListItem,
    IncidentResolve,
    IncidentUpdate,
    LinkConfirmRequest,
    TriageProposal,
)
from app.services.correlation import detect_duplicates, detect_storm
from app.services.embeddings import embed_texts
from app.services.retrieval import retrieve

router = APIRouter(prefix="/api/incidents", tags=["incidents"])
links_router = APIRouter(prefix="/api/incident-links", tags=["incidents"])


async def _next_reference(db: AsyncSession) -> str:
    count = (await db.execute(select(Incident.id))).all()
    return f"INC-{len(count) + 1:04d}"


async def _get_incident_or_404(db: AsyncSession, incident_id: int) -> Incident:
    incident = await db.get(Incident, incident_id)
    if incident is None:
        raise not_found(f"Incident {incident_id} not found.")
    return incident


@router.get("", response_model=list[IncidentListItem])
async def list_incidents(
    status: IncidentStatus | None = None,
    priority: str | None = None,
    team: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Incident]:
    stmt = select(Incident)
    if status is not None:
        stmt = stmt.where(Incident.status == status)
    if priority is not None:
        stmt = stmt.where(Incident.priority == priority)
    if team is not None:
        stmt = stmt.where(Incident.assigned_team == team)
    if q:
        stmt = stmt.where(Incident.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    return (await db.scalars(stmt)).all()


@router.post("", response_model=IncidentDetail, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> Incident:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    existing = await db.scalar(
        select(Incident)
        .where(Incident.title == payload.title, Incident.description == payload.description, Incident.created_at >= cutoff)
        .order_by(Incident.created_at.desc())
    )
    if existing is not None:
        raise conflict(
            f"An identical incident was just submitted as {existing.reference}.",
            details={"existing_incident_id": existing.id, "existing_reference": existing.reference},
        )

    incident = Incident(
        reference=await _next_reference(db),
        title=payload.title,
        description=payload.description,
        reporter=payload.reporter,
        status=IncidentStatus.new,
    )
    db.add(incident)
    await db.flush()

    [embedding] = await embed_texts(db, provider, [f"{incident.title}\n{incident.description}"])
    incident.embedding = embedding
    await db.flush()

    await detect_duplicates(db, incident)
    await detect_storm(db, incident, provider)

    await db.commit()
    return await _build_detail(db, incident.id)


async def _build_detail(db: AsyncSession, incident_id: int) -> IncidentDetail:
    incident = await _get_incident_or_404(db, incident_id)
    # Two refreshes: server-generated columns (created_at/updated_at/search_tsv) are
    # only pulled back on an unqualified refresh; relationships need to be named
    # explicitly. Needed because expire_on_commit=False means a just-inserted row's
    # server defaults otherwise stay unpopulated on the in-memory object.
    await db.refresh(incident)
    await db.refresh(incident, attribute_names=["comments", "category", "assigned_agent"])

    links = (
        await db.scalars(
            select(IncidentLink).where(
                (IncidentLink.from_incident_id == incident_id) | (IncidentLink.to_incident_id == incident_id)
            )
        )
    ).all()

    runs = (
        await db.scalars(
            select(AiRun)
            .where(AiRun.entity_type == "incident", AiRun.entity_id == incident_id)
            .order_by(AiRun.created_at.desc())
            .limit(10)
        )
    ).all()

    detail = IncidentDetail.model_validate(incident)
    detail.links = [IncidentLinkOut.model_validate(link) for link in links]
    detail.ai_runs = [AiRunOut.model_validate(run) for run in runs]
    return detail


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> IncidentDetail:
    return await _build_detail(db, incident_id)


@router.patch("/{incident_id}", response_model=IncidentDetail)
async def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncidentDetail:
    incident = await _get_incident_or_404(db, incident_id)
    if payload.updated_at is not None and payload.updated_at < incident.updated_at:
        raise conflict(
            "This incident was updated by someone else since you loaded it.",
            details={"current_updated_at": incident.updated_at.isoformat()},
        )

    for field in ("status", "priority", "category_id", "assigned_team", "assigned_agent_id"):
        value = getattr(payload, field)
        if value is not None:
            setattr(incident, field, value)

    await db.commit()
    return await _build_detail(db, incident_id)


@router.post("/{incident_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(
    incident_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Comment:
    await _get_incident_or_404(db, incident_id)
    comment = Comment(incident_id=incident_id, author=payload.author, body=payload.body, is_internal=payload.is_internal)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.post("/{incident_id}/resolve", response_model=IncidentDetail)
async def resolve_incident(
    incident_id: int,
    payload: IncidentResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> IncidentDetail:
    incident = await _get_incident_or_404(db, incident_id)
    if payload.updated_at is not None and payload.updated_at < incident.updated_at:
        raise conflict(
            "This incident was updated by someone else since you loaded it.",
            details={"current_updated_at": incident.updated_at.isoformat()},
        )

    incident.resolution_note = payload.resolution_note
    incident.status = IncidentStatus.resolved
    incident.resolved_at = datetime.now(timezone.utc)
    incident.resolved_by_user_id = current_user.id
    await db.flush()

    if provider is not None:
        comments = (await db.execute(select(Comment).where(Comment.incident_id == incident_id))).scalars().all()
        retrieval = await retrieve(
            db,
            query_text=f"{incident.title} {incident.description}",
            query_embedding=incident.embedding,
            exclude_incident_id=incident.id,
            top_k=3,
        )
        draft = await run_synthesis(db, incident, list(comments), provider, retrieval.hits)
        if draft.action != "skip":
            [article_embedding] = await embed_texts(
                db, provider, [f"{draft.title}\n{draft.symptom}\n{draft.cause}\n{' '.join(draft.resolution_steps)}"]
            )
            count = (await db.execute(select(KbArticle.id))).all()
            article = KbArticle(
                reference=f"KB-{len(count) + 1:03d}",
                title=draft.title,
                symptom=draft.symptom,
                cause=draft.cause,
                resolution_steps="\n".join(f"{i + 1}. {s}" for i, s in enumerate(draft.resolution_steps)),
                verification=draft.verification,
                tags=draft.tags,
                status=KbStatus.draft,
                source_incident_id=incident.id,
                created_by=KbSource.ai,
                embedding=article_embedding,
            )
            db.add(article)

    await db.commit()
    return await _build_detail(db, incident_id)


@router.post("/{incident_id}/triage", response_model=TriageProposal)
async def triage_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> TriageProposal:
    if provider is None:
        raise ai_unavailable()
    incident = await _get_incident_or_404(db, incident_id)
    return await run_triage(db, incident, provider)


@router.post("/{incident_id}/apply-triage", response_model=IncidentDetail)
async def apply_triage(
    incident_id: int,
    payload: ApplyTriageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncidentDetail:
    incident = await _get_incident_or_404(db, incident_id)
    category = await db.scalar(select(Category).where(Category.name == payload.category))
    if category is None:
        raise validation_error(f"Unknown category '{payload.category}'.")

    incident.category_id = category.id
    incident.impact = payload.impact
    incident.urgency = payload.urgency
    incident.assigned_team = payload.suggested_team
    incident.priority = payload.priority
    incident.status = IncidentStatus.triaged
    await db.commit()
    return await _build_detail(db, incident_id)


@router.get("/{incident_id}/ground")
async def ground(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> EventSourceResponse:
    incident = await _get_incident_or_404(db, incident_id)
    # Resolved (or raised as a clean AI_UNAVAILABLE/RATE_LIMITED error) before the SSE
    # stream opens, so errors reach the client as a normal JSON error response rather
    # than breaking a stream that already started with a 200.
    answer, retrieval = await ground_incident(db, incident, provider)

    async def event_stream():
        yield {"event": "status", "data": json.dumps({"phase": "generating"})}

        words = answer.diagnosis.split(" ")
        buffer = ""
        for word in words:
            buffer += word + " "
            yield {"event": "token", "data": json.dumps({"text": word + " "})}
            await asyncio.sleep(0.01)

        payload = {
            "answer": answer.model_dump(),
            "sources": [
                {
                    "id": h.id,
                    "reference": h.reference,
                    "kind": h.kind,
                    "title": h.title,
                    "fused_score": h.fused_score,
                    "vector_rank": h.vector_rank,
                    "lexical_rank": h.lexical_rank,
                }
                for h in retrieval.hits
            ],
            "degraded": retrieval.degraded,
        }
        yield {"event": "result", "data": json.dumps(payload)}

    return EventSourceResponse(event_stream())


@router.get("/{incident_id}/similar", response_model=list[IncidentLinkOut])
async def similar_incidents(
    incident_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[IncidentLink]:
    await _get_incident_or_404(db, incident_id)
    result = await db.execute(
        select(IncidentLink).where(
            (IncidentLink.from_incident_id == incident_id) | (IncidentLink.to_incident_id == incident_id)
        )
    )
    return result.scalars().all()


@links_router.post("/{link_id}/confirm", response_model=IncidentLinkOut)
async def confirm_link(
    link_id: int,
    payload: LinkConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncidentLink:
    link = await db.get(IncidentLink, link_id)
    if link is None:
        raise not_found(f"Link {link_id} not found.")
    if payload.confirmed:
        link.confirmed = True
        await db.commit()
    else:
        await db.delete(link)
        await db.commit()
    return link
