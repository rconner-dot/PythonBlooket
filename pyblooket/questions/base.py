"""Core building blocks shared by every question generator.

A *generator* is a function ``fn(rng: random.Random) -> Question`` registered
with :func:`generator`.  Generators must draw all randomness from ``rng`` so a
given seed always yields the same question.

Correctness is enforced by construction wherever possible: the helpers below
*execute* the generated snippet to compute the right answer, and drop any
distractor that turns out to be equal to it.
"""

from __future__ import annotations

import builtins
import io
import random
import threading
from dataclasses import dataclass, field
from typing import Callable, Iterable

EASY, MEDIUM, HARD = 1, 2, 3
DIFFICULTIES = (EASY, MEDIUM, HARD)
DIFFICULTY_LABELS = {EASY: "Easy", MEDIUM: "Medium", HARD: "Hard"}
DIFFICULTY_POINTS = {EASY: 100, MEDIUM: 250, HARD: 500}

NUM_CHOICES = 4
NOTHING_PRINTED = "(nothing is printed)"
MAX_CHOICE_LINES = 6
MAX_CHOICE_LINE_LEN = 60


class GenerationError(Exception):
    """Raised when a generator cannot produce a valid question for a seed."""


@dataclass
class Question:
    topic: str
    difficulty: int
    prompt: str
    choices: list[str]
    answer: int
    explanation: str
    code: str | None = None
    # "output": choices[answer] is exactly what ``code`` prints (tests re-run it).
    # "other": any other question style (value of an expression, concept, ...).
    kind: str = "other"

    @property
    def points(self) -> int:
        return DIFFICULTY_POINTS[self.difficulty]

    def public_dict(self) -> dict:
        """Everything the client may see before answering (no answer!)."""
        return {
            "topic": self.topic,
            "difficulty": self.difficulty,
            "difficulty_label": DIFFICULTY_LABELS[self.difficulty],
            "points": self.points,
            "prompt": self.prompt,
            "code": self.code,
            "choices": list(self.choices),
        }


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

GeneratorFn = Callable[[random.Random], Question]


@dataclass
class RegisteredGenerator:
    topic: str
    difficulty: int
    fn: GeneratorFn
    name: str = field(default="")


REGISTRY: list[RegisteredGenerator] = []


def generator(topic: str, difficulty: int):
    """Decorator registering ``fn(rng) -> Question`` for a topic/difficulty."""
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"bad difficulty {difficulty!r}")

    def deco(fn: GeneratorFn) -> GeneratorFn:
        REGISTRY.append(
            RegisteredGenerator(topic, difficulty, fn, f"{fn.__module__}.{fn.__name__}")
        )
        return fn

    return deco


# --------------------------------------------------------------------------
# Running snippets
# --------------------------------------------------------------------------

_EXEC_LOCK = threading.Lock()


@dataclass
class RunResult:
    output: str  # captured stdout with the final newline stripped
    error: str | None  # exception class name, or None if it ran cleanly
    namespace: dict


def run_code(code: str) -> RunResult:
    """Execute a *generated* snippet and capture what it prints.

    Only ever call this on code produced by our own generators, never on user
    input. ``print`` is redirected per call (not via sys.stdout) so concurrent
    requests can't interleave output; the lock is belt-and-braces.
    """
    buf = io.StringIO()

    def _print(*args, **kwargs):
        kwargs.setdefault("file", buf)
        builtins.print(*args, **kwargs)

    ns: dict = {"__name__": "__main__", "print": _print}
    error = None
    with _EXEC_LOCK:
        try:
            exec(compile(code, "<snippet>", "exec"), ns)
        except Exception as exc:  # noqa: BLE001 - we want the class name
            error = type(exc).__name__
    out = buf.getvalue()
    if out.endswith("\n"):
        out = out[:-1]
    return RunResult(out, error, ns)


def eval_expr(expr: str, setup: str = "") -> object:
    """Evaluate ``expr`` after running ``setup``. Raises on error."""
    res = run_code(setup)
    if res.error:
        raise GenerationError(f"setup raised {res.error}")
    ns = res.namespace
    with _EXEC_LOCK:
        return eval(compile(expr, "<expr>", "eval"), ns)


def error_choice(exc_name: str) -> str:
    """How a raised exception is shown as an answer choice."""
    return f"Error: {exc_name}"


def display_output(output: str) -> str:
    return output if output != "" else NOTHING_PRINTED


# --------------------------------------------------------------------------
# Building questions
# --------------------------------------------------------------------------


def _norm(choice: str) -> str:
    return "\n".join(line.rstrip() for line in str(choice).strip("\n").split("\n"))


