import asyncio
import sys
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# psycopg's async mode requires a selector-based event loop; Windows defaults to
# ProactorEventLoop, which it explicitly does not support. This only matters for
# native (non-Docker) Windows dev - the Linux container never hits this branch.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Base(DeclarativeBase):
    pass


# psycopg3 supports both sync and async connections under the same
# "postgresql+psycopg" URL scheme; create_async_engine selects the async path.
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
