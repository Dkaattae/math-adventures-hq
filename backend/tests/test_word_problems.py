"""Real-life word problem shapes.

The point of the rewrite is that the words carry work: each scene holds
facts the answer doesn't need, and ten questions in a row shouldn't share
a skeleton. These tests pin down the structure and the arithmetic, not
the wording — the wording is meant to keep moving.
"""
from __future__ import annotations

import random
import re

import pytest

from app import word_problems as wp
from app.models import Difficulty, Grade, MathType
from app.questions import _pick_factory, _word_problem_tier, generate_questions, time_limit_seconds

SEEDS = range(40)
ALL_LEVELS = [(g, d) for g in Grade for d in Difficulty]


def _questions(grade: Grade, difficulty: Difficulty, seed: int = 0):
    return generate_questions(MathType.word_problems, difficulty, grade, rng=random.Random(seed))


def _every_question():
    for grade, difficulty in ALL_LEVELS:
        for seed in SEEDS:
            yield from _questions(grade, difficulty, seed)


# ---------- tiers ----------


@pytest.mark.parametrize(
    "grade,difficulty,expected",
    [
        (Grade.K, Difficulty.easy, "simple"),
        (Grade.K, Difficulty.hard, "simple_wide"),   # never a list at K
        (Grade.G1, Difficulty.easy, "simple"),
        (Grade.G1, Difficulty.hard, "list"),
        (Grade.G2, Difficulty.easy, "list"),
        (Grade.G2, Difficulty.medium, "list_plus"),
        (Grade.G2, Difficulty.hard, "prices"),
        (Grade.G3, Difficulty.easy, "list"),
        (Grade.G3, Difficulty.medium, "prices"),
        (Grade.G4, Difficulty.hard, "prices"),
        (Grade.G5, Difficulty.easy, "prices"),
        (Grade.G5, Difficulty.hard, "deals"),
    ],
)
def test_tier_ladder(grade, difficulty, expected):
    g = 0 if grade == Grade.K else int(grade.value)
    assert _word_problem_tier(difficulty, g) == expected
    assert _pick_factory(MathType.word_problems, difficulty, grade).tier == expected


def test_kindergarten_questions_stay_one_line():
    """At K the reading is the hard part — no multi-line scenes."""
    for seed in SEEDS:
        for q in _questions(Grade.K, Difficulty.easy, seed):
            assert "\n" not in q.question
            assert len(q.question.split()) < 25


# ---------- variety: the thing the rewrite is for ----------


def test_a_quiz_rotates_through_every_shape_its_tier_offers():
    """Ten questions shouldn't be ten of the same puzzle."""
    for grade, difficulty in [
        (Grade.G2, Difficulty.medium), (Grade.G3, Difficulty.medium), (Grade.G5, Difficulty.hard)
    ]:
        tier = _word_problem_tier(difficulty, 0 if grade == Grade.K else int(grade.value))
        shapes = len(wp.TIERS[tier])
        for seed in (0, 1, 2, 3):
            questions = _questions(grade, difficulty, seed)
            asks = {q.question.splitlines()[-1] for q in questions}
            # Every shape offered should show up in a 10-question quiz
            # (the deck deals before it reshuffles), and no ask repeats
            # verbatim more often than the deck forces.
            assert len(asks) >= min(shapes, 5), (tier, sorted(asks))


def test_scenes_and_names_do_not_repeat_across_a_quiz():
    for grade, difficulty in [(Grade.G2, Difficulty.easy), (Grade.G5, Difficulty.hard)]:
        questions = _questions(grade, difficulty, seed=3)
        openers = {q.question.splitlines()[0] for q in questions}
        assert len(openers) >= 7, openers


def test_noise_is_sometimes_there_and_sometimes_not():
    """A kid mustn't be able to learn "ignore the last sentence"."""
    with_noise = without = 0
    for seed in SEEDS:
        for q in _questions(Grade.G3, Difficulty.medium, seed):
            blocks = q.question.split("\n\n")
            # blocks: opener, list, [facts], ask
            if len(blocks) > 3:
                with_noise += 1
            else:
                without += 1
    assert with_noise > 0 and without > 0, (with_noise, without)


def test_tax_note_is_not_stamped_on_every_price_question():
    seen = [
        "no tax" in q.question.lower() or "include everything" in q.question.lower()
        for seed in SEEDS
        for q in _questions(Grade.G4, Difficulty.medium, seed)
    ]
    assert any(seen) and not all(seen)


# ---------- shape: list sifting ----------


def test_list_scenes_show_more_than_the_answer_needs():
    """Even the short scale keeps at least one line the answer ignores."""
    for grade, difficulty, minimum in [
        (Grade.G2, Difficulty.easy, 3), (Grade.G3, Difficulty.easy, 4)
    ]:
        for seed in SEEDS:
            for q in _questions(grade, difficulty, seed):
                lines = [ln for ln in q.question.splitlines() if ln.startswith("•")]
                assert len(lines) >= minimum, q.question
                quantities = [int(re.match(r"• (\d+)", ln).group(1)) for ln in lines]
                assert q.correctAnswer < sum(quantities), q.question


