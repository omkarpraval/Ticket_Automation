"""Stage three: knowledge synthesis. Triggered when an incident is resolved with a
resolution note. Drafts a KB article from the incident, its comments and the
resolution note - or proposes "skip" for one-off issues with no reusable lesson.
The result is always saved as a draft; nothing here ever publishes automatically.
"""

import json

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider, ProviderRateLimited, ProviderUnavailable
from app.ai.prompts import SYNTHESIS_SCHEMA, synthesis_prompt
from app.ai.runs import log_run
from app.errors import ai_invalid_output, rate_limited
from app.models import AiStage, Comment, Incident
from app.schemas import SynthesisDraft
from app.services.retrieval import RetrievalHit


class _SynthesisModelOutput(BaseModel):
    action: str
    target_article_reference: str | None = None
    title: str
    symptom: str
    cause: str
    resolution_steps: list[str]
    verification: str
    tags: list[str]
    reasoning: str


async def run_synthesis(
    db: AsyncSession,
    incident: Incident,
    comments: list[Comment],
    provider: AIProvider,
    related: list[RetrievalHit],
) -> SynthesisDraft:
    comments_block = "\n".join(f"[{c.author}] {c.body}" for c in comments) or "(no comments)"
    related_block = "\n\n".join(f"[{h.reference}] {h.title}\n{h.content}" for h in related) or "(none found)"
    prompt = synthesis_prompt(
        incident_title=incident.title,
        incident_description=incident.description[:10_000],
        resolution_note=incident.resolution_note or "",
        comments_block=comments_block,
        related_block=related_block,
    )

    last_error = ""
    last_raw = ""
    for attempt in range(2):
        current_prompt = prompt if attempt == 0 else f"{prompt}\n\nYour previous response was invalid: {last_error}\nRespond again with valid JSON only."
        try:
            result = await provider.complete_json(prompt=current_prompt, schema=SYNTHESIS_SCHEMA, temperature=0.3)
        except ProviderRateLimited as exc:
            raise rate_limited() from exc
        except ProviderUnavailable as exc:
            await log_run(
                db,
                stage=AiStage.synthesize,
                entity_type="incident",
                entity_id=incident.id,
                input_summary=f"{incident.reference}: {incident.title}",
                parsed_ok=False,
                retry_count=attempt,
                error=str(exc),
            )
            await db.commit()
            raise ai_invalid_output(f"The AI provider is unavailable right now ({exc}).")

        last_raw = result.text
        try:
            data = json.loads(result.text)
            parsed = _SynthesisModelOutput.model_validate(data)
            if parsed.action not in ("create", "update", "skip"):
                raise ValueError("action must be create, update or skip")
            await log_run(
                db,
                stage=AiStage.synthesize,
                entity_type="incident",
                entity_id=incident.id,
                input_summary=f"{incident.reference}: {incident.title}",
                parsed_ok=True,
                model=result.model,
                retrieved_ids=[h.reference for h in related],
                raw_output=result.text,
                retry_count=attempt,
                latency_ms=result.latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            await db.commit()
            return SynthesisDraft(**parsed.model_dump())
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = str(exc)
            continue

    await log_run(
        db,
        stage=AiStage.synthesize,
        entity_type="incident",
        entity_id=incident.id,
        input_summary=f"{incident.reference}: {incident.title}",
        parsed_ok=False,
        raw_output=last_raw,
        retry_count=1,
        error=last_error,
    )
    await db.commit()
    raise ai_invalid_output("The AI returned output that didn't match the expected synthesis schema after a retry.")
