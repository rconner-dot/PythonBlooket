"""Property tests run against every registered question generator.

Run one topic only with e.g. ``pytest tests/test_generators.py -k "topics.strings"``.
"""

from __future__ import annotations

import random

import pytest

from pyblooket.questions import TOPICS, load_generators
from pyblooket.questions.base import (
    DIFFICULTIES,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    NUM_CHOICES,
    REGISTRY,
    Question,
    display_output,
    error_choice,
    run_code,
)

SEEDS = range(150)
MIN_GENERATORS_PER_LEVEL = 3

load_generators()
GENS = list(REGISTRY)


def _norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip("\n").split("\n"))


@pytest.mark.parametrize("gen", GENS, ids=[g.name for g in GENS])
def test_generator_produces_valid_questions(gen):
    for seed in SEEDS:
        q = gen.fn(random.Random(seed))
        ctx = f"{gen.name} seed={seed}"
        assert isinstance(q, Question), ctx
        assert q.topic == gen.topic, ctx
        assert q.difficulty == gen.difficulty, ctx
        assert q.prompt.strip(), ctx
        assert q.explanation.strip(), ctx
        assert len(q.choices) == NUM_CHOICES, ctx
        assert len({_norm(c) for c in q.choices}) == NUM_CHOICES, f"duplicate choices: {ctx}"
        assert 0 <= q.answer < NUM_CHOICES, ctx
        for c in q.choices:
            lines = c.split("\n")
            assert len(lines) <= MAX_CHOICE_LINES, ctx
            assert all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines), ctx
        if q.code is not None:
            compile(q.code, "<snippet>", "exec")
            assert len(q.code.split("\n")) <= 18, f"snippet too long: {ctx}"
        if q.kind == "output":
            res = run_code(q.code)
            expected = error_choice(res.error) if res.error else display_output(res.output)
            assert _norm(q.choices[q.answer]) == _norm(expected), ctx


@pytest.mark.parametrize("gen", GENS, ids=[g.name for g in GENS])
def test_generator_is_deterministic(gen):
    for seed in range(5):
        a = gen.fn(random.Random(seed))
        b = gen.fn(random.Random(seed))
        assert (a.prompt, a.code, a.choices, a.answer) == (b.prompt, b.code, b.choices, b.answer)


@pytest.mark.parametrize("gen", GENS, ids=[g.name for g in GENS])
def test_generator_varies(gen):
    seen = {(q.code, q.prompt, tuple(q.choices)) for q in (gen.fn(random.Random(s)) for s in SEEDS)}
    assert len(seen) >= 8, f"{gen.name} only produced {len(seen)} distinct questions"


@pytest.mark.parametrize("topic", list(TOPICS))
def test_topic_has_generators_at_every_difficulty(topic):
    for d in DIFFICULTIES:
        n = sum(1 for g in REGISTRY if g.topic == topic and g.difficulty == d)
        assert n >= MIN_GENERATORS_PER_LEVEL, f"{topic} has {n} generators at difficulty {d}"


def test_correct_answer_positions_are_balanced():
    counts = [0] * NUM_CHOICES
    for gen in GENS:
        for seed in range(40):
            counts[gen.fn(random.Random(seed)).answer] += 1
    total = sum(counts)
    for c in counts:
        assert c > total / NUM_CHOICES * 0.7, counts
