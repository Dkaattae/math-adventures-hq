"""Comparison & number sense: numbers at K-2, expressions after that.

Grade 4 used to get "which is biggest: 3, 15, 24?" — a grade-2 question.
From grade 3 both sides of a comparison are something to work out first,
and the operators widen with the grade. These tests check the ladder, and
independently recompute every expression rather than trusting the
generator's own arithmetic.
"""
from __future__ import annotations

import random
import re
from math import factorial

import pytest

from app.models import Difficulty, Grade, MathType
from app.question_times import SECONDS_PER_HEAVY_OP
from app.questions import (
    _COMPARISON_TIERS,
    _comparison_tier,
    _pick_factory,
    generate_questions,
)

SEEDS = range(30)


def _questions(grade: Grade, difficulty: Difficulty, seed: int = 0):
    return generate_questions(MathType.comparison, difficulty, grade, rng=random.Random(seed))


def _evaluate(expr: str) -> int:
    """Work the expression out independently of the generator.

    Deliberately a separate implementation: if both sides shared code, a
    bug in precedence or in the factorial would cancel itself out.
    """
    text = expr.replace("×", "*").replace("^", "**").replace("÷", "//")
    text = re.sub(r"(\d+)!", lambda m: str(factorial(int(m.group(1)))), text)
    # Only the operators the generator is allowed to print, so a new one
    # can't slip through unevaluated.
    assert re.fullmatch(r"[\d\s()+*/-]+", text), text
    return eval(text, {"__builtins__": {}}, {})  # noqa: S307 - test-only, generated input


def _comparisons(grade: Grade, difficulty: Difficulty):
    """Every "write <, > or =" question at a level, as (left, right, answer)."""
    for seed in SEEDS:
        for q in _questions(grade, difficulty, seed):
            m = re.search(r"blank:\n\n(.+?) _ (.+)$", q.question)
            if m:
                yield m.group(1), m.group(2), q.correctAnswer


# ---------- the ladder ----------


@pytest.mark.parametrize(
    "grade,difficulty,expected",
    [
        (Grade.K, Difficulty.easy, "basic"),
        (Grade.G1, Difficulty.hard, "basic"),
        (Grade.G2, Difficulty.easy, "basic"),
        (Grade.G2, Difficulty.medium, "numbers"),
        (Grade.G3, Difficulty.easy, "sums"),
        (Grade.G3, Difficulty.medium, "sums"),
        (Grade.G3, Difficulty.hard, "operators"),
        (Grade.G4, Difficulty.easy, "operators"),
        (Grade.G4, Difficulty.hard, "operators"),
        (Grade.G5, Difficulty.easy, "operators"),
        (Grade.G5, Difficulty.medium, "powers"),
        (Grade.G5, Difficulty.hard, "powers"),
    ],
)
def test_tier_ladder(grade, difficulty, expected):
    g = 0 if grade == Grade.K else int(grade.value)
    assert _comparison_tier(difficulty, g) == expected
    assert _pick_factory(MathType.comparison, difficulty, grade).tier == expected


def test_lower_grades_stay_on_plain_numbers():
    """K-2 compares numbers, never expressions."""
    for grade in (Grade.K, Grade.G1, Grade.G2):
        for difficulty in Difficulty:
            for seed in SEEDS:
                for q in _questions(grade, difficulty, seed):
                    assert "×" not in q.question, q.question
                    assert "^" not in q.question and "!" not in q.question, q.question


def test_grade_three_compares_sums_but_no_other_operator():
    """Only + at grade 3, as asked — but on both sides of the blank."""
    saw = False
    for left, right, _ in _comparisons(Grade.G3, Difficulty.medium):
        saw = True
        for side in (left, right):
            assert "+" in side, side
            assert "×" not in side and "^" not in side and "!" not in side, side
    assert saw, "grade 3 never produced an expression comparison"


def test_grade_four_brings_in_more_operators():
    sides = [s for left, right, _ in _comparisons(Grade.G4, Difficulty.medium) for s in (left, right)]
    assert any("×" in s for s in sides), "grade 4 never used multiplication"
    # …and never jumps straight to powers/factorials.
    assert not any("^" in s or "!" in s for s in sides)


