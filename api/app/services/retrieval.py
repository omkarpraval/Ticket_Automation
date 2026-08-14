"""Hybrid retrieval: a vector list and a lexical list over published KB articles and
resolved incidents, fused with Reciprocal Rank Fusion (RRF).

RRF is chosen over normalizing and averaging the two raw scores because cosine
distance and ts_rank_cd live on incomparable scales - RRF only needs each list's
*rank*, not its score, so there is nothing to normalize and nothing to get wrong.
Vector search alone misses exact error codes/hostnames it hasn't seen phrased that
way; lexical search alone misses paraphrases. Fusing both catches more than either.
"""

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

_RRF_K = 60
_CANDIDATE_LIMIT = 20

_VECTOR_SQL = text(
    """
    SELECT 'KB' AS kind, id, reference, title, embedding <=> (:qe)::vector AS distance
    FROM kb_articles
    WHERE status = 'published' AND embedding IS NOT NULL
    UNION ALL
    SELECT 'INC' AS kind, id, reference, title, embedding <=> (:qe)::vector AS distance
    FROM incidents
    WHERE status = 'resolved' AND embedding IS NOT NULL AND id != :exclude_id
    ORDER BY distance ASC
    LIMIT :limit
    """
)

_TERMS_SQL = text("SELECT DISTINCT lexeme FROM unnest(to_tsvector('english', :q)) AS u(lexeme, positions, weights)")

_LEXICAL_SQL = text(
    """
    SELECT 'KB' AS kind, id, reference, title,
           ts_rank_cd(search_tsv, to_tsquery('english', :tsq)) AS score
    FROM kb_articles
    WHERE status = 'published' AND search_tsv @@ to_tsquery('english', :tsq)
    UNION ALL
    SELECT 'INC' AS kind, id, reference, title,
           ts_rank_cd(search_tsv, to_tsquery('english', :tsq)) AS score
    FROM incidents
    WHERE status = 'resolved' AND search_tsv @@ to_tsquery('english', :tsq) AND id != :exclude_id
    ORDER BY score DESC
    LIMIT :limit
    """
)

_KB_CONTENT_SQL = text(
    "SELECT id, reference, title, symptom, cause, resolution_steps, verification FROM kb_articles WHERE id = ANY(:ids)"
)
_INC_CONTENT_SQL = text(
    "SELECT id, reference, title, description, resolution_note FROM incidents WHERE id = ANY(:ids)"
)


@dataclass
class RetrievalHit:
    id: int
    reference: str
    kind: str  # "KB" | "INC"
    title: str
    content: str
    fused_score: float
    vector_rank: int | None = None
    lexical_rank: int | None = None


@dataclass
class RetrievalResult:
    hits: list[RetrievalHit] = field(default_factory=list)
    degraded: bool = False
    best_score: float = 0.0


def _rrf_fuse(vector_refs: list[str], lexical_refs: list[str]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for rank, ref in enumerate(vector_refs, start=1):
        scores[ref] = scores.get(ref, 0.0) + 1 / (_RRF_K + rank)
    for rank, ref in enumerate(lexical_refs, start=1):
        scores[ref] = scores.get(ref, 0.0) + 1 / (_RRF_K + rank)
    return scores


async def retrieve(
    db: AsyncSession,
    *,
    query_text: str,
    query_embedding: list[float] | None,
    exclude_incident_id: int = -1,
    top_k: int | None = None,
) -> RetrievalResult:
    top_k = top_k or settings.retrieval_top_k
    degraded = query_embedding is None

    # websearch_to_tsquery ANDs every term together, which is right for a short user
    # search box but wrong here: the "query" is a whole incident title+description,
    # and requiring every one of its words to appear in a short KB article would
    # almost never match. Instead we tokenize the incident text with the same
    # 'english' config used for search_tsv and OR the resulting lexemes together, so
    # ts_rank_cd can do its job of ranking by how much of the query a document covers.
    terms = [row.lexeme for row in (await db.execute(_TERMS_SQL, {"q": query_text})).all()]
    lexical_refs: list[str] = []
    lexical_rows = []
    if terms:
        tsquery = " | ".join(terms)
        lexical_rows = (
            await db.execute(
                _LEXICAL_SQL, {"tsq": tsquery, "exclude_id": exclude_incident_id, "limit": _CANDIDATE_LIMIT}
            )
        ).all()
        lexical_refs = [row.reference for row in lexical_rows]

    vector_rows = []
    if not degraded:
        vector_rows = (
            await db.execute(
                _VECTOR_SQL, {"qe": str(query_embedding), "exclude_id": exclude_incident_id, "limit": _CANDIDATE_LIMIT}
            )
        ).all()
    vector_refs = [row.reference for row in vector_rows]

    fused = _rrf_fuse(vector_refs, lexical_refs)
    if not fused:
        return RetrievalResult(hits=[], degraded=degraded, best_score=0.0)

    ranked_refs = sorted(fused, key=lambda r: fused[r], reverse=True)[:top_k]
    by_ref = {row.reference: row for row in [*vector_rows, *lexical_rows]}

    kb_ids = [by_ref[r].id for r in ranked_refs if by_ref[r].kind == "KB"]
    inc_ids = [by_ref[r].id for r in ranked_refs if by_ref[r].kind == "INC"]

    kb_content = {row.reference: row for row in (await db.execute(_KB_CONTENT_SQL, {"ids": kb_ids})).all()} if kb_ids else {}
    inc_content = {row.reference: row for row in (await db.execute(_INC_CONTENT_SQL, {"ids": inc_ids})).all()} if inc_ids else {}

    hits = []
    for ref in ranked_refs:
        meta = by_ref[ref]
        if meta.kind == "KB":
            row = kb_content[ref]
            content = f"Symptom: {row.symptom}\nCause: {row.cause}\nResolution: {row.resolution_steps}\nVerification: {row.verification}"
        else:
            row = inc_content[ref]
            content = f"Description: {row.description}\nResolution: {row.resolution_note or 'n/a'}"
        hits.append(
            RetrievalHit(
                id=meta.id,
                reference=ref,
                kind=meta.kind,
                title=meta.title,
                content=content,
                fused_score=fused[ref],
                vector_rank=(vector_refs.index(ref) + 1) if ref in vector_refs else None,
                lexical_rank=(lexical_refs.index(ref) + 1) if ref in lexical_refs else None,
            )
        )

    best_score = max(fused.values())
    return RetrievalResult(hits=hits, degraded=degraded, best_score=best_score)
