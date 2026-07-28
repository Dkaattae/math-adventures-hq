"""Real-life word problem scenes.

The point of the rewrite is that the words carry work: each scene holds
facts the answer doesn't need, and the tiers step up from short stories
to prices to sale offers. These tests pin that down rather than the
wording, which is meant to keep changing.
"""
from __future__ import annotations

import random
import re

import pytest

from app import word_problems as wp
from app.models import Difficulty, Grade, MathType
from app.questions import _pick_factory, generate_questions, time_limit_seconds

SEEDS = range(40)


def _questions(grade: Grade, difficulty: Difficulty, seed: int = 0):
    return generate_questions(MathType.word_problems, difficulty, grade, rng=random.Random(seed))


# ---------- tiers ----------


@pytest.mark.parametrize(
    "grade,difficulty,expected",
    [
        (Grade.K, Difficulty.easy, wp.make_simple),
        (Grade.K, Difficulty.hard, wp.make_simple_wide),      # never a list at K
        (Grade.G1, Difficulty.easy, wp.make_simple),
        (Grade.G1, Difficulty.hard, wp.make_list),
        (Grade.G2, Difficulty.easy, wp.make_list),
        (Grade.G2, Difficulty.hard, wp.make_prices),
        (Grade.G3, Difficulty.easy, wp.make_list),
        (Grade.G3, Difficulty.medium, wp.make_prices),
        (Grade.G4, Difficulty.hard, wp.make_prices),
        (Grade.G5, Difficulty.easy, wp.make_prices),
        (Grade.G5, Difficulty.hard, wp.make_deals),
    ],
)
def test_tier_ladder(grade, difficulty, expected):
    assert _pick_factory(MathType.word_problems, difficulty, grade) is expected


def test_kindergarten_questions_stay_one_line():
    """At K the reading is the hard part — no multi-line scenes."""
    for seed in SEEDS:
        for q in _questions(Grade.K, Difficulty.easy, seed):
            assert "\n" not in q.question
            assert len(q.question.split()) < 25


# ---------- the sifting that makes them harder ----------


def test_list_scenes_carry_information_the_answer_does_not_need():
    """Every list question shows more lines than it asks about."""
    for seed in SEEDS:
        for q in _questions(Grade.G2, Difficulty.easy, seed):
            lines = [ln for ln in q.question.splitlines() if ln.startswith("•")]
            assert len(lines) >= 4, q.question
            quantities = [int(re.match(r"• (\d+)", ln).group(1)) for ln in lines]
            # The answer never uses every line, so it's always less than
            # the total of the list (that's the distractor doing its job).
            assert q.correctAnswer < sum(quantities), q.question


def test_priced_scenes_include_an_irrelevant_fact_and_say_tax_free():
    for seed in SEEDS:
        for q in _questions(Grade.G3, Difficulty.medium, seed):
            assert "There is no tax to add." in q.question
            # A flavour sentence or a "pays with a $N note" line is always
            # present alongside it.
            body = q.question.split("\n\n")[2]
            assert len(body.split(". ")) >= 2, body


def test_price_lines_show_a_quantity_and_a_unit_price():
    for seed in SEEDS:
        for q in _questions(Grade.G4, Difficulty.medium, seed):
            for line in q.question.splitlines():
                if line.startswith("•"):
                    assert re.match(r"• \d+ .+ — \$\d+ each", line), line


def test_deal_scenes_always_offer_a_real_saving():
    """A "2 for $5" that costs more than 2 × $3 would be a lie."""
    for seed in SEEDS:
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            deal_line = next(ln for ln in q.question.splitlines() if ln.startswith("•"))
            n_for = re.search(r"\$(\d+) each, or (\d+) for \$(\d+)", deal_line)
            if n_for:
                unit, count, deal = (int(g) for g in n_for.groups())
                assert deal < unit * count, deal_line
            else:
                assert "get 1 free" in deal_line, deal_line


