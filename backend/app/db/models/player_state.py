import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_TZ = DateTime(timezone=True)
_DECIMAL = Numeric(precision=28, scale=10)
_now = lambda: datetime.now(UTC)  # noqa: E731


class PlayerState(Base):
    """Persistent state for a single player.

    Tracks progression metadata, prestige level, offline parameters,
    click minigame stats, experiment cooldowns, active temporary effects,
    and the HMAC snapshot signature used to detect tampering.
    """

    __tablename__ = "player_state"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(_TZ, default=_now)
    updated_at: Mapped[datetime] = mapped_column(_TZ, default=_now, onupdate=_now)
    version: Mapped[int] = mapped_column(default=1)
    last_tick_at: Mapped[datetime] = mapped_column(_TZ, default=_now)
    last_online_at: Mapped[datetime] = mapped_column(_TZ, default=_now)
    prestige_count: Mapped[int] = mapped_column(default=0)
    tech_magic_level: Mapped[int] = mapped_column(default=0)
    offline_efficiency: Mapped[float] = mapped_column(default=0.20)
    offline_cap_seconds: Mapped[int] = mapped_column(default=14400)  # 4h
    snapshot_signature: Mapped[str] = mapped_column(String(256), default="")
    click_count: Mapped[int] = mapped_column(default=0)
    total_click_gains: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("0"))
    # Experiment cooldowns: {experiment_id: ISO-timestamp-string}
    experiment_cooldowns: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Temporary production multiplier from experiments
    temp_prod_multiplier: Mapped[Decimal] = mapped_column(_DECIMAL, default=Decimal("1"))
    temp_prod_multiplier_expires_at: Mapped[datetime | None] = mapped_column(
        _TZ, nullable=True, default=None
    )
