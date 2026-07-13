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
from math import gcd
from typing import Callable

from .models import Difficulty, Grade, MathType, QuestionInternal

_MAX_ATTEMPTS = 200


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

    if tier == 0:
        return _GEOMETRY_EASY
    if tier == 1:
        return _GEOMETRY_EASY + _GEOMETRY_MEDIUM
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

    return {
        MathType.addition: _make_addition,
        MathType.multiplication: _make_multiplication,
    }[math_type]


def generate_questions(
    math_type: MathType,
    difficulty: Difficulty,
    grade: Grade,
    *,
    rng: random.Random | None = None,
) -> list[QuestionInternal]:
    rng = rng or random.Random()
    lo, hi = _difficulty_range(difficulty, grade)

    # Geometry draws from a curated, level-aware pool. Each tier has
    # well over 10 entries, so sampling without replacement always
    # yields 10 unique questions.
    if math_type == MathType.geometry:
        pool = _geometry_pool(difficulty, grade)
        picks = rng.sample(pool, k=10)
        return [
            QuestionInternal(id=i, question=text, correctAnswer=ans, explanation=expl)
            for i, (text, ans, expl) in enumerate(picks)
        ]

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
            QuestionInternal(
                id=i, question=text, correctAnswer=answer, explanation=explanation
            )
        )

    return questions


def grade_answer(correct: int | str, user: str | None) -> bool:
    if user is None:
        return False
    user_stripped = user.strip()
    if user_stripped == "":
        return False
    if isinstance(correct, int):
        try:
            return int(user_stripped) == correct
        except ValueError:
            return False
    return user_stripped.lower() == str(correct).strip().lower()
