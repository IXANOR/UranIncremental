import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.player_state import PlayerState
from app.db.models.wallet import Wallet


class PlayerStateRepository:
    """Data access layer for PlayerState and its associated Wallet.

    In single-user mode there is always at most one PlayerState row.
    """

    @staticmethod
    async def get_by_id(session: AsyncSession, player_id: uuid.UUID) -> PlayerState | None:
        """Fetch a player state by primary key.

        Args:
            session: Active async database session.
            player_id: UUID of the player to fetch.

        Returns:
            PlayerState if found, None otherwise.
        """
        result = await session.get(PlayerState, player_id)
        return result

    @staticmethod
    async def get_single_player(session: AsyncSession) -> PlayerState | None:
        """Return the one and only player in single-user mode.

        Args:
            session: Active async database session.

        Returns:
            The first PlayerState row found, or None if no player exists yet.
        """
        result = await session.execute(select(PlayerState).limit(1))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession) -> PlayerState:
        """Create a new player with default state and a starting wallet.

        The UUID is generated explicitly before object creation so the Wallet
        foreign key is available immediately (SQLAlchemy defers column defaults
        until INSERT time, not object instantiation time).

        Args:
            session: Active async database session.

        Returns:
            Newly created and flushed PlayerState instance.
        """
        player_id = uuid.uuid4()
        player = PlayerState(id=player_id)
        wallet = Wallet(player_id=player_id)
        session.add(player)
        session.add(wallet)
        await session.flush()
        return player

    @staticmethod
    async def update(session: AsyncSession, player: PlayerState, **kwargs: object) -> PlayerState:
        """Apply field updates to an existing PlayerState.

        Args:
            session: Active async database session.
            player: PlayerState instance to update.
            **kwargs: Field names and their new values.

        Returns:
            Updated PlayerState instance after flush.

        Raises:
            AttributeError: If a key does not correspond to a model field.
        """
        for key, value in kwargs.items():
            setattr(player, key, value)
        await session.flush()
        return player
