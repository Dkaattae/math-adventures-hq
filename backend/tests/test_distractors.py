"""Wrong answers that are worth offering (PROJECT_PLAN §2.1).

Three faults were reported from play, all in the same place:

1. a "write <, > or =" question offered `128 · < · 127 · >`, so three of
   the four options weren't even the right kind of thing;
2. "Is 41 even or odd?" offered `< · 21 · 18 · odd` — one word among
   three numbers gives the answer away without any maths;
3. numeric distractors were all near misses (`480 · 470 · 479 · 477`).
   Nothing computes 479, so it tests nothing; the wrong answers that
   teach are the ones a real mistake lands on — 48, 4800, 500.

These tests pin the fixes at the level a player sees them: same-domain
options, small vocabularies offered whole, and misconception-shaped
numbers with at most one near miss.
"""
from __future__ import annotations

import random

import pytest

from app.distractors import (
    EVEN_ODD,
    SYMBOLS,
    alternatives_in_text,
    build_options,
    integer_distractors,
    kind_of,
    same_kind,
)
from app.models import AnswerMode, Difficulty, Grade, MathType
from app.questions import generate_questions

RNG = lambda seed=0: random.Random(seed)  # noqa: E731


# ---------- domains never mix ----------


def test_a_comparison_offers_only_comparison_symbols():
    options = build_options(">", "Write <, > or = in the blank:\n\n8! _ 2^6", [128, 127], RNG())
    assert sorted(options) == sorted(SYMBOLS)


def test_even_or_odd_offers_only_even_and_odd():
    options = build_options("odd", "Is 41 even or odd?", ["<", 21, 18], RNG())
    assert sorted(options) == sorted(EVEN_ODD)


def test_a_number_question_never_offers_a_symbol():
    options = build_options(162, "How many seconds is 2 minutes and 42 seconds?", ["<", "odd"], RNG())
    assert all(kind_of(o) == "integer" for o in options), options


def test_a_word_question_never_offers_a_number():
    options = build_options(
        "meters", "Which unit would you use to measure a swimming pool?", [9, 14, "<"], RNG()
    )
    assert all(kind_of(o) == "word" for o in options), options


def test_fractions_and_decimals_count_as_the_same_kind():
    """Both are "a number you could compare", so offering 0.5 against
    1/2's siblings is fair game; offering "meters" is not."""
    assert same_kind("1/2", "0.5")
    assert not same_kind("1/2", "meters")
    assert not same_kind("7", "<")


# ---------- the question's own alternatives are the best options ----------


def test_a_bulleted_question_offers_exactly_those_bullets():
    text = "Which unit would you use to measure the school playground?\n\n• grams\n• millimeters\n• meters"
    assert sorted(alternatives_in_text(text)) == ["grams", "meters", "millimeters"]
    options = build_options("meters", text, [], RNG())
    assert sorted(options) == ["grams", "meters", "millimeters"]


def test_pick_the_biggest_offers_the_numbers_it_listed():
    text = "Which number is the biggest: 21, 2 or 17?"
    options = build_options(21, text, [99], RNG())
    assert "2" in options and "17" in options, options
    assert "21" in options


def test_a_sentence_that_merely_contains_or_is_not_a_list():
    """"How many seconds are in 8 minutes?" must not offer 8."""
    assert alternatives_in_text("How many seconds are in 8 minutes?") == []
    options = build_options(480, "How many seconds are in 8 minutes?", [], RNG())
    assert "8" not in options, options


# ---------- numbers a real mistake would produce ----------


def test_a_method_error_is_always_among_the_first_offered():
    """A dropped zero, an extra zero, a doubling or a halving — the
    distractor a kid's own working would produce — leads the list."""
    for seed in range(20):
        first = integer_distractors(480, random.Random(seed))[0]
        assert first in {"48", "4800", "240", "960"}, first


def test_halving_and_doubling_show_up():
    options = set(integer_distractors(180, RNG(2)))
    assert {"90", "360"} & options, options


