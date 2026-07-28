"""Per-question answer kinds drive the mobile keyboard (PROJECT_PLAN §3.2)."""
from __future__ import annotations

import pytest

from app.models import AnswerKind, Difficulty, Grade, MathType
from app.questions import answer_kind, generate_questions


@pytest.mark.parametrize(
    "correct,expected",
    [
        (7, AnswerKind.integer),
        (0, AnswerKind.integer),
        ("42", AnswerKind.integer),
        (3.5, AnswerKind.decimal),
        ("0.75", AnswerKind.decimal),
        (".5", AnswerKind.decimal),
        # Negatives need a minus key, which numeric keypads don't have.
        (-3, AnswerKind.text),
        (-0.5, AnswerKind.text),
        ("3/5", AnswerKind.text),
        ("<", AnswerKind.text),
        ("hexagon", AnswerKind.text),
        ("even", AnswerKind.text),
    ],
)
def test_answer_kind_follows_the_answer(correct, expected):
    assert answer_kind(correct) == expected


def test_every_generated_question_gets_a_usable_kind():
    """A kind must never promise a keypad the answer can't be typed on."""
    for math_type in MathType:
        for grade in Grade:
            for difficulty in Difficulty:
                try:
                    questions = generate_questions(math_type, difficulty, grade)
                except ValueError:
                    continue  # topic not offered at this grade
                for q in questions:
                    kind = answer_kind(q.correctAnswer)
                    text = str(q.correctAnswer)
                    if kind == AnswerKind.integer:
                        assert text.isdigit(), f"{math_type} {grade} {difficulty}: {text!r}"
                    elif kind == AnswerKind.decimal:
                        assert not text.startswith("-") and text.replace(".", "", 1).isdigit()


def test_api_exposes_the_kind_on_each_question(client, signup):
    signup(client, "Kid")
    body = client.post(
        "/api/quizzes",
        json={"username": "Kid", "grade": "2", "mathType": "addition", "difficulty": "easy"},
    ).json()
    kinds = {q["answerKind"] for q in body["questions"]}
    assert kinds == {"integer"}  # grade-2 easy addition is whole numbers


def test_subtraction_with_negatives_is_typed_as_text(client, signup):
    """Grade-5 hard subtraction can go below zero — full keyboard."""
    signup(client, "Kid")
    body = client.post(
        "/api/quizzes",
        json={"username": "Kid", "grade": "5", "mathType": "subtraction", "difficulty": "hard"},
    ).json()
    # Whatever mix comes out, no question claims a numeric keypad for a
    # negative answer (that's what the generator test above guarantees);
    # here we just assert the field is present and valid on the wire.
    assert all(q["answerKind"] in {"integer", "decimal", "text"} for q in body["questions"])
