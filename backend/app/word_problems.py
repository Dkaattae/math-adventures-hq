"""Real-life word problems.

The first version of this topic was one-line templates with a name glued
on — "Maya has 9 apples and gives 2 away". Strip the words and the
arithmetic was untouched, so a fifth grader got a kindergarten task in a
longer sentence.

What makes ten questions feel different from each other is **shape**, not
vocabulary: twenty shopping lists are still one puzzle wearing twenty
coats. So the topic is built from six shapes, and a quiz rotates through
them rather than drawing at random:

1. `simple_*`   — one-sentence stories (K-1, where reading is the work)
2. `list_*`     — a categorised list; the answer needs part of it
3. `priced_*`   — quantity × price per line, then total / change / split
4. `tally_*`    — a scoring system stated as rules, then what happened
5. `deal_*`     — sale offers, where leftovers still pay full price
6. `choice_*`   — two ways to buy the same thing; which works out cheaper

Three things keep them from reading like a form:

* **Randomised noise.** Scene-setting facts appear *sometimes* — zero,
  one or two of them — so "the sentence before the question is always
  junk" isn't a rule a kid can learn. Noise built into the structure
  (list lines from the wrong aisle, a scoring rule nothing used) always
  stays: that's the puzzle, not decoration.
* **Rotated phrasing.** Openers and questions are drawn from several
  wordings each, so the same shape doesn't repeat the same sentence.
* **Rotated shapes.** `rotating()` deals from a shuffled deck of
  builders, so ten questions spread across the shapes available at that
  grade instead of clumping.

Conventions that keep answers typable on a phone: money is whole dollars,
quantities are whole and at least 2 (so no line reads "1 apples"), and
every answer is a plain non-negative integer.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from functools import partial
from typing import Callable

from .rotation import rotating

# A wide pool so a 10-question quiz rarely repeats a character. Each
# question mentions its name once, in the opening line.
NAMES = [
    "Maya", "Leo", "Ava", "Noah", "Zoe", "Sam", "Mia", "Eli", "Ruby", "Max",
    "Amara", "Priya", "Diego", "Hana", "Omar", "Freya", "Kofi", "Ines", "Yusuf", "Lena",
    "Marco", "Nina", "Tariq", "Sofia", "Jonas", "Aisha", "Bruno", "Elif", "Caleb", "Rosa",
    "Kai", "Dalia", "Milo", "Anya", "Idris", "Clara", "Nikhil", "Esme", "Theo", "Junko",
]


# ---------- reading scales ----------
#
# A 2nd grader and a 4th grader used to get the same 4-6 line list; only
# the arithmetic changed, the reading didn't. The maths level lives in
# the tier; the *reading* level lives here. Grades 1-2 get a short list
# with no scene-setting noise, grade 5 (above easy) gets a longer list
# with an extra distractor zone. The templates are the same — each scale
# just picks more or fewer items from the same scene.

SCALES = {
    "short": dict(target=(2, 2), other=(1, 2), third=False, facts=0,
                  priced=(2, 3), rule_used=(2, 2), deal_rest=(1, 1)),
    "standard": dict(target=(2, 3), other=(2, 3), third=False, facts=2,
                     priced=(3, 4), rule_used=(2, 3), deal_rest=(1, 2)),
    "long": dict(target=(3, 4), other=(2, 3), third=True, facts=2,
                 priced=(4, 5), rule_used=(2, 3), deal_rest=(2, 3)),
}


# ---------- shared helpers ----------

_TAX_NOTES = (
    "There is no tax to add.",
    "The prices already include everything.",
    "No tax, no delivery fee.",
)


def _cap(text: str) -> str:
    """Zone and item names read "the dairy case" mid-sentence but need a
    capital when an explanation starts with one."""
    return text[:1].upper() + text[1:]


def _noise(rng: random.Random, flavour, *, tax: bool = False, always=(),
           max_facts: int = 2) -> list[str]:
    """Up to `max_facts` scene-setting facts, chosen at random.

    Deliberately not always present: if every question ended with a
    throwaway sentence, ignoring the last sentence would become the
    trick. Sometimes there is nothing to ignore — and at the "short"
    reading scale (max_facts=0) there never is: a 1st grader gets the
    numbers and the question, full stop.
    """
    out: list[str] = []
    roll = rng.random()
    if flavour and max_facts > 0 and roll < 0.7:
        count = 2 if roll < 0.2 and len(flavour) > 1 and max_facts > 1 else 1
        out.extend(rng.sample(list(flavour), k=count))
    out.extend(always)
    if tax and rng.random() < 0.55:
        out.append(rng.choice(_TAX_NOTES))
    return out


def _bullets(lines) -> str:
    return "\n".join(f"• {line}" for line in lines)


def _offer_price(rng: random.Random, deal_n: int, low: int, high: int) -> int:
    """A "`deal_n` for $x" price that doesn't reduce to a round unit price.

    "2 for $2" is just "$1 each" wearing a costume — the kid never has to
    divide. Prefer a price the group size doesn't divide evenly.
    """
    candidates = [p for p in range(low, high + 1) if p % deal_n]
    return rng.choice(candidates) if candidates else rng.randint(low, high)


def _assemble(*blocks: str) -> str:
    """Join the non-empty blocks of a scene with blank lines."""
    return "\n\n".join(b for b in blocks if b)


# ---------- shape 1: one-sentence stories (K-1) ----------

_SIMPLE_ITEMS = [
    ("apples", "in the fruit bowl"), ("stickers", "in the album"),
    ("marbles", "in the jar"), ("crayons", "in the box"),
    ("shells", "in the bucket"), ("acorns", "in the basket"),
    ("toy cars", "on the shelf"), ("cookies", "on the plate"),
    ("pencils", "in the pot"), ("blocks", "in the tub"),
]


def simple_add(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    # The starting pile is always plural, so nothing reads "1 apples".
    a, b = rng.randint(2, max(3, hi)), rng.randint(lo, hi)
    name = rng.choice(NAMES)
    item, where = rng.choice(_SIMPLE_ITEMS)
    opener = rng.choice([
        f"There are {a} {item} {where}. {name} puts in {b} more.",
        f"{name} finds {a} {item} {where}, then adds {b} more.",
        f"{a} {item} are {where}. {name} drops in {b} more.",
    ])
    return (
        ("wp_add", min(a, b), max(a, b), item),
        f"{opener} How many {item} are there now?",
        a + b,
        f"{a} + {b} = {a + b}. Count on {b} more from {a}! 📖",
    )


def simple_sub(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    a = rng.randint(max(lo, 2), max(hi, 3))
    b = rng.randint(1, a)
    name = rng.choice(NAMES)
    item, where = rng.choice(_SIMPLE_ITEMS)
    opener = rng.choice([
        f"There are {a} {item} {where}. {name} takes {b} away.",
        f"{a} {item} are {where}. {name} gives {b} to a friend.",
        f"{name} counts {a} {item} {where}, then uses {b}.",
    ])
    return (
        ("wp_sub", a, b, item),
        f"{opener} How many {item} are left?",
        a - b,
        f"{a} - {b} = {a - b}. Take away {b} from {a}! 📖",
    )


def simple_groups(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    groups = rng.randint(2, max(3, hi // 3))
    each = rng.randint(2, max(3, hi // 2))
    item, _ = rng.choice(_SIMPLE_ITEMS)
    holder = rng.choice(["boxes", "bags", "jars", "baskets"])
    return (
        ("wp_mul", groups, each, item),
        f"There are {groups} {holder} with {each} {item} in each one. "
        f"How many {item} in all?",
        groups * each,
        f"{groups} {holder} × {each} each = {groups * each}. "
        f"That's {groups} groups of {each}! 📖",
    )


def simple_share(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    friends = rng.randint(2, max(3, hi // 3))
    each = rng.randint(2, max(3, hi // 2))
    total = friends * each
    name = rng.choice(NAMES)
    item, _ = rng.choice(_SIMPLE_ITEMS)
    return (
        ("wp_div", total, friends, item),
        f"{name} shares {total} {item} equally between {friends} friends. "
        f"How many does each friend get?",
        each,
        f"{total} ÷ {friends} = {each}. Everyone gets a fair share! 📖",
    )


# ---------- shape 2 & 3: lists, with or without prices ----------


@dataclass(frozen=True)
class Zone:
    """One section of a list: a place, and the things found there."""

    short: str                  # "the produce aisle"
    described: str              # "the produce aisle, where the fruit and vegetables are"
    items: tuple[str, ...]      # plural phrases: "apples", "loaves of bread"


@dataclass(frozen=True)
class CountScene:
    key: str
    list_name: str              # "shopping list"
    unit: str                   # "items" / "books" / "animals"
    zones: tuple[Zone, ...]
    flavour: tuple[str, ...]    # true, irrelevant facts


COUNT_SCENES: tuple[CountScene, ...] = (
    CountScene(
        key="grocery", list_name="shopping list", unit="items",
        zones=(
            Zone("the produce aisle", "the produce aisle, where the fruit and vegetables are",
                 ("apples", "bananas", "carrots", "potatoes", "oranges", "tomatoes", "peppers")),
            Zone("the bakery counter", "the bakery counter",
                 ("bagels", "muffins", "loaves of bread", "dinner rolls", "croissants")),
            Zone("the dairy case", "the dairy case",
                 ("yogurt cups", "cheese sticks", "milk cartons", "sticks of butter")),
        ),
        flavour=(
            "The store opens at 8 in the morning.",
            "There are 12 checkout lanes at the front.",
            "The cart has one wobbly wheel.",
            "It is raining outside.",
        ),
    ),
    CountScene(
        key="supplies", list_name="classroom supply order", unit="supplies",
        zones=(
            Zone("the art cupboard", "the art cupboard",
                 ("paintbrushes", "glue sticks", "boxes of crayons", "sheets of card", "paint pots")),
            Zone("the writing drawer", "the writing drawer",
                 ("pencils", "erasers", "notebooks", "pens", "rulers")),
            Zone("the cleaning shelf", "the cleaning shelf",
                 ("sponges", "rolls of paper towel", "bottles of soap")),
        ),
        flavour=(
            "The order arrives on a Tuesday.",
            "There are 24 children in the class.",
            "The cupboard has 3 shelves.",
        ),
    ),
    CountScene(
        key="library", list_name="library cart", unit="books",
        zones=(
            Zone("the picture-book bin", "the picture-book bin near the door",
                 ("picture books", "board books", "alphabet books")),
            Zone("the chapter-book shelf", "the chapter-book shelf",
                 ("mystery books", "adventure books", "poetry books", "fairy tale books")),
            Zone("the fact-book corner", "the fact-book corner",
                 ("dinosaur books", "space books", "atlases", "cookbooks")),
        ),
        flavour=(
            "The library closes at 6 o'clock.",
            "The cart has 2 squeaky wheels.",
            "Books are due back in 3 weeks.",
        ),
    ),
    CountScene(
        key="camping", list_name="camping packing list", unit="things",
        zones=(
            Zone("the kitchen box", "the kitchen box",
                 ("plates", "forks", "cooking pots", "water bottles", "mugs")),
            Zone("the sleeping pile", "the pile of sleeping gear",
                 ("sleeping bags", "pillows", "blankets", "camping mats")),
            Zone("the clothes bag", "the clothes bag",
                 ("jackets", "hats", "pairs of socks", "pairs of boots")),
        ),
        flavour=(
            "The drive to the campsite takes 2 hours.",
            "The tent sleeps 4 people.",
            "The trip lasts 3 nights.",
        ),
    ),
    CountScene(
        key="shelter", list_name="animal shelter list", unit="animals",
        zones=(
            Zone("the dog run", "the dog run out the back",
                 ("puppies", "beagles", "spaniels", "sheepdogs")),
            Zone("the cat room", "the cat room",
                 ("kittens", "tabby cats", "ginger cats", "black cats")),
            Zone("the small pet corner", "the small pet corner",
                 ("rabbits", "guinea pigs", "hamsters")),
        ),
        flavour=(
            "There are 5 volunteers on Saturday.",
            "Feeding time is at 7 in the morning.",
            "The shelter has been open for 20 years.",
        ),
    ),
    CountScene(
        key="bakesale", list_name="bake sale table", unit="things",
        zones=(
            Zone("the sweet tray", "the sweet tray",
                 ("cookies", "brownies", "cupcakes", "flapjacks")),
            Zone("the drinks cooler", "the drinks cooler",
                 ("juice boxes", "cups of lemonade", "bottles of water")),
            Zone("the savoury basket", "the savoury basket",
                 ("pretzels", "cheese crackers", "bread sticks")),
        ),
        flavour=(
            "The sale starts right after lunch.",
            "The table is 2 meters long.",
            "The money goes to the school garden.",
        ),
    ),
    CountScene(
        key="garden", list_name="garden centre trolley", unit="things",
        zones=(
            Zone("the flower beds", "the flower beds",
                 ("rose bushes", "sunflower seedlings", "tulip bulbs", "daisy plants")),
            Zone("the vegetable patch", "the vegetable patch",
                 ("tomato plants", "pepper plants", "lettuce seedlings", "bean plants")),
            Zone("the tool rack", "the tool rack",
                 ("trowels", "watering cans", "pairs of gloves")),
        ),
        flavour=(
            "The garden centre is open until 5.",
            "The garden gets sun all afternoon.",
            "It rained yesterday.",
        ),
    ),
    CountScene(
        key="sports", list_name="equipment room list", unit="things",
        zones=(
            Zone("the football bin", "the football bin",
                 ("footballs", "cones", "pairs of shin pads", "bibs")),
            Zone("the basketball rack", "the basketball rack",
                 ("basketballs", "hoop nets", "whistles")),
            Zone("the swimming crate", "the swimming crate",
                 ("kickboards", "pairs of goggles", "swim caps")),
        ),
        flavour=(
            "Practice starts at 4 o'clock.",
            "The team has 11 players.",
            "The room is next to the gym.",
        ),
    ),
)


@dataclass(frozen=True)
class PricedScene:
    key: str
    place: str                                  # "basket at the farmers market"
    items: tuple[tuple[str, int, int], ...]     # (plural phrase, min $, max $)
    flavour: tuple[str, ...]


PRICED_SCENES: tuple[PricedScene, ...] = (
    PricedScene(
        key="market", place="basket at the farmers market",
        items=(
            ("peaches", 2, 4), ("jars of honey", 5, 8), ("ears of corn", 1, 2),
            ("bunches of kale", 2, 4), ("loaves of bread", 3, 5), ("wedges of cheese", 6, 9),
        ),
        flavour=(
            "The market opens at 8 in the morning.",
            "There are 30 stalls at the market.",
            "The walk home takes 15 minutes.",
        ),
    ),
    PricedScene(
        key="bookfair", place="pile at the school book fair",
        items=(
            ("paperback books", 4, 6), ("hardback books", 8, 12), ("posters", 2, 4),
            ("bookmarks", 1, 2), ("sticker sheets", 2, 3), ("notebooks", 3, 5),
        ),
        flavour=(
            "The fair runs for 4 days.",
            "The hall has 6 long tables.",
            "A teacher stamps every receipt.",
        ),
    ),
    PricedScene(
        key="petshop", place="trolley at the pet shop",
        items=(
            ("bags of dog food", 10, 14), ("chew toys", 4, 6), ("bags of cat litter", 7, 9),
            ("catnip mice", 2, 3), ("tubs of fish flakes", 3, 5), ("bird feeders", 6, 9),
        ),
        flavour=(
            "The shop has a parrot called Biscuit.",
            "The shop is 10 minutes from home.",
            "The trolley squeaks.",
        ),
    ),
    PricedScene(
        key="hardware", place="list for building a bookshelf",
        items=(
            ("wooden planks", 5, 8), ("boxes of screws", 3, 5), ("tins of paint", 9, 13),
            ("paintbrushes", 2, 4), ("sheets of sandpaper", 1, 2), ("metal brackets", 2, 4),
        ),
        flavour=(
            "The bookshelf will go in the hallway.",
            "The shop closes at 6 o'clock.",
            "The job should take a whole Saturday.",
        ),
    ),
    PricedScene(
        key="craft", place="basket at the craft shop",
        items=(
            ("balls of yarn", 4, 6), ("packs of beads", 3, 5), ("sheets of felt", 1, 2),
            ("bottles of glitter glue", 2, 3), ("pairs of scissors", 5, 7), ("rolls of ribbon", 2, 4),
        ),
        flavour=(
            "The shop is on the corner.",
            "The craft club meets on Thursdays.",
            "There are 8 people in the club.",
        ),
    ),
    PricedScene(
        key="lunch", place="order at the food truck",
        items=(
            ("sandwiches", 6, 8), ("bowls of soup", 4, 6), ("fruit cups", 2, 4),
            ("bottles of water", 1, 2), ("cookies", 1, 3), ("bags of crisps", 2, 3),
        ),
        flavour=(
            "The queue is 9 people long.",
            "The truck parks by the park gates.",
            "Lunch break is 40 minutes.",
        ),
    ),
    PricedScene(
        key="party", place="party supply list",
        items=(
            ("packs of balloons", 3, 5), ("packs of paper plates", 2, 4), ("banners", 5, 7),
            ("packs of party hats", 2, 3), ("bags of sweets", 3, 5), ("party bags", 1, 2),
        ),
        flavour=(
            "The party starts at 3 o'clock.",
            "14 friends are invited.",
            "The party lasts 2 hours.",
        ),
    ),
    PricedScene(
        key="camping_shop", place="cart at the camping shop",
        items=(
            ("torches", 6, 9), ("packs of batteries", 3, 5), ("camping mugs", 2, 4),
            ("tent pegs", 1, 2), ("sleeping mats", 8, 12), ("gas canisters", 4, 6),
        ),
        flavour=(
            "The campsite is by a lake.",
            "The shop has a climbing wall inside.",
            "The trip starts on Friday.",
        ),
    ),
)


# Openers stay possessive so they read correctly for every scene noun —
# "shopping list", "trolley at the pet shop" and "list for building a
# bookshelf" all have to fit the same slot.
_LIST_OPENERS = (
    "{name}'s {noun}",
    "Here is {name}'s {noun}",
    "{name}'s {noun} today",
    "Look at {name}'s {noun}",
)


def _opener(rng: random.Random, name: str, noun: str) -> str:
    return rng.choice(_LIST_OPENERS).format(name=name, noun=noun) + ":"


def _count_lines(rng: random.Random, zone: Zone, count: int, hi: int):
    """`count` distinct items from a zone, each with a plural quantity."""
    chosen = rng.sample(zone.items, k=min(count, len(zone.items)))
    return [(item, rng.randint(2, max(3, min(9, hi)))) for item in chosen]


def _list_scene(rng: random.Random, hi: int, scale: str):
    """Shared setup for every list question: a scene, two zones, lines.

    At the "long" scale a third zone joins the list purely as extra
    sifting; its lines count as "not the target zone" but never appear
    in the question's own comparison.
    """
    cfg = SCALES[scale]
    scene = rng.choice(COUNT_SCENES)
    zones = list(scene.zones)
    rng.shuffle(zones)
    target, other = zones[0], zones[1]
    name = rng.choice(NAMES)
    target_lines = _count_lines(rng, target, rng.randint(*cfg["target"]), hi)
    other_lines = _count_lines(rng, other, rng.randint(*cfg["other"]), hi)
    extra_lines = (
        _count_lines(rng, zones[2], rng.randint(2, 3), hi)
        if cfg["third"] and len(zones) > 2
        else []
    )
    all_lines = target_lines + other_lines + extra_lines
    rng.shuffle(all_lines)
    lines = [f"{qty} {item}" for item, qty in all_lines]
    return scene, name, target, other, target_lines, other_lines + extra_lines, lines


def _list_question(rng, scene, name, lines, ask, answer, explanation, variant, target,
                   scale):
    signature = ("wp_list", scene.key, variant, target.short, tuple(sorted(lines)), answer)
    text = _assemble(
        _opener(rng, name, scene.list_name),
        _bullets(lines),
        " ".join(_noise(rng, scene.flavour, max_facts=SCALES[scale]["facts"])),
        ask,
    )
    return signature, text, answer, explanation


def list_count(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """How many of the list belong in one section?"""
    scene, name, target, other, target_lines, _, lines = _list_scene(rng, hi, scale)
    total = sum(q for _, q in target_lines)
    ask = rng.choice([
        f"Counting every single one, how many {scene.unit} on the list come from {target.described}?",
        f"How many {scene.unit} on the list belong in {target.short}?",
        f"Standing at {target.described}, how many {scene.unit} from the list go in the basket?",
    ])
    sums = " + ".join(str(q) for _, q in target_lines)
    explanation = (
        f"Only the {target.short} lines count: {sums} = {total}. "
        f"The rest of the list belongs somewhere else! 🛒"
    )
    return _list_question(
        rng, scene, name, lines, ask, total, explanation, "count", target, scale
    )


def list_outside(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """How much of the list is *not* in one section?"""
    scene, name, target, other, _, other_lines, lines = _list_scene(rng, hi, scale)
    total = sum(q for _, q in other_lines)
    ask = rng.choice([
        f"How many {scene.unit} on the list do NOT come from {target.short}?",
        f"Everything except {target.short} — how many {scene.unit} is that?",
    ])
    sums = " + ".join(str(q) for _, q in other_lines)
    explanation = f"Everything except the {target.short} lines: {sums} = {total}. 🛒"
    return _list_question(
        rng, scene, name, lines, ask, total, explanation, "outside", target, scale
    )


def list_difference(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """How many more come from one section than another?

    The comparison is target vs the named other zone; at the "long"
    scale the third zone's lines sit in the list purely as distractors,
    so they are excluded from both sides here.
    """
    scene, name, target, other, target_lines, all_other, lines = _list_scene(rng, hi, scale)
    other_lines = [
        (item, qty) for item, qty in all_other if item in other.items
    ]
    t_total = sum(q for _, q in target_lines)
    o_total = sum(q for _, q in other_lines)
    if t_total == o_total:  # a 0 answer makes a limp question
        return list_count(rng, lo, hi, scale=scale)
    big, small = (target, other) if t_total > o_total else (other, target)
    big_total, small_total = max(t_total, o_total), min(t_total, o_total)
    answer = big_total - small_total
    ask = rng.choice([
        f"How many more {scene.unit} come from {big.short} than from {small.short}?",
        f"{_cap(big.short)} has how many more {scene.unit} on this list than {small.short}?",
    ])
    explanation = (
        f"{_cap(big.short)}: {big_total}. {_cap(small.short)}: {small_total}. "
        f"{big_total} - {small_total} = {answer}. 🛒"
    )
    return _list_question(
        rng, scene, name, lines, ask, answer, explanation, "difference", target, scale
    )


# ---------- shape 3: priced lists ----------


def _priced_lines(rng: random.Random, scene: PricedScene, count: int):
    chosen = rng.sample(scene.items, k=min(count, len(scene.items)))
    return [(item, rng.randint(2, 5), rng.randint(lo, hi)) for item, lo, hi in chosen]


def _priced_scene(rng: random.Random, scale: str = "standard"):
    scene = rng.choice(PRICED_SCENES)
    name = rng.choice(NAMES)
    entries = _priced_lines(rng, scene, rng.randint(*SCALES[scale]["priced"]))
    lines = [f"{qty} {item} — ${price} each" for item, qty, price in entries]
    totals = [qty * price for _, qty, price in entries]
    return scene, name, entries, lines, totals, sum(totals)


def _priced_question(rng, scene, name, lines, extras, ask, answer, explanation, variant):
    signature = ("wp_priced", scene.key, variant, tuple(sorted(lines)), answer)
    text = _assemble(
        _opener(rng, name, scene.place),
        _bullets(lines),
        " ".join(extras),
        ask,
    )
    return signature, text, answer, explanation


def priced_total(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    scene, name, entries, lines, totals, total = _priced_scene(rng, scale)
    extras = _noise(rng, scene.flavour, tax=True, max_facts=SCALES[scale]["facts"])
    ask = rng.choice([
        "How many dollars does the whole list cost?",
        "How many dollars is everything altogether?",
        "What is the total, in dollars?",
    ])
    workings = " + ".join(f"{qty} × ${price}" for _, qty, price in entries)
    explanation = f"{workings} = {' + '.join(str(t) for t in totals)} = ${total}. 🧾"
    return _priced_question(rng, scene, name, lines, extras, ask, total, explanation, "total")


def priced_change(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    scene, name, entries, lines, totals, total = _priced_scene(rng, scale)
    note = next(n for n in (20, 50, 100, 200) if n > total)
    extras = _noise(rng, scene.flavour, tax=True, max_facts=SCALES[scale]["facts"],
                    always=[f"{name} pays with a ${note} note."])
    ask = rng.choice([
        "How many dollars of change come back?",
        "How much change is there, in dollars?",
    ])
    explanation = (
        f"The list costs {' + '.join(str(t) for t in totals)} = ${total}. "
        f"${note} - ${total} = ${note - total} change. 🧾"
    )
    return _priced_question(
        rng, scene, name, lines, extras, ask, note - total, explanation, "change"
    )


def priced_split(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Splitting the bill keeps division in the upper tiers."""
    scene, name, entries, lines, totals, total = _priced_scene(rng, scale)
    friends = _divisor_for(total, rng)
    if friends is None:  # no tidy split — ask the plain total instead
        return priced_total(rng, lo, hi, scale=scale)
    extras = _noise(rng, scene.flavour, tax=True, max_facts=SCALES[scale]["facts"],
                    always=[f"{friends} friends share the cost equally."])
    ask = rng.choice([
        "How many dollars does each friend pay?",
        "Split evenly, how many dollars is that each?",
    ])
    answer = total // friends
    explanation = (
        f"The list costs {' + '.join(str(t) for t in totals)} = ${total}. "
        f"${total} ÷ {friends} = ${answer} each. 🧾"
    )
    return _priced_question(rng, scene, name, lines, extras, ask, answer, explanation, "split")


