import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_TZ = DateTime(timezone=True)
_now = lambda: datetime.now(UTC)  # noqa: E731


class PlayerState(Base):
    """Persistent state for a single player.

    Tracks progression metadata, prestige level, offline parameters,
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
