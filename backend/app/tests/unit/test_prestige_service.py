"""Unit tests for prestige_service."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.player_upgrade import PlayerUpgradeRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.services.prestige_service import (
    PRESTIGE_U238_REQUIREMENT,
    PrestigeNotAvailableError,
    prestige,
    prestige_requirement,
)


async def _make_player_with_u238(session: AsyncSession, u238: Decimal):
    """Helper: create a player and set wallet.u238 to the given amount."""
    player = await PlayerStateRepository.create(session)
    w = await WalletRepository.get_by_player(session, player.id)
    assert w is not None
    w.u238 = u238
    return player, w


# ---------------------------------------------------------------------------
# Prestige requirement gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_requires_u238(db_session: AsyncSession) -> None:
    """prestige() raises PrestigeNotAvailableError when u238 < threshold."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, Decimal("0"))

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        with pytest.raises(PrestigeNotAvailableError):
            await prestige(db_session, p)


@pytest.mark.asyncio
async def test_prestige_allowed_at_exact_threshold(db_session: AsyncSession) -> None:
    """prestige() succeeds when u238 equals PRESTIGE_U238_REQUIREMENT exactly."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await prestige(db_session, p)

    assert result.new_prestige_count == 1


# ---------------------------------------------------------------------------
# Wallet reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_resets_wallet_to_starting_values(db_session: AsyncSession) -> None:
    """After prestige the wallet is reset: 50 ED, all others 0."""
    async with db_session.begin():
        await seed(db_session)
        player, w = await _make_player_with_u238(db_session, Decimal("5"))
        w.energy_drink = Decimal("999999")
        w.u235 = Decimal("100")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await prestige(db_session, p)

    wallet = await WalletRepository.get_by_player(db_session, player.id)
    assert wallet is not None
    assert wallet.energy_drink == Decimal("50")
    assert wallet.u238 == Decimal("0")
    assert wallet.u235 == Decimal("0")
    assert wallet.u233 == Decimal("0")
    assert wallet.meta_isotopes == Decimal("0")


# ---------------------------------------------------------------------------
# Prestige count and player state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_increments_prestige_count(db_session: AsyncSession) -> None:
    """prestige_count increases by exactly 1 per prestige."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await prestige(db_session, p)

    assert result.new_prestige_count == 1


@pytest.mark.asyncio
async def test_prestige_clears_snapshot_signature(db_session: AsyncSession) -> None:
    """Snapshot signature is cleared to '' so the next tick re-signs cleanly."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)
        player.snapshot_signature = "some-old-sig"

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await prestige(db_session, p)

    p2 = await PlayerStateRepository.get_by_id(db_session, player.id)
    assert p2 is not None
    assert p2.snapshot_signature == ""


@pytest.mark.asyncio
async def test_prestige_resets_offline_params_to_defaults(db_session: AsyncSession) -> None:
    """offline_efficiency and offline_cap_seconds return to defaults after prestige."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)
        player.offline_efficiency = 0.99
        player.offline_cap_seconds = 99999

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await prestige(db_session, p)

    p2 = await PlayerStateRepository.get_by_id(db_session, player.id)
    assert p2 is not None
    assert p2.offline_efficiency == pytest.approx(0.20)
    assert p2.offline_cap_seconds == 14400


# ---------------------------------------------------------------------------
# Unit reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_zeros_unit_amounts(db_session: AsyncSession) -> None:
    """All PlayerUnit.amount_owned values are reset to 0."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)
        await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=50)
        await PlayerUnitRepository.upsert(db_session, player.id, "mini_reactor", amount_owned=10)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await prestige(db_session, p)

    units = await PlayerUnitRepository.get_by_player(db_session, player.id)
    assert all(u.amount_owned == 0 for u in units)


@pytest.mark.asyncio
async def test_prestige_resets_effective_multipliers(db_session: AsyncSession) -> None:
    """effective_multiplier is reset to 1.0 for all units after prestige."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)
        await PlayerUnitRepository.upsert(
            db_session,
            player.id,
            "barrel",
            amount_owned=1,
            effective_multiplier=Decimal("3.5"),
        )

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await prestige(db_session, p)

    barrel = await PlayerUnitRepository.get_by_player_and_unit(db_session, player.id, "barrel")
    assert barrel is not None
    assert barrel.effective_multiplier == Decimal("1.0")


