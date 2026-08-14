from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Incident, Problem, User
from app.schemas import IncidentListItem, ProblemOut

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=list[ProblemOut])
async def list_problems(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ProblemOut]:
    problems = (await db.scalars(select(Problem).order_by(Problem.detected_at.desc()))).all()
    result = []
    for problem in problems:
        incidents = (await db.scalars(select(Incident).where(Incident.problem_id == problem.id))).all()
        out = ProblemOut.model_validate(problem)
        out.incidents = [IncidentListItem.model_validate(i) for i in incidents]
        result.append(out)
    return result
