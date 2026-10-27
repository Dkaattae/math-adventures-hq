"""The grade focus chart and the shared level ladder (app/curriculum.py)."""
from __future__ import annotations

import random
import re
from collections import Counter
from fractions import Fraction

import pytest

from app import curriculum
from app.curriculum import GRADE_FOCUS, MIXED_SEATS, grade_focus, level
from app.models import Difficulty, Grade, MathType
from app.questions import generate_questions, types_available

GRADES = [Grade.K, Grade.G1, Grade.G2, Grade.G3, Grade.G4, Grade.G5]


# ---------- the chart ----------


@pytest.mark.parametrize("grade", GRADES)
def test_the_chart_only_names_topics_the_grade_has_unlocked(grade):
    plan = grade_focus(grade)
    unlocked = set(types_available(grade))
    for topic in [*plan.focus, *plan.review]:
        assert topic in unlocked, f"{topic} is in the {grade} chart but locked there"
        assert topic != MathType.mixed
    assert not set(plan.focus) & set(plan.review), "a topic is both focus and review"
    assert 0 < plan.review_seats < MIXED_SEATS


def test_every_grade_has_a_chart():
    assert set(GRADE_FOCUS) == {curriculum.grade_index(g) for g in GRADES}


@pytest.mark.parametrize("grade", GRADES)
@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_mixed_quizzes_follow_the_chart(grade, difficulty):
    plan = grade_focus(grade)
    for seed in range(12):
        qs = generate_questions(MathType.mixed, difficulty, grade, rng=random.Random(seed))
        assert len(qs) == 10 and len({q.question for q in qs}) == 10
        topics = Counter(q.topic for q in qs)
        for topic, seats in plan.focus.items():
            assert topics[topic] == seats, (grade, difficulty, topics)
        review = {t: n for t, n in topics.items() if t not in plan.focus}
        assert set(review) <= set(plan.review), (grade, review)
        assert sum(review.values()) == plan.review_seats
        if len(plan.review) >= plan.review_seats:
            assert max(review.values()) == 1, f"a review topic repeated: {review}"


def test_grade_five_mixed_leaves_out_the_early_grade_topics():
    for difficulty in Difficulty:
        for seed in range(30):
            qs = generate_questions(MathType.mixed, difficulty, Grade.G5, rng=random.Random(seed))
            for q in qs:
                assert q.topic not in (
                    MathType.addition, MathType.subtraction,
                    MathType.comparison, MathType.money_time,
                ), q.question


def test_mixed_seats_move_around_the_quiz():
    positions: dict[MathType, set[int]] = {}
    for seed in range(40):
        for q in generate_questions(MathType.mixed, Difficulty.medium, Grade.G5,
                                    rng=random.Random(seed)):
            positions.setdefault(q.topic, set()).add(q.id)
    assert positions[MathType.fractions] == set(range(10))


# ---------- the ladder ----------


def test_levels_run_zero_to_twelve_and_neighbouring_grades_overlap():
    assert level(Difficulty.easy, Grade.K) == 0
    assert level(Difficulty.hard, Grade.G5) == curriculum.MAX_LEVEL == 12
    for lower, upper in zip(GRADES, GRADES[1:]):
        assert level(Difficulty.hard, lower) == level(Difficulty.easy, upper)


#: Topics whose questions come only from the level, so grade N hard and
#: grade N+1 easy must deal the very same quiz from the same seed.
#: (Subtraction adds negatives on grade 4-5 *hard*, and word problems
#: read longer by grade, so those two are left out.)
LEVEL_ONLY_TOPICS = [
    MathType.addition, MathType.multiplication, MathType.division,
    MathType.algebra, MathType.fractions, MathType.order_of_operations,
    MathType.decimals, MathType.comparison, MathType.money_time,
    MathType.measurement, MathType.percentages,
]


@pytest.mark.parametrize("math_type", LEVEL_ONLY_TOPICS, ids=lambda t: t.value)
def test_grade_n_hard_is_grade_n_plus_one_easy(math_type):
    for lower, upper in zip(GRADES, GRADES[1:]):
        if math_type not in types_available(lower):
            continue
        for seed in range(3):
            hard = generate_questions(math_type, Difficulty.hard, lower, rng=random.Random(seed))
            easy = generate_questions(math_type, Difficulty.easy, upper, rng=random.Random(seed))
            assert [q.question for q in hard] == [q.question for q in easy], (lower, upper)


# ---------- grade 5 is grade-5 work ----------


def _numbers(text: str) -> list[Fraction]:
    return [Fraction(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]


def test_grade_five_addition_is_multi_digit_or_decimal():
    for difficulty in Difficulty:
        for seed in range(10):
            for q in generate_questions(MathType.addition, difficulty, Grade.G5,
                                        rng=random.Random(seed)):
                a, b = _numbers(q.question)
                assert "." in q.question or min(a, b) >= 1000, q.question


def test_grade_five_multiplication_always_has_a_two_digit_factor_or_more():
    for difficulty in Difficulty:
        for seed in range(10):
            for q in generate_questions(MathType.multiplication, difficulty, Grade.G5,
                                        rng=random.Random(seed)):
                a, b = _numbers(q.question)
                if "." in q.question:
                    continue  # 3.25 × 6
                assert min(a, b) >= 11 and max(a, b) >= 12, q.question


def test_grade_five_division_uses_two_digit_divisors_above_easy():
    for difficulty in (Difficulty.medium, Difficulty.hard):
        for seed in range(10):
            for q in generate_questions(MathType.division, difficulty, Grade.G5,
                                        rng=random.Random(seed)):
                m = re.search(r"(\d+) ÷ (\d+)", q.question)
                if m and "decimal" not in q.question and "fraction" not in q.question:
                    assert int(m.group(2)) >= 11, q.question
