"""Async SQLAlchemy session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def make_session_factory(
    database_url: str,
    pool_pre_ping: bool = True,
    **engine_kwargs: object,
) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        database_url, echo=False, pool_pre_ping=pool_pre_ping, **engine_kwargs
    )
    return async_sessionmaker(engine, expire_on_commit=False)


def init_engine(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Create and return a session factory for the given database URL."""
    return make_session_factory(database_url)


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session
