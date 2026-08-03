"""Wrong answers worth offering.

A multiple-choice question is only as good as its wrong answers. Two
failures matter, and the old builder had both:

**Answers from the wrong universe.** "8! _ 2^6" was offered as
`128 · < · 127 · >`, and "Is 41 even or odd?" as `< · 21 · 18 · odd` —
in each case only one option is even the right *kind* of thing, so a kid
can score without doing any maths. Distractors here must match the
correct answer's domain: a comparison offers comparison symbols, a unit
question offers units, a number question offers numbers.

**Wrong answers nobody would ever compute.** "8 minutes is how many
seconds?" offered `480 · 470 · 479 · 477`. Nothing about 479 tests
anything: no method produces it, so it reads as noise. The distractors
that teach are the ones a real mistake lands on — 48 (dropped a zero),
4800 (added one), 240 (used 30 seconds a minute), 500 (rounded). So
numeric distractors are built from *misconceptions* — halving, doubling,
place-value slips, round-number guesses — and at most one is a near
miss.

Where the question already lists the alternatives ("meters, grams or
liters", "the biggest: 21, 2 or 17"), those are used directly: nothing
invented can beat the options the question itself put on the table.
"""
from __future__ import annotations

import ast
import operator
import random
import re
from typing import Optional

# ---------- recognising what kind of answer we're dealing with ----------

SYMBOLS = ("<", ">", "=")
EVEN_ODD = ("even", "odd")

_FRACTION_RE = re.compile(r"^-?\d+/\d+$")
_DECIMAL_RE = re.compile(r"^-?\d+\.\d+$")
_CLOCK_RE = re.compile(r"^(\d{1,2}):([0-5]\d)$")
_INT_RE = re.compile(r"^-?\d+$")

#: Closed vocabularies: when the answer is one of these, the whole set is
#: the option list. Three symbols beat three symbols and a stray 127.
CLOSED_SETS: tuple[tuple[str, ...], ...] = (SYMBOLS, EVEN_ODD)

#: Vocabularies to draw *distractors* from, for answers that are words.
#: Without these, a geometry question whose siblings all happen to be
#: numbers would have no honest options at all. Units are deliberately
#: one family rather than one per dimension: offering "grams" for a
#: length is the classic mistake, and it's what the app's own
#: "meters / grams / liters" questions already do.
ANGLE_TYPES = ("acute", "right", "obtuse", "straight")
TRIANGLE_TYPES = ("isosceles", "equilateral", "scalene")
SHAPES = (
    "triangle", "square", "rectangle", "pentagon", "hexagon", "heptagon",
    "octagon", "circle", "quadrilateral", "rhombus", "trapezoid", "oval",
)
UNITS = (
    "millimeters", "centimeters", "meters", "kilometers",
    "grams", "kilograms", "milliliters", "liters",
)
WORD_FAMILIES: tuple[tuple[str, ...], ...] = (
    ANGLE_TYPES, TRIANGLE_TYPES, SHAPES, UNITS,
)


def closed_set_for(answer: str) -> Optional[tuple[str, ...]]:
    for members in CLOSED_SETS:
        if answer in members:
            return members
    return None


def family_for(answer: str) -> tuple[str, ...]:
    """Words of the same sort as this answer (empty if it's not in one)."""
    for family in WORD_FAMILIES:
        if answer in family:
            return family
    return ()


def kind_of(answer: str) -> str:
    """Coarse domain of an answer, used to keep options comparable."""
    if answer in SYMBOLS:
        return "symbol"
    if _CLOCK_RE.match(answer):
        return "clock"
    if _FRACTION_RE.match(answer):
        return "fraction"
    if _DECIMAL_RE.match(answer):
        return "decimal"
    if _INT_RE.match(answer):
        return "integer"
    return "word"


def same_kind(a: str, b: str) -> bool:
    """Fractions and decimals are both 'a number you could compare', so
    they mix; nothing else crosses domains."""
    ka, kb = kind_of(a), kind_of(b)
    if ka == kb:
        return True
    numeric = {"integer", "decimal", "fraction"}
    return ka in numeric and kb in numeric


# ---------- alternatives the question itself offers ----------

_BULLET_RE = re.compile(r"^[•\-\*]\s*(.+)$", re.MULTILINE)
_OR_LIST_RE = re.compile(r":\s*(.+?)\?")


