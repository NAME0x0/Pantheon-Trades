"""Async SQLAlchemy session factory.

We keep ORM details out of this module. The router layer asks for an
``AsyncSession`` via :func:`get_session`; everything else lives in
domain-specific repositories. ``init_engine`` is called once during
``lifespan`` startup and disposed on shutdown so tests can swap engines.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pantheon_api.config import settings

log = structlog.get_logger("pantheon_api.db")

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> AsyncEngine:
    global _engine, _session_factory
    url = database_url or settings.database_url
    _engine = create_async_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    log.info("pantheon_api.db.engine_initialised", database_url=_safe_url(url))
    return _engine


async def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        log.info("pantheon_api.db.engine_disposed")


def engine() -> AsyncEngine:
    if _engine is None:
        return init_engine()
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    factory = session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession."""
    factory = session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


def _safe_url(url: str) -> str:
    # Strip embedded password before logging.
    if "@" not in url:
        return url
    scheme_creds, host = url.split("@", 1)
    if "://" not in scheme_creds:
        return f"***@{host}"
    scheme, creds = scheme_creds.split("://", 1)
    user = creds.split(":", 1)[0] if ":" in creds else creds
    return f"{scheme}://{user}:***@{host}"
