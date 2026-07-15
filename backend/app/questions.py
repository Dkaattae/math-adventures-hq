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
from math import gcd
from typing import Callable

from .models import AnswerMode, Difficulty, Grade, MathType, QuestionInternal

_MAX_ATTEMPTS = 200

# Every math type that a "mixed" quiz can draw from (mixed itself excluded).
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


def _difficulty_range(difficulty: Difficulty, grade: Grade) -> tuple[int, int]:
    g = 0 if grade == Grade.K else int(grade.value)
    base = g * 3
    if difficulty == Difficulty.easy:
        return 1, base + 5
    if difficulty == Difficulty.medium:
        return 2, base + 10
    return 5, base + 20


# ---------- per-type factories ----------
#
# Each factory returns (signature, question_text, correct_answer, explanation).
# `id` is assigned later by the dedup loop.

Factory = Callable[[random.Random, int, int], tuple[tuple, str, int | str, str]]


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


def _make_subtraction(rng: random.Random, lo: int, hi: int):
    return _sub_positive(rng, lo, hi)


def _make_subtraction_with_negatives(rng: random.Random, lo: int, hi: int):
    # ~50/50 mix so a hard quiz has both positive and negative answers.
    return rng.choice([_sub_positive, _sub_negative])(rng, lo, hi)


