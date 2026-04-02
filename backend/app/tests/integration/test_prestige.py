"""Integration tests for multi-prestige endpoint and prestige_options in game state."""

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
    """Seed definitions and return session.

    Args:
        db_session: In-memory SQLite session from root conftest.

    Returns:
        Seeded async session.
    """
    await seed(db_session)
    return db_session


@pytest.fixture
async def api_client(seeded):
    """AsyncClient with get_db overridden to use seeded test session.

    Args:
        seeded: Seeded async session.

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
    """Create a player with 1 U-238 in the wallet (enough for 1× prestige at p=0).

    Args:
        seeded: Seeded async session.

    Returns:
        PlayerState with sufficient U-238.
    """
    p = await PlayerStateRepository.create(seeded)
    w = await WalletRepository.get_by_player(seeded, p.id)
    assert w is not None
    w.u238 = Decimal("10")  # enough for several 1× prestiges
    await seeded.flush()
    return p


# ---------------------------------------------------------------------------
# GET /game/state — new prestige_options and bulk cost fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_includes_prestige_options(api_client, player) -> None:
    """GET /game/state returns prestige_options list with 4 entries."""
    resp = await api_client.get(
        "/api/v1/game/state",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "prestige_options" in data
    opts = data["prestige_options"]
    assert len(opts) == 4
    counts = {o["count"] for o in opts}
    assert counts == {1, 5, 10, 25}


@pytest.mark.asyncio
async def test_state_prestige_options_can_afford_flag(api_client, player, seeded) -> None:
    """can_afford is True for 1× U-238 when wallet has enough."""
    resp = await api_client.get(
        "/api/v1/game/state",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    opts = {o["count"]: o for o in resp.json()["prestige_options"]}
    # Player has 10 U-238, p=0 → 1× costs 1 U-238 → can afford
    assert opts[1]["can_afford"] is True
    # 5× U-235 costs 1 U-235 but player has 0 → cannot afford
    assert opts[5]["can_afford"] is False


@pytest.mark.asyncio
async def test_state_units_include_bulk_costs(api_client, player) -> None:
    """GET /game/state units include bulk_10_cost, bulk_100_cost, max_affordable."""
    resp = await api_client.get(
        "/api/v1/game/state",
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    units = resp.json()["units"]
    assert len(units) > 0
    for unit in units:
        assert "bulk_10_cost" in unit
        assert "bulk_100_cost" in unit
        assert "max_affordable" in unit
        assert Decimal(unit["bulk_10_cost"]) >= Decimal(unit["next_cost"])
        assert Decimal(unit["bulk_100_cost"]) >= Decimal(unit["bulk_10_cost"])
        assert isinstance(unit["max_affordable"], int)


# ---------------------------------------------------------------------------
# POST /game/prestige — 1× U-238 (default)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_1x_u238_success(api_client, player) -> None:
    """POST /game/prestige with default body increments prestige_count by 1."""
    resp = await api_client.post(
        "/api/v1/game/prestige",
        json={"count": 1, "currency": "u238"},
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["new_prestige_count"] == 1


@pytest.mark.asyncio
async def test_prestige_1x_insufficient_u238_returns_409(api_client, player, seeded) -> None:
    """POST /game/prestige returns 409 when player lacks U-238."""
    w = await WalletRepository.get_by_player(seeded, player.id)
    assert w is not None
    w.u238 = Decimal("0")
    await seeded.flush()

    resp = await api_client.post(
        "/api/v1/game/prestige",
        json={"count": 1, "currency": "u238"},
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_prestige_invalid_count_returns_422(api_client, player) -> None:
    """POST /game/prestige with invalid count returns 422."""
    resp = await api_client.post(
        "/api/v1/game/prestige",
        json={"count": 3, "currency": "u238"},
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /game/prestige — 5× U-235
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_5x_u235_success(api_client, player, seeded) -> None:
    """POST /game/prestige 5× U-235 increments prestige_count by 5."""
    w = await WalletRepository.get_by_player(seeded, player.id)
    assert w is not None
    w.u235 = Decimal("5")  # enough for 5× at p=0 (cost=1 U-235)
    await seeded.flush()

    resp = await api_client.post(
        "/api/v1/game/prestige",
        json={"count": 5, "currency": "u235"},
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_prestige_count"] == 5


@pytest.mark.asyncio
async def test_prestige_5x_u235_insufficient_returns_409(api_client, player) -> None:
    """5× U-235 prestige with 0 U-235 returns 409."""
    resp = await api_client.post(
        "/api/v1/game/prestige",
        json={"count": 5, "currency": "u235"},
        headers={"X-Player-ID": str(player.id)},
    )
    assert resp.status_code == 409
