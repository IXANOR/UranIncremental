"""Convert all timestamp columns to TIMESTAMPTZ.

SQLite tests were using naive datetimes; PostgreSQL requires TIMESTAMPTZ
when the application sends timezone-aware datetime objects.

Revision ID: a1b2c3d4e5f6
Revises: fc60fc089de5
Create Date: 2026-04-01
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "fc60fc089de5"
branch_labels = None
depends_on = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)

# (table, column) pairs to migrate
_COLUMNS = [
    ("player_state", "created_at"),
    ("player_state", "updated_at"),
    ("player_state", "last_tick_at"),
    ("player_state", "last_online_at"),
    ("event_log", "created_at"),
    ("balance_config", "created_at"),
    ("balance_test_run", "created_at"),
    ("player_upgrade", "purchased_at"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=_TIMESTAMPTZ,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    _TIMESTAMP = sa.DateTime(timezone=False)
    for table, column in _COLUMNS:
        op.alter_column(table, column, type_=_TIMESTAMP)
