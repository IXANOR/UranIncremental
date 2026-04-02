"""Integration tests for POST /api/v1/game/click endpoint."""

import time
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.services.click_service import _click_timestamps


@pytest.fixture(autouse=True)
def clear_rate_limiter() -> None:
    """Reset in-memory rate limiter state between tests.

    Yields:
        None
    """
    _click_timestamps.clear()
    yield
    _click_timestamps.clear()


@pytest.fixture
async def seeded(db_session):
    """Seed unit and upgrade definitions.

    Args:
        db_session: In-memory SQLite session from root conftest.

    Returns:
        Seeded session.
    """
    await seed(db_session)
    return db_session


@pytest.fixture
async def api_client(seeded):
    """AsyncClient with get_db overridden to use the seeded test session.

    Args:
        seeded: Seeded async database session.

    Yields:
        AsyncClient bound to the FastAPI ASGI app.
    """

    async def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def player(seeded):
    """Create a test player.

    Args:
        seeded: Seeded async database session.

    Returns:
        Newly created PlayerState.
    """
    p = await PlayerStateRepository.create(seeded)
    await seeded.flush()
    return p


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_click_returns_200_with_gained(api_client, player) -> None:
    """POST /click returns 200 with a positive ``gained`` field."""
    resp = await api_client.post(
        "/api/v1/game/click",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "gained" in data
    assert Decimal(data["gained"]) > 0


@pytest.mark.asyncio
async def test_click_increases_wallet_balance(api_client, player, seeded) -> None:
    """Clicking adds energy_drink to the player's wallet."""
    w = await WalletRepository.get_by_player(seeded, player.id)
    assert w is not None
    starting_ed = w.energy_drink

    resp = await api_client.post(
        "/api/v1/game/click",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    gained = Decimal(resp.json()["gained"])

    await seeded.refresh(w)
    assert w.energy_drink == starting_ed + gained


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_click_rate_limit_returns_429(api_client, player) -> None:
    """The 11th click within 1 second returns 429."""
    now = time.time()
    _click_timestamps[player.id] = [now] * 10

    resp = await api_client.post(
        "/api/v1/game/click",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Auth errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_click_missing_player_id_returns_400(api_client) -> None:
    """POST /click without X-Player-ID header returns 400."""
    resp = await api_client.post("/api/v1/game/click")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_click_unknown_player_returns_404(api_client) -> None:
    """POST /click with a non-existent player UUID returns 404."""
    import uuid

    resp = await api_client.post(
        "/api/v1/game/click",
        headers={"X-Player-ID": str(uuid.uuid4())},
    )
    assert resp.status_code == 404
