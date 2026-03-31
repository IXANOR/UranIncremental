import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Provide an async HTTP test client bound to the FastAPI app.

    Yields:
        AsyncClient: HTTPX client for making requests against the app.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
