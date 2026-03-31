"""Seed script for static game config: unit and upgrade definitions.

Run once after ``alembic upgrade head``:
    python -m app.db.seed
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.unit import UnitDefinition
from app.db.models.upgrade import UpgradeDefinition
from app.db.session import AsyncSessionLocal

# Seed data stored as plain dicts — ORM instances are created fresh on each
# seed() call to avoid SQLAlchemy identity-map issues across test sessions.
_UNIT_DATA: list[dict] = [  # type: ignore[type-arg]
    # --- Tier 1: produce energy_drink ---
    dict(id="barrel", name="Beczka Energetyka", tier=1,
         base_cost_currency="energy_drink", base_cost_amount=Decimal("15"),
         cost_growth_type="linear_early_exp_late", cost_growth_factor=Decimal("1.15"),
         production_resource="energy_drink", production_rate_per_sec=Decimal("0.1"),
         unlocked_by=None),
    dict(id="mini_reactor", name="Mini Reaktor Uranowy", tier=1,
         base_cost_currency="energy_drink", base_cost_amount=Decimal("100"),
         cost_growth_type="linear_early_exp_late", cost_growth_factor=Decimal("1.15"),
         production_resource="energy_drink", production_rate_per_sec=Decimal("0.5"),
         unlocked_by=None),
    dict(id="isotope_lab", name="Laboratorium Izotopów", tier=1,
         base_cost_currency="energy_drink", base_cost_amount=Decimal("1100"),
         cost_growth_type="linear_early_exp_late", cost_growth_factor=Decimal("1.15"),
         production_resource="energy_drink", production_rate_per_sec=Decimal("4.0"),
         unlocked_by=None),
    dict(id="processing_plant", name="Zakład Przetwórczy", tier=1,
         base_cost_currency="energy_drink", base_cost_amount=Decimal("12000"),
         cost_growth_type="linear_early_exp_late", cost_growth_factor=Decimal("1.15"),
         production_resource="energy_drink", production_rate_per_sec=Decimal("10.0"),
         unlocked_by=None),
    dict(id="uranium_mine", name="Kopalnia Uranu", tier=1,
         base_cost_currency="energy_drink", base_cost_amount=Decimal("130000"),
         cost_growth_type="linear_early_exp_late", cost_growth_factor=Decimal("1.15"),
         production_resource="energy_drink", production_rate_per_sec=Decimal("40.0"),
         unlocked_by=None),
    # --- Tier 2: produce u238, cost energy_drink ---
    dict(id="centrifuge_t2", name="Wirówka Izotopowa", tier=2,
         base_cost_currency="energy_drink", base_cost_amount=Decimal("1000000"),
         cost_growth_type="linear_early_exp_late", cost_growth_factor=Decimal("1.15"),
         production_resource="u238", production_rate_per_sec=Decimal("0.001"),
         unlocked_by=None),
    dict(id="enrichment_facility", name="Zakład Wzbogacania", tier=2,
         base_cost_currency="energy_drink", base_cost_amount=Decimal("10000000"),
         cost_growth_type="linear_early_exp_late", cost_growth_factor=Decimal("1.15"),
         production_resource="u238", production_rate_per_sec=Decimal("0.005"),
         unlocked_by=None),
]

_UPGRADE_DATA: list[dict] = [  # type: ignore[type-arg]
    dict(id="barrel_opt_mk1", name="Optymalizacja Beczki",
         description="Beczki produkują 10% więcej energetyka.",
         tier=1, cost_currency="energy_drink", cost_amount=Decimal("200"),
         effect_type="prod_mult", effect_value=Decimal("1.10"),
         target_unit_id="barrel",
         is_repeatable=False, survives_prestige=False),
    dict(id="reactor_tuning_mk1", name="Strojenie Reaktora",
         description="Mini Reaktory Uranowe produkują 20% więcej.",
         tier=1, cost_currency="energy_drink", cost_amount=Decimal("1000"),
         effect_type="prod_mult", effect_value=Decimal("1.20"),
         target_unit_id="mini_reactor",
         is_repeatable=False, survives_prestige=False),
    dict(id="offline_module_mk1", name="Moduł Offline Mk1",
         description="Zwiększa efektywność produkcji offline o 5%.",
         tier=1, cost_currency="energy_drink", cost_amount=Decimal("500"),
         effect_type="offline_eff_up", effect_value=Decimal("0.05"),
         target_unit_id=None,
         is_repeatable=False, survives_prestige=True),
    dict(id="offline_module_mk2", name="Moduł Offline Mk2",
         description="Zwiększa efektywność produkcji offline o kolejne 10%.",
         tier=1, cost_currency="energy_drink", cost_amount=Decimal("5000"),
         effect_type="offline_eff_up", effect_value=Decimal("0.10"),
         target_unit_id=None,
         is_repeatable=False, survives_prestige=True),
    dict(id="offline_cap_mk1", name="Rozszerzenie Bufora Offline Mk1",
         description="Zwiększa maksymalny czas offline o 2 godziny.",
         tier=1, cost_currency="energy_drink", cost_amount=Decimal("2000"),
         effect_type="offline_cap_up", effect_value=Decimal("7200"),
         target_unit_id=None,
         is_repeatable=False, survives_prestige=True),
    dict(id="offline_cap_mk2", name="Rozszerzenie Bufora Offline Mk2",
         description="Zwiększa maksymalny czas offline o kolejne 4 godziny.",
         tier=1, cost_currency="energy_drink", cost_amount=Decimal("20000"),
         effect_type="offline_cap_up", effect_value=Decimal("14400"),
         target_unit_id=None,
         is_repeatable=False, survives_prestige=True),
]


async def seed(session: AsyncSession) -> None:
    """Insert all static game config rows if they do not already exist.

    Idempotent — safe to run multiple times.

    Args:
        session: Active async database session (caller commits).
    """
    existing_units = set(
        (await session.execute(select(UnitDefinition.id))).scalars().all()
    )
    for data in _UNIT_DATA:
        if data["id"] not in existing_units:
            session.add(UnitDefinition(**data))

    existing_upgrades = set(
        (await session.execute(select(UpgradeDefinition.id))).scalars().all()
    )
    for data in _UPGRADE_DATA:
        if data["id"] not in existing_upgrades:
            session.add(UpgradeDefinition(**data))

    await session.flush()


async def _main() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await seed(session)
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(_main())
