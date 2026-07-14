"""Multiple-choice options and mixed-topic generation."""
from __future__ import annotations

import random

import pytest

from app.models import AnswerMode, Difficulty, Grade, MathType
from app.questions import generate_questions, grade_answer

ALL_TYPES = list(MathType)


@pytest.mark.parametrize("math_type", ALL_TYPES)
def test_multiple_choice_options_are_valid(math_type):
    """Every MC question must include its correct answer among 2-4 distinct
    options, with the answer key never missing from the choices."""
    for seed in range(15):
        rng = random.Random(seed)
        qs = generate_questions(
            math_type, Difficulty.hard, Grade.G5,
            answer_mode=AnswerMode.multiple_choice, rng=rng,
        )
        for q in qs:
            assert q.options is not None, f"{math_type} produced no options"
            assert 2 <= len(q.options) <= 4, q.options
            assert len(set(q.options)) == len(q.options), f"duplicate options: {q.options}"
            assert str(q.correctAnswer) in q.options, (
                f"correct answer {q.correctAnswer!r} missing from {q.options}"
            )


@pytest.mark.parametrize("math_type", ALL_TYPES)
def test_multiple_choice_exactly_one_option_grades_correct(math_type):
    """Grading any single option must mark exactly the correct one right."""
    for seed in range(10):
        rng = random.Random(seed)
        qs = generate_questions(
            math_type, Difficulty.medium, Grade.G3,
            answer_mode=AnswerMode.multiple_choice, rng=rng,
        )
        for q in qs:
            right = [opt for opt in q.options if grade_answer(q.correctAnswer, opt)]
            assert len(right) == 1, (
                f"{math_type}: {len(right)} options grade correct for "
                f"answer {q.correctAnswer!r} in {q.options}"
            )


def test_typing_mode_has_no_options():
    for math_type in (MathType.addition, MathType.geometry, MathType.mixed):
        qs = generate_questions(math_type, Difficulty.easy, Grade.G2, rng=random.Random(0))
        assert all(q.options is None for q in qs)


def test_mixed_draws_from_several_topics():
    """A mixed quiz should not be a single topic in disguise."""
    saw_arithmetic = False
    saw_word_or_geometry = False
    for seed in range(20):
        rng = random.Random(seed)
        qs = generate_questions(MathType.mixed, Difficulty.medium, Grade.G4, rng=rng)
        texts = " ".join(q.question for q in qs)
        if any(sym in texts for sym in ("+", "×", "÷")):
            saw_arithmetic = True
        if "has" in texts or "How many" in texts or "shape" in texts:
            saw_word_or_geometry = True
    assert saw_arithmetic and saw_word_or_geometry


def test_mixed_returns_10_unique_questions():
    for seed in range(30):
        rng = random.Random(seed)
        qs = generate_questions(MathType.mixed, Difficulty.hard, Grade.G5, rng=rng)
        assert len(qs) == 10
        assert len({q.question for q in qs}) == 10


def test_mixed_multiple_choice_options_valid():
    for seed in range(15):
        rng = random.Random(seed)
        qs = generate_questions(
            MathType.mixed, Difficulty.medium, Grade.G4,
            answer_mode=AnswerMode.multiple_choice, rng=rng,
        )
        for q in qs:
            assert q.options and str(q.correctAnswer) in q.options


def test_int_distractors_stay_non_negative_for_small_answers():
    from app.questions import _build_options

    rng = random.Random(1)
    opts = _build_options(1, sibling_answers=[2, 3, 4], rng=rng)
    assert all(int(o) >= 0 for o in opts)
