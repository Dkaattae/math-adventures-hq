"""Measurement: conversions put to work.

The topic used to be bare conversions — "24 feet is how many yards?" —
and grade 5 got the same question as grade 2 with a bigger factor. A
conversion on its own is a lookup; the skill is knowing when you need
one. So the tiers move from the plain conversion, through comparing two
measurements written in different units, to problems where converting is
just the first of two steps: how many 50 cm pieces come out of a 3 m
ribbon, how much juice is left in a 2 liter bottle.

Everything divides exactly — no rounding, no decimals — so every answer
is a whole number.
"""
from __future__ import annotations

import random

from .rotation import rotating

# (factor, small plural, big singular, big plural, family)
_CONVERSIONS_BASIC = [
    (100, "centimeters", "meter", "meters", "length"),
    (10, "millimeters", "centimeter", "centimeters", "length"),
    (60, "seconds", "minute", "minutes", "time"),
    (12, "inches", "foot", "feet", "length"),
]
_CONVERSIONS_FULL = _CONVERSIONS_BASIC + [
    (1000, "meters", "kilometer", "kilometers", "length"),
    (1000, "grams", "kilogram", "kilograms", "mass"),
    (1000, "milliliters", "liter", "liters", "volume"),
    (3, "feet", "yard", "yards", "length"),
    (60, "minutes", "hour", "hours", "time"),
]

# Things worth measuring, and the unit that actually suits them.
_UNIT_CHOICES = [
    ("a pencil", "centimeters", ("kilometers", "liters")),
    ("the school playground", "meters", ("millimeters", "grams")),
    ("the drive to the seaside", "kilometers", ("centimeters", "milliliters")),
    ("a bag of sugar", "grams", ("liters", "meters")),
    ("a bottle of juice", "milliliters", ("centimeters", "grams")),
    ("a person's height", "centimeters", ("kilometers", "milliliters")),
    ("a car's weight", "kilograms", ("milliliters", "centimeters")),
    ("a swimming pool", "meters", ("millimeters", "grams")),
]

_CUT_ITEMS = [
    ("ribbon", 100, "centimeters", "meters"),
    ("rope", 100, "centimeters", "meters"),
    ("wire", 100, "centimeters", "meters"),
    ("string", 100, "centimeters", "meters"),
]
_POUR_ITEMS = [
    ("bottle of juice", 1000, "milliliters", "liters", "glass"),
    ("carton of milk", 1000, "milliliters", "liters", "cup"),
    ("jug of water", 1000, "milliliters", "liters", "beaker"),
]


# ---------- the plain conversion ----------


def convert_up(rng: random.Random, lo: int, hi: int, *, table=None):
    """Big unit to small: 5 meters is how many centimeters?"""
    factor, small, big_one, big_many, _ = rng.choice(table or _CONVERSIONS_FULL)
    k = rng.randint(2, 9)
    return (
        ("meas_up", factor, small, k),
        f"How many {small} are in {k} {big_many}?",
        k * factor,
        f"1 {big_one} = {factor} {small}, so {k} {big_many} = {k} × {factor} "
        f"= {k * factor}! 📏",
    )


def convert_up_basic(rng: random.Random, lo: int, hi: int):
    return convert_up(rng, lo, hi, table=_CONVERSIONS_BASIC)


def convert_down(rng: random.Random, lo: int, hi: int):
    """Small unit to big: 24 feet is how many yards?"""
    factor, small, big_one, big_many, _ = rng.choice(_CONVERSIONS_FULL)
    k = rng.randint(2, 9)
    total = k * factor
    return (
        ("meas_down", factor, small, k),
        f"{total} {small} is how many {big_many}?",
        k,
        f"Divide by {factor}: {total} ÷ {factor} = {k} {big_many}! 📏",
    )


def convert_mixed(rng: random.Random, lo: int, hi: int):
    """2 meters and 30 centimeters is how many centimeters?"""
    factor, small, big_one, big_many, _ = rng.choice(
        [c for c in _CONVERSIONS_FULL if c[0] in (100, 60, 12)]
    )
    k = rng.randint(1, 5)
    extra = rng.randint(2, factor - 1)  # 2+, so it never reads "1 inches"
    big_word = big_one if k == 1 else big_many
    return (
        ("meas_mix", factor, small, k, extra),
        f"How many {small} is {k} {big_word} and {extra} {small}?",
        k * factor + extra,
        f"{k} × {factor} = {k * factor}, plus {extra} more = {k * factor + extra}! 📏",
    )


# ---------- knowing which unit fits ----------


def pick_the_unit(rng: random.Random, lo: int, hi: int):
    """Measuring is choosing a unit before it is doing any arithmetic."""
    thing, right, wrong = rng.choice(_UNIT_CHOICES)
    options = [right, *wrong]
    rng.shuffle(options)
    return (
        ("meas_unit", thing),
        f"Which unit would you use to measure {thing}?\n\n"
        + "\n".join(f"• {o}" for o in options),
        right,
        f"{thing.capitalize()} is measured in {right} — the others would give "
        f"a silly number. 📏",
    )


# ---------- comparing across units ----------


