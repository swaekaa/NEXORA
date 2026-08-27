"""
NEXORA Backend — Database Connection

Provides:
  - Async SQLAlchemy engine (asyncpg driver)
  - Async session factory
  - `get_db` dependency for FastAPI route injection
  - `check_db_connectivity` helper for health checks

Usage in routes:
    from app.database.connection import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(SomeModel))
        ...
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────

def _build_engine() -> AsyncEngine:
    """
    Build the SQLAlchemy async engine.
    Called once at module import — the engine is a singleton.
    """
    from sqlalchemy.pool import NullPool
    
    if settings.ENVIRONMENT == "test":
        return create_async_engine(
            settings.DATABASE_URL,
            poolclass=NullPool,
            echo=settings.DB_ECHO,
        )
    
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        echo=settings.DB_ECHO,
        pool_pre_ping=True,
    )


engine: AsyncEngine = _build_engine()

# ── Session Factory ────────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoids lazy-load errors after commit
    autoflush=False,
)


# ── FastAPI Dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async DB session per request.
    Rolls back on exception, always closes session.

    Inject via:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Health Check Helper ───────────────────────────────────────────────────────

async def check_db_connectivity() -> bool:
    """
    Execute a trivial query to verify the database is reachable.
    Returns True on success, False on any error.
    Used by the /health endpoint.
    """
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False