def test_round_number_guesses_show_up():
    """The user's example: 180 minutes should sit near 200, not 179."""
    options = set(integer_distractors(180, RNG(3)))
    assert {"200", "150", "100"} & options, options


def test_at_most_one_near_miss_is_offered():
    """`480 · 479 · 477 · 470` tested nothing. One near miss is a fair
    trap; three is noise."""
    for seed in range(30):
        options = build_options(480, "How many seconds are in 8 minutes?", [], random.Random(seed))
        near = [o for o in options if o != "480" and abs(int(o) - 480) <= 3]
        assert len(near) <= 1, options


def test_small_answers_still_use_neighbours():
    """3 vs 30 isn't a misconception, it's a different question — so for
    single digits the neighbours are the sensible distractors."""
    options = build_options(3, "1 + 2 = ?", [], RNG(4))
    assert all(0 < int(o) <= 12 for o in options), options


def test_distractors_are_never_negative_or_zero():
    for n in (1, 2, 5, 10, 100):
        for seed in range(10):
            options = build_options(n, f"{n} + 0 = ?", [], random.Random(seed))
            assert all(int(o) > 0 for o in options), (n, options)


def test_clock_answers_offer_other_times():
    options = build_options("5:20", "What time does the film finish?", [], RNG(5))
    assert all(kind_of(o) == "clock" for o in options), options
    assert "5:20" in options


# ---------- as served in a real quiz ----------


def _mc(math_type, grade, difficulty, seed=0):
    return generate_questions(
        math_type, difficulty, grade,
        answer_mode=AnswerMode.multiple_choice, rng=random.Random(seed),
    )


@pytest.mark.parametrize("grade", [Grade.G2, Grade.G4, Grade.G5], ids=lambda g: g.value)
def test_comparison_quizzes_never_mix_symbols_with_numbers(grade):
    for seed in range(15):
        for q in _mc(MathType.comparison, grade, Difficulty.hard, seed):
            if str(q.correctAnswer) in SYMBOLS:
                assert sorted(q.options) == sorted(SYMBOLS), (q.question, q.options)
            else:
                assert not set(q.options) & set(SYMBOLS), (q.question, q.options)


@pytest.mark.parametrize("math_type", list(MathType), ids=lambda t: t.value)
def test_no_quiz_gives_the_answer_away_by_shape(math_type):
    """Across every topic: an option list must not have exactly one
    option of one kind and the rest of another, which is what made the
    old lists guessable."""
    for grade in (Grade.G3, Grade.G5):
        for seed in range(6):
            for q in _mc(math_type, grade, Difficulty.medium, seed):
                kinds = {kind_of(str(o)) for o in q.options}
                numeric = {"integer", "decimal", "fraction"}
                assert len(kinds) == 1 or kinds <= numeric, (q.question, q.options)


@pytest.mark.parametrize("math_type", list(MathType), ids=lambda t: t.value)
def test_every_question_still_gets_options(math_type):
    """Tightening the rules must not leave a multiple-choice quiz with
    typed questions in it."""
    for grade in (Grade.G2, Grade.G5):
        for seed in range(6):
            for q in _mc(math_type, grade, Difficulty.hard, seed):
                assert q.options, (q.question, q.correctAnswer)
                assert str(q.correctAnswer) in q.options


def test_pick_the_biggest_expression_offers_the_other_answers():
    """"Which one is the biggest: (8+11)×8, (15+14)×5, or (14+12)×7?"
    wants a number back, and the numbers worth offering are what the
    other two expressions come to — that's what a kid who worked out the
    wrong one would write."""
    text = (
        "Which one is the biggest: (8 + 11) × 8, (15 + 14) × 5, or (14 + 12) × 7?"
        "\n\nWrite the answer as a number."
    )
    options = build_options(182, text, [], RNG())
    assert sorted(options) == ["145", "152", "182"], options


def test_expression_values_ignores_anything_it_cannot_parse():
    from app.distractors import expression_values

    assert expression_values(["2 + 3", "meters", "4 × 5"]) == [5, 20]
    assert expression_values(["__import__('os')"]) == []
