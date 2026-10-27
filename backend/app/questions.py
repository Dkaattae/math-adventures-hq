"""Question generation.

Design notes
------------
Every question factory returns a `QuestionInternal` plus a *signature* — a
tuple uniquely identifying the problem (e.g. `("add", 3, 5)` means 3+5).
`generate_questions` draws 10 questions per request and dedupes by
signature so the player never sees the same problem twice in a single
quiz. Signatures are normalized for commutative ops (addition,
multiplication) so "3 + 5" and "5 + 3" count as the same problem.

When the value space is too small to yield 10 uniques (e.g. Kindergarten
easy addition has only ~15 distinct unordered pairs), we give up after
`_MAX_ATTEMPTS` tries per slot and accept a duplicate rather than
looping forever.
"""
from __future__ import annotations

import random
import re
from fractions import Fraction
from math import factorial, gcd
from typing import Callable, NamedTuple

from . import curriculum, fraction_questions, measurement, money_time, percentages, word_problems
from .distractors import build_options
from .question_times import question_seconds
from .curriculum import MAX_LEVEL
from .rotation import rotating
from .models import AnswerKind, AnswerMode, Difficulty, Grade, MathType, QuestionInternal

_MAX_ATTEMPTS = 200

# Every math type a "mixed" quiz could draw from (mixed itself excluded).
# Which of them a grade actually mixes is curriculum.GRADE_FOCUS.
_MIXED_TYPES: list[MathType] = [
    MathType.addition,
    MathType.subtraction,
    MathType.multiplication,
    MathType.division,
    MathType.algebra,
    MathType.geometry,
    MathType.fractions,
    MathType.order_of_operations,
    MathType.word_problems,
    MathType.comparison,
    MathType.money_time,
    MathType.decimals,
    MathType.percentages,
    MathType.measurement,
]

# Lowest grade at which each topic is offered (K == 0). Roughly aligned to
# when the concept is introduced in a typical K-5 curriculum. `mixed` is
# always available and draws only from topics unlocked at the chosen grade.
# Keep this in sync with `minGradeForType` in frontend/src/data/quizConfig.ts.
_MIN_GRADE_FOR_TYPE: dict[MathType, int] = {
    MathType.addition: 0,
    MathType.subtraction: 0,
    MathType.comparison: 0,
    MathType.geometry: 0,
    MathType.word_problems: 0,
    MathType.money_time: 1,
    MathType.fractions: 2,
    MathType.multiplication: 2,
    MathType.measurement: 2,
    MathType.algebra: 2,
    MathType.division: 3,
    MathType.order_of_operations: 3,
    MathType.decimals: 3,
    MathType.percentages: 4,
    MathType.mixed: 0,
}


def _grade_index(grade: Grade) -> int:
    return 0 if grade == Grade.K else int(grade.value)


def types_available(grade: Grade) -> list[MathType]:
    """Topics offered at this grade (includes `mixed`), in enum order."""
    g = _grade_index(grade)
    return [t for t in MathType if _MIN_GRADE_FOR_TYPE[t] <= g]


def min_grade_for_type(math_type: MathType) -> Grade:
    """Lowest grade a topic is offered at, as a Grade enum member."""
    g = _MIN_GRADE_FOR_TYPE[math_type]
    return Grade.K if g == 0 else Grade(str(g))


#: The gentle (lo, hi) the tiered topics' scenes and fractions are sized
#: from, per level (curriculum.level). Close to the old per-grade range
#: it replaced, but read off the level so grade N hard and grade N+1
#: easy see the same numbers. The one-line arithmetic topics use the
#: steeper tables further down instead.
_SCENE_RANGES: list[tuple[int, int]] = [
    (1, 5), (2, 10), (3, 12), (3, 14), (4, 16), (4, 18), (5, 20),
    (5, 22), (5, 24), (5, 27), (5, 30), (5, 32), (5, 35),
]


def _difficulty_range(difficulty: Difficulty, grade: Grade) -> tuple[int, int]:
    return _SCENE_RANGES[curriculum.level(difficulty, grade)]


# ---------- per-type factories ----------
#
# Each factory returns (signature, question_text, correct_answer, explanation),
# optionally followed by a figure string for the client to draw (fraction
# pies use this; see `_unpack`). `id` is assigned later by the dedup loop.

Factory = Callable[[random.Random, int, int], tuple]


def _unpack(result: tuple) -> tuple[tuple, str, int | str, str, str | None]:
    """A factory's result with the optional figure filled in as None."""
    signature, text, answer, explanation, *rest = result
    return signature, text, answer, explanation, (rest[0] if rest else None)


def _make_addition(rng: random.Random, lo: int, hi: int):
    a, b = rng.randint(lo, hi), rng.randint(lo, hi)
    lo_, hi_ = (a, b) if a <= b else (b, a)  # commutative → normalize
    return (
        ("add", lo_, hi_),
        f"{a} + {b} = ?",
        a + b,
        f"{a} + {b} = {a + b}. Try counting {b} more after {a}! 🤓",
    )


# ---------- subtraction: positive-only, plus an advanced variant with negatives ----------


def _sub_positive(rng: random.Random, lo: int, hi: int):
    a = rng.randint(lo, hi)
    b = rng.randint(lo, min(a, hi))  # keep answer non-negative
    return (
        ("sub", a, b),
        f"{a} - {b} = ?",
        a - b,
        f"{a} - {b} = {a - b}. Start at {a} and count back {b}! 👆",
    )


def _sub_negative(rng: random.Random, lo: int, hi: int):
    # Force b > a so the result is below zero.
    if hi - lo < 2:
        return _sub_positive(rng, lo, hi)
    a = rng.randint(lo, hi - 1)
    b = rng.randint(a + 1, hi)
    return (
        ("sub", a, b),
        f"{a} - {b} = ?",
        a - b,
        f"{a} - {b} = {a - b}. Going below zero! {b} is bigger than {a}, "
        f"so the answer is negative. 🥶",
    )


# ---------- division: integer, remainder, fraction, decimal ----------


