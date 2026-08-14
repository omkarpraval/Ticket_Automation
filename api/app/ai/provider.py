"""AIProvider protocol. Nothing outside app/ai/ may import the Gemini SDK directly —
routers and services depend on this Protocol so the provider can be swapped
(e.g. for a test double) without touching call sites.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ProviderResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model: str
    error: str | None = field(default=None)


class AIProvider(Protocol):
    async def complete_json(self, *, prompt: str, schema: dict, temperature: float) -> ProviderResult: ...

    async def complete_text(self, *, prompt: str, temperature: float) -> ProviderResult: ...

    async def embed(self, texts: list[str]) -> list[list[float] | None]: ...


class ProviderRateLimited(Exception):
    """Raised when the provider returns 429. Callers map this to the RATE_LIMITED error code."""


class ProviderUnavailable(Exception):
    """Raised for non-recoverable provider errors (5xx after retries, network failure, etc)."""
