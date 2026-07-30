"""Percentages, measurement and money & time: shapes that grow with grade.

All three used to be one-line templates whose only difficulty knob was
the size of the numbers — grade 5 percentages was "What is 10% of 350?",
grade 5 money was "a sticker costs 70¢". These tests pin the ladders
down, and re-derive the answers from the question text rather than
trusting the generators.
"""
from __future__ import annotations

import random
import re

import pytest

from app import measurement, money_time, percentages
from app.models import Difficulty, Grade, MathType
from app.questions import _pick_factory, generate_questions

SEEDS = range(30)


def _questions(math_type, grade, difficulty, seed=0):
    return generate_questions(math_type, difficulty, grade, rng=random.Random(seed))


def _all(math_type, grade, difficulty):
    for seed in SEEDS:
        yield from _questions(math_type, grade, difficulty, seed)


def _tier(math_type, grade, difficulty):
    return _pick_factory(math_type, difficulty, grade).tier


# ---------- percentages ----------


@pytest.mark.parametrize(
    "grade,difficulty,expected",
    [
        (Grade.G4, Difficulty.easy, "basic"),
        (Grade.G4, Difficulty.medium, "applied"),
        (Grade.G4, Difficulty.hard, "applied"),
        (Grade.G5, Difficulty.easy, "applied"),
        (Grade.G5, Difficulty.medium, "advanced"),
        (Grade.G5, Difficulty.hard, "advanced"),
    ],
)
def test_percentage_tiers(grade, difficulty, expected):
    assert _tier(MathType.percentages, grade, difficulty) == expected


def test_grade_five_percentages_are_more_than_percent_of_a_number():
    """The old topic only ever asked "what is X% of N?"."""
    questions = list(_all(MathType.percentages, Grade.G5, Difficulty.hard))
    plain = [q for q in questions if re.match(r"^What is \d+% of \d+\?$", q.question)]
    assert len(plain) / len(questions) < 0.25, "grade 5 is still mostly the plain question"
    text = " ".join(q.question for q in questions)
    assert "% off" in text, "no discount questions"
    assert "tip" in text, "no tip questions"
    assert "of a number is" in text, "never runs the percentage backwards"


def test_no_nonsense_percentages():
    """"100% off" is free, and "100% of a number is 7" gives it away."""
    for q in _all(MathType.percentages, Grade.G5, Difficulty.hard):
        assert "100% off" not in q.question, q.question
        assert not q.question.startswith("100% of a number"), q.question


def test_percentage_answers_are_whole_and_positive():
    for difficulty in Difficulty:
        for q in _all(MathType.percentages, Grade.G5, difficulty):
            assert isinstance(q.correctAnswer, int), q.question
            assert q.correctAnswer >= 0, q.question


def test_discount_answers_are_the_price_after_the_cut():
    checked = 0
    for q in _all(MathType.percentages, Grade.G5, Difficulty.easy):
        m = re.match(r"^A .+ costs \$(\d+)\. Today it is (\d+)% off\.", q.question)
        if not m:
            continue
        price, percent = int(m.group(1)), int(m.group(2))
        assert q.correctAnswer == price - price * percent // 100, q.question
        checked += 1
    assert checked > 0


def test_double_discount_is_not_the_two_percentages_added():
    """50% then 20% is 60% of the price, not 30% — that's the whole point."""
    checked = 0
    for q in _all(MathType.percentages, Grade.G5, Difficulty.hard):
        m = re.match(
            r"^A .+ costs \$(\d+)\. It is (\d+)% off in the sale\.\n\n"
            r"At the till, another (\d+)% comes off",
            q.question,
        )
        if not m:
            continue
        price, first, second = (int(g) for g in m.groups())
        after_first = price - price * first // 100
        assert q.correctAnswer == after_first - after_first * second // 100, q.question
        naive = price - price * (first + second) // 100
        assert q.correctAnswer != naive or first + second >= 100, q.question
        checked += 1
    assert checked > 0


def test_tip_makes_the_bill_bigger():
    checked = 0
    for q in _all(MathType.percentages, Grade.G5, Difficulty.easy):
        m = re.match(r"^A .+ costs \$(\d+)\. A (\d+)% tip is added\.", q.question)
        if not m:
            continue
        price, percent = int(m.group(1)), int(m.group(2))
        assert q.correctAnswer == price + price * percent // 100 > price, q.question
        checked += 1
    assert checked > 0


