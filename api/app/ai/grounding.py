"""Stage two: grounded answer. Retrieves context, then asks the model to answer
*only* from that context. The abstain path is the most important behaviour in this
app: if the best fused retrieval score is below GROUNDING_MIN_SCORE we never call
the model at all - we return the abstain response directly. That makes the guardrail
free to test (no API key needed) and saves a call on every hopeless query.
"""

import json

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider, ProviderRateLimited, ProviderUnavailable
from app.ai.prompts import GROUNDING_SCHEMA, grounding_prompt
from app.ai.runs import log_run
from app.config import settings
from app.errors import ai_unavailable, rate_limited
from app.models import AiStage, Incident
from app.schemas import GroundedAnswer
from app.services.embeddings import embed_texts
from app.services.retrieval import RetrievalResult, retrieve


class _GroundingModelOutput(BaseModel):
    has_sufficient_evidence: bool
    diagnosis: str
    recommended_steps: list[str]
    citations: list[str]
    confidence_reason: str
    escalate_to: str | None = None


def _abstain(reason: str, escalate_to: str | None, degraded: bool) -> GroundedAnswer:
    return GroundedAnswer(
        has_sufficient_evidence=False,
        diagnosis="Not enough evidence to answer safely.",
        recommended_steps=[],
        citations=[],
        confidence_reason=reason,
        escalate_to=escalate_to,
        degraded=degraded,
    )


async def ground_incident(
    db: AsyncSession, incident: Incident, provider: AIProvider | None
) -> tuple[GroundedAnswer, RetrievalResult]:
    embedding = None
    if provider is not None and settings.ai_enabled:
        [embedding] = await embed_texts(db, provider, [f"{incident.title}\n{incident.description}"])

    retrieval = await retrieve(
        db,
        query_text=f"{incident.title} {incident.description}",
        query_embedding=embedding,
        exclude_incident_id=incident.id,
    )

    escalate_to = incident.assigned_team or "the service desk"

    if retrieval.best_score < settings.grounding_min_score or not retrieval.hits:
        answer = _abstain(
            f"Best retrieval match scored {retrieval.best_score:.4f}, below the "
            f"{settings.grounding_min_score} grounding threshold - no model call was made.",
            escalate_to,
            retrieval.degraded,
        )
        await log_run(
            db,
            stage=AiStage.ground,
            entity_type="incident",
            entity_id=incident.id,
            input_summary=f"{incident.reference}: {incident.title}",
            parsed_ok=True,
            model="none (short-circuited)",
            retrieved_ids=[h.reference for h in retrieval.hits],
            raw_output="abstained: best_score below threshold",
        )
        await db.commit()
        return answer, retrieval

    # Past this point there IS enough evidence to answer - the only reason we can't
    # is a missing key, which is a real AI_UNAVAILABLE error, not a manufactured
    # abstain. (The threshold short-circuit above deliberately runs before this
    # check, so the abstain guardrail itself is testable with no API key at all.)
    if provider is None or not settings.ai_enabled:
        raise ai_unavailable()

    context_refs = {h.reference for h in retrieval.hits}
    context_block = "\n\n".join(f"[{h.reference}] {h.title}\n{h.content}" for h in retrieval.hits)
    prompt = grounding_prompt(
        incident_title=incident.title, incident_description=incident.description[:10_000], context_block=context_block
    )

    try:
        result = await provider.complete_json(prompt=prompt, schema=GROUNDING_SCHEMA, temperature=0.2)
    except ProviderRateLimited as exc:
        raise rate_limited() from exc
    except ProviderUnavailable as exc:
        answer = _abstain(f"The AI provider is unavailable right now ({exc}).", escalate_to, retrieval.degraded)
        await log_run(
            db,
            stage=AiStage.ground,
            entity_type="incident",
            entity_id=incident.id,
            input_summary=f"{incident.reference}: {incident.title}",
            parsed_ok=False,
            retrieved_ids=list(context_refs),
            error=str(exc),
        )
        await db.commit()
        return answer, retrieval

    hallucinated: list[str] = []
    try:
        data = json.loads(result.text)
        parsed = _GroundingModelOutput.model_validate(data)
        valid_citations = [c for c in parsed.citations if c in context_refs]
        hallucinated = [c for c in parsed.citations if c not in context_refs]
        answer = GroundedAnswer(
            has_sufficient_evidence=parsed.has_sufficient_evidence and bool(valid_citations),
            diagnosis=parsed.diagnosis,
            recommended_steps=parsed.recommended_steps,
            citations=valid_citations,
            confidence_reason=parsed.confidence_reason,
            escalate_to=parsed.escalate_to or escalate_to,
            degraded=retrieval.degraded,
        )
        if not answer.has_sufficient_evidence:
            answer = _abstain(parsed.confidence_reason or "The model could not ground an answer.", escalate_to, retrieval.degraded)
        parsed_ok = True
    except (json.JSONDecodeError, ValidationError) as exc:
        answer = _abstain(f"The AI returned an invalid response ({exc}).", escalate_to, retrieval.degraded)
        parsed_ok = False

    await log_run(
        db,
        stage=AiStage.ground,
        entity_type="incident",
        entity_id=incident.id,
        input_summary=f"{incident.reference}: {incident.title}",
        parsed_ok=parsed_ok,
        model=result.model,
        retrieved_ids=list(context_refs),
        raw_output=result.text + (f"\n\nHALLUCINATED CITATIONS STRIPPED: {hallucinated}" if hallucinated else ""),
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        error=f"hallucinated citations stripped: {hallucinated}" if hallucinated else None,
    )
    await db.commit()
    return answer, retrieval
