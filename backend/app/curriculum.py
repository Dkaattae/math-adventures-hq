"""What each grade is about, and one difficulty ladder shared by all grades.

Two ideas live here, and every topic's generator leans on both:

**The level ladder.** A grade and a difficulty fold into one number,

    level = 2 × grade + difficulty      (K = 0; easy 0, medium 1, hard 2)

so the levels run 0 (K easy) to 12 (grade 5 hard) and *neighbouring
grades overlap by one step*: grade 3 hard and grade 4 easy are both
level 8 and draw the same questions. Before this, every grade restarted
near the bottom — grade 5 easy was sums of numbers up to 20 — because
difficulty only nudged a range that grew by 3 per grade.

**The grade focus chart.** A mixed quiz used to pick each question's
topic evenly from everything unlocked, so a 5th grader drew plain
addition as often as fractions. Each grade now names the topics its
year is actually spent on (most of the seats) and a shorter list kept
for review; anything else is left out of that grade's mix. Topics can
still be picked on their own at any grade they're unlocked — they just
come at that grade's level (grade-5 addition is four-digit and decimal).

Roughly a typical US (Common Core) K-5 sequence. Percentages are a
6th-grade topic there; they sit in grade 5's review as a step up.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Difficulty, Grade, MathType

MAX_LEVEL = 12

_DIFFICULTY_STEP = {Difficulty.easy: 0, Difficulty.medium: 1, Difficulty.hard: 2}


def grade_index(grade: Grade) -> int:
    return 0 if grade == Grade.K else int(grade.value)


def level(difficulty: Difficulty, grade: Grade) -> int:
    """One number for a grade/difficulty pair; see the module docstring."""
    return 2 * grade_index(grade) + _DIFFICULTY_STEP[difficulty]


#: Questions in a mixed quiz.
MIXED_SEATS = 10


@dataclass(frozen=True)
class GradeFocus:
    #: Topic → seats it always gets in a mixed quiz.
    focus: dict[MathType, int]
    #: The remaining seats are drawn from these, each topic at most once
    #: while there are enough of them to go round.
    review: tuple[MathType, ...]

    @property
    def review_seats(self) -> int:
        return MIXED_SEATS - sum(self.focus.values())


M = MathType

#: The chart. Keep the copy in README.md in step when changing it.
GRADE_FOCUS: dict[int, GradeFocus] = {
    # Add/subtract within 10, counting and comparing.
    0: GradeFocus(
        focus={M.addition: 3, M.subtraction: 3, M.comparison: 1},
        review=(M.geometry, M.word_problems),
    ),
    # Add/subtract within 20, story problems.
    1: GradeFocus(
        focus={M.addition: 3, M.subtraction: 2, M.word_problems: 2},
        review=(M.comparison, M.money_time, M.geometry),
    ),
    # Two-digit add/subtract with regrouping, money and time.
    2: GradeFocus(
        focus={M.addition: 2, M.subtraction: 2, M.money_time: 2, M.word_problems: 1},
        review=(M.measurement, M.geometry, M.fractions, M.comparison, M.multiplication),
    ),
    # Multiplication and division facts, unit fractions.
    3: GradeFocus(
        focus={M.multiplication: 2, M.division: 2, M.fractions: 2, M.word_problems: 1},
        review=(M.geometry, M.money_time, M.measurement, M.comparison,
                M.addition, M.subtraction),
    ),
    # Multi-digit × and long division, equivalent fractions, decimals.
    4: GradeFocus(
        focus={M.multiplication: 2, M.division: 2, M.fractions: 2, M.decimals: 1},
        review=(M.geometry, M.measurement, M.word_problems,
                M.order_of_operations, M.algebra),
    ),
    # Fraction and decimal operations, two-digit divisors, brackets.
    5: GradeFocus(
        focus={M.fractions: 3, M.decimals: 2, M.multiplication: 1, M.division: 1,
               M.order_of_operations: 1},
        review=(M.geometry, M.algebra, M.word_problems, M.measurement, M.percentages),
    ),
}

del M


def grade_focus(grade: Grade) -> GradeFocus:
    return GRADE_FOCUS[grade_index(grade)]
