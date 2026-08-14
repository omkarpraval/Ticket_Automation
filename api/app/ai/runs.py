from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import PROMPT_VERSION
from app.config import settings
from app.models import AiRun, AiStage


async def log_run(
    db: AsyncSession,
    *,
    stage: AiStage,
    entity_type: str,
    entity_id: int | None,
    input_summary: str,
    parsed_ok: bool,
    model: str | None = None,
    retrieved_ids: list[str] | None = None,
    raw_output: str | None = None,
    retry_count: int = 0,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    error: str | None = None,
) -> AiRun:
    """Write one ai_runs row. Called for every AI call, including failures - this is
    the audit trail the "Why this?" drawer reads from, so it is not optional."""
    run = AiRun(
        stage=stage,
        entity_type=entity_type,
        entity_id=entity_id,
        model=model or settings.gemini_chat_model,
        prompt_version=PROMPT_VERSION,
        input_summary=input_summary[:2000],
        retrieved_ids=retrieved_ids or [],
        raw_output=(raw_output or "")[:8000],
        parsed_ok=parsed_ok,
        retry_count=retry_count,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        error=error,
    )
    db.add(run)
    await db.flush()
    return run
