"""How many seconds each question is worth — the whole table, in one file.

This is the file to edit when a topic feels rushed or sleepy. Nothing
here computes anything clever: it is a lookup table plus a small
reading-length bonus, and `question_seconds()` is the only way the rest
of the app reads it.

**How a budget is worked out**

    seconds = topic base for this grade
            + difficulty adjustment
            + reading bonus (long questions)
            + thinking bonus (powers and factorials)
    clamped to [MINIMUM, MAXIMUM]

**How to change a number**

- One topic, every level: change its `base`.
- One topic at one grade: add an entry to its `by_grade` — an absolute
  number of seconds that replaces the base ("grade 3 comparison is 30").
- One topic at one difficulty: add an entry to its `by_difficulty` — a
  *relative* adjustment in seconds, added to whatever the grade resolved
  to ("hard word problems get 5 seconds more"). Use a negative number to
  take time away.

Grades are the `Grade` values ("K", "1" … "5") and difficulties are the
`Difficulty` values ("easy", "medium", "hard"). Every `MathType` must
appear in TOPICS — `test_question_times.py` fails if one is missing, so
a new topic can't quietly inherit a default nobody chose.

The numbers are read at request time, so changing them takes effect for
quizzes already created but not yet played.
"""
from __future__ import annotations

import re
from typing import Optional, TypedDict

from .models import Difficulty, Grade, MathType

# ---------- global knobs ----------

#: Floor and ceiling. No question is ever worth less or more than this,
#: whatever the table and the bonuses add up to.
MINIMUM = 5
MAXIMUM = 120

#: The default a topic gets when its `base` isn't set. Also the historical
#: value every topic used before this table existed.
DEFAULT_BASE = 15

#: Reading bonus: words a question gets "for free" before the clock
#: starts paying for reading, and what each further word is worth. A
#: one-line sum is well under the free allowance; a shopping-list scene
#: is well over it.
FREE_WORDS = 25
SECONDS_PER_EXTRA_WORD = 1

#: Thinking bonus: a power or a factorial is short to read and slow to
#: work out — "9^4 _ 7!" is eight characters and two real calculations —
#: so each one buys its own time on top of the reading.
SECONDS_PER_HEAVY_OP = 10
HEAVY_OP = re.compile(r"\d\^\d|\d!")

#: Lines that only restate notation ("Reminder: 3^2 means 3 × 3") are
#: skipped when counting heavy operations: nothing in them is worked
#: out, and counting them would pay twice for the same question.
REMINDER_PREFIX = "Reminder:"


class TopicTiming(TypedDict, total=False):
    base: int
    by_grade: dict[str, int]
    by_difficulty: dict[str, int]


# ---------- the table ----------

TOPICS: dict[MathType, TopicTiming] = {
    # --- one-line arithmetic: read in a glance, the clock is thinking time ---
    MathType.addition: {"base": 15},
    MathType.subtraction: {"base": 15},
    MathType.multiplication: {"base": 15},
    MathType.division: {"base": 15},
    MathType.algebra: {"base": 15},
    MathType.fractions: {"base": 15},
    MathType.order_of_operations: {"base": 15},
    MathType.decimals: {"base": 15},

    # --- word problems: a scene to read before any maths starts ---
    # 15s was reported as far too fast in play: by the time a kid has read
    # a shopping list and found the line that matters, the question is
    # gone. 30s is the floor for every grade; longer scenes then earn more
    # through the reading bonus, so a 60-word grade-5 list lands near 65s.
    MathType.word_problems: {
        "base": 30,
        "by_difficulty": {"hard": 5},
    },

    # --- comparison: pure numbers low down, expressions to evaluate high up ---
    # K-2 compare bare numbers ("which is biggest: 3, 15, 24?") and 15s is
    # plenty. From grade 3 the question becomes "work out both sides, then
    # compare", which is two calculations plus the comparison — also
    # reported as too fast, so 30s from grade 3 up. Grade 4-5 expressions
    # with powers and factorials earn a further 10s each on top.
    MathType.comparison: {
        "base": 15,
        "by_grade": {"3": 30, "4": 30, "5": 30},
        "by_difficulty": {"hard": 5},
    },

    # --- topics that mix a short prompt with a bit of reading ---
    # These carry scenes too (a price list, a bus timetable), but their
    # prompts are shorter than a word problem's; the reading bonus covers
    # the long ones. Raise the base here if they also feel rushed.
    MathType.money_time: {"base": 15},
    MathType.measurement: {"base": 15},
    MathType.percentages: {"base": 15},

    # --- geometry: naming a shape is quick, measuring a figure isn't ---
    # Grades 4-5 compute perimeter and area from a labelled drawing, which
    # means reading the figure before any arithmetic.
    MathType.geometry: {
        "base": 15,
        "by_grade": {"4": 20, "5": 20},
    },

    # A mixed quiz's questions each remember the topic they came from, so
    # this entry is only the fallback for a question whose topic is
    # unknown (a quiz created before questions carried one).
    MathType.mixed: {"base": 15},
}


# ---------- lookup ----------


def topic_base(math_type: Optional[MathType], grade: Optional[Grade]) -> int:
    """The table's base for a topic at a grade, before any bonuses."""
    entry = TOPICS.get(math_type) if math_type is not None else None
    if entry is None:
        return DEFAULT_BASE
    if grade is not None:
        by_grade = entry.get("by_grade") or {}
        if grade.value in by_grade:
            return by_grade[grade.value]
    return entry.get("base", DEFAULT_BASE)


def difficulty_adjustment(
    math_type: Optional[MathType], difficulty: Optional[Difficulty]
) -> int:
    """Seconds to add (or remove) for the difficulty. 0 when unset."""
    if math_type is None or difficulty is None:
        return 0
    entry = TOPICS.get(math_type) or {}
    return (entry.get("by_difficulty") or {}).get(difficulty.value, 0)


def reading_bonus(text: str) -> int:
    """Seconds bought by a question that runs past the free word count."""
    words = len(text.split())
    return SECONDS_PER_EXTRA_WORD * max(0, words - FREE_WORDS)


def thinking_bonus(text: str) -> int:
    """Seconds bought by powers and factorials, ignoring reminder lines."""
    body = "\n".join(
        line for line in text.splitlines() if not line.startswith(REMINDER_PREFIX)
    )
    return SECONDS_PER_HEAVY_OP * len(HEAVY_OP.findall(body))


def question_seconds(
    text: str,
    math_type: Optional[MathType] = None,
    difficulty: Optional[Difficulty] = None,
    grade: Optional[Grade] = None,
) -> int:
    """The clock a single question is worth.

    Every argument but the text is optional: a caller that doesn't know
    the level (an old stored quiz, a unit test) still gets a sane budget
    from the default base plus the text-derived bonuses.
    """
    seconds = (
        topic_base(math_type, grade)
        + difficulty_adjustment(math_type, difficulty)
        + reading_bonus(text)
        + thinking_bonus(text)
    )
    return max(MINIMUM, min(MAXIMUM, seconds))
