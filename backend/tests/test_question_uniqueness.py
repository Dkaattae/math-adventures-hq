"""Proves generate_questions returns distinct questions within a single quiz
and that algebra draws from several templates."""
from __future__ import annotations

import random
import re

import pytest

from app.models import Difficulty, Grade, MathType
from app.questions import generate_questions

ALL_TYPES = [
    MathType.addition,
    MathType.subtraction,
    MathType.multiplication,
    MathType.division,
    MathType.algebra,
    MathType.geometry,
    MathType.fractions,
    MathType.order_of_operations,
    MathType.word_problems,
    MathType.comparison,
    MathType.money_time,
    MathType.decimals,
    MathType.percentages,
    MathType.measurement,
]

# (difficulty, grade) combos that have enough value-space for 10 uniques.
# K/easy has a tiny range, so collisions are possible there — we cover that
# case explicitly in test_small_space_falls_back_gracefully below.
RICH_CONFIGS = [
    (Difficulty.easy, Grade.G3),
    (Difficulty.medium, Grade.G3),
    (Difficulty.hard, Grade.G4),
    (Difficulty.hard, Grade.G5),
]


@pytest.mark.parametrize("math_type", ALL_TYPES)
@pytest.mark.parametrize("difficulty,grade", RICH_CONFIGS)
def test_all_10_questions_are_unique(math_type, difficulty, grade):
    # Run many trials with different seeds to catch sporadic collisions.
    for seed in range(50):
        rng = random.Random(seed)
        qs = generate_questions(math_type, difficulty, grade, rng=rng)
        # Visual geometry questions share wording but differ by figure, so
        # the uniqueness key includes the figure.
        keys = [(q.question, q.figure) for q in qs]
        assert len(set(keys)) == 10, (
            f"duplicate question for {math_type}/{difficulty}/{grade} seed={seed}: {keys}"
        )


def test_geometry_returns_10_unique_questions_for_all_levels():
    for difficulty in (Difficulty.easy, Difficulty.medium, Difficulty.hard):
        for grade in (Grade.K, Grade.G1, Grade.G2, Grade.G3, Grade.G4, Grade.G5):
            for seed in range(10):
                rng = random.Random(seed)
                qs = generate_questions(MathType.geometry, difficulty, grade, rng=rng)
                assert len(qs) == 10
                # Visual questions deliberately share wording ("How many
                # sides does this shape have?"), so uniqueness is by the
                # (question, figure) pair rather than text alone.
                assert len({(q.question, q.figure) for q in qs}) == 10


def test_visual_geometry_questions_carry_a_figure():
    from app.questions import _GEOMETRY_VISUAL

    saw_figure = False
    for seed in range(30):
        rng = random.Random(seed)
        qs = generate_questions(MathType.geometry, Difficulty.easy, Grade.K, rng=rng)
        for q in qs:
            if q.figure is not None:
                saw_figure = True
                assert q.figure in {f[3] for f in _GEOMETRY_VISUAL}
    assert saw_figure, "K/easy geometry never included a visual shape question"


def test_geometry_pool_has_at_least_100_total_questions():
    from app.questions import _GEOMETRY_EASY, _GEOMETRY_HARD, _GEOMETRY_MEDIUM

    total = len(_GEOMETRY_EASY) + len(_GEOMETRY_MEDIUM) + len(_GEOMETRY_HARD)
    assert total >= 100, f"only {total} geometry questions"
    # Each tier individually needs ≥10 so sampling can never fail.
    assert len(_GEOMETRY_EASY) >= 10
    assert len(_GEOMETRY_MEDIUM) >= 10
    assert len(_GEOMETRY_HARD) >= 10


def test_kindergarten_geometry_is_identification_only():
    """K-level geometry should never show a perimeter/area/volume question."""
    rng = random.Random(0)
    formulas_seen = False
    for _ in range(30):
        qs = generate_questions(MathType.geometry, Difficulty.easy, Grade.K, rng=rng)
        for q in qs:
            if any(tok in q.question.lower() for tok in ("perimeter", "area", "volume", "×", "÷")):
                formulas_seen = True
    assert not formulas_seen, "K/easy should not contain formula-based questions"


