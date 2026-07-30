"""Money & time: reading a clock and handling coins, properly tiered.

At grade 5 this topic was still asking "a sticker costs 70¢ and you pay
100¢" — a grade-1 question. The two halves both have real depth once you
go past counting:

* **Money** — how many coins make an amount, the *fewest* coins that
  make it (which is the skill a till uses), and whether you have enough.
* **Time** — not just "how long between these two?", but what time it
  will be after a duration, and totalling durations that carry past an
  hour.

Time answers are written like `5:20`; `grade_answer` accepts `05:20` too.
Money stays in whole cents or whole dollars — no decimal point to type.
"""
from __future__ import annotations

import random

from .rotation import rotating

# (singular, plural, value in cents) — biggest first, which the
# fewest-coins question relies on.
COINS = [
    ("quarter", "quarters", 25),
    ("dime", "dimes", 10),
    ("nickel", "nickels", 5),
    ("penny", "pennies", 1),
]

# Coin-sized things, for questions that pay with a quarter or a dollar.
_SMALL_BUYS = ["sticker", "pencil", "eraser", "badge", "bouncy ball", "sweet", "postcard"]
# Dollar-ish things, for the "have you got enough?" question — nobody
# pays 194¢ for a sweet.
_BIGGER_BUYS = [
    "comic", "notebook", "toy car", "pack of cards", "ice cream",
    "keyring", "water bottle", "puzzle book",
]
_EVENTS = [
    ("film", "starts"), ("swimming lesson", "starts"), ("train", "leaves"),
    ("match", "kicks off"), ("party", "starts"), ("bus", "leaves"),
]
_ACTIVITIES = [
    ("piano practice", [15, 20, 30, 45]),
    ("football training", [45, 60, 90]),
    ("a chapter of the book", [10, 15, 20, 25]),
    ("the dog walk", [20, 30, 40]),
    ("homework", [15, 25, 30, 45]),
]


def _clock(hour: int, minute: int) -> str:
    return f"{hour}:{minute:02d}"


