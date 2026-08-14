"""Shared FastAPI dependencies that don't belong to a single router."""

from functools import lru_cache

from app.ai.provider import AIProvider
from app.config import settings


@lru_cache
def _gemini_singleton() -> AIProvider:
    from app.ai.gemini import GeminiProvider

    return GeminiProvider()


def get_ai_provider() -> AIProvider | None:
    """Returns None when GEMINI_API_KEY is unset - callers must degrade gracefully
    rather than crash, per the "never crash on a missing key" requirement."""
    if not settings.ai_enabled:
        return None
    return _gemini_singleton()
