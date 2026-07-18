"""pin recovery + login lockout columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16

Adds users.recovery_hash (hashed rescue code for PIN resets) and the
brute-force lockout pair users.failed_attempts / users.locked_until.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db_models import UTCDateTime

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("recovery_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("locked_until", UTCDateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_attempts")
    op.drop_column("users", "recovery_hash")
