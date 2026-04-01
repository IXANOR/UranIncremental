import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_DECIMAL = Numeric(precision=28, scale=10)


class UpgradeDefinition(Base):
    """Read-only game config defining a purchasable upgrade.

    ``survives_prestige`` marks upgrades that are retained after a soft reset.
    Currently that covers all ``offline_eff_up`` and ``offline_cap_up`` effects.
    """

    __tablename__ = "upgrade_definition"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512))
    tier: Mapped[int]
    cost_currency: Mapped[str] = mapped_column(String(32))
    cost_amount: Mapped[Decimal] = mapped_column(_DECIMAL)
    effect_type: Mapped[str] = mapped_column(String(32))
    effect_value: Mapped[Decimal] = mapped_column(_DECIMAL)
    target_unit_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=False)
    survives_prestige: Mapped[bool] = mapped_column(Boolean, default=False)


class PlayerUpgrade(Base):
    """Records that a player has purchased a specific upgrade.

    Composite primary key (player_id, upgrade_id).
    ``level`` is relevant for repeatable upgrades; always 1 for non-repeatable.
    """

    __tablename__ = "player_upgrade"

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("player_state.id", ondelete="CASCADE"), primary_key=True
    )
    upgrade_id: Mapped[str] = mapped_column(ForeignKey("upgrade_definition.id"), primary_key=True)
    level: Mapped[int] = mapped_column(default=1)
    purchased_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
