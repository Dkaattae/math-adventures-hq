"""Deal question shapes from a shuffled deck instead of drawing at random.

`_generate_typed` calls a topic's factory ten times for one quiz. Picking
a shape at random each time clumps — the same wording turns up three
times while another never appears. Dealing guarantees a quiz covers
every shape its tier offers before repeating one.
"""
from __future__ import annotations

import random
from typing import Callable


def rotating(builders: tuple[Callable, ...], tier: str):
    deck: list[Callable] = []

    def factory(rng: random.Random, lo: int, hi: int):
        if not deck:
            deck.extend(builders)
            rng.shuffle(deck)
        return deck.pop()(rng, lo, hi)

    factory.tier = tier          # type: ignore[attr-defined]
    factory.builders = builders  # type: ignore[attr-defined]
    return factory
