"""SQLAlchemy setup. Database URL comes from $DATABASE_URL.

Defaults:
- Tests default to in-memory sqlite (see tests/conftest.py).
- Local dev with docker-compose: postgresql+psycopg://math:math@localhost:5432/math_adventures
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://math:math@localhost:5432/math_adventures"


def get_database_url() -> str:
    return normalize_database_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def normalize_database_url(url: str) -> str:
    """Coerce a hosted Postgres URL to the psycopg-v3 driver.

    Supabase (and Heroku-style platforms) hand out `postgresql://…` or
    `postgres://…`, but SQLAlchemy needs the driver named explicitly.
    So a pasted Supabase connection string Just Works.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def init_engine(url: str | None = None):
    """(Re)initialize the engine and session factory.

    Schema is owned by Alembic (see run_migrations), not create_all — so
    this no longer creates tables. The app runs migrations at startup;
    tests build their own schema in fixtures.
    """
    global _engine, _SessionLocal
    url = url or get_database_url()
    _engine = create_engine(url, future=True, connect_args=_connect_args(url))
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    # Import models so metadata is populated (used by Alembic autogenerate).
    from . import db_models  # noqa: F401

    return _engine


def run_migrations(url: str | None = None) -> None:
    """Apply all Alembic migrations up to head.

    Called at application startup so a fresh database (Supabase, a new
    Railway deploy, local sqlite) gets the full schema, and existing ones
    pick up new columns. Safe to run repeatedly — Alembic no-ops when
    already at head.
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url or get_database_url())
    command.upgrade(cfg, "head")


def get_engine():
    if _engine is None:
        init_engine()
    return _engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    if _SessionLocal is None:
        init_engine()
    assert _SessionLocal is not None
    with _SessionLocal() as session:
        yield session
