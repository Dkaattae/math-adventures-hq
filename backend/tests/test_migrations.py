"""Alembic migrations build the full current schema."""
from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.db import run_migrations


def test_migrations_create_full_schema(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    run_migrations(url)

    eng = create_engine(url)
    tables = set(inspect(eng).get_table_names())
    assert {"users", "quizzes", "quiz_results", "leaderboard", "alembic_version"} <= tables

    # The pin_hash column that plain create_all wouldn't have added to an
    # existing DB is present in the baseline migration.
    user_cols = {c["name"] for c in inspect(eng).get_columns("users")}
    assert "pin_hash" in user_cols

    lb_indexes = {ix["name"] for ix in inspect(eng).get_indexes("leaderboard")}
    assert "ix_leaderboard_math_type" in lb_indexes
    eng.dispose()


def test_migrations_are_idempotent(tmp_path):
    url = f"sqlite:///{tmp_path / 'twice.db'}"
    run_migrations(url)
    run_migrations(url)  # already at head → no-op, must not raise


def test_schema_matches_models(tmp_path):
    """Every table the ORM declares should exist after migrating."""
    from app.db import Base
    import app.db_models  # noqa: F401

    url = f"sqlite:///{tmp_path / 'compare.db'}"
    run_migrations(url)
    eng = create_engine(url)
    migrated = set(inspect(eng).get_table_names())
    for table in Base.metadata.tables:
        assert table in migrated, f"model table {table!r} missing from migrations"
    eng.dispose()
