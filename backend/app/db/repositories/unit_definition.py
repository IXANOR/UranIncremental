from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.unit import UnitDefinition


class UnitDefinitionRepository:
    """Read-only data access layer for UnitDefinition config rows."""

    @staticmethod
    async def get_all(session: AsyncSession) -> list[UnitDefinition]:
        """Return all unit definitions ordered by tier and base cost.

        Args:
            session: Active async database session.

        Returns:
            List of all UnitDefinition rows.
        """
        result = await session.execute(
            select(UnitDefinition).order_by(UnitDefinition.tier, UnitDefinition.base_cost_amount)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, unit_id: str) -> UnitDefinition | None:
        """Fetch a unit definition by its string identifier.

        Args:
            session: Active async database session.
            unit_id: String primary key of the unit definition.

        Returns:
            UnitDefinition if found, None otherwise.
        """
        return await session.get(UnitDefinition, unit_id)
