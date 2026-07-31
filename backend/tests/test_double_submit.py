"""One quiz, one result — even when two submits overlap.

PROJECT_PLAN §4 flagged this: the router reads `row.submitted`, grades
ten answers, then writes. Those are separate steps, so two submits of
the same quiz can both pass the read and each write a result row and a
leaderboard row — one quiz counted twice on the board, and twice in the
player's history.

The fix is a conditional `UPDATE ... WHERE submitted = false` in
`mark_submitted`, which the database resolves atomically. These tests
drive the interleaving deliberately rather than hoping threads collide:
a competing submit is committed *during* the first request's grading,
which is exactly the window the plain check couldn't cover.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app import storage
from app.db_models import LeaderboardRow, QuizResultRow
from app.models import (
    Difficulty,
    Grade,
    LeaderboardEntry,
    MathType,
    QuizResult,
    Recommendation,
)


def _make_quiz(client, username="Racer", math_type="addition"):
    client.post("/api/users", json={"username": username, "pin": "1234"})
    return client.post(
        "/api/quizzes",
        json={
            "username": username,
            "grade": "3",
            "mathType": math_type,
            "difficulty": "easy",
        },
    ).json()


def _answers(db_session, quiz_id):
    row = storage.get_quiz(db_session, UUID(quiz_id))
    return [str(q.correctAnswer) for q in storage.quiz_questions(row)]


def _counts(db_session, quiz_id):
    results = (
        db_session.query(QuizResultRow).filter(QuizResultRow.quiz_id == UUID(quiz_id)).count()
    )
    board = db_session.query(LeaderboardRow).count()
    return results, board


# ---------- the storage-level guard ----------


def test_claiming_a_quiz_twice_fails_the_second_time(client, db_session):
    quiz = _make_quiz(client)
    quiz_id = UUID(quiz["id"])
    result = QuizResult(
        quizId=quiz_id,
        username="Racer",
        score=10,
        total=10,
        timeUsedSeconds=42,
        badge="🏆",
        results=[],
        submittedAt=datetime.now(timezone.utc),
        recommendation=Recommendation(direction="up", grade=Grade.G4, difficulty=Difficulty.easy),
    )

    assert storage.mark_submitted(db_session, quiz_id, result) is True
    assert storage.mark_submitted(db_session, quiz_id, result) is False
    # The loser wrote nothing.
    assert db_session.query(QuizResultRow).filter(QuizResultRow.quiz_id == quiz_id).count() == 1


def test_claiming_a_quiz_that_does_not_exist_is_a_loss_not_a_crash(client, db_session):
    result = QuizResult(
        quizId=uuid4(),
        username="Ghost",
        score=0,
        total=10,
        timeUsedSeconds=1,
        badge=None,
        results=[],
        submittedAt=datetime.now(timezone.utc),
        recommendation=Recommendation(direction="down", grade=Grade.G2, difficulty=Difficulty.easy),
    )
    assert storage.mark_submitted(db_session, uuid4(), result) is False


# ---------- the race, driven through the API ----------


def _rival_submits(engine, quiz_id, *, username="Racer", score=10, seconds=55):
    """A second worker finishing the same quiz, on its own connection.

    Stands in for a concurrent HTTP request: it does exactly what the
    handler does — claim the quiz, write the result, write the board row.
    (An actual nested request through TestClient deadlocks, and threads
    would only collide by luck; this pins the interleaving down.)
    """
    from sqlalchemy.orm import sessionmaker

    other = sessionmaker(bind=engine, autoflush=False, future=True)()
    try:
        now = datetime.now(timezone.utc)
        result = QuizResult(
            quizId=quiz_id,
            username=username,
            score=score,
            total=10,
            timeUsedSeconds=seconds,
            badge="🏆",
            results=[],
            submittedAt=now,
            recommendation=Recommendation(
                direction="up", grade=Grade.G4, difficulty=Difficulty.easy
            ),
        )
        if not storage.mark_submitted(other, quiz_id, result):
            return False
        storage.add_leaderboard_entry(
            other,
            LeaderboardEntry(
                name=username,
                score=score,
                total=10,
                timeUsedSeconds=seconds,
                time=storage.format_time(seconds),
                badge="🏆",
                mathType=MathType.addition,
                difficulty=Difficulty.easy,
                grade=Grade.G3,
                achievedAt=now,
            ),
        )
        return True
    finally:
        other.close()


def _race_during_grading(monkeypatch, run_rival):
    """Fire `run_rival` once, from inside a submit that has already
    passed its `submitted` check and is part-way through grading."""
    import app.routers.quizzes as quizzes_mod

    real_next_level = quizzes_mod.next_level
    fired = {}

    def race(*args, **kwargs):
        if not fired:
            fired["ran"] = run_rival()
        return real_next_level(*args, **kwargs)

    monkeypatch.setattr(quizzes_mod, "next_level", race)
    return fired


def test_a_submit_that_lands_mid_grading_does_not_double_count(
    client, db_session, engine, monkeypatch
):
    """The interleaving the plain `if row.submitted` check can't catch:
    request A reads submitted=False, and while it grades, request B runs
    to completion. A must lose."""
    quiz = _make_quiz(client)
    answers = _answers(db_session, quiz["id"])
    quiz_id = UUID(quiz["id"])

    fired = _race_during_grading(
        monkeypatch, lambda: _rival_submits(engine, quiz_id, seconds=55)
    )

    first = client.post(
        f"/api/quizzes/{quiz['id']}/submit", json={"answers": answers, "timeUsedSeconds": 40}
    )

    assert fired.get("ran") is True, "the competing submit never landed"
    assert first.status_code == 409, first.text
    assert first.json()["detail"]["code"] == "already_submitted"

    results, board = _counts(db_session, quiz["id"])
    assert results == 1, f"{results} result rows for one quiz"
    assert board == 1, f"{board} leaderboard rows for one quiz"
    # The winner's numbers are the ones that stuck, not a blend of both.
    assert db_session.query(LeaderboardRow).one().time_used_seconds == 55


def test_the_loser_does_not_pollute_history(client, db_session, engine, monkeypatch, signup):
    headers = signup(client, "Racer")
    quiz = _make_quiz(client)
    answers = _answers(db_session, quiz["id"])
    quiz_id = UUID(quiz["id"])

    _race_during_grading(monkeypatch, lambda: _rival_submits(engine, quiz_id, seconds=30))
    client.post(
        f"/api/quizzes/{quiz['id']}/submit", json={"answers": answers, "timeUsedSeconds": 30}
    )

    stats = client.get("/api/users/Racer/stats", headers=headers).json()
    assert stats["totalQuizzes"] == 1, stats
    assert sum(t["quizzes"] for t in stats["byTopic"]) == 1, stats


# ---------- the ordinary, non-racing case still behaves ----------


@pytest.mark.parametrize("second_answers", [None, "wrong"])
def test_plain_double_submit_is_still_a_409(client, db_session, second_answers):
    quiz = _make_quiz(client)
    answers = _answers(db_session, quiz["id"])
    first = client.post(
        f"/api/quizzes/{quiz['id']}/submit", json={"answers": answers, "timeUsedSeconds": 40}
    )
    assert first.status_code == 200
    assert first.json()["score"] == 10

    retry = ["wrong"] * 10 if second_answers else answers
    second = client.post(
        f"/api/quizzes/{quiz['id']}/submit", json={"answers": retry, "timeUsedSeconds": 5}
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "already_submitted"

    results, board = _counts(db_session, quiz["id"])
    assert (results, board) == (1, 1)
