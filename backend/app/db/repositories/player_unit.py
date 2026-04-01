import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.unit import PlayerUnit


class PlayerUnitRepository:
    """Data access layer for PlayerUnit (units owned by a player)."""

    @staticmethod
    async def get_by_player(session: AsyncSession, player_id: uuid.UUID) -> list[PlayerUnit]:
        """Return all unit rows for a player.

        Args:
            session: Active async database session.
            player_id: UUID of the player.

        Returns:
            List of PlayerUnit rows (may be empty if no units purchased yet).
        """
        result = await session.execute(select(PlayerUnit).where(PlayerUnit.player_id == player_id))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_player_and_unit(
        session: AsyncSession, player_id: uuid.UUID, unit_id: str
    ) -> PlayerUnit | None:
        """Fetch a specific unit row for a player.

        Args:
            session: Active async database session.
            player_id: UUID of the player.
            unit_id: Identifier of the unit type.

        Returns:
            PlayerUnit if the player owns at least one of this unit, None otherwise.
        """
        return await session.get(PlayerUnit, (player_id, unit_id))

    @staticmethod
    async def upsert(
        session: AsyncSession, player_id: uuid.UUID, unit_id: str, **kwargs: object
    ) -> PlayerUnit:
        """Create a PlayerUnit row if it doesn't exist, then apply field updates.

        Args:
            session: Active async database session.
            player_id: UUID of the player.
            unit_id: Identifier of the unit type.
            **kwargs: Field names and values to set on the row.

        Returns:
            Created or updated PlayerUnit instance after flush.
        """
        row = await session.get(PlayerUnit, (player_id, unit_id))
        if row is None:
            row = PlayerUnit(player_id=player_id, unit_id=unit_id)
            session.add(row)
        for key, value in kwargs.items():
            setattr(row, key, value)
        await session.flush()
        return row
