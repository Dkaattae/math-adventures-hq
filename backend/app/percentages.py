"""Percentages: seven shapes instead of one.

The topic used to be a single question — "What is 25% of 80?" — with the
only difference between grade 4 and grade 5 being which percentages were
in the table. A percentage is worth more than that: the useful skills are
running it backwards (what percent is 9 out of 12?), finding the whole
from a part, and the everyday version nobody escapes — a discount, a tip,
and the sale that takes another 10% off the already-reduced price.

Every answer is a whole number, so the numbers are chosen to divide
cleanly rather than rounded afterwards.
"""
from __future__ import annotations

import random

from .rotation import rotating

# (percent, the multiple `n` must be so the answer stays whole)
_BASIC_PERCENTS = [(50, 2), (10, 10), (100, 1)]
_FULL_PERCENTS = _BASIC_PERCENTS + [(25, 4), (20, 5), (75, 4), (5, 20)]
# Percentages that come out whole for a "what percent is this?" question.
_TIDY_PERCENTS = [10, 20, 25, 40, 50, 60, 75, 80]
# 100% is worth teaching in "what is 100% of 40?" but makes a nonsense
# discount ("100% off") and a giveaway backwards question.
_PART_PERCENTS = [(p, m) for p, m in _FULL_PERCENTS if p != 100]

_THINGS = [
    ("jacket", 20, 80), ("bike", 60, 200), ("game", 20, 60), ("pair of boots", 30, 90),
    ("tent", 40, 160), ("guitar", 80, 240), ("scooter", 40, 120), ("backpack", 20, 60),
    ("watch", 30, 100), ("desk lamp", 10, 40),
]
_MEALS = [("pizza", 10, 40), ("lunch", 10, 30), ("dinner", 20, 80), ("takeaway", 10, 50)]
_GROUPS = [
    ("shots at the hoop", "went in"), ("spelling words", "were right"),
    ("seeds planted", "grew"), ("raffle tickets", "won a prize"),
    ("questions on the test", "were correct"), ("apples in the crate", "were ripe"),
]


