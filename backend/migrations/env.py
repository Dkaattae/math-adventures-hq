"""Alembic environment.

The database URL comes from (in order): a URL set programmatically on the
Alembic config (app.db.run_migrations does this), then $DATABASE_URL.
`target_metadata` is the app's Base.metadata so future `--autogenerate`
runs can diff the models.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the `app` package importable when Alembic runs env.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base  # noqa: E402
import app.db_models  # noqa: E402,F401  (registers tables on Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    from app.db import normalize_database_url

    url = config.get_main_option("sqlalchemy.url")
    if url:
        return normalize_database_url(url)
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        raise RuntimeError("No database URL: set DATABASE_URL or pass one to run_migrations().")
    return normalize_database_url(env_url)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