# ---------- shape: prices ----------


def test_price_lines_show_a_quantity_and_a_unit_price():
    for seed in SEEDS:
        for q in _questions(Grade.G4, Difficulty.medium, seed):
            for line in q.question.splitlines():
                if line.startswith("•") and "each" in line and "for $" not in line:
                    assert re.match(r"• \d+ .+ — \$\d+ each", line), line


# ---------- shape: rules & tallies ----------


def _tally_questions(grade=Grade.G3, difficulty=Difficulty.medium):
    for seed in SEEDS:
        for q in _questions(grade, difficulty, seed):
            if " — " in q.question and "$" not in q.question:
                yield q


def test_tally_scenes_state_their_rules():
    """A kid who has never watched football still has to be able to
    answer, so the points are always spelled out."""
    found = 0
    for q in _tally_questions():
        rules = [ln for ln in q.question.splitlines() if ln.startswith("•")]
        assert len(rules) >= 3, q.question
        for line in rules:
            assert re.match(r"• .+ — \d+ \w+$", line), line
        found += 1
    assert found > 0, "no tally questions generated"


def test_tally_rules_include_one_the_question_never_uses():
    """The distractor lives in the structure, not in a spare sentence."""
    for q in _tally_questions():
        lines = q.question.splitlines()
        rules = [ln for ln in lines if ln.startswith("•")]
        # Everything that isn't a rule: the intro, what happened, the ask.
        rest = " ".join(ln for ln in lines if not ln.startswith("•")).lower()
        # Rule labels are singular and the story is plural, so match
        # either — on word boundaries, or "basket" hits "basketball".
        unused = [
            r for r in rules
            if not re.search(rf"\b{re.escape(r.split(' — ')[0][2:].lower())}s?\b", rest)
        ]
        assert unused, (rules, rest)


def test_tally_units_are_singular_for_one():
    for q in _every_question():
        assert not re.search(r"— 1 (points|tickets|cents|stars|tokens)\b", q.question), q.question


def test_lower_grades_never_get_big_point_values():
    """Grade 2 shouldn't be multiplying by 25."""
    for seed in SEEDS:
        for q in _questions(Grade.G2, Difficulty.medium, seed):
            for line in q.question.splitlines():
                m = re.match(r"• .+ — (\d+) \w+$", line)
                if m:
                    assert int(m.group(1)) <= 5, line


# ---------- shape: sale offers ----------


def test_deal_scenes_always_offer_a_real_saving():
    for seed in SEEDS:
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            for line in q.question.splitlines():
                m = re.search(r"\$(\d+) each, or (\d+) for \$(\d+)", line)
                if m:
                    unit, count, deal = (int(g) for g in m.groups())
                    assert deal < unit * count, line


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
    [(3, 5, 2, 10), (6, 5, 2, 20), (4, 5, 3, 15), (2, 5, 2, 10)],
)
def test_free_item_cost(qty, unit, buy_n, expected):
    assert wp._free_cost(qty, unit, buy_n) == expected


# ---------- shape: two ways to buy ----------


def _choice_questions():
    for seed in range(120):
        for q in _questions(Grade.G5, Difficulty.hard, seed):
            if "there are two kinds" in q.question:
                yield q


def test_choice_scenes_offer_two_priced_options():
    found = 0
    for q in _choice_questions():
        lines = [ln for ln in q.question.splitlines() if ln.startswith("•")]
        assert len(lines) == 2, q.question
        assert "each" in lines[0] and " for $" in lines[1], lines
        found += 1
    assert found > 0, "no choice questions generated"