def test_grade_five_uses_powers_and_factorials():
    sides = [
        s for left, right, _ in _comparisons(Grade.G5, Difficulty.hard) for s in (left, right)
    ]
    assert any("^" in s for s in sides), "grade 5 never compared powers"
    assert any("!" in s for s in sides), "grade 5 never compared a factorial"


def test_grade_five_still_sees_a_bracketed_expression():
    sides = [
        s for left, right, _ in _comparisons(Grade.G5, Difficulty.hard) for s in (left, right)
    ]
    assert any("(" in s for s in sides)


# ---------- the arithmetic itself ----------


@pytest.mark.parametrize(
    "grade,difficulty",
    [(Grade.G3, Difficulty.medium), (Grade.G4, Difficulty.medium),
     (Grade.G4, Difficulty.hard), (Grade.G5, Difficulty.medium), (Grade.G5, Difficulty.hard)],
)
def test_every_comparison_answer_is_right(grade, difficulty):
    checked = 0
    for left, right, answer in _comparisons(grade, difficulty):
        a, b = _evaluate(left), _evaluate(right)
        expected = "<" if a < b else (">" if a > b else "=")
        assert answer == expected, f"{left} _ {right} → said {answer}, really {expected}"
        checked += 1
    assert checked > 20, checked


def test_biggest_of_three_expressions_is_right():
    checked = 0
    for grade, difficulty in [(Grade.G3, Difficulty.medium), (Grade.G5, Difficulty.hard)]:
        for seed in SEEDS:
            for q in _questions(grade, difficulty, seed):
                m = re.match(r"Which one is the biggest: (.+?)\?\n", q.question)
                if not m:
                    continue
                parts = [p.strip() for p in m.group(1).replace(", or ", ", ").split(", ")]
                assert len(parts) == 3, parts
                assert q.correctAnswer == max(_evaluate(p) for p in parts), q.question
                checked += 1
    assert checked > 0


def test_doubling_sequences_are_right():
    checked = 0
    for seed in SEEDS:
        for q in _questions(Grade.G4, Difficulty.medium, seed):
            m = re.match(r"What number comes next: (\d+), (\d+), (\d+), (\d+), \?", q.question)
            if not m:
                continue
            a, b, c, d = (int(x) for x in m.groups())
            step = b // a
            assert (b, c, d) == (a * step, a * step**2, a * step**3), q.question
            assert q.correctAnswer == d * step, q.question
            checked += 1
    assert checked > 0


# ---------- fairness & readability ----------


def test_neither_direction_is_a_safe_guess():
    """A kid answering "<" every time shouldn't do better than chance."""
    for grade, difficulty in [(Grade.G3, Difficulty.medium), (Grade.G5, Difficulty.hard)]:
        answers = [a for _, _, a in _comparisons(grade, difficulty)]
        for symbol in ("<", ">"):
            share = answers.count(symbol) / len(answers)
            assert 0.3 < share < 0.6, (grade, symbol, share)


def test_equals_shows_up_sometimes():
    for grade, difficulty in [(Grade.G3, Difficulty.medium), (Grade.G4, Difficulty.medium)]:
        answers = [a for _, _, a in _comparisons(grade, difficulty)]
        assert "=" in answers


def test_powers_and_factorials_come_with_a_reminder():
    """A fifth grader may never have seen "!" before."""
    for seed in SEEDS:
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            if "!" in q.question:
                assert "5! means 5 × 4 × 3 × 2 × 1" in q.question, q.question
            if "^" in q.question:
                assert "means 4 × 4 × 4" in q.question, q.question


def test_powers_stay_workable():
    """Big enough to make the point, small enough to actually compute."""
    for seed in SEEDS:
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            for base, exp in re.findall(r"(\d+)\^(\d+)", q.question):
                assert int(base) ** int(exp) <= 10_000, q.question


def test_a_quiz_rotates_through_its_tier():
    for grade, difficulty in [(Grade.G3, Difficulty.medium), (Grade.G5, Difficulty.hard)]:
        tier = _comparison_tier(difficulty, int(grade.value))
        for seed in (0, 1, 2):
            questions = _questions(grade, difficulty, seed)
            openers = {q.question.split("\n")[0][:20] for q in questions}
            assert len(openers) >= min(len(_COMPARISON_TIERS[tier]), 4), openers


