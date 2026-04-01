"""Balance tests for prestige mechanics."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.player_unit import PlayerUnitRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.services.game_loop_service import tick
from app.services.prestige_service import PRESTIGE_U238_REQUIREMENT, prestige


@pytest.mark.asyncio
async def test_centrifuge_reaches_prestige_threshold_in_reasonable_time(
    db_session: AsyncSession,
) -> None:
    """One centrifuge accumulates >= 1 u238 after 1100 simulated seconds.

    centrifuge_t2 produces 0.001 u238/s → 1100s × 0.001 = 1.1 u238 >= threshold.
    This verifies the production chain to first prestige is viable.
    """
    from datetime import UTC, datetime, timedelta

    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_tick_at = datetime.now(UTC) - timedelta(seconds=1100)
        player.last_online_at = datetime.now(UTC)
        # Pre-fund with centrifuge and give it to the player
        await PlayerUnitRepository.upsert(
            db_session, player.id, "centrifuge_t2", amount_owned=1
        )
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("0")  # no ED production, isolate u238 output

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    assert result.wallet.u238 >= PRESTIGE_U238_REQUIREMENT, (
        f"Expected u238 >= {PRESTIGE_U238_REQUIREMENT}, got {result.wallet.u238}"
    )


@pytest.mark.asyncio
async def test_prestige_production_boost_measurable(db_session: AsyncSession) -> None:
    """Production with prestige_count=1 is strictly greater than without prestige."""
    from datetime import UTC, datetime, timedelta

    delta_seconds = 100

    # Baseline: no prestige
    async with db_session.begin():
        await seed(db_session)
        player_base = await PlayerStateRepository.create(db_session)
        player_base.last_tick_at = datetime.now(UTC) - timedelta(seconds=delta_seconds)
        player_base.last_online_at = datetime.now(UTC)
        await PlayerUnitRepository.upsert(
            db_session, player_base.id, "barrel", amount_owned=10
        )
        w = await WalletRepository.get_by_player(db_session, player_base.id)
        assert w is not None
        w.energy_drink = Decimal("0")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player_base.id)
        assert p is not None
        base_result = await tick(db_session, p)
    base_gains = base_result.gains.get("energy_drink", Decimal("0"))

    # With prestige_count=1 (1.15× multiplier)
    async with db_session.begin():
        await seed(db_session)
        player_p1 = await PlayerStateRepository.create(db_session)
        player_p1.prestige_count = 1
        player_p1.last_tick_at = datetime.now(UTC) - timedelta(seconds=delta_seconds)
        player_p1.last_online_at = datetime.now(UTC)
        await PlayerUnitRepository.upsert(
            db_session, player_p1.id, "barrel", amount_owned=10
        )
        w2 = await WalletRepository.get_by_player(db_session, player_p1.id)
        assert w2 is not None
        w2.energy_drink = Decimal("0")

    async with db_session.begin():
        p2 = await PlayerStateRepository.get_by_id(db_session, player_p1.id)
        assert p2 is not None
        p1_result = await tick(db_session, p2)
    p1_gains = p1_result.gains.get("energy_drink", Decimal("0"))

    assert p1_gains > base_gains, (
        f"Prestige boost not applied: base={base_gains}, p1={p1_gains}"
    )
    # Verify the multiplier is approximately 1.15
    ratio = p1_gains / base_gains
    assert Decimal("1.14") <= ratio <= Decimal("1.16"), f"Unexpected ratio: {ratio}"


@pytest.mark.asyncio
async def test_prestige_surviving_upgrade_effect_persists(
    db_session: AsyncSession,
) -> None:
    """offline_efficiency is still boosted after prestige if module_mk1 survived."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.u238 = Decimal("5")
        # Pre-create the surviving upgrade row directly
        from app.db.repositories.player_upgrade import PlayerUpgradeRepository
        await PlayerUpgradeRepository.create(db_session, player.id, "offline_module_mk1")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        await prestige(db_session, p)

    p2 = await PlayerStateRepository.get_by_id(db_session, player.id)
    assert p2 is not None
    # default 0.20 + offline_module_mk1 +0.05 = 0.25
    assert p2.offline_efficiency == pytest.approx(0.25)
