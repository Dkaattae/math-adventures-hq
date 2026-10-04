"""Fractions: pictures first, then the arithmetic, then the bridges to
decimals and division.

The topic used to be four templates — "2/3 of 12", like denominators,
unlike denominators, multiplication — and a second grader met fractions
as symbols with nothing to look at. A fraction is a picture before it is
a number, so the ladder now starts there:

1. `pictures`  (grade 2-3 easy) — what part of the pie is shaded, which
   slice is bigger, adding slices of the same pie, all with a pie drawn
2. `building`  (grade 2 medium+) — the same skills with less hand-holding,
   plus equivalent fractions ("1/2 = ?/8")
3. `wholes`    (grade 3 medium+, grade 4 easy) — more than one pie: 13/5
   is 13 ÷ 5 = 2 R 3, which is the mixed number 2 3/5
4. `decimals`  (grade 4 medium, grade 5 easy) — 1/4 = 0.25 and back,
   unlike denominators, comparing fractions that share nothing
5. `advanced`  (grade 4 hard, grade 5 medium+) — multiplication, mixed
   numbers both ways, trickier decimals; no pictures

Pictures travel as a `figure` string the client draws (`FractionPies`):
`pie:` then space-separated tokens, each a fraction ("3/8") or an
operator ("+"). A fraction bigger than one draws as several pies, so
"pie:13/5" is two full pies and three fifths of a third. Only fractions
that draw legibly get one — at most 12 slices a pie and 3 pies.

The question text keeps the plain "1/4 + 2/9" form; the client stacks
every "a/b" it prints, so the phone shows a proper numerator over a
denominator without the backend knowing anything about layout.

Each builder returns (signature, text, answer, explanation[, figure]).
"""
from __future__ import annotations

import random
from fractions import Fraction
from functools import partial
from math import gcd
from typing import Callable

from .rotation import rotating

#: Past this many slices a pie is a hairbrush, not a picture.
PIE_MAX_DEN = 12
#: Pies drawn for one fraction; 13/5 needs three.
PIE_MAX_WHOLES = 3

#: Fixed examples shown in the question so a kid knows the format. A
#: question whose answer *is* the example is regenerated.
REMAINDER_EXAMPLE = "5 R 1"
MIXED_EXAMPLE = "1 1/2"

_PIE_THINGS = ("pizza", "pie", "cake", "pancake", "quesadilla")


# ---------- helpers ----------


def simplify(num: int, den: int) -> str:
    """num/den in lowest terms; whole-number results drop the denominator."""
    if num == 0:
        return "0"
    g = gcd(num, den)
    num, den = num // g, den // g
    return str(num) if den == 1 else f"{num}/{den}"


def mixed(num: int, den: int) -> str:
    """An improper fraction as a mixed number in lowest terms ("2 3/5")."""
    whole, rest = divmod(num, den)
    if rest == 0:
        return str(whole)
    part = simplify(rest, den)
    return part if whole == 0 else f"{whole} {part}"


def decimal_str(num: int, den: int) -> str | None:
    """num/den as a terminating decimal ("0.25"), or None if it repeats."""
    value = Fraction(num, den)
    for places in range(0, 5):
        scaled = value * 10 ** places
        if scaled.denominator == 1:
            digits = str(scaled.numerator).rjust(places + 1, "0")
            if places == 0:
                return digits
            return f"{digits[:-places]}.{digits[-places:]}"
    return None


def fits_pie(num: int, den: int) -> bool:
    return 1 <= den <= PIE_MAX_DEN and 0 <= num <= den * PIE_MAX_WHOLES


def pie(*tokens: str) -> str:
    return "pie:" + " ".join(tokens)


def _with_figure(result: tuple, figure: str | None, picture: bool) -> tuple:
    return result + (figure,) if picture and figure else result


def _coprime_numerator(rng: random.Random, den: int, lo: int = 1, hi: int | None = None) -> int:
    hi = den - 1 if hi is None else hi
    choices = [n for n in range(lo, hi + 1) if gcd(n, den) == 1]
    return rng.choice(choices)


# ---------- the originals (text unchanged, pictures added) ----------


