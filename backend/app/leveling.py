"""Single source of truth for the adaptive level ladder.

Both the end-of-quiz recommendation (computed at submit time from the
quiz's score) and the returning-player suggestion (computed from recent
history) step through the same grade/difficulty ladder here, so they can
never disagree on which way is "up".
"""
from __future__ import annotations

from enum import Enum

from .models import Difficulty, Grade

_GRADES = [Grade.K, Grade.G1, Grade.G2, Grade.G3, Grade.G4, Grade.G5]
_DIFFICULTIES = [Difficulty.easy, Difficulty.medium, Difficulty.hard]


class LevelDirection(str, Enum):
    up = "up"
    steady = "steady"
    down = "down"


def next_level(
    grade: Grade, difficulty: Difficulty, score: float
) -> tuple[Grade, Difficulty, LevelDirection]:
    """Given a level and a score (out of 10), return the level to play next.

    - score >= 9: step up (harder difficulty, or next grade at easy).
    - score <= 4: step down (easier difficulty, or previous grade at hard).
    - otherwise: hold.
    At the ceiling/floor the level is unchanged but the direction still
    reflects intent (so the UI can say "you've mastered it").
    """
    gi, di = _GRADES.index(grade), _DIFFICULTIES.index(difficulty)

    if score >= 9:
        if di < len(_DIFFICULTIES) - 1:
            return grade, _DIFFICULTIES[di + 1], LevelDirection.up
        if gi < len(_GRADES) - 1:
            return _GRADES[gi + 1], Difficulty.easy, LevelDirection.up
        return grade, difficulty, LevelDirection.up  # already at the top

    if score <= 4:
        if di > 0:
            return grade, _DIFFICULTIES[di - 1], LevelDirection.down
        if gi > 0:
            return _GRADES[gi - 1], Difficulty.hard, LevelDirection.down
        return grade, difficulty, LevelDirection.down  # already at the floor

    return grade, difficulty, LevelDirection.steady