def alternatives_in_text(text: str) -> list[str]:
    """Choices the question already lists.

    Two shapes appear in this app: a bulleted list ("• meters"), and an
    inline list ending in "or" ("the biggest: 21, 2 or 17?"). Anything
    else returns nothing — this only harvests genuine enumerations, not
    every number that happens to appear in a sentence, because "8" from
    "8 minutes" is not a plausible answer to "how many seconds?".
    """
    bullets = [m.strip() for m in _BULLET_RE.findall(text)]
    if bullets:
        return bullets

    found: list[str] = []
    for candidate in _OR_LIST_RE.findall(text):
        if " or " not in candidate:
            continue
        parts = re.split(r",\s*|\s+or\s+", candidate)
        parts = [p.strip() for p in parts if p.strip()]
        # Only trust it when the pieces are uniform — a list of numbers or
        # a list of words, not a sentence that happens to contain "or".
        if len(parts) >= 2 and len({kind_of(p) for p in parts}) == 1:
            found.extend(parts)
    return found


_ARITH_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
              ast.Mult: operator.mul, ast.Div: operator.floordiv}


def expression_values(parts: list[str]) -> list[int]:
    """Work out listed arithmetic expressions, skipping any that don't
    parse. Only + - × ÷ and brackets — enough for the "which one is the
    biggest" questions, and nothing that could evaluate arbitrary text.
    """
    values: list[int] = []
    for part in parts:
        try:
            tree = ast.parse(part.replace("×", "*").replace("÷", "/"), mode="eval")
        except SyntaxError:
            continue

        def walk(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in _ARITH_OPS:
                return _ARITH_OPS[type(node.op)](walk(node.left), walk(node.right))
            raise ValueError(part)

        try:
            values.append(walk(tree.body))
        except (ValueError, ZeroDivisionError, TypeError):
            continue
    return values


# ---------- misconception-shaped numbers ----------


def _round_neighbours(n: int) -> list[int]:
    """The round numbers either side — where a guess lands."""
    out = []
    for step in (10, 50, 100, 1000):
        if n <= step:
            continue
        below, above = (n // step) * step, ((n // step) + 1) * step
        out.extend([below, above])
    return out


def _digit_swap(n: int) -> list[int]:
    """Transposed digits: 162 -> 126, the classic copying slip."""
    digits = list(str(abs(n)))
    if len(digits) < 2:
        return []
    out = []
    for i in range(len(digits) - 1):
        swapped = digits[:]
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        if swapped[0] != "0":
            out.append(int("".join(swapped)))
    return out


def integer_distractors(n: int, rng: random.Random) -> list[str]:
    """Wrong integers a real mistake would produce, best first.

    Structural errors lead — halving, doubling, place-value slips,
    round-number guesses — and exactly one near miss is allowed in, so a
    kid who worked it out properly still sees their answer stand out but
    a kid who didn't can't pick by shape.
    """
    seen: set[int] = set()

    def tier(*values: int) -> list[int]:
        out = []
        for v in values:
            if v != n and v > 0 and v not in seen:
                seen.add(v)
                out.append(v)
        rng.shuffle(out)
        return out

    # Strongest first: the errors that come from a wrong method rather
    # than a wrong keystroke. A dropped zero and a doubled answer are
    # things a kid actually hands in; 479 is not.
    method = tier(
        n // 10 if n >= 10 and n % 10 == 0 else 0,
        n * 10 if n >= 10 else 0,
        n // 2 if n % 2 == 0 else 0,
        n * 2,
    )
    guesses = tier(*_round_neighbours(n))
    slips = tier(*_digit_swap(n), n + 10, n - 10)
    near = tier(n + 1, n - 1, n + 2, n - 2)

    # Small numbers have no structure to get wrong — 3 vs 30 isn't a
    # misconception, it's a different question — so neighbours lead.
    if n < 10:
        ordered = near + method + guesses + slips
    else:
        # One strong error, one plausible guess, then a single near miss:
        # enough to catch a kid who guessed, not so much noise that the
        # right answer stands out by shape.
        ordered = method[:1] + guesses[:1] + near[:1] + method[1:] + guesses[1:] + slips
    return [str(v) for v in ordered]


def decimal_distractors(s: str, rng: random.Random) -> list[str]:
    """Place-value slips first: 0.7 -> 0.07, 7.0, 0.75."""
    places = len(s.split(".")[1])
    value = float(s)
    out: list[str] = []

    def offer(v: float, dp: int = places):
        if v <= 0:
            return
        text = f"{v:.{dp}f}"
        if text != s and text not in out:
            out.append(text)

    offer(value * 10)
    offer(value / 10, places + 1)
    offer(value * 2)
    offer(round(value) if round(value) != value else value + 1, places)
    step = 10 ** (-places)
    offer(round(value + step, places))
    offer(round(value - step, places))
    return out


def fraction_distractors(s: str, rng: random.Random) -> list[str]:
    """Numerator and denominator swapped, or one of them off by one —
    the two things that actually go wrong with fractions."""
    num, den = (int(x) for x in s.split("/"))
    correct = num / den
    out: list[str] = []

    def offer(n2: int, d2: int):
        if n2 < 1 or d2 < 2:
            return
        text = f"{n2}/{d2}"
        if text != s and abs(n2 / d2 - correct) > 1e-9 and text not in out:
            out.append(text)

    offer(den, num)          # flipped
    offer(num + 1, den)      # counted one too many
    offer(num, den + 1)      # split into one piece too many
    offer(num - 1, den)
    offer(num, den - 1)
    offer(num + 1, den + 1)
    return out


def clock_distractors(s: str, rng: random.Random) -> list[str]:
    """Other times of day: an hour out, or minutes mixed up."""
    hour, minute = (int(x) for x in _CLOCK_RE.match(s).groups())
    out: list[str] = []

    def offer(h: int, m: int):
        if not (0 <= m < 60):
            return
        h = h if 1 <= h <= 12 else (12 if h % 12 == 0 else h % 12)
        text = f"{h}:{m:02d}"
        if text != s and text not in out:
            out.append(text)

    offer(hour + 1, minute)          # an hour too far
    offer(hour - 1, minute)
    offer(hour, (60 - minute) % 60)  # counted minutes backwards
    offer(hour, (minute + 30) % 60)
    offer(hour, (minute + 15) % 60)
    return out


# ---------- putting the options together ----------

MAX_OPTIONS = 4


def build_options(
    correct,
    question_text: str,
    sibling_answers,
    rng: random.Random,
) -> Optional[list[str]]:
    """Shuffled options for one question, or None if no honest distractor
    could be found (the question then stays a typed one).

    Order of preference:
      1. a closed vocabulary the answer belongs to (<, >, = / even, odd),
      2. alternatives the question text already lists,
      3. misconception-shaped values for the answer's type,
      4. other answers from the same quiz, filtered to the same kind.
    """
    correct_str = str(correct)

    members = closed_set_for(correct_str)
    if members:
        # The whole vocabulary, nothing else. Three symbols, or two
        # words — a smaller list that's entirely plausible beats four
        # options where three are obviously the wrong sort of thing.
        options = list(members)
        rng.shuffle(options)
        return options

    distractors: list[str] = []

    def add(value: str) -> None:
        value = str(value)
        if (
            value != correct_str
            and value not in distractors
            and len(distractors) < MAX_OPTIONS - 1
            and same_kind(value, correct_str)
        ):
            distractors.append(value)

    listed = [a for a in alternatives_in_text(question_text) if a != correct_str]
    if listed and not same_kind(listed[0], correct_str):
        # "Which one is the biggest: (8+11)×8, (15+14)×5, or (14+12)×7?"
        # lists expressions but wants a number back. The other two
        # expressions' *values* are the best possible wrong answers —
        # they're what a kid who worked out the wrong one would write.
        listed = [str(v) for v in expression_values(listed)]
    rng.shuffle(listed)
    for value in listed:
        add(value)

    if listed and same_kind(listed[0], correct_str):
        # The question put a list on the table ("• grams • meters …",
        # "the biggest: 21, 2 or 17"). Those are the options, all of
        # them and nothing else — inventing a fourth choice the question
        # never mentioned is a different question.
        options = distractors + [correct_str]
        rng.shuffle(options)
        return options

    kind = kind_of(correct_str)
    if kind == "integer":
        for value in integer_distractors(int(correct_str), rng):
            add(value)
    elif kind == "decimal":
        for value in decimal_distractors(correct_str, rng):
            add(value)
    elif kind == "fraction":
        for value in fraction_distractors(correct_str, rng):
            add(value)
    elif kind == "clock":
        for value in clock_distractors(correct_str, rng):
            add(value)
    else:
        family = [w for w in family_for(correct_str) if w != correct_str]
        rng.shuffle(family)
        for value in family:
            add(value)

    siblings = [str(s) for s in sibling_answers]
    rng.shuffle(siblings)
    for value in siblings:
        add(value)

    if not distractors:
        return None
    options = distractors + [correct_str]
    rng.shuffle(options)
    return options