def frac_of_whole(rng: random.Random, lo: int, hi: int, *, picture: bool = False):
    den = rng.choice([2, 3, 4, 5, 10])
    multiplier = rng.randint(1, max(2, hi // den))
    whole = den * multiplier
    num = rng.randint(1, den - 1)
    answer = num * whole // den
    return _with_figure(
        (
            ("fracof", num, den, whole),
            f"What is {num}/{den} of {whole}?",
            answer,
            f"{whole} ÷ {den} = {whole // den}, then × {num} = {answer}. 🍕",
        ),
        pie(f"{num}/{den}"),
        picture,
    )


def frac_same_denom(rng: random.Random, lo: int, hi: int, *, picture: bool = False,
                    max_den: int | None = None):
    top = max(3, hi // 2) if max_den is None else max_den
    den = rng.randint(2, top)
    a = rng.randint(1, den - 1)
    b = rng.randint(1, den - 1)
    op = rng.choice(["+", "-"])
    if op == "-" and b > a:
        a, b = b, a
    num = a + b if op == "+" else a - b
    result = simplify(num, den)
    hint = f"{a}/{den} {op} {b}/{den} = {num}/{den}" + (
        f" = {result}" if result != f"{num}/{den}" else ""
    ) + "."
    if op == "+":
        hint += f" Same-size slices, so just count them: {a} + {b} = {num}."
    else:
        hint += f" Same-size slices, so just take away: {a} − {b} = {num}."
    figure = pie(f"{a}/{den}", op, f"{b}/{den}") if fits_pie(max(a, b), den) else None
    return _with_figure(
        (
            ("fracsame", op, den, a, b),
            f"{a}/{den} {op} {b}/{den} = ? (simplest form)",
            result,
            hint + " 🍕",
        ),
        figure,
        picture,
    )


def frac_unlike_denom(rng: random.Random, lo: int, hi: int, *, picture: bool = False):
    d1 = rng.randint(2, max(3, hi // 3))
    d2 = rng.randint(2, max(3, hi // 3))
    if d2 == d1:
        d2 += 1
    n1 = rng.randint(1, d1 - 1)
    n2 = rng.randint(1, d2 - 1)
    lcd = d1 * d2 // gcd(d1, d2)
    num = n1 * (lcd // d1) + n2 * (lcd // d2)
    result = simplify(num, lcd)
    figure = (
        pie(f"{n1}/{d1}", "+", f"{n2}/{d2}") if fits_pie(n1, d1) and fits_pie(n2, d2) else None
    )
    return _with_figure(
        (
            ("fracunlike", d1, n1, d2, n2),
            f"{n1}/{d1} + {n2}/{d2} = ? (simplest form)",
            result,
            f"The slices are different sizes, so cut them the same first. "
            f"LCD of {d1} and {d2} is {lcd}: {n1}/{d1} = {n1 * (lcd // d1)}/{lcd}, "
            f"{n2}/{d2} = {n2 * (lcd // d2)}/{lcd}. Sum = {num}/{lcd}"
            + (f" = {result}" if result != f"{num}/{lcd}" else "")
            + ". 🍕",
        ),
        figure,
        picture,
    )


def frac_multiply(rng: random.Random, lo: int, hi: int):
    n1 = rng.randint(1, max(2, hi // 3))
    d1 = rng.randint(n1 + 1, max(n1 + 2, hi // 2 + 1))
    n2 = rng.randint(1, max(2, hi // 3))
    d2 = rng.randint(n2 + 1, max(n2 + 2, hi // 2 + 1))
    num, den = n1 * n2, d1 * d2
    result = simplify(num, den)
    return (
        ("fracmul", n1, d1, n2, d2),
        f"{n1}/{d1} × {n2}/{d2} = ? (simplest form)",
        result,
        f"Multiply straight across: ({n1}×{n2})/({d1}×{d2}) = {num}/{den}"
        + (f" = {result}" if result != f"{num}/{den}" else "")
        + ". 🍕",
    )


# ---------- reading a picture ----------


def frac_shaded(rng: random.Random, lo: int, hi: int):
    """The first fraction skill: count the shaded slices, count them all.

    The numerator is kept coprime with the denominator so the slice count
    *is* the simplest form — a second grader who counts 2 of 4 slices
    shouldn't be marked wrong for not writing 1/2.
    """
    den = rng.choice([2, 3, 4, 5, 6, 8])
    shaded = _coprime_numerator(rng, den)
    thing = rng.choice(_PIE_THINGS)
    ask_unshaded = den > 2 and rng.random() < 0.35
    answer_num = den - shaded if ask_unshaded else shaded
    which = "NOT shaded" if ask_unshaded else "shaded"
    return (
        ("fracpic", shaded, den, ask_unshaded),
        f"This {thing} is cut into equal slices. What fraction of it is {which}?",
        f"{answer_num}/{den}",
        f"There are {den} slices in all (the bottom number) and {answer_num} "
        f"{'are' if answer_num != 1 else 'is'} {which} (the top number): "
        f"{answer_num}/{den}. 🍕",
        pie(f"{shaded}/{den}"),
    )


def frac_compare(rng: random.Random, lo: int, hi: int, *, modes: tuple[str, ...],
                 picture: bool = False):
    """Which is bigger? From unit fractions (1/3 vs 1/5 — fewer slices
    means *bigger* slices, the classic surprise) up to fractions that
    share nothing and need cross-multiplying."""
    mode = rng.choice(modes)
    if mode == "unit":
        a, b = rng.sample(range(2, 11), 2)
        left, right = (1, a), (1, b)
        why = (f"Both are one slice. Cutting into fewer slices makes each slice bigger, "
               f"so 1/{min(a, b)} is bigger than 1/{max(a, b)}.")
    elif mode == "same_den":
        den = rng.randint(3, 12)
        a, b = rng.sample(range(1, den), 2)
        left, right = (a, den), (b, den)
        why = f"Same-size slices ({den} in a whole), so more slices is more: {max(a, b)} > {min(a, b)}."
    elif mode == "same_num":
        num = rng.randint(2, 5)
        a, b = rng.sample(range(num + 1, 13), 2)
        left, right = (num, a), (num, b)
        why = (f"Both have {num} slices, but slices out of {min(a, b)} are bigger "
               f"than slices out of {max(a, b)}.")
    else:  # "any"
        while True:
            d1, d2 = rng.sample(range(3, 13), 2)
            n1, n2 = _coprime_numerator(rng, d1), _coprime_numerator(rng, d2)
            if Fraction(n1, d1) != Fraction(n2, d2):
                break
        left, right = (n1, d1), (n2, d2)
        why = (f"Cross-multiply: {n1} × {d2} = {n1 * d2} and {n2} × {d1} = {n2 * d1}, "
               f"so the {'first' if n1 * d2 > n2 * d1 else 'second'} one is bigger.")
    if rng.random() < 0.5:
        left, right = right, left
    l_str, r_str = f"{left[0]}/{left[1]}", f"{right[0]}/{right[1]}"
    answer = l_str if Fraction(*left) > Fraction(*right) else r_str
    figure = pie(l_str, r_str) if fits_pie(*left) and fits_pie(*right) else None
    return _with_figure(
        (
            ("fraccmp", left, right),
            f"Which is bigger: {l_str} or {r_str}?",
            answer,
            f"{why} {answer} is bigger! 🍕",
        ),
        figure,
        picture,
    )


def frac_equivalent(rng: random.Random, lo: int, hi: int, *, picture: bool = False,
                    max_factor: int = 4):
    """1/2 = ?/8 — the same amount of pie, cut into more slices."""
    den = rng.choice([2, 3, 4, 5, 6])
    num = _coprime_numerator(rng, den)
    k = rng.randint(2, max_factor)
    missing_top = rng.random() < 0.6
    if missing_top:
        text = f"Fill in the missing number: {num}/{den} = ?/{den * k}"
        answer = num * k
        why = f"{den} × {k} = {den * k}, so the top goes up {k} times too: {num} × {k} = {num * k}."
    else:
        text = f"Fill in the missing number: {num}/{den} = {num * k}/?"
        answer = den * k
        why = f"{num} × {k} = {num * k}, so the bottom goes up {k} times too: {den} × {k} = {den * k}."
    return _with_figure(
        (
            ("fraceq", num, den, k, missing_top),
            text,
            answer,
            f"{why} Same amount of pie, just cut into {k} times as many slices. 🍕",
        ),
        pie(f"{num}/{den}"),
        picture,
    )


# ---------- more than one whole: division, remainders, mixed numbers ----------


def _improper(rng: random.Random, max_wholes: int, dens: tuple[int, ...]) -> tuple[int, int]:
    """An improper fraction n/d with 1 < n/d < max_wholes + 1, in lowest
    terms and never a whole number."""
    den = rng.choice(dens)
    while True:
        whole = rng.randint(1, max_wholes)
        rest = rng.randint(1, den - 1)
        num = whole * den + rest
        if gcd(num, den) == 1:
            return num, den


def frac_remainder(rng: random.Random, lo: int, hi: int, *, picture: bool = False,
                   max_wholes: int = 2, dens: tuple[int, ...] = (2, 3, 4, 5, 6)):
    """13/5 is 13 ÷ 5: two whole pies and 3 slices over — 2 R 3."""
    while True:
        num, den = _improper(rng, max_wholes, dens)
        whole, rest = divmod(num, den)
        answer = f"{whole} R {rest}"
        if answer != REMAINDER_EXAMPLE:
            break
    figure = pie(f"{num}/{den}") if fits_pie(num, den) else None
    return _with_figure(
        (
            ("fracrem", num, den),
            f"The fraction bar means divide: {num}/{den} = {num} ÷ {den}. "
            f"Write it as a whole number and a remainder (e.g. {REMAINDER_EXAMPLE}).",
            answer,
            f"{den} goes into {num} {whole} time{'s' if whole != 1 else ''} "
            f"({whole} × {den} = {whole * den}), with {rest} left over: {answer}. "
            f"That's {whole} whole pie{'s' if whole != 1 else ''} and {rest}/{den} of another, "
            f"or {mixed(num, den)} as a mixed number. 🍕",
        ),
        figure,
        picture,
    )


def frac_to_mixed(rng: random.Random, lo: int, hi: int, *, picture: bool = False,
                  max_wholes: int = 2, dens: tuple[int, ...] = (2, 3, 4, 5, 6)):
    while True:
        num, den = _improper(rng, max_wholes, dens)
        answer = mixed(num, den)
        if answer != MIXED_EXAMPLE:
            break
    whole, rest = divmod(num, den)
    figure = pie(f"{num}/{den}") if fits_pie(num, den) else None
    return _with_figure(
        (
            ("fracmix", num, den),
            f"Write {num}/{den} as a mixed number (e.g. {MIXED_EXAMPLE}).",
            answer,
            f"{num} ÷ {den} = {whole} R {rest}: {whole} whole{'s' if whole != 1 else ''} "
            f"and {rest}/{den} left over, "
            f"so {num}/{den} = {answer}. 🍕",
        ),
        figure,
        picture,
    )


def frac_from_mixed(rng: random.Random, lo: int, hi: int, *, max_wholes: int = 4,
                    dens: tuple[int, ...] = (2, 3, 4, 5, 6, 8)):
    num, den = _improper(rng, max_wholes, dens)
    whole, rest = divmod(num, den)
    return (
        ("fracimp", num, den),
        f"Write {whole} {rest}/{den} as an improper fraction.",
        f"{num}/{den}",
        f"Each whole is {den}/{den}, so {whole} wholes = {whole * den}/{den}. "
        f"Add the {rest}/{den}: {whole * den} + {rest} = {num}, so it's {num}/{den}. 🍕",
    )


# ---------- fractions and decimals ----------

#: Denominators that turn into tidy decimals, by how hard they are.
_DEC_DENS_EASY = (2, 4, 5, 10)
_DEC_DENS_HARD = (2, 4, 5, 8, 10, 20, 25, 100)


def _decimal_pair(rng: random.Random, dens: tuple[int, ...], improper: bool):
    den = rng.choice(dens)
    num = _coprime_numerator(rng, den)
    if improper and rng.random() < 0.35:
        num += den * rng.randint(1, 2)
    return num, den, decimal_str(num, den)


def frac_to_decimal(rng: random.Random, lo: int, hi: int, *, picture: bool = False,
                    dens: tuple[int, ...] = _DEC_DENS_EASY, improper: bool = False):
    num, den, dec = _decimal_pair(rng, dens, improper)
    scale = next(s for s in (10, 100, 1000) if s % den == 0)
    over = num * scale // den
    word = {10: "tenths", 100: "hundredths", 1000: "thousandths"}[scale]
    why = (
        f"Make the bottom {scale}: {num}/{den} = {over}/{scale}, which is {over} {word} = {dec}."
        if scale != den
        else f"{num}/{den} is {num} {word}, which is {dec}."
    )
    figure = pie(f"{num}/{den}") if fits_pie(num, den) else None
    return _with_figure(
        (
            ("fracdec", num, den),
            f"Write {num}/{den} as a decimal.",
            dec,
            f"{why} (Or divide: {num} ÷ {den} = {dec}.) 💡",
        ),
        figure,
        picture,
    )


def decimal_to_frac(rng: random.Random, lo: int, hi: int, *,
                    dens: tuple[int, ...] = _DEC_DENS_EASY, improper: bool = False):
    num, den, dec = _decimal_pair(rng, dens, improper)
    places = len(dec.split(".")[1])
    scale = 10 ** places
    over = int(Fraction(dec) * scale)
    answer = f"{num}/{den}"
    return (
        ("decfrac", num, den),
        f"Write {dec} as a fraction in simplest form.",
        answer,
        f"{dec} is {over}/{scale}"
        + (f", and dividing top and bottom by {scale // den} gives {answer}" if scale != den else "")
        + ". 💡",
    )


# ---------- tiers ----------

_COMPARE_YOUNG = ("unit", "same_den")
_COMPARE_MIDDLE = ("unit", "same_den", "same_num")

TIERS: dict[str, tuple[Callable, ...]] = {
    # Grade 2-3 easy: every question has a picture to look at.
    "pictures": (
        frac_shaded,
        partial(frac_compare, modes=_COMPARE_YOUNG, picture=True),
        partial(frac_same_denom, picture=True, max_den=8),
        partial(frac_of_whole, picture=True),
        partial(frac_equivalent, picture=True, max_factor=3),
    ),
    # Grade 2 medium+: the same skills, a little further from the picture.
    "building": (
        frac_shaded,
        partial(frac_compare, modes=_COMPARE_MIDDLE, picture=True),
        partial(frac_same_denom, picture=True, max_den=12),
        frac_of_whole,
        partial(frac_equivalent, picture=True),
    ),
    # Grade 3 medium+, grade 4 easy: more than one whole pie.
    "wholes": (
        partial(frac_remainder, picture=True),
        partial(frac_to_mixed, picture=True),
        partial(frac_compare, modes=_COMPARE_MIDDLE, picture=True),
        partial(frac_same_denom, picture=True, max_den=12),
        frac_equivalent,
        frac_of_whole,
    ),
    # Grade 4 medium, grade 5 easy: fractions ⇄ decimals, unlike slices.
    "decimals": (
        partial(frac_to_decimal, picture=True),
        decimal_to_frac,
        partial(frac_unlike_denom, picture=True),
        partial(frac_compare, modes=("same_num", "any")),
        partial(frac_remainder, max_wholes=3, dens=(3, 4, 5, 6, 7, 8)),
        partial(frac_to_mixed, max_wholes=3, dens=(3, 4, 5, 6, 7, 8)),
        frac_same_denom,
    ),
    # Grade 4 hard, grade 5 medium+: no pictures, bigger numbers.
    "advanced": (
        frac_unlike_denom,
        frac_multiply,
        partial(frac_to_decimal, dens=_DEC_DENS_HARD, improper=True),
        partial(decimal_to_frac, dens=_DEC_DENS_HARD, improper=True),
        partial(frac_to_mixed, max_wholes=5, dens=(3, 4, 5, 6, 7, 8, 9, 10, 12)),
        frac_from_mixed,
        partial(frac_compare, modes=("any",)),
    ),
}


def tier_for(difficulty: str, g: int) -> str:
    """Which fraction tier a grade/difficulty draws from (difficulty is
    the enum's value: "easy", "medium" or "hard")."""
    if (g >= 5 and difficulty != "easy") or (g == 4 and difficulty == "hard"):
        return "advanced"
    if g >= 5 or (g == 4 and difficulty == "medium"):
        return "decimals"
    if g == 4 or (g == 3 and difficulty != "easy"):
        return "wholes"
    if difficulty != "easy":
        return "building"
    return "pictures"


def tier_factory(tier: str):
    return rotating(TIERS[tier], tier)
