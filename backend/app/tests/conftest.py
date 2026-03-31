"""Root test configuration.

Environment variables must be set before any app module is imported,
because app.core.config instantiates Settings() at module level.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SNAPSHOT_SECRET", "test-secret-key-for-tests-only")
os.environ.setdefault("TEST_MODE", "true")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.db.models  # noqa: E402, F401 — registers all models on Base.metadata
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh async SQLite session with all tables created.

    StaticPool keeps a single connection so all transactions in the test
    share the same in-memory database.

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


@pytest.fixture
async def client() -> AsyncClient:
    """Provide an async HTTP test client bound to the FastAPI app.

    Yields:
        AsyncClient: HTTPX client for making requests against the app.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
