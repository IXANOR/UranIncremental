import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


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
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