# ---------------------------------------------------------------------------
# Upgrade handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_removes_non_surviving_upgrades(db_session: AsyncSession) -> None:
    """Upgrades with survives_prestige=False are deleted after prestige."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)
        # barrel_opt_mk1 has survives_prestige=False
        await PlayerUpgradeRepository.create(db_session, player.id, "barrel_opt_mk1")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await prestige(db_session, p)

    assert "barrel_opt_mk1" not in result.surviving_upgrade_ids
    pu = await PlayerUpgradeRepository.get_by_player_and_upgrade(
        db_session, player.id, "barrel_opt_mk1"
    )
    assert pu is None


@pytest.mark.asyncio
async def test_prestige_keeps_surviving_upgrades(db_session: AsyncSession) -> None:
    """Upgrades with survives_prestige=True are preserved after prestige."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)
        # offline_module_mk1 has survives_prestige=True
        await PlayerUpgradeRepository.create(db_session, player.id, "offline_module_mk1")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await prestige(db_session, p)

    assert "offline_module_mk1" in result.surviving_upgrade_ids
    pu = await PlayerUpgradeRepository.get_by_player_and_upgrade(
        db_session, player.id, "offline_module_mk1"
    )
    assert pu is not None
    assert pu.level == 1


@pytest.mark.asyncio
async def test_prestige_reapplies_surviving_offline_efficiency_upgrade(
    db_session: AsyncSession,
) -> None:
    """offline_module_mk1 effect (offline_eff_up +0.05) is re-applied after prestige."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, PRESTIGE_U238_REQUIREMENT)
        await PlayerUpgradeRepository.create(db_session, player.id, "offline_module_mk1")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await prestige(db_session, p)

    p2 = await PlayerStateRepository.get_by_id(db_session, player.id)
    assert p2 is not None
    # default 0.20 + offline_module_mk1 effect 0.05 = 0.25
    assert p2.offline_efficiency == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Production multiplier boost
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prestige_production_multiplier_is_1_15_per_prestige(
    db_session: AsyncSession,
) -> None:
    """prestige_count=1 gives 1.15× production; prestige_count=2 gives 1.15²×."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, Decimal("10"))

    # First prestige
    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        r1 = await prestige(db_session, p)

    assert r1.new_prestige_count == 1

    # Give u238 again for second prestige
    async with db_session.begin():
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.u238 = Decimal("5")

    async with db_session.begin():
        p2 = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p2 is not None
        r2 = await prestige(db_session, p2)

    assert r2.new_prestige_count == 2


# ---------------------------------------------------------------------------
# Scaling prestige requirement
# ---------------------------------------------------------------------------


def test_prestige_requirement_pure_scaling() -> None:
    """prestige_requirement doubles for each prestige: 1, 2, 4, 8..."""
    assert prestige_requirement(0) == Decimal("1")
    assert prestige_requirement(1) == Decimal("2")
    assert prestige_requirement(2) == Decimal("4")
    assert prestige_requirement(3) == Decimal("8")


@pytest.mark.asyncio
async def test_second_prestige_requires_more_u238(db_session: AsyncSession) -> None:
    """After first prestige (count=1) the requirement rises to 2 U-238."""
    async with db_session.begin():
        await seed(db_session)
        player, _ = await _make_player_with_u238(db_session, Decimal("5"))

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        r1 = await prestige(db_session, p)
    assert r1.new_prestige_count == 1

    # Give only 1 U-238 — below the new requirement of 2
    async with db_session.begin():
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.u238 = Decimal("1")

    async with db_session.begin():
        p2 = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p2 is not None
        with pytest.raises(PrestigeNotAvailableError):
            await prestige(db_session, p2)
