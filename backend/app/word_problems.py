"""Real-life word problems.

The first version of this topic was one-line templates with a name glued
on — "Maya has 9 apples and gives 2 away, how many are left?". The words
did no work: strip them out and the arithmetic was untouched, the same
ten names came round every question, and a fifth grader got a
kindergarten task in a longer sentence.

These build a small scene instead — a shopping list, a supply cupboard,
a market stall — and ask for one number out of it. Two things make them
harder than the arithmetic they contain:

* **Sifting.** Every scene carries facts the answer doesn't need: the
  bakery items when the question is about the produce aisle, the time
  the market opens, the bags someone brought along. Choosing which
  numbers matter is the skill being practised, and it's the part a
  one-line template can't teach.
* **Steps.** A price question is a multiplication per line and then a
  sum. A sale question divides into deal-sized groups first, and the
  leftovers still pay full price.

Conventions that keep answers typable on a phone: money is whole
dollars, quantities are whole items and at least 2 (so no line ever
reads "1 apples"), and every answer is a plain non-negative integer.

Grade tiers are chosen by `_pick_factory` in questions.py:
K-1 short stories → grade 2+ list sifting → grade 3+ prices →
grade 5 hard sale deals.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# A wide pool so a 10-question quiz rarely repeats a character, and each
# question mentions its name once — in the title of the list — instead of
# three times in one sentence.
NAMES = [
    "Maya", "Leo", "Ava", "Noah", "Zoe", "Sam", "Mia", "Eli", "Ruby", "Max",
    "Amara", "Priya", "Diego", "Hana", "Omar", "Freya", "Kofi", "Ines", "Yusuf", "Lena",
    "Marco", "Nina", "Tariq", "Sofia", "Jonas", "Aisha", "Bruno", "Elif", "Caleb", "Rosa",
    "Kai", "Dalia", "Milo", "Anya", "Idris", "Clara", "Nikhil", "Esme", "Theo", "Junko",
]


# ---------- scenes ----------


@dataclass(frozen=True)
class Zone:
    """One section of a scene: a place, and the things found there."""

    short: str                  # "the produce aisle"
    described: str              # "the produce aisle, where the fruit and vegetables are"
    items: tuple[str, ...]      # plural phrases: "apples", "loaves of bread"


@dataclass(frozen=True)
class CountScene:
    key: str
    title: str                  # "{name}'s shopping list"
    unit: str                   # "items" / "books" / "animals"
    zones: tuple[Zone, ...]
    flavour: tuple[str, ...]    # true, irrelevant facts


COUNT_SCENES: tuple[CountScene, ...] = (
    CountScene(
        key="grocery",
        title="{name}'s shopping list",
        unit="items",
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
            "There are 12 checkout lanes at the front of the store.",
            "The cart has one wobbly wheel.",
        ),
    ),
    CountScene(
        key="supplies",
        title="{name}'s classroom supply order",
        unit="supplies",
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
        key="library",
        title="{name}'s library cart",
        unit="books",
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
        key="camping",
        title="{name}'s camping packing list",
        unit="things",
        zones=(
            Zone("the kitchen box", "the kitchen box",
                 ("plates", "forks", "cooking pots", "water bottles", "mugs")),
            Zone("the sleeping bag", "the pile of sleeping gear",
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
        key="shelter",
        title="{name}'s animal shelter list",
        unit="animals",
        zones=(
            Zone("the dog run", "the dog run out the back",
                 ("puppies", "beagles", "spaniels", "sheepdogs")),
            Zone("the cat room", "the cat room",
                 ("kittens", "tabby cats", "ginger cats", "black cats")),
            Zone("the small pet corner", "the small pet corner",
                 ("rabbits", "guinea pigs", "hamsters")),
        ),
        flavour=(
            "The shelter has 5 volunteers on Saturday.",
            "Feeding time is at 7 in the morning.",
            "The shelter has been open for 20 years.",
        ),
    ),
    CountScene(
        key="bakesale",
        title="{name}'s bake sale table",
        unit="things",
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
            "The table is 2 metres long.",
            "The money goes to the school garden.",
        ),
    ),
    CountScene(
        key="garden",
        title="{name}'s garden centre trolley",
        unit="things",
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
        key="sports",
        title="{name}'s equipment room list",
        unit="things",
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
    title: str                                  # "{name}'s cart at the farmers market"
    items: tuple[tuple[str, int, int], ...]     # (plural phrase, min $, max $)
    flavour: tuple[str, ...]


PRICED_SCENES: tuple[PricedScene, ...] = (
    PricedScene(
        key="market",
        title="{name}'s basket at the farmers market",
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
        key="bookfair",
        title="{name}'s pile at the school book fair",
        items=(
            ("paperback books", 4, 6), ("hardback books", 8, 12), ("posters", 2, 4),
            ("bookmarks", 1, 2), ("sticker sheets", 2, 3), ("notebooks", 3, 5),
        ),
        flavour=(
            "The fair runs for 4 days.",
            "The hall has 6 long tables.",
            "The fair is in the school hall.",
        ),
    ),
    PricedScene(
        key="petshop",
        title="{name}'s trolley at the pet shop",
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
        key="hardware",
        title="{name}'s list for building a bookshelf",
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
        key="craft",
        title="{name}'s basket at the craft shop",
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
        key="lunch",
        title="{name}'s order at the food truck",
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
        key="party",
        title="{name}'s party supply list",
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
)


# ---------- helpers ----------

_NO_TAX = "There is no tax to add."


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"• {line}" for line in lines)


def _scene_text(title: str, lines: list[str], *, extras: list[str], ask: str) -> str:
    """Assemble a scene: a titled list, some facts, then the question."""
    body = "\n".join(filter(None, [" ".join(extras)]))
    parts = [f"{title}:", _bullets(lines)]
    if body:
        parts.append(body)
    parts.append(ask)
    return "\n\n".join(parts)


def _plural_only(rng: random.Random, lo: int, hi: int) -> int:
    """A count of at least 2, so no line ever reads "1 apples"."""
    return rng.randint(2, max(3, min(9, hi)))


def _cap(text: str) -> str:
    """Zone names read "the dairy case" mid-sentence but need a capital
    when an explanation starts with one."""
    return text[:1].upper() + text[1:]


# ---------- tier 1: short stories (K-1) ----------
#
# Kept deliberately small: at K-1 the reading itself is the hard part, so
# these stay one sentence. The richer scenes below start at grade 2.

_SIMPLE_ITEMS = [
    ("apples", "in the fruit bowl"), ("stickers", "in the album"),
    ("marbles", "in the jar"), ("crayons", "in the box"),
    ("shells", "in the bucket"), ("acorns", "in the basket"),
    ("toy cars", "on the shelf"), ("cookies", "on the plate"),
]


def wp_simple_add(rng: random.Random, lo: int, hi: int):
    # The starting pile is always plural, so no question reads "1 apples".
    a, b = rng.randint(2, max(3, hi)), rng.randint(lo, hi)
    name = rng.choice(NAMES)
    item, where = rng.choice(_SIMPLE_ITEMS)
    small, big = (a, b) if a <= b else (b, a)
    return (
        ("wp_add", small, big, item),
        f"There are {a} {item} {where}. {name} puts in {b} more. How many {item} are there now?",
        a + b,
        f"{a} + {b} = {a + b}. Count on {b} more from {a}! 📖",
    )


def wp_simple_sub(rng: random.Random, lo: int, hi: int):
    a = rng.randint(max(lo, 2), max(hi, 3))
    b = rng.randint(1, a)
    name = rng.choice(NAMES)
    item, where = rng.choice(_SIMPLE_ITEMS)
    return (
        ("wp_sub", a, b, item),
        f"There are {a} {item} {where}. {name} takes {b} away. How many {item} are left?",
        a - b,
        f"{a} - {b} = {a - b}. Take away {b} from {a}! 📖",
    )


def wp_simple_groups(rng: random.Random, lo: int, hi: int):
    groups = rng.randint(2, max(3, hi // 3))
    each = rng.randint(2, max(3, hi // 2))
    item, _ = rng.choice(_SIMPLE_ITEMS)
    return (
        ("wp_mul", groups, each, item),
        f"There are {groups} boxes with {each} {item} in each box. How many {item} in all?",
        groups * each,
        f"{groups} boxes × {each} each = {groups * each}. That's {groups} groups of {each}! 📖",
    )


def wp_simple_share(rng: random.Random, lo: int, hi: int):
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


# ---------- tier 2: sift the list (grade 2+) ----------


def _count_lines(rng: random.Random, zone: Zone, count: int, hi: int) -> list[tuple[str, int]]:
    """`count` distinct items from a zone, each with a quantity."""
    chosen = rng.sample(zone.items, k=min(count, len(zone.items)))
    return [(item, _plural_only(rng, 1, hi)) for item in chosen]


def wp_list(rng: random.Random, lo: int, hi: int):
    """A categorised list where only part of it answers the question."""
    scene = rng.choice(COUNT_SCENES)
    target, other = rng.sample(scene.zones, k=2)
    name = rng.choice(NAMES)

    target_lines = _count_lines(rng, target, rng.randint(2, 3), hi)
    other_lines = _count_lines(rng, other, rng.randint(2, 3), hi)
    all_lines = target_lines + other_lines
    rng.shuffle(all_lines)

    target_total = sum(q for _, q in target_lines)
    other_total = sum(q for _, q in other_lines)
    lines = [f"{qty} {item}" for item, qty in all_lines]
    flavour = [rng.choice(scene.flavour)]
    variant = rng.choice(["here", "not_here", "difference"])

    if variant == "here":
        ask = (
            f"Counting every single one, how many {scene.unit} on the list "
            f"come from {target.described}?"
        )
        answer = target_total
        sums = " + ".join(str(q) for _, q in target_lines)
        explanation = (
            f"Only the {target.short} lines count: {sums} = {target_total}. "
            f"The rest of the list belongs somewhere else! 🛒"
        )
    elif variant == "not_here":
        ask = f"How many {scene.unit} on the list do NOT come from {target.short}?"
        answer = other_total
        sums = " + ".join(str(q) for _, q in other_lines)
        explanation = (
            f"Everything except the {target.short} lines: {sums} = {other_total}. 🛒"
        )
    elif variant == "difference" and target_total != other_total:
        # Keep the subtraction positive whichever way the draw fell.
        big, small = (target, other) if target_total >= other_total else (other, target)
        big_total, small_total = max(target_total, other_total), min(target_total, other_total)
        ask = f"How many more {scene.unit} come from {big.short} than from {small.short}?"
        answer = big_total - small_total
        explanation = (
            f"{_cap(big.short)}: {big_total}. {_cap(small.short)}: {small_total}. "
            f"{big_total} - {small_total} = {answer}. 🛒"
        )
    else:
        # Both zones came out equal — "how many more?" would answer 0, so
        # fall back to the straight count.
        variant = "here"
        ask = (
            f"Counting every single one, how many {scene.unit} on the list "
            f"come from {target.described}?"
        )
        answer = target_total
        sums = " + ".join(str(q) for _, q in target_lines)
        explanation = (
            f"Only the {target.short} lines count: {sums} = {target_total}. "
            f"The rest of the list belongs somewhere else! 🛒"
        )

    signature = ("wp_list", scene.key, variant, target.short, tuple(sorted(lines)), answer)
    text = _scene_text(scene.title.format(name=name), lines, extras=flavour, ask=ask)
    return signature, text, answer, explanation


# ---------- tier 3: prices (grade 3+) ----------


def _priced_lines(rng: random.Random, scene: PricedScene, count: int):
    """`count` distinct items, each with a quantity and a whole-dollar price."""
    chosen = rng.sample(scene.items, k=min(count, len(scene.items)))
    out = []
    for item, price_lo, price_hi in chosen:
        out.append((item, rng.randint(2, 5), rng.randint(price_lo, price_hi)))
    return out


def wp_prices(rng: random.Random, lo: int, hi: int):
    """Quantity × price on each line, then a sum — with facts to ignore."""
    scene = rng.choice(PRICED_SCENES)
    name = rng.choice(NAMES)
    entries = _priced_lines(rng, scene, rng.randint(3, 4))
    lines = [f"{qty} {item} — ${price} each" for item, qty, price in entries]
    totals = [qty * price for _, qty, price in entries]
    total = sum(totals)
    variant = rng.choice(["total", "total", "change", "difference", "split"])

    if variant == "split":
        # Splitting the bill keeps division in the upper tiers, where the
        # rest of the scene is multiply-then-add.
        friends = _divisor_for(total, rng)
        if friends is None:  # no tidy split — just ask for the total
            variant = "total"
            extras, ask, answer, explanation = _prices_total(scene, entries, totals, total, rng)
        else:
            extras = [f"{friends} friends share the cost equally.", _NO_TAX]
            ask = "How many dollars does each friend pay?"
            answer = total // friends
            explanation = (
                f"The list costs {' + '.join(str(t) for t in totals)} = ${total}. "
                f"${total} ÷ {friends} = ${answer} each. 🧾"
            )
    elif variant == "total":
        extras, ask, answer, explanation = _prices_total(scene, entries, totals, total, rng)
    elif variant == "change":
        # A note big enough to cover it, rounded to something a kid holds.
        note = next(n for n in (20, 50, 100, 200) if n > total)
        extras = [f"{name} pays with a ${note} note.", _NO_TAX]
        ask = "How many dollars of change come back?"
        answer = note - total
        explanation = (
            f"The list costs {' + '.join(str(t) for t in totals)} = ${total}. "
            f"${note} - ${total} = ${note - total} change. 🧾"
        )
    else:
        (item_a, qty_a, price_a), (item_b, qty_b, price_b) = _pick_two_by_cost(entries)
        if qty_a * price_a == qty_b * price_b:
            # Two lines that happen to cost the same would make a "how
            # much more?" question with a 0 answer — ask the total instead.
            variant = "total"
            extras, ask, answer, explanation = _prices_total(scene, entries, totals, total, rng)
        else:
            extras = [rng.choice(scene.flavour), _NO_TAX]
            ask = f"How many dollars more do the {item_a} cost than the {item_b}?"
            answer = qty_a * price_a - qty_b * price_b
            explanation = (
                f"{_cap(item_a)}: {qty_a} × ${price_a} = ${qty_a * price_a}. "
                f"{_cap(item_b)}: {qty_b} × ${price_b} = ${qty_b * price_b}. "
                f"${qty_a * price_a} - ${qty_b * price_b} = ${answer}. 🧾"
            )

    signature = ("wp_prices", scene.key, variant, tuple(sorted(lines)), answer)
    text = _scene_text(scene.title.format(name=name), lines, extras=extras, ask=ask)
    return signature, text, answer, explanation


def _prices_total(scene: PricedScene, entries, totals, total: int, rng: random.Random):
    """The plain "add up the whole list" ask."""
    workings = " + ".join(f"{qty} × ${price}" for _, qty, price in entries)
    return (
        [rng.choice(scene.flavour), _NO_TAX],
        "How many dollars does the whole list cost?",
        total,
        f"{workings} = {' + '.join(str(t) for t in totals)} = ${total}. 🧾",
    )


def _divisor_for(total: int, rng: random.Random) -> int | None:
    """A believable number of friends that splits the bill exactly."""
    options = [n for n in (2, 3, 4, 5, 6) if total % n == 0]
    return rng.choice(options) if options else None


def _pick_two_by_cost(entries):
    """Two lines, dearer first, so the difference is never negative."""
    ranked = sorted(entries, key=lambda e: e[1] * e[2], reverse=True)
    return ranked[0], ranked[-1]


# ---------- tier 4: sale deals (grade 5 hard) ----------


def _deal_cost(qty: int, unit: int, deal_n: int, deal_price: int) -> int:
    """"`deal_n` for $`deal_price`" — leftovers still pay full price."""
    groups, left = divmod(qty, deal_n)
    return groups * deal_price + left * unit


def _free_cost(qty: int, unit: int, buy_n: int) -> int:
    """"Buy `buy_n`, get one free" — one item in every buy_n+1 is free."""
    free = qty // (buy_n + 1)
    return (qty - free) * unit


def wp_deals(rng: random.Random, lo: int, hi: int):
    """One line is on offer, so it can't just be quantity × price."""
    scene = rng.choice(PRICED_SCENES)
    name = rng.choice(NAMES)
    entries = _priced_lines(rng, scene, rng.randint(2, 3))

    # The deal line needs enough of the item for the offer to bite.
    deal_item, _, deal_unit = entries[0]
    deal_unit = max(deal_unit, 2)
    deal_kind = rng.choice(["n_for", "n_for", "free"])

    if deal_kind == "n_for":
        deal_n = rng.choice([2, 3])
        # Priced below the regular cost of that many, so it's a real saving.
        deal_price = rng.randint(deal_n * deal_unit - deal_unit + 1, deal_n * deal_unit - 1)
        deal_qty = rng.randint(deal_n + 1, deal_n * 3)
        deal_line = f"{deal_qty} {deal_item} — ${deal_unit} each, or {deal_n} for ${deal_price}"
        deal_cost = _deal_cost(deal_qty, deal_unit, deal_n, deal_price)
        groups, left = divmod(deal_qty, deal_n)
        lot_word = "lot" if groups == 1 else "lots"
        deal_working = (
            f"{_cap(deal_item)}: {groups} {lot_word} of {deal_n} at ${deal_price} "
            f"= ${groups * deal_price}"
            + (f", plus {left} left over at ${deal_unit} = ${left * deal_unit}" if left else "")
            + f" → ${deal_cost}"
        )
    else:
        buy_n = rng.choice([2, 3])
        deal_qty = rng.randint(buy_n + 1, (buy_n + 1) * 2 + 1)
        deal_line = f"{deal_qty} {deal_item} — ${deal_unit} each, buy {buy_n} get 1 free"
        deal_cost = _free_cost(deal_qty, deal_unit, buy_n)
        free = deal_qty // (buy_n + 1)
        is_are = "is" if free == 1 else "are"
        deal_working = (
            f"{_cap(deal_item)}: {free} of the {deal_qty} {is_are} free, so "
            f"{deal_qty - free} × ${deal_unit} = ${deal_cost}"
        )

    rest = entries[1:]
    rest_lines = [f"{qty} {item} — ${price} each" for item, qty, price in rest]
    rest_costs = [qty * price for _, qty, price in rest]
    lines = [deal_line] + rest_lines
    total = deal_cost + sum(rest_costs)
    variant = rng.choice(["total", "total", "saving"])

    if variant == "total":
        extras = [rng.choice(scene.flavour), _NO_TAX]
        ask = "How many dollars does the whole list cost?"
        answer = total
        rest_working = "".join(
            f" {_cap(item)}: {qty} × ${price} = ${qty * price}."
            for item, qty, price in rest
        )
        explanation = f"{deal_working}.{rest_working} Altogether ${total}. 🏷️"
    else:
        full_price = deal_qty * deal_unit
        extras = [rng.choice(scene.flavour), _NO_TAX]
        ask = f"How many dollars does the offer save on the {deal_item}?"
        answer = full_price - deal_cost
        explanation = (
            f"Without the offer: {deal_qty} × ${deal_unit} = ${full_price}. "
            f"{deal_working}. Saving: ${full_price} - ${deal_cost} = ${answer}. 🏷️"
        )

    signature = ("wp_deals", scene.key, variant, deal_kind, tuple(sorted(lines)), answer)
    text = _scene_text(scene.title.format(name=name), lines, extras=extras, ask=ask)
    return signature, text, answer, explanation


# ---------- tier entry points (used by questions.py) ----------


def make_simple(rng: random.Random, lo: int, hi: int):
    return rng.choice([wp_simple_add, wp_simple_sub])(rng, lo, hi)


def make_simple_wide(rng: random.Random, lo: int, hi: int):
    return rng.choice([wp_simple_add, wp_simple_sub, wp_simple_groups, wp_simple_share])(rng, lo, hi)


def make_list(rng: random.Random, lo: int, hi: int):
    return wp_list(rng, lo, hi)


def make_prices(rng: random.Random, lo: int, hi: int):
    return wp_prices(rng, lo, hi)


def make_deals(rng: random.Random, lo: int, hi: int):
    return wp_deals(rng, lo, hi)
