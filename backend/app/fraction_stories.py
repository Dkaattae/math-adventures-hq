"""Fraction word problems: pizza, birthday cake and music.

The rest of word_problems.py keeps every answer a whole number. These
stories are the exception on purpose — "what part of the pizza does each
person get?" only has a fraction for an answer — so their answers are
simplest-form fractions ("1/8") or mixed numbers ("2 1/2"), which the
grader and the multiple-choice builder both understand.

Three families, each with a ladder:

* **Pizza** — eat some slices, what's left (grade 2); cut it in half, save
  half, share the rest (grade 3-5); a party's worth of pizzas as a mixed
  number (grade 5 hard).
* **Birthday cake** — friends each eat a few slices; what's left, or eaten.
* **Music** — note values are fractions of a whole note: how many 8th
  notes fit in a half note, how many beats a rhythm lasts, and (grade 5
  hard) converting a metronome marking from one note to another.

Builders take the same (rng, lo, hi, *, scale) as word_problems'. The
reading scale only decides whether a scene-setting sentence rides along.
"""
from __future__ import annotations

import random
from fractions import Fraction
from math import gcd

from .fraction_questions import mixed, pie, simplify

NAMES = (
    "Leo", "Maya", "Alex", "Priya", "Diego", "Hana", "Omar", "Freya", "Kofi",
    "Ines", "Sam", "Zoe", "Noah", "Ruby", "Theo", "Aisha", "Milo", "Clara",
)

_PIZZA_NOISE = (
    "It has extra cheese on top.",
    "The box says it is 12 inches across.",
    "It came out of the oven 5 minutes ago.",
    "Half of it has mushrooms.",
)
_CAKE_NOISE = (
    "The cake has 9 candles on it.",
    "It is a chocolate cake with blue icing.",
    "The party starts at 3 o'clock.",
)
_MUSIC_NOISE = (
    "The piece is 32 measures long.",
    "The concert is on Friday.",
    "The piece is written for piano.",
)


def _noise(rng: random.Random, pool, scale: str) -> str:
    """Sometimes one sentence the maths doesn't need (never at "short")."""
    if scale == "short" or rng.random() < 0.5:
        return ""
    return " " + rng.choice(pool)


# ---------- pizza ----------


