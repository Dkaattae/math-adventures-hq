"""The shared adaptive-level ladder (single source of truth)."""
from __future__ import annotations

from app.leveling import LevelDirection, next_level
from app.models import Difficulty, Grade


def test_high_score_bumps_difficulty_within_grade():
    g, d, direction = next_level(Grade.G3, Difficulty.easy, 9)
    assert (g, d) == (Grade.G3, Difficulty.medium)
    assert direction is LevelDirection.up


def test_acing_hard_moves_up_a_grade_at_easy():
    g, d, direction = next_level(Grade.G3, Difficulty.hard, 10)
    assert (g, d) == (Grade.G4, Difficulty.easy)
    assert direction is LevelDirection.up


def test_ceiling_holds_but_still_reads_as_up():
    g, d, direction = next_level(Grade.G5, Difficulty.hard, 10)
    assert (g, d) == (Grade.G5, Difficulty.hard)
    assert direction is LevelDirection.up


def test_low_score_eases_difficulty():
    g, d, direction = next_level(Grade.G4, Difficulty.hard, 3)
    assert (g, d) == (Grade.G4, Difficulty.medium)
    assert direction is LevelDirection.down


def test_low_score_at_easy_drops_a_grade_to_hard():
    g, d, direction = next_level(Grade.G3, Difficulty.easy, 2)
    assert (g, d) == (Grade.G2, Difficulty.hard)
    assert direction is LevelDirection.down


def test_floor_holds_but_still_reads_as_down():
    g, d, direction = next_level(Grade.K, Difficulty.easy, 1)
    assert (g, d) == (Grade.K, Difficulty.easy)
    assert direction is LevelDirection.down


def test_middling_score_holds_steady():
    g, d, direction = next_level(Grade.G2, Difficulty.medium, 6)
    assert (g, d) == (Grade.G2, Difficulty.medium)
    assert direction is LevelDirection.steady


def test_submit_response_includes_recommendation(client, db_session):
    from uuid import UUID
    from app import storage

    client.post("/api/users", json={"username": "Rec", "pin": "1234"})
    quiz = client.post(
        "/api/quizzes",
        json={"username": "Rec", "grade": "3", "mathType": "addition", "difficulty": "easy"},
    ).json()
    row = storage.get_quiz(db_session, UUID(quiz["id"]))
    answers = [str(q.correctAnswer) for q in storage.quiz_questions(row)]
    result = client.post(
        f"/api/quizzes/{quiz['id']}/submit", json={"answers": answers, "timeUsedSeconds": 30}
    ).json()

    assert result["score"] == 10
    rec = result["recommendation"]
    assert rec["direction"] == "up"
    assert (rec["grade"], rec["difficulty"]) == ("3", "medium")