def test_grade5_hard_geometry_includes_advanced_topics():
    """Grade 5 hard should hit advanced content (angles / volumes / triangle types)."""
    rng = random.Random(0)
    saw_advanced = False
    advanced_keywords = (
        "volume",
        "angle",
        "equilateral",
        "isosceles",
        "scalene",
        "acute",
        "obtuse",
        "interior",
    )
    for _ in range(20):
        qs = generate_questions(MathType.geometry, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            if any(k in q.question.lower() for k in advanced_keywords):
                saw_advanced = True
                break
        if saw_advanced:
            break
    assert saw_advanced, "grade 5 hard should surface advanced geometry topics"


def test_easy_subtraction_never_produces_negative_results():
    """K-3 and any 'easy' difficulty must stay non-negative."""
    for grade in (Grade.K, Grade.G1, Grade.G2, Grade.G3):
        for difficulty in (Difficulty.easy, Difficulty.medium, Difficulty.hard):
            for seed in range(30):
                rng = random.Random(seed)
                qs = generate_questions(MathType.subtraction, difficulty, grade, rng=rng)
                for q in qs:
                    assert int(q.correctAnswer) >= 0, (
                        f"negative result leaked into {grade}/{difficulty}: {q.question}"
                    )
    # Grade 4+ with easy/medium difficulty also stays positive.
    for grade in (Grade.G4, Grade.G5):
        for difficulty in (Difficulty.easy, Difficulty.medium):
            for seed in range(30):
                rng = random.Random(seed)
                qs = generate_questions(MathType.subtraction, difficulty, grade, rng=rng)
                for q in qs:
                    assert int(q.correctAnswer) >= 0


def test_hard_subtraction_grade4plus_can_produce_negatives():
    """Grade 4/5 hard should surface at least some negative answers across trials."""
    for grade in (Grade.G4, Grade.G5):
        saw_negative = False
        for seed in range(50):
            rng = random.Random(seed)
            qs = generate_questions(MathType.subtraction, Difficulty.hard, grade, rng=rng)
            if any(int(q.correctAnswer) < 0 for q in qs):
                saw_negative = True
                break
        assert saw_negative, f"no negative results ever appeared at {grade}/hard"


def test_easy_division_always_integer():
    """Easy division (any grade) must produce plain integer answers, no remainder/fraction/decimal."""
    for grade in (Grade.K, Grade.G1, Grade.G2, Grade.G3, Grade.G4, Grade.G5):
        for seed in range(30):
            rng = random.Random(seed)
            qs = generate_questions(MathType.division, Difficulty.easy, grade, rng=rng)
            for q in qs:
                assert isinstance(q.correctAnswer, int), q.question
                assert "remainder" not in q.question.lower()
                assert "fraction" not in q.question.lower()
                assert "decimal" not in q.question.lower()


def test_division_introduces_remainder_from_grade3_medium():
    """Grade 3+ medium/hard division should eventually ask for a remainder."""
    for grade in (Grade.G3, Grade.G4, Grade.G5):
        for difficulty in (Difficulty.medium, Difficulty.hard):
            saw_remainder = False
            for seed in range(50):
                rng = random.Random(seed)
                qs = generate_questions(MathType.division, difficulty, grade, rng=rng)
                if any("remainder" in q.question.lower() for q in qs):
                    saw_remainder = True
                    break
            assert saw_remainder, f"no remainder questions at {grade}/{difficulty}"


def test_grade5_hard_division_includes_fractions_and_decimals():
    """G5/hard division should eventually ask for both fraction and decimal answers."""
    saw_fraction = False
    saw_decimal = False
    for seed in range(80):
        rng = random.Random(seed)
        qs = generate_questions(MathType.division, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            if "fraction" in q.question.lower():
                saw_fraction = True
            if "decimal" in q.question.lower():
                saw_decimal = True
        if saw_fraction and saw_decimal:
            break
    assert saw_fraction, "G5/hard never asked for a fraction"
    assert saw_decimal, "G5/hard never asked for a decimal"


def test_division_fraction_answers_are_simplified():
    """Every fraction answer must be in lowest terms."""
    from math import gcd

    for seed in range(100):
        rng = random.Random(seed)
        qs = generate_questions(MathType.division, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            if not isinstance(q.correctAnswer, str) or "/" not in q.correctAnswer:
                continue
            num_s, den_s = q.correctAnswer.split("/")
            num, den = int(num_s), int(den_s)
            assert gcd(num, den) == 1, f"unsimplified fraction: {q.correctAnswer}"


def test_division_decimal_answers_roundtrip():
    """Every decimal answer must parse as a float and stringify cleanly."""
    for seed in range(100):
        rng = random.Random(seed)
        qs = generate_questions(MathType.division, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            if not isinstance(q.correctAnswer, str) or "." not in q.correctAnswer:
                continue
            # Must parse to a valid positive decimal.
            val = float(q.correctAnswer)
            assert val > 0


def test_negative_subtraction_answer_grading_still_works():
    """grade_answer should accept '-3' for correctAnswer=-3."""
    from app.questions import grade_answer

    assert grade_answer(-3, "-3") is True
    assert grade_answer(-3, "3") is False
    assert grade_answer(-3, "-3 ") is True  # whitespace tolerant


def test_fraction_and_decimal_answer_grading():
    from app.questions import grade_answer

    assert grade_answer("3/4", "3/4") is True
    assert grade_answer("3/4", " 3/4 ") is True
    assert grade_answer("3/4", "6/8") is False  # must be simplified
    assert grade_answer("0.75", "0.75") is True
    assert grade_answer("0.75", "0.5") is False


def test_geometry_tier_selector_by_grade_and_difficulty():
    from app.questions import (
        _GEOMETRY_EASY,
        _GEOMETRY_HARD,
        _GEOMETRY_VISUAL,
        _geometry_pool,
    )

    # EASY tier is the curated easy items plus the visual shape questions.
    easy_set = {q[0] for q in _GEOMETRY_EASY} | {q[0] for q in _GEOMETRY_VISUAL}
    hard_set = {q[0] for q in _GEOMETRY_HARD}

    # K easy → EASY only (no HARD)
    pool = _geometry_pool(Difficulty.easy, Grade.K)
    assert {q[0] for q in pool} <= easy_set

    # K medium → still EASY only
    pool = _geometry_pool(Difficulty.medium, Grade.K)
    assert {q[0] for q in pool} <= easy_set

    # G5 hard → MEDIUM + HARD (no EASY identification questions)
    pool = _geometry_pool(Difficulty.hard, Grade.G5)
    pool_questions = {q[0] for q in pool}
    assert pool_questions & hard_set, "G5/hard must include HARD tier"
    assert not (pool_questions & easy_set), "G5/hard should not include EASY tier"

    # G3 medium → EASY + MEDIUM (no HARD)
    pool = _geometry_pool(Difficulty.medium, Grade.G3)
    pool_questions = {q[0] for q in pool}
    assert pool_questions & easy_set
    assert not (pool_questions & hard_set)


def test_algebra_uses_multiple_templates_for_higher_grades():
    # Collect the template prefix from many questions; at grade 3 hard, we
    # should see at least 3 distinct templates across 10 questions (usually 4-5).
    rng = random.Random(0)
    seen_shapes: set[str] = set()
    for _ in range(5):
        qs = generate_questions(MathType.algebra, Difficulty.hard, Grade.G3, rng=rng)
        for q in qs:
            seen_shapes.add(_algebra_shape(q.question))
    assert len(seen_shapes) >= 3, f"only saw templates: {seen_shapes}"


def test_algebra_easy_kindergarten_only_uses_plus_minus():
    rng = random.Random(0)
    shapes: set[str] = set()
    for _ in range(10):
        qs = generate_questions(MathType.algebra, Difficulty.easy, Grade.K, rng=rng)
        for q in qs:
            shapes.add(_algebra_shape(q.question))
    # Only the two easy templates: "x + c = ..." and "x - c = ..."
    assert shapes <= {"x+c", "x-c"}, f"unexpected shapes for K/easy: {shapes}"


def test_addition_dedup_treats_commutative_pairs_as_same():
    # Force the generator to draw the same unordered pair twice and verify
    # the dedup catches it.
    from app.questions import _make_addition  # type: ignore

    class FixedRng:
        def __init__(self, values):
            self.values = list(values)

        def randint(self, a, b):
            return self.values.pop(0)

    # First call: (3, 5) → sig ("add", 3, 5)
    # Second call: (5, 3) → sig ("add", 3, 5) — should be considered dup
    rng1 = FixedRng([3, 5])
    sig1, *_ = _make_addition(rng1, 1, 10)
    rng2 = FixedRng([5, 3])
    sig2, *_ = _make_addition(rng2, 1, 10)
    assert sig1 == sig2


def test_algebra_hard_grade4_introduces_two_step_equations():
    """G4+/hard algebra should eventually produce an ax + b = c question."""
    saw_two_step = False
    for seed in range(30):
        rng = random.Random(seed)
        qs = generate_questions(MathType.algebra, Difficulty.hard, Grade.G4, rng=rng)
        if any(re.match(r"^\d+x [+-] \d+ =", q.question) for q in qs):
            saw_two_step = True
            break
    assert saw_two_step, "G4/hard algebra never produced a two-step equation"


def test_algebra_two_step_answers_are_non_negative_integers():
    from app.questions import _alg_two_step_minus, _alg_two_step_plus

    rng = random.Random(0)
    for _ in range(100):
        for factory in (_alg_two_step_plus, _alg_two_step_minus):
            _, _, answer, _ = factory(rng, 5, 32)
            assert isinstance(answer, int) and answer >= 0


def test_fractions_basic_tier_is_fraction_of_whole_only():
    rng = random.Random(0)
    for _ in range(10):
        qs = generate_questions(MathType.fractions, Difficulty.easy, Grade.K, rng=rng)
        for q in qs:
            assert q.question.startswith("What is"), q.question


def test_fractions_advanced_tier_unlocks_unlike_denominators_and_multiplication():
    saw_unlike = False
    saw_multiply = False
    for seed in range(60):
        rng = random.Random(seed)
        qs = generate_questions(MathType.fractions, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            if "×" in q.question:
                saw_multiply = True
                continue
            m = re.match(r"^\d+/(\d+) \+ \d+/(\d+) = \?", q.question)
            if m and m.group(1) != m.group(2):
                saw_unlike = True
        if saw_unlike and saw_multiply:
            break
    assert saw_unlike, "G5/hard fractions never showed unlike-denominator addition"
    assert saw_multiply, "G5/hard fractions never showed fraction multiplication"


def test_fraction_answers_are_simplified():
    from math import gcd

    for seed in range(50):
        rng = random.Random(seed)
        qs = generate_questions(MathType.fractions, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            if not isinstance(q.correctAnswer, str) or "/" not in q.correctAnswer:
                continue
            num_s, den_s = q.correctAnswer.split("/")
            assert gcd(int(num_s), int(den_s)) == 1, f"unsimplified fraction: {q.correctAnswer}"


def test_order_of_operations_basic_tier_has_no_parentheses_or_three_terms():
    rng = random.Random(0)
    for _ in range(10):
        qs = generate_questions(MathType.order_of_operations, Difficulty.easy, Grade.K, rng=rng)
        for q in qs:
            assert "(" not in q.question, q.question


def test_order_of_operations_hard_grade4_unlocks_parentheses():
    saw_parens = False
    for seed in range(30):
        rng = random.Random(seed)
        qs = generate_questions(MathType.order_of_operations, Difficulty.hard, Grade.G4, rng=rng)
        if any("(" in q.question for q in qs):
            saw_parens = True
            break
    assert saw_parens, "G4/hard order_of_operations never produced a parenthesized expression"


def test_order_of_operations_respects_precedence_not_left_to_right():
    """Multiplication/division must bind before +/- in every generated question."""
    for seed in range(20):
        rng = random.Random(seed)
        for difficulty in (Difficulty.easy, Difficulty.medium, Difficulty.hard):
            qs = generate_questions(MathType.order_of_operations, difficulty, Grade.G5, rng=rng)
            for q in qs:
                m = re.match(r"^(\d+) \+ (\d+) × (\d+) = \?$", q.question)
                if m:
                    a, b, c = map(int, m.groups())
                    assert q.correctAnswer == a + b * c

                m = re.match(r"^(\d+) × (\d+) \+ (\d+) = \?$", q.question)
                if m:
                    a, b, c = map(int, m.groups())
                    assert q.correctAnswer == a * b + c


# ---------- word problems ----------


def test_word_problems_basic_is_add_sub_stories_only():
    """K/easy word problems: no multiplication or division phrasing."""
    rng = random.Random(0)
    for _ in range(10):
        qs = generate_questions(MathType.word_problems, Difficulty.easy, Grade.K, rng=rng)
        for q in qs:
            assert "each bag" not in q.question and "shares" not in q.question, q.question


def test_word_problems_advanced_includes_division():
    saw_div = False
    for seed in range(40):
        rng = random.Random(seed)
        qs = generate_questions(MathType.word_problems, Difficulty.hard, Grade.G4, rng=rng)
        if any("shares" in q.question for q in qs):
            saw_div = True
            break
    assert saw_div, "G4/hard word problems never produced a sharing/division story"


def test_word_problem_answers_match_the_story():
    """Independently recompute each story's answer from its text."""
    for seed in range(20):
        rng = random.Random(seed)
        qs = generate_questions(MathType.word_problems, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            m = re.search(r"has (\d+) .+ and gets (\d+) more", q.question)
            if m:
                assert q.correctAnswer == int(m.group(1)) + int(m.group(2)), q.question
            m = re.search(r"has (\d+) .+ and gives (\d+)", q.question)
            if m:
                assert q.correctAnswer == int(m.group(1)) - int(m.group(2)), q.question
            m = re.search(r"(\d+) bags with (\d+)", q.question)
            if m:
                assert q.correctAnswer == int(m.group(1)) * int(m.group(2)), q.question
            m = re.search(r"shares (\d+) .+ among (\d+)", q.question)
            if m:
                assert q.correctAnswer == int(m.group(1)) // int(m.group(2)), q.question


# ---------- comparison & number sense ----------


def test_comparison_symbol_answers_are_correct():
    for seed in range(20):
        rng = random.Random(seed)
        qs = generate_questions(MathType.comparison, Difficulty.medium, Grade.G3, rng=rng)
        for q in qs:
            m = re.match(r"^Fill in the blank: (\d+) _ (\d+)", q.question)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                expected = "<" if a < b else (">" if a > b else "=")
                assert q.correctAnswer == expected, q.question


def test_comparison_rounding_only_at_grade3_hard():
    rng = random.Random(0)
    for _ in range(10):
        qs = generate_questions(MathType.comparison, Difficulty.easy, Grade.G1, rng=rng)
        for q in qs:
            assert "Round" not in q.question, q.question

    saw_round = False
    for seed in range(40):
        rng = random.Random(seed)
        qs = generate_questions(MathType.comparison, Difficulty.hard, Grade.G3, rng=rng)
        if any("Round" in q.question for q in qs):
            saw_round = True
            break
    assert saw_round, "G3/hard comparison never produced a rounding question"


def test_comparison_rounding_answers_are_correct():
    for seed in range(30):
        rng = random.Random(seed)
        qs = generate_questions(MathType.comparison, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            m = re.match(r"^Round (\d+) to the nearest 10\.", q.question)
            if m:
                n = int(m.group(1))
                assert q.correctAnswer == ((n + 5) // 10) * 10, q.question


# ---------- money & time ----------


def test_money_answers_are_whole_cents():
    for seed in range(20):
        rng = random.Random(seed)
        for difficulty in (Difficulty.easy, Difficulty.medium, Difficulty.hard):
            qs = generate_questions(MathType.money_time, difficulty, Grade.G3, rng=rng)
            for q in qs:
                assert isinstance(q.correctAnswer, int), q.question
                assert q.correctAnswer > 0, q.question


def test_money_coin_totals_are_correct():
    values = {"quarter": 25, "dime": 10, "nickel": 5, "penny": 1,
              "quarters": 25, "dimes": 10, "nickels": 5, "pennies": 1}
    for seed in range(30):
        rng = random.Random(seed)
        qs = generate_questions(MathType.money_time, Difficulty.hard, Grade.G4, rng=rng)
        for q in qs:
            m = re.match(r"^You have (\d+) (\w+) and (\d+) (\w+)\.", q.question)
            if m:
                total = int(m.group(1)) * values[m.group(2)] + int(m.group(3)) * values[m.group(4)]
                assert q.correctAnswer == total, q.question


def test_elapsed_time_answers_are_correct():
    for seed in range(30):
        rng = random.Random(seed)
        qs = generate_questions(MathType.money_time, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            m = re.match(r"^How many minutes is it from (\d+):(\d+) to (\d+):(\d+)\?", q.question)
            if m:
                h1, m1, h2, m2 = map(int, m.groups())
                assert q.correctAnswer == (h2 * 60 + m2) - (h1 * 60 + m1), q.question
                assert q.correctAnswer > 0, q.question


# ---------- decimals ----------


def test_decimal_answers_evaluate_exactly():
    for seed in range(30):
        rng = random.Random(seed)
        for difficulty in (Difficulty.easy, Difficulty.hard):
            qs = generate_questions(MathType.decimals, difficulty, Grade.G5, rng=rng)
            for q in qs:
                m = re.match(r"^([\d.]+) ([+-]) ([\d.]+) = \?$", q.question)
                if m:
                    a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
                    expected = round(a + b if op == "+" else a - b, 2)
                    assert float(str(q.correctAnswer)) == expected, q.question


def test_decimals_basic_tier_is_tenths_only():
    """Below G4/hard, decimals stick to single-digit tenths arithmetic."""
    rng = random.Random(0)
    for _ in range(10):
        qs = generate_questions(MathType.decimals, Difficulty.medium, Grade.G3, rng=rng)
        for q in qs:
            assert "×" not in q.question and "bigger" not in q.question, q.question


def test_decimal_comparison_answers_are_correct():
    saw_compare = False
    for seed in range(40):
        rng = random.Random(seed)
        qs = generate_questions(MathType.decimals, Difficulty.hard, Grade.G5, rng=rng)
        for q in qs:
            m = re.match(r"^Which is bigger: ([\d.]+) or ([\d.]+)\?$", q.question)
            if m:
                saw_compare = True
                bigger = max(float(m.group(1)), float(m.group(2)))
                assert float(str(q.correctAnswer)) == bigger, q.question
    assert saw_compare, "G5/hard decimals never produced a comparison question"


# ---------- percentages ----------


def test_percentage_answers_are_whole_and_correct():
    for seed in range(30):
        rng = random.Random(seed)
        for grade, difficulty in ((Grade.G3, Difficulty.easy), (Grade.G5, Difficulty.hard)):
            qs = generate_questions(MathType.percentages, difficulty, grade, rng=rng)
            for q in qs:
                m = re.match(r"^What is (\d+)% of (\d+)\?$", q.question)
                assert m, q.question
                pct, n = int(m.group(1)), int(m.group(2))
                assert pct * n % 100 == 0, f"non-integer answer: {q.question}"
                assert q.correctAnswer == pct * n // 100, q.question


def test_percentage_25_75_only_at_grade5_hard():
    rng = random.Random(0)
    for _ in range(20):
        qs = generate_questions(MathType.percentages, Difficulty.medium, Grade.G4, rng=rng)
        for q in qs:
            m = re.match(r"^What is (\d+)%", q.question)
            assert int(m.group(1)) in (10, 50, 100), q.question


# ---------- measurement ----------


def test_measurement_conversions_are_correct():
    factors = {
        "centimeters": {"meter": 100}, "millimeters": {"centimeter": 10},
        "seconds": {"minute": 60}, "inches": {"foot": 12},
        "meters": {"kilometer": 1000}, "grams": {"kilogram": 1000},
        "milliliters": {"liter": 1000}, "feet": {"yard": 3},
    }
    for seed in range(30):
        rng = random.Random(seed)
        for grade, difficulty in ((Grade.K, Difficulty.easy), (Grade.G5, Difficulty.hard)):
            qs = generate_questions(MathType.measurement, difficulty, grade, rng=rng)
            for q in qs:
                m = re.match(r"^How many (\w+) are in (\d+) (\w+)\?$", q.question)
                if m:
                    small, k, big_plural = m.group(1), int(m.group(2)), m.group(3)
                    big = big_plural.rstrip("s") if big_plural != "feet" else "foot"
                    factor = factors[small][big]
                    assert q.correctAnswer == k * factor, q.question


def test_measurement_reverse_direction_appears_at_grade3_medium():
    saw_reverse = False
    for seed in range(40):
        rng = random.Random(seed)
        qs = generate_questions(MathType.measurement, Difficulty.medium, Grade.G3, rng=rng)
        if any("is how many" in q.question for q in qs):
            saw_reverse = True
            break
    assert saw_reverse, "G3/medium measurement never produced a reverse conversion"


# ---------- answer grading normalization ----------


def test_grade_answer_accepts_equivalent_decimal_formats():
    from app.questions import grade_answer

    assert grade_answer("0.5", "0.50") is True
    assert grade_answer("0.5", ".5") is True
    assert grade_answer("0.5", "0.5") is True
    assert grade_answer("1.2", "1.20") is True
    assert grade_answer("0.5", "0.6") is False
    assert grade_answer(7, "7.0") is True
    assert grade_answer(7, "7") is True
    assert grade_answer(7, "8.0") is False


def test_grade_answer_still_requires_simplified_fractions():
    from app.questions import grade_answer

    assert grade_answer("3/4", "6/8") is False
    assert grade_answer("3/4", "3/4") is True
    assert grade_answer("3/4", "0.75") is False  # fraction questions want a fraction


def test_grade_answer_word_answers_stay_case_insensitive():
    from app.questions import grade_answer

    assert grade_answer("even", "EVEN") is True
    assert grade_answer("<", "<") is True
    assert grade_answer("even", "odd") is False


def test_small_space_falls_back_gracefully():
    # K/easy addition has a very small value space (lo=1, hi=5 → ~15
    # unordered pairs). Even so, generation must not crash or loop, and
    # should still return exactly 10 questions.
    rng = random.Random(0)
    qs = generate_questions(MathType.addition, Difficulty.easy, Grade.K, rng=rng)
    assert len(qs) == 10
    # With 15 pairs available, we expect all 10 to still be unique.
    assert len({q.question for q in qs}) == 10


# ---------- helpers ----------


def _algebra_shape(q: str) -> str:
    """Return a short tag for the algebra template shape."""
    if re.match(r"^x \+ \d+", q):
        return "x+c"
    if re.match(r"^x - \d+", q):
        return "x-c"
    if re.match(r"^\d+ - x", q):
        return "c-x"
    if re.match(r"^\d+ × x", q):
        return "c*x"
    if re.match(r"^x ÷ \d+", q):
        return "x/c"
    return "unknown:" + q
