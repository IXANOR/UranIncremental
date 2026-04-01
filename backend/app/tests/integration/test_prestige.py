"""Integration tests for POST /api/v1/game/prestige."""

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
    """Seeded test session."""
    await seed(db_session)
    return db_session


@pytest.fixture
async def api_client(seeded):
    """AsyncClient with get_db overridden to use the test session."""

    async def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def player(seeded):
    """Player with enough u238 to prestige."""
    p = await PlayerStateRepository.create(seeded)
    w = await WalletRepository.get_by_player(seeded, p.id)
    assert w is not None
    w.energy_drink = Decimal("1000")
    w.u238 = Decimal("5")
    await seeded.flush()
    return p


@pytest.fixture
def player_header(player) -> dict[str, str]:
    return {"X-Player-ID": str(player.id)}


# ---------------------------------------------------------------------------
# POST /api/v1/game/prestige
# ---------------------------------------------------------------------------


async def test_prestige_success(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """Prestige with sufficient u238 returns 200 with new_prestige_count=1."""
    resp = await api_client.post("/api/v1/game/prestige", headers=player_header)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["new_prestige_count"] == 1
    assert body["production_multiplier"] == pytest.approx(1.15)
    assert isinstance(body["surviving_upgrades"], list)


async def test_prestige_not_available_without_u238(
    api_client: AsyncClient, seeded, player_header: dict, player
) -> None:
    """Prestige with 0 u238 returns 409."""
    # Zero out u238
    w = await WalletRepository.get_by_player(seeded, player.id)
    assert w is not None
    w.u238 = Decimal("0")
    await seeded.commit()

    resp = await api_client.post("/api/v1/game/prestige", headers=player_header)
    assert resp.status_code == 409


async def test_prestige_resets_wallet(
    api_client: AsyncClient, player, player_header: dict, seeded
) -> None:
    """After prestige, GET /state shows wallet reset to starting values."""
    await api_client.post("/api/v1/game/prestige", headers=player_header)
    state_resp = await api_client.get("/api/v1/game/state", headers=player_header)
    assert state_resp.status_code == 200
    wallet = state_resp.json()["wallet"]
    assert Decimal(wallet["u238"]) == Decimal("0")
    # energy_drink might have ticked slightly above 50, but not 1000
    assert Decimal(wallet["energy_drink"]) < Decimal("100")


async def test_prestige_surviving_upgrades_preserved(
    api_client: AsyncClient, player, player_header: dict, seeded
) -> None:
    """offline_module_mk1 (survives_prestige=True) appears in surviving_upgrades."""
    # Give player enough energy for offline_module_mk1 (costs 500)
    w = await WalletRepository.get_by_player(seeded, player.id)
    assert w is not None
    w.energy_drink = Decimal("10000")
    await seeded.commit()

    # Buy the surviving upgrade
    buy_resp = await api_client.post(
        "/api/v1/economy/buy-upgrade",
        json={"upgrade_id": "offline_module_mk1"},
        headers=player_header,
    )
    assert buy_resp.status_code == 200

    # Now prestige
    resp = await api_client.post("/api/v1/game/prestige", headers=player_header)
    assert resp.status_code == 200
    assert "offline_module_mk1" in resp.json()["surviving_upgrades"]


async def test_prestige_state_valid_after(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """GET /state works cleanly after prestige (snapshot re-signed correctly)."""
    await api_client.post("/api/v1/game/prestige", headers=player_header)
    state_resp = await api_client.get("/api/v1/game/state", headers=player_header)
    assert state_resp.status_code == 200
    assert state_resp.json()["player"]["prestige_count"] == 1


async def test_prestige_missing_header(api_client: AsyncClient) -> None:
    """Prestige without X-Player-ID returns 400."""
    resp = await api_client.post("/api/v1/game/prestige")
    assert resp.status_code == 400