def _check_choice_shape(choice: str) -> None:
    lines = choice.split("\n")
    if len(lines) > MAX_CHOICE_LINES:
        raise GenerationError(f"choice has {len(lines)} lines: {choice!r}")
    for line in lines:
        if len(line) > MAX_CHOICE_LINE_LEN:
            raise GenerationError(f"choice line too long: {line!r}")
    if not choice.strip():
        raise GenerationError("empty choice")


def build_question(
    *,
    topic: str,
    difficulty: int,
    prompt: str,
    correct: str,
    distractors: Iterable[str],
    explanation: str,
    rng: random.Random,
    code: str | None = None,
    kind: str = "other",
) -> Question:
    """Assemble a multiple-choice question.

    ``distractors`` may contain duplicates or even the correct answer; they are
    de-duplicated (after normalising whitespace) and the first three distinct
    wrong ones are used, in the order given.  Put your most plausible wrong
    answers first.  Raises :class:`GenerationError` if fewer than three remain.
    """
    correct = _norm(correct)
    seen = {correct}
    wrong: list[str] = []
    for d in distractors:
        d = _norm(d)
        if d in seen or not d.strip():
            continue
        seen.add(d)
        wrong.append(d)
        if len(wrong) == NUM_CHOICES - 1:
            break
    if len(wrong) < NUM_CHOICES - 1:
        raise GenerationError(f"only {len(wrong)} distinct distractors for {correct!r}")
    choices = [correct, *wrong]
    for c in choices:
        _check_choice_shape(c)
    rng.shuffle(choices)
    return Question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        choices=choices,
        answer=choices.index(correct),
        explanation=explanation,
        code=code,
        kind=kind,
    )


def output_question(
    *,
    topic: str,
    difficulty: int,
    code: str,
    distractors: Iterable[str],
    explanation: str,
    rng: random.Random,
    prompt: str = "What does this code print?",
    allow_error: bool = False,
) -> Question:
    """'What does this print?' — the correct answer is computed by running ``code``.

    If ``allow_error`` is true and the code raises, the correct answer becomes
    ``error_choice(ExcName)`` (and the prompt should say so, e.g. "What is
    printed, or which error is raised?").  Otherwise raising is a bug.
    Empty output is shown as :data:`NOTHING_PRINTED`.
    """
    code = code.strip("\n")
    res = run_code(code)
    if res.error:
        if not allow_error:
            raise GenerationError(f"snippet raised {res.error}:\n{code}")
        correct = error_choice(res.error)
    else:
        correct = display_output(res.output)
    return build_question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=[display_output(d) if d == "" else d for d in distractors],
        explanation=explanation,
        rng=rng,
        code=code,
        kind="output",
    )


def which_expression_question(
    *,
    topic: str,
    difficulty: int,
    prompt: str,
    setup: str,
    target: object,
    correct_expr: str,
    wrong_exprs: Iterable[str],
    explanation: str,
    rng: random.Random,
) -> Question:
    """'Which expression evaluates to X?' — verified by evaluation.

    ``correct_expr`` must evaluate to ``target``; any wrong expression that
    *also* evaluates to ``target`` (or raises, if target isn't an error) is
    discarded automatically, so exactly one choice is right.
    """
    if eval_expr(correct_expr, setup) != target:
        raise GenerationError(f"{correct_expr!r} does not evaluate to {target!r}")
    wrong = []
    for e in wrong_exprs:
        try:
            val = eval_expr(e, setup)
        except Exception:  # noqa: BLE001 - erroring expressions are fine distractors
            wrong.append(e)
            continue
        # Drop anything equal to the target (6.0 == 6 would make two right answers).
        if val != target:
            wrong.append(e)
    return build_question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct_expr,
        distractors=wrong,
        explanation=explanation,
        rng=rng,
        code=setup.strip("\n") or None,
    )


# --------------------------------------------------------------------------
# Small helpers for making varied snippets / distractors
# --------------------------------------------------------------------------

VAR_NAMES = ["a", "b", "c", "x", "y", "z", "n", "m", "total", "count", "val", "num"]
WORDS = [
    "apple", "banana", "cherry", "python", "code", "loop", "snake", "pixel",
    "rocket", "tiger", "lemon", "mango", "orbit", "quest", "blook", "candy",
]
NAMES = ["Ava", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon"]


def pick_vars(rng: random.Random, k: int) -> list[str]:
    return rng.sample(VAR_NAMES, k)


def int_distractors(correct: int, rng: random.Random, spread: int = 3) -> list[str]:
    """Nearby integers, shuffled — a generic fallback for numeric answers."""
    cands = {correct + d for d in range(-spread, spread + 1) if d}
    cands |= {correct * 2, -correct}
    cands.discard(correct)
    out = sorted(cands)
    rng.shuffle(out)
    return [str(c) for c in out]
