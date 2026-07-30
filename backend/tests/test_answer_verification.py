"""Every printed question is solved again, independently, and the two
answers must agree.

PROJECT_PLAN §4 listed this as a backend testing gap: the newer topics
re-derive their answers in tests, but the original arithmetic types
(addition, subtraction, multiplication, division, algebra, fractions,
order of operations, decimals) were only checked by the generator
agreeing with itself — a builder that computed `a - b` and printed
`{a} + {b}` would have passed everything.

The property: *parse the question text, evaluate it with Python's own
parser and exact rational arithmetic, and get `correctAnswer` back.*
Precedence in particular comes from `ast`, not from the order the
builder happened to multiply things in, so a PEMDAS mistake shows up.

It's a sweep rather than a `hypothesis` run because the input space here
isn't values, it's RNG seeds: every grade × difficulty × seed below is a
draw from the same distribution real quizzes come from, and a shrunk
counterexample would be a seed either way. `test_no_question_escapes_the_checker`
is what keeps it honest — a new question shape that this file can't
parse fails the suite instead of quietly going unchecked.
"""
from __future__ import annotations

import ast
import operator
import random
import re
from fractions import Fraction

import pytest

from app.models import Difficulty, Grade, MathType
from app.questions import generate_questions

SEEDS = range(12)

ARITHMETIC_TYPES = [
    MathType.addition,
    MathType.subtraction,
    MathType.multiplication,
    MathType.division,
    MathType.algebra,
    MathType.fractions,
    MathType.order_of_operations,
    MathType.decimals,
]


