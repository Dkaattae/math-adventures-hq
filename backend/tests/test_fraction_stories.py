"""Fraction word problems: pizza, birthday cake and music.

Every story's answer is re-derived from the printed text, the way
test_answer_verification does for the arithmetic topics, so a story that
says "4 people" and divides by 3 fails here.
"""
from __future__ import annotations

import random
import re
from fractions import Fraction

import pytest

from app import fraction_stories as fs
from app import word_problems as wp
from app.distractors import build_options
from app.models import Difficulty, Grade, MathType
from app.questions import generate_questions, grade_answer

SEEDS = range(60)
BUILDERS = [fs.pizza_eaten, fs.pizza_share, fs.pizza_party, fs.cake_left, fs.music_count, fs.metronome]
NOTE = {"whole": Fraction(1), "half": Fraction(1, 2), "quarter": Fraction(1, 4),
        "8th": Fraction(1, 8), "16th": Fraction(1, 16)}


def _value(answer) -> Fraction:
    text = str(answer)
    if " " in text:
        whole, part = text.split(" ")
        return int(whole) + Fraction(part)
    return Fraction(text)


def _lowest_terms(answer) -> bool:
    part = str(answer).split(" ")[-1]
    if "/" not in part:
        return True
    num, den = (int(x) for x in part.split("/"))
    return Fraction(num, den).denominator == den and den != 1


def resolve(text: str) -> Fraction | int:
    """Solve a fraction story from its words alone."""
    if m := re.search(r"cuts a pizza into (\d+) equal slices and eats (\d+)", text):
        slices, eaten = int(m.group(1)), int(m.group(2))
        return Fraction(slices - eaten if "is left" in text else eaten, slices)
    if m := re.search(r"cuts it (in half|into (\d) equal parts)\. \w+ saves (one|\d) \w+", text):
        pieces = 2 if m.group(1) == "in half" else int(m.group(2))
        saved = 1 if m.group(3) == "one" else int(m.group(3))
        people = int(re.search(r"(\d+) people share", text).group(1))
        return Fraction(pieces - saved, pieces) / people
    if m := re.search(r"orders (\d+) pizzas .* cut into (\d+) slices\..* (\d+) kids eat (\d+) slices each", text):
        pizzas, slices, kids, each = (int(g) for g in m.groups())
        eaten = kids * each
        return Fraction(pizzas * slices - eaten if "left over" in text else eaten, slices)
    if m := re.search(r"cut into (\d+) equal slices\..* (\d+) friends each eat (\d+) slice", text):
        slices, friends, each = (int(g) for g in m.groups())
        eaten = friends * each
        return Fraction(slices - eaten if "is left" in text else eaten, slices)
    if m := re.search(r"fill the time of one (\w+) note with (\w+) notes", text):
        return NOTE[m.group(1)] / NOTE[m.group(2)]
    if m := re.search(r"plays (\d+) quarter notes? and then (\d+) 8th notes", text):
        return int(m.group(1)) + Fraction(int(m.group(2)), 2)
    if m := re.search(r"played at (\w+) note = (\d+) bpm .* changes to (\w+) note = (\d+) bpm", text):
        given, bpm, target, second = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        converted = bpm * NOTE[given] / NOTE[target]
        return abs(second - converted) if "How many more" in text else converted
    raise AssertionError(f"unrecognised story: {text}")


@pytest.mark.parametrize("builder", BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize("scale", ["short", "standard", "long"])
def test_every_story_answer_matches_its_words(builder, scale):
    for seed in SEEDS:
        sig, text, answer, explanation, *figure = builder(random.Random(seed), 1, 20, scale=scale)
        assert _value(answer) == resolve(text), (text, answer)
        assert _lowest_terms(answer), (text, answer)
        assert _value(answer) > 0, text
        # The grader accepts exactly what the key says.
        assert grade_answer(answer, str(answer)), (text, answer)


def test_the_resolver_can_fail():
    text = ("Leo buys a pizza and cuts it in half. Leo saves one half for tomorrow. "
            "4 people share the other half equally. What fraction of the whole pizza "
            "does each person get? (simplest form)")
    assert resolve(text) == Fraction(1, 8)
    assert resolve(text) != Fraction(1, 4)


def test_the_teachers_metronome_example():
    """The example the feature was asked for: 16th = 150, then 8th = 90."""
    text = ("Alex's teacher asks for a piece to be played at 16th note = 150 bpm "
            "(beats per minute). Later the music changes to 8th note = 90 bpm. "
            "To compare the two speeds, Alex changes the first marking into 8th notes "
            "per minute. How many 8th notes per minute is that?")
    assert resolve(text) == 75


def test_mixed_number_stories_never_answer_with_the_example():
    for seed in range(200):
        _, text, answer, *_ = fs.pizza_party(random.Random(seed), 1, 20)
        assert "e.g. 1 1/2" in text and answer != "1 1/2"
        assert re.fullmatch(r"\d+ \d+/\d+", answer), answer


def test_short_scale_has_no_scene_noise():
    """Grade 1-2 reading: nothing but the facts that matter."""
    for seed in SEEDS:
        _, text, *_ = fs.pizza_eaten(random.Random(seed), 1, 20, scale="short")
        assert text.count(".") == 1, text


def test_fraction_stories_reach_the_right_grades():
    def stories(grade, difficulty):
        out = set()
        for seed in range(15):
            for q in generate_questions(MathType.word_problems, difficulty, grade,
                                        rng=random.Random(seed)):
                if re.search(r"pizza|\bcake\b|\bnotes?\b", q.question):
                    out.add(q.question)
        return out

    assert not stories(Grade.K, Difficulty.hard)
    assert not stories(Grade.G2, Difficulty.easy)
    assert stories(Grade.G2, Difficulty.medium)
    g3 = " ".join(stories(Grade.G3, Difficulty.medium))
    assert "pizza" in g3 and "cake" in g3 and "note" in g3
    g5 = " ".join(stories(Grade.G5, Difficulty.hard))
    assert "bpm" in g5 and "mixed number" in g5
    # The metronome conversion is a grade-5-hard idea, not a grade-3 one.
    assert "bpm" not in g3


def test_stories_get_honest_multiple_choice_options():
    for builder in BUILDERS:
        for seed in range(20):
            _, text, answer, *_ = builder(random.Random(seed), 1, 20)
            options = build_options(answer, text, [], random.Random(seed))
            assert options and str(answer) in options, (text, options)
            assert len(set(options)) == len(options)
            assert sum(_value(o) == _value(answer) for o in options) == 1, (text, options)


def test_pizza_slices_picture_shows_the_cut_not_the_answer():
    for seed in SEEDS:
        _, text, answer, _, figure = fs.pizza_eaten(random.Random(seed), 1, 20)
        slices = re.search(r"into (\d+) equal slices", text).group(1)
        assert figure == f"pie:0/{slices}"


def test_tiers_still_deal_every_shape():
    for tier in ("list_plus", "prices", "deals"):
        assert any(b.__module__ == fs.__name__ for b in wp.TIERS[tier]), tier
