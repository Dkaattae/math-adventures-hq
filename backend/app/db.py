"""SQLAlchemy setup. Database URL comes from $DATABASE_URL.

Defaults:
- Tests default to in-memory sqlite (see tests/conftest.py).
- Local dev with docker-compose: postgresql+psycopg://math:math@localhost:5432/math_adventures
"""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://math:math@localhost:5432/math_adventures"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def init_engine(url: str | None = None):
    """(Re)initialize the engine. Called at startup and from tests."""
    global _engine, _SessionLocal
    url = url or get_database_url()
    _engine = create_engine(url, future=True, connect_args=_connect_args(url))
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    # Import models so metadata is populated, then create tables.
    from . import db_models  # noqa: F401

    Base.metadata.create_all(_engine)
    return _engine


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
