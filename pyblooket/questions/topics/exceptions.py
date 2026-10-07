"""Question generators for the "exceptions" topic (Exceptions).

Covers naming the exception a line raises, try/except flow (the rest of the
``try`` block is skipped once something fails), ``else`` and ``finally``,
several ``except`` clauses and the exception hierarchy (``LookupError``,
``Exception``, the first matching clause wins), raising exceptions with
``raise``, custom exception classes, exceptions raised inside handlers or
``else`` blocks, nested ``try`` blocks, exceptions propagating out of
functions, re-raising with a bare ``raise``, and ``finally`` running on
``return`` / ``break`` / ``continue``.

Only exception *class names* ever appear in choices, never message text.
"""

from __future__ import annotations

import random
import re
from typing import NamedTuple

from ..base import (
    EASY,
    HARD,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    MEDIUM,
    NAMES,
    NOTHING_PRINTED,
    WORDS,
    GenerationError,
    Question,
    build_question,
    display_output,
    error_choice,
    generator,
    int_distractors,
    output_question,
    run_code,
)

TOPIC = "exceptions"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
BLANK = "____"
MAX_SNIPPET_LINES = 14


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _code(*lines: str | None) -> str:
    """Join snippet lines (skipping ``None``) and enforce the length limit."""
    code = "\n".join(line for line in lines if line is not None)
    if len(code.split("\n")) > MAX_SNIPPET_LINES:
        raise GenerationError(f"snippet too long:\n{code}")
    return code


def _prog(*blocks: str) -> str:
    """Join top-level blocks (class/def, main code) with two blank lines (PEP 8)."""
    return _code("\n\n\n".join(b.strip("\n") for b in blocks))


def _lines(*parts) -> str:
    """Printed output, one part per line ("(nothing is printed)" if empty)."""
    return "\n".join(str(p) for p in parts) if parts else NOTHING_PRINTED


def _fits(choice: str) -> bool:
    lines = [line.rstrip() for line in choice.strip("\n").split("\n")]
    return (
        bool(choice.strip())
        and len(lines) <= MAX_CHOICE_LINES
        and all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines)
    )


def _usable(distractors) -> list[str]:
    """Stringify distractors and drop any that would not fit on a choice button."""
    out = []
    for d in distractors:
        if d is None:
            continue
        d = display_output(str(d))
        if _fits(d):
            out.append(d)
    return out


def _output(
    code: str,
    difficulty: int,
    distractors,
    explanation: str,
    rng: random.Random,
    *,
    prompt: str = PRINT,
    allow_error: bool = False,
) -> Question:
    """An output question. If the snippet prints something and *then* raises,
    a distractor equal to that partial output would be half-right, so drop it."""
    distractors = _usable(distractors)
    res = run_code(code)
    if res.error and res.output:
        partial = display_output(res.output).strip()
        distractors = [d for d in distractors if d.strip() != partial]
    q = output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=distractors,
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )
    if q.prompt == PRINT and any(c.startswith("Error: ") for c in q.choices):
        q.prompt = PRINT_OR_ERROR  # an "Error: ..." choice needs the wider prompt
    return q


def _choice(
    *,
    difficulty: int,
    prompt: str,
    code: str | None,
    correct: str,
    distractors,
    explanation: str,
    rng: random.Random,
) -> Question:
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=str(correct),
        distractors=_usable(distractors),
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _raised(code: str) -> str | None:
    """Name of the exception ``code`` raises (None if it runs cleanly)."""
    return run_code(code).error


def _expr_raises(expr: str, setup: str = "") -> str | None:
    """Name of the exception evaluating ``expr`` raises after ``setup`` runs."""
    return run_code(_code(setup or None, f"_ = {expr}")).error


def _labels(rng: random.Random, n: int) -> list[str]:
    """``n`` consecutive capital letters used as print markers (A B C ... / P Q R ...)."""
    start = rng.choice("AFKP")
    return [chr(ord(start) + i) for i in range(n)]


def _dict_src(pairs) -> str:
    """A dict literal written with double quotes, like a person would type it."""
    return "{" + ", ".join(f'"{k}": {v}' for k, v in pairs) + "}"


def _list_src(strings) -> str:
    """A list-of-strings literal written with double quotes."""
    return "[" + ", ".join(f'"{s}"' for s in strings) + "]"


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _a(word: str) -> str:
    """``word`` with the right indefinite article ("a GameError", "an AppError")."""
    return ("an " if word[:1].lower() in "aeiou" else "a ") + word


def _short_words(max_len: int = 6) -> list[str]:
    return [w for w in WORDS if len(w) <= max_len]


# A small catalogue of "risky" operations that raise a given exception only
# when ``fail`` is true, so the same snippet shape can go either way.

_FALLBACK = {
    "ZeroDivisionError": ["cannot divide", "no groups", "divide error"],
    "ValueError": ["not a number", "bad number", "invalid input"],
    "IndexError": ["no such item", "out of range", "bad position"],
    "KeyError": ["not found", "unknown item", "missing"],
    "TypeError": ["wrong type", "type problem", "mixed types"],
}

# Variable that receives the risky value inside a ``try`` block.
_TARGET = {
    "ZeroDivisionError": "share",
    "ValueError": "number",
    "IndexError": "item",
    "KeyError": "price",
    "TypeError": "label",
}

_MENUS = [
    ("prices", ["tea", "cake", "pie", "bun", "soup", "juice"]),
    ("stock", ["apples", "pears", "plums", "kiwis", "limes"]),
    ("ages", ["Ava", "Ben", "Cara", "Dev", "Eli", "Fay"]),
]


class _Risky(NamedTuple):
    setup: str | None  # line to put before the ``try`` (None if inline)
    expr: str  # expression that raises ``exc`` iff ``fail``
    near: list[str]  # plausible WRONG outputs of ``print(expr)``
    why: str  # short reason this expr raises / works


