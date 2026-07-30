"""Leaderboard ordering, including the ties the ranking used to fudge.

Score descending, then the faster run, then the earliest achievement
(with the row id as a final tiebreak). The third key matters: 10/10 in
45 seconds on an easy quiz is a common result, and with only two keys
the order among those rows — and therefore who makes the top five —
was whatever the database happened to return.

The expected order here is re-derived with Python's own sort from the
same key, not copied from what the query returned.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import storage
from app.models import Difficulty, Grade, LeaderboardEntry, MathType

BASE = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _add(db, name, score, seconds, *, minutes_late=0, math_type=MathType.addition):
    storage.add_leaderboard_entry(
        db,
        LeaderboardEntry(
            name=name,
            score=score,
            total=10,
            timeUsedSeconds=seconds,
            time=storage.format_time(seconds),
            badge="🏆",
            mathType=math_type,
            difficulty=Difficulty.easy,
            grade=Grade.G3,
            achievedAt=BASE + timedelta(minutes=minutes_late),
        ),
    )


def _names(db, **kwargs):
    return [e.name for e in storage.query_leaderboard(db, **kwargs)]


def test_score_beats_time(db_session):
    """A slow perfect run still outranks a fast poor one."""
    _add(db_session, "Fast", score=6, seconds=20)
    _add(db_session, "Slow", score=10, seconds=300)
    assert _names(db_session) == ["Slow", "Fast"]


def test_equal_scores_are_ranked_by_time(db_session):
    _add(db_session, "Middle", score=10, seconds=60)
    _add(db_session, "Quickest", score=10, seconds=31)
    _add(db_session, "Slowest", score=10, seconds=180)
    assert _names(db_session) == ["Quickest", "Middle", "Slowest"]


def test_a_dead_heat_is_broken_by_who_got_there_first(db_session):
    """Same score, same seconds — the earlier run keeps the higher rank."""
    _add(db_session, "Later", score=10, seconds=45, minutes_late=90)
    _add(db_session, "Earlier", score=10, seconds=45, minutes_late=5)
    _add(db_session, "Middle", score=10, seconds=45, minutes_late=40)
    assert _names(db_session) == ["Earlier", "Middle", "Later"]


def test_matching_a_score_later_never_demotes_the_holder(db_session):
    """The whole point of the third key: rank 1 is stable."""
    _add(db_session, "Holder", score=10, seconds=45, minutes_late=0)
    assert _names(db_session)[0] == "Holder"
    for i in range(1, 6):
        _add(db_session, f"Challenger{i}", score=10, seconds=45, minutes_late=i)
        assert _names(db_session)[0] == "Holder"


def test_the_limit_cut_is_deterministic_under_ties(db_session):
    """Ten identical rows, top 3 — the same three every time."""
    for i in range(10):
        _add(db_session, f"Kid{i}", score=8, seconds=50, minutes_late=i)
    assert _names(db_session, limit=3) == ["Kid0", "Kid1", "Kid2"]


def test_zero_scores_still_rank_among_themselves(db_session):
    _add(db_session, "Zippy", score=0, seconds=12)
    _add(db_session, "Dawdler", score=0, seconds=200)
    assert _names(db_session) == ["Zippy", "Dawdler"]


@pytest.mark.parametrize("seed", range(8))
def test_ordering_matches_an_independent_sort(db_session, seed):
    """Property check: the query's order equals sorting the same rows in
    Python by (-score, seconds, achievedAt). Scores and times are drawn
    from small pools so ties happen constantly."""
    import random

    rng = random.Random(seed)
    rows = []
    for i in range(25):
        score = rng.choice([0, 5, 8, 10])
        seconds = rng.choice([30, 45, 45, 60, 120])
        rows.append((f"Kid{i:02d}", score, seconds, i))
        _add(db_session, f"Kid{i:02d}", score=score, seconds=seconds, minutes_late=i)

    expected = [r[0] for r in sorted(rows, key=lambda r: (-r[1], r[2], r[3]))]
    assert _names(db_session, limit=25) == expected
    # And any prefix of it, so limit can't reshuffle the head.
    for limit in (1, 3, 7):
        assert _names(db_session, limit=limit) == expected[:limit]


def test_filters_do_not_disturb_the_ordering(db_session):
    _add(db_session, "AddFast", score=10, seconds=40, math_type=MathType.addition)
    _add(db_session, "GeoFast", score=10, seconds=35, math_type=MathType.geometry)
    _add(db_session, "AddSlow", score=10, seconds=90, math_type=MathType.addition)
    assert _names(db_session, math_type=MathType.addition) == ["AddFast", "AddSlow"]
    assert _names(db_session, math_type=MathType.geometry) == ["GeoFast"]
