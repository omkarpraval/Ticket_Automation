from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import AIProvider
from app.auth import get_current_user
from app.db import get_db
from app.deps import get_ai_provider
from app.errors import not_found, validation_error
from app.models import KbArticle, KbStatus, User
from app.schemas import KbArticleOut, KbArticleUpdate
from app.services.embeddings import embed_texts

router = APIRouter(prefix="/api/kb", tags=["kb"])


async def _get_article_or_404(db: AsyncSession, article_id: int) -> KbArticle:
    article = await db.get(KbArticle, article_id)
    if article is None:
        raise not_found(f"KB article {article_id} not found.")
    return article


@router.get("", response_model=list[KbArticleOut])
async def list_articles(
    status: KbStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[KbArticle]:
    stmt = select(KbArticle).order_by(KbArticle.created_at.desc())
    if status is not None:
        stmt = stmt.where(KbArticle.status == status)
    return (await db.scalars(stmt)).all()


@router.get("/{article_id}", response_model=KbArticleOut)
async def get_article(
    article_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> KbArticle:
    return await _get_article_or_404(db, article_id)


@router.patch("/{article_id}", response_model=KbArticleOut)
async def update_article(
    article_id: int,
    payload: KbArticleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KbArticle:
    article = await _get_article_or_404(db, article_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(article, field, value)
    await db.commit()
    await db.refresh(article)
    return article


@router.post("/{article_id}/publish", response_model=KbArticleOut)
async def publish_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> KbArticle:
    article = await _get_article_or_404(db, article_id)
    if article.status == KbStatus.published:
        raise validation_error("This article is already published.")

    [embedding] = await embed_texts(
        db, provider, [f"{article.title}\n{article.symptom}\n{article.cause}\n{article.resolution_steps}"]
    )
    article.embedding = embedding
    article.status = KbStatus.published
    article.approved_by_user_id = current_user.id
    await db.commit()
    await db.refresh(article)
    return article


@router.post("/{article_id}/reject", response_model=KbArticleOut)
async def reject_article(
    article_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> KbArticle:
    article = await _get_article_or_404(db, article_id)
    article.status = KbStatus.rejected
    await db.commit()
    await db.refresh(article)
    return article
