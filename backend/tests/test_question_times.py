"""The per-question clock: the table, and the numbers it produces.

Timers used to be a formula buried in `questions.py` — 15 seconds plus a
word count — with no way to say "word problems need longer" without
editing logic. They now live in `app/question_times.py` as a table keyed
by topic, grade and difficulty, and this file is what stops a tuning
edit from quietly breaking something:

- the table covers every topic, so a new one can't inherit a default
  nobody chose;
- the two numbers that were reported as too fast (word problems, and
  comparison from grade 3 up) are pinned;
- the budgets are checked *through the API*, because a table the
  endpoint doesn't read is just a document;
- and the arithmetic that never needed more time still gets 15.
"""
from __future__ import annotations

import random
from uuid import UUID

import pytest

from app import storage
from app.models import Difficulty, Grade, MathType
from app.question_times import (
    DEFAULT_BASE,
    MAXIMUM,
    MINIMUM,
    SECONDS_PER_HEAVY_OP,
    TOPICS,
    question_seconds,
)
from app.questions import generate_questions, min_grade_for_type

GRADES = list(Grade)
DIFFICULTIES = list(Difficulty)
SHORT = "7 + 5 = ?"


# ---------- the table is complete and sane ----------


def test_every_topic_has_an_entry():
    """A topic missing from the table would silently fall back to the
    default — findable only by a kid running out of time."""
    assert set(TOPICS) == set(MathType)


@pytest.mark.parametrize("math_type", list(MathType), ids=lambda t: t.value)
def test_every_entry_is_well_formed(math_type):
    entry = TOPICS[math_type]
    assert set(entry) <= {"base", "by_grade", "by_difficulty"}, entry
    assert isinstance(entry.get("base", DEFAULT_BASE), int)
    for grade_key, seconds in (entry.get("by_grade") or {}).items():
        assert grade_key in {g.value for g in Grade}, grade_key
        assert MINIMUM <= seconds <= MAXIMUM, (grade_key, seconds)
    for difficulty_key, delta in (entry.get("by_difficulty") or {}).items():
        assert difficulty_key in {d.value for d in Difficulty}, difficulty_key
        assert isinstance(delta, int)


@pytest.mark.parametrize("math_type", list(MathType), ids=lambda t: t.value)
def test_every_level_lands_in_a_playable_range(math_type):
    """No combination of table and bonuses can produce a clock that's
    unusable at either end."""
    for grade in GRADES:
        for difficulty in DIFFICULTIES:
            seconds = question_seconds(SHORT, math_type, difficulty, grade)
            assert MINIMUM <= seconds <= MAXIMUM, (math_type, grade, difficulty, seconds)


def test_a_runaway_question_is_still_capped():
    assert question_seconds(" ".join(["word"] * 5000), MathType.word_problems) == MAXIMUM


# ---------- the numbers that were reported as too fast ----------


@pytest.mark.parametrize("grade", GRADES, ids=lambda g: g.value)
@pytest.mark.parametrize("difficulty", DIFFICULTIES, ids=lambda d: d.value)
def test_word_problems_get_at_least_thirty_seconds(grade, difficulty):
    """Reported in play: 15s wasn't enough to read the scene, never mind
    solve it. 30 is the floor at every level; longer scenes earn more."""
    assert question_seconds(SHORT, MathType.word_problems, difficulty, grade) >= 30


@pytest.mark.parametrize("grade", [Grade.G3, Grade.G4, Grade.G5], ids=lambda g: g.value)
@pytest.mark.parametrize("difficulty", DIFFICULTIES, ids=lambda d: d.value)
def test_comparison_gets_at_least_thirty_seconds_from_grade_three(grade, difficulty):
    """From grade 3 a comparison stops being "which number is bigger" and
    becomes "work out both sides, then compare"."""
    assert question_seconds(SHORT, MathType.comparison, difficulty, grade) >= 30


@pytest.mark.parametrize("grade", [Grade.K, Grade.G1, Grade.G2], ids=lambda g: g.value)
def test_comparison_below_grade_three_is_unchanged(grade):
    """K-2 compare bare numbers; the extra time is for the expressions."""
    assert question_seconds(SHORT, MathType.comparison, Difficulty.easy, grade) == 15


@pytest.mark.parametrize(
    "math_type",
    [
        MathType.addition,
        MathType.subtraction,
        MathType.multiplication,
        MathType.division,
        MathType.algebra,
        MathType.fractions,
        MathType.order_of_operations,
        MathType.decimals,
    ],
    ids=lambda t: t.value,
)
def test_one_line_arithmetic_still_gets_fifteen_seconds(math_type):
    """This change was meant to lengthen two topics, not all of them."""
    for grade in GRADES:
        for difficulty in DIFFICULTIES:
            assert question_seconds(SHORT, math_type, difficulty, grade) == 15


# ---------- the bonuses stack on top of the table ----------


def test_a_long_scene_earns_more_than_the_base():
    short = question_seconds(SHORT, MathType.word_problems, Difficulty.easy, Grade.G5)
    long_scene = question_seconds(
        " ".join(["word"] * 60), MathType.word_problems, Difficulty.easy, Grade.G5
    )
    assert long_scene == short + 35, (short, long_scene)