def test_powers_and_factorials_buy_thinking_time():
    """"9^4 _ 7!" is short to read and slow to work out."""
    from app.questions import time_limit_seconds

    assert time_limit_seconds("Write <, > or = in the blank:\n\n9^4 _ 7!") > 30
    # Nothing else changes: a plain one-liner keeps the standard 15.
    assert time_limit_seconds("7 + 5 = ?") == 15
    assert time_limit_seconds("Write <, > or = in the blank:\n\n14 + 63 _ 49 + 19") == 15


def test_grade_five_power_questions_are_not_on_a_fifteen_second_clock():
    """Asked the way the API asks it — topic, difficulty and grade — so
    this reflects the clock a player actually gets."""
    from app.questions import time_limit_seconds

    checked = 0
    for seed in SEEDS:
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            if re.search(r"\d\^\d|\d!", q.question):
                budget = time_limit_seconds(
                    q.question, MathType.comparison, Difficulty.hard, Grade.G5
                )
                # 30 (grade 3+) + 5 (hard) + 10 per power/factorial.
                assert budget >= 45, (budget, q.question)
                checked += 1
    assert checked > 0


def test_the_reminder_line_does_not_buy_extra_time():
    """"Reminder: 4^3 means 4 × 4 × 4" is explanation, not work."""
    from app.questions import time_limit_seconds

    with_reminder = time_limit_seconds(
        "Reminder: 4^3 means 4 × 4 × 4.\n\nWrite <, > or = in the blank:\n\n5^2 _ 3^6"
    )
    without = time_limit_seconds("Write <, > or = in the blank:\n\n5^2 _ 3^6")
    # The reminder adds a few words of reading, not two more calculations.
    assert with_reminder - without < SECONDS_PER_HEAVY_OP



# ---------- variety: one skill, many shapes (PROJECT_PLAN §2.1) ----------
#
# Reported from play: a grade-5 comparison quiz was "3^4 vs 4!" over and
# over. The maths was right, but with only 29 power pairs and five
# factorials to draw on, the same handful of questions came round again
# — within a quiz and across quizzes.


def _pairs(q):
    """The two sides of a comparison, order-insensitive."""
    m = re.search(r"blank:\n\n(.+?) _ (.+)$", q.question)
    return tuple(sorted(m.groups())) if m else None


@pytest.mark.parametrize("grade", [Grade.G4, Grade.G5], ids=lambda g: g.value)
@pytest.mark.parametrize("difficulty", [Difficulty.medium, Difficulty.hard], ids=lambda d: d.value)
def test_a_quiz_never_repeats_a_comparison(grade, difficulty):
    """Including with the sides swapped — "3^4 _ 4!" and "4! _ 3^4" read
    as the same question even though the answer flips."""
    for seed in range(120):
        qs = _questions(grade, difficulty, seed)
        pairs = [p for p in (_pairs(q) for q in qs) if p]
        assert len(set(pairs)) == len(pairs), (seed, pairs)
        assert len({q.question for q in qs}) == 10


def test_grade_five_comparisons_are_not_all_bare_powers():
    """The complaint in one assertion: powers and factorials must turn
    up inside arithmetic too, not only on their own."""
    mixed = plain = 0
    for seed in SEEDS:
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            pair = _pairs(q)
            if not pair:
                continue
            for side in pair:
                if "^" in side or "!" in side:
                    if any(op in side for op in ("+", "-", "×")):
                        mixed += 1
                    else:
                        plain += 1
    assert mixed > 0, "no power/factorial ever appeared inside a larger expression"
    assert mixed >= plain / 3, f"only {mixed} mixed against {plain} bare"


def test_the_pool_of_grade_five_questions_is_wide():
    """Thirty quizzes should not keep meeting the same questions."""
    seen = set()
    for seed in range(30):
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            seen.add(q.question)
    # 300 draws; anything near 300 means collisions are rare.
    assert len(seen) > 240, len(seen)


def test_grade_four_comparisons_have_more_than_one_shape():
    shapes = set()
    for seed in SEEDS:
        for q in _questions(Grade.G4, Difficulty.medium, seed):
            pair = _pairs(q)
            if not pair:
                continue
            for side in pair:
                shapes.add(
                    ("÷" in side, "-" in side, "×" in side, "(" in side, "+" in side)
                )
    assert len(shapes) >= 5, shapes
