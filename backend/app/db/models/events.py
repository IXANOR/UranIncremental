import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_TZ = DateTime(timezone=True)
_now = lambda: datetime.now(UTC)  # noqa: E731


class EventLog(Base):
    """Append-only audit log for significant game events.

    Used for delta anomaly detection, prestige history, and error tracking.
    Never modified after insert.
    """

    __tablename__ = "event_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("player_state.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(_TZ, default=_now)
