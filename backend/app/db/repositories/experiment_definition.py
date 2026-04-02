"""Data access layer for ExperimentDefinition config rows."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.experiment import ExperimentDefinition


class ExperimentDefinitionRepository:
    """Read-only repository for static experiment definitions."""

    @staticmethod
    async def get_all(session: AsyncSession) -> list[ExperimentDefinition]:
        """Return all experiment definitions ordered by ED cost.

        Args:
            session: Active async database session.

        Returns:
            List of all ExperimentDefinition rows.
        """
        result = await session.execute(
            select(ExperimentDefinition).order_by(ExperimentDefinition.ed_cost)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, experiment_id: str) -> ExperimentDefinition | None:
        """Fetch an experiment definition by its string identifier.

        Args:
            session: Active async database session.
            experiment_id: String primary key of the experiment definition.

        Returns:
            ExperimentDefinition if found, None otherwise.
        """
        return await session.get(ExperimentDefinition, experiment_id)
