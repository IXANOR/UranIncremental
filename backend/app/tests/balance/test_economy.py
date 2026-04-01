"""Balance tests: economy stability with default starting parameters.

These tests simulate basic game progression and assert that the economy
never reaches a deadlock (player always has a path forward).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.seed import seed
from app.services.game_loop_service import tick


@pytest.mark.asyncio
async def test_starting_balance_can_afford_first_unit(db_session: AsyncSession) -> None:
    """Player should be able to buy the cheapest unit with the starting balance."""
    async with db_session.begin():
        await seed(db_session)

    async with db_session.begin():
        cheapest = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        assert cheapest is not None

    # Starting balance is 50 ED; barrel costs 15 ED
    assert Decimal("50") >= cheapest.base_cost_amount, (
        "Starting balance too low to buy first unit — economy deadlock risk"
    )


@pytest.mark.asyncio
async def test_single_barrel_produces_positive_output(db_session: AsyncSession) -> None:
    """One barrel over 60 s should produce a measurable, positive amount."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        player.last_tick_at = datetime.now(UTC) - timedelta(seconds=60)
        player.last_online_at = datetime.now(UTC)

        from app.db.repositories.player_unit import PlayerUnitRepository

        await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=1)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p)

    # 1 barrel × 0.3 ED/s × 60s = 18 ED; must be > 0 with no multiplier overhead
    gains = result.gains.get("energy_drink", Decimal("0"))
    assert gains > Decimal("0"), "Single barrel must produce positive output"
    assert gains == pytest.approx(Decimal("18"), rel=Decimal("0.01"))


@pytest.mark.asyncio
async def test_no_deadlock_after_offline_tick(db_session: AsyncSession) -> None:
    """After maximum offline cap, energy_drink balance should still be positive."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        # Simulate returning after full 4h offline cap
        player.last_tick_at = datetime.now(UTC) - timedelta(hours=8)
        player.last_online_at = datetime.now(UTC) - timedelta(hours=8)

        from app.db.repositories.player_unit import PlayerUnitRepository

        await PlayerUnitRepository.upsert(db_session, player.id, "barrel", amount_owned=5)

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await tick(db_session, p, force_offline=True)

    assert result.wallet.energy_drink > Decimal("0"), (
        "Economy deadlock: energy_drink depleted after offline tick"
    )
    assert result.cap_applied, "Cap should have been applied for 8h offline period"