def compare_measures(rng: random.Random, lo: int, hi: int):
    """2 meters or 250 centimeters — which is more?"""
    factor, small, big_one, big_many, _ = rng.choice(
        [c for c in _CONVERSIONS_FULL if c[0] in (100, 1000, 10, 60)]
    )
    k = rng.randint(2, 6)
    big_value = k * factor
    if rng.random() < 0.2:
        small_value = big_value            # a genuine "=" case
    else:
        offset = rng.choice([-1, 1]) * rng.randint(1, max(2, factor // 2))
        small_value = max(1, big_value + offset)
    left, right = f"{k} {big_many}", f"{small_value} {small}"
    answer = "<" if big_value < small_value else (">" if big_value > small_value else "=")
    if rng.random() < 0.5:
        left, right = right, left
        answer = {"<": ">", ">": "<", "=": "="}[answer]
    return (
        ("meas_cmp", factor, k, small_value),
        f"Write <, > or = in the blank:\n\n{left} _ {right}",
        answer,
        f"Put both in {small}: {k} {big_many} = {big_value} {small}, "
        f"against {small_value} {small}. So {left} {answer} {right}. ⚖️",
    )


# ---------- convert, then do something with it ----------


def cut_into_pieces(rng: random.Random, lo: int, hi: int):
    """A 3 meter ribbon into 50 centimeter pieces — convert, then divide."""
    item, factor, small, big_many = rng.choice(_CUT_ITEMS)
    piece = rng.choice([20, 25, 50, 10, 4])
    whole = rng.randint(2, 6)
    total = whole * factor
    pieces = total // piece
    return (
        ("meas_cut", item, whole, piece),
        f"A {item} is {whole} {big_many} long. It is cut into pieces "
        f"{piece} {small} long.\n\nHow many pieces are there?",
        pieces,
        f"{whole} {big_many} = {total} {small}. {total} ÷ {piece} = {pieces} pieces! ✂️",
    )


def how_much_is_left(rng: random.Random, lo: int, hi: int):
    """Convert the big number down before you can take anything away."""
    item, factor, small, big_many, vessel = rng.choice(_POUR_ITEMS)
    whole = rng.randint(1, 3)
    total = whole * factor
    glasses = rng.randint(2, 5)
    each = rng.choice([50, 100, 125, 200, 250])
    poured = glasses * each
    if poured >= total:
        glasses, each = 2, 50
        poured = 100
    unit_word = big_many if whole > 1 else big_many[:-1]
    return (
        ("meas_left", item, whole, glasses, each),
        f"A {item} holds {whole} {unit_word}. {glasses} {vessel}s are poured "
        f"out, {each} {small} each.\n\nHow many {small} are left?",
        total - poured,
        f"{whole} {unit_word} = {total} {small}. Poured out: {glasses} × {each} "
        f"= {poured} {small}. Left: {total} - {poured} = {total - poured}! 🥤",
    )


# What can sensibly hold each kind of measurement — a jug holds liters,
# not kilometers.
# Only things a container can *hold* — length gets its own shapes
# (cut_into_pieces, total_laps), because a rope doesn't "hold" meters.
_VESSELS = {
    "volume": ("jug", "bottle", "carton"),
    "mass": ("sack", "bag", "box"),
}


def add_across_units(rng: random.Random, lo: int, hi: int):
    """Two amounts in different units — one has to move before adding."""
    factor, small, big_one, big_many, family = rng.choice(
        [c for c in _CONVERSIONS_FULL if c[0] in (1000, 100) and c[4] in _VESSELS]
    )
    vessel = rng.choice(_VESSELS[family])
    big_count = rng.randint(1, 3)
    small_count = rng.randint(2, 9) * (factor // 10 if factor >= 100 else 1)
    total = big_count * factor + small_count
    big_word = big_one if big_count == 1 else big_many
    return (
        ("meas_add", factor, big_count, small_count),
        f"One {vessel} holds {big_count} {big_word}. Another holds {small_count} {small}.\n\n"
        f"How many {small} is that altogether?",
        total,
        f"{big_count} {big_word} = {big_count * factor} {small}. "
        f"{big_count * factor} + {small_count} = {total} {small}! 📏",
    )


def total_laps(rng: random.Random, lo: int, hi: int):
    """Distance × repeats, with the units changing on the way."""
    laps = rng.randint(3, 8)
    meters = rng.choice([200, 250, 400, 500])
    total = laps * meters
    km, remainder = divmod(total, 1000)
    return (
        ("meas_laps", laps, meters),
        f"One lap of the running track is {meters} meters. A runner does "
        f"{laps} laps.\n\nHow many meters is that in total?",
        total,
        f"{laps} × {meters} = {total} meters"
        + (f" — that's {km} km and {remainder} m! 🏃" if km else "! 🏃"),
    )


TIERS = {
    # Grade 2: what the units are, and the plain conversion up.
    "basic": (convert_up_basic, pick_the_unit, convert_mixed),
    # Grade 3-4: both directions, and comparing across units.
    "convert": (convert_up, convert_down, convert_mixed, compare_measures, pick_the_unit),
    # Grade 4-5: converting is step one of two.
    "applied": (
        cut_into_pieces, how_much_is_left, add_across_units,
        total_laps, compare_measures, convert_down,
    ),
}


def tier_for(difficulty_is_easy: bool, difficulty_is_hard: bool, g: int) -> str:
    if g >= 5 or (g >= 4 and not difficulty_is_easy) or (g >= 3 and difficulty_is_hard):
        return "applied"
    if g >= 3 or not difficulty_is_easy:
        return "convert"
    return "basic"


def tier_factory(tier: str):
    return rotating(TIERS[tier], tier)
