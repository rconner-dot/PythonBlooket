"""Question generation: topic catalogue, registry and the public entry point."""

from __future__ import annotations

import importlib
import random

from .base import (
    DIFFICULTIES,
    DIFFICULTY_LABELS,
    DIFFICULTY_POINTS,
    REGISTRY,
    GenerationError,
    Question,
)

# id -> (display name, emoji icon, short description). Order = display order.
TOPICS: dict[str, tuple[str, str, str]] = {
    "basics": ("Variables & Math", "🔢", "Assignment, arithmetic operators, // % **, types"),
    "strings": ("Strings", "🔤", "Indexing, slicing, methods, f-strings"),
    "conditionals": ("Conditionals & Logic", "🔀", "if/elif/else, and/or/not, comparisons, truthiness"),
    "loops": ("Loops", "🔁", "for, while, range, break/continue, nested loops"),
    "lists": ("Lists", "📋", "Indexing, methods, slicing, mutation & aliasing"),
    "dicts": ("Dictionaries", "📖", "Keys & values, get, methods, iteration"),
    "tuples_sets": ("Tuples & Sets", "🧺", "Unpacking, immutability, set operations"),
    "functions": ("Functions", "🧩", "Parameters, defaults, return, scope, *args/**kwargs"),
    "comprehensions": ("Comprehensions", "✨", "List/dict/set comprehensions, generator expressions"),
    "builtins": ("Built-in Functions", "🧰", "len, sorted, zip, enumerate, map, filter, min/max, sum"),
    "exceptions": ("Exceptions", "💥", "try/except/else/finally, raising, error types"),
    "oop": ("Classes & OOP", "🏛️", "Classes, __init__, methods, inheritance, dunder methods"),
    "recursion": ("Recursion", "🌀", "Base cases, tracing recursive calls"),
}

_loaded = False


def load_generators() -> None:
    """Import every topic module so their @generator decorators register."""
    global _loaded
    if _loaded:
        return
    for topic in TOPICS:
        try:
            importlib.import_module(f"{__name__}.topics.{topic}")
        except ModuleNotFoundError as exc:
            if exc.name != f"{__name__}.topics.{topic}":
                raise
    _loaded = True


def generators_for(topic: str, difficulty: int):
    load_generators()
    return [g for g in REGISTRY if g.topic == topic and g.difficulty == difficulty]


def available_topics() -> list[dict]:
    load_generators()
    out = []
    for tid, (name, icon, desc) in TOPICS.items():
        counts = {d: len(generators_for(tid, d)) for d in DIFFICULTIES}
        if sum(counts.values()) == 0:
            continue
        out.append(
            {"id": tid, "name": name, "icon": icon, "description": desc, "generators": counts}
        )
    return out


# Weights used when the player picks "Mixed" difficulty.
MIXED_WEIGHTS = {1: 0.45, 2: 0.35, 3: 0.20}


def generate_question(
    topics: list[str] | None = None,
    difficulty: int | None = None,
    rng: random.Random | None = None,
    max_attempts: int = 25,
) -> Question:
    """Generate one random question.

    ``topics``: topic ids to draw from (None/empty = all).
    ``difficulty``: 1/2/3, or None for a weighted mix.
    """
    load_generators()
    rng = rng or random.Random()
    valid = [t for t in (topics or TOPICS) if t in TOPICS]
    if not valid:
        valid = list(TOPICS)
    last_err: Exception | None = None
    for _ in range(max_attempts):
        diff = difficulty
        if diff is None:
            diff = rng.choices(list(MIXED_WEIGHTS), weights=list(MIXED_WEIGHTS.values()))[0]
        pool = [g for t in valid for g in generators_for(t, diff)]
        if not pool:
            # Fall back to any difficulty for these topics.
            pool = [g for t in valid for d in DIFFICULTIES for g in generators_for(t, d)]
        if not pool:
            raise GenerationError("no generators registered")
        # Pick a topic first so topics with many generators don't dominate.
        topic = rng.choice(sorted({g.topic for g in pool}))
        gen = rng.choice([g for g in pool if g.topic == topic])
        try:
            return gen.fn(random.Random(rng.random()))
        except GenerationError as exc:
            last_err = exc
    raise GenerationError(f"could not generate a question: {last_err}")


__all__ = [
    "DIFFICULTIES",
    "DIFFICULTY_LABELS",
    "DIFFICULTY_POINTS",
    "TOPICS",
    "Question",
    "GenerationError",
    "available_topics",
    "generate_question",
    "load_generators",
]
