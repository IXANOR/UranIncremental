"""Integration tests for experiment endpoints."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.db.session import get_db
from app.main import app


@pytest.fixture
async def seeded(db_session):
    """Seed definitions into the in-memory test database.

    Args:
        db_session: Async SQLite session from root conftest.

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
    """Create a test player with ample funds.

    Args:
        seeded: Seeded async database session.

    Returns:
        Newly created PlayerState.
    """
    p = await PlayerStateRepository.create(seeded)
    w = await WalletRepository.get_by_player(seeded, p.id)
    assert w is not None
    w.energy_drink = Decimal("10000")
    w.u238 = Decimal("100")
    await seeded.flush()
    return p


# ---------------------------------------------------------------------------
# GET /api/v1/game/experiments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_experiments_returns_3(api_client, player) -> None:
    """GET /experiments returns all 3 seeded experiments."""
    resp = await api_client.get(
        "/api/v1/game/experiments",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_experiments_includes_cooldown(api_client, player) -> None:
    """Each experiment in the list has a cooldown_remaining_seconds field."""
    resp = await api_client.get(
        "/api/v1/game/experiments",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    for exp in resp.json():
        assert "cooldown_remaining_seconds" in exp
        assert exp["cooldown_remaining_seconds"] == 0  # fresh player, no cooldowns


# ---------------------------------------------------------------------------
# POST /api/v1/game/experiment/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_experiment_returns_outcome(api_client, player) -> None:
    """POST /experiment/alpha_test returns 200 with outcome fields."""
    resp = await api_client.post(
        "/api/v1/game/experiment/alpha_test",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "outcome_label" in data
    assert "effect_type" in data
    assert "cooldown_until" in data


@pytest.mark.asyncio
async def test_run_experiment_unknown_returns_404(api_client, player) -> None:
    """POST /experiment/nope returns 404."""
    resp = await api_client.post(
        "/api/v1/game/experiment/nope",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_experiment_on_cooldown_returns_409(api_client, player, seeded) -> None:
    """Second run within cooldown window returns 409."""
    headers = {"X-Player-ID": str(player.id)}
    # First run — should succeed
    r1 = await api_client.post("/api/v1/game/experiment/alpha_test", headers=headers)
    assert r1.status_code == 200

    # Reload player to get updated cooldowns (same session, need refresh)
    await seeded.refresh(player)

    # Second run — should fail with 409
    r2 = await api_client.post("/api/v1/game/experiment/alpha_test", headers=headers)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_run_experiment_insufficient_funds_returns_402(api_client, seeded) -> None:
    """POST /experiment/alpha_test with 0 ED returns 402."""
    broke_player = await PlayerStateRepository.create(seeded)
    w = await WalletRepository.get_by_player(seeded, broke_player.id)
    assert w is not None
    w.energy_drink = Decimal("0")
    await seeded.flush()

    resp = await api_client.post(
        "/api/v1/game/experiment/alpha_test",
        headers={"X-Player-ID": str(broke_player.id)},
    )
    assert resp.status_code == 402


@pytest.mark.asyncio
async def test_run_experiment_missing_player_returns_400(api_client) -> None:
    """POST /experiment/alpha_test without X-Player-ID returns 400."""
    resp = await api_client.post("/api/v1/game/experiment/alpha_test")
    assert resp.status_code == 400
