"""Add click_count and total_click_gains to player_state.

Supports the click minigame (Task 13): tracks per-player click statistics.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-02
"""

import sqlalchemy as sa

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

_DECIMAL = sa.Numeric(precision=28, scale=10)


def upgrade() -> None:
    op.add_column(
        "player_state",
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "player_state",
        sa.Column("total_click_gains", _DECIMAL, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("player_state", "total_click_gains")
    op.drop_column("player_state", "click_count")
