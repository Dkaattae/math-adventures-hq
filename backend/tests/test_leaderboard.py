from datetime import timedelta
from uuid import UUID

from app import storage


def _run_quiz(
    client, db_session, username, math_type="geometry", time_used=60, correct=True
):
    client.post("/api/users", json={"username": username, "pin": "1234"})
    quiz = client.post(
        "/api/quizzes",
        json={
            "username": username,
            "grade": "3",
            "mathType": math_type,
            "difficulty": "easy",
        },
    ).json()
    row = storage.get_quiz(db_session, UUID(quiz["id"]))
    # The server clamps reported time to the created->submitted window,
    # so backdate creation far enough for the claimed time to be real.
    row.created_at = row.created_at - timedelta(seconds=time_used + 30)
    db_session.commit()
    if correct:
        answers = [str(q.correctAnswer) for q in storage.quiz_questions(row)]
    else:
        answers = ["wrong"] * 10
    client.post(
        f"/api/quizzes/{quiz['id']}/submit",
        json={"answers": answers, "timeUsedSeconds": time_used},
    )
    return quiz


def test_leaderboard_empty_by_default(client):
    r = client.get("/api/leaderboard")
    assert r.status_code == 200
    assert r.json() == []


def test_leaderboard_includes_new_submission(client, db_session):
    _run_quiz(client, db_session, "Taylor", time_used=60, correct=True)
    r = client.get("/api/leaderboard")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "Taylor"
    assert body[0]["score"] == 10
    assert body[0]["time"] == "1m 00s"
    assert body[0]["mathType"] == "geometry"


def test_leaderboard_sorted_by_score_then_time(client, db_session):
    _run_quiz(client, db_session, "Alice", time_used=90, correct=True)   # score 10, 90s
    _run_quiz(client, db_session, "Bob", time_used=30, correct=False)    # score 0, 30s
    _run_quiz(client, db_session, "Carol", time_used=45, correct=True)   # score 10, 45s
    body = client.get("/api/leaderboard").json()
    names = [e["name"] for e in body]
    # Score desc, then time asc: Carol (10,45) -> Alice (10,90) -> Bob (0,30)
    assert names == ["Carol", "Alice", "Bob"]


def test_leaderboard_limit(client, db_session):
    for name in ["A", "B", "C"]:
        _run_quiz(client, db_session, name, correct=True)
    r = client.get("/api/leaderboard", params={"limit": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_leaderboard_filter_by_math_type(client, db_session):
    _run_quiz(client, db_session, "Geo", math_type="geometry", correct=True)
    _run_quiz(client, db_session, "Addy", math_type="addition", correct=False)
    r = client.get("/api/leaderboard", params={"mathType": "geometry"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "Geo"


def test_leaderboard_limit_validation(client):
    r = client.get("/api/leaderboard", params={"limit": 0})
    assert r.status_code == 422
