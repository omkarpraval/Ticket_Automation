"""Embedding batching, content-hash cache and backoff. The actual HTTP retry/backoff
with jitter lives in app.ai.gemini (tenacity, max 5 attempts) - this module owns
batching (50 texts/call), the embedding_cache lookup, and the concurrency cap.
"""

import asyncio
import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider, ProviderRateLimited, ProviderUnavailable
from app.config import settings
from app.models import EmbeddingCache

logger = logging.getLogger("helix.embeddings")

BATCH_SIZE = 50
_CONCURRENCY = asyncio.Semaphore(2)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def embed_texts(db: AsyncSession, provider: AIProvider | None, texts: list[str]) -> list[list[float] | None]:
    """Returns one embedding per input text, or None per text if embeddings are
    unavailable (no API key) or the call ultimately failed after retries."""
    if provider is None or not settings.ai_enabled:
        logger.warning("GEMINI_API_KEY not set - skipping embeddings for %d text(s)", len(texts))
        return [None] * len(texts)

    hashes = [content_hash(t) for t in texts]
    cached: dict[str, list[float]] = {}
    if hashes:
        rows = await db.scalars(select(EmbeddingCache).where(EmbeddingCache.content_hash.in_(hashes)))
        cached = {row.content_hash: list(row.embedding) for row in rows}

    results: list[list[float] | None] = [None] * len(texts)
    to_fetch = [i for i, h in enumerate(hashes) if h not in cached]
    for i, h in enumerate(hashes):
        if h in cached:
            results[i] = cached[h]

    chunks = [to_fetch[i : i + BATCH_SIZE] for i in range(0, len(to_fetch), BATCH_SIZE)]

    async def fetch(idx_chunk: list[int]) -> tuple[list[int], list[list[float] | None]]:
        async with _CONCURRENCY:
            try:
                return idx_chunk, await provider.embed([texts[i] for i in idx_chunk])
            except (ProviderRateLimited, ProviderUnavailable) as exc:
                logger.warning("Embedding batch of %d failed after retries: %s", len(idx_chunk), exc)
                return idx_chunk, [None] * len(idx_chunk)

    for idx_chunk, embeds in await asyncio.gather(*[fetch(c) for c in chunks]):
        for i, emb in zip(idx_chunk, embeds):
            results[i] = emb
            if emb is not None:
                stmt = pg_insert(EmbeddingCache).values(content_hash=hashes[i], embedding=emb)
                stmt = stmt.on_conflict_do_nothing(index_elements=["content_hash"])
                await db.execute(stmt)

    if to_fetch:
        await db.flush()
    return results
