"""Every topic driven through the real HTTP endpoints, not the generator.

PROJECT_PLAN §4 flagged this: the topic suites call `generate_questions`
directly, and only `addition` was ever exercised through
`POST /api/quizzes` → `POST /api/quizzes/{id}/submit`. Everything
between the generator and the player — JSON serialization of answers
that are sometimes strings and sometimes ints, the answer-key stripping,
`answerKind` and `timeLimitSeconds`, grading a submitted string against
a stored answer, the leaderboard and history writes — was untested for
the other fourteen topics.

Each topic runs at the lowest grade it's offered at (and, for the ones
gated above K, at grade 5 too), in both answer modes.
"""
from __future__ import annotations

from uuid import UUID

import pytest

from app import storage
from app.distractors import kind_of
from app.models import AnswerMode, Difficulty, Grade, MathType
from app.questions import min_grade_for_type

TOPICS = list(MathType)


def _grades_for(math_type: MathType) -> list[Grade]:
    """The entry grade, plus the top grade when they differ."""
    low = min_grade_for_type(math_type)
    return [low] if low == Grade.G5 else [low, Grade.G5]


def _create(client, math_type, grade, difficulty=Difficulty.medium, answer_mode="typing"):
    client.post("/api/users", json={"username": "Pat", "pin": "1234"})
    r = client.post(
        "/api/quizzes",
        json={
            "username": "Pat",
            "grade": grade.value,
            "mathType": math_type.value,
            "difficulty": difficulty.value,
            "answerMode": answer_mode,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _correct_answers(db_session, quiz_id):
    row = storage.get_quiz(db_session, UUID(quiz_id))
    return [str(q.correctAnswer) for q in storage.quiz_questions(row)]


# ---------- creation ----------


@pytest.mark.parametrize("math_type", TOPICS, ids=lambda t: t.value)
def test_every_topic_creates_a_clean_quiz(client, math_type):
    for grade in _grades_for(math_type):
        body = _create(client, math_type, grade)
        questions = body["questions"]
        assert len(questions) == 10
        assert [q["id"] for q in questions] == list(range(10))
        # Keyed on text *and* figure: "how many corners does this shape
        # have?" is a different question for a square and a hexagon.
        seen = {(q["question"], q["figure"]) for q in questions}
        assert len(seen) == 10, "duplicate question in one quiz"
        for q in questions:
            # The answer key never crosses the wire before submission.
            assert "correctAnswer" not in q
            assert "explanation" not in q
            assert q["question"].strip(), "blank question text"
            assert q["answerKind"] in {"integer", "decimal", "text"}
            assert 15 <= q["timeLimitSeconds"] <= 120, q["timeLimitSeconds"]


@pytest.mark.parametrize("math_type", TOPICS, ids=lambda t: t.value)
def test_every_topic_can_be_answered_by_tapping(client, math_type):
    """Multiple choice must offer distinct, plausible options that
    include the right answer without giving it away.

    Not always four: "write <, > or =" has exactly three possible
    answers and "even or odd" two, and padding those out with numbers is
    what made the answer obvious (PROJECT_PLAN §2.1).
    """
    for grade in _grades_for(math_type):
        body = _create(client, math_type, grade, answer_mode="multiple_choice")
        for q in body["questions"]:
            options = q["options"]
            assert options is not None, q["question"]
            assert 2 <= len(options) <= 4, options
            assert len(set(options)) == len(options), options
            assert all(str(o).strip() for o in options), options
            # Every option is the same sort of thing as every other, so
            # the odd one out can't be spotted without doing the maths.
            kinds = {kind_of(str(o)) for o in options}
            numeric = {"integer", "decimal", "fraction"}
            assert len(kinds) == 1 or kinds <= numeric, (q["question"], options)


# ---------- the full round trip ----------


@pytest.mark.parametrize("math_type", TOPICS, ids=lambda t: t.value)
def test_every_topic_grades_a_perfect_run(client, db_session, math_type):
    for grade in _grades_for(math_type):
        body = _create(client, math_type, grade)
        answers = _correct_answers(db_session, body["id"])
        r = client.post(
            f"/api/quizzes/{body['id']}/submit",
            json={"answers": answers, "timeUsedSeconds": 90},
        )
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["score"] == 10, [
            (x["question"], x["userAnswer"], x["correctAnswer"])
            for x in result["results"]
            if not x["isCorrect"]
        ]
        assert result["badge"] == "🏆"
        # Now — and only now — the key comes back, with a hint attached.
        for item in result["results"]:
            assert item["correctAnswer"] not in (None, "")
            assert item["explanation"].strip()


@pytest.mark.parametrize("math_type", TOPICS, ids=lambda t: t.value)
def test_every_topic_scores_zero_for_nonsense(client, math_type):
    """The mirror of the perfect run: nothing grades as accidentally
    right, which is what would happen if a topic's answers were empty."""
    for grade in _grades_for(math_type):
        body = _create(client, math_type, grade)
        r = client.post(
            f"/api/quizzes/{body['id']}/submit",
            json={"answers": ["zzz"] * 10, "timeUsedSeconds": 90},
        )
        assert r.status_code == 200, r.text
        assert r.json()["score"] == 0


@pytest.mark.parametrize("math_type", TOPICS, ids=lambda t: t.value)
def test_a_tapped_option_grades_the_same_as_a_typed_answer(client, db_session, math_type):
    """Whatever the generator put in `options` has to be gradeable text:
    an option formatted differently from the stored answer would mark a
    correct tap wrong."""
    grade = min_grade_for_type(math_type)
    body = _create(client, math_type, grade, answer_mode="multiple_choice")
    answers = _correct_answers(db_session, body["id"])
    for q, answer in zip(body["questions"], answers):
        assert any(str(o) == answer for o in q["options"]), (q["question"], q["options"], answer)

    r = client.post(
        f"/api/quizzes/{body['id']}/submit",
        json={"answers": answers, "timeUsedSeconds": 60},
    )
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 10


# ---------- what a finished quiz leaves behind ----------


@pytest.mark.parametrize("math_type", TOPICS, ids=lambda t: t.value)
def test_a_finished_quiz_reaches_the_board_and_history(client, db_session, signup, math_type):
    headers = signup(client, "Pat")
    grade = min_grade_for_type(math_type)
    body = _create(client, math_type, grade)
    answers = _correct_answers(db_session, body["id"])
    client.post(
        f"/api/quizzes/{body['id']}/submit",
        json={"answers": answers, "timeUsedSeconds": 75},
    )

    board = client.get("/api/leaderboard").json()
    assert len(board) == 1
    row = board[0]
    assert row["name"] == "Pat"
    assert row["score"] == 10
    # The row carries the level it was set at — the leaderboard chips
    # and the filters both read these.
    assert row["mathType"] == math_type.value
    assert row["grade"] == grade.value
    assert row["difficulty"] == "medium"

    filtered = client.get("/api/leaderboard", params={"mathType": math_type.value}).json()
    assert len(filtered) == 1, f"{math_type.value} row missing from its own filter"

    stats = client.get("/api/users/Pat/stats", headers=headers).json()
    assert stats["totalQuizzes"] == 1
    assert [t["mathType"] for t in stats["byTopic"]] == [math_type.value]
    assert stats["recent"][0]["mathType"] == math_type.value


# ---------- gating, through the API ----------


@pytest.mark.parametrize("math_type", TOPICS, ids=lambda t: t.value)
def test_an_out_of_grade_topic_still_produces_a_sane_quiz(client, db_session, math_type):
    """Grade gating is advisory, not enforced (see PROJECT_PLAN §2).

    The setup screen only offers topics that fit the chosen grade, and
    🎲 Mixed samples only unlocked ones — but `POST /api/quizzes` itself
    accepts any grade/topic pair. This test documents that, and pins the
    property that actually matters if someone does ask for percentages
    at K: the generator still returns ten distinct, gradeable questions
    rather than looping or dividing by zero on a tiny number range.
    """
    if min_grade_for_type(math_type) == Grade.K:
        pytest.skip("offered at every grade anyway")

    body = _create(client, math_type, Grade.K, difficulty=Difficulty.easy)
    assert len(body["questions"]) == 10
    # Not a distinctness assertion: K/easy squeezes some topics into a
    # value space too small for ten different questions, and the
    # generator is documented to repeat rather than loop forever
    # (test_question_uniqueness.test_small_space_falls_back_gracefully).
    # What must hold is that the quiz is still playable and gradeable.
    answers = _correct_answers(db_session, body["id"])
    r = client.post(
        f"/api/quizzes/{body['id']}/submit",
        json={"answers": answers, "timeUsedSeconds": 60},
    )
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 10


@pytest.mark.parametrize("difficulty", list(Difficulty), ids=lambda d: d.value)
def test_mixed_quizzes_run_end_to_end_at_every_difficulty(client, db_session, difficulty):
    body = _create(client, MathType.mixed, Grade.G4, difficulty=difficulty)
    answers = _correct_answers(db_session, body["id"])
    r = client.post(
        f"/api/quizzes/{body['id']}/submit",
        json={"answers": answers, "timeUsedSeconds": 100},
    )
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 10


def test_answer_modes_are_the_only_two_the_api_accepts(client):
    assert {m.value for m in AnswerMode} == {"typing", "multiple_choice"}
    client.post("/api/users", json={"username": "Pat", "pin": "1234"})
    r = client.post(
        "/api/quizzes",
        json={
            "username": "Pat",
            "grade": "3",
            "mathType": "addition",
            "difficulty": "easy",
            "answerMode": "telepathy",
        },
    )
    assert r.status_code == 422
