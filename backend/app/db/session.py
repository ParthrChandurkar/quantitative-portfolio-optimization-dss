"""Asynchronous SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def create_engine(
    database_url: str | None = None, *, echo: bool = False
) -> AsyncEngine:
    """Create an async engine without establishing a connection eagerly."""

    url = database_url if database_url is not None else get_settings().database_url
    return create_async_engine(url, echo=echo, pool_pre_ping=True)


engine = create_engine()
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one transactional request-scoped database session."""

    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