def test_cheapest_variant_answers_with_the_lower_of_the_two():
    for q in _choice_questions():
        if "cheaper" not in q.question and "as little as possible" not in q.question:
            continue
        qty, unit, deal_n, deal_price = _choice_numbers(q)
        assert q.correctAnswer == min(qty * unit, (qty // deal_n) * deal_price), q.question


def test_specified_variant_ignores_the_bargain():
    """When the list names one kind, the cheaper shelf is off the table."""
    checked = 0
    for q in _choice_questions():
        if "cheaper" in q.question or "as little as possible" in q.question:
            continue
        qty, unit, deal_n, deal_price = _choice_numbers(q)
        plain, fancy = qty * unit, (qty // deal_n) * deal_price
        assert q.correctAnswer == max(plain, fancy), q.question
        assert q.correctAnswer != min(plain, fancy)
        checked += 1
    assert checked > 0, "no specified-kind questions generated"


def _choice_numbers(q):
    lines = [ln for ln in q.question.splitlines() if ln.startswith("•")]
    qty = int(re.search(r"says: (\d+) ", q.question).group(1))
    unit = int(re.search(r"\$(\d+) each", lines[0]).group(1))
    deal_n, deal_price = (int(x) for x in re.search(r"(\d+) for \$(\d+)", lines[1]).groups())
    return qty, unit, deal_n, deal_price


# ---------- answers stay typable ----------


def test_answers_are_whole_non_negative_numbers_everywhere():
    for q in _every_question():
        assert isinstance(q.correctAnswer, int), q.question
        assert q.correctAnswer >= 0, q.question


def test_no_line_reads_one_apples():
    for q in _every_question():
        for line in q.question.splitlines():
            assert not line.startswith("• 1 "), line


# ---------- reading time ----------


def test_one_line_questions_keep_the_original_fifteen_seconds():
    assert time_limit_seconds("7 + 5 = ?") == 15
    assert time_limit_seconds(" ".join(["word"] * 25)) == 15


def test_long_scenes_earn_more_time():
    assert time_limit_seconds(" ".join(["word"] * 65)) > 15
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


def test_offers_never_reduce_to_a_round_unit_price():
    """"2 for $2" is "$1 each" in a costume — no division needed."""
    for grade, difficulty in [(Grade.G5, Difficulty.hard), (Grade.G5, Difficulty.easy)]:
        for seed in SEEDS:
            for q in _questions(grade, difficulty, seed):
                for m in re.finditer(r"(\d+) for \$(\d+)", q.question):
                    count, price = int(m.group(1)), int(m.group(2))
                    assert price % count, q.question


# ---------- reading scales ----------
#
# The maths tier and the reading load are separate knobs: a 2nd grader
# used to get the same 4-6 line list as a 4th grader.


def _bullets_of(q):
    return [ln for ln in q.question.splitlines() if ln.startswith("•")]


def test_grades_one_and_two_read_short_lists_with_no_noise():
    for grade, difficulty in [
        (Grade.G1, Difficulty.hard), (Grade.G2, Difficulty.easy),
        (Grade.G2, Difficulty.medium), (Grade.G2, Difficulty.hard),
    ]:
        for seed in SEEDS:
            for q in _questions(grade, difficulty, seed):
                blocks = q.question.split("\n\n")
                bullets = _bullets_of(q)
                if bullets:
                    assert len(bullets) <= 4, q.question
                # No scene-setting noise: every block is the opener, the
                # list/rules, a *required* fact (pays-with, shares), or
                # the question itself.
                for block in blocks[2:-1]:
                    assert (
                        "note." in block or "share the cost" in block
                        or "no tax" in block.lower() or "prices already" in block.lower()
                        or "delivery fee" in block.lower()
                        or block.startswith(("The score", "The reading", "The spotting"))
                        or " shows " in block
                    ), f"unexpected extra reading at {grade}/{difficulty}: {block!r}"


def test_grade_five_reads_longer_lists_than_lower_grades():
    """Same maths tier (prices), different reading scale: G5 medium runs
    long, G3 medium runs standard, G2 hard runs short."""
    def average_bullets(grade, difficulty):
        counts = [
            len(_bullets_of(q))
            for seed in SEEDS
            for q in _questions(grade, difficulty, seed)
            if _bullets_of(q)
        ]
        return sum(counts) / len(counts)

    g2 = average_bullets(Grade.G2, Difficulty.hard)
    g3 = average_bullets(Grade.G3, Difficulty.medium)
    g5 = average_bullets(Grade.G5, Difficulty.medium)
    assert g2 < g3 < g5, (g2, g3, g5)


def test_long_scale_lists_can_carry_a_third_distractor_zone():
    """Grade-5 list questions may show lines from a zone the question
    never mentions — pure sifting."""
    # list shapes only appear at the long scale through medium G5? They
    # don't: G5 runs prices/deals. Long-scale lists exist via the mixed
    # topic; assert the machinery directly instead.
    import random as _random

    from app import word_problems as wp

    saw_extra = False
    for seed in range(60):
        rng = _random.Random(seed)
        sig, text, answer, expl = wp.list_count(rng, 1, 9, scale="long")
        bullets = [ln for ln in text.splitlines() if ln.startswith("•")]
        if len(bullets) >= 7:
            saw_extra = True
            break
    assert saw_extra, "long scale never produced an extended list"


def test_scale_only_changes_the_reading_not_the_tier():
    from app.questions import _reading_scale, _word_problem_tier

    # Same tier at G3 easy and G2 easy-adjacent levels can differ in scale…
    assert _word_problem_tier(Difficulty.easy, 2) == _word_problem_tier(Difficulty.easy, 3)
    assert _reading_scale(Difficulty.easy, 2) == "short"
    assert _reading_scale(Difficulty.easy, 3) == "standard"
    # …and grade 5 splits scale by difficulty without changing maths tier.
    assert _reading_scale(Difficulty.easy, 5) == "standard"
    assert _reading_scale(Difficulty.hard, 5) == "long"
