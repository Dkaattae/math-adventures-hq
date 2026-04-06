"""Integration test that exercises the repository against a real Postgres.

Runs against the docker-compose Postgres by default. Override with:
    INTEGRATION_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db pytest

Skips automatically if the database is not reachable — so `pytest` stays
green on machines where Postgres isn't running.
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app import storage
from app.db import Base
from app.models import Difficulty, Grade, LeaderboardEntry, MathType
from app.questions import generate_questions

DEFAULT_URL = "postgresql+psycopg://math:math@localhost:5432/math_adventures"
DB_URL = os.environ.get("INTEGRATION_DATABASE_URL", DEFAULT_URL)


def _postgres_available() -> bool:
    try:
        eng = create_engine(DB_URL, future=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except OperationalError:
        return False
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"Postgres not reachable at {DB_URL} — start it with `docker compose up -d postgres`",
)


@pytest.fixture(scope="module")
def pg_engine():
    from app import db_models  # noqa: F401

    eng = create_engine(DB_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def pg_session(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    # Clean slate for each test.
    storage.reset(session)
    yield session
    storage.reset(session)
    session.close()


def test_empty_db_starts_clean(pg_session):
    assert storage.user_exists(pg_session, "Emma") is False
    assert storage.query_leaderboard(pg_session, limit=10) == []


def test_create_user_persists_case_insensitive(pg_session):
    storage.create_user(pg_session, "Alice")
    assert storage.user_exists(pg_session, "alice")
    assert storage.user_exists(pg_session, "ALICE")


def test_full_quiz_flow_persists(pg_session):
    storage.create_user(pg_session, "Taylor")
    quiz_id = uuid4()
    internal = generate_questions(MathType.addition, Difficulty.easy, Grade.G3)
    storage.save_quiz(
        pg_session,
        quiz_id,
        "Taylor",
        Grade.G3,
        MathType.addition,
        Difficulty.easy,
        internal,
    )

    row = storage.get_quiz(pg_session, quiz_id)
    assert row is not None
    assert row.username == "Taylor"
    assert len(row.questions_json) == 10
    loaded = storage.quiz_questions(row)
    assert loaded[0].correctAnswer == internal[0].correctAnswer

    # Add leaderboard entry and verify filter works.
    entry = LeaderboardEntry(
        name="Taylor",
        score=10,
        total=10,
        timeUsedSeconds=75,
        time="1m 15s",
        badge="🏆",
        mathType=MathType.addition,
        difficulty=Difficulty.easy,
        grade=Grade.G3,
        achievedAt=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    storage.add_leaderboard_entry(pg_session, entry)

    top = storage.query_leaderboard(
        pg_session, math_type=MathType.addition, difficulty=Difficulty.easy, grade=Grade.G3, limit=1
    )
    assert top[0].name == "Taylor"
    assert top[0].score == 10


def test_leaderboard_ordering_on_postgres(pg_session):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    for name, score, secs in [("A", 10, 90), ("B", 10, 45), ("C", 8, 30)]:
        storage.add_leaderboard_entry(
            pg_session,
            LeaderboardEntry(
                name=name,
                score=score,
                total=10,
                timeUsedSeconds=secs,
                time=storage.format_time(secs),
                mathType=MathType.addition,
                difficulty=Difficulty.easy,
                grade=Grade.G3,
                achievedAt=now,
            ),
        )
    entries = storage.query_leaderboard(pg_session, limit=10)
    # Score desc, time asc: B(10,45) -> A(10,90) -> C(8,30)
    assert [e.name for e in entries] == ["B", "A", "C"]