# ---------- an evaluator that shares no code with the generator ----------

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def ev(expr: str) -> Fraction:
    """Exact value of an arithmetic expression written the way the app
    prints it (× ÷ − and all). Fractions throughout, so 1/3 stays 1/3
    and 0.1 + 0.2 is exactly 0.3."""
    src = expr.replace("×", "*").replace("÷", "/").replace("−", "-")
    tree = ast.parse(src, mode="eval")

    def go(node):
        if isinstance(node, ast.Constant):
            return Fraction(str(node.value))
        if isinstance(node, ast.BinOp):
            return _BINOPS[type(node.op)](go(node.left), go(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -go(node.operand)
        raise AssertionError(f"unexpected node in {expr!r}: {ast.dump(node)}")

    return go(tree.body)


def val(answer) -> Fraction:
    """The app's answer as an exact number ('3/4', '0.25', 7 → Fraction)."""
    return Fraction(str(answer))


def is_reduced(answer) -> bool:
    """A fraction answer must be in lowest terms and never 'n/1'."""
    text = str(answer)
    if "/" not in text:
        return True
    num, den = (int(p) for p in text.split("/"))
    return den != 1 and abs(Fraction(num, den).denominator) == den


# ---------- one checker per question shape the app can print ----------
#
# Each returns True if it recognised the question (and asserts the
# answer while it's there). Order matters only where patterns overlap.

def _plain_expression(text, answer) -> bool:
    """`7 + 5 = ?`, `12 - 4 = ?`, `3 × 4 = ?`, `20 ÷ 5 = ?`,
    `8 + 2 × 3 - 1 = ?`, `(4 + 3) × 2 = ?`, `0.7 + 0.4 = ?` …"""
    m = re.fullmatch(r"([\d\s().+\-×÷*/]+?) = \?", text)
    if not m:
        return False
    assert ev(m.group(1)) == val(answer), (text, answer)
    return True


def _remainder(text, answer) -> bool:
    m = re.fullmatch(r"What is the remainder when (\d+) ÷ (\d+)\?", text)
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    assert val(answer) == a % b, (text, answer)
    return True


def _division_as_fraction(text, answer) -> bool:
    m = re.fullmatch(
        r"Write (\d+) ÷ (\d+) as a fraction in simplest form \(e\.g\. 3/4\)\.", text
    )
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    assert val(answer) == Fraction(a, b), (text, answer)
    assert is_reduced(answer), (text, answer)
    assert 0 < Fraction(a, b) < 1, f"asked for a proper fraction: {text}"
    return True


def _division_as_decimal(text, answer) -> bool:
    m = re.fullmatch(r"What is (\d+) ÷ (\d+) as a decimal\?", text)
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    assert val(answer) == Fraction(a, b), (text, answer)
    # It has to terminate, or it can't be typed in.
    assert re.fullmatch(r"\d+\.\d+", str(answer)), (text, answer)
    return True


def _equation(text, answer) -> bool:
    """`x + 4 = 11. What is x?`, `3x - 2 = 10. What is x?` — the claimed
    x is substituted back in and both sides must agree."""
    m = re.fullmatch(r"(.+?) = (-?\d+)\. What is x\?", text)
    if not m:
        return False
    lhs, rhs = m.group(1), int(m.group(2))
    substituted = re.sub(r"(\d)x", r"\1*x", lhs).replace("x", f"({val(answer)})")
    assert ev(substituted) == rhs, (text, answer)
    return True


def _fraction_of_whole(text, answer) -> bool:
    m = re.fullmatch(r"What is (\d+)/(\d+) of (\d+)\?", text)
    if not m:
        return False
    num, den, whole = (int(g) for g in m.groups())
    assert val(answer) == Fraction(num, den) * whole, (text, answer)
    return True


def _fraction_expression(text, answer) -> bool:
    """`3/8 + 1/8 = ? (simplest form)` and friends."""
    m = re.fullmatch(r"(\d+/\d+ [+\-×] \d+/\d+) = \? \(simplest form\)", text)
    if not m:
        return False
    assert ev(m.group(1)) == val(answer), (text, answer)
    assert is_reduced(answer), (text, answer)
    return True


def _bigger_decimal(text, answer) -> bool:
    m = re.fullmatch(r"Which is bigger: ([\d.]+) or ([\d.]+)\?", text)
    if not m:
        return False
    a, b = m.group(1), m.group(2)
    assert Fraction(a) != Fraction(b), f"no bigger one: {text}"
    assert str(answer) == (a if Fraction(a) > Fraction(b) else b), (text, answer)
    return True


def _times_ten(text, answer) -> bool:
    m = re.fullmatch(r"What is ([\d.]+) × 10\?", text)
    if not m:
        return False
    assert val(answer) == Fraction(m.group(1)) * 10, (text, answer)
    return True


CHECKERS = [
    _plain_expression,
    _remainder,
    _division_as_fraction,
    _division_as_decimal,
    _equation,
    _fraction_of_whole,
    _fraction_expression,
    _bigger_decimal,
    _times_ten,
]


def verify(text: str, answer) -> bool:
    """Re-solve one question. False means no checker recognised it."""
    return any(check(text, answer) for check in CHECKERS)


def _sweep(math_type: MathType):
    for grade in Grade:
        for difficulty in Difficulty:
            for seed in SEEDS:
                rng = random.Random(seed)
                for q in generate_questions(math_type, difficulty, grade, rng=rng):
                    yield grade, difficulty, q


# ---------- the property ----------


@pytest.mark.parametrize("math_type", ARITHMETIC_TYPES, ids=lambda t: t.value)
def test_printed_question_and_stored_answer_agree(math_type):
    checked = 0
    for _grade, _difficulty, q in _sweep(math_type):
        assert verify(q.question, q.correctAnswer), f"unrecognised: {q.question!r}"
        checked += 1
    assert checked > 1000, f"only {checked} {math_type.value} questions swept"


def test_no_question_escapes_the_checker():
    """The guard on the guard: if a new shape is added to one of these
    topics and nothing here can parse it, this fails rather than letting
    the topic drift out of verification."""
    unrecognised = set()
    for math_type in ARITHMETIC_TYPES:
        for _grade, _difficulty, q in _sweep(math_type):
            if not verify(q.question, q.correctAnswer):
                unrecognised.add(q.question)
    assert not unrecognised, sorted(unrecognised)[:5]


def test_mixed_quizzes_carry_the_same_guarantee():
    """Mixed pulls from every topic; whatever arithmetic surfaces there
    is held to the same standard."""
    checked = 0
    for grade in Grade:
        for difficulty in Difficulty:
            for seed in SEEDS:
                rng = random.Random(seed)
                for q in generate_questions(MathType.mixed, difficulty, grade, rng=rng):
                    if verify(q.question, q.correctAnswer):
                        checked += 1
    assert checked > 100, f"only {checked} mixed arithmetic questions verified"


# ---------- the checker itself has to be able to fail ----------


def test_the_checker_rejects_a_wrong_answer():
    assert verify("7 + 5 = ?", 12)
    with pytest.raises(AssertionError):
        verify("7 + 5 = ?", 13)


def test_the_checker_respects_precedence():
    """Left-to-right would give 27; PEMDAS gives 11."""
    assert verify("3 + 4 × 2 = ?", 11)
    with pytest.raises(AssertionError):
        verify("3 + 4 × 2 = ?", 14)


def test_the_checker_rejects_an_unreduced_fraction():
    assert verify("1/4 + 1/4 = ? (simplest form)", "1/2")
    with pytest.raises(AssertionError):
        verify("1/4 + 1/4 = ? (simplest form)", "2/4")


def test_the_checker_rejects_a_wrong_solution_to_an_equation():
    assert verify("3x + 2 = 11. What is x?", 3)
    with pytest.raises(AssertionError):
        verify("3x + 2 = 11. What is x?", 4)
