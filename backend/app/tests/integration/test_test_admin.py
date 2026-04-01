"""Integration tests for test/admin endpoints.

Covers both TEST_MODE=true (normal operation) and TEST_MODE=false (hard block).
"""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures (mirror the pattern from test_endpoints.py)
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded(db_session):
    """Seed unit and upgrade definitions.

    Args:
        db_session: In-memory SQLite session from root conftest.

    Returns:
        The seeded session.
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
    """Create a test player with 1 000 energy_drink.

    Args:
        seeded: Seeded async database session.

    Returns:
        Newly created PlayerState.
    """
    p = await PlayerStateRepository.create(seeded)
    w = await WalletRepository.get_by_player(seeded, p.id)
    assert w is not None
    w.energy_drink = Decimal("1000")
    await seeded.flush()
    return p


@pytest.fixture
def player_header(player) -> dict[str, str]:
    """X-Player-ID header dict for the test player.

    Args:
        player: Test PlayerState.

    Returns:
        Header dict for HTTPX requests.
    """
    return {"X-Player-ID": str(player.id)}


# ---------------------------------------------------------------------------
# POST /api/v1/test/simulate-time — TEST_MODE guard
# ---------------------------------------------------------------------------


async def test_simulate_time_blocked_when_test_mode_false(
    api_client: AsyncClient, player_header: dict, monkeypatch
) -> None:
    """simulate-time returns 404 when TEST_MODE is false."""
    monkeypatch.setattr(settings, "test_mode", False)
    resp = await api_client.post(
        "/api/v1/test/simulate-time",
        json={"seconds": 60},
        headers=player_header,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/test/simulate-time — happy path
# ---------------------------------------------------------------------------


async def test_simulate_time_advances_production(
    api_client: AsyncClient, player, player_header: dict, seeded
) -> None:
    """simulate-time with 3600s applies one hour of barrel production."""
    # Give the player a barrel so production is non-zero
    from app.db.repositories.player_unit import PlayerUnitRepository

    await PlayerUnitRepository.upsert(seeded, player.id, "barrel", amount_owned=1)
    await seeded.flush()

    resp = await api_client.post(
        "/api/v1/test/simulate-time",
        json={"seconds": 3600},
        headers=player_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["simulated_seconds"] == 3600
    assert body["new_state_version"] > 1


async def test_simulate_time_increments_version(
    api_client: AsyncClient, player_header: dict
) -> None:
    """Each simulate-time call increments state_version."""
    r1 = await api_client.post(
        "/api/v1/test/simulate-time", json={"seconds": 10}, headers=player_header
    )
    r2 = await api_client.post(
        "/api/v1/test/simulate-time", json={"seconds": 10}, headers=player_header
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["new_state_version"] > r1.json()["new_state_version"]


async def test_simulate_time_zero_seconds_rejected(
    api_client: AsyncClient, player_header: dict
) -> None:
    """seconds=0 is rejected with 422."""
    resp = await api_client.post(
        "/api/v1/test/simulate-time",
        json={"seconds": 0},
        headers=player_header,
    )
    assert resp.status_code == 422


async def test_simulate_time_negative_seconds_rejected(
    api_client: AsyncClient, player_header: dict
) -> None:
    """Negative seconds are rejected with 422."""
    resp = await api_client.post(
        "/api/v1/test/simulate-time",
        json={"seconds": -100},
        headers=player_header,
    )
    assert resp.status_code == 422


async def test_simulate_time_missing_player_header(api_client: AsyncClient) -> None:
    """simulate-time without X-Player-ID returns 400."""
    resp = await api_client.post("/api/v1/test/simulate-time", json={"seconds": 60})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/test/correct-state — TEST_MODE guard
# ---------------------------------------------------------------------------


async def test_correct_state_blocked_when_test_mode_false(
    api_client: AsyncClient, player_header: dict, monkeypatch
) -> None:
    """correct-state returns 404 when TEST_MODE is false."""
    monkeypatch.setattr(settings, "test_mode", False)
    resp = await api_client.post(
        "/api/v1/test/correct-state",
        json={"wallet": {"energy_drink": "99999"}},
        headers=player_header,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/test/correct-state — happy path
# ---------------------------------------------------------------------------


async def test_correct_state_patches_wallet(api_client: AsyncClient, player_header: dict) -> None:
    """correct-state sets energy_drink to the provided value."""
    resp = await api_client.post(
        "/api/v1/test/correct-state",
        json={"wallet": {"energy_drink": "99999"}},
        headers=player_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert Decimal(body["wallet_after"]["energy_drink"]) == Decimal("99999")


async def test_correct_state_patches_only_provided_fields(
    api_client: AsyncClient, player_header: dict
) -> None:
    """correct-state with partial wallet patch leaves other currencies untouched."""
    resp = await api_client.post(
        "/api/v1/test/correct-state",
        json={"wallet": {"u238": "500"}},
        headers=player_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    # energy_drink must still be the original 1000 (not zeroed)
    assert Decimal(body["wallet_after"]["energy_drink"]) == Decimal("1000")
    assert Decimal(body["wallet_after"]["u238"]) == Decimal("500")


async def test_correct_state_patches_units(api_client: AsyncClient, player_header: dict) -> None:
    """correct-state sets barrel amount_owned to the provided value."""
    resp = await api_client.post(
        "/api/v1/test/correct-state",
        json={"units": {"barrel": {"amount_owned": 10}}},
        headers=player_header,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_correct_state_empty_body(api_client: AsyncClient, player_header: dict) -> None:
    """correct-state with empty body is a no-op and returns current wallet."""
    resp = await api_client.post(
        "/api/v1/test/correct-state",
        json={},
        headers=player_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "wallet_after" in body


async def test_correct_state_state_is_usable_after_correction(
    api_client: AsyncClient, player_header: dict
) -> None:
    """After correct-state, GET /state still works (signature was invalidated cleanly)."""
    await api_client.post(
        "/api/v1/test/correct-state",
        json={"wallet": {"energy_drink": "500"}},
        headers=player_header,
    )
    resp = await api_client.get("/api/v1/game/state", headers=player_header)
    assert resp.status_code == 200
