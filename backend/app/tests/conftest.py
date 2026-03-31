"""Root test configuration.

Environment variables must be set before any app module is imported,
because app.core.config instantiates Settings() at module level.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SNAPSHOT_SECRET", "test-secret-key-for-tests-only")
os.environ.setdefault("TEST_MODE", "true")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncClient:
    """Provide an async HTTP test client bound to the FastAPI app.

    Yields:
        AsyncClient: HTTPX client for making requests against the app.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