def _risky(rng: random.Random, exc: str, fail: bool, *, inline: bool = False) -> _Risky:
    if exc == "ZeroDivisionError":
        total = rng.choice([12, 18, 20, 24, 30, 36])
        op = rng.choice(["//", "/"])
        k = 0 if fail else rng.choice([d for d in (2, 3, 4, 6) if total % d == 0])
        if inline:
            setup, expr = None, f"{total} {op} {k}"
        else:
            name = rng.choice(["count", "groups", "people", "teams"])
            setup, expr = f"{name} = {k}", f"{total} {op} {name}"
        if fail:
            near = ["0", str(total)] if op == "//" else ["0.0", "0"]
            why = f"dividing by zero is impossible, so `{expr}` raises ZeroDivisionError"
        else:
            q = total // k
            near = [f"{q}.0", "0"] if op == "//" else [str(q), "0"]
            why = f"`{expr}` divides by {k}, which is fine"
        return _Risky(setup, expr, near, why)

    if exc == "ValueError":
        if fail:
            text = rng.choice(["ten", "abc", "seven", "12a", "two", "five"])
        else:
            text = str(rng.randint(10, 99))
        if inline:
            setup, expr = None, f'int("{text}")'
        else:
            setup, expr = f'text = "{text}"', "int(text)"
        if fail:
            near = [text, "0"]
            why = f'`"{text}"` is not a whole number, so `{expr}` raises ValueError'
        else:
            near = [f"'{text}'", str(int(text) + 1)]
            why = f'`{expr}` turns `"{text}"` into the number {text}'
        return _Risky(setup, expr, near, why)

    if exc == "IndexError":
        name = rng.choice(["nums", "scores", "points", "values"])
        items = rng.sample(range(2, 30), rng.choice([3, 4]))
        i = len(items) if fail else rng.randrange(len(items))
        setup, expr = f"{name} = {items}", f"{name}[{i}]"
        if fail:
            near = [str(items[-1]), "None"]
            why = (
                f"`{name}` has {len(items)} items, so its indexes are 0 to {len(items) - 1}; "
                f"`{expr}` raises IndexError"
            )
        else:
            j = i + 1 if i + 1 < len(items) else i - 1
            near = [str(items[j]), "None"]
            why = f"`{expr}` is item number {i} (counting from 0), which is {items[i]}"
        return _Risky(setup, expr, near, why)

    if exc == "KeyError":
        dname, keys = rng.choice(_MENUS)
        k1, k2, missing = rng.sample(keys, 3)
        v1, v2 = rng.sample(range(2, 15), 2)
        key = missing if fail else rng.choice([k1, k2])
        setup = f"{dname} = {_dict_src([(k1, v1), (k2, v2)])}"
        expr = f'{dname}["{key}"]'
        if fail:
            near = ["None", "0"]
            why = f'`"{key}"` is not a key in `{dname}`, so `{expr}` raises KeyError'
        else:
            other = v2 if key == k1 else v1
            near = [str(other), "None"]
            why = f'`"{key}"` is a key in `{dname}`, so `{expr}` works'
        return _Risky(setup, expr, near, why)

    if exc == "TypeError":
        var = rng.choice(["score", "level", "age", "lives"])
        n = rng.randint(2, 20)
        setup = f"{var} = {n}" if fail else f'{var} = "{n}"'
        expr = f'"{var.title()}: " + {var}'
        if fail:
            near = [f"{var.title()}: {n}", f"{var.title()}: {var}"]
            why = f"`{var}` is an int, and `+` cannot join a str and an int, so `{expr}` raises TypeError"
        else:
            near = [f"{var.title()}:{n}", f"{var.title()}: {var}"]
            why = f'`{var}` is the string `"{n}"`, so `+` simply joins two strings'
        return _Risky(setup, expr, near, why)

    raise GenerationError(f"no risky template for {exc}")


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_name_the_error(rng: random.Random) -> Question:
    """Which exception class does a short snippet raise?"""
    kind = rng.choice(["zero", "index", "key", "type", "value", "name", "attr"])
    if kind == "zero":
        name = rng.choice(["count", "players", "boxes", "teams"])
        total = rng.randint(10, 60)
        op = rng.choice(["/", "//", "%"])
        code = f"{name} = 0\nprint({total} {op} {name})"
        exc = "ZeroDivisionError"
        wrong = ["ValueError", "TypeError", "NameError", "IndexError"]
        why = (
            f"`{name}` is 0, and dividing by zero is impossible, so `{total} {op} {name}` raises "
            "ZeroDivisionError (`/`, `//` and `%` all do)."
        )
    elif kind == "index":
        exc = "IndexError"
        wrong = ["KeyError", "ValueError", "TypeError", "NameError"]
        if rng.random() < 0.5:
            name = rng.choice(["nums", "scores", "ages", "points"])
            items = rng.sample(range(1, 40), rng.randint(3, 5))
            n = len(items)
            code = f"{name} = {items}\nprint({name}[{n}])"
            why = (
                f"`{name}` has {n} items, so its valid indexes are 0 to {n - 1}. "
                f"Index {n} is past the end, which raises IndexError."
            )
        else:
            word = rng.choice(_short_words())
            n = len(word)
            code = f'word = "{word}"\nprint(word[{n}])'
            why = (
                f'`"{word}"` has {n} characters at indexes 0 to {n - 1}, so `word[{n}]` '
                "is out of range and raises IndexError."
            )
    elif kind == "key":
        exc = "KeyError"
        wrong = ["IndexError", "ValueError", "NameError", "TypeError"]
        dname, keys = rng.choice(_MENUS)
        k1, k2, missing = rng.sample(keys, 3)
        v1, v2 = rng.sample(range(1, 15), 2)
        code = f'{dname} = {_dict_src([(k1, v1), (k2, v2)])}\nprint({dname}["{missing}"])'
        why = (
            f'Looking up a key that is not in a dict raises KeyError, and `"{missing}"` is not '
            f"one of the keys of `{dname}`."
        )
    elif kind == "type":
        exc = "TypeError"
        wrong = ["ValueError", "NameError", "AttributeError", "SyntaxError"]
        var = rng.choice(["age", "score", "level", "lives"])
        n = rng.randint(2, 30)
        shape = rng.choice(["str_plus_int", "int_plus_str", "len_int"])
        if shape == "str_plus_int":
            code = f'{var} = {n}\nprint("{var.title()}: " + {var})'
            why = f"`+` cannot join a str and an int (`{var}` is {n}), so Python raises TypeError."
        elif shape == "int_plus_str":
            k = rng.randint(1, 9)
            code = f'{var} = {n}\nprint({var} + "{k}")'
            why = f'`{var} + "{k}"` adds an int to a str, which Python refuses with a TypeError.'
        else:
            code = f"{var} = {n * 100 + 7}\nprint(len({var}))"
            why = "An int has no length, so `len()` raises TypeError (you'd need `len(str(...))`)."
    elif kind == "value":
        exc = "ValueError"
        wrong = ["TypeError", "NameError", "KeyError", "SyntaxError"]
        text = rng.choice(["ten", "abc", "seven", "4x", "hello", "one"])
        func = rng.choice(["int", "int", "float"])
        code = f'text = "{text}"\nnumber = {func}(text)'
        why = (
            f'`{func}()` accepts a string, so the type is fine, but `"{text}"` is not a number. '
            "A right-type-but-bad-value argument raises ValueError."
        )
    elif kind == "name":
        exc = "NameError"
        wrong = ["SyntaxError", "ValueError", "TypeError", "KeyError"]
        var = rng.choice(["score", "total", "points", "count"])
        n = rng.randint(2, 20)
        if rng.random() < 0.5:
            code = f"print({var} + 1)\n{var} = {n}"
            why = (
                f"Lines run top to bottom, so `{var}` doesn't exist yet when `print` uses it. "
                "Using a name that hasn't been assigned raises NameError."
            )
        else:
            other = rng.choice(["bonus", "extra", "tax"])
            code = f"{var} = {n}\nprint({var} + {other})"
            why = f"`{other}` was never assigned, so Python doesn't know that name and raises NameError."
    else:
        exc = "AttributeError"
        wrong = ["TypeError", "ValueError", "NameError", "KeyError"]
        shape = rng.choice(["tuple", "str", "int"])
        if shape == "tuple":
            a, b, c = rng.sample(range(1, 10), 3)
            code = f"point = ({a}, {b})\npoint.append({c})"
            why = "Tuples are immutable and have no `append` method; calling a method that doesn't exist raises AttributeError."
        elif shape == "str":
            word = rng.choice(_short_words())
            code = f'word = "{word}"\nword.append("!")'
            why = "Strings have no `append` method (that's a list method), so Python raises AttributeError."
        else:
            n = rng.randint(2, 50)
            code = f"count = {n}\nprint(count.upper())"
            why = "`upper` is a string method; an int has no attribute called `upper`, so this raises AttributeError."
    if _raised(code) != exc:
        raise GenerationError(f"expected {exc}:\n{code}")
    return _choice(
        difficulty=EASY,
        prompt="Which exception does this code raise?",
        code=code,
        correct=exc,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_try_except_basic(rng: random.Random) -> Question:
    """Does the except block run? Only if the try block actually fails."""
    exc = rng.choice(["ZeroDivisionError", "ValueError", "IndexError", "KeyError"])
    fail = rng.random() < 0.6
    r = _risky(rng, exc, fail)
    fallback = rng.choice(_FALLBACK[exc])
    code = _code(
        r.setup,
        "try:",
        f"    print({r.expr})",
        f"except {exc}:",
        f'    print("{fallback}")',
    )
    if fail:
        distractors = [
            r.near[0],
            error_choice(exc),
            r.near[1],
            NOTHING_PRINTED,
            _lines(r.near[0], fallback),
        ]
        why = (
            f"{_cap(r.why)}. Python jumps straight to the matching "
            f"`except {exc}` block, so it prints `{fallback}` instead of crashing."
        )
    else:
        value = run_code(code).output
        distractors = [fallback, _lines(value, fallback), r.near[0], error_choice(exc), r.near[1]]
        why = (
            f"{_cap(r.why)}: it prints {value}. No exception is raised, so "
            "the `except` block is skipped entirely."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_skip_rest_of_try(rng: random.Random) -> Question:
    """Once a line in try fails, the rest of the try block is skipped."""
    exc = rng.choice(["ValueError", "ValueError", "ZeroDivisionError", "IndexError", "KeyError"])
    fail = rng.random() < 0.75
    r = _risky(rng, exc, fail, inline=exc == "ValueError")
    a, b, c, d = _labels(rng, 4)
    has_before = rng.random() < 0.7
    has_after = not has_before or rng.random() < 0.6
    code = _code(
        r.setup,
        "try:",
        f'    print("{a}")' if has_before else None,
        f"    {_TARGET[exc]} = {r.expr}",
        f'    print("{b}")',
        f"except {exc}:",
        f'    print("{c}")',
        f'print("{d}")' if has_after else None,
    )
    pre = [a] if has_before else []
    post = [d] if has_after else []
    if fail:
        distractors = [
            _lines(*pre, b, c, *post),  # the rest of the try block still runs
            _lines(c, *post),  # earlier prints are "undone"
            _lines(*pre, c),  # the program stops after the handler
            _lines(*pre, b, *post),  # the error is ignored
            _lines(*pre, *post),
            error_choice(exc),
        ]
        why = (
            f"{_cap(r.why)}. The moment that happens, the rest of the `try` "
            f'block is skipped (so `"{b}"` never prints) and the `except` block runs. '
            "Anything printed before the error stays printed, and the program carries on after the handler."
        )
    else:
        distractors = [
            _lines(*pre, b, c, *post),  # except always runs
            _lines(*pre, c, *post),
            _lines(*pre, b),
            error_choice(exc),
            _lines(*pre, *post),
        ]
        why = (
            f"{_cap(r.why)}, so no exception happens: the whole `try` block "
            "runs and the `except` block is skipped."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_finally_always(rng: random.Random) -> Question:
    """finally runs whether or not an exception happened."""
    exc = rng.choice(["ZeroDivisionError", "ValueError", "IndexError", "KeyError"])
    fail = rng.random() < 0.55
    r = _risky(rng, exc, fail)
    fallback = rng.choice(_FALLBACK[exc])
    end = rng.choice(["done", "finished", "all done", "goodbye", "the end"])
    code = _code(
        r.setup,
        "try:",
        f"    print({r.expr})",
        f"except {exc}:",
        f'    print("{fallback}")',
        "finally:",
        f'    print("{end}")',
    )
    if fail:
        distractors = [
            fallback,  # forgets finally
            _lines(end, fallback),
            end,  # thinks finally replaces the handler
            _lines(r.near[0], end),
            error_choice(exc),
        ]
        why = (
            f"{_cap(r.why)}, which the `except` block catches, printing `{fallback}`. "
            f"The `finally` block runs no matter what, so `{end}` is printed afterwards."
        )
    else:
        value = run_code(code).output.split("\n")[0]
        distractors = [
            value,  # thinks finally only runs after an error
            _lines(value, fallback, end),
            _lines(fallback, end),
            _lines(end, value),
            r.near[0],
        ]
        why = (
            f"{_cap(r.why)}, so it prints {value} and the `except` block is "
            f"skipped. `finally` runs whether or not there was an error, so `{end}` follows."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_else_clause(rng: random.Random) -> Question:
    """else runs only when the try block raised nothing."""
    exc = rng.choice(["ZeroDivisionError", "ValueError", "IndexError", "KeyError"])
    fail = rng.random() < 0.5
    r = _risky(rng, exc, fail)
    fallback = rng.choice(_FALLBACK[exc])
    has_after = rng.random() < 0.5
    after = rng.choice(["bye", "done", "next"])
    code = _code(
        r.setup,
        "try:",
        f"    result = {r.expr}",
        f"except {exc}:",
        f'    print("{fallback}")',
        "else:",
        "    print(result)",
        f'print("{after}")' if has_after else None,
    )
    post = [after] if has_after else []
    if fail:
        distractors = [
            error_choice("NameError"),  # else runs, but result was never assigned
            _lines(fallback, r.near[0], *post),
            _lines(*post) if post else r.near[0],
            _lines(r.near[0], *post),
            error_choice(exc),
        ]
        why = (
            f"{_cap(r.why)}, which the `except` block catches, printing `{fallback}`. "
            "The `else` block runs only when the `try` block raised nothing, so it is skipped."
        )
    else:
        value = run_code(code).output.split("\n")[0]
        distractors = [
            _lines(fallback, value, *post),  # thinks except always runs too
            _lines(value, fallback, *post),
            _lines(fallback, *post),
            _lines(r.near[0], *post),
            _lines(*post) if post else error_choice(exc),
        ]
        why = (
            f"{_cap(r.why)}, so no exception happens: `except` is skipped and "
            f"the `else` block prints `result`, which is {value}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_RAISE_CHECKS = [
    # (variable, condition with {v}, values that trigger, values that don't, message)
    ("age", "{v} < 0", [-5, -3, -1], [7, 12, 15], "age cannot be negative"),
    ("speed", "{v} > 100", [120, 130, 150], [60, 80, 95], "too fast"),
    ("quantity", "{v} == 0", [0], [2, 3, 4, 5], "quantity cannot be zero"),
    ("score", "{v} > 10", [11, 12, 20], [3, 7, 9, 10], "score must be at most 10"),
]


@generator(TOPIC, EASY)
def gen_raise_statement(rng: random.Random) -> Question:
    """`raise` stops normal flow right there (and can be caught like any error)."""
    var, cond_src, bad_vals, ok_vals, msg = rng.choice(_RAISE_CHECKS)
    triggered = rng.random() < 0.55
    value = rng.choice(bad_vals if triggered else ok_vals)
    cond = cond_src.format(v=var)
    mult = rng.randint(2, 3)
    raise_line = rng.choice([f'raise ValueError("{msg}")', "raise ValueError"])
    if rng.random() < 0.5:
        code = _code(
            f"{var} = {value}",
            f"if {cond}:",
            f"    {raise_line}",
            f"print({var} * {mult})",
        )
        if triggered:
            distractors = [
                str(value * mult),
                NOTHING_PRINTED,
                error_choice("TypeError"),
                str(value),
                "None",
            ]
            why = (
                f"`{cond}` is True for {value}, so `raise ValueError` runs. Nothing catches it, so the "
                "program stops with a ValueError before reaching `print`."
            )
        else:
            distractors = [
                error_choice("ValueError"),
                NOTHING_PRINTED,
                str(value),
                str(value + mult),
            ]
            why = (
                f"`{cond}` is False for {value}, so the `raise` line is skipped and the program "
                f"prints {value} * {mult} = {value * mult}."
            )
        return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)

    ok_msg = rng.choice(["accepted", "ok", "saved"])
    bad_msg = rng.choice(["rejected", "invalid", "try again"])
    code = _code(
        f"{var} = {value}",
        "try:",
        f"    if {cond}:",
        f"        {raise_line}",
        f'    print("{ok_msg}")',
        "except ValueError:",
        f'    print("{bad_msg}")',
    )
    if triggered:
        distractors = [
            _lines(ok_msg, bad_msg),
            ok_msg,
            error_choice("ValueError"),
            _lines(bad_msg, ok_msg),
        ]
        why = (
            f"`{cond}` is True for {value}, so `raise ValueError` runs. That skips the rest of the "
            f"`try` block, and `except ValueError` catches it and prints `{bad_msg}`."
        )
    else:
        distractors = [
            _lines(ok_msg, bad_msg),
            bad_msg,
            error_choice("ValueError"),
            NOTHING_PRINTED,
        ]
        why = (
            f"`{cond}` is False for {value}, so nothing is raised: `{ok_msg}` is printed and the "
            "`except` block is skipped."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


# Most plausible wrong except-clause names for each exception, best first.
_CONFUSED_WITH = {
    "ZeroDivisionError": ["ValueError", "TypeError", "IndexError", "NameError"],
    "ValueError": ["TypeError", "NameError", "KeyError", "IndexError"],
    "IndexError": ["KeyError", "ValueError", "TypeError", "NameError"],
    "KeyError": ["IndexError", "ValueError", "NameError", "TypeError"],
    "TypeError": ["ValueError", "NameError", "AttributeError", "KeyError"],
}


@generator(TOPIC, EASY)
def gen_fill_except_blank(rng: random.Random) -> Question:
    """Pick the exception name that makes the handler catch the error."""
    exc = rng.choice(list(_CONFUSED_WITH))
    r = _risky(rng, exc, True)
    fallback = rng.choice(_FALLBACK[exc])

    def build(name: str) -> str:
        return _code(
            r.setup, "try:", f"    print({r.expr})", f"except {name}:", f'    print("{fallback}")'
        )

    if run_code(build(exc)).output != fallback:
        raise GenerationError("correct exception does not produce the fallback")
    pool = _CONFUSED_WITH[exc][:]
    first, rest = pool[0], pool[1:]
    rng.shuffle(rest)
    # Each wrong name must NOT make the snippet print the fallback.
    wrong = [n for n in [first, *rest] if run_code(build(n)).output != fallback]
    return _choice(
        difficulty=EASY,
        prompt=f"Which exception name fills the blank so the code prints `{fallback}`?",
        code=build(BLANK),
        correct=exc,
        distractors=wrong,
        explanation=(
            f"{_cap(r.why)}. An `except` clause only catches the exception type it "
            f"names (or its subclasses), so it must say `{exc}`."
        ),
        rng=rng,
    )


# ==========================================================================
# MEDIUM
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_except_clause_match(rng: random.Random) -> Question:
    """Several except clauses: which one handles the first thing that fails?"""
    k1, k2, k3 = rng.sample(["red", "blue", "green", "gold", "pink", "gray"], 3)
    n = rng.choice([12, 24, 36, 60])
    divisors = [d for d in (2, 3, 4, 6) if n % d == 0]
    long_list = rng.sample(divisors, 3)
    short_list = [rng.choice(divisors)]
    case = rng.choice(["key", "index", "zero", "zero", "ok"])
    zero_pos = rng.randrange(3)
    if case == "zero":
        long_list[zero_pos] = 0
    elif rng.random() < 0.5:
        long_list[zero_pos] = 0  # a zero that isn't touched this time
    data = {k1: long_list, k2: short_list}
    if case == "key":
        key, i = k3, rng.choice([0, 1, 3])
    elif case == "index":
        key, i = rng.choice([(k1, 3), (k2, 1), (k2, 2)])
    elif case == "zero":
        key, i = k1, zero_pos
    else:
        key = rng.choice([k1, k2])
        i = rng.choice([j for j, v in enumerate(data[key]) if v != 0])
    labels = {"KeyError": "no key", "IndexError": "bad index", "ZeroDivisionError": "zero"}
    order = list(labels)
    rng.shuffle(order)
    handlers = []
    for exc in order:
        handlers += [f"except {exc}:", f'    print("{labels[exc]}")']
    code = _code(
        f"data = {_dict_src([(k1, long_list), (k2, short_list)])}",
        "try:",
        f'    nums = data["{key}"]',
        f"    print({n} // nums[{i}])",
        *handlers,
    )
    if case == "key":
        distractors = [
            labels["IndexError"],
            error_choice("KeyError"),
            _lines("no key", "bad index"),
            labels["ZeroDivisionError"],
        ]
        why = (
            f'`data["{key}"]` fails first: there is no key `"{key}"`, so KeyError is raised and the '
            "next line never runs. Python picks the `except KeyError` clause."
        )
    elif case == "index":
        lst = data[key]
        first_ok = next((v for v in lst if v), 1)
        distractors = [
            labels["KeyError"],
            labels["ZeroDivisionError"],
            error_choice("IndexError"),
            str(n // first_ok),
        ]
        why = (
            f'`data["{key}"]` is {lst}, which has no index {i}, so `nums[{i}]` raises IndexError '
            "and only the `except IndexError` clause runs."
        )
    elif case == "zero":
        distractors = [
            labels["IndexError"],
            "0",
            error_choice("ZeroDivisionError"),
            labels["KeyError"],
        ]
        why = (
            f"`nums[{i}]` is 0, so `{n} // 0` raises ZeroDivisionError and Python runs the matching "
            "`except ZeroDivisionError` clause, skipping the others."
        )
    else:
        val = data[key][i]
        distractors = [
            str(n / val),
            labels["IndexError"],
            labels["ZeroDivisionError"],
            labels["KeyError"],
        ]
        why = (
            f'`data["{key}"][{i}]` is {val}, so `{n} // {val}` = {n // val} is printed. Nothing fails, '
            "so none of the `except` clauses run."
        )
    expected = str(n // data[key][i]) if case == "ok" else labels[_CASE_EXC[case]]
    if run_code(code).output != expected:
        raise GenerationError("unexpected outcome")
    return _output(code, MEDIUM, distractors, why, rng, allow_error=True, prompt=PRINT_OR_ERROR)


_CASE_EXC = {"key": "KeyError", "index": "IndexError", "zero": "ZeroDivisionError"}


# (raised exception, the two except clauses in order)
_HIERARCHY_CASES = [
    ("KeyError", ["IndexError", "LookupError"]),
    ("IndexError", ["KeyError", "LookupError"]),
    ("KeyError", ["LookupError", "KeyError"]),
    ("IndexError", ["LookupError", "IndexError"]),
    ("ValueError", ["Exception", "ValueError"]),
    ("ZeroDivisionError", ["ValueError", "Exception"]),
    ("KeyError", ["ValueError", "Exception"]),
    ("KeyError", ["IndexError", "ValueError"]),
    ("IndexError", ["KeyError", "TypeError"]),
    ("ValueError", ["LookupError", "TypeError"]),
]

_PARENTS = {
    "KeyError": ["LookupError", "Exception"],
    "IndexError": ["LookupError", "Exception"],
    "ValueError": ["Exception"],
    "ZeroDivisionError": ["ArithmeticError", "Exception"],
}

_CLAUSE_LABEL = {
    "KeyError": "key",
    "IndexError": "index",
    "LookupError": "lookup",
    "ValueError": "value",
    "TypeError": "type",
    "Exception": "general",
}


@generator(TOPIC, MEDIUM)
def gen_hierarchy_catch(rng: random.Random) -> Question:
    """A parent class (LookupError, Exception) catches its subclasses; first match wins."""
    exc, clauses = rng.choice(_HIERARCHY_CASES)
    r = _risky(rng, exc, True)
    labels = [_CLAUSE_LABEL[c] for c in clauses]
    code = _code(
        r.setup,
        "try:",
        f"    print({r.expr})",
        f"except {clauses[0]}:",
        f'    print("{labels[0]}")',
        f"except {clauses[1]}:",
        f'    print("{labels[1]}")',
    )
    matches = [c for c in clauses if c == exc or c in _PARENTS[exc]]
    distractors = [labels[1], labels[0], error_choice(exc), _lines(*labels), NOTHING_PRINTED]
    if not matches:
        why = (
            f"`{r.expr}` raises {exc}. Neither `{clauses[0]}` nor `{clauses[1]}` is {exc} or one of "
            f"its parent classes, so no clause catches it and the program stops with {exc}."
        )
    else:
        hit = matches[0]
        if hit == exc:
            reason = f"`except {hit}` names it exactly"
        elif hit == "Exception":
            reason = f"almost every built-in error, {exc} included, is a subclass of `Exception`"
        else:
            reason = f"`{hit}` is the parent class of both KeyError and IndexError"
        why = f"`{r.expr}` raises {exc}, and {reason}. "
        if hit == clauses[0] and len(matches) > 1:
            why += "Python runs only the FIRST matching clause, so the second one is never reached."
        elif hit == clauses[1]:
            why += f"The first clause, `except {clauses[0]}`, doesn't match, so Python moves on to the second."
        else:
            why += "Python runs that clause and skips the rest."
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


def _gotcha_list_index(rng: random.Random):
    name = rng.choice(["nums", "scores", "ages"])
    items = rng.sample(range(5, 40), 4)
    if rng.random() < 0.7:
        x = rng.choice([v for v in range(5, 40) if v not in items])
        code = f"{name} = {items}\nprint({name}.index({x}))"
        d = ["-1", error_choice("IndexError"), "None", error_choice("KeyError")]
        why = (
            f"{x} is not in `{name}`, and `list.index` raises ValueError for a missing value. "
            "(Returning -1 is what `str.find` does; lists have no `find`.)"
        )
    else:
        i = rng.randrange(4)
        x = items[i]
        code = f"{name} = {items}\nprint({name}.index({x}))"
        d = [str(i + 1), str(x), "-1", error_choice("ValueError")]
        why = f"`{name}.index({x})` returns the position of {x}, counting from 0, which is {i}."
    return code, d, why


def _gotcha_find_vs_index(rng: random.Random):
    word = rng.choice(_short_words())
    ch = rng.choice([c for c in "xzqjvw" if c not in word])
    method = rng.choice(["find", "index"])
    code = f'word = "{word}"\nprint(word.{method}("{ch}"))'
    if method == "find":
        d = [error_choice("ValueError"), error_choice("IndexError"), "None", "0"]
        why = f'`"{ch}"` is not in `"{word}"`. `str.find` signals "not found" by returning -1; it never raises.'
    else:
        d = ["-1", error_choice("IndexError"), "None", "0"]
        why = (
            f'`"{ch}"` is not in `"{word}"`. `str.index` works like `find` but raises ValueError '
            "when the substring is missing, instead of returning -1."
        )
    return code, d, why


def _gotcha_int_float(rng: random.Random):
    whole = rng.randint(2, 9)
    frac = rng.choice([2, 5, 7, 8, 9])
    shape = rng.choice(["str", "str", "float"])
    if shape == "str":
        code = f'text = "{whole}.{frac}"\nprint(int(text))'
        d = [str(whole), str(whole + 1), f"{whole}.{frac}", error_choice("TypeError")]
        why = (
            f'`int()` only parses whole-number strings, and `"{whole}.{frac}"` contains a decimal '
            f"point, so it raises ValueError. (`int({whole}.{frac})` on the float would give {whole}.)"
        )
    else:
        code = f"price = {whole}.{frac}\nprint(int(price))"
        d = [
            str(whole + 1),
            error_choice("ValueError"),
            f"{whole}.{frac}",
            error_choice("TypeError"),
        ]
        why = (
            f"`int()` on a float just chops off the fractional part (it doesn't round), so "
            f'`int({whole}.{frac})` is {whole}. Only a string like `"{whole}.{frac}"` would raise ValueError.'
        )
    return code, d, why


def _gotcha_slice(rng: random.Random):
    name = rng.choice(["nums", "scores", "points"])
    items = rng.sample(range(2, 30), 4)
    if rng.random() < 0.55:
        start = rng.randint(1, 2)
        stop = rng.randint(6, 10)
        code = f"{name} = {items}\nprint({name}[{start}:{stop}])"
        d = [
            error_choice("IndexError"),
            str(items[start : start + 1]),
            str(items[start - 1 :]),
            "None",
        ]
        why = (
            f"Slices never raise IndexError: `{name}[{start}:{stop}]` simply stops at the end of the "
            f"list, giving {items[start:]}. Only a single index like `{name}[{stop}]` would fail."
        )
    else:
        i = rng.randint(4, 6)
        code = f"{name} = {items}\nprint({name}[{i}])"
        d = [str(items[-1]), "[]", "None", error_choice("KeyError")]
        why = (
            f"`{name}` has 4 items (indexes 0 to 3), so the single index {i} is out of range and raises "
            f"IndexError. (The slice `{name}[{i}:]` would just give `[]`.)"
        )
    return code, d, why


def _gotcha_empty(rng: random.Random):
    name = rng.choice(["scores", "prices", "times"])
    func = rng.choice(["max", "min", "sum"])
    code = f"{name} = []\nprint({func}({name}))"
    if func == "sum":
        d = [error_choice("ValueError"), "None", "[]", error_choice("TypeError")]
        why = "`sum` starts from 0 and adds each item; with no items it just returns 0, no error."
    else:
        d = ["0", "None", error_choice("IndexError"), "[]"]
        why = (
            f"An empty list has no largest or smallest item, so `{func}()` raises ValueError. "
            "(`sum([])` would happily give 0.)"
        )
    return code, d, why


def _gotcha_len_int(rng: random.Random):
    var = rng.choice(["code", "pin", "year", "number"])
    n = rng.randint(100, 99999)
    digits = len(str(n))
    if rng.random() < 0.65:
        code = f"{var} = {n}\nprint(len({var}))"
        d = [str(digits), error_choice("ValueError"), error_choice("AttributeError"), "1"]
        why = (
            f"An int has no length, so `len({var})` raises TypeError. To count digits you need "
            f"`len(str({var}))`, which would give {digits}."
        )
    else:
        code = f"{var} = {n}\nprint(len(str({var})))"
        d = [error_choice("TypeError"), str(n), "1", str(digits + 1)]
        why = f'`str({var})` is the string `"{n}"`, and `len` counts its {digits} characters.'
    return code, d, why


def _gotcha_immutable(rng: random.Random):
    shape = rng.choice(["str_item", "tuple_item", "tuple_append"])
    if shape == "str_item":
        word = rng.choice([w for w in _short_words() if len(w) >= 4])
        c = rng.choice([ch for ch in "bdfhmrst" if ch != word[0]])
        code = f'word = "{word}"\nword[0] = "{c}"\nprint(word)'
        d = [c + word[1:], word, error_choice("AttributeError"), error_choice("ValueError")]
        why = (
            "Strings are immutable: you can't change one character in place, so `word[0] = ...` "
            f'raises TypeError. Build a new string instead, e.g. `"{c}" + word[1:]`.'
        )
    elif shape == "tuple_item":
        a, b, c = rng.sample(range(1, 10), 3)
        code = f"point = ({a}, {b})\npoint[0] = {c}\nprint(point)"
        d = [
            f"({c}, {b})",
            f"({a}, {b})",
            error_choice("AttributeError"),
            error_choice("IndexError"),
        ]
        why = "Tuples are immutable, so assigning to `point[0]` raises TypeError."
    else:
        a, b, c = rng.sample(range(1, 10), 3)
        code = f"point = ({a}, {b})\npoint.append({c})\nprint(point)"
        d = [f"({a}, {b}, {c})", error_choice("TypeError"), f"[{a}, {b}, {c}]", f"({a}, {b})"]
        why = "Tuples have no `append` method at all, so looking it up raises AttributeError."
    return code, d, why


def _gotcha_get_none(rng: random.Random):
    dname, keys = rng.choice(_MENUS)
    k1, k2, missing = rng.sample(keys, 3)
    v1, v2 = rng.sample(range(2, 15), 2)
    setup = f"{dname} = {_dict_src([(k1, v1), (k2, v2)])}"
    if rng.random() < 0.6:
        code = f'{setup}\nprint({dname}.get("{missing}") + 1)'
        d = ["1", error_choice("KeyError"), "None", "2"]
        why = (
            f'`"{missing}"` is missing, so `get` returns None instead of raising KeyError. '
            "Then `None + 1` raises TypeError."
        )
    else:
        code = f'{setup}\nprint({dname}.get("{missing}", 0) + 1)'
        d = [error_choice("TypeError"), error_choice("KeyError"), "None", "0"]
        why = (
            f'`"{missing}"` is missing, so `get` returns the default 0 instead of raising, and '
            "0 + 1 is 1."
        )
    return code, d, why


def _gotcha_remove(rng: random.Random):
    name = rng.choice(["nums", "scores", "ages"])
    items = rng.sample(range(5, 30), 4)
    if rng.random() < 0.65:
        x = rng.choice([v for v in range(5, 30) if v not in items])
        code = f"{name} = {items}\n{name}.remove({x})\nprint({name})"
        d = [str(items), error_choice("IndexError"), error_choice("KeyError"), "None"]
        why = f"`remove` deletes a value, and raises ValueError if that value ({x}) isn't in the list."
    else:
        x = rng.choice(items)
        rest = [v for v in items if v != x]
        code = f"{name} = {items}\n{name}.remove({x})\nprint({name})"
        d = [error_choice("IndexError"), str(items), error_choice("ValueError"), "None"]
        why = (
            f"`remove({x})` deletes the value {x} (not the item at index {x}), leaving {rest}. "
            "It would only raise ValueError if the value were missing."
        )
    return code, d, why


_GOTCHAS = [
    _gotcha_list_index,
    _gotcha_find_vs_index,
    _gotcha_int_float,
    _gotcha_slice,
    _gotcha_empty,
    _gotcha_len_int,
    _gotcha_immutable,
    _gotcha_get_none,
    _gotcha_remove,
]


@generator(TOPIC, MEDIUM)
def gen_error_or_value(rng: random.Random) -> Question:
    """Commonly-confused operations: which raise, which quietly return something?"""
    code, distractors, why = rng.choice(_GOTCHAS)(rng)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_partial_try_value(rng: random.Random) -> Question:
    """Changes made before the error are kept; the rest of try is skipped; else is conditional."""
    var = rng.choice(["x", "total", "score", "points"])
    a = rng.randint(1, 9)
    b = rng.randint(2, 9)
    c = rng.choice([10, 20, 50, 100])
    fail = rng.random() < 0.7
    if rng.random() < 0.5:
        exc = "ValueError"
        t = rng.randint(2, 9)
        text = rng.choice(["six", "abc", "4.5", "two"]) if fail else str(t)
        risky = f'{var} += int("{text}")'

        def apply(v):
            return v + t

    else:
        exc = "ZeroDivisionError"
        d = 0 if fail else rng.choice([2, 3])
        risky = f"{var} //= {d}"

        def apply(v):
            return v // d

    h_src, h_fn = rng.choice(
        [("*= 2", lambda v: v * 2), ("-= 1", lambda v: v - 1), ("+= 1000", lambda v: v + 1000)]
    )
    e_src, e_fn = rng.choice(
        [
            (src, fn)
            for src, fn in [("+= 1", lambda v: v + 1), ("*= 10", lambda v: v * 10)]
            if src[:2] != h_src[:2]
        ]
    )
    use_else = rng.random() < 0.6
    code = _code(
        f"{var} = {a}",
        "try:",
        f"    {var} += {b}",
        f"    {risky}",
        f"    {var} += {c}",
        f"except {exc}:",
        f"    {var} {h_src}",
        "else:" if use_else else None,
        f"    {var} {e_src}" if use_else else None,
        f"print({var})",
    )
    e = e_fn if use_else else (lambda v: v)
    if fail:
        correct = h_fn(a + b)
        cands = [
            h_fn(a),  # thinks the whole try block is undone
            h_fn(a + b + c),  # thinks the rest of try still runs
            e_fn(h_fn(a + b)) if use_else else a + b,  # else runs too
            a + b,  # forgets the handler
            h_fn(b),
        ]
        why = (
            f"`{var} += {b}` runs first ({var} becomes {a + b}); then `{risky}` raises {exc}, so "
            f"`{var} += {c}` is skipped. Python does not undo earlier changes, so the handler's "
            f"`{var} {h_src}` starts from {a + b}, giving {correct}."
            + (" `else` is skipped because there was an error." if use_else else "")
        )
    else:
        mid = apply(a + b) + c
        correct = e(mid)
        cands = [
            mid if use_else else a + b + c,  # forgets the else step / the risky line
            h_fn(e(mid)),  # thinks except always runs
            e(apply(a + b)),  # forgets the line after the risky one
            e(apply(a) + c),
            e(h_fn(mid)),
        ]
        why = (
            f"Nothing fails: {var} goes {a} → {a + b} → {apply(a + b)} → {mid}. The `except` block is skipped"
            + (
                f", and `else` runs because there was no error, giving {correct}."
                if use_else
                else f", so {mid} is printed."
            )
        )
    if run_code(code).output != str(correct):
        raise GenerationError("model mismatch")
    distractors = [str(v) for v in cands] + int_distractors(correct, rng)
    return _output(code, MEDIUM, distractors, why, rng)


# exception -> wrong-but-plausible except clause
_MISMATCH = {
    "ValueError": "TypeError",
    "IndexError": "KeyError",
    "KeyError": "IndexError",
    "TypeError": "ValueError",
    "ZeroDivisionError": "ValueError",
}


@generator(TOPIC, MEDIUM)
def gen_uncaught_mismatch(rng: random.Random) -> Question:
    """An except clause only catches its own type; anything else still crashes."""
    exc = rng.choice(list(_MISMATCH))
    case = rng.choices(["mismatch", "match", "ok"], weights=[6, 3, 2])[0]
    r = _risky(rng, exc, case != "ok")
    clause = _MISMATCH[exc] if case == "mismatch" else exc
    fallback = rng.choice(_FALLBACK[clause])
    after = rng.choice(["finished", "the end", "done"])
    code = _code(
        r.setup,
        "try:",
        f"    value = {r.expr}",
        "    print(value)",
        f"except {clause}:",
        f'    print("{fallback}")',
        f'print("{after}")',
    )
    if case == "mismatch":
        distractors = [
            _lines(fallback, after),
            after,
            error_choice(clause),
            _lines(r.near[0], after),
        ]
        why = (
            f"{_cap(r.why)}. The only handler is `except {clause}`, which does not "
            f"match {exc}, so the error is not caught and the program stops."
        )
    elif case == "match":
        distractors = [error_choice(exc), fallback, after, _lines(r.near[0], after)]
        why = (
            f"{_cap(r.why)}. `except {exc}` matches, so `{fallback}` is printed and "
            f"the program continues with `{after}`."
        )
    else:
        value = run_code(code).output.split("\n")[0]
        distractors = [
            _lines(value, fallback, after),
            _lines(fallback, after),
            error_choice(exc),
            _lines(r.near[0], after),
        ]
        why = f"{_cap(r.why)}, so nothing is raised: {value} is printed, the handler is skipped, then `{after}`."
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_function_propagation(rng: random.Random) -> Question:
    """An error inside a function escapes to the caller's try, skipping the rest."""
    good = [str(v) for v in rng.sample(range(2, 30), 2)]
    bad = rng.choice(["ten", "abc", "4.5", "two", "n/a"])
    case = rng.choice(["first_bad", "second_bad", "second_bad", "ok"])
    x, y = good
    if case == "first_bad":
        x = bad
    elif case == "second_bad":
        y = bad
    fn = rng.choice(["parse", "convert", "to_number"])
    msg = rng.choice(["bad input", "invalid", "error"])
    shape = rng.choice(["print_first", "print_after"])
    if shape == "print_first":
        verb = rng.choice(["parsing", "reading"])
        func = f'def {fn}(text):\n    print("{verb}", text)\n    return int(text)'
    else:
        verb = "got"
        func = f'def {fn}(text):\n    number = int(text)\n    print("{verb}", number)\n    return number'
    main = (
        f'try:\n    total = {fn}("{x}") + {fn}("{y}")\n    print(total)\n'
        f'except ValueError:\n    print("{msg}")'
    )
    code = _prog(func, main)

    def call_lines(texts):
        if shape == "print_first":
            return [f"{verb} {t}" for t in texts]
        return [f"{verb} {t}" for t in texts if t.isdigit()]

    if case == "ok":
        total = int(x) + int(y)
        distractors = [
            _lines(*call_lines([x, y]), x + y),  # string joining
            _lines(*call_lines([x, y]), msg),
            str(total),
            _lines(*call_lines([x, y]), total, msg),
        ]
        why = (
            f"Both calls succeed and return ints, so `total` is {x} + {y} = {total}. "
            "No exception, so the `except` block never runs."
        )
    elif case == "first_bad":
        distractors = [
            _lines(*call_lines([x, y]), msg),  # thinks the second call still happens
            error_choice("ValueError"),  # thinks the caller's try can't catch it
            _lines(f"{verb} {x}", f"{verb} {y}", msg),
            msg,
            _lines(f"{verb} {x}", msg),
        ]
        why = (
            f'`{fn}("{x}")` raises ValueError inside the function. It isn\'t caught there, so it '
            f'jumps out to the caller\'s `try` immediately: `{fn}("{y}")` is never called and '
            f"`print(total)` is skipped."
        )
    else:
        distractors = [
            _lines(f"{verb} {x}", f"{verb} {y}", msg),
            error_choice("ValueError"),  # thinks the caller's try can't catch it
            _lines(f"{verb} {x}", msg),
            msg,
            _lines(*call_lines([x, y]), x),
        ]
        why = (
            f'`{fn}("{x}")` works, then `{fn}("{y}")` raises ValueError inside the function. The '
            "error travels up to the caller's `try`, so `print(total)` is skipped and the handler runs."
        )
    if shape == "print_after" and case != "ok":
        why += " The function's own `print` after `int(text)` is skipped for the bad input too."
    return _output(code, MEDIUM, distractors, why, rng)


def _num_text(s: str) -> int | None:
    try:
        return int(s)
    except ValueError:
        return None


@generator(TOPIC, MEDIUM)
def gen_loop_try_count(rng: random.Random) -> Question:
    """try/except inside a loop: a failure skips one item, not the whole loop."""
    if rng.random() < 0.55:
        n_valid = rng.choice([3, 3, 4])
        valid = [str(rng.randint(1, 20)) for _ in range(n_valid)]
        if rng.random() < 0.4:
            valid[0] = f"-{rng.randint(2, 9)}"
        invalid = rng.sample(["x", "ten", "five", "2.5", "1.5", "n/a"], rng.choice([1, 2]))
        items = valid + invalid
        rng.shuffle(items)
        if _num_text(items[0]) is None:  # make the first-error-stops-loop misconception visible
            j = next(k for k, s in enumerate(items) if _num_text(s) is not None)
            items[0], items[j] = items[j], items[0]
        h_src, h = rng.choice([("pass", 0), ("total -= 1", -1), ("total += 100", 100)])
        code = _code(
            f"items = {_list_src(items)}",
            "total = 0",
            "for item in items:",
            "    try:",
            "        total += int(item)",
            "    except ValueError:",
            f"        {h_src}",
            "print(total)",
        )

        def model(stop=False, trunc=False, neg_bad=False, handler=True):
            t = 0
            for s in items:
                v = _num_text(s)
                if v is not None and neg_bad and v < 0:
                    v = None
                if v is None and trunc and s.replace(".", "", 1).isdigit():
                    v = int(float(s))
                if v is None:
                    t += h if handler else 0
                    if stop:
                        break
                else:
                    t += v
            return t

        correct = model()
        cands = [model(stop=True), model(trunc=True), model(neg_bad=True), model(handler=False)]
        bad_list = " and ".join(f'`"{s}"`' for s in items if _num_text(s) is None)
        decimals = [s for s in items if "." in s]
        negatives = [s for s in items if s.startswith("-")]
        why = (
            f"`int()` raises ValueError for {bad_list}"
            + (" (a decimal string isn't a valid whole number)" if decimals else "")
            + f". When that happens, the handler runs (`{h_src}`) and the loop moves on to the next item; "
            "it doesn't stop. "
            + (
                f'A minus sign is fine: `int("{negatives[0]}")` is {negatives[0]}. '
                if negatives
                else ""
            )
            + f"The total is {correct}."
        )
        distractors = [str(v) for v in cands] + int_distractors(correct, rng)
        return _output(code, MEDIUM, distractors, why, rng)

    dname, keys = rng.choice(_MENUS[:2])
    present = rng.sample(keys, 3)
    prices = {k: rng.randint(2, 9) for k in present}
    missing = [k for k in keys if k not in present]
    found = rng.sample(present, 2)
    rest = [found[1], *rng.sample(missing, rng.choice([1, 1, 2]))]
    rng.shuffle(rest)
    order = [found[0], *rest]
    if order[-1] not in prices:  # keep a found item after the first miss
        order[-1], order[1] = order[1], order[-1]
    code = _code(
        f"{dname} = {_dict_src(prices.items())}",
        f"order = {_list_src(order)}",
        "total = 0",
        "for item in order:",
        "    try:",
        f"        total += {dname}[item]",
        "    except KeyError:",
        '        print("no", item)',
        "print(total)",
    )
    total = sum(prices.get(k, 0) for k in order)
    first_bad = next(i for i, k in enumerate(order) if k not in prices)
    before = sum(prices[k] for k in order[:first_bad])
    misses = [f"no {k}" for k in order if k not in prices]
    distractors = [
        _lines(misses[0], before),  # thinks the loop ends at the first error
        str(total),  # forgets the handler's prints
        _lines(*misses, before),
        _lines(*misses, total + len(misses)),
        _lines(misses[0], total),
        error_choice("KeyError"),
        _lines(total, *misses),
    ]
    why = (
        f"Each missing key raises KeyError, which is caught inside the loop: Python prints the "
        f"message and continues with the next item. Only the found items are added, so total is {total}."
    )
    return _output(code, MEDIUM, distractors, why, rng)


# target exception -> list of (setup, [expressions that raise it], [expressions that don't])
def _which_raises_case(rng: random.Random):
    exc = rng.choice(["ZeroDivisionError", "TypeError", "ValueError", "IndexError", "KeyError"])
    if exc == "ZeroDivisionError":
        a, b = rng.sample(["a", "x", "n", "total"], 2)
        n = rng.randint(3, 20)
        setup = f"{a} = {n}\n{b} = 0"
        right = [f"{a} / {b}", f"{a} // {b}", f"{a} % {b}"]
        wrong = [
            f"{b} / {a}",
            f"{b} // {a}",
            f"{b} % {a}",
            f"{a} * {b}",
            f"{a} ** {b}",
            f"{a} - {b}",
        ]
        why = f"Only dividing BY zero fails. `{b}` is 0, so `{b} / {a}` is just 0.0, but dividing {n} by `{b}` raises ZeroDivisionError."
    elif exc == "TypeError":
        n = rng.randint(2, 9)
        word = rng.choice(_short_words(5))
        setup = f'count = {n}\nlabel = "{word}"'
        right = ["label + count", "count + label", "len(count)"]
        wrong = [
            "label * count",
            "label + str(count)",
            "str(count) + label",
            "count * 2",
            "len(label)",
            "count + len(label)",
        ]
        why = "Mixing a str and an int with `+` (or asking for the `len` of an int) raises TypeError. `*` between a str and an int is allowed: it repeats the string."
    elif exc == "ValueError":
        whole = rng.randint(2, 9)
        frac = rng.choice([2, 5, 7])
        setup = f'text = "{whole}.{frac}"'
        right = ["int(text)"]
        wrong = [
            "float(text)",
            "int(float(text))",
            "round(float(text))",
            'text.split(".")',
            "len(text)",
            "str(text)",
        ]
        why = f'`int()` only accepts whole-number strings, so `int("{whole}.{frac}")` raises ValueError. Converting with `float()` first works.'
    elif exc == "IndexError":
        word = rng.choice([w for w in WORDS if 4 <= len(w) <= 6])
        n = len(word)
        setup = f'word = "{word}"'
        right = [f"word[{n}]"]
        wrong = [f"word[-{n}]", f"word[{n - 1}]", f"word[1:{n + 5}]", f"word[{n}:]", "word[-1]"]
        why = (
            f'`"{word}"` has {n} characters, so the valid indexes are 0 to {n - 1} (or -1 to -{n}). '
            f'`word[{n}]` is out of range. Slices like `word[{n}:]` never raise; they just give `""`.'
        )
    else:
        dname, keys = rng.choice(_MENUS)
        k1, k2, missing = rng.sample(keys, 3)
        v1, v2 = rng.sample(range(2, 15), 2)
        setup = f"{dname} = {_dict_src([(k1, v1), (k2, v2)])}"
        right = [f'{dname}["{missing}"]']
        wrong = [
            f'{dname}.get("{missing}")',
            f'"{missing}" in {dname}',
            f'{dname}.get("{missing}", 0)',
            f'{dname}["{k1}"]',
            f"len({dname})",
        ]
        why = f'Square brackets raise KeyError for a missing key like `"{missing}"`; `get` returns None (or the default) and `in` returns False instead.'
    correct = rng.choice(right)
    rng.shuffle(wrong)
    return exc, setup, correct, wrong, why


@generator(TOPIC, MEDIUM)
def gen_which_raises(rng: random.Random) -> Question:
    """Pick the one expression that raises a given exception."""
    exc, setup, correct, wrong, why = _which_raises_case(rng)
    if _expr_raises(correct, setup) != exc:
        raise GenerationError(f"{correct} does not raise {exc}")
    safe = [e for e in wrong if _expr_raises(e, setup) is None]
    return _choice(
        difficulty=MEDIUM,
        prompt=f"After this code runs, which expression raises a {exc}?",
        code=setup,
        correct=correct,
        distractors=safe,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# HARD
# ==========================================================================


@generator(TOPIC, HARD)
def gen_finally_with_return(rng: random.Random) -> Question:
    """finally runs even when the function returns (and before the caller prints)."""
    shape = rng.choice(["print", "override", "late_change", "except_return", "caller_catches"])
    fn = rng.choice(["compute", "process", "calc", "run"])
    if shape == "print":
        k = rng.randint(2, 5)
        v = rng.randint(3, 12)
        msg = rng.choice(["cleanup", "closing", "finally"])
        code = _prog(
            f'def {fn}(n):\n    try:\n        return n * {k}\n    finally:\n        print("{msg}")',
            f"print({fn}({v}))",
        )
        distractors = [_lines(v * k, msg), str(v * k), _lines(msg, "None"), msg]
        why = (
            f"`return n * {k}` computes {v * k}, but before the function actually hands it back, the "
            f"`finally` block runs and prints `{msg}`. Only then does the caller's `print` show {v * k}."
        )
    elif shape == "override":
        k = rng.randint(2, 5)
        v = rng.randint(3, 12)
        j = rng.choice([x for x in range(1, 10) if v + x != v * k])
        code = _prog(
            f"def {fn}(n):\n    try:\n        return n * {k}\n    finally:\n        return n + {j}",
            f"print({fn}({v}))",
        )
        distractors = [str(v * k), _lines(v * k, v + j), _lines(v + j, v * k), str(v * k + j)]
        why = (
            f"The `try` block starts to return {v * k}, but `finally` always runs on the way out, and "
            f"its own `return` replaces that value, so the function returns {v} + {j} = {v + j}."
        )
    elif shape == "late_change":
        a = rng.randint(1, 9)
        b = rng.randint(2, 9)
        c = rng.choice([10, 20, 100])
        var = rng.choice(["count", "total", "result"])
        code = _prog(
            f"def {fn}():\n    {var} = {a}\n    try:\n        {var} += {b}\n        return {var}\n"
            f"    finally:\n        {var} += {c}",
            f"print({fn}())",
        )
        distractors = [str(a + b + c), str(a), str(a + c), "None"]
        why = (
            f"`return {var}` evaluates the value {a + b} immediately. `finally` then changes the local "
            f"variable to {a + b + c}, but that doesn't change the value already being returned."
        )
    elif shape == "except_return":
        a = rng.randint(10, 40)
        b = rng.choice([0, 0, rng.randint(2, 5)])
        fb = rng.choice([-1, 0])
        fname = rng.choice(["safe_div", "share"])
        code = _prog(
            f"def {fname}(a, b):\n    try:\n        return a // b\n    except ZeroDivisionError:\n"
            f'        return {fb}\n    finally:\n        print("checked", b)',
            f"print({fname}({a}, {b}))",
        )
        result = fb if b == 0 else a // b
        distractors = [
            _lines(result, f"checked {b}"),  # finally runs after the caller prints
            str(result),  # forgets finally
            _lines(f"checked {b}", "None"),
            error_choice("ZeroDivisionError") if b == 0 else _lines(f"checked {b}", fb),
            _lines(f"checked {b}", a) if b == 0 else _lines(f"checked {b}", a / b),
        ]
        if b == 0:
            why = (
                f"`{a} // 0` raises ZeroDivisionError, so the `except` block returns {fb}. On the way "
                "out, `finally` still runs and prints first; then the caller prints the returned value."
            )
        else:
            why = (
                f"`{a} // {b}` works, so `try` returns {a // b}. `finally` runs before the function "
                "actually returns, so its print comes first."
            )
    else:
        a = rng.randint(10, 40)
        b = rng.choice([0, 0, rng.randint(2, 5)])
        msg = rng.choice(["cleanup", "closing"])
        code = _prog(
            f'def {fn}(a, b):\n    try:\n        return a // b\n    finally:\n        print("{msg}")',
            f'try:\n    print({fn}({a}, {b}))\nexcept ZeroDivisionError:\n    print("caught")',
        )
        if b == 0:
            distractors = [
                "caught",
                _lines("caught", msg),
                error_choice("ZeroDivisionError"),
                _lines(msg, "None"),
            ]
            why = (
                f"`{a} // 0` raises inside the function. There's no `except` there, but `finally` "
                f"still runs (printing `{msg}`) before the error escapes to the caller's `try`, "
                "which prints `caught`."
            )
        else:
            distractors = [
                _lines(a // b, msg),
                str(a // b),
                _lines(msg, a // b, "caught"),
                _lines(msg, "caught"),
            ]
            why = (
                f"`{a} // {b}` is {a // b}. `finally` runs as the function returns, so `{msg}` "
                "is printed before the caller prints the result."
            )
    return _output(code, HARD, distractors, why, rng)


def _nested_risky(rng: random.Random, exc: str):
    """(setup line or None, statement raising ``exc``, a sibling class that won't match)."""
    if exc == "ValueError":
        word = rng.choice(["ten", "abc", "seven", "4.5"])
        return None, f'value = int("{word}")', rng.choice(["TypeError", "KeyError"])
    if exc == "IndexError":
        items = rng.sample(range(2, 20), 3)
        return f"nums = {items}", f"value = nums[{rng.choice([3, 4, 5])}]", "KeyError"
    dname, keys = rng.choice(_MENUS)
    k1, k2, missing = rng.sample(keys, 3)
    v1, v2 = rng.sample(range(2, 15), 2)
    return (
        f"{dname} = {_dict_src([(k1, v1), (k2, v2)])}",
        f'value = {dname}["{missing}"]',
        "IndexError",
    )


@generator(TOPIC, HARD)
def gen_nested_try(rng: random.Random) -> Question:
    """Trace an inner try (except + finally) inside an outer try."""
    exc = rng.choice(["ValueError", "IndexError", "KeyError"])
    setup, stmt, sibling = _nested_risky(rng, exc)
    parents = _PARENTS[exc]
    case = rng.choices(["inner", "outer", "uncaught"], weights=[4, 5, 1])[0]
    if case == "inner":
        inner = rng.choice([exc, exc, parents[0]])
        outer = rng.choice([exc, "Exception", sibling])
    elif case == "outer":
        inner = sibling
        outer = rng.choice([exc, *parents])
    else:
        inner, outer = sibling, rng.choice(["TypeError", "AttributeError"])
        if outer == inner:
            outer = "AttributeError"
    a, b, c, d, e, f, g = _labels(rng, 7)
    has_b = rng.random() < 0.6
    code = _code(
        setup,
        "try:",
        "    try:",
        f'        print("{a}")',
        f"        {stmt}",
        f'        print("{b}")' if has_b else None,
        f"    except {inner}:",
        f'        print("{c}")',
        "    finally:",
        f'        print("{d}")',
        f'    print("{e}")',
        f"except {outer}:",
        f'    print("{f}")',
        f'print("{g}")',
    )
    bb = [b] if has_b else []
    if case == "inner":
        distractors = [
            _lines(a, c, d, g),  # thinks E is skipped
            _lines(a, *bb, c, d, e, g),
            _lines(a, c, e, g),  # forgets finally
            _lines(a, c, d, e, f, g),
            _lines(a, d, f, g),
        ]
        why = (
            f"`{stmt}` raises {exc}, which the inner `except {inner}` catches, so `{c}` prints. "
            f"The inner `finally` prints `{d}`, and since the error was handled, the outer `try` "
            f"continues normally with `{e}`; the outer `except` never runs."
        )
    elif case == "outer":
        distractors = [
            _lines(a, d, e, f, g),  # thinks the outer try carries on
            _lines(a, f, d, g),  # outer handler before inner finally
            _lines(a, f, g),  # forgets finally
            _lines(a, c, d, e, g),  # thinks the inner except catches it
            _lines(a, d, g),
        ]
        why = (
            f"`{stmt}` raises {exc}. The inner `except {inner}` doesn't match, but the inner "
            f"`finally` still runs (`{d}`) before the error moves outward. That skips `{e}`, and the "
            f"outer `except {outer}` catches it."
        )
    else:
        distractors = [
            _lines(a, d, f, g),
            _lines(a, c, d, e, g),
            _lines(a, d, e, g),
            _lines(a, f, g),
        ]
        why = (
            f"`{stmt}` raises {exc}. Neither `except {inner}` nor `except {outer}` matches it, so after "
            "the inner `finally` runs the error escapes and the program stops."
        )
    if case != "uncaught" and rng.random() < 0.5:
        # Sometimes offer "it crashes" too, so an error choice never gives the answer away.
        distractors.insert(rng.randrange(3), error_choice(exc))
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_error_in_handler(rng: random.Random) -> Question:
    """An exception raised inside an except block is not caught by its sibling clauses."""
    a, b, c, d = _labels(rng, 4)
    first = rng.choice(["ten", "abc", "seven", "n/a"])
    if rng.random() < 0.5:
        backup_bad = rng.random() < 0.8
        backup = rng.choice(["two", "?", "4.5", "none"]) if backup_bad else str(rng.randint(10, 99))
        code = _code(
            "try:",
            "    try:",
            f'        number = int("{first}")',
            "    except ValueError:",
            f'        print("{a}")',
            f'        number = int("{backup}")',
            "    finally:",
            f'        print("{b}")',
            "    print(number)",
            f"except {rng.choice(['ValueError', 'ValueError', 'Exception'])}:",
            f'    print("{c}")',
            f'print("{d}")',
        )
        if backup_bad:
            distractors = [
                error_choice("ValueError"),  # thinks an error inside except can't be caught
                _lines(a, c, b, d),  # outer handler before the inner finally
                _lines(a, c, d),  # forgets finally
                _lines(a, b, d),
                _lines(a, b, c),
            ]
            why = (
                f'`int("{first}")` fails, so the handler prints `{a}` and tries `int("{backup}")`, which '
                "raises a NEW ValueError inside the handler. The inner `finally` runs first, then the "
                f"new error leaves the inner `try`, skips `print(number)`, and the outer handler prints `{c}`."
            )
        else:
            distractors = [
                _lines(a, backup, b, d),
                _lines(a, b, c, d),
                _lines(b, backup, d),
                _lines(a, b, d),
            ]
            why = (
                f'`int("{first}")` fails, so the handler prints `{a}` and sets `number` to {backup}. '
                f"`finally` prints `{b}`, then `print(number)` runs; the outer handler isn't needed."
            )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)

    backups = rng.sample(range(2, 30), 3)
    i = rng.choice([3, 4])
    outer = rng.choice(["LookupError", "IndexError", "Exception", "KeyError"])
    code = _code(
        f"backups = {backups}",
        "try:",
        "    try:",
        f'        number = int("{first}")',
        "    except ValueError:",
        f'        print("{a}")',
        f"        number = backups[{i}]",
        "    except IndexError:",
        f'        print("{b}")',
        "    finally:",
        f'        print("{c}")',
        f"except {outer}:",
        f'    print("{d}")',
    )
    distractors = [
        _lines(a, b, c),  # thinks the sibling clause catches it
        _lines(a, b, c, d),
        _lines(a, d, c),
        error_choice("IndexError"),
        _lines(a, c, d),
        _lines(a, c),
    ]
    why = (
        f"`backups[{i}]` raises IndexError while the `except ValueError` handler is running. "
        "The other clauses of the same `try` only guard the `try` block itself, so "
        f"`except IndexError` does NOT catch it. `finally` prints `{c}`, then "
        + (
            f"the outer `except {outer}` catches the error."
            if outer != "KeyError"
            else "the error reaches the outer `except KeyError`, which doesn't match, so the program stops."
        )
    )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_CUSTOM_PAIRS = [
    ("AppError", "LoginError"),
    ("GameError", "OutOfLivesError"),
    ("BankError", "OverdraftError"),
    ("ShopError", "OutOfStockError"),
    ("ShapeError", "NegativeSizeError"),
]


@generator(TOPIC, HARD)
def gen_custom_exception(rng: random.Random) -> Question:
    """Custom exception classes: a parent clause catches child errors, not vice versa."""
    base, child = rng.choice(_CUSTOM_PAIRS)
    raised, clauses = rng.choice(
        [
            (base, [child, base]),
            (child, [base, child]),
            (base, [child, "ValueError"]),
            (child, ["ValueError", base]),
            (child, [child, base]),
            (base, [child, "Exception"]),
        ]
    )

    def label(cls: str) -> str:
        if cls == "Exception":
            return "other problem"
        words = re.findall(r"[A-Z][a-z]*", cls[: -len("Error")])
        return " ".join(words).lower() + " problem"

    code = _prog(
        f"class {base}(Exception):\n    pass",
        f"class {child}({base}):\n    pass",
        (
            f"try:\n    raise {raised}\n"
            f'except {clauses[0]}:\n    print("{label(clauses[0])}")\n'
            f'except {clauses[1]}:\n    print("{label(clauses[1])}")'
        ),
    )
    labels = [label(c) for c in clauses]
    distractors = [
        labels[1],
        labels[0],
        error_choice(raised),
        _lines(*labels),
        label(child),
        label(base),
    ]
    is_a = {base: {base, "Exception"}, child: {child, base, "Exception"}}[raised]
    matches = [c for c in clauses if c in is_a]
    rule = (
        f"`{child}` inherits from `{base}`, so every {child} is also {_a(base)}, "
        f"but a plain {base} is not {_a(child)}."
    )
    if not matches:
        why = f"{rule} `raise {raised}` matches neither clause, so the error goes uncaught."
    else:
        hit = matches[0]
        why = f"{rule} `raise {raised}` is caught by the first clause that matches: `except {hit}`."
        if len(matches) > 1:
            why += " Later matching clauses are never reached."
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_finally_in_loop(rng: random.Random) -> Question:
    """finally still runs when break or continue leaves the try block."""
    n = rng.randint(4, 7)
    k = rng.randint(1, n - 2)
    jump = rng.choice(["break", "continue"])
    done, clean = rng.choice([("done", "cleanups"), ("worked", "closed"), ("steps", "tidied")])
    code = _code(
        f"{done} = 0",
        f"{clean} = 0",
        f"for i in range({n}):",
        "    try:",
        f"        if i == {k}:",
        f"            {jump}",
        f"        {done} += 1",
        "    finally:",
        f"        {clean} += 1",
        f"print({done}, {clean})",
    )
    if jump == "break":
        right = (k, k + 1)
        cands = [(k, k), (k + 1, k + 1), (k, n), (k + 1, k + 2), (n - 1, n)]
        counted = "only i = 0" if k == 1 else f"i = 0 to {k - 1}"
        why = (
            f"`{done} += 1` runs for {counted}, so `{done}` is {k}. When i == {k}, `break` leaves the `try` "
            f"block, but `finally` still runs once more on the way out, making `{clean}` {k + 1}."
        )
    else:
        right = (n - 1, n)
        cands = [(n - 1, n - 1), (k, k + 1), (n, n), (k, k), (n - 2, n - 1)]
        why = (
            f"`continue` skips `{done} += 1` only for i == {k}, so `{done}` is {n - 1}. `finally` "
            f"runs even when `continue` jumps out of the `try`, so `{clean}` counts all {n} iterations."
        )
    if run_code(code).output != f"{right[0]} {right[1]}":
        raise GenerationError("model mismatch")
    distractors = [f"{x} {y}" for x, y in cands]
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_reraise(rng: random.Random) -> Question:
    """A bare `raise` in a handler re-raises the same exception to the caller."""
    p, q, missing = rng.sample(NAMES, 3)
    vp, vq = rng.sample(range(2, 15), 2)
    left, right = rng.choice(
        [(p, missing), (missing, p), (q, missing), (missing, q), (p, missing), (p, q)]
    )
    outer = rng.choices(
        ["LookupError", "KeyError", "Exception", "IndexError"], weights=[4, 2, 2, 2]
    )[0]
    fn = rng.choice(["load", "lookup", "get_score"])
    code = _prog(
        f"def {fn}(scores, name):\n    try:\n        return scores[name]\n    except KeyError:\n"
        '        print("missing", name)\n        raise',
        (
            f"scores = {_dict_src([(p, vp), (q, vq)])}\ntry:\n"
            f'    total = {fn}(scores, "{left}") + {fn}(scores, "{right}")\n    print(total)\n'
            f'except {outer}:\n    print("lookup failed")'
        ),
    )
    vals = {p: vp, q: vq}
    if missing not in (left, right):
        total = vals[left] + vals[right]
        distractors = [
            str(vals[left]),
            "lookup failed",
            _lines(total, "lookup failed"),
            error_choice("KeyError"),
        ]
        why = f"Both names are in `scores`, so neither call raises: {vals[left]} + {vals[right]} = {total}."
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    distractors = [
        error_choice("TypeError"),  # thinks the handler swallows it and returns None
        error_choice("KeyError"),  # thinks a re-raised error can't be caught again
        "lookup failed",  # forgets the function's own print
        _lines(f"missing {missing}", "lookup failed"),
        f"missing {missing}",
        _lines(f"missing {missing}", "lookup failed", "lookup failed"),
    ]
    caught = outer in ("LookupError", "KeyError", "Exception")
    why = (
        f'`{fn}(scores, "{missing}")` raises KeyError; the function\'s handler prints '
        f"`missing {missing}` and then the bare `raise` re-raises the same KeyError to the caller. "
    )
    if left == missing:
        why += "Since the left call fails, the right call never happens. "
    if caught:
        why += f"`except {outer}` matches KeyError, so `lookup failed` is printed."
    else:
        why += f"`except {outer}` does not match KeyError, so the program stops with that error."
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_error_in_else(rng: random.Random) -> Question:
    """Errors in else are NOT protected by the try's except clauses."""
    colors = rng.sample(["red", "green", "blue", "pink", "gold", "gray"], 3)
    case = rng.choices(
        ["else_index", "try_index", "negative", "bad_text", "ok"], weights=[8, 4, 3, 2, 3]
    )[0]
    if case in ("else_index", "try_index"):
        text = str(rng.choice([3, 4]))
    elif case == "negative":
        text = str(rng.choice([-1, -2, -3]))
    elif case == "bad_text":
        text = rng.choice(["one", "two", "1.0", "first"])
    else:
        text = str(rng.randrange(3))
    in_try = case == "try_index" or (case != "else_index" and rng.random() < 0.3)
    msg = rng.choice(["bad choice", "invalid", "try again"])
    body = (
        ["    index = int(text)", "    print(items[index])"]
        if in_try
        else ["    index = int(text)"]
    )
    handler = ["except (ValueError, IndexError):", f'    print("{msg}")']
    code = _code(
        f"items = {_list_src(colors)}",
        f'text = "{text}"',
        "try:",
        *body,
        *handler,
        "else:" if not in_try else None,
        "    print(items[index])" if not in_try else None,
        "finally:",
        '    print("done")',
    )
    res = run_code(code)
    idx = int(text) if case != "bad_text" else None
    if res.error:
        distractors = [
            _lines(msg, "done"),
            msg,
            _lines(colors[-1], "done"),
            error_choice("ValueError"),
        ]
        why = (
            f'`int("{text}")` works, so `else` runs, and `items[{text}]` raises IndexError there. '
            "Code in `else` is NOT protected by the `except` clauses of the same `try`, so the "
            "error isn't caught: `finally` prints `done` and then the program stops with IndexError."
        )
    elif case == "bad_text":
        distractors = [msg, _lines(msg, colors[0], "done"), error_choice("ValueError"), "done"]
        why = f'`int("{text}")` raises ValueError, which the `except` clause catches; `finally` always prints `done`.'
    elif idx is not None and 0 <= idx < 3 or idx is not None and -3 <= idx < 0:
        if idx >= len(colors) or idx < -len(colors):
            raise GenerationError("unexpected index")
        distractors = [
            _lines(msg, "done"),
            error_choice("IndexError"),
            _lines(colors[idx], msg, "done"),
            colors[idx],
            _lines(colors[(idx + 1) % 3], "done"),
            error_choice("ValueError"),
        ]
        if idx < 0:
            why = (
                f'`int("{text}")` happily converts the negative string, and a negative index counts '
                f"from the end, so `items[{idx}]` is `{colors[idx]}`. No error; `finally` prints `done`."
            )
        else:
            why = f'`int("{text}")` is {idx} and `items[{idx}]` is `{colors[idx]}`; no error, then `finally` prints `done`.'
    else:
        distractors = [
            error_choice("IndexError"),
            _lines(msg),
            _lines(colors[-1], "done"),
            _lines(msg, colors[-1], "done"),
        ]
        why = (
            f"`items[{text}]` raises IndexError, and here it is INSIDE the `try` block, so "
            "`except (ValueError, IndexError)` catches it. `finally` then prints `done`."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