def _add_minutes(hour: int, minute: int, minutes: int) -> tuple[int, int]:
    total = hour * 60 + minute + minutes
    hour24 = (total // 60) % 12
    return (hour24 or 12), total % 60


# ---------- money ----------


def coins_total(rng: random.Random, lo: int, hi: int, *, pool=slice(1, 4)):
    """Two kinds of coin, added up."""
    (n1, p1, v1), (n2, p2, v2) = rng.sample(COINS[pool], 2)
    c1, c2 = rng.randint(1, 4), rng.randint(1, 4)
    total = c1 * v1 + c2 * v2
    return (
        ("coins", v1, c1, v2, c2),
        f"You have {c1} {n1 if c1 == 1 else p1} and {c2} {n2 if c2 == 1 else p2}. "
        f"How many cents is that?",
        total,
        f"{c1} × {v1}¢ + {c2} × {v2}¢ = {total}¢! 💰",
    )


def coins_total_easy(rng: random.Random, lo: int, hi: int):
    return coins_total(rng, lo, hi, pool=slice(1, 4))   # no quarters yet


def coins_total_full(rng: random.Random, lo: int, hi: int):
    return coins_total(rng, lo, hi, pool=slice(0, 4))


def change_from(rng: random.Random, lo: int, hi: int):
    paid = rng.choice([25, 50, 100])
    price = rng.randint(1, paid - 1)
    thing = rng.choice(_SMALL_BUYS)
    return (
        ("change", price, paid),
        f"A {thing} costs {price}¢ and you pay {paid}¢. "
        f"How many cents of change do you get?",
        paid - price,
        f"{paid}¢ - {price}¢ = {paid - price}¢ change! 💰",
    )


def how_many_coins(rng: random.Random, lo: int, hi: int):
    """How many of one coin make an amount — division in disguise."""
    name, plural, value = rng.choice(COINS[:3])
    count = rng.randint(3, 12)
    total = count * value
    return (
        ("coin_count", value, count),
        f"How many {plural} make {total}¢?",
        count,
        f"Each {name} is {value}¢, so {total} ÷ {value} = {count} {plural}! 💰",
    )


def fewest_coins(rng: random.Random, lo: int, hi: int):
    """The question a till answers: what is the smallest handful?"""
    amount = rng.randint(6, 99)
    left, used = amount, []
    for name, plural, value in COINS:
        n, left = divmod(left, value)
        if n:
            used.append((n, name if n == 1 else plural, value))
    count = sum(n for n, _, _ in used)
    breakdown = " + ".join(f"{n} {word} ({n * value}¢)" for n, word, value in used)
    return (
        ("fewest", amount),
        f"Coins come in 25¢, 10¢, 5¢ and 1¢.\n\n"
        f"What is the FEWEST number of coins that makes {amount}¢?",
        count,
        f"Take the biggest coins first: {breakdown} — that's {count} coins. 💰",
    )


def enough_money(rng: random.Random, lo: int, hi: int):
    """Have you got enough, and how much short or spare?"""
    price = rng.randint(30, 250)
    purse = rng.randint(20, 300)
    while purse == price:
        purse = rng.randint(20, 300)
    thing = rng.choice(_BIGGER_BUYS)
    short = purse < price
    answer = abs(purse - price)
    asked = "short are you" if short else "would be left over"
    return (
        ("enough", price, purse),
        f"A {thing} costs {price}¢. You have {purse}¢.\n\n"
        f"How many cents {asked}?",
        answer,
        (
            f"{price}¢ - {purse}¢ = {answer}¢ short. 💰"
            if short
            else f"{purse}¢ - {price}¢ = {answer}¢ left over. 💰"
        ),
    )


# ---------- time ----------


def hours_to_minutes(rng: random.Random, lo: int, hi: int):
    h = rng.randint(2, 9)
    return (
        ("h2m", h),
        f"How many minutes are in {h} hours?",
        h * 60,
        f"Each hour has 60 minutes: {h} × 60 = {h * 60}! ⏰",
    )


def minutes_to_next_hour(rng: random.Random, lo: int, hi: int):
    h = rng.randint(1, 11)
    m = rng.choice([5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return (
        ("tonext", h, m),
        f"How many minutes is it from {_clock(h, m)} to {_clock(h + 1, 0)}?",
        60 - m,
        f"From {_clock(h, m)} up to {_clock(h + 1, 0)} is 60 - {m} = {60 - m} minutes! ⏰",
    )


def elapsed_minutes(rng: random.Random, lo: int, hi: int):
    h1 = rng.randint(1, 9)
    m1 = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    hours = rng.randint(1, 2)
    m2 = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    h2 = h1 + hours
    answer = hours * 60 + (m2 - m1)
    return (
        ("elapsed", h1, m1, h2, m2),
        f"How many minutes is it from {_clock(h1, m1)} to {_clock(h2, m2)}?",
        answer,
        f"From {_clock(h1, m1)} to {_clock(h2, m2)} is {answer} minutes. "
        f"Count the full hours first, then the extra minutes! ⏰",
    )


def what_time_after(rng: random.Random, lo: int, hi: int):
    """Forwards, not backwards — and the answer is a time, not a number."""
    hour, minute = rng.randint(1, 11), rng.choice([0, 5, 10, 15, 20, 25, 30, 40, 45, 50])
    minutes = rng.choice([25, 35, 40, 45, 50, 55, 70, 80, 90, 95, 105])
    thing, verb = rng.choice(_EVENTS)
    end_h, end_m = _add_minutes(hour, minute, minutes)
    return (
        ("time_after", hour, minute, minutes),
        f"The {thing} {verb} at {_clock(hour, minute)} and lasts {minutes} minutes.\n\n"
        f"What time does it finish? Write it like {_clock(4, 30)}.",
        _clock(end_h, end_m),
        f"{_clock(hour, minute)} plus {minutes} minutes is "
        f"{_clock(end_h, end_m)}. Add the hours first, then the minutes! ⏰",
    )


def what_time_before(rng: random.Random, lo: int, hi: int):
    """Working back from a deadline — leaving time, not arriving time."""
    hour, minute = rng.randint(2, 11), rng.choice([0, 10, 15, 20, 30, 40, 45])
    minutes = rng.choice([20, 25, 35, 40, 45, 50, 55, 70, 90])
    thing, verb = rng.choice(_EVENTS)
    start_h, start_m = _add_minutes(hour, minute, -minutes)
    return (
        ("time_before", hour, minute, minutes),
        f"The {thing} {verb} at {_clock(hour, minute)}. The journey there takes "
        f"{minutes} minutes.\n\nWhat time do you need to leave? "
        f"Write it like {_clock(4, 30)}.",
        _clock(start_h, start_m),
        f"Count back {minutes} minutes from {_clock(hour, minute)}: "
        f"{_clock(start_h, start_m)}. ⏰",
    )


def total_duration(rng: random.Random, lo: int, hi: int):
    """Durations that carry past an hour."""
    activity, lengths = rng.choice(_ACTIVITIES)
    each = rng.choice(lengths)
    times = rng.randint(3, 6)
    total = each * times
    hours, minutes = divmod(total, 60)
    return (
        ("duration", each, times),
        f"{activity.capitalize()} takes {each} minutes, {times} times a week.\n\n"
        f"How many minutes is that in a week?",
        total,
        f"{times} × {each} = {total} minutes"
        + (f" — that's {hours} hours and {minutes} minutes! ⏰" if hours else "! ⏰"),
    )


TIERS = {
    # Grade 1-2: counting coins and whole hours.
    "basic": (coins_total_easy, hours_to_minutes, how_many_coins),
    # Grade 2-3: change, quarters, minutes off the clock.
    "counting": (
        coins_total_full, change_from, how_many_coins,
        minutes_to_next_hour, hours_to_minutes,
    ),
    # Grade 3-4: elapsed time, the fewest-coins problem, enough-money.
    "reasoning": (
        fewest_coins, enough_money, elapsed_minutes,
        minutes_to_next_hour, coins_total_full, total_duration,
    ),
    # Grade 5: clock arithmetic that lands on a time, forwards and back.
    "planning": (
        what_time_after, what_time_before, total_duration,
        fewest_coins, enough_money, elapsed_minutes,
    ),
}


def tier_for(difficulty_is_easy: bool, difficulty_is_hard: bool, g: int) -> str:
    if g >= 5 or (g >= 4 and difficulty_is_hard):
        return "planning"
    if g >= 4 or (g >= 3 and not difficulty_is_easy):
        return "reasoning"
    if g >= 2 or not difficulty_is_easy:
        return "counting"
    return "basic"


def tier_factory(tier: str):
    return rotating(TIERS[tier], tier)
