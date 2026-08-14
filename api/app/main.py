from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.errors import register_exception_handlers
from app.routers import ai, auth, incidents, kb, problems

app = FastAPI(title="Helix", version="0.1.0")

app.add_middleware(
    # Auth is a Bearer token in the Authorization header, not a cookie, so
    # allow_credentials is unnecessary here - a wildcard origin is enough.
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(incidents.router)
app.include_router(incidents.links_router)
app.include_router(kb.router)
app.include_router(problems.router)
app.include_router(ai.router)


@app.get("/health")
async def health() -> dict:
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "ai_enabled": settings.ai_enabled,
    }
