"""Pytest fixtures for unit tests.

Uses an in-memory SQLite database (aiosqlite) so tests run without PostgreSQL.
All models are created fresh for each test function and dropped afterwards.
"""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401 — registers all models on Base.metadata
from app.db.base import Base

# StaticPool keeps a single connection so all transactions share the same
# in-memory SQLite database (SQLite :memory: is per-connection otherwise).
_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh async SQLite session with all tables created.

    Yields:
        AsyncSession: Session bound to an isolated in-memory database.
    """
    engine = create_async_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
