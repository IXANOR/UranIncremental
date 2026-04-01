import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_TZ = DateTime(timezone=True)
_now = lambda: datetime.now(UTC)  # noqa: E731


class BalanceConfig(Base):
    """Versioned game balance configuration blob.

    Only one config can be ``is_active=True`` at a time.
    Configs are read-only in production (``TEST_MODE=false``).
    AI-proposed configs start as ``is_active=False`` and require admin approval.
    """

    __tablename__ = "balance_config"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_tag: Mapped[str] = mapped_column(String(64), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    json_blob: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(_TZ, default=_now)


class BalanceProposal(Base):
    """AI-generated balance proposal awaiting admin review.

    Lifecycle: ``pending`` → ``approved`` / ``rejected`` → ``applied``.
    Only ``approved`` proposals can be applied to the live game config.
    """

    __tablename__ = "balance_proposal"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    changes_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(_TZ, default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(_TZ, nullable=True, default=None)


class BalanceTestRun(Base):
    """Records the result of a balance test suite run against a config version.

    A config can only become active after a run with ``status='passed'``
    and admin approval.
    """

    __tablename__ = "balance_test_run"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    config_version: Mapped[str] = mapped_column(String(64))
    test_suite_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))  # passed | failed
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(_TZ, default=_now)
