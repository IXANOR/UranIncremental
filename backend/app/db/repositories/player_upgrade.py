import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.upgrade import PlayerUpgrade


class PlayerUpgradeRepository:
    """Data access layer for PlayerUpgrade (upgrades purchased by a player)."""

    @staticmethod
    async def get_by_player(
        session: AsyncSession, player_id: uuid.UUID
    ) -> list[PlayerUpgrade]:
        """Return all upgrade rows for a player.

        Args:
            session: Active async database session.
            player_id: UUID of the player.

        Returns:
            List of PlayerUpgrade rows.
        """
        result = await session.execute(
            select(PlayerUpgrade).where(PlayerUpgrade.player_id == player_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_player_and_upgrade(
        session: AsyncSession, player_id: uuid.UUID, upgrade_id: str
    ) -> PlayerUpgrade | None:
        """Fetch a specific purchased upgrade for a player.

        Args:
            session: Active async database session.
            player_id: UUID of the player.
            upgrade_id: Identifier of the upgrade.

        Returns:
            PlayerUpgrade if purchased, None otherwise.
        """
        return await session.get(PlayerUpgrade, (player_id, upgrade_id))

    @staticmethod
    async def create(
        session: AsyncSession, player_id: uuid.UUID, upgrade_id: str
    ) -> PlayerUpgrade:
        """Record that a player has purchased an upgrade (level 1).

        Args:
            session: Active async database session.
            player_id: UUID of the player.
            upgrade_id: Identifier of the upgrade.

        Returns:
            Newly created PlayerUpgrade instance after flush.
        """
        row = PlayerUpgrade(player_id=player_id, upgrade_id=upgrade_id)
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def increment_level(
        session: AsyncSession, upgrade: PlayerUpgrade
    ) -> PlayerUpgrade:
        """Increment the level of a repeatable upgrade by 1.

        Args:
            session: Active async database session.
            upgrade: PlayerUpgrade instance to increment.

        Returns:
            Updated PlayerUpgrade instance after flush.
        """
        upgrade.level += 1
        await session.flush()
        return upgrade
