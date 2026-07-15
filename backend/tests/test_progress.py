"""Per-user progress stats and history-based level suggestion."""
from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app import storage


def _play(client, db_session, username, math_type, grade, difficulty, correct_count, time_used=60):
    """Run one quiz for `username`, answering `correct_count` questions right."""
    client.post("/api/users", json={"username": username, "pin": "1234"})
    quiz = client.post(
        "/api/quizzes",
        json={"username": username, "grade": grade, "mathType": math_type, "difficulty": difficulty},
    ).json()
    row = storage.get_quiz(db_session, UUID(quiz["id"]))
    row.created_at = row.created_at - timedelta(seconds=time_used + 30)
    db_session.commit()
    correct = [str(q.correctAnswer) for q in storage.quiz_questions(row)]
    answers = [correct[i] if i < correct_count else "definitely-wrong" for i in range(10)]
    client.post(f"/api/quizzes/{quiz['id']}/submit", json={"answers": answers, "timeUsedSeconds": time_used})
    return quiz


def test_stats_empty_for_new_player(client):
    r = client.get("/api/users/NoQuizzes/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["totalQuizzes"] == 0
    assert body["averageScore"] == 0
    assert body["byTopic"] == []
    assert body["recent"] == []


def test_stats_aggregate_across_quizzes(client, db_session):
    _play(client, db_session, "Ada", "addition", "2", "easy", correct_count=10)
    _play(client, db_session, "Ada", "addition", "2", "easy", correct_count=6)
    _play(client, db_session, "Ada", "geometry", "2", "easy", correct_count=8)

    body = client.get("/api/users/Ada/stats").json()
    assert body["totalQuizzes"] == 3
    assert body["bestScore"] == 10
    assert body["averageScore"] == round((10 + 6 + 8) / 3, 1)

    topics = {t["mathType"]: t for t in body["byTopic"]}
    assert topics["addition"]["quizzes"] == 2
    assert topics["addition"]["averageScore"] == 8.0
    assert topics["addition"]["bestScore"] == 10
    assert topics["geometry"]["quizzes"] == 1
    assert len(body["recent"]) == 3


def test_stats_recent_is_capped_at_five_and_newest_first(client, db_session):
    for i in range(7):
        _play(client, db_session, "Bob", "addition", "1", "easy", correct_count=i, time_used=10 + i)
    body = client.get("/api/users/Bob/stats").json()
    assert body["totalQuizzes"] == 7
    assert len(body["recent"]) == 5


def test_stats_username_is_case_insensitive(client, db_session):
    _play(client, db_session, "Cara", "addition", "1", "easy", correct_count=5)
    assert client.get("/api/users/CARA/stats").json()["totalQuizzes"] == 1


def test_suggested_level_none_without_history(client):
    r = client.get("/api/users/Nobody/suggested-level")
    assert r.status_code == 200
    assert r.json() is None


def test_suggested_level_bumps_difficulty_after_high_scores(client, db_session):
    _play(client, db_session, "Deb", "addition", "3", "easy", correct_count=10)
    _play(client, db_session, "Deb", "addition", "3", "easy", correct_count=9)
    body = client.get("/api/users/Deb/suggested-level").json()
    assert body["grade"] == "3"
    assert body["difficulty"] == "medium"


def test_suggested_level_eases_down_after_low_scores(client, db_session):
    _play(client, db_session, "Eli", "addition", "4", "hard", correct_count=2)
    body = client.get("/api/users/Eli/suggested-level").json()
    assert body["grade"] == "4"
    assert body["difficulty"] == "medium"


def test_suggested_level_holds_for_middling_scores(client, db_session):
    _play(client, db_session, "Fay", "addition", "2", "medium", correct_count=6)
    body = client.get("/api/users/Fay/suggested-level").json()
    assert body["grade"] == "2"
    assert body["difficulty"] == "medium"
