"""Stage one: triage. The model reads the ticket and proposes a classification;
priority itself is computed in Python from impact/urgency (see compute_priority),
never generated, so it stays reproducible and auditable. Triage never writes to the
incident directly - it returns a proposal that a human must accept via /apply-triage.
"""

import json

from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider, ProviderRateLimited, ProviderUnavailable
from app.ai.prompts import TRIAGE_SCHEMA, triage_prompt
from app.ai.runs import log_run
from app.errors import ai_invalid_output, rate_limited
from app.models import Agent, AiStage, Category, Incident, Priority
from app.schemas import TriageEntities, TriageProposal, TriageRationale

# impact/urgency -> priority, per the brief's fixed matrix. Deliberately not a formula:
# the mapping is a policy decision (e.g. why 2,2 outranks 3,1) and reads clearer as a table.
_PRIORITY_MATRIX: dict[tuple[int, int], Priority] = {
    (1, 1): Priority.P1, (1, 2): Priority.P1, (1, 3): Priority.P2, (1, 4): Priority.P2,
    (2, 1): Priority.P1, (2, 2): Priority.P2, (2, 3): Priority.P2, (2, 4): Priority.P3,
    (3, 1): Priority.P2, (3, 2): Priority.P3, (3, 3): Priority.P3, (3, 4): Priority.P4,
    (4, 1): Priority.P3, (4, 2): Priority.P3, (4, 3): Priority.P4, (4, 4): Priority.P4,
}


def compute_priority(impact: int, urgency: int) -> Priority:
    return _PRIORITY_MATRIX[(impact, urgency)]


class _TriageModelOutput(BaseModel):
    category: str
    affected_system: str
    impact: int
    urgency: int
    suggested_team: str
    entities: TriageEntities
    summary: str
    rationale: TriageRationale

    @field_validator("impact", "urgency")
    @classmethod
    def _in_range(cls, v: int) -> int:
        if not 1 <= v <= 4:
            raise ValueError("must be between 1 and 4")
        return v


async def run_triage(db: AsyncSession, incident: Incident, provider: AIProvider) -> TriageProposal:
    categories = [c.name for c in (await db.scalars(select(Category))).all()]
    teams = sorted({t for (t,) in (await db.execute(select(Agent.team).distinct())).all() if t})

    prompt = triage_prompt(
        title=incident.title, description=incident.description[:10_000], categories=categories, teams=teams
    )

    parsed, retry_count, run_kwargs = await _complete_with_retry(
        provider=provider, prompt=prompt, schema=TRIAGE_SCHEMA, categories=categories, teams=teams
    )

    if parsed is None:
        await log_run(
            db,
            stage=AiStage.triage,
            entity_type="incident",
            entity_id=incident.id,
            input_summary=f"{incident.reference}: {incident.title}",
            parsed_ok=False,
            retry_count=retry_count,
            **run_kwargs,
        )
        await db.commit()
        raise ai_invalid_output(
            "The AI returned output that didn't match the expected triage schema after a retry.",
            details={"incident": incident.reference},
        )

    await log_run(
        db,
        stage=AiStage.triage,
        entity_type="incident",
        entity_id=incident.id,
        input_summary=f"{incident.reference}: {incident.title}",
        parsed_ok=True,
        retry_count=retry_count,
        **run_kwargs,
    )
    await db.commit()

    priority = compute_priority(parsed.impact, parsed.urgency)
    return TriageProposal(
        category=parsed.category,
        affected_system=parsed.affected_system,
        impact=parsed.impact,
        urgency=parsed.urgency,
        suggested_team=parsed.suggested_team,
        entities=parsed.entities,
        summary=parsed.summary,
        rationale=parsed.rationale,
        priority=priority,
    )


async def _complete_with_retry(
    *, provider: AIProvider, prompt: str, schema: dict, categories: list[str], teams: list[str]
) -> tuple[_TriageModelOutput | None, int, dict]:
    last_raw = ""
    last_error = ""
    for attempt in range(2):
        current_prompt = prompt if attempt == 0 else f"{prompt}\n\nYour previous response was invalid: {last_error}\nFix it and respond again with valid JSON only."
        try:
            result = await provider.complete_json(prompt=current_prompt, schema=schema, temperature=0.1)
        except ProviderRateLimited as exc:
            raise rate_limited() from exc
        except ProviderUnavailable as exc:
            return None, attempt, {
                "model": None,
                "raw_output": str(exc),
                "latency_ms": None,
                "input_tokens": None,
                "output_tokens": None,
                "error": str(exc),
            }

        last_raw = result.text
        try:
            data = json.loads(result.text)
            parsed = _TriageModelOutput.model_validate(data)
            if parsed.category not in categories:
                raise ValueError(f"category '{parsed.category}' is not one of the known categories")
            if parsed.suggested_team not in teams:
                raise ValueError(f"suggested_team '{parsed.suggested_team}' is not one of the known teams")
            return parsed, attempt, {
                "model": result.model,
                "raw_output": result.text,
                "latency_ms": result.latency_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "error": None,
            }
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            continue

    return None, 1, {
        "model": None,
        "raw_output": last_raw,
        "latency_ms": None,
        "input_tokens": None,
        "output_tokens": None,
        "error": last_error,
    }
