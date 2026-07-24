"""login sessions

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-20

Adds the sessions table backing bearer-token auth on the per-player
endpoints (stats, suggested-level). Only the SHA-256 of each token is
stored.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db_models import UTCDateTime

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=True),
        sa.Column("expires_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["username"], ["users.username"]),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_sessions_username", "sessions", ["username"])


def downgrade() -> None:
    op.drop_index("ix_sessions_username", table_name="sessions")
    op.drop_table("sessions")