def _div_remainder(rng: random.Random, lo: int, hi: int):
    divisor = rng.randint(2, max(3, hi // 3))
    quotient = rng.randint(1, max(2, hi // 2))
    remainder = rng.randint(1, divisor - 1) if divisor > 1 else 0
    dividend = divisor * quotient + remainder
    return (
        ("divrem", dividend, divisor),
        f"What is the remainder when {dividend} ÷ {divisor}?",
        remainder,
        f"{dividend} = {divisor} × {quotient} + {remainder}, so the remainder is {remainder}. 🧮",
    )


def _div_fraction(rng: random.Random, lo: int, hi: int):
    # Proper fraction, then simplify.
    divisor = rng.randint(2, max(4, hi // 2))
    dividend = rng.randint(1, divisor - 1)
    g = gcd(dividend, divisor)
    num, den = dividend // g, divisor // g
    hint = (
        f"{dividend}/{divisor} simplifies to {num}/{den} "
        f"(divide top and bottom by {g})."
        if g > 1
        else f"{dividend}/{divisor} is already in simplest form."
    )
    return (
        ("divfrac", dividend, divisor),
        f"Write {dividend} ÷ {divisor} as a fraction in simplest form (e.g. 3/4).",
        f"{num}/{den}",
        hint + " ✏️",
    )


# Hand-picked "nice" decimals that terminate cleanly — safe to type in.
_DECIMAL_CASES: list[tuple[int, int, str]] = [
    (1, 2, "0.5"), (3, 2, "1.5"), (5, 2, "2.5"), (7, 2, "3.5"), (9, 2, "4.5"),
    (1, 4, "0.25"), (3, 4, "0.75"), (5, 4, "1.25"), (7, 4, "1.75"), (9, 4, "2.25"),
    (1, 5, "0.2"), (2, 5, "0.4"), (3, 5, "0.6"), (4, 5, "0.8"), (6, 5, "1.2"),
    (1, 10, "0.1"), (3, 10, "0.3"), (7, 10, "0.7"), (9, 10, "0.9"),
    (1, 8, "0.125"), (3, 8, "0.375"), (5, 8, "0.625"), (7, 8, "0.875"),
]


def _div_decimal(rng: random.Random, lo: int, hi: int):
    dividend, divisor, result = rng.choice(_DECIMAL_CASES)
    return (
        ("divdec", dividend, divisor),
        f"What is {dividend} ÷ {divisor} as a decimal?",
        result,
        f"{dividend} ÷ {divisor} = {result} 💡",
    )


# ---------- algebra: several templates for variety ----------

def _alg_x_plus_c(rng: random.Random, lo: int, hi: int):
    x = rng.randint(lo, hi)
    c = rng.randint(1, hi)
    return (
        ("alg+", x, c),
        f"x + {c} = {x + c}. What is x?",
        x,
        f"x = {x}. Subtract {c} from both sides: {x + c} − {c} = {x}. 🧠",
    )


def _alg_x_minus_c(rng: random.Random, lo: int, hi: int):
    x = rng.randint(max(lo, 1), hi)
    c = rng.randint(1, x)  # keep RHS non-negative
    return (
        ("alg-", x, c),
        f"x - {c} = {x - c}. What is x?",
        x,
        f"x = {x}. Add {c} to both sides: {x - c} + {c} = {x}. 🧠",
    )


def _alg_c_minus_x(rng: random.Random, lo: int, hi: int):
    c = rng.randint(max(lo, 2), hi)
    x = rng.randint(1, c)
    return (
        ("algrev", c, x),
        f"{c} - x = {c - x}. What is x?",
        x,
        f"x = {x}. Rearranging: x = {c} − {c - x} = {x}. 🧠",
    )


def _alg_c_times_x(rng: random.Random, lo: int, hi: int):
    c = rng.randint(2, max(3, hi // 2))
    x = rng.randint(1, max(2, hi // 2))
    return (
        ("algmul", c, x),
        f"{c} × x = {c * x}. What is x?",
        x,
        f"x = {x}. Divide both sides by {c}: {c * x} ÷ {c} = {x}. 🧠",
    )


def _alg_x_over_c(rng: random.Random, lo: int, hi: int):
    c = rng.randint(2, max(3, hi // 3))
    x_div_c = rng.randint(1, max(2, hi // 2))
    x = x_div_c * c
    return (
        ("algdiv", x, c),
        f"x ÷ {c} = {x_div_c}. What is x?",
        x,
        f"x = {x}. Multiply both sides by {c}: {x_div_c} × {c} = {x}. 🧠",
    )


def _alg_two_step_plus(rng: random.Random, lo: int, hi: int):
    a = rng.randint(2, max(3, hi // 3))
    x = rng.randint(1, max(2, hi // 2))
    b = rng.randint(1, hi)
    c = a * x + b
    return (
        ("alg2+", a, b, x),
        f"{a}x + {b} = {c}. What is x?",
        x,
        f"x = {x}. Subtract {b} from both sides: {a}x = {c - b}. "
        f"Divide by {a}: x = {x}. 🧠",
    )


def _alg_two_step_minus(rng: random.Random, lo: int, hi: int):
    a = rng.randint(2, max(3, hi // 3))
    x = rng.randint(1, max(2, hi // 2))
    b = rng.randint(0, a * x)  # keep c = a*x - b non-negative
    c = a * x - b
    return (
        ("alg2-", a, b, x),
        f"{a}x - {b} = {c}. What is x?",
        x,
        f"x = {x}. Add {b} to both sides: {a}x = {c + b}. "
        f"Divide by {a}: x = {x}. 🧠",
    )


_ALGEBRA_TEMPLATES_EASY: list[Factory] = [_alg_x_plus_c, _alg_x_minus_c]
_ALGEBRA_TEMPLATES_FULL: list[Factory] = [
    _alg_x_plus_c,
    _alg_x_minus_c,
    _alg_c_minus_x,
    _alg_c_times_x,
    _alg_x_over_c,
]
_ALGEBRA_TEMPLATES_HARD: list[Factory] = _ALGEBRA_TEMPLATES_FULL + [
    _alg_two_step_plus,
    _alg_two_step_minus,
]


def _make_algebra(rng: random.Random, lo: int, hi: int):
    # K/1 stick to +/-; older grades see the full template set.
    templates = _ALGEBRA_TEMPLATES_EASY if hi < 10 else _ALGEBRA_TEMPLATES_FULL
    return rng.choice(templates)(rng, lo, hi)


def _make_algebra_hard(rng: random.Random, lo: int, hi: int):
    # Two-step equations (ax + b = c) on top of the full one-step set.
    return rng.choice(_ALGEBRA_TEMPLATES_HARD)(rng, lo, hi)


# ---------- fractions ----------
#
# Pictures, mixed numbers and the fraction ⇄ decimal bridge outgrew this
# file — see fraction_questions.py.


# ---------- order of operations: PEMDAS templates of increasing complexity ----------


def _ooo_add_mul(rng: random.Random, lo: int, hi: int):
    a = rng.randint(lo, hi)
    b = rng.randint(1, max(2, hi // 4))
    c = rng.randint(1, max(2, hi // 4))
    answer = a + b * c
    return (
        ("ooo_am", a, b, c),
        f"{a} + {b} × {c} = ?",
        answer,
        f"Multiply first: {b} × {c} = {b * c}. Then add: {a} + {b * c} = {answer}. Remember PEMDAS! 📐",
    )


def _ooo_mul_add(rng: random.Random, lo: int, hi: int):
    a = rng.randint(1, max(2, hi // 4))
    b = rng.randint(1, max(2, hi // 4))
    c = rng.randint(lo, hi)
    answer = a * b + c
    return (
        ("ooo_ma", a, b, c),
        f"{a} × {b} + {c} = ?",
        answer,
        f"Multiply first: {a} × {b} = {a * b}. Then add: {a * b} + {c} = {answer}. Remember PEMDAS! 📐",
    )


def _ooo_sub_mul(rng: random.Random, lo: int, hi: int):
    b = rng.randint(1, max(2, hi // 4))
    c = rng.randint(1, max(2, hi // 4))
    product = b * c
    a = rng.randint(product, product + max(5, hi))
    answer = a - product
    return (
        ("ooo_sm", a, b, c),
        f"{a} - {b} × {c} = ?",
        answer,
        f"Multiply first: {b} × {c} = {product}. Then subtract: {a} - {product} = {answer}. Remember PEMDAS! 📐",
    )


def _ooo_div_add(rng: random.Random, lo: int, hi: int):
    divisor = rng.randint(2, max(3, hi // 4))
    quotient = rng.randint(1, max(2, hi // 4))
    dividend = divisor * quotient
    c = rng.randint(lo, hi)
    answer = quotient + c
    return (
        ("ooo_da", dividend, divisor, c),
        f"{dividend} ÷ {divisor} + {c} = ?",
        answer,
        f"Divide first: {dividend} ÷ {divisor} = {quotient}. Then add: {quotient} + {c} = {answer}. Remember PEMDAS! 📐",
    )


def _ooo_three_terms(rng: random.Random, lo: int, hi: int):
    a = rng.randint(lo, hi)
    b = rng.randint(1, max(2, hi // 4))
    c = rng.randint(1, max(2, hi // 4))
    product = b * c
    d = rng.randint(0, product)
    answer = a + product - d
    return (
        ("ooo_3t", a, b, c, d),
        f"{a} + {b} × {c} - {d} = ?",
        answer,
        f"Multiply first: {b} × {c} = {product}. Then: {a} + {product} - {d} = {answer}. Remember PEMDAS! 📐",
    )


def _ooo_parens(rng: random.Random, lo: int, hi: int):
    a = rng.randint(lo, hi)
    b = rng.randint(1, max(2, hi // 4))
    c = rng.randint(2, max(3, hi // 4))
    answer = (a + b) * c
    return (
        ("ooo_pa", a, b, c),
        f"({a} + {b}) × {c} = ?",
        answer,
        f"Parentheses first: {a} + {b} = {a + b}. Then multiply: {a + b} × {c} = {answer}. Parentheses win! 📐",
    )


def _make_ooo_basic(rng: random.Random, lo: int, hi: int):
    return rng.choice([_ooo_add_mul, _ooo_mul_add])(rng, lo, hi)


def _make_ooo_intermediate(rng: random.Random, lo: int, hi: int):
    return rng.choice([_ooo_add_mul, _ooo_mul_add, _ooo_sub_mul, _ooo_div_add])(rng, lo, hi)


def _make_ooo_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice([_ooo_sub_mul, _ooo_div_add, _ooo_three_terms, _ooo_parens])(rng, lo, hi)


# ---------- word problems ----------
#
# The scenes and question shapes live in word_problems.py — this topic
# grew past the one-liner templates the rest of the file uses. Its
# factories are built per quiz (see _pick_factory) so the ten questions
# rotate through every shape a tier offers instead of drawing at random;
# each shape still returns the usual
# (signature, text, answer, explanation).


# ---------- comparison & number sense ----------


def _cmp_symbol(rng: random.Random, lo: int, hi: int):
    a = rng.randint(lo, hi)
    # 1-in-5 chance of equality so "=" answers actually appear.
    b = a if rng.random() < 0.2 else rng.randint(lo, hi)
    answer = "<" if a < b else (">" if a > b else "=")
    return (
        ("cmp", a, b),
        f"Fill in the blank: {a} _ {b} (write <, > or =)",
        answer,
        f"{a} {answer} {b}. The open side of < and > always faces the bigger number! ⚖️",
    )


def _cmp_biggest(rng: random.Random, lo: int, hi: int):
    nums = rng.sample(range(lo, hi + 10), 3)
    answer = max(nums)
    return (
        ("cmpbig", *sorted(nums)),
        f"Which number is the biggest: {nums[0]}, {nums[1]} or {nums[2]}?",
        answer,
        f"{answer} is bigger than the other two! ⚖️",
    )


def _even_odd(rng: random.Random, lo: int, hi: int):
    n = rng.randint(1, max(10, hi * 3))
    answer = "even" if n % 2 == 0 else "odd"
    return (
        ("evenodd", n),
        f"Is {n} even or odd?",
        answer,
        f"{n} is {answer} — even numbers end in 0, 2, 4, 6 or 8! 🔍",
    )


def _sequence_next(rng: random.Random, lo: int, hi: int):
    start = rng.randint(lo, hi)
    step = rng.randint(2, 5)
    a, b, c = start, start + step, start + 2 * step
    return (
        ("seq", start, step),
        f"What number comes next: {a}, {b}, {c}, ?",
        c + step,
        f"The pattern adds {step} each time: {c} + {step} = {c + step}! 🔁",
    )


def _place_value(rng: random.Random, lo: int, hi: int):
    n = rng.randint(100, 999)
    place, digit = rng.choice(
        [("hundreds", n // 100), ("tens", (n // 10) % 10), ("ones", n % 10)]
    )
    return (
        ("place", n, place),
        f"In the number {n}, which digit is in the {place} place?",
        digit,
        f"In {n}, the {place} digit is {digit}! 🏷️",
    )


def _round_to_ten(rng: random.Random, lo: int, hi: int):
    n = rng.randint(11, max(99, hi * 5))
    if n % 10 == 0:
        n += rng.randint(1, 9)
    answer = ((n + 5) // 10) * 10
    return (
        ("round10", n),
        f"Round {n} to the nearest 10.",
        answer,
        f"{n} is closest to {answer}. Look at the ones digit: 5 or more rounds up! 🎯",
    )


# ---------- comparing expressions, not just numbers ----------
#
# "Which is biggest: 3, 15, 24?" is a grade-2 question, and it was still
# what grade 4 got. From grade 3 up, both sides of the comparison are
# something to work out first: sums, then mixed operators where
# precedence decides the answer, then powers and factorials where the
# point is how fast each one grows.
#
# These factories set their own number ranges rather than using the
# shared lo/hi — the tier they're selected for already encodes the level.


class _Expr(NamedTuple):
    text: str
    value: int


def _expr_sum(rng: random.Random, lo: int, hi: int, target: int | None = None) -> _Expr:
    if target is not None:
        low, high = max(lo, target - hi), min(hi, target - lo)
        if low <= high:
            a = rng.randint(low, high)
            return _Expr(f"{a} + {target - a}", target)
    a, b = rng.randint(lo, hi), rng.randint(lo, hi)
    return _Expr(f"{a} + {b}", a + b)


def _expr_mul_add(rng: random.Random, target: int | None = None) -> _Expr | None:
    """`x × y + z`, written either way round so precedence always matters."""
    for _ in range(40):
        x, y = rng.randint(2, 12), rng.randint(2, 12)
        product = x * y
        if target is None:
            z = rng.randint(2, 40)
        else:
            z = target - product
            if not 1 <= z <= 60:
                continue
        text = f"{x} × {y} + {z}" if rng.random() < 0.5 else f"{z} + {x} × {y}"
        return _Expr(text, product + z)
    return None


def _expr_mul_add_only(rng: random.Random) -> _Expr:
    """`_expr_mul_add` without the "may return None" contract, for
    callers that just want one of these and can't retry."""
    return _expr_mul_add(rng) or _expr_sum(rng, 12, 99)


def _expr_brackets(rng: random.Random) -> _Expr:
    a, b = rng.randint(3, 20), rng.randint(2, 15)
    m = rng.randint(2, 9)
    return _Expr(f"({a} + {b}) × {m}", (a + b) * m)


# (base, exponent) pairs that stay under 10,000 — big enough to make the
# point, small enough that a kid can actually work them out.
_POWERS = [
    (b, e) for b in range(2, 10) for e in range(2, 7) if 16 <= b ** e <= 10_000
]
# Different-looking powers that are secretly equal, so "=" can happen.
_EQUAL_POWERS = [((2, 4), (4, 2)), ((2, 6), (8, 2)), ((3, 4), (9, 2)),
                 ((2, 9), (8, 3)), ((2, 10), (4, 5)), ((3, 6), (9, 3))]


def _expr_power(rng: random.Random) -> _Expr:
    base, exp = rng.choice(_POWERS)
    return _Expr(f"{base}^{exp}", base ** exp)


def _expr_factorial(rng: random.Random) -> _Expr:
    n = rng.randint(4, 8)
    return _Expr(f"{n}!", factorial(n))


# Powers small enough to sit inside a longer expression without the
# arithmetic around them becoming irrelevant.
_SMALL_POWERS = [(b, e) for (b, e) in _POWERS if b ** e <= 1_000]


def _expr_power_plus(rng: random.Random) -> _Expr:
    """`2^4 + 3 × 2 + 8` — a power buried in ordinary arithmetic.

    Every term is added, so the pieces can be shuffled: the power turns
    up first, last or in the middle, and the question stops looking like
    the same template every time.
    """
    base, exp = rng.choice(_SMALL_POWERS)
    parts, value = [f"{base}^{exp}"], base ** exp
    if rng.random() < 0.7:
        x, y = rng.randint(2, 9), rng.randint(2, 9)
        parts.append(f"{x} × {y}")
        value += x * y
    if rng.random() < 0.6 or len(parts) == 1:
        c = rng.randint(2, 40)
        parts.append(str(c))
        value += c
    rng.shuffle(parts)
    return _Expr(" + ".join(parts), value)


def _expr_power_scaled(rng: random.Random) -> _Expr:
    """`3 × 2^4` — a multiplier in front of a power."""
    base, exp = rng.choice(_SMALL_POWERS)
    m = rng.randint(2, 9)
    return _Expr(f"{m} × {base}^{exp}", m * base ** exp)


def _expr_power_minus(rng: random.Random) -> _Expr:
    """`5^3 - 40` — a power you have to work out and then trim."""
    base, exp = rng.choice(_SMALL_POWERS)
    value = base ** exp
    c = rng.randint(2, max(3, value // 2))
    return _Expr(f"{base}^{exp} - {c}", value - c)


def _expr_two_powers(rng: random.Random) -> _Expr:
    """`2^5 + 3^3` — two powers, neither of them the whole answer."""
    (b1, e1), (b2, e2) = rng.sample(_SMALL_POWERS, 2)
    return _Expr(f"{b1}^{e1} + {b2}^{e2}", b1 ** e1 + b2 ** e2)


def _expr_factorial_mix(rng: random.Random) -> _Expr:
    """`6! - 200`, `4! × 3` — a factorial that isn't the final answer."""
    n = rng.randint(4, 7)
    value = factorial(n)
    roll = rng.random()
    if roll < 0.4:
        c = rng.randint(2, max(3, value // 2))
        return _Expr(f"{n}! - {c}", value - c)
    if roll < 0.7:
        c = rng.randint(2, 60)
        return _Expr(f"{n}! + {c}", value + c)
    m = rng.randint(2, 5)
    return _Expr(f"{m} × {n}!", m * value)


def _expr_mul_sub(rng: random.Random) -> _Expr:
    """`9 × 7 - 12` — precedence again, the other way round."""
    x, y = rng.randint(3, 12), rng.randint(3, 12)
    product = x * y
    c = rng.randint(2, max(3, product - 1))
    return _Expr(f"{x} × {y} - {c}", product - c)


def _expr_div_add(rng: random.Random) -> _Expr:
    """`48 ÷ 6 + 15` — division first, then the addition."""
    divisor, quotient = rng.randint(2, 9), rng.randint(2, 12)
    c = rng.randint(2, 40)
    return _Expr(f"{divisor * quotient} ÷ {divisor} + {c}", quotient + c)


def _expr_two_products(rng: random.Random) -> _Expr:
    """`4 × 6 + 3 × 5` — two multiplications before a single add."""
    a, b, c, d = (rng.randint(2, 12) for _ in range(4))
    return _Expr(f"{a} × {b} + {c} × {d}", a * b + c * d)


_POWER_REMINDER = "Reminder: 4^3 means 4 × 4 × 4."
_FACTORIAL_REMINDER = "Reminder: 5! means 5 × 4 × 3 × 2 × 1."


def _compare(rng: random.Random, left: _Expr, right: _Expr, tag: str, reminder: str | None = None):
    """Build a "write <, > or =" question from two worked-out sides.

    Which side goes first is a coin flip, so no builder can skew the
    answer — a kid guessing "<" every time shouldn't beat the odds.
    """
    if rng.random() < 0.5:
        left, right = right, left
    answer = "<" if left.value < right.value else (">" if left.value > right.value else "=")
    text = "\n\n".join(filter(None, [
        reminder,
        "Write <, > or = in the blank:",
        f"{left.text} _ {right.text}",
    ]))
    explanation = (
        f"{left.text} = {left.value} and {right.text} = {right.value}, "
        f"so {left.text} {answer} {right.text}. ⚖️"
    )
    # Sorted, so the coin flip above can't smuggle the same pair back
    # into a quiz with the sides swapped — that reads as a repeat even
    # though the answer flipped.
    return (tag, *sorted([left.text, right.text])), text, answer, explanation


def _cmp_sums(rng: random.Random, lo: int, hi: int):
    """Grade 3: still only +, but both sides need adding up first."""
    left = _expr_sum(rng, 12, 99)
    right = (
        _expr_sum(rng, 12, 99, target=left.value)
        if rng.random() < 0.2
        else _expr_sum(rng, 12, 99)
    )
    return _compare(rng, left, right, "cmpsum")


def _cmp_sum_biggest(rng: random.Random, lo: int, hi: int):
    """Three sums to work out before you can pick the biggest."""
    exprs: list[_Expr] = []
    while len(exprs) < 3:
        candidate = _expr_sum(rng, 12, 99)
        if all(candidate.value != e.value for e in exprs):
            exprs.append(candidate)
    best = max(exprs, key=lambda e: e.value)
    joined = ", ".join(e.text for e in exprs[:-1]) + f", or {exprs[-1].text}"
    workings = ", ".join(f"{e.text} = {e.value}" for e in exprs)
    return (
        ("cmpsumbig", tuple(sorted(e.text for e in exprs))),
        f"Which one is the biggest: {joined}?\n\nWrite the answer as a number.",
        best.value,
        f"{workings}. The biggest is {best.value}! ⚖️",
    )


def _cmp_expr_biggest(rng: random.Random, lo: int, hi: int):
    """Three mixed-operator expressions — work them all out, then pick."""
    exprs: list[_Expr] = []
    guard = 0
    while len(exprs) < 3 and guard < 60:
        guard += 1
        candidate = rng.choice([_expr_mul_add, lambda r: _expr_brackets(r)])(rng)
        if candidate and all(candidate.value != e.value for e in exprs):
            exprs.append(candidate)
    if len(exprs) < 3:
        return _cmp_sum_biggest(rng, lo, hi)
    best = max(exprs, key=lambda e: e.value)
    joined = ", ".join(e.text for e in exprs[:-1]) + f", or {exprs[-1].text}"
    workings = ", ".join(f"{e.text} = {e.value}" for e in exprs)
    return (
        ("cmpexprbig", tuple(sorted(e.text for e in exprs))),
        f"Which one is the biggest: {joined}?\n\nWrite the answer as a number.",
        best.value,
        f"{workings}. The biggest is {best.value}! ⚖️",
    )


def _sequence_doubling(rng: random.Random, lo: int, hi: int):
    """A sequence that multiplies instead of adding."""
    start = rng.randint(2, 9)
    step = rng.choice([2, 3])
    terms = [start * step ** i for i in range(4)]
    return (
        ("seqmul", start, step),
        "What number comes next: " + ", ".join(str(t) for t in terms) + ", ?",
        terms[-1] * step,
        f"Each number is {step} times the one before: {terms[-1]} × {step} = {terms[-1] * step}! 🔁",
    )


def _round_to_hundred(rng: random.Random, lo: int, hi: int):
    n = rng.randint(150, 9_499)
    if n % 100 == 0:
        n += rng.randint(1, 99)
    answer = ((n + 50) // 100) * 100
    return (
        ("round100", n),
        f"Round {n} to the nearest 100.",
        answer,
        f"{n} is closest to {answer}. Look at the tens digit: 5 or more rounds up! 🎯",
    )


def _cmp_big_sums(rng: random.Random, lo: int, hi: int):
    """Grade 4: the same idea with numbers worth lining up carefully."""
    left = _expr_sum(rng, 120, 999)
    right = (
        _expr_sum(rng, 120, 999, target=left.value)
        if rng.random() < 0.2
        else _expr_sum(rng, 120, 999)
    )
    return _compare(rng, left, right, "cmpbigsum")


def _cmp_mixed_ops(rng: random.Random, lo: int, hi: int):
    """Grade 4: × and + on both sides — precedence decides the answer."""
    left = _expr_mul_add(rng)
    if left is None:
        return _cmp_sums(rng, lo, hi)
    right = _expr_mul_add(rng, target=left.value) if rng.random() < 0.2 else _expr_mul_add(rng)
    if right is None:
        right = _expr_mul_add(rng)
    return _compare(rng, left, right, "cmpops")


def _cmp_brackets(rng: random.Random, lo: int, hi: int):
    """Grade 5: brackets against plain precedence."""
    left = _expr_brackets(rng)
    right = _expr_mul_add(rng) or _expr_sum(rng, 20, 99)
    return _compare(rng, left, right, "cmpbrackets")


def _cmp_powers(rng: random.Random, lo: int, hi: int):
    """Grade 5: 4^5 against 5^4 — same digits, very different answers."""
    if rng.random() < 0.2:
        (b1, e1), (b2, e2) = rng.choice(_EQUAL_POWERS)
    else:
        (b1, e1), (b2, e2) = rng.sample(_POWERS, 2)
    left, right = _Expr(f"{b1}^{e1}", b1 ** e1), _Expr(f"{b2}^{e2}", b2 ** e2)
    return _compare(rng, left, right, "cmppow", _POWER_REMINDER)


def _cmp_factorial(rng: random.Random, lo: int, hi: int):
    """Grade 5: how a factorial outruns a power."""
    left = _expr_factorial(rng)
    right = _expr_power(rng)
    reminder = "Reminder: 5! means 5 × 4 × 3 × 2 × 1, and 4^3 means 4 × 4 × 4."
    return _compare(rng, left, right, "cmpfact", reminder)


def _cmp_arithmetic_mix(rng: random.Random, lo: int, hi: int):
    """Grade 4: two expressions drawn from several shapes, not one.

    Before this the grade-4 comparison was `x × y + z` on both sides
    nearly every time; a quiz of ten looked like one question repeated.
    """
    builders = (_expr_mul_add_only, _expr_mul_sub, _expr_div_add,
                _expr_two_products, _expr_brackets)
    left = rng.choice(builders)(rng)
    right = rng.choice(builders)(rng)
    return _compare(rng, left, right, "cmpmix")


def _cmp_power_mix(rng: random.Random, lo: int, hi: int):
    """Grade 5: powers and factorials with arithmetic around them.

    `3^4 _ 4!` on its own is one shape, and ten of them in a row is the
    same question ten times over — the reported complaint. These sides
    look like `2^4 + 3 × 2 + 8`, `3 × 2^5`, `6! - 200`, so the pattern
    changes even when the skill doesn't.
    """
    builders = (_expr_power_plus, _expr_power_scaled, _expr_power_minus,
                _expr_two_powers, _expr_factorial_mix)
    left = rng.choice(builders)(rng)
    right = rng.choice(builders)(rng)
    reminder = (
        "Reminder: 4^3 means 4 × 4 × 4, and 5! means 5 × 4 × 3 × 2 × 1."
        if "!" in left.text + right.text
        else _POWER_REMINDER
    )
    return _compare(rng, left, right, "cmppowmix", reminder)


_COMPARISON_TIERS = {
    # Numbers on their own while that's the skill...
    "basic": (_cmp_symbol, _even_odd, _sequence_next),
    "numbers": (_cmp_symbol, _even_odd, _sequence_next, _cmp_biggest, _place_value),
    # ...then both sides of the comparison become something to work out.
    "sums": (_cmp_sums, _cmp_sum_biggest, _sequence_next, _place_value, _round_to_ten),
    "operators": (
        _cmp_mixed_ops, _cmp_arithmetic_mix, _cmp_big_sums, _cmp_expr_biggest,
        _sequence_doubling, _round_to_hundred,
    ),
    "powers": (
        _cmp_powers, _cmp_power_mix, _cmp_factorial, _cmp_brackets,
        _cmp_arithmetic_mix, _cmp_expr_biggest, _sequence_doubling,
    ),
}


def _comparison_tier(difficulty: Difficulty, g: int) -> str:
    """Numbers alone until grade 3, then expressions on both sides —
    read off the level ladder (curriculum.level)."""
    lvl = curriculum.level(difficulty, Grade.K if g == 0 else Grade(str(g)))
    if lvl >= 11:
        return "powers"
    if lvl >= 8:
        return "operators"
    if lvl >= 7:
        return "sums"
    if lvl >= 5:
        return "numbers"
    return "basic"


# ---------- decimals: exact arithmetic in integer tenths/hundredths ----------


def _fmt_tenths(v: int) -> str:
    return f"{v // 10}.{v % 10}"


def _fmt_hundredths(v: int) -> str:
    return f"{v // 100}.{v % 100:02d}"


def _dec_add_tenths(rng: random.Random, lo: int, hi: int):
    a, b = rng.randint(1, 9), rng.randint(1, 9)
    lo_, hi_ = (a, b) if a <= b else (b, a)
    return (
        ("decadd", lo_, hi_),
        f"{_fmt_tenths(a)} + {_fmt_tenths(b)} = ?",
        _fmt_tenths(a + b),
        f"{a} tenths + {b} tenths = {a + b} tenths = {_fmt_tenths(a + b)}! 🔢",
    )


def _dec_sub_tenths(rng: random.Random, lo: int, hi: int):
    a = rng.randint(2, 18)
    b = rng.randint(1, min(a, 9))
    return (
        ("decsub", a, b),
        f"{_fmt_tenths(a)} - {_fmt_tenths(b)} = ?",
        _fmt_tenths(a - b),
        f"{a} tenths - {b} tenths = {a - b} tenths = {_fmt_tenths(a - b)}! 🔢",
    )


def _dec_add_hundredths(rng: random.Random, lo: int, hi: int):
    a, b = rng.randint(5, 395), rng.randint(5, 395)
    lo_, hi_ = (a, b) if a <= b else (b, a)
    return (
        ("decadd100", lo_, hi_),
        f"{_fmt_hundredths(a)} + {_fmt_hundredths(b)} = ?",
        _fmt_hundredths(a + b),
        f"Line up the decimal points: {_fmt_hundredths(a)} + {_fmt_hundredths(b)} "
        f"= {_fmt_hundredths(a + b)}! 🔢",
    )


def _dec_compare(rng: random.Random, lo: int, hi: int):
    # Same whole part, different fractional parts — the classic 0.7 vs 0.65 trap.
    whole = rng.randint(0, 5)
    t = rng.randint(1, 9)
    h = rng.randint(1, 99)
    if h == t * 10:
        h += 1
    a = whole * 10 + t          # tenths
    b = whole * 100 + h         # hundredths
    a_str, b_str = _fmt_tenths(a), _fmt_hundredths(b)
    answer = a_str if t * 10 > h else b_str
    return (
        ("deccmp", a, b),
        f"Which is bigger: {a_str} or {b_str}?",
        answer,
        f"Compare place by place: {a_str} is {t * 10} hundredths, {b_str} is {h} hundredths — "
        f"so {answer} is bigger! 🔢",
    )


def _dec_times_ten(rng: random.Random, lo: int, hi: int):
    v = rng.randint(1, 99)
    if v % 10 == 0:
        v += 1
    return (
        ("dec10", v),
        f"What is {_fmt_tenths(v)} × 10?",
        v,
        f"Multiplying by 10 moves the decimal point one place right: {_fmt_tenths(v)} × 10 = {v}! 🔢",
    )


def _make_decimals_basic(rng: random.Random, lo: int, hi: int):
    return rng.choice([_dec_add_tenths, _dec_sub_tenths])(rng, lo, hi)


def _make_decimals_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [_dec_add_tenths, _dec_sub_tenths, _dec_add_hundredths, _dec_compare, _dec_times_ten]
    )(rng, lo, hi)


# ---------- the level ladder: number sizes per level ----------
#
# The one-line arithmetic topics size their numbers from the level
# (curriculum.level: 2 × grade + difficulty, so grade 3 hard == grade 4
# easy), one table per topic and one row per level 0-12. The old shared
# range grew by 3 per grade, which left grade 5 on sums of numbers up to
# 35 and products up to 17 × 11 — third-grade work. Topics that pick a
# *tier* of question shapes (fractions, word problems, …) read the same
# level through their tier functions.

#: Operand range for addition and subtraction.
_ADD_BANDS: list[tuple[int, int]] = [
    (1, 5), (1, 9), (2, 12), (4, 16),        # K – grade 1: within 10, then 20
    (10, 40), (15, 70), (25, 99),            # grade 2: two-digit, regrouping
    (100, 499), (150, 999),                  # grade 3: three-digit
    (1000, 4999), (1000, 9999),              # grade 4: four-digit
    (10000, 49999), (10000, 99999),          # grade 5: five-digit (and decimals)
]

#: Largest whole part of a decimal operand, from the level decimals join
#: addition and subtraction.
_ADD_DECIMAL_WHOLES = {11: 99, 12: 999}

#: (first factor range, second factor range) for multiplication.
_MUL_BANDS: list[tuple[tuple[int, int], tuple[int, int]]] = [
    ((1, 3), (1, 5)), ((1, 3), (1, 5)),      # (not offered before grade 2)
    ((1, 5), (1, 5)), ((1, 5), (1, 5)),
    ((1, 5), (1, 5)),                        # grade 2: equal groups
    ((2, 5), (1, 10)), ((2, 5), (2, 10)),    # ×2 … ×5 facts
    ((2, 10), (2, 10)),                      # grade 3: all facts to 10 × 10
    ((11, 49), (2, 9)),                      # two-digit × one-digit
    ((101, 999), (2, 9)),                    # grade 4: three-digit × one-digit
    ((12, 99), (12, 99)),                    # two-digit × two-digit
    ((101, 999), (11, 99)),                  # grade 5: three-digit × two-digit
    ((1001, 9999), (11, 99)),                # four-digit × two-digit
]

#: (divisor range, quotient range) for division.
_DIV_BANDS: list[tuple[tuple[int, int], tuple[int, int]]] = [
    ((2, 3), (1, 5)), ((2, 3), (1, 5)),      # (not offered before grade 3)
    ((2, 5), (1, 5)), ((2, 5), (1, 5)),
    ((2, 5), (1, 5)), ((2, 5), (1, 10)),
    ((2, 5), (2, 10)),                       # grade 3: facts …
    ((2, 10), (2, 10)),                      # … to 100 ÷ 10
    ((2, 9), (11, 30)),                      # two-digit ÷ one-digit
    ((2, 9), (20, 199)),                     # grade 4: three-digit ÷ one-digit
    ((2, 9), (100, 999)),                    # four-digit ÷ one-digit
    ((11, 49), (11, 99)),                    # grade 5: two-digit divisors
    ((12, 99), (21, 199)),
]

#: (lo, hi) for the topics still written against a plain range (algebra,
#: order of operations). Steeper than `_SCENE_RANGES`.
_LEVEL_RANGES: list[tuple[int, int]] = [
    (1, 5), (1, 8), (1, 10), (2, 13), (2, 16), (2, 20), (3, 25),
    (4, 30), (5, 40), (6, 50), (8, 60), (10, 80), (12, 100),
]

#: Order of operations is about precedence, not long multiplication: its
#: factors are a quarter of `hi`, so `hi` stops where they reach 12.
_OOO_MAX_HI = 48

#: The remainder example the question shows, which no answer may equal.
_REMAINDER_EXAMPLE = "5 R 1"


def _level_band(table: list, lvl: int):
    return table[max(0, min(lvl, len(table) - 1))]


def _fmt_decimal(value: Fraction) -> str:
    """A terminating decimal without trailing zeros ("4.2", "0.0425")."""
    scaled, rest = divmod(value.numerator * 10**6, value.denominator)
    assert rest == 0, value  # every caller builds at most millionths
    s = f"{scaled // 10**6}.{scaled % 10**6:06d}".rstrip("0")
    return s.rstrip(".")


def _decimal_answer(value: Fraction) -> int | str:
    return int(value) if value.denominator == 1 else _fmt_decimal(value)


def _add_decimals(rng: random.Random, max_whole: int):
    """Two hundredths operands with up to `max_whole` wholes each."""
    a, b = rng.randint(101, max_whole * 100 + 99), rng.randint(101, max_whole * 100 + 99)
    lo_, hi_ = (a, b) if a <= b else (b, a)
    return (
        ("add", "dec", lo_, hi_),
        f"{_fmt_hundredths(a)} + {_fmt_hundredths(b)} = ?",
        _fmt_hundredths(a + b),
        f"Line up the decimal points, then add like whole numbers: "
        f"{_fmt_hundredths(a)} + {_fmt_hundredths(b)} = {_fmt_hundredths(a + b)}. 🔢",
    )


def _sub_decimals(rng: random.Random, max_whole: int):
    a = rng.randint(201, max_whole * 100 + 99)
    b = rng.randint(101, a - 1)
    return (
        ("sub", "dec", a, b),
        f"{_fmt_hundredths(a)} - {_fmt_hundredths(b)} = ?",
        _fmt_hundredths(a - b),
        f"Line up the decimal points, then subtract like whole numbers: "
        f"{_fmt_hundredths(a)} - {_fmt_hundredths(b)} = {_fmt_hundredths(a - b)}. 🔢",
    )


def _addition_at(lvl: int) -> Factory:
    lo, hi = _level_band(_ADD_BANDS, lvl)
    max_whole = _ADD_DECIMAL_WHOLES.get(min(lvl, MAX_LEVEL))

    def factory(rng: random.Random, _lo: int, _hi: int):
        if max_whole and rng.random() < 0.4:
            return _add_decimals(rng, max_whole)
        return _make_addition(rng, lo, hi)

    return factory


def _subtraction_at(lvl: int, negatives: bool) -> Factory:
    lo, hi = _level_band(_ADD_BANDS, lvl)
    max_whole = _ADD_DECIMAL_WHOLES.get(min(lvl, MAX_LEVEL))

    def factory(rng: random.Random, _lo: int, _hi: int):
        roll = rng.random()
        if negatives and roll < 0.35:
            # Below zero is about the idea, not the digits: two-digit numbers.
            return _sub_negative(rng, 10, 99)
        if max_whole and roll > 0.6:
            return _sub_decimals(rng, max_whole)
        return _sub_positive(rng, lo, hi)

    return factory


def _mul_explanation(m1: int, m2: int) -> str:
    big, small = (m1, m2) if m1 >= m2 else (m2, m1)
    if big < 10:
        return f"{m1} × {m2} = {m1 * m2}. Think of {m1} groups of {m2}! 🎯"
    if small < 10:
        tens, ones = big - big % 10, big % 10
        parts = f"{tens} × {small} + {ones} × {small}" if ones else f"{tens} × {small}"
        return (
            f"Split {big} by place value: {parts} = "
            f"{tens * small}{f' + {ones * small}' if ones else ''} = {m1 * m2}. 🎯"
        )
    tens, ones = small - small % 10, small % 10
    return (
        f"Split {small} into {tens} and {ones}: {big} × {tens} = {big * tens}, "
        f"{big} × {ones} = {big * ones}, and {big * tens} + {big * ones} = {m1 * m2}. 🎯"
    )


def _mul_decimal_by_whole(rng: random.Random):
    d = rng.randint(101, 999)
    while d % 10 == 0:
        d = rng.randint(101, 999)
    w = rng.randint(3, 12)
    value = Fraction(d, 100) * w
    return (
        ("mul", "dec", d, w),
        f"{_fmt_hundredths(d)} × {w} = ?",
        _decimal_answer(value),
        f"Multiply as if there were no point: {d} × {w} = {d * w}. "
        f"There were two decimal places, so put two back: {_fmt_decimal(value)}. 🎯",
    )


def _multiplication_at(lvl: int) -> Factory:
    (a_lo, a_hi), (b_lo, b_hi) = _level_band(_MUL_BANDS, lvl)

    def factory(rng: random.Random, _lo: int, _hi: int):
        if lvl >= MAX_LEVEL and rng.random() < 0.3:
            return _mul_decimal_by_whole(rng)
        m1, m2 = rng.randint(a_lo, a_hi), rng.randint(b_lo, b_hi)
        if a_hi <= 10 and rng.random() < 0.5:  # facts read both ways round
            m1, m2 = m2, m1
        lo_, hi_ = (m1, m2) if m1 <= m2 else (m2, m1)
        return (
            ("mul", lo_, hi_),
            f"{m1} × {m2} = ?",
            m1 * m2,
            _mul_explanation(m1, m2),
        )

    return factory


def _div_exact_band(rng: random.Random, divisors: tuple[int, int], quotients: tuple[int, int]):
    divisor, answer = rng.randint(*divisors), rng.randint(*quotients)
    dividend = divisor * answer
    if answer <= 10 and divisor <= 10:
        why = f"{dividend} split into {divisor} equal groups gives {answer}! 🍰"
    else:
        why = f"Check it by multiplying back: {divisor} × {answer} = {dividend}. 🍰"
    return (
        ("div", dividend, divisor),
        f"{dividend} ÷ {divisor} = ?",
        answer,
        f"{dividend} ÷ {divisor} = {answer}. {why}",
    )


def _div_with_remainder_band(rng: random.Random, divisors: tuple[int, int],
                             quotients: tuple[int, int]):
    """Long division with the whole answer written out: 1234 ÷ 7 = 176 R 2."""
    divisor, quotient = rng.randint(*divisors), rng.randint(*quotients)
    remainder = rng.randint(1, divisor - 1)
    dividend = divisor * quotient + remainder
    answer = f"{quotient} R {remainder}"
    if answer == _REMAINDER_EXAMPLE:
        return _div_exact_band(rng, divisors, quotients)
    return (
        ("divR", dividend, divisor),
        f"What is {dividend} ÷ {divisor}? Write it with a remainder "
        f"(e.g. {_REMAINDER_EXAMPLE}).",
        answer,
        f"{divisor} × {quotient} = {divisor * quotient}, and {dividend} − "
        f"{divisor * quotient} = {remainder} left over: {answer}. 🧮",
    )


def _division_at(lvl: int) -> Factory:
    divisors, quotients = _level_band(_DIV_BANDS, lvl)

    def exact(rng, _lo, _hi):
        return _div_exact_band(rng, divisors, quotients)

    def remainder_only(rng, _lo, _hi):
        # Grade 3: the remainder alone, with small numbers.
        return _div_remainder(rng, 1, 2 * divisors[1] + 1)

    def full_remainder(rng, _lo, _hi):
        return _div_with_remainder_band(rng, divisors, quotients)

    if lvl >= MAX_LEVEL:
        shapes = (exact, full_remainder, exact, full_remainder, _div_fraction, _div_decimal)
    elif lvl >= 8:
        shapes = (exact, full_remainder)
    elif lvl >= 7:
        shapes = (exact, remainder_only)
    else:
        shapes = (exact,)

    def factory(rng: random.Random, lo: int, hi: int):
        return rng.choice(shapes)(rng, lo, max(hi, 24))

    return factory


# ---------- decimals at grade 4-5 ----------


def _dec_sub_hundredths(rng: random.Random, lo: int, hi: int):
    a = rng.randint(105, 995)
    b = rng.randint(5, a - 1)
    return (
        ("decsub100", a, b),
        f"{_fmt_hundredths(a)} - {_fmt_hundredths(b)} = ?",
        _fmt_hundredths(a - b),
        f"Line up the decimal points: {_fmt_hundredths(a)} - {_fmt_hundredths(b)} "
        f"= {_fmt_hundredths(a - b)}! 🔢",
    )


def _dec_add_big(rng: random.Random, lo: int, hi: int):
    return _add_decimals(rng, 99)


def _dec_sub_big(rng: random.Random, lo: int, hi: int):
    return _sub_decimals(rng, 99)


def _dec_times_power(rng: random.Random, lo: int, hi: int):
    """× or ÷ by 10 or 100: the point moves, the digits don't."""
    d = rng.randint(101, 9999)
    while d % 10 == 0:
        d = rng.randint(101, 9999)
    power = rng.choice([10, 100])
    if rng.random() < 0.5:
        value, op, way = Fraction(d, 100) * power, "×", "right"
    else:
        value, op, way = Fraction(d, 100) / power, "÷", "left"
    places = "one place" if power == 10 else "two places"
    return (
        ("decpow", d, op, power),
        f"{_fmt_hundredths(d)} {op} {power} = ?",
        _decimal_answer(value),
        f"{op} {power} moves the decimal point {places} {way}: "
        f"{_fmt_hundredths(d)} {op} {power} = {_fmt_decimal(value)}! 🔢",
    )


def _dec_times_whole(rng: random.Random, lo: int, hi: int):
    t = rng.randint(11, 99)
    while t % 10 == 0:
        t = rng.randint(11, 99)
    w = rng.randint(2, 9)
    value = Fraction(t, 10) * w
    return (
        ("decmulw", t, w),
        f"{_fmt_tenths(t)} × {w} = ?",
        _decimal_answer(value),
        f"{t} tenths × {w} = {t * w} tenths = {_fmt_decimal(value)}! 🔢",
    )


def _dec_times_dec(rng: random.Random, lo: int, hi: int):
    a, b = rng.randint(2, 39), rng.randint(2, 9)
    while a % 10 == 0:
        a = rng.randint(2, 39)
    value = Fraction(a, 10) * Fraction(b, 10)
    return (
        ("decmuld", a, b),
        f"{_fmt_tenths(a)} × {_fmt_tenths(b)} = ?",
        _decimal_answer(value),
        f"Multiply without the points: {a} × {b} = {a * b}. Each number had one "
        f"decimal place, so the answer has two: {_fmt_decimal(value)}! 🔢",
    )


def _dec_div_whole(rng: random.Random, lo: int, hi: int):
    w = rng.randint(2, 9)
    q = rng.randint(11, 99)
    while q % 10 == 0:
        q = rng.randint(11, 99)
    dividend = Fraction(q * w, 10)
    return (
        ("decdivw", q * w, w),
        f"{_fmt_decimal(dividend)} ÷ {w} = ?",
        _fmt_decimal(Fraction(q, 10)),
        f"Divide as if there were no point: {q * w} ÷ {w} = {q}, then put the point "
        f"back: {_fmt_decimal(Fraction(q, 10))}! 🔢",
    )


_DECIMAL_SHAPES_OPS = (
    _dec_add_hundredths, _dec_sub_hundredths, _dec_compare, _dec_times_power, _dec_times_whole,
)
_DECIMAL_SHAPES_FLUENT = (
    _dec_add_big, _dec_sub_big, _dec_times_power, _dec_times_whole, _dec_times_dec,
    _dec_div_whole, _dec_compare,
)


def _ooo_brackets_four(rng: random.Random, lo: int, hi: int):
    """(8 + 4) × 3 - 6 ÷ 2: brackets, then × and ÷, then the subtraction."""
    a, b = rng.randint(lo, hi // 2), rng.randint(1, max(2, hi // 4))
    c = rng.randint(2, max(3, hi // 6))
    e = rng.randint(2, 9)
    q = rng.randint(1, max(2, ((a + b) * c) // e))
    d = q * e
    answer = (a + b) * c - q
    return (
        ("ooo_b4", a, b, c, d, e),
        f"({a} + {b}) × {c} - {d} ÷ {e} = ?",
        answer,
        f"Brackets first: {a} + {b} = {a + b}. Then × and ÷: {a + b} × {c} = {(a + b) * c} "
        f"and {d} ÷ {e} = {q}. Last, subtract: {(a + b) * c} - {q} = {answer}. 📐",
    )


def _make_ooo_fluent(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [_ooo_three_terms, _ooo_parens, _ooo_brackets_four, _ooo_brackets_four]
    )(rng, lo, hi)


# ---------- geometry: sample from curated pools by difficulty ----------
#
# Three tiers:
#   EASY   — shape identification, counting sides / corners / vertices
#   MEDIUM — perimeter & area with small numbers, basic 3D solid facts
#   HARD   — area / volume formulas, angle arithmetic, triangle
#            classification (equilateral / isosceles / scalene)
#
# Answers may be int or string (e.g. "triangle", "acute"); `grade_answer`
# compares strings case-insensitively.

GeometryItem = tuple[str, int | str, str]

_GEOMETRY_EASY: list[GeometryItem] = [
    # identification
    ("Which shape has exactly 3 sides?", "triangle", "A triangle has 3 sides! 📐"),
    ("Which shape has 4 equal sides and 4 right angles?", "square", "All sides equal + right angles = square! ⬜"),
    ("Which shape has no straight sides?", "circle", "A circle is perfectly round! ⭕"),
    ("A STOP sign is shaped like which polygon?", "octagon", "STOP signs are octagons — 8 sides! 🛑"),
    ("A YIELD sign is shaped like which polygon?", "triangle", "YIELD signs are triangles! ⚠️"),
    ("A shape with 4 sides is called a ___.", "quadrilateral", "Quad = 4, so quadrilateral! 🔲"),
    ("Which 2D shape has 5 sides?", "pentagon", "Penta = 5, so pentagon! ⭐"),
    ("Which 2D shape has 6 sides?", "hexagon", "Hexa = 6 (like honeycomb)! 🐝"),
    ("Which 2D shape has 8 sides?", "octagon", "Octa = 8 (like an octopus)! 🐙"),
    # sides
    ("How many sides does a triangle have?", 3, "A triangle always has 3 sides! 📐"),
    ("How many sides does a square have?", 4, "A square has 4 equal sides! ⬜"),
    ("How many sides does a rectangle have?", 4, "A rectangle has 4 sides! 🟩"),
    ("How many sides does a pentagon have?", 5, "Penta means 5, so 5 sides! ⭐"),
    ("How many sides does a hexagon have?", 6, "Hexa means 6, so 6 sides! 🔷"),
    ("How many sides does a heptagon have?", 7, "Hepta means 7! 🔷"),
    ("How many sides does an octagon have?", 8, "Octa means 8! 🐙"),
    ("How many sides does a nonagon have?", 9, "Nona means 9! 🔷"),
    ("How many sides does a decagon have?", 10, "Deca means 10! 🔟"),
    ("How many sides does a rhombus have?", 4, "A rhombus (diamond) has 4 sides! 💠"),
    ("How many sides does a trapezoid have?", 4, "A trapezoid has 4 sides! 🔻"),
    ("How many sides does a parallelogram have?", 4, "A parallelogram has 4 sides! 🔲"),
    ("How many sides does a kite (shape) have?", 4, "A kite has 4 sides! 🪁"),
    ("How many sides does a circle have?", 0, "A circle has no straight sides — it's a curve! ⭕"),
    # corners / vertices
    ("How many corners does a triangle have?", 3, "3 sides → 3 corners! 📐"),
    ("How many corners does a square have?", 4, "4 sides → 4 corners! ⬜"),
    ("How many corners does a rectangle have?", 4, "A rectangle has 4 corners (vertices)! 🟩"),
    ("How many corners does a pentagon have?", 5, "5 sides → 5 corners! ⭐"),
    ("How many corners does a hexagon have?", 6, "6 sides → 6 corners! 🔷"),
    ("How many corners does a heptagon have?", 7, "7 sides → 7 corners! 🔷"),
    ("How many corners does an octagon have?", 8, "8 sides → 8 corners! 🐙"),
    ("How many corners does a nonagon have?", 9, "9 sides → 9 corners! 🔷"),
    ("How many corners does a decagon have?", 10, "10 sides → 10 corners! 🔟"),
    ("How many vertices does a triangle have?", 3, "Vertices = corners. A triangle has 3! 📐"),
    ("How many vertices does a square have?", 4, "Vertices = corners. A square has 4! ⬜"),
    ("How many vertices does a pentagon have?", 5, "A pentagon has 5 vertices! ⭐"),
    ("How many vertices does a hexagon have?", 6, "A hexagon has 6 vertices! 🔷"),
    # simple facts
    ("How many sides does a STOP sign have?", 8, "STOP signs are octagons — 8 sides! 🛑"),
    ("A circle has how many corners?", 0, "Circles have no corners — just one smooth curve! ⭕"),
    ("How many right angles are in a square?", 4, "Every corner of a square is a right angle! ⬜"),
    ("How many right angles are in a rectangle?", 4, "All 4 corners of a rectangle are right angles! 🟩"),
    ("How many sides does a regular hexagon have?", 6, "Regular hexagons have 6 equal sides! 🐝"),
]

_GEOMETRY_MEDIUM: list[GeometryItem] = [
    # perimeter — squares
    ("Perimeter of a square with side 5? (P = 4×s)", 20, "4 × 5 = 20 🧮"),
    ("Perimeter of a square with side 3? (P = 4×s)", 12, "4 × 3 = 12 🧮"),
    ("Perimeter of a square with side 7? (P = 4×s)", 28, "4 × 7 = 28 🧮"),
    ("Perimeter of a square with side 10? (P = 4×s)", 40, "4 × 10 = 40 🧮"),
    ("Perimeter of a square with side 6? (P = 4×s)", 24, "4 × 6 = 24 🧮"),
    # perimeter — rectangles
    ("Perimeter of a rectangle 4 × 6? (P = 2(l+w))", 20, "2 × (4 + 6) = 20 🧮"),
    ("Perimeter of a rectangle 5 × 3? (P = 2(l+w))", 16, "2 × (5 + 3) = 16 🧮"),
    ("Perimeter of a rectangle 8 × 2? (P = 2(l+w))", 20, "2 × (8 + 2) = 20 🧮"),
    ("Perimeter of a rectangle 10 × 4? (P = 2(l+w))", 28, "2 × (10 + 4) = 28 🧮"),
    ("Perimeter of a rectangle 7 × 3? (P = 2(l+w))", 20, "2 × (7 + 3) = 20 🧮"),
    # perimeter — triangle
    ("Perimeter of an equilateral triangle with side 4? (P = 3×s)", 12, "3 × 4 = 12 🔺"),
    ("Perimeter of an equilateral triangle with side 7? (P = 3×s)", 21, "3 × 7 = 21 🔺"),
    ("Perimeter of an equilateral triangle with side 9? (P = 3×s)", 27, "3 × 9 = 27 🔺"),
    # area — squares
    ("Area of a square with side 5? (A = s²)", 25, "5 × 5 = 25 🧮"),
    ("Area of a square with side 4? (A = s²)", 16, "4 × 4 = 16 🧮"),
    ("Area of a square with side 6? (A = s²)", 36, "6 × 6 = 36 🧮"),
    ("Area of a square with side 3? (A = s²)", 9, "3 × 3 = 9 🧮"),
    ("Area of a square with side 8? (A = s²)", 64, "8 × 8 = 64 🧮"),
    # area — rectangles
    ("Area of a rectangle 4 × 5? (A = l×w)", 20, "4 × 5 = 20 🧮"),
    ("Area of a rectangle 6 × 3? (A = l×w)", 18, "6 × 3 = 18 🧮"),
    ("Area of a rectangle 7 × 2? (A = l×w)", 14, "7 × 2 = 14 🧮"),
    ("Area of a rectangle 8 × 5? (A = l×w)", 40, "8 × 5 = 40 🧮"),
    ("Area of a rectangle 10 × 3? (A = l×w)", 30, "10 × 3 = 30 🧮"),
    ("Area of a rectangle 9 × 4? (A = l×w)", 36, "9 × 4 = 36 🧮"),
    # 3D — cubes
    ("How many faces does a cube have?", 6, "A cube has 6 square faces! 🎲"),
    ("How many edges does a cube have?", 12, "A cube has 12 edges! 📦"),
    ("How many vertices does a cube have?", 8, "A cube has 8 corners! 🎲"),
    # 3D — rectangular prism
    ("How many faces does a rectangular prism have?", 6, "A box has 6 faces! 📦"),
    ("How many edges does a rectangular prism have?", 12, "A box has 12 edges! 📦"),
    ("How many vertices does a rectangular prism have?", 8, "A box has 8 corners! 📦"),
    # 3D — triangular prism
    ("How many faces does a triangular prism have?", 5, "2 triangle faces + 3 rectangle faces = 5! 🔺"),
    ("How many edges does a triangular prism have?", 9, "A triangular prism has 9 edges! 🔺"),
    ("How many vertices does a triangular prism have?", 6, "A triangular prism has 6 corners! 🔺"),
    # 3D — square pyramid
    ("How many faces does a square pyramid have?", 5, "1 square base + 4 triangle faces = 5! 🔺"),
    ("How many edges does a square pyramid have?", 8, "A square pyramid has 8 edges! 🔺"),
    ("How many vertices does a square pyramid have?", 5, "4 base corners + 1 top = 5! 🔺"),
    # 3D — tetrahedron
    ("How many faces does a tetrahedron (triangular pyramid) have?", 4, "4 triangle faces! 🔺"),
    ("How many edges does a tetrahedron have?", 6, "A tetrahedron has 6 edges! 🔺"),
    ("How many vertices does a tetrahedron have?", 4, "A tetrahedron has 4 corners! 🔺"),
    # 3D — cylinder / cone
    ("How many flat faces does a cylinder have?", 2, "2 circular flat faces (top + bottom)! 🥫"),
    ("How many flat faces does a cone have?", 1, "1 flat circular base! 🍦"),
]

_GEOMETRY_HARD: list[GeometryItem] = [
    # area of triangles
    ("Area of a triangle, base 6, height 4? (A = ½×b×h)", 12, "½ × 6 × 4 = 12 🔺"),
    ("Area of a triangle, base 10, height 8? (A = ½×b×h)", 40, "½ × 10 × 8 = 40 🔺"),
    ("Area of a triangle, base 5, height 6? (A = ½×b×h)", 15, "½ × 5 × 6 = 15 🔺"),
    ("Area of a triangle, base 12, height 5? (A = ½×b×h)", 30, "½ × 12 × 5 = 30 🔺"),
    ("Area of a triangle, base 8, height 7? (A = ½×b×h)", 28, "½ × 8 × 7 = 28 🔺"),
    # area of parallelograms
    ("Area of a parallelogram, base 7, height 4? (A = b×h)", 28, "7 × 4 = 28 🔲"),
    ("Area of a parallelogram, base 9, height 5? (A = b×h)", 45, "9 × 5 = 45 🔲"),
    ("Area of a parallelogram, base 12, height 6? (A = b×h)", 72, "12 × 6 = 72 🔲"),
    # area — bigger squares
    ("Area of a square with side 9? (A = s²)", 81, "9 × 9 = 81 🧮"),
    ("Area of a square with side 12? (A = s²)", 144, "12 × 12 = 144 🧮"),
    ("Area of a rectangle 12 × 5? (A = l×w)", 60, "12 × 5 = 60 🧮"),
    ("Area of a rectangle 15 × 4? (A = l×w)", 60, "15 × 4 = 60 🧮"),
    # volume — cubes
    ("Volume of a cube with side 2? (V = s³)", 8, "2³ = 8 🎲"),
    ("Volume of a cube with side 3? (V = s³)", 27, "3³ = 27 🎲"),
    ("Volume of a cube with side 4? (V = s³)", 64, "4³ = 64 🎲"),
    ("Volume of a cube with side 5? (V = s³)", 125, "5³ = 125 🎲"),
    # volume — rectangular prisms
    ("Volume of a rectangular prism 2×3×4? (V = l×w×h)", 24, "2 × 3 × 4 = 24 📦"),
    ("Volume of a rectangular prism 5×2×3? (V = l×w×h)", 30, "5 × 2 × 3 = 30 📦"),
    ("Volume of a rectangular prism 4×4×5? (V = l×w×h)", 80, "4 × 4 × 5 = 80 📦"),
    ("Volume of a rectangular prism 6×2×5? (V = l×w×h)", 60, "6 × 2 × 5 = 60 📦"),
    ("Volume of a rectangular prism 3×3×3? (V = l×w×h)", 27, "3 × 3 × 3 = 27 📦"),
    # perimeters — regular polygons
    ("Perimeter of a regular pentagon with side 6? (P = 5×s)", 30, "5 × 6 = 30 ⭐"),
    ("Perimeter of a regular hexagon with side 5? (P = 6×s)", 30, "6 × 5 = 30 🔷"),
    ("Perimeter of a regular octagon with side 4? (P = 8×s)", 32, "8 × 4 = 32 🐙"),
    # angles
    ("How many degrees in a right angle?", 90, "A right angle is always 90°! 📏"),
    ("How many degrees in a straight angle?", 180, "A straight angle is 180°! 📏"),
    ("How many degrees in a full turn?", 360, "One full turn = 360°! 🔄"),
    ("Sum of interior angles of a triangle?", 180, "Every triangle's angles add to 180°! 🔺"),
    ("Sum of interior angles of a quadrilateral?", 360, "Any 4-sided shape's angles add to 360°! 🔲"),
    ("Two angles of a triangle are 60° and 70°. The third?", 50, "180 − 60 − 70 = 50° 🔺"),
    ("Two angles of a triangle are 40° and 50°. The third?", 90, "180 − 40 − 50 = 90° 🔺"),
    ("Two angles of a triangle are 30° and 80°. The third?", 70, "180 − 30 − 80 = 70° 🔺"),
    ("An angle less than 90° is called ___.", "acute", "Less than 90° = acute! 📐"),
    ("An angle greater than 90° but less than 180° is called ___.", "obtuse", "Between 90° and 180° = obtuse! 📐"),
    ("An angle exactly 90° is called ___.", "right", "Exactly 90° = right angle! 📐"),
    # triangle classification
    ("A triangle with all 3 sides equal is called ___.", "equilateral", "Equi = equal! 🔺"),
    ("A triangle with exactly 2 sides equal is called ___.", "isosceles", "Isosceles = 2 equal sides! 🔺"),
    ("A triangle with no sides equal is called ___.", "scalene", "Scalene = all different! 🔺"),
    ("How many equal sides does an equilateral triangle have?", 3, "All 3 sides are equal! 🔺"),
    ("How many equal sides does an isosceles triangle have?", 2, "Exactly 2 sides are equal! 🔺"),
    ("How many equal sides does a scalene triangle have?", 0, "No sides are equal! 🔺"),
    ("Each angle of an equilateral triangle measures how many degrees?", 60, "180 ÷ 3 = 60° each! 🔺"),
]

# Visual questions: the client draws the `figure` shape as SVG. Each entry
# is (question, answer, explanation, figure). Question text intentionally
# does NOT name the shape (the picture is the point), so several share
# wording — dedup within a quiz is by (text, figure), which stays unique.
VisualGeometryItem = tuple[str, int | str, str, str]

_GEOMETRY_VISUAL: list[VisualGeometryItem] = [
    ("How many sides does this shape have?", 3, "A triangle has 3 sides! 📐", "triangle"),
    ("How many sides does this shape have?", 4, "A square has 4 sides! ⬜", "square"),
    ("How many sides does this shape have?", 5, "A pentagon has 5 sides! ⭐", "pentagon"),
    ("How many sides does this shape have?", 6, "A hexagon has 6 sides! 🔷", "hexagon"),
    ("How many sides does this shape have?", 8, "An octagon has 8 sides! 🐙", "octagon"),
    ("How many sides does this shape have?", 0, "A circle has no straight sides! ⭕", "circle"),
    ("How many corners does this shape have?", 3, "3 sides → 3 corners! 📐", "triangle"),
    ("How many corners does this shape have?", 5, "5 sides → 5 corners! ⭐", "pentagon"),
    ("How many corners does this shape have?", 6, "6 sides → 6 corners! 🔷", "hexagon"),
    ("How many corners does this shape have?", 8, "8 sides → 8 corners! 🐙", "octagon"),
    ("What is the name of this shape?", "triangle", "3 sides makes a triangle! 📐", "triangle"),
    ("What is the name of this shape?", "square", "4 equal sides makes a square! ⬜", "square"),
    ("What is the name of this shape?", "pentagon", "5 sides makes a pentagon! ⭐", "pentagon"),
    ("What is the name of this shape?", "hexagon", "6 sides makes a hexagon! 🔷", "hexagon"),
    ("What is the name of this shape?", "circle", "A round shape is a circle! ⭕", "circle"),
]


def _geometry_tier(difficulty: Difficulty, grade: Grade) -> int:
    """0 = identification, 1 = properties, 2 = formulas & reasoning.

    Read off the level ladder (curriculum.level), so grade 3 hard —
    area and perimeter — is grade 4 easy too.
    """
    lvl = curriculum.level(difficulty, grade)
    if lvl >= 8:
        return 2
    if lvl >= 4:
        return 1
    return 0


def _geometry_pool(difficulty: Difficulty, grade: Grade) -> list[GeometryItem]:
    tier = _geometry_tier(difficulty, grade)
    # Visual shape-ID questions ride along with the EASY tier. Entries
    # may be 3-tuples (text-only) or 4-tuples (with a figure);
    # _generate_geometry normalizes both. The richer visual questions
    # (symmetry, angles, perimeter/area) are generated per quiz — see
    # _visual_items.
    if tier == 0:
        return _GEOMETRY_EASY + _GEOMETRY_VISUAL
    if tier == 1:
        return _GEOMETRY_EASY + _GEOMETRY_VISUAL + _GEOMETRY_MEDIUM
    return _GEOMETRY_MEDIUM + _GEOMETRY_HARD


# ---------- visual geometry beyond shape ID ----------
#
# The same grade ladder the text questions follow, applied to pictures:
# K-2 identify the shape they see; grade 2-3 read a *property* off the
# figure (symmetry, what kind of angle); grade 4-5 compute from labelled
# dimensions (perimeter, then area). The rectangle's numbers are drawn
# in the figure — reading data off a diagram is the skill — while the
# angle figure is deliberately unlabelled, because printing the degrees
# would answer "acute or obtuse?" by itself.

_SYMMETRY_SHAPES = [
    ("square", 4, "A square folds onto itself 4 ways!"),
    ("rectangle", 2, "A rectangle folds in half two ways — but not on its diagonals!"),
    ("triangle", 3, "This triangle has 3 equal sides, so 3 fold lines!"),
    ("pentagon", 5, "A regular pentagon: one fold line through each corner!"),
    ("hexagon", 6, "A regular hexagon: 6 fold lines!"),
    ("octagon", 8, "A regular octagon: 8 fold lines!"),
]


def _vis_symmetry(rng: random.Random, used: set) -> VisualGeometryItem | None:
    options = [x for x in _SYMMETRY_SHAPES if ("sym", x[0]) not in used]
    if not options:
        return None
    shape, count, why = rng.choice(options)
    used.add(("sym", shape))
    return (
        "How many lines of symmetry does this shape have?",
        count,
        f"{why} ✂️",
        shape,
    )


def _vis_angle_type(rng: random.Random, used: set) -> VisualGeometryItem | None:
    kind = rng.choice(["acute", "right", "obtuse"])
    if kind == "right":
        deg = 90
    elif kind == "acute":
        deg = rng.choice([20, 30, 40, 45, 55, 65, 75])
    else:
        deg = rng.choice([100, 110, 120, 130, 140, 150, 160])
    if ("angle", deg) in used:
        return None
    used.add(("angle", deg))
    return (
        "Look at this angle. Is it acute, right, or obtuse?",
        kind,
        f"This angle is {deg}° — {'exactly a quarter turn' if deg == 90 else ('smaller than 90°' if deg < 90 else 'bigger than 90°')}, so it is {kind}! 📐",
        f"angle:{deg}",
    )


def _vis_perimeter(rng: random.Random, used: set) -> VisualGeometryItem | None:
    w, h = rng.randint(3, 12), rng.randint(2, 9)
    if w == h or ("rect", w, h) in used:
        return None
    used.add(("rect", w, h))
    return (
        "The rectangle's sides are labelled in centimeters.\n\n"
        "What is its perimeter, in centimeters?",
        2 * (w + h),
        f"Perimeter goes all the way round: {w} + {h} + {w} + {h} = {2 * (w + h)} cm! 📏",
        f"rect:{w}x{h}",
    )


def _vis_area(rng: random.Random, used: set) -> VisualGeometryItem | None:
    w, h = rng.randint(3, 12), rng.randint(2, 9)
    if w == h or ("rect", w, h) in used:
        return None
    used.add(("rect", w, h))
    return (
        "The rectangle's sides are labelled in centimeters.\n\n"
        "What is its area, in square centimeters?",
        w * h,
        f"Area fills the inside: {w} × {h} = {w * h} square cm! 📐",
        f"rect:{w}x{h}",
    )


def _visual_items(difficulty: Difficulty, grade: Grade, rng: random.Random):
    """Per-quiz generated visual questions for this level.

    Tier 0 adds nothing (the static shape-ID visuals already ride along
    with the EASY pool); tier 1 reads properties off the figure; tier 2
    adds computing from labelled dimensions.
    """
    tier = _geometry_tier(difficulty, grade)
    if tier == 0:
        return []
    builders = (
        [_vis_symmetry, _vis_angle_type, _vis_perimeter]
        if tier == 1
        else [_vis_angle_type, _vis_perimeter, _vis_area, _vis_symmetry]
    )
    used: set = set()
    items = []
    for builder in builders * 2:  # two of each shape, dedup permitting
        item = builder(rng, used)
        if item is not None:
            items.append(item)
    return items


def _reading_scale(difficulty: Difficulty, g: int) -> str:
    """How much reading a scene question carries (word_problems.SCALES).

    Separate from the maths tier on purpose: a 2nd grader used to get
    the same 4-6 line list as a 4th grader — easier arithmetic, but the
    same wall of text. Grades 1-2 read a short list with no scene noise;
    grade 5 above easy reads a longer one with an extra distractor zone.
    """
    if g <= 2:
        return "short"
    if g >= 5 and difficulty != Difficulty.easy:
        return "long"
    return "standard"


def _word_problem_tier(difficulty: Difficulty, g: int) -> str:
    """Which set of word-problem shapes a grade/difficulty draws from.

    The scenes get richer as the reading gets easier: one-sentence
    stories, then sifting a list, then scoring rules and prices, then
    sale offers and cheapest-option comparisons. Read off the level
    ladder (curriculum.level), so neighbouring grades meet at one step.
    """
    lvl = curriculum.level(difficulty, Grade.K if g == 0 else Grade(str(g)))
    if lvl >= MAX_LEVEL:
        return "deals"
    if lvl >= 6:
        return "prices"
    if lvl >= 5:
        return "list_plus"
    # Kindergarten never gets a list — the reading alone would be the
    # whole task.
    if lvl >= 4:
        return "list"
    # Equal groups and sharing wait for grade 1 medium: kindergarten
    # stories only add and take away.
    return "simple_wide" if lvl >= 3 else "simple"


def _pick_factory(math_type: MathType, difficulty: Difficulty, grade: Grade) -> Factory:
    """Select the right factory for this (math_type, difficulty, grade).

    Everything is chosen by the level (curriculum.level: 2 × grade +
    difficulty, 0-12), so grade N hard and grade N+1 easy always match.

    - Addition, subtraction, multiplication, division: number sizes from
      the `_ADD_BANDS` / `_MUL_BANDS` / `_DIV_BANDS` tables. Decimals
      join + and − at level 11, decimal × whole at 12. Subtraction below
      zero is a grade 4-5 *hard* extra. Division: remainder-only at
      level 7, written-out remainders (176 R 2) from 8, fraction and
      decimal answers at 12.
    - Algebra: two-step equations (ax + b = c) from level 10.
    - Fractions: pictures → building → wholes → decimals → advanced →
      mastery (fraction_questions.tier_for).
    - Order of operations: two-term problems below level 7, then
      − and ÷; parentheses and three terms from 10; (a + b) × c − d ÷ e
      from 11.
    - Decimals: tenths below 8; hundredths, comparing and ×10 from 8;
      × and ÷ by 10/100 and decimal × whole at 10; decimal × decimal and
      decimal ÷ whole from 11.
    - Word problems, comparison, money & time, percentages, measurement
      and geometry pick a tier of question shapes from the level.
    """
    g = curriculum.grade_index(grade)
    lvl = curriculum.level(difficulty, grade)

    if math_type == MathType.addition:
        return _addition_at(lvl)

    if math_type == MathType.subtraction:
        return _subtraction_at(lvl, negatives=difficulty == Difficulty.hard and g >= 4)

    if math_type == MathType.multiplication:
        return _multiplication_at(lvl)

    if math_type == MathType.division:
        return _division_at(lvl)

    if math_type == MathType.algebra:
        return _make_algebra_hard if lvl >= 10 else _make_algebra

    if math_type == MathType.fractions:
        return fraction_questions.tier_factory(fraction_questions.tier_for(lvl))

    if math_type == MathType.order_of_operations:
        if lvl >= 11:
            return _make_ooo_fluent
        if lvl >= 10:
            return _make_ooo_advanced
        if lvl >= 7:
            return _make_ooo_intermediate
        return _make_ooo_basic

    if math_type == MathType.word_problems:
        return word_problems.tier_factory(
            _word_problem_tier(difficulty, g), scale=_reading_scale(difficulty, g)
        )

    if math_type == MathType.comparison:
        tier = _comparison_tier(difficulty, g)
        return rotating(_COMPARISON_TIERS[tier], tier)

    if math_type == MathType.money_time:
        return money_time.tier_factory(money_time.tier_for(lvl))

    if math_type == MathType.decimals:
        if lvl >= 11:
            return rotating(_DECIMAL_SHAPES_FLUENT, "fluent")
        if lvl >= 10:
            return rotating(_DECIMAL_SHAPES_OPS, "ops")
        if lvl >= 8:
            return _make_decimals_advanced
        return _make_decimals_basic

    if math_type == MathType.percentages:
        return percentages.tier_factory(percentages.tier_for(lvl))

    if math_type == MathType.measurement:
        return measurement.tier_factory(measurement.tier_for(lvl))

    raise ValueError(f"no factory for {math_type}")


def _number_range(math_type: MathType, difficulty: Difficulty, grade: Grade) -> tuple[int, int]:
    """The (lo, hi) a factory is called with.

    Algebra and order of operations size their numbers from it, so they
    get the level ladder's range. The band-driven topics ignore it, and
    the tiered ones (fractions, word problems, …) get the gentler
    `_SCENE_RANGES` — their scenes were tuned against numbers that size,
    and their difficulty comes from the tier instead.
    """
    if math_type in (MathType.algebra, MathType.order_of_operations):
        lo, hi = _level_band(_LEVEL_RANGES, curriculum.level(difficulty, grade))
        if math_type == MathType.order_of_operations:
            hi = min(hi, _OOO_MAX_HI)
        return lo, hi
    return _difficulty_range(difficulty, grade)


def _generate_geometry(difficulty: Difficulty, grade: Grade, rng: random.Random):
    # Geometry draws from a curated, level-aware pool. Each tier has
    # well over 10 entries, so sampling without replacement always
    # yields 10 unique questions. Pool entries are 3-tuples (text-only)
    # or 4-tuples (with a figure to draw).
    pool = _geometry_pool(difficulty, grade)
    # The generated visual items (symmetry, angles, labelled rectangles)
    # are a handful against a static pool of ~80-90, so they get a
    # guaranteed 2-3 seats per quiz instead of a raffle ticket.
    visuals = _visual_items(difficulty, grade, rng)
    if visuals:
        take = min(len(visuals), rng.randint(2, 3))
        # A labelled-rectangle question is the point of the top tier, so
        # when the tier offers one, one of the seats is reserved for it.
        rects = [v for v in visuals if v[3].startswith("rect:")]
        chosen = [rng.choice(rects)] if rects else []
        rest = [v for v in visuals if v not in chosen]
        chosen += rng.sample(rest, k=take - len(chosen))
        picks = chosen + rng.sample(pool, k=10 - take)
        rng.shuffle(picks)
    else:
        picks = rng.sample(pool, k=10)
    questions: list[QuestionInternal] = []
    for i, item in enumerate(picks):
        text, ans, expl = item[0], item[1], item[2]
        figure = item[3] if len(item) > 3 else None
        questions.append(
            QuestionInternal(
                id=i,
                question=text,
                correctAnswer=ans,
                explanation=expl,
                figure=figure,
                topic=MathType.geometry,
            )
        )
    return questions


def _generate_typed(math_type: MathType, difficulty: Difficulty, grade: Grade, rng: random.Random):
    lo, hi = _number_range(math_type, difficulty, grade)
    factory = _pick_factory(math_type, difficulty, grade)
    questions: list[QuestionInternal] = []
    seen: set[tuple] = set()
    for i in range(10):
        signature, text, answer, explanation, figure = _unpack(factory(rng, lo, hi))
        attempts = 1
        while signature in seen and attempts < _MAX_ATTEMPTS:
            signature, text, answer, explanation, figure = _unpack(factory(rng, lo, hi))
            attempts += 1
        seen.add(signature)
        questions.append(
            QuestionInternal(
                id=i,
                question=text,
                correctAnswer=answer,
                explanation=explanation,
                figure=figure,
                topic=math_type,
            )
        )
    return questions


def _mixed_seats(grade: Grade, rng: random.Random) -> list[MathType]:
    """The topic of each of a mixed quiz's ten questions, in quiz order.

    The grade's focus topics get their fixed seats (curriculum.GRADE_FOCUS);
    the rest go to its review topics, each at most once while there are
    enough of them. Drawn evenly from everything unlocked, as this used
    to be, a 5th grader saw plain addition as often as fractions.
    """
    plan = curriculum.grade_focus(grade)
    seats = [t for t, n in plan.focus.items() for _ in range(n)]
    review = list(plan.review)
    while len(seats) < curriculum.MIXED_SEATS:
        take = min(len(review), curriculum.MIXED_SEATS - len(seats))
        seats += rng.sample(review, k=take)
    rng.shuffle(seats)
    return seats


def _generate_mixed(difficulty: Difficulty, grade: Grade, rng: random.Random):
    """Ten questions whose topics follow the grade's focus chart.

    Each topic gets one factory for the whole quiz, so a topic with two
    or three seats deals different shapes (a pie, a decimal, a mixed
    number…) rather than three draws that land on the same one.

    Signatures already carry a per-type prefix, so a single `seen` set
    dedupes across types; question text is tracked too as a safety net
    (geometry items live outside the signature system).
    """
    seats = _mixed_seats(grade, rng)
    factories = {
        t: _pick_factory(t, difficulty, grade) for t in set(seats) if t != MathType.geometry
    }
    questions: list[QuestionInternal] = []
    seen_sig: set[tuple] = set()
    seen_text: set[str] = set()
    for i, math_type in enumerate(seats):
        figure = None
        for _ in range(_MAX_ATTEMPTS):
            if math_type == MathType.geometry:
                # The generated visual items are a handful against a
                # static pool of ~80, so give them a fixed share here or
                # a mixed quiz would almost never show one.
                visuals = _visual_items(difficulty, grade, rng)
                if visuals and rng.random() < 0.35:
                    item = rng.choice(visuals)
                else:
                    item = rng.choice(_geometry_pool(difficulty, grade))
                text, answer, explanation = item[0], item[1], item[2]
                figure = item[3] if len(item) > 3 else None
                signature = ("geo", text)
            else:
                lo, hi = _number_range(math_type, difficulty, grade)
                signature, text, answer, explanation, figure = _unpack(
                    factories[math_type](rng, lo, hi)
                )
            # Dedup by text so a mixed quiz never repeats wording (a
            # visual "how many sides…" appears at most once).
            if signature not in seen_sig and text not in seen_text:
                break
        seen_sig.add(signature)
        seen_text.add(text)
        questions.append(
            QuestionInternal(
                id=i,
                question=text,
                correctAnswer=answer,
                explanation=explanation,
                figure=figure,
                topic=math_type,
            )
        )
    return questions


# ---------- multiple-choice distractors ----------
#
# The wrong answers live in distractors.py: which ones are worth offering
# turned out to be a topic of its own (domains that must not mix, and
# mistakes a kid would actually make), and it was drowning this file.


def _attach_options(questions: list[QuestionInternal], rng: random.Random) -> None:
    all_answers = [q.correctAnswer for q in questions]
    for i, q in enumerate(questions):
        siblings = all_answers[:i] + all_answers[i + 1:]
        q.options = build_options(q.correctAnswer, q.question, siblings, rng)


def generate_questions(
    math_type: MathType,
    difficulty: Difficulty,
    grade: Grade,
    *,
    answer_mode: AnswerMode = AnswerMode.typing,
    rng: random.Random | None = None,
) -> list[QuestionInternal]:
    rng = rng or random.Random()

    if math_type == MathType.mixed:
        questions = _generate_mixed(difficulty, grade, rng)
    elif math_type == MathType.geometry:
        questions = _generate_geometry(difficulty, grade, rng)
    else:
        questions = _generate_typed(math_type, difficulty, grade, rng)

    if answer_mode == AnswerMode.multiple_choice:
        _attach_options(questions, rng)

    return questions


# Units a question asks for out loud ("How many dollars…"), which a kid
# may well type back. The answer is right; only the clothes are wrong.
_ANSWER_UNITS = ("dollars", "dollar", "cents", "cent", "minutes", "minute")


_CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _normalize_clock(s: str) -> str | None:
    """"05:20" and "5:20" are the same time to everyone but a string
    comparison, and a kid reading a digital clock may type either."""
    m = _CLOCK_RE.match(s.strip())
    if not m:
        return None
    hour, minute = int(m.group(1)), m.group(2)
    return f"{hour}:{minute}" if 0 <= hour <= 24 else None


def _parse_number(s: str) -> float | None:
    cleaned = s.strip().lower().lstrip("$").replace(",", "").strip()
    for unit in _ANSWER_UNITS:
        if cleaned.endswith(unit):
            cleaned = cleaned[: -len(unit)].strip()
            break
    try:
        return float(cleaned)
    except ValueError:
        return None


def time_limit_seconds(
    text: str,
    math_type: MathType | None = None,
    difficulty: Difficulty | None = None,
    grade: Grade | None = None,
) -> int:
    """How long a question is worth, in seconds.

    A one-line sum and a five-line shopping list can't share a clock, and
    neither can "3 + 4 = ?" and "is 8! bigger than 4^4?". The numbers all
    live in `question_times.py` — that's the file to edit — and this is
    the thin wrapper the rest of the app calls.

    The level arguments are optional so a caller that only has the text
    still gets a sensible budget from the default base.
    """
    return question_seconds(text, math_type, difficulty, grade)


def answer_kind(correct: int | str) -> AnswerKind:
    """Which on-screen keyboard fits this answer (PROJECT_PLAN §3.2).

    Derived from the answer itself rather than the topic, because a topic
    isn't uniform: division yields whole numbers, decimals *and*
    fractions. Negative answers stay `text` on purpose — phone numeric
    keypads have no minus key, so a kid typing "-3" needs the full one.
    Fractions ("3/5"), comparisons ("<") and words ("hexagon") are text
    for the same reason.

    This is a keyboard hint, not a spoiler: it says an answer is some
    non-negative number, which the question already implies.
    """
    if isinstance(correct, bool):  # bool is an int subclass — never an answer
        return AnswerKind.text
    if isinstance(correct, int):
        return AnswerKind.integer if correct >= 0 else AnswerKind.text
    if isinstance(correct, float):
        return AnswerKind.decimal if correct >= 0 else AnswerKind.text

    text = str(correct).strip()
    if re.fullmatch(r"\d+", text):
        return AnswerKind.integer
    if re.fullmatch(r"\d*\.\d+", text):
        return AnswerKind.decimal
    return AnswerKind.text


_REMAINDER_ANSWER_RE = re.compile(r"^(\d+) R (\d+)$")
_REMAINDER_TYPED_RE = re.compile(
    r"^(\d+)\s*(?:r|rem|remainder)\.?\s*(\d+)$", re.IGNORECASE
)
_MIXED_ANSWER_RE = re.compile(r"^\d+ \d+/\d+$")
_MIXED_TYPED_RE = re.compile(r"^(\d+)\s*(?:\s|\band\b|\+|-)\s*(\d+)\s*/\s*(\d+)$", re.IGNORECASE)


def _normalize_remainder(s: str) -> str | None:
    """"2 R 3", "2r3", "2 rem 3" and "2 remainder 3" are one answer."""
    m = _REMAINDER_TYPED_RE.match(s.strip())
    return f"{int(m.group(1))} R {int(m.group(2))}" if m else None


def _normalize_mixed(s: str) -> str | None:
    """"2 3/5", "2  3/5" and "2 and 3/5" are one answer. The parts are
    kept as typed, so "2 6/10" still isn't simplest form."""
    m = _MIXED_TYPED_RE.match(s.strip())
    return f"{int(m.group(1))} {int(m.group(2))}/{int(m.group(3))}" if m else None


def grade_answer(correct: int | str, user: str | None) -> bool:
    """Compare a typed answer against the key.

    Numeric answers are compared as numbers so "0.50", ".5", and "0.5"
    all match a correct answer of 0.5 (kids type trailing zeros).
    Fraction answers ("3/4") stay exact string matches on purpose — the
    question asks for simplest form, so "6/8" must NOT be accepted.
    Word answers ("even", "triangle") are case-insensitive. Remainders
    ("2 R 3") and mixed numbers ("2 3/5") forgive spacing and the words
    kids use for them ("2 remainder 3", "2 and 3/5"), never the maths.
    """
    if user is None:
        return False
    user_stripped = user.strip()
    if user_stripped == "":
        return False
    if isinstance(correct, int):
        try:
            return int(user_stripped) == correct
        except ValueError:
            user_num = _parse_number(user_stripped)
            return user_num is not None and user_num == correct
    correct_stripped = str(correct).strip()
    if user_stripped.lower() == correct_stripped.lower():
        return True
    if _REMAINDER_ANSWER_RE.match(correct_stripped):
        return _normalize_remainder(user_stripped) == correct_stripped
    if _MIXED_ANSWER_RE.match(correct_stripped):
        return _normalize_mixed(user_stripped) == correct_stripped
    correct_clock = _normalize_clock(correct_stripped)
    if correct_clock is not None:
        return _normalize_clock(user_stripped) == correct_clock
    if "/" not in correct_stripped:
        correct_num = _parse_number(correct_stripped)
        user_num = _parse_number(user_stripped)
        if correct_num is not None and user_num is not None:
            return correct_num == user_num
    return False
