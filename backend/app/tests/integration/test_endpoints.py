"""Integration tests for MVP endpoints.

Each test uses a real in-memory SQLite database (via the shared ``db_session``
fixture) with ``get_db`` overridden so the app uses the same session as the
test setup code.
"""

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded(db_session):
    """Seed unit and upgrade definitions into the test database.

    Args:
        db_session: In-memory SQLite session from the root conftest.

    Returns:
        The same session after seeding.
    """
    await seed(db_session)
    return db_session


@pytest.fixture
async def api_client(seeded):
    """AsyncClient with ``get_db`` overridden to use the test session.

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
        Newly created PlayerState with an inflated wallet.
    """
    p = await PlayerStateRepository.create(seeded)
    w = await WalletRepository.get_by_player(seeded, p.id)
    assert w is not None
    w.energy_drink = Decimal("1000")
    await seeded.flush()
    return p


@pytest.fixture
async def player_header(player) -> dict[str, str]:
    """Return an ``X-Player-ID`` header dict for the test player.

    Args:
        player: Test PlayerState fixture.

    Returns:
        Dict suitable for use as ``headers=`` in HTTPX requests.
    """
    return {"X-Player-ID": str(player.id)}


# ---------------------------------------------------------------------------
# POST /api/v1/game/start
# ---------------------------------------------------------------------------


async def test_start_game_creates_player(api_client: AsyncClient) -> None:
    """POST /start with no existing player creates one and returns its id."""
    resp = await api_client.post("/api/v1/game/start")
    assert resp.status_code == 200
    body = resp.json()
    assert "player_id" in body
    assert "state_version" in body
    assert "started_at" in body
    # UUID must be parseable
    uuid.UUID(body["player_id"])


async def test_start_game_idempotent(api_client: AsyncClient) -> None:
    """POST /start twice returns the same player_id both times."""
    r1 = await api_client.post("/api/v1/game/start")
    r2 = await api_client.post("/api/v1/game/start")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["player_id"] == r2.json()["player_id"]


# ---------------------------------------------------------------------------
# GET /api/v1/game/state
# ---------------------------------------------------------------------------


async def test_get_state_missing_header(api_client: AsyncClient) -> None:
    """GET /state without X-Player-ID returns 400."""
    resp = await api_client.get("/api/v1/game/state")
    assert resp.status_code == 400
    assert "X-Player-ID" in resp.json()["detail"]


async def test_get_state_invalid_uuid(api_client: AsyncClient) -> None:
    """GET /state with a non-UUID X-Player-ID returns 400."""
    resp = await api_client.get("/api/v1/game/state", headers={"X-Player-ID": "not-a-uuid"})
    assert resp.status_code == 400


async def test_get_state_unknown_player(api_client: AsyncClient) -> None:
    """GET /state with a valid but non-existent UUID returns 404."""
    resp = await api_client.get("/api/v1/game/state", headers={"X-Player-ID": str(uuid.uuid4())})
    assert resp.status_code == 404


async def test_get_state_success(api_client: AsyncClient, player, player_header: dict) -> None:
    """GET /state returns player, wallet, server_time, units, and upgrades after a tick."""
    resp = await api_client.get("/api/v1/game/state", headers=player_header)
    assert resp.status_code == 200
    body = resp.json()
    assert body["player"]["id"] == str(player.id)
    assert "wallet" in body
    assert "server_time" in body
    for currency in ("energy_drink", "u238", "u235", "u233", "meta_isotopes"):
        assert currency in body["wallet"]
    # Task 11: state must include units and upgrades catalog
    assert "units" in body, "GET /state must return units array"
    assert "upgrades" in body, "GET /state must return upgrades array"
    assert len(body["units"]) > 0
    assert len(body["upgrades"]) > 0
    unit = body["units"][0]
    assert "unit_id" in unit
    assert "name" in unit
    assert "amount_owned" in unit
    assert "next_cost" in unit
    assert "production_rate_per_sec" in unit
    upgrade = body["upgrades"][0]
    assert "upgrade_id" in upgrade
    assert "name" in upgrade
    assert "cost_amount" in upgrade
    assert "purchased_level" in upgrade


