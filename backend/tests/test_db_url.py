"""DATABASE_URL normalization so hosted Postgres strings work as-is."""
from __future__ import annotations

from app.db import normalize_database_url


def test_supabase_style_postgresql_url_gets_psycopg_driver():
    url = "postgresql://postgres:pw@db.abc.supabase.co:5432/postgres"
    assert normalize_database_url(url) == "postgresql+psycopg://postgres:pw@db.abc.supabase.co:5432/postgres"


def test_bare_postgres_scheme_is_upgraded():
    assert normalize_database_url("postgres://u:p@host:5432/db").startswith("postgresql+psycopg://")


def test_already_qualified_url_is_untouched():
    url = "postgresql+psycopg://u:p@host:5432/db"
    assert normalize_database_url(url) == url


def test_sqlite_url_is_untouched():
    assert normalize_database_url("sqlite:///dev.db") == "sqlite:///dev.db"
