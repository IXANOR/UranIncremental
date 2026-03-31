import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_DECIMAL = Numeric(precision=28, scale=10)


class Wallet(Base):
    """Stores all currency balances for a player.

    All amounts are stored as high-precision decimals to avoid
    floating-point drift over long idle sessions.
    """

    __tablename__ = "wallet"

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("player_state.id", ondelete="CASCADE"), primary_key=True
    )
    energy_drink: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("50"))
    u238: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("0"))
    u235: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("0"))
    u233: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("0"))
    meta_isotopes: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("0"))
