"""Gemini implementation of AIProvider. This is the only module allowed to import
the google-genai SDK — everything else in the app talks to app.ai.provider.AIProvider.
"""

import time

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.ai.provider import ProviderRateLimited, ProviderResult, ProviderUnavailable
from app.config import settings


def _classify(exc: Exception) -> Exception:
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    message = str(exc)
    if status == 429 or "RESOURCE_EXHAUSTED" in message or "429" in message:
        return ProviderRateLimited(message)
    return ProviderUnavailable(message)


class GeminiProvider:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    @retry(
        retry=retry_if_exception_type(ProviderRateLimited),
        wait=wait_random_exponential(multiplier=1, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete_json(self, *, prompt: str, schema: dict, temperature: float) -> ProviderResult:
        start = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(
                model=settings.gemini_chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed provider error below
            raise _classify(exc) from exc
        return self._to_result(response, start)

    @retry(
        retry=retry_if_exception_type(ProviderRateLimited),
        wait=wait_random_exponential(multiplier=1, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete_text(self, *, prompt: str, temperature: float) -> ProviderResult:
        start = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(
                model=settings.gemini_chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature),
            )
        except Exception as exc:  # noqa: BLE001
            raise _classify(exc) from exc
        return self._to_result(response, start)

    @retry(
        retry=retry_if_exception_type(ProviderRateLimited),
        wait=wait_random_exponential(multiplier=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def embed(self, texts: list[str]) -> list[list[float] | None]:
        try:
            response = await self._client.aio.models.embed_content(
                model=settings.gemini_embed_model,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim),
            )
        except Exception as exc:  # noqa: BLE001
            raise _classify(exc) from exc
        return [list(e.values) if e.values else None for e in response.embeddings]

    def _to_result(self, response, start: float) -> ProviderResult:
        latency_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage_metadata
        return ProviderResult(
            text=response.text or "",
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            latency_ms=latency_ms,
            model=settings.gemini_chat_model,
        )