def priced_difference(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    scene, name, entries, lines, totals, total = _priced_scene(rng, scale)
    ranked = sorted(entries, key=lambda e: e[1] * e[2], reverse=True)
    (item_a, qty_a, price_a), (item_b, qty_b, price_b) = ranked[0], ranked[-1]
    if qty_a * price_a == qty_b * price_b:
        return priced_total(rng, lo, hi, scale=scale)
    extras = _noise(rng, scene.flavour, tax=True, max_facts=SCALES[scale]["facts"])
    answer = qty_a * price_a - qty_b * price_b
    ask = rng.choice([
        f"How many dollars more do the {item_a} cost than the {item_b}?",
        f"What is the difference in dollars between the {item_a} and the {item_b}?",
    ])
    explanation = (
        f"{_cap(item_a)}: {qty_a} × ${price_a} = ${qty_a * price_a}. "
        f"{_cap(item_b)}: {qty_b} × ${price_b} = ${qty_b * price_b}. "
        f"${qty_a * price_a} - ${qty_b * price_b} = ${answer}. 🧾"
    )
    return _priced_question(
        rng, scene, name, lines, extras, ask, answer, explanation, "difference"
    )


def _divisor_for(total: int, rng: random.Random):
    options = [n for n in (2, 3, 4, 5, 6) if total % n == 0]
    return rng.choice(options) if options else None


# ---------- shape 4: rules & tallies ----------


@dataclass(frozen=True)
class RuleScene:
    """A scoring system spelled out, then a record of what happened.

    The rules are stated because a kid who has never watched football
    can't be expected to know a touchdown is 6 — and because listing one
    rule the question doesn't use puts the distractor inside the
    structure instead of in a throwaway sentence.
    """

    key: str
    intro: str                                  # "{name} plays for the Tigers."
    rules_lead: str                             # "How football scoring works:"
    record: str                                 # "the score sheet"
    verb: str                                   # "scored"
    unit: str                                   # "points"
    rules: tuple[tuple[str, str, int], ...]     # (plural, singular, value)
    flavour: tuple[str, ...]


RULE_SCENES: tuple[RuleScene, ...] = (
    RuleScene(
        key="football", intro="{name} plays for the Tigers football team.",
        rules_lead="How football scoring works:", record="the score sheet",
        verb="scored", unit="points",
        rules=(("touchdowns", "touchdown", 6), ("field goals", "field goal", 3),
               ("safeties", "safety", 2), ("extra points", "extra point", 1)),
        flavour=("The game was played on Saturday.", "It rained all afternoon.",
                 "There were 4 quarters."),
    ),
    RuleScene(
        key="basketball", intro="{name} plays in the Sunday basketball league.",
        rules_lead="How basketball scoring works:", record="the score sheet",
        verb="scored", unit="points",
        rules=(("three-pointers", "three-pointer", 3), ("baskets", "basket", 2),
               ("free throws", "free throw", 1)),
        flavour=("The game lasts 4 quarters.", "The court is next to the pool.",
                 "The team wears blue."),
    ),
    RuleScene(
        key="arcade", intro="{name} spent Saturday afternoon at the arcade.",
        rules_lead="Tickets each game pays out:", record="the ticket counter",
        verb="won", unit="tickets",
        rules=(("skee-ball games", "skee-ball game", 12), ("hoop shots", "hoop shot", 8),
               ("claw grabs", "claw grab", 25), ("air hockey wins", "air hockey win", 5)),
        flavour=("The arcade is open until 9.", "A big prize costs 500 tickets.",
                 "The machines are very loud."),
    ),
    RuleScene(
        key="recycling", intro="{name} took the recycling to the deposit machine.",
        rules_lead="What the machine pays back:", record="the receipt",
        verb="returned", unit="cents",
        rules=(("small bottles", "small bottle", 10), ("cans", "can", 5),
               ("big bottles", "big bottle", 25), ("glass jars", "glass jar", 15)),
        flavour=("The machine is outside the supermarket.", "The bag was heavy.",
                 "The machine beeps for every item."),
    ),
    RuleScene(
        key="reading", intro="{name} joined the summer reading challenge.",
        rules_lead="Points each book is worth:", record="the reading log",
        verb="read", unit="points",
        rules=(("chapter books", "chapter book", 5), ("picture books", "picture book", 2),
               ("comic books", "comic book", 1), ("fact books", "fact book", 3)),
        flavour=("The challenge runs all summer.", "A prize is given out in September.",
                 "The library is open on Sundays."),
    ),
    RuleScene(
        key="housepoints", intro="{name} is in Oak house at school.",
        rules_lead="How house points are given:", record="the house chart",
        verb="earned", unit="points",
        rules=(("finished homeworks", "finished homework", 5), ("tidy desks", "tidy desk", 2),
               ("good deeds", "good deed", 3), ("neat handwritings", "neat handwriting", 1)),
        flavour=("There are 4 houses in the school.", "Points are counted on Fridays.",
                 "The winning house gets an extra playtime."),
    ),
    RuleScene(
        key="scouts", intro="{name} is collecting scout badges.",
        rules_lead="Points each badge is worth:", record="the badge sash",
        verb="earned", unit="points",
        rules=(("first aid badges", "first aid badge", 15), ("hiking badges", "hiking badge", 10),
               ("cooking badges", "cooking badge", 8), ("swimming badges", "swimming badge", 12)),
        flavour=("Scouts meet on Wednesday evenings.", "The campfire is at 8.",
                 "The sash is dark green."),
    ),
    RuleScene(
        key="sportsday", intro="{name} took part in sports day.",
        rules_lead="Points for each race:", record="the score card",
        verb="won", unit="points",
        rules=(("first places", "first place", 5), ("second places", "second place", 3),
               ("third places", "third place", 1)),
        flavour=("Sports day is in June.", "There were 6 races in total.",
                 "Parents watched from the field."),
    ),
    RuleScene(
        key="funfair", intro="{name} went to the funfair with tokens to spend.",
        rules_lead="Tokens each ride costs:", record="the ride card",
        verb="used", unit="tokens",
        rules=(("roller coaster rides", "roller coaster ride", 6), ("carousel rides", "carousel ride", 2),
               ("bumper car rides", "bumper car ride", 4), ("ghost train rides", "ghost train ride", 5)),
        flavour=("The funfair is in town for a week.", "The big wheel is 30 meters tall.",
                 "The fair closes at 10."),
    ),
    RuleScene(
        key="boardgame", intro="{name} finished a long board game.",
        rules_lead="What each treasure is worth:", record="the treasure pile",
        verb="collected", unit="points",
        rules=(("gems", "gem", 10), ("gold coins", "gold coin", 5),
               ("silver coins", "silver coin", 3), ("map pieces", "map piece", 2)),
        flavour=("The game took 2 hours.", "There were 4 players.",
                 "The board is made of wood."),
    ),
    RuleScene(
        key="chores", intro="{name} keeps a chore chart on the fridge.",
        rules_lead="Stars each chore is worth:", record="the chore chart",
        verb="earned", unit="stars",
        rules=(("laundry loads", "laundry load", 4), ("washed-up dinners", "washed-up dinner", 3),
               ("swept floors", "swept floor", 2), ("walked dogs", "walked dog", 5)),
        flavour=("Stars are counted on Sunday night.", "The chart is held up by 2 magnets.",
                 "10 stars means a trip to the park."),
    ),
    RuleScene(
        key="birdwatch", intro="{name} spent the morning bird watching.",
        rules_lead="Points the club gives for each bird:", record="the spotting sheet",
        verb="spotted", unit="points",
        rules=(("robins", "robin", 2), ("woodpeckers", "woodpecker", 8),
               ("herons", "heron", 12), ("sparrows", "sparrow", 1)),
        flavour=("The walk started at 7 in the morning.", "The hide holds 6 people.",
                 "It was cold and clear."),
    ),
)


def _rule_setup(rng: random.Random, hi: int, *, used: int = 2, max_value: int | None = None):
    """A scene, its rules, and how many of each thing happened.

    Always lists more rules than the question uses, so there's a
    distractor baked into the structure rather than bolted on as a
    throwaway sentence.

    `max_value` keeps the lower grades away from 25-tickets-a-go scoring:
    only scenes with enough small-value rules are eligible.
    """
    scenes = RULE_SCENES
    if max_value is not None:
        scenes = tuple(
            s for s in RULE_SCENES
            if len([r for r in s.rules if r[2] <= max_value]) >= max(3, used + 1)
        )
    scene = rng.choice(scenes)
    name = rng.choice(NAMES)
    rules = [r for r in scene.rules if max_value is None or r[2] <= max_value]
    shown = rng.sample(rules, k=min(len(rules), max(3, used + 1)))
    # Always leave at least one rule unused: that spare rule *is* the
    # distractor. A scene with only three rules therefore uses two.
    used = min(used, len(shown) - 1)
    chosen = shown[:used]
    counts = [rng.randint(2, max(3, min(6, hi))) for _ in chosen]
    rules_block = _bullets(
        # "1 point", not "1 points" — every unit here is a plural noun.
        f"{_cap(singular)} — {value} {scene.unit[:-1] if value == 1 else scene.unit}"
        for _, singular, value in shown
    )
    return scene, name, shown, chosen, counts, rules_block


def _rule_question(rng, scene, name, rules_block, event, ask, answer, explanation, variant,
                   key, scale="standard"):
    signature = ("wp_rules", scene.key, variant, key, answer)
    text = _assemble(
        scene.intro.format(name=name),
        f"{scene.rules_lead}\n{rules_block}",
        " ".join(_noise(rng, scene.flavour, always=[event],
                        max_facts=SCALES[scale]["facts"])),
        ask,
    )
    return signature, text, answer, explanation


def tally_total(rng: random.Random, lo: int, hi: int, *, max_value: int | None = None,
                scale: str = "standard"):
    """Rules stated, then a tally: multiply each and add up."""
    scene, name, shown, chosen, counts, rules_block = _rule_setup(
        rng, hi, used=rng.randint(*SCALES[scale]["rule_used"]), max_value=max_value
    )
    parts = [f"{c} {plural}" for (plural, _, _), c in zip(chosen, counts)]
    event = (
        f"{_cap(scene.record)} shows "
        + (", ".join(parts[:-1]) + f" and {parts[-1]}" if len(parts) > 1 else parts[0])
        + "."
    )
    answer = sum(c * value for (_, _, value), c in zip(chosen, counts))
    ask = rng.choice([
        f"How many {scene.unit} is that altogether?",
        f"How many {scene.unit} in total?",
        f"Adding it all up, how many {scene.unit}?",
    ])
    workings = " + ".join(
        f"{c} × {value}" for (_, _, value), c in zip(chosen, counts)
    )
    explanation = (
        f"{workings} = {answer} {scene.unit}. "
        f"The other rule wasn't needed this time! 🏅"
    )
    key = tuple((p, c) for (p, _, _), c in zip(chosen, counts))
    return _rule_question(
        rng, scene, name, rules_block, event, ask, answer, explanation, "total", key, scale
    )


def tally_difference(rng: random.Random, lo: int, hi: int, *, max_value: int | None = None,
                     scale: str = "standard"):
    """Which kind was worth more, and by how much?"""
    scene, name, shown, chosen, counts, rules_block = _rule_setup(
        rng, hi, used=2, max_value=max_value
    )
    (plural_a, _, value_a), (plural_b, _, value_b) = chosen
    total_a, total_b = counts[0] * value_a, counts[1] * value_b
    if total_a == total_b:
        return tally_total(rng, lo, hi, max_value=max_value, scale=scale)
    event = f"{_cap(scene.record)} shows {counts[0]} {plural_a} and {counts[1]} {plural_b}."
    if total_a > total_b:
        big_name, small_name, big, small = plural_a, plural_b, total_a, total_b
    else:
        big_name, small_name, big, small = plural_b, plural_a, total_b, total_a
    answer = big - small
    ask = rng.choice([
        f"How many more {scene.unit} came from the {big_name} than the {small_name}?",
        f"What is the difference in {scene.unit} between the {big_name} and the {small_name}?",
    ])
    explanation = (
        f"{_cap(plural_a)}: {counts[0]} × {value_a} = {total_a}. "
        f"{_cap(plural_b)}: {counts[1]} × {value_b} = {total_b}. "
        f"{big} - {small} = {answer} {scene.unit}. 🏅"
    )
    key = ((plural_a, counts[0]), (plural_b, counts[1]))
    return _rule_question(
        rng, scene, name, rules_block, event, ask, answer, explanation, "difference", key, scale
    )


def tally_missing(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Total known, one kind only — how many were there? (division)"""
    scene, name, shown, chosen, counts, rules_block = _rule_setup(rng, hi, used=1)
    (plural, singular, value) = chosen[0]
    count = counts[0]
    total = count * value
    event = f"{_cap(scene.record)} shows {total} {scene.unit}, all from {plural}."
    answer = count
    ask = rng.choice([
        f"How many {plural} was that?",
        f"How many {plural} does that mean?",
    ])
    explanation = (
        f"Each {singular} is worth {value} {scene.unit}, so "
        f"{total} ÷ {value} = {answer} {plural}. 🏅"
    )
    return _rule_question(
        rng, scene, name, rules_block, event, ask, answer, explanation, "missing",
        (plural, total), scale
    )


# ---------- shape 5: sale offers ----------


def _deal_cost(qty: int, unit: int, deal_n: int, deal_price: int) -> int:
    """"`deal_n` for $`deal_price`" — leftovers still pay full price."""
    groups, left = divmod(qty, deal_n)
    return groups * deal_price + left * unit


def _free_cost(qty: int, unit: int, buy_n: int) -> int:
    """"Buy `buy_n`, get one free" — one item in every buy_n+1 is free."""
    free = qty // (buy_n + 1)
    return (qty - free) * unit


def _deal_setup(rng: random.Random, scale: str = "standard"):
    """One line on offer, the rest at plain prices."""
    scene = rng.choice(PRICED_SCENES)
    name = rng.choice(NAMES)
    entries = _priced_lines(rng, scene, 1 + rng.randint(*SCALES[scale]["deal_rest"]))
    deal_item, _, unit = entries[0]
    unit = max(unit, 2)

    if rng.random() < 0.65:
        deal_n = rng.choice([2, 3])
        # Priced under the regular cost of that many, so the saving is real.
        deal_price = _offer_price(rng, deal_n, deal_n * unit - unit + 1, deal_n * unit - 1)
        qty = rng.randint(deal_n + 1, deal_n * 3)
        line = f"{qty} {deal_item} — ${unit} each, or {deal_n} for ${deal_price}"
        cost = _deal_cost(qty, unit, deal_n, deal_price)
        groups, left = divmod(qty, deal_n)
        lot = "lot" if groups == 1 else "lots"
        working = (
            f"{_cap(deal_item)}: {groups} {lot} of {deal_n} at ${deal_price} = ${groups * deal_price}"
            + (f", plus {left} left over at ${unit} = ${left * unit}" if left else "")
            + f" → ${cost}"
        )
        kind = "n_for"
    else:
        buy_n = rng.choice([2, 3])
        qty = rng.randint(buy_n + 1, (buy_n + 1) * 2 + 1)
        line = f"{qty} {deal_item} — ${unit} each, buy {buy_n} get 1 free"
        cost = _free_cost(qty, unit, buy_n)
        free = qty // (buy_n + 1)
        is_are = "is" if free == 1 else "are"
        working = (
            f"{_cap(deal_item)}: {free} of the {qty} {is_are} free, so "
            f"{qty - free} × ${unit} = ${cost}"
        )
        kind = "free"

    rest = entries[1:]
    lines = [line] + [f"{q} {item} — ${p} each" for item, q, p in rest]
    return scene, name, deal_item, qty, unit, cost, working, kind, rest, lines


def deal_total(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    scene, name, deal_item, qty, unit, cost, working, kind, rest, lines = _deal_setup(rng, scale)
    total = cost + sum(q * p for _, q, p in rest)
    extras = _noise(rng, scene.flavour, tax=True, max_facts=SCALES[scale]["facts"])
    ask = rng.choice([
        "How many dollars does the whole list cost?",
        "With the offer used, how many dollars is that altogether?",
    ])
    rest_working = "".join(
        f" {_cap(item)}: {q} × ${p} = ${q * p}." for item, q, p in rest
    )
    explanation = f"{working}.{rest_working} Altogether ${total}. 🏷️"
    signature = ("wp_deal", scene.key, "total", kind, tuple(sorted(lines)), total)
    text = _assemble(
        _opener(rng, name, scene.place), _bullets(lines), " ".join(extras), ask
    )
    return signature, text, total, explanation


def deal_saving(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    scene, name, deal_item, qty, unit, cost, working, kind, rest, lines = _deal_setup(rng, scale)
    full = qty * unit
    if full - cost < 2:  # a $1 saving isn't worth asking about
        return deal_total(rng, lo, hi, scale=scale)
    extras = _noise(rng, scene.flavour, tax=True, max_facts=SCALES[scale]["facts"])
    answer = full - cost
    ask = rng.choice([
        f"How many dollars does the offer save on the {deal_item}?",
        f"How much is saved on the {deal_item} by using the offer?",
    ])
    explanation = (
        f"Without the offer: {qty} × ${unit} = ${full}. {working}. "
        f"Saving: ${full} - ${cost} = ${answer}. 🏷️"
    )
    signature = ("wp_deal", scene.key, "saving", kind, tuple(sorted(lines)), answer)
    text = _assemble(
        _opener(rng, name, scene.place), _bullets(lines), " ".join(extras), ask
    )
    return signature, text, answer, explanation


# ---------- shape 6: two ways to buy the same thing ----------


@dataclass(frozen=True)
class ChoiceItem:
    generic: str      # "peaches"
    plain: str        # "white peaches"
    fancy: str        # "yellow peaches"
    place: str        # "the fruit stall"


CHOICE_ITEMS: tuple[ChoiceItem, ...] = (
    ChoiceItem("peaches", "white peaches", "yellow peaches", "the fruit stall"),
    ChoiceItem("apples", "green apples", "red apples", "the fruit stall"),
    ChoiceItem("loaves of bread", "white loaves", "brown loaves", "the bakery"),
    ChoiceItem("yogurt pots", "plain yogurt pots", "berry yogurt pots", "the dairy case"),
    ChoiceItem("pencils", "wooden pencils", "colour pencils", "the stationery shop"),
    ChoiceItem("pairs of socks", "grey socks", "stripy socks", "the clothes shop"),
    ChoiceItem("juice cartons", "apple juice cartons", "orange juice cartons", "the drinks aisle"),
    ChoiceItem("notebooks", "lined notebooks", "spotty notebooks", "the stationery shop"),
    ChoiceItem("cupcakes", "vanilla cupcakes", "chocolate cupcakes", "the bakery"),
    ChoiceItem("tennis balls", "yellow tennis balls", "green tennis balls", "the sports shop"),
)


def _choice_setup(rng: random.Random):
    """Two ways to buy the same thing, priced so one really is cheaper."""
    item = rng.choice(CHOICE_ITEMS)
    name = rng.choice(NAMES)
    for _ in range(20):
        deal_n = rng.choice([2, 3])
        qty = deal_n * rng.randint(2, 3)          # divides exactly — no messy leftovers
        unit = rng.randint(2, 6)
        deal_price = _offer_price(rng, deal_n, deal_n * unit - unit, deal_n * unit + unit)
        plain_cost = qty * unit
        fancy_cost = (qty // deal_n) * deal_price
        if plain_cost != fancy_cost:
            return item, name, qty, unit, deal_n, deal_price, plain_cost, fancy_cost
    # Fall back to a guaranteed gap.
    unit, deal_n, deal_price, qty = 3, 2, 5, 6
    return item, name, qty, unit, deal_n, deal_price, qty * unit, (qty // deal_n) * deal_price


def _choice_lines(item: ChoiceItem, unit: int, deal_n: int, deal_price: int):
    return [
        f"{_cap(item.plain)} — ${unit} each",
        f"{_cap(item.fancy)} — {deal_n} for ${deal_price}",
    ]


def choice_cheapest(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """The list says just "peaches" — so either kind will do."""
    item, name, qty, unit, deal_n, deal_price, plain_cost, fancy_cost = _choice_setup(rng)
    lines = _choice_lines(item, unit, deal_n, deal_price)
    answer = min(plain_cost, fancy_cost)
    cheaper, dearer = (
        (item.plain, item.fancy) if plain_cost < fancy_cost else (item.fancy, item.plain)
    )
    extras = _noise(rng, (
        f"The shop shuts at {rng.choice([5, 6, 7])} o'clock.",
        "The queue is short today.",
    ), tax=True, always=[rng.choice([
        f"{name} buys whichever works out cheaper.",
        f"{name} wants to spend as little as possible.",
    ])])
    ask = rng.choice([
        "How many dollars does that cost?",
        "Buying the cheaper kind, how many dollars is that?",
    ])
    explanation = (
        f"{_cap(item.plain)}: {qty} × ${unit} = ${plain_cost}. "
        f"{_cap(item.fancy)}: {qty} ÷ {deal_n} = {qty // deal_n} lots at ${deal_price} = ${fancy_cost}. "
        f"The {cheaper} are cheaper than the {dearer}, so ${answer}. 🔎"
    )
    signature = ("wp_choice", item.generic, "cheapest", qty, unit, deal_n, deal_price)
    text = _assemble(
        f"{name}'s shopping list says: {qty} {item.generic}.",
        f"At {item.place} there are two kinds:\n{_bullets(lines)}",
        " ".join(extras),
        ask,
    )
    return signature, text, answer, explanation


def choice_specified(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Same stall, but the list names one kind — the cheaper one may be
    off the table. Reading carefully *is* the question."""
    item, name, qty, unit, deal_n, deal_price, plain_cost, fancy_cost = _choice_setup(rng)
    lines = _choice_lines(item, unit, deal_n, deal_price)
    # Ask for whichever kind is *not* the bargain, so a kid who skims and
    # grabs the cheaper number gets it wrong.
    if plain_cost < fancy_cost:
        wanted, answer = item.fancy, fancy_cost
        working = (
            f"{qty} ÷ {deal_n} = {qty // deal_n} lots at ${deal_price} = ${fancy_cost}"
        )
    else:
        wanted, answer = item.plain, plain_cost
        working = f"{qty} × ${unit} = ${plain_cost}"
    extras = _noise(rng, (
        "The shop is busy this morning.",
        f"The stall has been there for {rng.choice([5, 10, 20])} years.",
    ), tax=True)
    ask = rng.choice([
        "How many dollars does that cost?",
        "Following the list exactly, how many dollars is that?",
    ])
    explanation = (
        f"The list asks for {wanted}, so the other price doesn't apply: "
        f"{working} = ${answer}. Read the list carefully! 🔎"
    )
    signature = ("wp_choice", item.generic, "specified", qty, unit, deal_n, deal_price)
    text = _assemble(
        f"{name}'s shopping list says: {qty} {wanted}.",
        f"At {item.place} there are two kinds:\n{_bullets(lines)}",
        " ".join(extras),
        ask,
    )
    return signature, text, answer, explanation


# ---------- tiers (used by questions.py) ----------

TIER_SIMPLE = (simple_add, simple_sub)
TIER_SIMPLE_WIDE = (simple_add, simple_sub, simple_groups, simple_share)
TIER_LIST = (list_count, list_outside, list_difference)



def tally_total_small(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    """Grade-2 scoring: nothing worth more than 5 a go."""
    return tally_total(rng, lo, hi, max_value=5, scale=scale)


def tally_difference_small(rng: random.Random, lo: int, hi: int, *, scale: str = "standard"):
    return tally_difference(rng, lo, hi, max_value=5, scale=scale)


TIER_LIST_PLUS = TIER_LIST + (tally_total_small, tally_difference_small)
TIER_PRICES = (
    priced_total, priced_change, priced_split, priced_difference,
    tally_total, tally_difference, tally_missing,
)
TIER_DEALS = (
    deal_total, deal_saving, choice_cheapest, choice_specified,
    priced_split, tally_missing,
)


# Which shapes a quiz draws from, by tier. `_pick_factory` builds a fresh
# rotating factory from one of these per quiz.
TIERS: dict[str, tuple[Callable, ...]] = {
    "simple": TIER_SIMPLE,
    "simple_wide": TIER_SIMPLE_WIDE,
    "list": TIER_LIST,
    "list_plus": TIER_LIST_PLUS,
    "prices": TIER_PRICES,
    "deals": TIER_DEALS,
}


def tier_factory(tier: str, scale: str = "standard"):
    """A fresh rotating factory for `tier` — one per quiz.

    `scale` sets the reading load (SCALES above), independent of the
    maths tier: a 2nd grader's list question and a 4th grader's differ
    in how much there is to read, not just in the arithmetic.
    """
    builders = tuple(partial(b, scale=scale) for b in TIERS[tier])
    return rotating(builders, tier)
