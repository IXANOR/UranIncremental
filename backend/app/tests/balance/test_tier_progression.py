"""Balance tests: tier progression time bounds and currency relevance.

These tests assert that:
- Tier 1 units are reachable within expected time windows from starting state.
- Tier 2 units are NOT accessible before serious tier-1 investment (no runaway
  inflation at tier 2 boundary).
- energy_drink remains the gate currency for all unit purchases, ensuring it
  never becomes irrelevant in late game.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.seed import seed
from app.services.pricing_service import compute_unit_cost

# ---------------------------------------------------------------------------
# T1 reachability: mini_reactor in < 2 min with 10 barrels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t1_mini_reactor_reachable_under_2_minutes(
    db_session: AsyncSession,
) -> None:
    """10 barrels (1 ED/s) can afford the first mini_reactor within 120 seconds.

    Validates the t1 → t1-upgrade path is accessible early without grinding.
    """
    async with db_session.begin():
        await seed(db_session)
        barrel = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        reactor = await UnitDefinitionRepository.get_by_id(db_session, "mini_reactor")
        assert barrel is not None and reactor is not None

    first_reactor_cost = compute_unit_cost(
        reactor.base_cost_amount,
        reactor.cost_growth_factor,
        reactor.cost_growth_type,
        0,
    )
    barrel_production_per_sec = Decimal("10") * barrel.production_rate_per_sec
    seconds_needed = first_reactor_cost / barrel_production_per_sec

    assert seconds_needed <= Decimal("120"), (
        f"mini_reactor unreachable in time: needs {seconds_needed}s with 10 barrels "
        f"(threshold: 120s). T1 progression blocked."
    )


# ---------------------------------------------------------------------------
# T2 anti-runaway-inflation: centrifuge_t2 NOT reachable before 4 minutes of
# even the best t1 production scenario
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t2_centrifuge_not_reachable_under_4_minutes_max_t1(
    db_session: AsyncSession,
) -> None:
    """Even with 100 uranium_mines (best t1 unit, 4 000 ED/s), centrifuge_t2
    requires > 4 minutes of pure production — proving it is safely gated behind
    substantial t1 investment.

    Ensures there is no early shortcut that bypasses the t1 grind.
    """
    async with db_session.begin():
        await seed(db_session)
        mine = await UnitDefinitionRepository.get_by_id(db_session, "uranium_mine")
        centrifuge = await UnitDefinitionRepository.get_by_id(db_session, "centrifuge_t2")
        assert mine is not None and centrifuge is not None

    # 100 uranium_mines is an extremely high t1 build (costs ~100 × 130 000 ED alone)
    peak_t1_production = Decimal("100") * mine.production_rate_per_sec
    centrifuge_cost = compute_unit_cost(
        centrifuge.base_cost_amount,
        centrifuge.cost_growth_factor,
        centrifuge.cost_growth_type,
        0,
    )
    seconds_needed = centrifuge_cost / peak_t1_production
    minutes_needed = seconds_needed / Decimal("60")

    assert minutes_needed >= Decimal("4"), (
        f"Runaway inflation risk: centrifuge_t2 reachable in {minutes_needed:.1f} min "
        f"with 100 uranium_mines (threshold: ≥ 4 min). T2 gate is too cheap."
    )


# ---------------------------------------------------------------------------
# T2 cost currency: energy_drink gates access throughout progression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_units_cost_energy_drink(db_session: AsyncSession) -> None:
    """Every unit definition uses energy_drink as its purchase currency.

    This guarantees that energy_drink remains a progression bottleneck at all
    tiers and never becomes irrelevant in late game.
    """
    async with db_session.begin():
        await seed(db_session)
        all_units = await UnitDefinitionRepository.get_all(db_session)

    non_ed_units = [u for u in all_units if u.base_cost_currency != "energy_drink"]
    assert non_ed_units == [], (
        f"Units with non-ED cost currency found (breaks late-game relevance): "
        f"{[u.id for u in non_ed_units]}"
    )


# ---------------------------------------------------------------------------
# Cost curve: 50th unit is expensive enough to prevent mass-buying
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_barrel_50th_unit_significantly_more_expensive(
    db_session: AsyncSession,
) -> None:
    """The 50th barrel should cost substantially more than the first, preventing
    trivial mass-buying and ensuring production scaling is earned.

    Checks the hybrid pricing curve creates meaningful cost growth.
    """
    async with db_session.begin():
        await seed(db_session)
        barrel = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        assert barrel is not None

    cost_0 = compute_unit_cost(
        barrel.base_cost_amount, barrel.cost_growth_factor, barrel.cost_growth_type, 0
    )
    cost_49 = compute_unit_cost(
        barrel.base_cost_amount, barrel.cost_growth_factor, barrel.cost_growth_type, 49
    )
    ratio = cost_49 / cost_0

    # At n=49 (past crossover) the exponential curve should push cost well above 10×
    assert ratio >= Decimal("10"), (
        f"50th barrel cost ({cost_49}) only {ratio:.1f}× first barrel ({cost_0}). "
        "Pricing curve provides insufficient friction."
    )
