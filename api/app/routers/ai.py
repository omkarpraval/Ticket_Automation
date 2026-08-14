from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import AiRun, AiStage, Incident, IncidentStatus, KbArticle, KbStatus, Priority, User
from app.schemas import AiRunOut, StatsOut

router = APIRouter(prefix="/api", tags=["ai"])


@router.get("/ai-runs", response_model=list[AiRunOut])
async def list_ai_runs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AiRun]:
    stmt = select(AiRun).order_by(AiRun.created_at.desc()).limit(100)
    if entity_type is not None:
        stmt = stmt.where(AiRun.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AiRun.entity_id == entity_id)
    return (await db.scalars(stmt)).all()


@router.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> StatsOut:
    open_incidents = await db.scalar(
        select(func.count()).select_from(Incident).where(Incident.status.in_([IncidentStatus.new, IncidentStatus.triaged, IncidentStatus.in_progress]))
    )
    p1_incidents = await db.scalar(select(func.count()).select_from(Incident).where(Incident.priority == Priority.P1))
    kb_published = await db.scalar(select(func.count()).select_from(KbArticle).where(KbArticle.status == KbStatus.published))
    kb_draft = await db.scalar(select(func.count()).select_from(KbArticle).where(KbArticle.status == KbStatus.draft))

    total_incidents = await db.scalar(select(func.count()).select_from(Incident))
    resolved_incidents = await db.scalar(
        select(func.count()).select_from(Incident).where(Incident.status.in_([IncidentStatus.resolved, IncidentStatus.closed]))
    )
    resolution_rate = (resolved_incidents / total_incidents) if total_incidents else 0.0

    ground_runs = await db.scalar(select(func.count()).select_from(AiRun).where(AiRun.stage == AiStage.ground))
    abstain_runs = await db.scalar(
        select(func.count()).select_from(AiRun).where(AiRun.stage == AiStage.ground, AiRun.raw_output.ilike("abstained%"))
    )
    abstain_rate = (abstain_runs / ground_runs) if ground_runs else 0.0

    return StatsOut(
        open_incidents=open_incidents or 0,
        p1_incidents=p1_incidents or 0,
        kb_published=kb_published or 0,
        kb_draft=kb_draft or 0,
        resolution_rate=round(resolution_rate, 3),
        abstain_rate=round(abstain_rate, 3),
        ai_enabled=settings.ai_enabled,
    )
