"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-15

Baseline schema: users (with pin_hash), quizzes, quiz_results, leaderboard.
Uses the app's portable GUID / UTCDateTime types so the same migration
works on both Postgres and sqlite.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db_models import GUID, UTCDateTime

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("username_lower", sa.String(length=20), nullable=False),
        sa.Column("pin_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("username"),
    )
    op.create_index("ix_users_username_lower", "users", ["username_lower"], unique=True)

    op.create_table(
        "quizzes",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("grade", sa.String(length=2), nullable=False),
        sa.Column("math_type", sa.String(length=20), nullable=False),
        sa.Column("difficulty", sa.String(length=10), nullable=False),
        sa.Column("questions_json", sa.JSON(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=True),
        sa.Column("submitted", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["username"], ["users.username"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "quiz_results",
        sa.Column("quiz_id", GUID(), nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("time_used_seconds", sa.Integer(), nullable=False),
        sa.Column("badge", sa.String(length=8), nullable=True),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("submitted_at", UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"]),
        sa.PrimaryKeyConstraint("quiz_id"),
    )

    op.create_table(
        "leaderboard",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("time_used_seconds", sa.Integer(), nullable=False),
        sa.Column("badge", sa.String(length=8), nullable=True),
        sa.Column("math_type", sa.String(length=20), nullable=True),
        sa.Column("difficulty", sa.String(length=10), nullable=True),
        sa.Column("grade", sa.String(length=2), nullable=True),
        sa.Column("achieved_at", UTCDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leaderboard_name", "leaderboard", ["name"])
    op.create_index("ix_leaderboard_score", "leaderboard", ["score"])
    op.create_index("ix_leaderboard_math_type", "leaderboard", ["math_type"])
    op.create_index("ix_leaderboard_difficulty", "leaderboard", ["difficulty"])
    op.create_index("ix_leaderboard_grade", "leaderboard", ["grade"])


def downgrade() -> None:
    op.drop_table("leaderboard")
    op.drop_table("quiz_results")
    op.drop_table("quizzes")
    op.drop_index("ix_users_username_lower", table_name="users")
    op.drop_table("users")
