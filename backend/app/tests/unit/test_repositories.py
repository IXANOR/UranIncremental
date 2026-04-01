"""Unit tests for all repository classes against an in-memory SQLite DB."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.event_log import EventLogRepository
from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.player_upgrade import PlayerUpgradeRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.repositories.upgrade_definition import UpgradeDefinitionRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed

# ---------------------------------------------------------------------------
# PlayerState
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_get_player(db_session: AsyncSession) -> None:
    """Creating a player should return a row retrievable by id."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        fetched = await PlayerStateRepository.get_by_id(db_session, player.id)

    assert fetched is not None
    assert fetched.id == player.id
    assert fetched.prestige_count == 0
    assert fetched.offline_efficiency == pytest.approx(0.20)


@pytest.mark.asyncio
async def test_get_single_player_returns_none_when_empty(db_session: AsyncSession) -> None:
    """get_single_player should return None when no player exists."""
    result = await PlayerStateRepository.get_single_player(db_session)
    assert result is None


@pytest.mark.asyncio
async def test_update_player_fields(db_session: AsyncSession) -> None:
    """update() should persist changed fields."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await PlayerStateRepository.update(db_session, p, prestige_count=3)

    async with db_session.begin():
        updated = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert updated is not None
        assert updated.prestige_count == 3


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wallet_created_with_starting_balance(db_session: AsyncSession) -> None:
    """Wallet should start with 50 energy_drink and 0 for all other currencies."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        wallet = await WalletRepository.get_by_player(db_session, player.id)

    assert wallet is not None
    assert wallet.energy_drink == Decimal("50")
    assert wallet.u238 == Decimal("0")


@pytest.mark.asyncio
async def test_wallet_update(db_session: AsyncSession) -> None:
    """update() should persist new currency values."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        wallet = await WalletRepository.get_by_player(db_session, player.id)
        assert wallet is not None
        await WalletRepository.update(db_session, wallet, energy_drink=Decimal("999"))

    async with db_session.begin():
        refreshed = await WalletRepository.get_by_player(db_session, player.id)
        assert refreshed is not None
        assert refreshed.energy_drink == Decimal("999")


# ---------------------------------------------------------------------------
# UnitDefinition + PlayerUnit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_loads_unit_definitions(db_session: AsyncSession) -> None:
    """Seed should insert all unit definitions; get_all returns them ordered."""
    async with db_session.begin():
        await seed(db_session)

    async with db_session.begin():
        units = await UnitDefinitionRepository.get_all(db_session)

    ids = [u.id for u in units]
    assert "barrel" in ids
    assert "centrifuge_t2" in ids
    assert len(units) == 7


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    """Running seed twice should not raise and should not duplicate rows."""
    async with db_session.begin():
        await seed(db_session)
    async with db_session.begin():
        await seed(db_session)

    async with db_session.begin():
        units = await UnitDefinitionRepository.get_all(db_session)
    assert len(units) == 7


@pytest.mark.asyncio
async def test_player_unit_upsert_creates_and_updates(db_session: AsyncSession) -> None:
    """upsert() should create the row on first call and update on subsequent calls."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)
        await seed(db_session)

    async with db_session.begin():
        row = await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=5)
    assert row.amount_owned == 5

    async with db_session.begin():
        row2 = await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=10)
    assert row2.amount_owned == 10

    async with db_session.begin():
        fetched = await PlayerUnitRepository.get_by_player_and_unit(db_session, player.id, "barrel")
        assert fetched is not None
        assert fetched.amount_owned == 10


# ---------------------------------------------------------------------------
# UpgradeDefinition + PlayerUpgrade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_loads_upgrade_definitions(db_session: AsyncSession) -> None:
    """Seed should insert all upgrade definitions."""
    async with db_session.begin():
        await seed(db_session)

    async with db_session.begin():
        upgrades = await UpgradeDefinitionRepository.get_all(db_session)

    ids = [u.id for u in upgrades]
    assert "offline_module_mk1" in ids
    assert "offline_cap_mk2" in ids
    assert len(upgrades) == 6


@pytest.mark.asyncio
async def test_player_upgrade_create_and_fetch(db_session: AsyncSession) -> None:
    """Creating a PlayerUpgrade should be retrievable by (player_id, upgrade_id)."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)
        await seed(db_session)

    async with db_session.begin():
        row = await PlayerUpgradeRepository.create(db_session, player.id, "offline_module_mk1")
    assert row.level == 1

    async with db_session.begin():
        fetched = await PlayerUpgradeRepository.get_by_player_and_upgrade(
            db_session, player.id, "offline_module_mk1"
        )
        assert fetched is not None
        assert fetched.upgrade_id == "offline_module_mk1"


# ---------------------------------------------------------------------------
# EventLog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_log_create(db_session: AsyncSession) -> None:
    """EventLog.create should persist a row with the given event_type and payload."""
    async with db_session.begin():
        player = await PlayerStateRepository.create(db_session)

    async with db_session.begin():
        event = await EventLogRepository.create(
            db_session,
            player.id,
            "delta_anomaly",
            {"delta_seconds": -5},
        )
    assert event.event_type == "delta_anomaly"
    assert event.payload["delta_seconds"] == -5
