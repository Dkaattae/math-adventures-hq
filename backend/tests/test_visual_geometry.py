"""Visual geometry beyond shape ID, on the same grade ladder as text.

K-2 identify the shape they see; grade 2-3 read a property off the
figure (symmetry, angle type); grade 4-5 compute from labelled
dimensions. Answers are re-derived from the figure string, not trusted.
"""
from __future__ import annotations

import random
import re

from app.models import Difficulty, Grade, MathType
from app.questions import _geometry_tier, generate_questions

SEEDS = range(30)

_SYMMETRY = {
    "square": 4, "rectangle": 2, "triangle": 3,
    "pentagon": 5, "hexagon": 6, "octagon": 8,
}


def _visuals(grade, difficulty):
    for seed in SEEDS:
        rng = random.Random(seed)
        for q in generate_questions(MathType.geometry, difficulty, grade, rng=rng):
            if q.figure:
                yield q


# ---------- the ladder ----------


def test_kindergarten_visuals_are_identification_only():
    for q in _visuals(Grade.K, Difficulty.easy):
        assert ":" not in q.figure, q.figure
        assert "symmetry" not in q.question, q.question


def test_grade_three_reads_properties_off_the_figure():
    questions = list(_visuals(Grade.G3, Difficulty.medium))
    text = " ".join(q.question for q in questions)
    assert "symmetry" in text, "no symmetry questions at grade 3"
    assert "acute" in text, "no angle questions at grade 3"


def test_grade_five_computes_from_labelled_dimensions():
    questions = list(_visuals(Grade.G5, Difficulty.medium))
    text = " ".join(q.question for q in questions)
    assert "perimeter" in text or "area" in text, "no measured-figure questions at grade 5"


def test_area_only_at_the_top_tier():
    """Area is a tier-2 skill; a grade-2 medium quiz shouldn't see it."""
    for q in _visuals(Grade.G2, Difficulty.medium):
        assert "area" not in q.question, q.question


# ---------- answers re-derived from the figure ----------


def test_angle_classification_matches_the_drawn_angle():
    checked = 0
    for grade, difficulty in [(Grade.G3, Difficulty.medium), (Grade.G5, Difficulty.hard)]:
        for q in _visuals(grade, difficulty):
            m = re.fullmatch(r"angle:(\d+)", q.figure or "")
            if not m:
                continue
            deg = int(m.group(1))
            expected = "right" if deg == 90 else ("acute" if deg < 90 else "obtuse")
            assert q.correctAnswer == expected, (q.figure, q.correctAnswer)
            assert 10 <= deg <= 170, q.figure
            checked += 1
    assert checked > 0


def test_perimeter_and_area_match_the_labelled_sides():
    checked = 0
    for grade, difficulty in [(Grade.G4, Difficulty.medium), (Grade.G5, Difficulty.hard)]:
        for q in _visuals(grade, difficulty):
            m = re.fullmatch(r"rect:(\d+)x(\d+)", q.figure or "")
            if not m:
                continue
            w, h = int(m.group(1)), int(m.group(2))
            if "perimeter" in q.question:
                assert q.correctAnswer == 2 * (w + h), q.figure
            else:
                assert "area" in q.question, q.question
                assert q.correctAnswer == w * h, q.figure
            checked += 1
    assert checked > 0


def test_symmetry_counts_are_right():
    checked = 0
    for q in _visuals(Grade.G3, Difficulty.medium):
        if "symmetry" not in q.question:
            continue
        assert q.correctAnswer == _SYMMETRY[q.figure], (q.figure, q.correctAnswer)
        checked += 1
    assert checked > 0


def test_angle_figures_never_print_their_degrees_in_the_question():
    """The picture is the question — the text naming 120° would answer
    "acute or obtuse?" by itself."""
    for grade in (Grade.G3, Grade.G4, Grade.G5):
        for q in _visuals(grade, Difficulty.medium):
            if (q.figure or "").startswith("angle:"):
                assert "°" not in q.question, q.question
                assert not re.search(r"\d", q.question), q.question


def test_every_figure_string_is_renderable():
    """The client understands named shapes, angle:N and rect:WxH."""
    named = {"triangle", "square", "pentagon", "hexagon", "heptagon",
             "octagon", "circle", "rectangle"}
    for grade in Grade:
        for difficulty in Difficulty:
            for q in _visuals(grade, difficulty):
                ok = (
                    q.figure in named
                    or re.fullmatch(r"angle:\d+", q.figure)
                    or re.fullmatch(r"rect:\d+x\d+", q.figure)
                )
                assert ok, q.figure


def test_geometry_quizzes_still_yield_ten_unique_questions():
    for grade in Grade:
        for difficulty in Difficulty:
            for seed in range(10):
                rng = random.Random(seed)
                qs = generate_questions(MathType.geometry, difficulty, grade, rng=rng)
                assert len({(q.question, q.figure) for q in qs}) == 10


def test_mixed_quizzes_can_carry_the_new_figures():
    saw = False
    for seed in range(60):
        rng = random.Random(seed)
        for q in generate_questions(MathType.mixed, Difficulty.medium, Grade.G4, rng=rng):
            if q.figure and ":" in q.figure:
                saw = True
    assert saw, "mixed quizzes never surfaced a parametric figure"


def test_tier_function_matches_the_documented_ladder():
    assert _geometry_tier(Difficulty.easy, Grade.K) == 0
    assert _geometry_tier(Difficulty.medium, Grade.G2) == 1
    assert _geometry_tier(Difficulty.easy, Grade.G4) == 1
    assert _geometry_tier(Difficulty.medium, Grade.G5) == 2
    assert _geometry_tier(Difficulty.hard, Grade.G3) == 2


def test_property_visuals_have_a_guaranteed_presence():
    """2-3 per quiz from grade 2 up — not a raffle against the static pool."""
    for grade, difficulty in [(Grade.G3, Difficulty.medium), (Grade.G5, Difficulty.medium)]:
        for seed in range(10):
            rng = random.Random(seed)
            qs = generate_questions(MathType.geometry, difficulty, grade, rng=rng)
            rich = [
                q for q in qs
                if q.figure and (":" in q.figure or "symmetry" in q.question)
            ]
            assert 2 <= len(rich) <= 3, (grade, difficulty, seed, len(rich))
