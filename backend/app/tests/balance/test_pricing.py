"""Balance tests: pricing curve and unit affordability with default parameters.

Asserts that the economy is accessible — a player with starting balance can
buy the first unit, and production income outpaces cost growth at early tiers.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.player_state import PlayerStateRepository
from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.repositories.wallet import WalletRepository
from app.db.seed import seed
from app.services.economy_service import buy_unit
from app.services.pricing_service import compute_unit_cost


@pytest.mark.asyncio
async def test_first_barrel_affordable_from_start(db_session: AsyncSession) -> None:
    """Starting balance (50 ED) must cover barrel cost (15 ED)."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        wallet = await WalletRepository.get_by_player(db_session, player.id)
        barrel = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        assert wallet is not None and barrel is not None

    first_cost = compute_unit_cost(
        barrel.base_cost_amount, barrel.cost_growth_factor, barrel.cost_growth_type, 0
    )
    assert wallet.energy_drink >= first_cost, (
        f"Starting balance {wallet.energy_drink} < first barrel cost {first_cost}"
    )


@pytest.mark.asyncio
async def test_barrel_25th_unit_still_finite(db_session: AsyncSession) -> None:
    """The 25th barrel (crossover point) should have a finite, reasonable cost."""
    async with db_session.begin():
        await seed(db_session)
        barrel = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        assert barrel is not None

    cost_25 = compute_unit_cost(
        barrel.base_cost_amount, barrel.cost_growth_factor, barrel.cost_growth_type, 25
    )
    # 15 × (1 + 0.15 × 25) = 15 × 4.75 = 71.25 ED — extremely affordable
    assert cost_25 == pytest.approx(Decimal("71.25"), rel=Decimal("0.001"))


@pytest.mark.asyncio
async def test_mini_reactor_reachable_with_10_barrels(db_session: AsyncSession) -> None:
    """10 barrels (1 ED/s) should accumulate mini_reactor cost (100 ED) in ≤ 120 s.

    This checks that the t1 upgrade path is not blocked by excessive cost.
    """
    async with db_session.begin():
        await seed(db_session)
        reactor = await UnitDefinitionRepository.get_by_id(db_session, "mini_reactor")
        assert reactor is not None

    first_reactor_cost = compute_unit_cost(
        reactor.base_cost_amount,
        reactor.cost_growth_factor,
        reactor.cost_growth_type,
        0,
    )
    # 10 barrels × 0.1 ED/s = 1 ED/s; 100 ED → 100 s from zero
    production_per_sec = Decimal("10") * Decimal("0.1")
    time_to_afford = first_reactor_cost / production_per_sec
    assert time_to_afford <= Decimal("120"), (
        f"First mini_reactor takes {time_to_afford}s with 10 barrels — too slow"
    )


@pytest.mark.asyncio
async def test_buy_unit_transaction_reduces_balance(db_session: AsyncSession) -> None:
    """buy_unit() within a session transaction should reduce wallet balance."""
    async with db_session.begin():
        await seed(db_session)
        player = await PlayerStateRepository.create(db_session)
        w = await WalletRepository.get_by_player(db_session, player.id)
        assert w is not None
        w.energy_drink = Decimal("1000")

    async with db_session.begin():
        p = await PlayerStateRepository.get_by_id(db_session, player.id)
        assert p is not None
        result = await buy_unit(db_session, p, "barrel", quantity=5)

    assert result.wallet.energy_drink < Decimal("1000")
    assert result.player_unit.amount_owned == 5
    assert result.total_cost > Decimal("0")