# ---------- answers stay typable ----------


def test_answers_are_whole_non_negative_numbers_everywhere():
    for grade in Grade:
        for difficulty in Difficulty:
            for seed in SEEDS:
                for q in generate_questions(
                    MathType.word_problems, difficulty, grade, rng=random.Random(seed)
                ):
                    assert isinstance(q.correctAnswer, int), q.question
                    assert q.correctAnswer >= 0, q.question


def test_no_line_reads_one_apples():
    """Quantities on list lines are always plural."""
    for grade in (Grade.K, Grade.G2, Grade.G3, Grade.G5):
        for difficulty in Difficulty:
            for seed in SEEDS:
                for q in generate_questions(
                    MathType.word_problems, difficulty, grade, rng=random.Random(seed)
                ):
                    for line in q.question.splitlines():
                        if line.startswith("• 1 "):
                            pytest.fail(f"singular quantity on a plural noun: {line}")


def test_a_quiz_uses_several_different_scenes_and_names():
    """Ten questions shouldn't all be the same shop with the same kid."""
    for grade, difficulty in [(Grade.G2, Difficulty.easy), (Grade.G5, Difficulty.hard)]:
        questions = _questions(grade, difficulty, seed=3)
        titles = {q.question.splitlines()[0] for q in questions}
        assert len(titles) >= 6, titles


# ---------- the maths behind the deals ----------


@pytest.mark.parametrize(
    "qty,unit,deal_n,deal_price,expected",
    [
        (6, 3, 2, 5, 15),      # 3 lots of 2
        (7, 3, 2, 5, 18),      # 3 lots + 1 at full price
        (2, 4, 3, 10, 8),      # not enough for the offer
        (9, 4, 3, 10, 30),
    ],
)
def test_deal_cost_charges_full_price_for_leftovers(qty, unit, deal_n, deal_price, expected):
    assert wp._deal_cost(qty, unit, deal_n, deal_price) == expected


@pytest.mark.parametrize(
    "qty,unit,buy_n,expected",
    [
        (3, 5, 2, 10),   # buy 2 get 1 free → pay for 2
        (6, 5, 2, 20),   # two full groups → pay for 4
        (4, 5, 3, 15),   # buy 3 get 1 free → pay for 3
        (2, 5, 2, 10),   # not enough for the offer
    ],
)
def test_free_item_cost(qty, unit, buy_n, expected):
    assert wp._free_cost(qty, unit, buy_n) == expected


def test_explanations_show_the_working():
    for seed in SEEDS:
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            assert "$" in q.explanation
            assert q.explanation.strip().endswith("🏷️")


# ---------- reading time ----------


def test_one_line_questions_keep_the_original_fifteen_seconds():
    assert time_limit_seconds("7 + 5 = ?") == 15
    assert time_limit_seconds(" ".join(["word"] * 25)) == 15


def test_long_scenes_earn_more_time():
    short = time_limit_seconds(" ".join(["word"] * 25))
    long = time_limit_seconds(" ".join(["word"] * 65))
    assert long > short
    assert time_limit_seconds(" ".join(["word"] * 1000)) <= 120


def test_word_problem_scenes_get_more_time_than_a_bare_sum():
    scene = _questions(Grade.G5, Difficulty.hard, seed=1)[0]
    assert time_limit_seconds(scene.question) > 15


def test_api_sends_the_per_question_time(client, signup):
    signup(client, "Kid")
    body = client.post(
        "/api/quizzes",
        json={"username": "Kid", "grade": "5", "mathType": "word_problems", "difficulty": "hard"},
    ).json()
    assert all(q["timeLimitSeconds"] > 15 for q in body["questions"])

    plain = client.post(
        "/api/quizzes",
        json={"username": "Kid", "grade": "2", "mathType": "addition", "difficulty": "easy"},
    ).json()
    assert all(q["timeLimitSeconds"] == 15 for q in plain["questions"])