# ---------- measurement ----------


@pytest.mark.parametrize(
    "grade,difficulty,expected",
    [
        (Grade.G2, Difficulty.easy, "basic"),
        (Grade.G2, Difficulty.medium, "convert"),
        (Grade.G3, Difficulty.medium, "convert"),
        (Grade.G3, Difficulty.hard, "applied"),
        (Grade.G4, Difficulty.medium, "applied"),
        (Grade.G5, Difficulty.easy, "applied"),
    ],
)
def test_measurement_tiers(grade, difficulty, expected):
    assert _tier(MathType.measurement, grade, difficulty) == expected


def test_grade_five_measurement_is_more_than_a_lookup():
    questions = list(_all(MathType.measurement, Grade.G5, Difficulty.hard))
    bare = [
        q for q in questions
        if re.match(r"^(How many \w+ are in \d+ \w+\?|\d+ \w+ is how many \w+\?)$", q.question)
    ]
    assert len(bare) / len(questions) < 0.4, "grade 5 is still mostly bare conversions"
    text = " ".join(q.question for q in questions)
    assert "cut into pieces" in text, "no convert-then-divide questions"
    assert "_" in text, "no cross-unit comparisons"


def test_measurement_answers_are_whole_and_positive():
    for grade in (Grade.G2, Grade.G3, Grade.G4, Grade.G5):
        for q in _all(MathType.measurement, grade, Difficulty.hard):
            if isinstance(q.correctAnswer, int):
                assert q.correctAnswer >= 0, q.question


def test_cutting_answers_convert_before_dividing():
    checked = 0
    for q in _all(MathType.measurement, Grade.G5, Difficulty.hard):
        m = re.match(
            r"^A \w+ is (\d+) meters long\. It is cut into pieces (\d+) centimeters long",
            q.question,
        )
        if not m:
            continue
        whole, piece = int(m.group(1)), int(m.group(2))
        assert q.correctAnswer == whole * 100 // piece, q.question
        checked += 1
    assert checked > 0


def test_cross_unit_comparisons_are_right():
    # Keyed by (small, big) pair, not by unit: "minutes" is 60 seconds
    # but a sixtieth of an hour, so a flat per-unit table can't say what
    # a minute is worth without knowing what it's being compared to.
    pairs = {
        ("centimeters", "meters"): 100,
        ("millimeters", "centimeters"): 10,
        ("seconds", "minutes"): 60,
        ("meters", "kilometers"): 1000,
        ("grams", "kilograms"): 1000,
        ("milliliters", "liters"): 1000,
        ("minutes", "hours"): 60,
    }
    checked = 0
    for q in _all(MathType.measurement, Grade.G5, Difficulty.hard):
        m = re.search(r"blank:\n\n(\d+) (\w+) _ (\d+) (\w+)$", q.question)
        if not m:
            continue
        a, unit_a, b, unit_b = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
        if (unit_a, unit_b) in pairs:            # a is the small unit
            left, right = a, b * pairs[(unit_a, unit_b)]
        else:
            left, right = a * pairs[(unit_b, unit_a)], b
        expected = "<" if left < right else (">" if left > right else "=")
        assert q.correctAnswer == expected, q.question
        checked += 1
    assert checked > 0


def test_containers_hold_something_they_could_actually_hold():
    """A jug does not hold kilometers."""
    for grade in (Grade.G4, Grade.G5):
        for q in _all(MathType.measurement, grade, Difficulty.hard):
            m = re.match(r"^One (\w+) holds \d+ (\w+)\.", q.question)
            if m:
                assert m.group(2).rstrip("s") not in {
                    "meter", "kilometer", "centimeter", "millimeter", "inch", "foot",
                }, q.question


def test_lower_grades_never_get_the_two_step_shapes():
    for q in _all(MathType.measurement, Grade.G2, Difficulty.easy):
        assert "cut into pieces" not in q.question, q.question
        assert "poured" not in q.question, q.question


# ---------- money & time ----------


@pytest.mark.parametrize(
    "grade,difficulty,expected",
    [
        (Grade.G1, Difficulty.easy, "basic"),
        (Grade.G1, Difficulty.medium, "counting"),
        (Grade.G2, Difficulty.medium, "counting"),
        (Grade.G3, Difficulty.medium, "reasoning"),
        (Grade.G4, Difficulty.easy, "reasoning"),
        (Grade.G4, Difficulty.hard, "planning"),
        (Grade.G5, Difficulty.easy, "planning"),
    ],
)
def test_money_time_tiers(grade, difficulty, expected):
    assert _tier(MathType.money_time, grade, difficulty) == expected


