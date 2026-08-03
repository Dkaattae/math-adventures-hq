"""The shared adaptive-level ladder (single source of truth)."""
from __future__ import annotations

import pytest

from app.leveling import LevelDirection, next_level
from app.models import Difficulty, Grade, MathType


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


# ---------- a topic's own floor (PROJECT_PLAN §2.1) ----------
#
# The ladder used to step the grade down without knowing which topic it
# was stepping down *in*, so a struggling grade-4 percentages player was
# told to "try grade 3" — a level percentages isn't written for, and one
# where the number ranges are too small to build ten different
# questions, so the quiz repeated itself.


@pytest.mark.parametrize(
    "math_type,entry",
    [
        (MathType.percentages, Grade.G4),
        (MathType.division, Grade.G3),
        (MathType.multiplication, Grade.G2),
        (MathType.money_time, Grade.G1),
    ],
    ids=lambda v: getattr(v, "value", v),
)
def test_a_weak_score_never_drops_below_the_topics_entry_grade(math_type, entry):
    grade, difficulty, direction = next_level(entry, Difficulty.easy, 3, math_type)
    assert grade == entry, f"{math_type.value} dropped to grade {grade.value}"
    assert difficulty == Difficulty.easy
    # The intent is still "this was too hard", even though nothing moved.
    assert direction == LevelDirection.down


def test_without_a_topic_the_ladder_is_unchanged():
    """Callers that don't know the topic keep the old behaviour."""
    assert next_level(Grade.G2, Difficulty.easy, 3) == (
        Grade.G1, Difficulty.hard, LevelDirection.down,
    )


def test_difficulty_still_steps_down_before_the_grade_does():
    """The floor only blocks the grade step; going hard → medium → easy
    within the entry grade is still the right first move."""
    assert next_level(Grade.G4, Difficulty.hard, 2, MathType.percentages) == (
        Grade.G4, Difficulty.medium, LevelDirection.down,
    )
    assert next_level(Grade.G4, Difficulty.medium, 2, MathType.percentages) == (
        Grade.G4, Difficulty.easy, LevelDirection.down,
    )


def test_a_topic_offered_everywhere_still_reaches_kindergarten():
    assert next_level(Grade.G1, Difficulty.easy, 1, MathType.addition) == (
        Grade.K, Difficulty.hard, LevelDirection.down,
    )


def test_stepping_up_is_not_affected_by_the_floor():
    assert next_level(Grade.G4, Difficulty.hard, 10, MathType.percentages) == (
        Grade.G5, Difficulty.easy, LevelDirection.up,
    )


def test_the_recommendation_after_a_bad_quiz_is_a_level_that_exists(client, db_session):
    """End to end: submit a weak percentages quiz and the level it
    suggests must be one the topic is actually offered at."""
    from uuid import UUID

    from app import storage

    client.post("/api/users", json={"username": "Percy", "pin": "1234"})
    quiz = client.post(
        "/api/quizzes",
        json={
            "username": "Percy",
            "grade": "4",
            "mathType": "percentages",
            "difficulty": "easy",
        },
    ).json()
    result = client.post(
        f"/api/quizzes/{quiz['id']}/submit",
        json={"answers": ["nope"] * 10, "timeUsedSeconds": 60},
    ).json()

    assert result["score"] == 0
    rec = result["recommendation"]
    assert rec["grade"] == "4", rec
    assert rec["direction"] == "down"
