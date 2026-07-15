"""Grade-appropriate topic gating for direct selection and mixed quizzes."""
from __future__ import annotations

import random
import re

import pytest

from app.models import Difficulty, Grade, MathType
from app.questions import (
    _MIN_GRADE_FOR_TYPE,
    _MIXED_TYPES,
    generate_questions,
    types_available,
)


def test_every_math_type_has_a_min_grade():
    for mt in MathType:
        assert mt in _MIN_GRADE_FOR_TYPE, f"{mt} missing from _MIN_GRADE_FOR_TYPE"


def test_kindergarten_offers_only_the_basics():
    available = set(types_available(Grade.K))
    assert MathType.addition in available
    assert MathType.subtraction in available
    assert MathType.mixed in available
    # Concepts introduced later must not appear at K.
    for locked in (
        MathType.division,
        MathType.multiplication,
        MathType.fractions,
        MathType.decimals,
        MathType.percentages,
        MathType.order_of_operations,
    ):
        assert locked not in available, f"{locked} should be locked at K"


def test_grade5_offers_everything():
    available = set(types_available(Grade.G5))
    assert available == set(MathType)


def test_availability_is_monotonic_by_grade():
    """A topic available at grade N is available at every higher grade."""
    order = [Grade.K, Grade.G1, Grade.G2, Grade.G3, Grade.G4, Grade.G5]
    for mt in MathType:
        first_seen = None
        for g in order:
            here = mt in types_available(g)
            if here and first_seen is None:
                first_seen = g
            if first_seen is not None:
                assert here, f"{mt} vanished at {g} after appearing at {first_seen}"


@pytest.mark.parametrize("grade", [Grade.K, Grade.G1, Grade.G2, Grade.G3, Grade.G4, Grade.G5])
def test_mixed_only_draws_grade_appropriate_topics(grade):
    """A mixed quiz must never surface a topic locked at that grade.

    Checked via markers unique to a single gated topic: "%" only comes
    from percentages (grade 4+), and a bare "d.d" decimal only from the
    decimals topic (grade 3+; money uses ¢, not a decimal point).
    """
    allowed = set(types_available(grade))
    for seed in range(40):
        rng = random.Random(seed)
        qs = generate_questions(MathType.mixed, Difficulty.medium, grade, rng=rng)
        text = " ".join(q.question for q in qs)
        if MathType.percentages not in allowed:
            assert "%" not in text, f"percentages leaked into mixed at {grade}: {text}"
        if MathType.decimals not in allowed:
            assert not re.search(r"\d\.\d", text), f"decimals leaked into mixed at {grade}: {text}"


def test_mixed_at_kindergarten_still_fills_10_unique():
    for seed in range(20):
        rng = random.Random(seed)
        qs = generate_questions(MathType.mixed, Difficulty.easy, Grade.K, rng=rng)
        assert len(qs) == 10
        assert len({q.question for q in qs}) == 10


def test_min_grade_map_matches_mixed_type_list():
    # Every mixable type (all but `mixed`) must have a threshold.
    for mt in _MIXED_TYPES:
        assert mt in _MIN_GRADE_FOR_TYPE
