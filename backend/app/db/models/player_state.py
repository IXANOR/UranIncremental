import uuid
from datetime import UTC, datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlayerState(Base):
    """Persistent state for a single player.

    Tracks progression metadata, prestige level, offline parameters,
    and the HMAC snapshot signature used to detect tampering.
    """

    __tablename__ = "player_state"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    version: Mapped[int] = mapped_column(default=1)
    last_tick_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    last_online_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    prestige_count: Mapped[int] = mapped_column(default=0)
    tech_magic_level: Mapped[int] = mapped_column(default=0)
    offline_efficiency: Mapped[float] = mapped_column(default=0.20)
    offline_cap_seconds: Mapped[int] = mapped_column(default=14400)  # 4h
    snapshot_signature: Mapped[str] = mapped_column(String(256), default="")
