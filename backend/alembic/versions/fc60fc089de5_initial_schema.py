"""initial schema

Revision ID: fc60fc089de5
Revises:
Create Date: 2026-03-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "fc60fc089de5"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DECIMAL = sa.Numeric(precision=28, scale=10)


def upgrade() -> None:
    """Create all Phase 1 tables."""
    op.create_table(
        "player_state",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_online_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prestige_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tech_magic_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offline_efficiency", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("offline_cap_seconds", sa.Integer(), nullable=False, server_default="14400"),
        sa.Column("snapshot_signature", sa.String(256), nullable=False, server_default=""),
    )

    op.create_table(
        "wallet",
        sa.Column(
            "player_id", sa.Uuid(),
            sa.ForeignKey("player_state.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column("energy_drink", _DECIMAL, nullable=False, server_default="50"),
        sa.Column("u238", _DECIMAL, nullable=False, server_default="0"),
        sa.Column("u235", _DECIMAL, nullable=False, server_default="0"),
        sa.Column("u233", _DECIMAL, nullable=False, server_default="0"),
        sa.Column("meta_isotopes", _DECIMAL, nullable=False, server_default="0"),
    )

    op.create_table(
        "unit_definition",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("base_cost_currency", sa.String(32), nullable=False),
        sa.Column("base_cost_amount", _DECIMAL, nullable=False),
        sa.Column("cost_growth_type", sa.String(32), nullable=False),
        sa.Column("cost_growth_factor", _DECIMAL, nullable=False),
        sa.Column("production_resource", sa.String(32), nullable=False),
        sa.Column("production_rate_per_sec", _DECIMAL, nullable=False),
        sa.Column("unlocked_by", sa.String(64), nullable=True),
    )

    op.create_table(
        "player_unit",
        sa.Column(
            "player_id", sa.Uuid(),
            sa.ForeignKey("player_state.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column("unit_id", sa.String(64), sa.ForeignKey("unit_definition.id"), primary_key=True),
        sa.Column("amount_owned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effective_multiplier", _DECIMAL, nullable=False, server_default="1.0"),
        sa.Column("automation_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("upkeep_energy_per_sec", _DECIMAL, nullable=False, server_default="0"),
    )

    op.create_table(
        "upgrade_definition",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("cost_currency", sa.String(32), nullable=False),
        sa.Column("cost_amount", _DECIMAL, nullable=False),
        sa.Column("effect_type", sa.String(32), nullable=False),
        sa.Column("effect_value", _DECIMAL, nullable=False),
        sa.Column("is_repeatable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("survives_prestige", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_table(
        "player_upgrade",
        sa.Column(
            "player_id", sa.Uuid(),
            sa.ForeignKey("player_state.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "upgrade_id", sa.String(64),
            sa.ForeignKey("upgrade_definition.id"), primary_key=True,
        ),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "balance_config",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version_tag", sa.String(64), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("json_blob", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "balance_test_run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("config_version", sa.String(64), nullable=False),
        sa.Column("test_suite_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "event_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "player_id", sa.Uuid(),
            sa.ForeignKey("player_state.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop all Phase 1 tables in reverse dependency order."""
    op.drop_table("event_log")
    op.drop_table("balance_test_run")
    op.drop_table("balance_config")
    op.drop_table("player_upgrade")
    op.drop_table("upgrade_definition")
    op.drop_table("player_unit")
    op.drop_table("unit_definition")
    op.drop_table("wallet")
    op.drop_table("player_state")