def test_powers_and_factorials_buy_their_own_time():
    plain = question_seconds(
        "Write <, > or = in the blank:\n\n14 + 63 _ 49 + 19",
        MathType.comparison,
        Difficulty.hard,
        Grade.G5,
    )
    heavy = question_seconds(
        "Write <, > or = in the blank:\n\n9^4 _ 7!",
        MathType.comparison,
        Difficulty.hard,
        Grade.G5,
    )
    assert heavy == plain + 2 * SECONDS_PER_HEAVY_OP


def test_a_reminder_line_is_reading_not_work():
    with_reminder = question_seconds(
        "Reminder: 4^3 means 4 × 4 × 4.\n\nWrite <, > or = in the blank:\n\n5^2 _ 3^6",
        MathType.comparison,
        Difficulty.hard,
        Grade.G5,
    )
    without = question_seconds(
        "Write <, > or = in the blank:\n\n5^2 _ 3^6",
        MathType.comparison,
        Difficulty.hard,
        Grade.G5,
    )
    assert with_reminder - without < SECONDS_PER_HEAVY_OP


def test_an_unknown_level_still_gets_a_budget():
    """Old stored quizzes carry no topic; they must not end up on a
    zero-second clock."""
    assert question_seconds(SHORT) == DEFAULT_BASE
    assert question_seconds(SHORT, None, None, None) == DEFAULT_BASE


# ---------- what the API actually serves ----------


def _quiz(client, math_type, grade, difficulty=Difficulty.medium):
    client.post("/api/users", json={"username": "Tick", "pin": "1234"})
    r = client.post(
        "/api/quizzes",
        json={
            "username": "Tick",
            "grade": grade.value,
            "mathType": math_type.value,
            "difficulty": difficulty.value,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_the_api_serves_word_problem_budgets_from_the_table(client):
    body = _quiz(client, MathType.word_problems, Grade.G3)
    for q in body["questions"]:
        assert q["timeLimitSeconds"] >= 30, q


def test_the_api_serves_comparison_budgets_from_the_table(client):
    at_grade_four = _quiz(client, MathType.comparison, Grade.G4)
    for q in at_grade_four["questions"]:
        assert q["timeLimitSeconds"] >= 30, q

    at_grade_one = _quiz(client, MathType.comparison, Grade.G1, Difficulty.easy)
    for q in at_grade_one["questions"]:
        assert q["timeLimitSeconds"] == 15, q


def test_a_word_problem_inside_a_mixed_quiz_keeps_its_own_clock(client, db_session):
    """The quiz's topic is `mixed`, but each question remembers where it
    came from — otherwise a scene in a mixed quiz would get 15 seconds."""
    seen = 0
    for _ in range(12):
        body = _quiz(client, MathType.mixed, Grade.G4)
        row = storage.get_quiz(db_session, UUID(body["id"]))
        stored = storage.quiz_questions(row)
        for internal, public in zip(stored, body["questions"]):
            if internal.topic == MathType.word_problems:
                assert public["timeLimitSeconds"] >= 30, public
                seen += 1
            elif internal.topic == MathType.addition:
                assert public["timeLimitSeconds"] == 15, public
    assert seen > 0, "no word problem turned up in a mixed quiz"


def test_reading_a_quiz_back_gives_the_same_budgets(client):
    created = _quiz(client, MathType.word_problems, Grade.G5)
    fetched = client.get(f"/api/quizzes/{created['id']}").json()
    assert [q["timeLimitSeconds"] for q in fetched["questions"]] == [
        q["timeLimitSeconds"] for q in created["questions"]
    ]


def test_stored_questions_remember_their_topic(db_session):
    """The round trip through JSON has to keep `topic`, or a mixed quiz
    loses its per-question clocks the moment it's read back."""
    qs = generate_questions(
        MathType.mixed, Difficulty.medium, Grade.G4, rng=random.Random(0)
    )
    revived = [storage._question_from_json(storage._question_to_json(q)) for q in qs]
    assert [q.topic for q in revived] == [q.topic for q in qs]
    assert all(q.topic is not None for q in revived)


def test_a_quiz_stored_before_topics_existed_still_gets_clocks(client, db_session):
    """Old rows have no `topic` key; they fall back to the quiz's own."""
    body = _quiz(client, MathType.word_problems, Grade.G3)
    row = storage.get_quiz(db_session, UUID(body["id"]))
    row.questions_json = [
        {k: v for k, v in q.items() if k != "topic"} for q in row.questions_json
    ]
    db_session.commit()

    fetched = client.get(f"/api/quizzes/{body['id']}").json()
    for q in fetched["questions"]:
        assert q["timeLimitSeconds"] >= 30, q


# ---------- the whole-quiz clock the player sees ----------


@pytest.mark.parametrize("math_type", list(MathType), ids=lambda t: t.value)
def test_a_whole_quiz_fits_in_a_sitting(client, math_type):
    """The front end's total clock is the sum of the ten budgets plus 30
    seconds of slack. A table edit that pushed a quiz past ~12 minutes
    would be a different product; this is the guard rail."""
    grade = min_grade_for_type(math_type)
    body = _quiz(client, math_type, Grade.G5 if grade == Grade.G5 else grade)
    total = sum(q["timeLimitSeconds"] for q in body["questions"]) + 30
    assert total <= 12 * 60, f"{math_type.value}: {total}s"
