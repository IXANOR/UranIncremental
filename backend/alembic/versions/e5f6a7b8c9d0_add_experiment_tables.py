"""Add experiment_definition table and experiment columns to player_state.

Task 14 - Sezonowy Sink: Eksperyment Jądrowy.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-02
"""

import sqlalchemy as sa

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

_DECIMAL = sa.Numeric(precision=28, scale=10)
_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "experiment_definition",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("ed_cost", _DECIMAL, nullable=False, server_default="0"),
        sa.Column("u238_cost", _DECIMAL, nullable=False, server_default="0"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("outcomes", sa.JSON(), nullable=False),
    )

    op.add_column(
        "player_state",
        sa.Column(
            "experiment_cooldowns",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "player_state",
        sa.Column(
            "temp_prod_multiplier",
            _DECIMAL,
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "player_state",
        sa.Column("temp_prod_multiplier_expires_at", _TZ, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("player_state", "temp_prod_multiplier_expires_at")
    op.drop_column("player_state", "temp_prod_multiplier")
    op.drop_column("player_state", "experiment_cooldowns")
    op.drop_table("experiment_definition")
