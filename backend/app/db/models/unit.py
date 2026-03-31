import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_DECIMAL = Numeric(precision=28, scale=10)


class UnitDefinition(Base):
    """Read-only game config defining a purchasable unit type.

    Loaded from seed data. Must not be modified at runtime in production.
    """

    __tablename__ = "unit_definition"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    tier: Mapped[int]
    base_cost_currency: Mapped[str] = mapped_column(String(32))
    base_cost_amount: Mapped[Decimal] = mapped_column(_DECIMAL)
    cost_growth_type: Mapped[str] = mapped_column(String(32))
    cost_growth_factor: Mapped[Decimal] = mapped_column(_DECIMAL)
    production_resource: Mapped[str] = mapped_column(String(32))
    production_rate_per_sec: Mapped[Decimal] = mapped_column(_DECIMAL)
    unlocked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PlayerUnit(Base):
    """Tracks how many of a given unit a player owns and its current state.

    Composite primary key (player_id, unit_id) — one row per unit type per player.
    """

    __tablename__ = "player_unit"

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("player_state.id", ondelete="CASCADE"), primary_key=True
    )
    unit_id: Mapped[str] = mapped_column(
        ForeignKey("unit_definition.id"), primary_key=True
    )
    amount_owned: Mapped[int] = mapped_column(default=0)
    effective_multiplier: Mapped[Decimal] = mapped_column(
        _DECIMAL, default=Decimal("1.0")
    )
    automation_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    upkeep_energy_per_sec: Mapped[Decimal] = mapped_column(
        _DECIMAL, default=Decimal("0")
    )