def pizza_eaten(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Grade 2: count slices. The picture shows how the pizza is cut; the
    words say how many went. Eaten and left are both kept in lowest terms
    by choosing slices coprime with the cut."""
    slices = rng.choice([4, 5, 6, 8])
    eaten = rng.choice([n for n in range(1, slices) if gcd(n, slices) == 1])
    name = rng.choice(NAMES)
    ask_left = rng.random() < 0.5
    part = slices - eaten if ask_left else eaten
    ask = "What fraction of the pizza is left?" if ask_left else f"What fraction of the pizza did {name} eat?"
    return (
        ("fs_eaten", slices, eaten, ask_left),
        f"{name} cuts a pizza into {slices} equal slices and eats {eaten} of them."
        f"{_noise(rng, _PIZZA_NOISE, scale)} {ask}",
        f"{part}/{slices}",
        f"The pizza has {slices} slices, so each is 1/{slices}. "
        + (
            f"{slices} − {eaten} = {part} slice{' is' if part == 1 else 's are'} left: "
            if ask_left else f"{name} ate {eaten}: "
        )
        + f"{part}/{slices}. 🍕",
        pie(f"0/{slices}"),
    )


_PIECES = {2: "in half", 3: "into 3 equal parts", 4: "into 4 equal parts"}
_PIECE_WORD = {2: "half", 3: "third", 4: "quarter"}


def pizza_share(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Cut it into big pieces, keep some for tomorrow, share the rest:
    each person's share is a fraction of a fraction."""
    pieces = rng.choice([2, 2, 3, 4])
    shared = 1 if pieces == 2 else rng.randint(1, pieces - 1)
    saved = pieces - shared
    people = rng.randint(2, 5)
    name = rng.choice(NAMES)
    answer = simplify(shared, pieces * people)
    # Halves read naturally as "the other half"; thirds and quarters say
    # "the rest", so working out how much is shared is part of the job.
    word = _PIECE_WORD[pieces]
    if pieces == 2:
        saved_text, shared_text = "one half", "the other half"
    else:
        saved_text = f"one {word}" if saved == 1 else f"{saved} {word}s"
        shared_text = "the rest"
    return (
        ("fs_share", pieces, shared, people),
        f"{name} buys a pizza and cuts it {_PIECES[pieces]}. {name} saves {saved_text} "
        f"for tomorrow.{_noise(rng, _PIZZA_NOISE, scale)} {people} people share "
        f"{shared_text} equally. What fraction of the whole pizza does each person get? "
        f"(simplest form)",
        answer,
        f"They share {simplify(shared, pieces)} of the pizza. Split into {people} equal parts: "
        f"{shared}/{pieces} ÷ {people} = {shared}/{pieces * people}"
        + (f" = {answer}" if answer != f"{shared}/{pieces * people}" else "")
        + f". Check: {people} × {answer} = {simplify(shared, pieces)} of the pizza. 🍕",
    )


def pizza_party(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Grade 5 hard: several pizzas, slices eaten across all of them, and
    the amount as a mixed number of pizzas."""
    for _ in range(100):
        slices = rng.choice([6, 8, 10, 12])
        pizzas = rng.randint(3, 5)
        kids = rng.randint(4, 9)
        each = rng.randint(2, 3)
        eaten = kids * each
        left = pizzas * slices - eaten
        if (
            eaten > slices and eaten % slices and left > slices and left % slices
            # The question shows "1 1/2" as the format example.
            and "1 1/2" not in (mixed(eaten, slices), mixed(left, slices))
        ):
            break
    else:  # pragma: no cover - the ranges above always find one
        slices, pizzas, kids, each, eaten, left = 8, 3, 5, 2, 10, 14
    name = rng.choice(NAMES)
    ask_left = rng.random() < 0.5
    amount = left if ask_left else eaten
    answer = mixed(amount, slices)
    ask = (
        "How many pizzas are left over? Write it as a mixed number (e.g. 1 1/2)."
        if ask_left
        else "How many pizzas did the kids eat? Write it as a mixed number (e.g. 1 1/2)."
    )
    whole, rest = divmod(amount, slices)
    return (
        ("fs_party", slices, pizzas, kids, each, ask_left),
        f"{name} orders {pizzas} pizzas for a party, and each one is cut into {slices} "
        f"slices.{_noise(rng, _PIZZA_NOISE, scale)} {kids} kids eat {each} slices each. {ask}",
        answer,
        f"{kids} × {each} = {eaten} slices eaten"
        + (f", so {pizzas} × {slices} − {eaten} = {left} slices are left" if ask_left else "")
        + f". {amount} ÷ {slices} = {whole} R {rest}, so that's {whole} whole pizza"
        + ("s" if whole != 1 else "")
        + f" and {rest}/{slices} of another: {answer}. 🍕",
    )


# ---------- birthday cake ----------


def cake_left(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    for _ in range(100):
        slices = rng.choice([8, 10, 12, 16])
        friends = rng.randint(2, 5)
        each = rng.randint(1, 3)
        eaten = friends * each
        if eaten < slices:
            break
    name = rng.choice(NAMES)
    ask_left = rng.random() < 0.6
    part = slices - eaten if ask_left else eaten
    answer = simplify(part, slices)
    ask = "What fraction of the cake is left?" if ask_left else "What fraction of the cake did they eat?"
    return (
        ("fs_cake", slices, friends, each, ask_left),
        f"{name}'s birthday cake is cut into {slices} equal slices.{_noise(rng, _CAKE_NOISE, scale)} "
        f"{friends} friends each eat {each} slice{'s' if each != 1 else ''}. {ask} (simplest form)",
        answer,
        f"{friends} × {each} = {eaten} slices eaten"
        + (f", so {slices} − {eaten} = {part} are left" if ask_left else "")
        + f": {part}/{slices}"
        + (f" = {answer}" if answer != f"{part}/{slices}" else "")
        + ". 🎂",
    )


# ---------- music ----------

#: Note names and their length as a fraction of a whole note.
NOTES = {
    "whole": Fraction(1),
    "half": Fraction(1, 2),
    "quarter": Fraction(1, 4),
    "8th": Fraction(1, 8),
    "16th": Fraction(1, 16),
}


def _a(note: str) -> str:
    """"an 8th note", "a quarter note"."""
    return "an" if note[0] == "8" else "a"


def _frac(note: str) -> str:
    value = NOTES[note]
    return simplify(value.numerator, value.denominator)


def music_count(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """How many short notes fill a long one, or how many beats a rhythm
    lasts — note values are fractions of a whole note."""
    name = rng.choice(NAMES)
    if rng.random() < 0.5:
        long_, short = rng.choice([
            ("whole", "half"), ("whole", "quarter"), ("whole", "8th"),
            ("half", "quarter"), ("half", "8th"), ("half", "16th"),
            ("quarter", "8th"), ("quarter", "16th"), ("8th", "16th"),
        ])
        answer = int(NOTES[long_] / NOTES[short])
        facts = f"{_a(short)} {short} note is {_frac(short)} of a whole note"
        if long_ != "whole":
            facts = f"{_a(long_)} {long_} note is {_frac(long_)} of a whole note and " + facts[0].lower() + facts[1:]
        return (
            ("fs_notes", long_, short),
            f"{facts[0].upper() + facts[1:]}.{_noise(rng, _MUSIC_NOISE, scale)} "
            f"{name} wants to fill the time of one {long_} note with {short} notes. "
            f"How many {short} notes is that?",
            answer,
            f"{_frac(long_)} ÷ {_frac(short)} = {answer}. "
            f"Each {short} note is 1/{answer} of {_a(long_)} {long_} note. 🎵",
        )
    quarters = rng.randint(1, 4)
    eighths = 2 * rng.randint(1, 3)
    answer = quarters + eighths // 2
    return (
        ("fs_beats", quarters, eighths),
        f"In this song a quarter note gets 1 beat, so an 8th note gets 1/2 a beat."
        f"{_noise(rng, _MUSIC_NOISE, scale)} {name} plays {quarters} quarter note"
        f"{'s' if quarters != 1 else ''} and then {eighths} 8th notes. How many beats is that?",
        answer,
        f"{quarters} quarter note{'s' if quarters != 1 else ''} = {quarters} beat"
        f"{'s' if quarters != 1 else ''}. {eighths} 8th notes × 1/2 = {eighths // 2} beat"
        f"{'s' if eighths // 2 != 1 else ''}. {quarters} + {eighths // 2} = {answer} beats. 🎵",
    )


_METRONOME_PAIRS = (
    # (first marking's note, the note to convert to)
    ("16th", "8th"), ("8th", "quarter"), ("16th", "quarter"),
    ("8th", "16th"), ("quarter", "8th"), ("half", "quarter"),
)


def metronome(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Grade 5 hard: a tempo marking counts one kind of note per minute.
    Comparing two markings means converting one into the other's note.

    16th note = 150 means 150 sixteenth notes a minute; a 16th is half an
    8th, so that's 75 eighth notes a minute.
    """
    for _ in range(200):
        given, target = rng.choice(_METRONOME_PAIRS)
        ratio = NOTES[given] / NOTES[target]   # how many targets one given note is
        # Round markings like the ones printed in real music: the given
        # tempo is a multiple of 10, and the converted one lands on a 5.
        step = 10 * ratio.denominator // 2 if ratio.denominator > 1 else 10
        bpm = rng.randrange(60, 201, step)
        converted = bpm * ratio
        if converted.denominator == 1 and 40 <= converted <= 240:
            break
    converted = int(converted)
    name = rng.choice(NAMES)
    gap = rng.randint(2, 6) * 5
    second = converted + gap if converted - gap < 40 or rng.random() < 0.5 else converted - gap
    ask_compare = rng.random() < 0.5
    relation = "half" if ratio == Fraction(1, 2) else "twice" if ratio == 2 else (
        "a quarter" if ratio == Fraction(1, 4) else "4 times"
    )
    if ask_compare:
        answer = abs(second - converted)
        ask = (
            f"To compare, {name} changes the first marking into {target} notes per minute. "
            f"How many more {target} notes per minute is the faster marking?"
        )
        tail = (
            f" The other marking is {second}, so the difference is "
            f"{max(second, converted)} − {min(second, converted)} = {answer}."
        )
    else:
        answer = converted
        ask = (
            f"To compare the two speeds, {name} changes the first marking into {target} notes "
            f"per minute. How many {target} notes per minute is that?"
        )
        tail = (
            f" That's {'slower' if converted < second else 'faster'} than the second marking of {second}."
        )
    return (
        ("fs_metronome", given, target, bpm, second, ask_compare),
        f"{name}'s teacher asks for a piece to be played at {given} note = {bpm} bpm "
        f"(beats per minute). Later the music changes to {target} note = {second} bpm."
        f"{_noise(rng, _MUSIC_NOISE, scale)} {ask}",
        answer,
        f"{_a(given).capitalize()} {given} note is {relation} as long as {_a(target)} {target} note, so {bpm} {given} notes "
        f"take the same time as {bpm} × {ratio} = {converted} {target} notes.{tail} 🎵",
    )