async def test_get_state_increments_version(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """Each GET /state call increments the state_version."""
    r1 = await api_client.get("/api/v1/game/state", headers=player_header)
    r2 = await api_client.get("/api/v1/game/state", headers=player_header)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["player"]["version"] > r1.json()["player"]["version"]


# ---------------------------------------------------------------------------
# POST /api/v1/economy/buy-unit
# ---------------------------------------------------------------------------


async def test_buy_unit_success(api_client: AsyncClient, player, player_header: dict) -> None:
    """Buying a barrel with sufficient funds returns new_amount_owned=1."""
    resp = await api_client.post(
        "/api/v1/economy/buy-unit",
        json={"unit_id": "barrel", "quantity": 1},
        headers=player_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["new_amount_owned"] == 1
    assert "wallet_after" in body
    # Cost of first barrel is 15; player had 1000
    assert Decimal(body["wallet_after"]["energy_drink"]) < Decimal("1000")


async def test_buy_unit_bulk(api_client: AsyncClient, player, player_header: dict) -> None:
    """Buying quantity=3 barrels returns new_amount_owned=3."""
    resp = await api_client.post(
        "/api/v1/economy/buy-unit",
        json={"unit_id": "barrel", "quantity": 3},
        headers=player_header,
    )
    assert resp.status_code == 200
    assert resp.json()["new_amount_owned"] == 3


async def test_buy_unit_insufficient_funds(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """Buying a unit the player cannot afford returns 409."""
    resp = await api_client.post(
        "/api/v1/economy/buy-unit",
        # centrifuge_t2 costs 1 000 000; player only has 1 000
        json={"unit_id": "centrifuge_t2", "quantity": 1},
        headers=player_header,
    )
    assert resp.status_code == 409


async def test_buy_unit_unknown_unit(api_client: AsyncClient, player, player_header: dict) -> None:
    """Buying a non-existent unit_id returns 404."""
    resp = await api_client.post(
        "/api/v1/economy/buy-unit",
        json={"unit_id": "does_not_exist", "quantity": 1},
        headers=player_header,
    )
    assert resp.status_code == 404


async def test_buy_unit_invalid_quantity(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """Buying quantity=0 returns 422."""
    resp = await api_client.post(
        "/api/v1/economy/buy-unit",
        json={"unit_id": "barrel", "quantity": 0},
        headers=player_header,
    )
    assert resp.status_code == 422


async def test_buy_unit_missing_header(api_client: AsyncClient) -> None:
    """buy-unit without X-Player-ID returns 400."""
    resp = await api_client.post(
        "/api/v1/economy/buy-unit", json={"unit_id": "barrel", "quantity": 1}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/economy/buy-upgrade
# ---------------------------------------------------------------------------


async def test_buy_upgrade_success(api_client: AsyncClient, player, player_header: dict) -> None:
    """Buying barrel_opt_mk1 (costs 200) with 1000 energy_drink succeeds."""
    resp = await api_client.post(
        "/api/v1/economy/buy-upgrade",
        json={"upgrade_id": "barrel_opt_mk1"},
        headers=player_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["upgrade_level"] == 1
    assert body["applied_effect"]["effect_type"] == "prod_mult"


async def test_buy_upgrade_insufficient_funds(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """Buying an upgrade the player cannot afford returns 409."""
    # offline_cap_mk2 costs 20 000; player has 1 000
    resp = await api_client.post(
        "/api/v1/economy/buy-upgrade",
        json={"upgrade_id": "offline_cap_mk2"},
        headers=player_header,
    )
    assert resp.status_code == 409


async def test_buy_upgrade_already_purchased(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """Buying a non-repeatable upgrade twice returns 409 on the second attempt."""
    payload = {"upgrade_id": "barrel_opt_mk1"}
    r1 = await api_client.post("/api/v1/economy/buy-upgrade", json=payload, headers=player_header)
    assert r1.status_code == 200
    r2 = await api_client.post("/api/v1/economy/buy-upgrade", json=payload, headers=player_header)
    assert r2.status_code == 409


async def test_buy_upgrade_unknown_upgrade(
    api_client: AsyncClient, player, player_header: dict
) -> None:
    """Buying a non-existent upgrade_id returns 404."""
    resp = await api_client.post(
        "/api/v1/economy/buy-upgrade",
        json={"upgrade_id": "ghost_upgrade"},
        headers=player_header,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/time/claim-offline
# ---------------------------------------------------------------------------


async def test_claim_offline_success(api_client: AsyncClient, player, player_header: dict) -> None:
    """claim-offline returns simulated_seconds, efficiency_used, gains, cap_applied."""
    resp = await api_client.post("/api/v1/time/claim-offline", headers=player_header)
    assert resp.status_code == 200
    body = resp.json()
    assert "simulated_seconds" in body
    assert "efficiency_used" in body
    assert "gains" in body
    assert "cap_applied" in body
    assert isinstance(body["simulated_seconds"], int)
    assert isinstance(body["cap_applied"], bool)


async def test_claim_offline_missing_header(api_client: AsyncClient) -> None:
    """claim-offline without X-Player-ID returns 400."""
    resp = await api_client.post("/api/v1/time/claim-offline")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Snapshot integrity — tampered state returns 409
# ---------------------------------------------------------------------------


async def test_tampered_snapshot_returns_409(
    api_client: AsyncClient, player, player_header: dict, seeded
) -> None:
    """GET /state returns 409 when the stored snapshot signature is corrupted."""
    # First call signs the state
    r1 = await api_client.get("/api/v1/game/state", headers=player_header)
    assert r1.status_code == 200

    # Directly corrupt the signature in the DB
    from app.db.repositories.player_state import PlayerStateRepository

    p = await PlayerStateRepository.get_by_id(seeded, player.id)
    assert p is not None
    p.snapshot_signature = "corrupted-signature-value"
    await seeded.commit()

    # Next call must detect tampering
    r2 = await api_client.get("/api/v1/game/state", headers=player_header)
    assert r2.status_code == 409