def test_grade_five_money_is_not_change_from_a_dollar():
    questions = list(_all(MathType.money_time, Grade.G5, Difficulty.hard))
    text = " ".join(q.question for q in questions)
    assert "What time does it finish" in text, "no clock-arithmetic questions"
    assert "FEWEST" in text, "no fewest-coins questions"
    sticker = [q for q in questions if "and you pay" in q.question]
    assert not sticker, "grade 5 is still asking for change from a coin"


def test_fewest_coins_really_is_the_fewest():
    """Brute-force the minimum and compare — greedy is optimal for these
    coins, but the test shouldn't assume that."""
    from itertools import product

    checked = 0
    for q in _all(MathType.money_time, Grade.G5, Difficulty.hard):
        m = re.search(r"makes (\d+)¢", q.question)
        if not m:
            continue
        amount = int(m.group(1))
        best = min(
            q_ + d + n + p
            for q_, d, n, p in product(range(amount // 25 + 1), range(amount // 10 + 1),
                                       range(amount // 5 + 1), range(5))
            if q_ * 25 + d * 10 + n * 5 + p == amount
        )
        assert q.correctAnswer == best, q.question
        checked += 1
    assert checked > 0


def test_clock_answers_are_valid_times():
    checked = 0
    for q in _all(MathType.money_time, Grade.G5, Difficulty.hard):
        if "Write it like" not in q.question:
            continue
        assert isinstance(q.correctAnswer, str), q.question
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", q.correctAnswer)
        assert m, q.correctAnswer
        assert 1 <= int(m.group(1)) <= 12 and 0 <= int(m.group(2)) <= 59, q.correctAnswer
        checked += 1
    assert checked > 0


def test_finish_time_is_the_start_plus_the_duration():
    checked = 0
    for q in _all(MathType.money_time, Grade.G5, Difficulty.hard):
        m = re.match(
            r"^The .+ (?:starts|leaves|kicks off) at (\d{1,2}):(\d{2}) and lasts (\d+) minutes",
            q.question,
        )
        if not m:
            continue
        hour, minute, minutes = (int(g) for g in m.groups())
        total = hour * 60 + minute + minutes
        expected = f"{(total // 60) % 12 or 12}:{total % 60:02d}"
        assert q.correctAnswer == expected, q.question
        checked += 1
    assert checked > 0


def test_clock_answers_accept_a_leading_zero():
    from app.questions import grade_answer

    assert grade_answer("5:20", "05:20") is True
    assert grade_answer("5:20", "5:20") is True
    assert grade_answer("5:20", "5:21") is False
    assert grade_answer("5:20", "520") is False
    # Word answers are untouched by the clock rule.
    assert grade_answer("meters", "METERS") is True


def test_enough_money_answers_the_gap_either_way():
    checked = 0
    for q in _all(MathType.money_time, Grade.G5, Difficulty.hard):
        m = re.match(r"^A .+ costs (\d+)¢\. You have (\d+)¢\.", q.question)
        if not m:
            continue
        price, purse = int(m.group(1)), int(m.group(2))
        assert q.correctAnswer == abs(purse - price), q.question
        assert ("short are you" in q.question) == (purse < price), q.question
        checked += 1
    assert checked > 0


# ---------- variety, across all three ----------


@pytest.mark.parametrize(
    "math_type,grade,difficulty",
    [
        (MathType.percentages, Grade.G5, Difficulty.hard),
        (MathType.measurement, Grade.G5, Difficulty.hard),
        (MathType.money_time, Grade.G5, Difficulty.hard),
    ],
)
def test_a_quiz_rotates_through_its_shapes(math_type, grade, difficulty):
    for seed in (0, 1, 2, 3):
        questions = _questions(math_type, grade, difficulty, seed)
        openers = {q.question.split("\n")[0][:25] for q in questions}
        assert len(openers) >= 5, (math_type, sorted(openers))


@pytest.mark.parametrize(
    "module,count", [(percentages, 3), (measurement, 3), (money_time, 4)]
)
def test_every_tier_offers_several_shapes(module, count):
    assert len(module.TIERS) == count
    for tier, builders in module.TIERS.items():
        assert len(builders) >= 3, tier
