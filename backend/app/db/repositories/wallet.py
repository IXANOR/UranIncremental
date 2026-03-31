import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.wallet import Wallet


class WalletRepository:
    """Data access layer for player wallet (currency balances)."""

    @staticmethod
    async def get_by_player(session: AsyncSession, player_id: uuid.UUID) -> Wallet | None:
        """Fetch the wallet for a given player.

        Args:
            session: Active async database session.
            player_id: UUID of the player whose wallet to fetch.

        Returns:
            Wallet if found, None otherwise.
        """
        return await session.get(Wallet, player_id)

    @staticmethod
    async def update(
        session: AsyncSession, wallet: Wallet, **kwargs: Decimal
    ) -> Wallet:
        """Apply currency updates to a wallet.

        Args:
            session: Active async database session.
            wallet: Wallet instance to update.
            **kwargs: Currency field names and their new Decimal values.

        Returns:
            Updated Wallet instance after flush.
        """
        for key, value in kwargs.items():
            setattr(wallet, key, value)
        await session.flush()
        return wallet
