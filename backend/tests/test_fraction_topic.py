"""The fractions topic ladder: pictures → wholes → decimals → advanced.

Answers are re-solved in test_answer_verification; this file pins which
level sees what, how the new answer shapes are graded, and the options
multiple choice offers for them.
"""
from __future__ import annotations

import random
import re

import pytest

from app import fraction_questions as fq
from app.distractors import build_options, kind_of
from app.models import AnswerMode, Difficulty, Grade, MathType
from app.questions import _pick_factory, answer_kind, generate_questions, grade_answer


def _quiz(grade, difficulty, seed=0, **kw):
    return generate_questions(MathType.fractions, difficulty, grade, rng=random.Random(seed), **kw)


@pytest.mark.parametrize(
    "grade,difficulty,expected",
    [
        (Grade.G2, Difficulty.easy, "pictures"),
        (Grade.G2, Difficulty.medium, "building"),
        (Grade.G2, Difficulty.hard, "building"),
        (Grade.G3, Difficulty.easy, "pictures"),
        (Grade.G3, Difficulty.medium, "wholes"),
        (Grade.G4, Difficulty.easy, "wholes"),
        (Grade.G4, Difficulty.medium, "decimals"),
        (Grade.G4, Difficulty.hard, "advanced"),
        (Grade.G5, Difficulty.easy, "decimals"),
        (Grade.G5, Difficulty.medium, "advanced"),
        (Grade.G5, Difficulty.hard, "advanced"),
    ],
)
def test_tier_ladder(grade, difficulty, expected):
    assert _pick_factory(MathType.fractions, difficulty, grade).tier == expected


def _texts(grade, difficulty, seeds=range(15)):
    return " ".join(q.question for s in seeds for q in _quiz(grade, difficulty, s))


def test_each_rung_brings_its_own_skill():
    assert "shaded" in _texts(Grade.G2, Difficulty.easy)
    assert "missing number" in _texts(Grade.G2, Difficulty.medium)
    g3 = _texts(Grade.G3, Difficulty.medium)
    assert "remainder" in g3 and "mixed number" in g3
    g4 = _texts(Grade.G4, Difficulty.medium)
    assert "as a decimal" in g4 and re.search(r"Write \d+\.\d+ as a fraction", g4)
    assert "improper fraction" in _texts(Grade.G5, Difficulty.hard)
    # Decimals wait until the child has met them (decimals unlock at grade 3,
    # tenths and hundredths properly at grade 4).
    assert "decimal" not in _texts(Grade.G3, Difficulty.hard)


def test_pictures_fade_out_as_the_grades_go_up():
    def share(grade, difficulty):
        qs = [q for s in range(15) for q in _quiz(grade, difficulty, s)]
        return sum(bool(q.figure) for q in qs) / len(qs)

    assert share(Grade.G2, Difficulty.easy) == 1
    assert share(Grade.G3, Difficulty.medium) > 0.5
    assert share(Grade.G5, Difficulty.hard) == 0


def test_more_than_one_pie_for_an_improper_fraction():
    for seed in range(40):
        for q in _quiz(Grade.G3, Difficulty.medium, seed):
            if "remainder" in q.question and q.figure:
                num, den = (int(x) for x in q.figure[4:].split("/"))
                assert num > den, q.figure
                return
    pytest.fail("no pictured remainder question")


# ---------- grading the new answer shapes ----------


@pytest.mark.parametrize("typed", ["2 R 3", "2r3", "2 r 3", "2 R3", "2 rem 3", "2 remainder 3", " 2  R  3 "])
def test_remainder_answers_forgive_how_they_are_typed(typed):
    assert grade_answer("2 R 3", typed)


@pytest.mark.parametrize("typed", ["3 R 2", "2", "23", "2 R 4", "13/5", "2 3/5"])
def test_remainder_answers_still_need_the_right_numbers(typed):
    assert not grade_answer("2 R 3", typed)