def _make_multiplication(rng: random.Random, lo: int, hi: int):
    m1 = rng.randint(1, max(2, hi // 2))
    m2 = rng.randint(1, max(2, hi // 3))
    lo_, hi_ = (m1, m2) if m1 <= m2 else (m2, m1)
    return (
        ("mul", lo_, hi_),
        f"{m1} × {m2} = ?",
        m1 * m2,
        f"{m1} × {m2} = {m1 * m2}. Think of {m1} groups of {m2}! 🎯",
    )


# ---------- division: integer, remainder, fraction, decimal ----------


def _div_integer(rng: random.Random, lo: int, hi: int):
    divisor = rng.randint(2, max(3, hi // 3))
    answer = rng.randint(1, max(2, hi // 2))
    dividend = divisor * answer
    return (
        ("div", dividend, divisor),
        f"{dividend} ÷ {divisor} = ?",
        answer,
        f"{dividend} ÷ {divisor} = {answer}. "
        f"{dividend} split into {divisor} equal groups gives {answer}! 🍰",
    )


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


def _make_division(rng: random.Random, lo: int, hi: int):
    return _div_integer(rng, lo, hi)


def _make_division_with_remainder(rng: random.Random, lo: int, hi: int):
    return rng.choice([_div_integer, _div_remainder])(rng, lo, hi)


def _make_division_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice([_div_integer, _div_remainder, _div_fraction, _div_decimal])(rng, lo, hi)


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


# ---------- fractions: whole-number share, like/unlike denominators, product ----------


def _simplify_fraction(num: int, den: int) -> str:
    """Format num/den in lowest terms; whole-number results drop the denominator."""
    if num == 0:
        return "0"
    g = gcd(num, den)
    num, den = num // g, den // g
    return str(num) if den == 1 else f"{num}/{den}"


def _frac_of_whole(rng: random.Random, lo: int, hi: int):
    den = rng.choice([2, 3, 4, 5, 10])
    multiplier = rng.randint(1, max(2, hi // den))
    whole = den * multiplier
    num = rng.randint(1, den - 1)
    answer = num * whole // den
    return (
        ("fracof", num, den, whole),
        f"What is {num}/{den} of {whole}?",
        answer,
        f"{whole} ÷ {den} = {whole // den}, then × {num} = {answer}. 🍕",
    )


def _frac_same_denom(rng: random.Random, lo: int, hi: int):
    den = rng.randint(2, max(3, hi // 2))
    a = rng.randint(1, den - 1)
    b = rng.randint(1, den - 1)
    op = rng.choice(["+", "-"])
    if op == "-" and b > a:
        a, b = b, a
    num = a + b if op == "+" else a - b
    result = _simplify_fraction(num, den)
    hint = f"{a}/{den} {op} {b}/{den} = {num}/{den}" + (f" = {result}" if result != f"{num}/{den}" else "") + "."
    return (
        ("fracsame", op, den, a, b),
        f"{a}/{den} {op} {b}/{den} = ? (simplest form)",
        result,
        hint + " 🍕",
    )


def _frac_unlike_denom(rng: random.Random, lo: int, hi: int):
    d1 = rng.randint(2, max(3, hi // 3))
    d2 = rng.randint(2, max(3, hi // 3))
    if d2 == d1:
        d2 += 1
    n1 = rng.randint(1, d1 - 1)
    n2 = rng.randint(1, d2 - 1)
    lcd = d1 * d2 // gcd(d1, d2)
    num = n1 * (lcd // d1) + n2 * (lcd // d2)
    result = _simplify_fraction(num, lcd)
    return (
        ("fracunlike", d1, n1, d2, n2),
        f"{n1}/{d1} + {n2}/{d2} = ? (simplest form)",
        result,
        f"LCD of {d1} and {d2} is {lcd}: {n1}/{d1} = {n1 * (lcd // d1)}/{lcd}, "
        f"{n2}/{d2} = {n2 * (lcd // d2)}/{lcd}. Sum = {num}/{lcd}"
        + (f" = {result}" if result != f"{num}/{lcd}" else "")
        + ". 🍕",
    )


def _frac_multiply(rng: random.Random, lo: int, hi: int):
    n1 = rng.randint(1, max(2, hi // 3))
    d1 = rng.randint(n1 + 1, max(n1 + 2, hi // 2 + 1))
    n2 = rng.randint(1, max(2, hi // 3))
    d2 = rng.randint(n2 + 1, max(n2 + 2, hi // 2 + 1))
    num, den = n1 * n2, d1 * d2
    result = _simplify_fraction(num, den)
    return (
        ("fracmul", n1, d1, n2, d2),
        f"{n1}/{d1} × {n2}/{d2} = ? (simplest form)",
        result,
        f"Multiply straight across: ({n1}×{n2})/({d1}×{d2}) = {num}/{den}"
        + (f" = {result}" if result != f"{num}/{den}" else "")
        + ". 🍕",
    )


def _make_fractions_basic(rng: random.Random, lo: int, hi: int):
    return _frac_of_whole(rng, lo, hi)


def _make_fractions_intermediate(rng: random.Random, lo: int, hi: int):
    return rng.choice([_frac_of_whole, _frac_same_denom])(rng, lo, hi)


def _make_fractions_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice([_frac_same_denom, _frac_unlike_denom, _frac_multiply])(rng, lo, hi)


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


# ---------- word problems: arithmetic wrapped in short stories ----------
#
# The numbers (not the names/items) form the dedup signature, so a retry
# after a collision redraws the numbers rather than just the character.

_WP_NAMES = ["Maya", "Leo", "Ava", "Noah", "Zoe", "Sam", "Mia", "Eli", "Ruby", "Max"]
_WP_ITEMS = ["stickers", "marbles", "crayons", "apples", "cookies", "toy cars", "seashells", "balloons"]


def _wp_add(rng: random.Random, lo: int, hi: int):
    a, b = rng.randint(lo, hi), rng.randint(lo, hi)
    name, item = rng.choice(_WP_NAMES), rng.choice(_WP_ITEMS)
    lo_, hi_ = (a, b) if a <= b else (b, a)
    return (
        ("wp_add", lo_, hi_),
        f"{name} has {a} {item} and gets {b} more. How many {item} does {name} have now?",
        a + b,
        f"{a} + {b} = {a + b}. Count on {b} more from {a}! 📖",
    )


def _wp_sub(rng: random.Random, lo: int, hi: int):
    a = rng.randint(lo, hi)
    b = rng.randint(lo, min(a, hi))
    name, item = rng.choice(_WP_NAMES), rng.choice(_WP_ITEMS)
    return (
        ("wp_sub", a, b),
        f"{name} has {a} {item} and gives {b} to a friend. How many {item} does {name} have left?",
        a - b,
        f"{a} - {b} = {a - b}. Take away {b} from {a}! 📖",
    )


def _wp_mul(rng: random.Random, lo: int, hi: int):
    a = rng.randint(2, max(3, hi // 3))
    b = rng.randint(2, max(3, hi // 2))
    item = rng.choice(_WP_ITEMS)
    return (
        ("wp_mul", a, b),
        f"There are {a} bags with {b} {item} in each bag. How many {item} are there in all?",
        a * b,
        f"{a} bags × {b} each = {a * b}. That's {a} groups of {b}! 📖",
    )


def _wp_div(rng: random.Random, lo: int, hi: int):
    divisor = rng.randint(2, max(3, hi // 3))
    answer = rng.randint(2, max(3, hi // 2))
    dividend = divisor * answer
    name, item = rng.choice(_WP_NAMES), rng.choice(_WP_ITEMS)
    return (
        ("wp_div", dividend, divisor),
        f"{name} shares {dividend} {item} equally among {divisor} friends. "
        f"How many does each friend get?",
        answer,
        f"{dividend} ÷ {divisor} = {answer}. Everyone gets a fair share! 📖",
    )


def _make_word_problems_basic(rng: random.Random, lo: int, hi: int):
    return rng.choice([_wp_add, _wp_sub])(rng, lo, hi)


def _make_word_problems_intermediate(rng: random.Random, lo: int, hi: int):
    return rng.choice([_wp_add, _wp_sub, _wp_mul])(rng, lo, hi)


def _make_word_problems_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice([_wp_add, _wp_sub, _wp_mul, _wp_div])(rng, lo, hi)


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


def _make_comparison_basic(rng: random.Random, lo: int, hi: int):
    return rng.choice([_cmp_symbol, _even_odd, _sequence_next])(rng, lo, hi)


def _make_comparison_intermediate(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [_cmp_symbol, _even_odd, _sequence_next, _cmp_biggest, _place_value]
    )(rng, lo, hi)


def _make_comparison_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [_cmp_symbol, _sequence_next, _cmp_biggest, _place_value, _round_to_ten]
    )(rng, lo, hi)


# ---------- money & time ----------
#
# Money stays in whole cents so kids never have to type a decimal point.

_COINS = [("quarter", "quarters", 25), ("dime", "dimes", 10), ("nickel", "nickels", 5), ("penny", "pennies", 1)]


def _money_coins(rng: random.Random, lo: int, hi: int, *, coin_pool: slice = slice(1, 4)):
    # Two distinct coin types with small counts.
    pool = _COINS[coin_pool]
    (name1, plural1, val1), (name2, plural2, val2) = rng.sample(pool, 2)
    c1, c2 = rng.randint(1, 4), rng.randint(1, 4)
    total = c1 * val1 + c2 * val2
    w1 = name1 if c1 == 1 else plural1
    w2 = name2 if c2 == 1 else plural2
    return (
        ("coins", val1, c1, val2, c2),
        f"You have {c1} {w1} and {c2} {w2}. How many cents is that?",
        total,
        f"{c1} × {val1}¢ + {c2} × {val2}¢ = {total}¢! 💰",
    )


def _money_coins_easy(rng: random.Random, lo: int, hi: int):
    return _money_coins(rng, lo, hi, coin_pool=slice(1, 4))  # dimes/nickels/pennies


def _money_coins_full(rng: random.Random, lo: int, hi: int):
    return _money_coins(rng, lo, hi, coin_pool=slice(0, 4))  # quarters too


def _money_change(rng: random.Random, lo: int, hi: int):
    paid = rng.choice([25, 50, 100])
    price = rng.randint(1, paid - 1)
    return (
        ("change", price, paid),
        f"A sticker costs {price}¢ and you pay {paid}¢. How many cents of change do you get?",
        paid - price,
        f"{paid}¢ - {price}¢ = {paid - price}¢ change! 💰",
    )


def _time_hours_to_minutes(rng: random.Random, lo: int, hi: int):
    h = rng.randint(2, 9)
    return (
        ("h2m", h),
        f"How many minutes are in {h} hours?",
        h * 60,
        f"Each hour has 60 minutes: {h} × 60 = {h * 60}! ⏰",
    )


def _time_to_next_hour(rng: random.Random, lo: int, hi: int):
    h = rng.randint(1, 11)
    m = rng.choice([5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return (
        ("tonext", h, m),
        f"How many minutes is it from {h}:{m:02d} to {h + 1}:00?",
        60 - m,
        f"From {h}:{m:02d} up to {h + 1}:00 is 60 - {m} = {60 - m} minutes! ⏰",
    )


def _time_elapsed(rng: random.Random, lo: int, hi: int):
    h1 = rng.randint(1, 9)
    m1 = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    hours = rng.randint(1, 2)
    m2 = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    h2 = h1 + hours
    answer = hours * 60 + (m2 - m1)
    return (
        ("elapsed", h1, m1, h2, m2),
        f"How many minutes is it from {h1}:{m1:02d} to {h2}:{m2:02d}?",
        answer,
        f"From {h1}:{m1:02d} to {h2}:{m2:02d} is {answer} minutes. "
        f"Count the full hours first, then the extra minutes! ⏰",
    )


def _make_money_time_basic(rng: random.Random, lo: int, hi: int):
    return rng.choice([_money_coins_easy, _time_hours_to_minutes])(rng, lo, hi)


def _make_money_time_intermediate(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [_money_coins_easy, _money_change, _time_hours_to_minutes, _time_to_next_hour]
    )(rng, lo, hi)


def _make_money_time_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [_money_coins_full, _money_change, _time_to_next_hour, _time_elapsed]
    )(rng, lo, hi)


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


# ---------- percentages: percent of a number, always whole answers ----------

# (percent, required multiple) — n is drawn as a multiple so the answer is whole.
_PCT_BASIC = [(50, 2), (10, 10), (100, 1)]
_PCT_FULL = _PCT_BASIC + [(25, 4), (20, 5), (75, 4)]


def _pct_of(rng: random.Random, lo: int, hi: int, *, table: list[tuple[int, int]]):
    pct, multiple = rng.choice(table)
    n = multiple * rng.randint(1, max(10, hi))
    answer = pct * n // 100
    return (
        ("pct", pct, n),
        f"What is {pct}% of {n}?",
        answer,
        f"{pct}% means {pct} out of every 100: {pct}% of {n} = {answer}! 💯",
    )


def _make_percentages_basic(rng: random.Random, lo: int, hi: int):
    return _pct_of(rng, lo, hi, table=_PCT_BASIC)


def _make_percentages_advanced(rng: random.Random, lo: int, hi: int):
    return _pct_of(rng, lo, hi, table=_PCT_FULL)


# ---------- measurement conversions ----------

# (factor, small unit plural, big unit singular, big unit plural)
_CONVERSIONS_BASIC = [
    (100, "centimeters", "meter", "meters"),
    (10, "millimeters", "centimeter", "centimeters"),
    (60, "seconds", "minute", "minutes"),
    (12, "inches", "foot", "feet"),
]
_CONVERSIONS_FULL = _CONVERSIONS_BASIC + [
    (1000, "meters", "kilometer", "kilometers"),
    (1000, "grams", "kilogram", "kilograms"),
    (1000, "milliliters", "liter", "liters"),
    (3, "feet", "yard", "yards"),
]


def _meas_big_to_small(rng: random.Random, lo: int, hi: int, *, table: list):
    factor, small, big_one, big_many = rng.choice(table)
    k = rng.randint(2, 9)
    return (
        ("meas", factor, small, k),
        f"How many {small} are in {k} {big_many}?",
        k * factor,
        f"1 {big_one} = {factor} {small}, so {k} {big_many} = {k} × {factor} = {k * factor}! 📏",
    )


def _meas_small_to_big(rng: random.Random, lo: int, hi: int):
    factor, small, big_one, big_many = rng.choice(_CONVERSIONS_FULL)
    k = rng.randint(2, 9)
    total = k * factor
    return (
        ("measrev", factor, small, k),
        f"{total} {small} is how many {big_many}?",
        k,
        f"Divide by {factor}: {total} ÷ {factor} = {k} {big_many}! 📏",
    )


def _meas_mixed(rng: random.Random, lo: int, hi: int):
    factor, small, big_one, big_many = rng.choice(
        [c for c in _CONVERSIONS_FULL if c[0] in (100, 60, 12)]
    )
    k = rng.randint(1, 5)
    extra = rng.randint(1, factor - 1)
    big_word = big_one if k == 1 else big_many
    return (
        ("measmix", factor, small, k, extra),
        f"How many {small} is {k} {big_word} and {extra} {small}?",
        k * factor + extra,
        f"{k} × {factor} = {k * factor}, plus {extra} more = {k * factor + extra}! 📏",
    )


def _make_measurement_basic(rng: random.Random, lo: int, hi: int):
    return _meas_big_to_small(rng, lo, hi, table=_CONVERSIONS_BASIC)


def _make_measurement_intermediate(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [
            lambda r, a, b: _meas_big_to_small(r, a, b, table=_CONVERSIONS_FULL),
            _meas_small_to_big,
        ]
    )(rng, lo, hi)


def _make_measurement_advanced(rng: random.Random, lo: int, hi: int):
    return rng.choice(
        [
            lambda r, a, b: _meas_big_to_small(r, a, b, table=_CONVERSIONS_FULL),
            _meas_small_to_big,
            _meas_mixed,
        ]
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


def _geometry_pool(difficulty: Difficulty, grade: Grade) -> list[GeometryItem]:
    """Pick which tiers are in play for this (difficulty, grade) combo.

    Grade is the primary driver (you don't ask a Kindergartener about
    volume). Difficulty shifts the tier up or down by one step.
    """
    g = 0 if grade == Grade.K else int(grade.value)
    if g <= 1:
        base_tier = 0  # EASY
    elif g <= 3:
        base_tier = 1  # EASY + MEDIUM
    else:
        base_tier = 2  # MEDIUM + HARD

    if difficulty == Difficulty.easy and base_tier > 0:
        tier = base_tier - 1
    elif difficulty == Difficulty.hard and base_tier < 2:
        tier = base_tier + 1
    else:
        tier = base_tier

    # Visual shape questions ride along with the EASY tier (they're
    # identification-level). Entries may be 3-tuples (text-only) or
    # 4-tuples (with a figure); _generate_geometry normalizes both.
    if tier == 0:
        return _GEOMETRY_EASY + _GEOMETRY_VISUAL
    if tier == 1:
        return _GEOMETRY_EASY + _GEOMETRY_VISUAL + _GEOMETRY_MEDIUM
    return _GEOMETRY_MEDIUM + _GEOMETRY_HARD


def _pick_factory(math_type: MathType, difficulty: Difficulty, grade: Grade) -> Factory:
    """Select the right factory for this (math_type, difficulty, grade).

    - Subtraction: negative-capable variant kicks in at grade 4+ hard.
    - Division: remainder questions appear from grade 3 onward at
      medium/hard; fractions and decimals only at grade 5 hard.
    - Algebra: two-step equations (ax + b = c) kick in at grade 4+ hard.
    - Fractions: "fraction of a whole" only below grade 2/easy; unlike
      denominators and multiplication unlock at grade 4+ hard.
    - Order of operations: two-term problems only below grade 3/medium;
      parentheses and three-term expressions unlock at grade 4+ hard.
    - Word problems: add/sub stories at first; multiplication joins at
      grade 2+ medium, division at grade 3+ hard.
    - Comparison: symbol/even-odd/sequences at first; place value at
      grade 2+ medium; rounding at grade 3+ hard.
    - Money & time: coin counting and hours→minutes at first; change and
      to-the-next-hour at grade 2+ medium; quarters and cross-hour
      elapsed time at grade 3+ hard.
    - Decimals: tenths add/sub at first; hundredths, comparison, and
      ×10 at grade 4+ hard.
    - Percentages: 10/50/100% at first; 20/25/75% at grade 5 hard.
    - Measurement: big→small conversions at first; reverse direction at
      grade 3+ medium; mixed units at grade 4+ hard.
    - Other types use a single factory regardless of difficulty.
    """
    g = 0 if grade == Grade.K else int(grade.value)

    if math_type == MathType.subtraction:
        if difficulty == Difficulty.hard and g >= 4:
            return _make_subtraction_with_negatives
        return _make_subtraction

    if math_type == MathType.division:
        if difficulty == Difficulty.hard and g >= 5:
            return _make_division_advanced
        if g >= 3 and difficulty != Difficulty.easy:
            return _make_division_with_remainder
        return _make_division

    if math_type == MathType.algebra:
        if difficulty == Difficulty.hard and g >= 4:
            return _make_algebra_hard
        return _make_algebra

    if math_type == MathType.fractions:
        if difficulty == Difficulty.hard and g >= 4:
            return _make_fractions_advanced
        if g >= 2 and difficulty != Difficulty.easy:
            return _make_fractions_intermediate
        return _make_fractions_basic

    if math_type == MathType.order_of_operations:
        if difficulty == Difficulty.hard and g >= 4:
            return _make_ooo_advanced
        if g >= 3 and difficulty != Difficulty.easy:
            return _make_ooo_intermediate
        return _make_ooo_basic

    if math_type == MathType.word_problems:
        if difficulty == Difficulty.hard and g >= 3:
            return _make_word_problems_advanced
        if g >= 2 and difficulty != Difficulty.easy:
            return _make_word_problems_intermediate
        return _make_word_problems_basic

    if math_type == MathType.comparison:
        if difficulty == Difficulty.hard and g >= 3:
            return _make_comparison_advanced
        if g >= 2 and difficulty != Difficulty.easy:
            return _make_comparison_intermediate
        return _make_comparison_basic

    if math_type == MathType.money_time:
        if difficulty == Difficulty.hard and g >= 3:
            return _make_money_time_advanced
        if g >= 2 and difficulty != Difficulty.easy:
            return _make_money_time_intermediate
        return _make_money_time_basic

    if math_type == MathType.decimals:
        if difficulty == Difficulty.hard and g >= 4:
            return _make_decimals_advanced
        return _make_decimals_basic

    if math_type == MathType.percentages:
        if difficulty == Difficulty.hard and g >= 5:
            return _make_percentages_advanced
        return _make_percentages_basic

    if math_type == MathType.measurement:
        if difficulty == Difficulty.hard and g >= 4:
            return _make_measurement_advanced
        if g >= 3 and difficulty != Difficulty.easy:
            return _make_measurement_intermediate
        return _make_measurement_basic

    return {
        MathType.addition: _make_addition,
        MathType.multiplication: _make_multiplication,
    }[math_type]


def _generate_geometry(difficulty: Difficulty, grade: Grade, rng: random.Random):
    # Geometry draws from a curated, level-aware pool. Each tier has
    # well over 10 entries, so sampling without replacement always
    # yields 10 unique questions. Pool entries are 3-tuples (text-only)
    # or 4-tuples (with a figure to draw).
    pool = _geometry_pool(difficulty, grade)
    picks = rng.sample(pool, k=10)
    questions: list[QuestionInternal] = []
    for i, item in enumerate(picks):
        text, ans, expl = item[0], item[1], item[2]
        figure = item[3] if len(item) > 3 else None
        questions.append(
            QuestionInternal(
                id=i, question=text, correctAnswer=ans, explanation=expl, figure=figure
            )
        )
    return questions


def _generate_typed(math_type: MathType, difficulty: Difficulty, grade: Grade, rng: random.Random):
    lo, hi = _difficulty_range(difficulty, grade)
    factory = _pick_factory(math_type, difficulty, grade)
    questions: list[QuestionInternal] = []
    seen: set[tuple] = set()
    for i in range(10):
        signature, text, answer, explanation = factory(rng, lo, hi)
        attempts = 1
        while signature in seen and attempts < _MAX_ATTEMPTS:
            signature, text, answer, explanation = factory(rng, lo, hi)
            attempts += 1
        seen.add(signature)
        questions.append(
            QuestionInternal(id=i, question=text, correctAnswer=answer, explanation=explanation)
        )
    return questions


def _generate_mixed(difficulty: Difficulty, grade: Grade, rng: random.Random):
    """Sample each of the 10 questions from a randomly chosen topic.

    Signatures already carry a per-type prefix, so a single `seen` set
    dedupes across types; question text is tracked too as a safety net
    (geometry items live outside the signature system).
    """
    lo, hi = _difficulty_range(difficulty, grade)
    # Only mix in topics that are grade-appropriate (a Kindergartener's
    # "mixed" quiz shouldn't surprise them with long division).
    pool_types = [t for t in types_available(grade) if t != MathType.mixed]
    questions: list[QuestionInternal] = []
    seen_sig: set[tuple] = set()
    seen_text: set[str] = set()
    for i in range(10):
        figure = None
        for _ in range(_MAX_ATTEMPTS):
            math_type = rng.choice(pool_types)
            if math_type == MathType.geometry:
                item = rng.choice(_geometry_pool(difficulty, grade))
                text, answer, explanation = item[0], item[1], item[2]
                figure = item[3] if len(item) > 3 else None
                signature = ("geo", text)
            else:
                factory = _pick_factory(math_type, difficulty, grade)
                signature, text, answer, explanation = factory(rng, lo, hi)
                figure = None
            # Dedup by text so a mixed quiz never repeats wording (a
            # visual "how many sides…" appears at most once).
            if signature not in seen_sig and text not in seen_text:
                break
        seen_sig.add(signature)
        seen_text.add(text)
        questions.append(
            QuestionInternal(
                id=i, question=text, correctAnswer=answer, explanation=explanation, figure=figure
            )
        )
    return questions


# ---------- multiple-choice distractors ----------

_FRACTION_RE = re.compile(r"^-?\d+/\d+$")
_DECIMAL_RE = re.compile(r"^-?\d+\.\d+$")


def _int_distractors(n: int, rng: random.Random) -> list[int]:
    """Plausible off-by-a-little wrong integers (never negative if n >= 0)."""
    deltas = [1, -1, 2, -2, 3, -3, 5, -5, 10, -10]
    rng.shuffle(deltas)
    out: list[int] = []
    for d in deltas:
        v = n + d
        if v == n or (n >= 0 and v < 0) or v in out:
            continue
        out.append(v)
    return out


def _decimal_distractors(s: str, rng: random.Random) -> list[str]:
    places = len(s.split(".")[1])
    step = 10 ** (-places)
    val = float(s)
    out: list[str] = []
    for mult in (1, -1, 2, -2, 5, -5):
        v = round(val + mult * step, places)
        if v <= 0 or abs(v - val) < step / 2:
            continue
        formatted = f"{v:.{places}f}"
        if formatted != s and formatted not in out:
            out.append(formatted)
    return out


def _fraction_distractors(s: str, rng: random.Random) -> list[str]:
    num, den = (int(x) for x in s.split("/"))
    correct_val = num / den
    out: list[str] = []
    for dn, dd in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]:
        n2, d2 = num + dn, den + dd
        if n2 < 1 or d2 < 2:
            continue
        cand = f"{n2}/{d2}"
        if cand != s and abs(n2 / d2 - correct_val) > 1e-9 and cand not in out:
            out.append(cand)
    return out


def _build_options(correct, sibling_answers, rng: random.Random) -> list[str] | None:
    """Return shuffled options (correct + 1-3 distractors), or None if we
    couldn't produce even one plausible distractor.

    Distractors come first from type-appropriate near-misses, then from
    the other correct answers in the same quiz (same topic/difficulty →
    naturally plausible), which also covers categorical answers like
    "even"/"odd", "<"/">"/"=", or shape names without hardcoded pools.
    """
    correct_str = str(correct)
    distractors: list[str] = []

    def add(value: str):
        if value != correct_str and value not in distractors and len(distractors) < 3:
            distractors.append(value)

    if isinstance(correct, int):
        for v in _int_distractors(correct, rng):
            add(str(v))
    elif _DECIMAL_RE.match(correct_str):
        for v in _decimal_distractors(correct_str, rng):
            add(v)
    elif _FRACTION_RE.match(correct_str):
        for v in _fraction_distractors(correct_str, rng):
            add(v)

    # Supplement with sibling answers (shuffled) to reach 3 where possible.
    siblings = [str(s) for s in sibling_answers]
    rng.shuffle(siblings)
    for s in siblings:
        add(s)

    if not distractors:
        return None
    options = distractors + [correct_str]
    rng.shuffle(options)
    return options


def _attach_options(questions: list[QuestionInternal], rng: random.Random) -> None:
    all_answers = [q.correctAnswer for q in questions]
    for i, q in enumerate(questions):
        siblings = all_answers[:i] + all_answers[i + 1:]
        q.options = _build_options(q.correctAnswer, siblings, rng)


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


def _parse_number(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def grade_answer(correct: int | str, user: str | None) -> bool:
    """Compare a typed answer against the key.

    Numeric answers are compared as numbers so "0.50", ".5", and "0.5"
    all match a correct answer of 0.5 (kids type trailing zeros).
    Fraction answers ("3/4") stay exact string matches on purpose — the
    question asks for simplest form, so "6/8" must NOT be accepted.
    Word answers ("even", "triangle") are case-insensitive.
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
    if "/" not in correct_stripped:
        correct_num = _parse_number(correct_stripped)
        user_num = _parse_number(user_stripped)
        if correct_num is not None and user_num is not None:
            return correct_num == user_num
    return False
