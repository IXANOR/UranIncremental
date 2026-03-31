from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.upgrade import UpgradeDefinition


class UpgradeDefinitionRepository:
    """Read-only data access layer for UpgradeDefinition config rows."""

    @staticmethod
    async def get_all(session: AsyncSession) -> list[UpgradeDefinition]:
        """Return all upgrade definitions ordered by tier and cost.

        Args:
            session: Active async database session.

        Returns:
            List of all UpgradeDefinition rows.
        """
        result = await session.execute(
            select(UpgradeDefinition).order_by(
                UpgradeDefinition.tier, UpgradeDefinition.cost_amount
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(
        session: AsyncSession, upgrade_id: str
    ) -> UpgradeDefinition | None:
        """Fetch an upgrade definition by its string identifier.

        Args:
            session: Active async database session.
            upgrade_id: String primary key of the upgrade definition.

        Returns:
            UpgradeDefinition if found, None otherwise.
        """
        return await session.get(UpgradeDefinition, upgrade_id)