@pytest.mark.parametrize("typed", ["2 3/5", "2  3/5", "2 and 3/5", "2-3/5", "2 + 3/5", "2 3 / 5"])
def test_mixed_numbers_forgive_spacing_and_and(typed):
    assert grade_answer("2 3/5", typed)


@pytest.mark.parametrize("typed", ["13/5", "2.6", "23/5", "2 6/10", "3 3/5", "2"])
def test_mixed_numbers_still_want_a_mixed_number_in_simplest_form(typed):
    assert not grade_answer("2 3/5", typed)


def test_decimal_from_a_fraction_accepts_the_usual_spellings():
    assert grade_answer("0.25", ".25") and grade_answer("0.25", "0.250")
    assert not grade_answer("0.25", "1/4")


def test_new_answers_use_the_full_keyboard_except_decimals():
    assert answer_kind("2 R 3").value == "text"
    assert answer_kind("2 3/5").value == "text"
    assert answer_kind("0.25").value == "decimal"


# ---------- multiple choice ----------


def test_mixed_and_remainder_answers_get_their_own_kind_of_options():
    assert kind_of("2 3/5") == "mixed" and kind_of("2 R 3") == "remainder"
    for grade, difficulty in [(Grade.G3, Difficulty.medium), (Grade.G5, Difficulty.hard)]:
        for seed in range(20):
            for q in _quiz(grade, difficulty, seed, answer_mode=AnswerMode.multiple_choice):
                kind = kind_of(str(q.correctAnswer))
                if kind not in ("mixed", "remainder"):
                    continue
                assert q.options and str(q.correctAnswer) in q.options, q.question
                assert {kind_of(o) for o in q.options} == {kind}, (q.question, q.options)


def test_comparison_options_are_the_two_fractions_shown():
    text = "Which is bigger: 1/3 or 1/5?"
    options = build_options("1/3", text, ["3/4", "2"], random.Random(0))
    assert sorted(options) == ["1/3", "1/5"]


# ---------- helpers ----------


def test_helpers():
    assert fq.simplify(6, 8) == "3/4" and fq.simplify(8, 4) == "2"
    assert fq.mixed(13, 5) == "2 3/5" and fq.mixed(12, 8) == "1 1/2" and fq.mixed(10, 5) == "2"
    assert fq.decimal_str(1, 4) == "0.25" and fq.decimal_str(7, 4) == "1.75"
    assert fq.decimal_str(1, 8) == "0.125" and fq.decimal_str(1, 3) is None
    assert fq.fits_pie(13, 5) and not fq.fits_pie(1, 16) and not fq.fits_pie(20, 5)


# ---------- fractions in mixed quizzes ----------


@pytest.mark.parametrize("grade", [Grade.G2, Grade.G3, Grade.G4, Grade.G5])
@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_mixed_quizzes_keep_three_seats_for_fractions(grade, difficulty):
    for seed in range(15):
        qs = generate_questions(MathType.mixed, difficulty, grade, rng=random.Random(seed))
        fractions = [q for q in qs if q.topic == MathType.fractions]
        assert len(fractions) >= 3, [q.question for q in qs]
        # Drawn from one deck, so they aren't three of the same shape.
        shapes = {re.sub(r"\d+", "#", q.question) for q in fractions}
        assert len(shapes) >= 2, [q.question for q in fractions]


def test_mixed_fraction_seats_move_around_the_quiz():
    positions = set()
    for seed in range(20):
        qs = generate_questions(MathType.mixed, Difficulty.medium, Grade.G3, rng=random.Random(seed))
        positions |= {q.id for q in qs if q.topic == MathType.fractions}
    assert positions == set(range(10))


@pytest.mark.parametrize("grade", [Grade.K, Grade.G1])
def test_mixed_quizzes_before_grade_two_have_no_fractions(grade):
    for seed in range(15):
        for q in generate_questions(MathType.mixed, Difficulty.hard, grade, rng=random.Random(seed)):
            assert q.topic != MathType.fractions, q.question
