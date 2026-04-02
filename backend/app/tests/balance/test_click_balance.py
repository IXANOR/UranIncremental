"""Balance test: click reward must not replace passive production.

The reward per click must be less than 1% of the hourly energy_drink
production from a single barrel (the cheapest unit).  This ensures that
clicking never dominates over building and running units passively.
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.unit_definition import UnitDefinitionRepository
from app.db.seed import seed
from app.services.click_service import BASE_CLICK_REWARD


@pytest.mark.asyncio
async def test_click_reward_below_1pct_hourly_barrel(db_session: AsyncSession) -> None:
    """BASE_CLICK_REWARD must be < 1% of one barrel's hourly ED production.

    barrel production_rate_per_sec = 0.3 ED/s → 1080 ED/h → 1% = 10.8 ED.
    BASE_CLICK_REWARD must stay below this threshold so clicking cannot
    substitute for passive production.
    """
    async with db_session.begin():
        await seed(db_session)
        barrel = await UnitDefinitionRepository.get_by_id(db_session, "barrel")
        assert barrel is not None

    hourly = barrel.production_rate_per_sec * Decimal("3600")
    threshold = hourly * Decimal("0.01")

    assert BASE_CLICK_REWARD < threshold, (
        f"BASE_CLICK_REWARD ({BASE_CLICK_REWARD}) >= 1% of hourly barrel production "
        f"({threshold:.4f} ED). Reduce BASE_CLICK_REWARD."
    )