def _price_for(rng: random.Random, low: int, high: int, percent: int) -> int:
    """A price in range that the percentage divides into whole dollars."""
    step = 100 // _gcd(percent, 100)
    lowest = max(step, (low // step) * step)
    highest = max(lowest, (high // step) * step)
    return rng.randrange(lowest, highest + 1, step)


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


# ---------- the plain skill ----------


def _percent_of(rng: random.Random, table) -> tuple[int, int, int]:
    percent, multiple = rng.choice(table)
    n = multiple * rng.randint(2, 20)
    return percent, n, percent * n // 100


def pct_of_basic(rng: random.Random, lo: int, hi: int):
    percent, n, answer = _percent_of(rng, _BASIC_PERCENTS)
    return (
        ("pct_of", percent, n),
        f"What is {percent}% of {n}?",
        answer,
        f"{percent}% means {percent} out of every 100: {percent}% of {n} = {answer}! 💯",
    )


def pct_of_full(rng: random.Random, lo: int, hi: int):
    percent, n, answer = _percent_of(rng, _FULL_PERCENTS)
    return (
        ("pct_of", percent, n),
        f"What is {percent}% of {n}?",
        answer,
        f"{percent}% of {n} = {answer}. Find 1% first ({n} ÷ 100), then multiply! 💯",
    )


# ---------- running it backwards ----------


def pct_what_percent(rng: random.Random, lo: int, hi: int):
    """9 out of 12 — what percent is that?"""
    percent = rng.choice(_TIDY_PERCENTS)
    step = 100 // _gcd(percent, 100)
    whole = step * rng.randint(1, max(2, 200 // step))
    part = whole * percent // 100
    thing, verb = rng.choice(_GROUPS)
    return (
        ("pct_what", percent, whole),
        f"{part} of the {whole} {thing} {verb}. What percent is that?\n\n"
        f"Write just the number.",
        percent,
        f"{part} out of {whole} = {part} ÷ {whole} = {percent / 100:g}, "
        f"which is {percent}%. 💯",
    )


def pct_find_whole(rng: random.Random, lo: int, hi: int):
    """20% of a number is 15 — what was the number?"""
    percent, multiple = rng.choice(_PART_PERCENTS)
    whole = multiple * rng.randint(2, 20)
    part = percent * whole // 100
    return (
        ("pct_whole", percent, whole),
        f"{percent}% of a number is {part}. What is the number?",
        whole,
        f"If {percent}% is {part}, then 1% is {part} ÷ {percent} = {part / percent:g}, "
        f"so 100% is {whole}. 💯",
    )


# ---------- the everyday versions ----------


def pct_discount(rng: random.Random, lo: int, hi: int):
    """The price after a sale — not the saving, which is the easy half."""
    percent, _ = rng.choice(_PART_PERCENTS)
    thing, low, high = rng.choice(_THINGS)
    price = _price_for(rng, low, high, percent)
    saving = price * percent // 100
    answer = price - saving
    return (
        ("pct_disc", percent, price, thing),
        f"A {thing} costs ${price}. Today it is {percent}% off.\n\n"
        f"How many dollars does it cost now?",
        answer,
        f"{percent}% of ${price} is ${saving} off, so you pay "
        f"${price} - ${saving} = ${answer}. 🏷️",
    )


def pct_tip(rng: random.Random, lo: int, hi: int):
    """A total that goes *up* — the direction kids get wrong."""
    percent = rng.choice([10, 20, 25, 50])
    thing, low, high = rng.choice(_MEALS)
    price = _price_for(rng, low, high, percent)
    extra = price * percent // 100
    return (
        ("pct_tip", percent, price, thing),
        f"A {thing} costs ${price}. A {percent}% tip is added.\n\n"
        f"How many dollars is the bill altogether?",
        price + extra,
        f"{percent}% of ${price} is ${extra}, so the bill is "
        f"${price} + ${extra} = ${price + extra}. 🧾",
    )


def pct_double_discount(rng: random.Random, lo: int, hi: int):
    """Two discounts in a row — and no, they don't add up to 60%."""
    first, second = rng.choice([(50, 10), (50, 20), (25, 20), (20, 25), (50, 50), (40, 25)])
    thing, low, high = rng.choice(_THINGS)
    for _ in range(30):
        price = _price_for(rng, low, high, first)
        after_first = price - price * first // 100
        if after_first * second % 100 == 0:
            break
    else:
        price, first, second = 100, 50, 20
        after_first = 50
    final = after_first - after_first * second // 100
    return (
        ("pct_double", first, second, price, thing),
        f"A {thing} costs ${price}. It is {first}% off in the sale.\n\n"
        f"At the till, another {second}% comes off the sale price.\n\n"
        f"How many dollars does it cost in the end?",
        final,
        f"{first}% off ${price} leaves ${after_first}. Then {second}% off "
        f"${after_first} leaves ${final}. Careful — that is not the same as "
        f"{first + second}% off! 🏷️",
    )


def pct_better_deal(rng: random.Random, lo: int, hi: int):
    """A percentage off against a flat amount off."""
    percent, _ = rng.choice([(25, 4), (20, 5), (50, 2), (10, 10)])
    thing, low, high = rng.choice(_THINGS)
    for _ in range(30):
        price = _price_for(rng, low, high, percent)
        percent_saving = price * percent // 100
        flat = rng.randint(max(2, percent_saving - 12), percent_saving + 12)
        if flat != percent_saving and flat < price:
            break
    else:
        price, percent, percent_saving, flat = 80, 25, 20, 15
    answer = price - max(percent_saving, flat)
    better = f"{percent}% off" if percent_saving > flat else f"${flat} off"
    return (
        ("pct_deal", percent, price, flat, thing),
        f"A {thing} costs ${price}. Two coupons are on the counter:\n\n"
        f"• {percent}% off\n"
        f"• ${flat} off\n\n"
        f"Using the better coupon, how many dollars does it cost?",
        answer,
        f"{percent}% off saves ${percent_saving}; the other saves ${flat}. "
        f"The {better} coupon wins, so you pay ${answer}. 🏷️",
    )


TIERS = {
    # Grade 4 easy: the plain skill, friendly percentages.
    "basic": (pct_of_basic, pct_of_full, pct_discount),
    # Grade 4 medium+ and grade 5: backwards, and the everyday versions.
    "applied": (pct_of_full, pct_discount, pct_tip, pct_what_percent, pct_find_whole),
    # Grade 5 hard: two steps, and choosing between deals.
    "advanced": (
        pct_double_discount, pct_better_deal, pct_find_whole,
        pct_what_percent, pct_tip, pct_discount,
    ),
}


def tier_for(difficulty_is_easy: bool, g: int) -> str:
    if g >= 5 and not difficulty_is_easy:
        return "advanced"
    if g >= 5 or not difficulty_is_easy:
        return "applied"
    return "basic"


def tier_factory(tier: str):
    return rotating(TIERS[tier], tier)
