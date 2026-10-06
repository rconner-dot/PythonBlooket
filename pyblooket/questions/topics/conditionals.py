"""Question generators for the "conditionals" topic (Conditionals & Logic).

Covers if/elif/else (only the FIRST true branch runs), separate ``if``s vs an
``elif`` chain, nested ifs and which ``if`` an ``else`` belongs to, ``and`` /
``or`` / ``not`` and their precedence, short-circuit evaluation and the
*values* ``and``/``or`` return, truthiness, comparison chaining, conditional
(ternary) expressions, ``is None`` vs falsy checks and membership tests.
"""

from __future__ import annotations

import itertools
import operator
import random
import re

from ..base import (
    EASY,
    HARD,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    MEDIUM,
    NOTHING_PRINTED,
    GenerationError,
    Question,
    build_question,
    error_choice,
    generator,
    output_question,
    run_code,
    which_expression_question,
)

TOPIC = "conditionals"
PRINT_OR_ERROR = "What is printed, or which error is raised?"

_CMP = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _run(code: str) -> str:
    """The choice text for what ``code`` prints, or the error it raises."""
    res = run_code(code)
    if res.error:
        return error_choice(res.error)
    return res.output if res.output else NOTHING_PRINTED


def _fits(choice: str) -> bool:
    """Would ``choice`` pass the choice-shape limits?"""
    lines = choice.split("\n")
    return len(lines) <= MAX_CHOICE_LINES and all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines)


def _src(value: object) -> str:
    """Python source for a literal, with double-quoted strings (PEP 8 consistency in snippets)."""
    return repr(value).replace("'", '"')


def _ev(expr: str, **names: object) -> object:
    """Evaluate one of OUR generated expressions with the given names bound."""
    return eval(expr, {"__builtins__": {}}, dict(names))  # noqa: S307 - trusted, generated text


def _output(
    code: str,
    difficulty: int,
    distractors: list[str],
    explanation: str,
    rng: random.Random,
    *,
    prompt: str = "What does this code print?",
    allow_error: bool = False,
) -> Question:
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[d for d in distractors if _fits(d)],
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _bool_rows(n: int, rng: random.Random) -> list[str]:
    """Every row of n True/False words, shuffled (generic fallback distractors)."""
    rows = [" ".join(row) for row in itertools.product(("True", "False"), repeat=n)]
    rng.shuffle(rows)
    return rows


def _atom(rng: random.Random, name: str, value: int, want: bool, ops: tuple[str, ...]) -> str:
    """A comparison like ``name > 4`` that is ``want`` when ``name == value``."""
    for _ in range(200):
        op = rng.choice(ops)
        const = max(0, value + rng.randint(-5, 5))
        if _CMP[op](value, const) == want:
            return f"{name} {op} {const}"
    raise GenerationError("could not build a comparison")


# ==========================================================================
# EASY
# ==========================================================================

_IF_ELSE_WORDS = {
    ">": [("big", "small"), ("high", "low"), ("pass", "fail"), ("hot", "cold"), ("win", "lose")],
    "<": [("small", "big"), ("low", "high"), ("cold", "hot"), ("early", "late"), ("cheap", "pricey")],
    "==": [("match", "no match"), ("yes", "no"), ("bingo", "nope"), ("exact", "off")],
    "!=": [("changed", "same"), ("different", "equal"), ("moved", "stayed")],
}
_IF_ELSE_WORDS[">="] = _IF_ELSE_WORDS[">"]
_IF_ELSE_WORDS["<="] = _IF_ELSE_WORDS["<"]
_IF_ELSE_NAMES = ["score", "temp", "level", "speed", "coins", "age", "height", "points"]


def _boundary_note(op: str, v: int, t: int) -> str:
    if v != t:
        return ""
    if op in (">", "<"):
        return f" (`{op}` does not include equality)"
    if op in (">=", "<="):
        return f" (`{op}` includes equality)"
    return ""


@generator(TOPIC, EASY)
def gen_if_else_branch(rng: random.Random) -> Question:
    """One if/else (or an if followed by an unindented line): which line(s) run?"""
    shape = rng.choice(["if_else", "if_else", "if_only", "update"])
    name = rng.choice(_IF_ELSE_NAMES)
    if shape in ("if_else", "if_only"):
        op = rng.choice([">", ">=", "<", "<=", ">", "<", "==", "!="])
        t = rng.randint(5, 30)
        if rng.random() < (0.5 if op in ("==", "!=") else 0.4):
            v = t
        else:
            v = t + rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        cond = _CMP[op](v, t)
        wt, wf = rng.choice(_IF_ELSE_WORDS[op])
        note = _boundary_note(op, v, t)
        if shape == "if_else":
            code = f'{name} = {v}\nif {name} {op} {t}:\n    print("{wt}")\nelse:\n    print("{wf}")'
            shown = wt if cond else wf
            distractors = [wf if cond else wt, f"{wt}\n{wf}", NOTHING_PRINTED, f"{wf}\n{wt}"]
            why = (
                f"`{v} {op} {t}` is {cond}{note}, so only the "
                f"{'`if`' if cond else '`else`'} branch runs and it prints `{shown}`. "
                "Exactly one of the two branches always runs."
            )
        else:
            done = rng.choice(["done", "end", "finished", "bye"])
            code = f'{name} = {v}\nif {name} {op} {t}:\n    print("{wt}")\nprint("{done}")'
            distractors = [done, f"{wt}\n{done}", wt, NOTHING_PRINTED, f"{done}\n{wt}"]
            why = (
                f'`print("{done}")` is not indented, so it is outside the `if` and always runs. '
                f"The indented line runs only when the condition is True, and `{v} {op} {t}` is {cond}{note}."
            )
        return _output(code, EASY, distractors, why, rng)

    var = rng.choice(["n", "x", "num", "steps"])
    v = rng.randint(3, 20)
    k = rng.randint(2, 6)
    kind = rng.choice(["parity", "gt", "lt"])
    if kind == "parity":
        cond_s = f"{var} % 2 == 0"
        then_s, else_s = rng.choice(
            [(f"{var} // 2", f"{var} * 3 + 1"), (f"{var} // 2", f"{var} + 1"), (f"{var} + {k}", f"{var} - {k}")]
        )
    else:
        t = v + rng.choice([-3, -2, -1, 0, 1, 2, 3])
        cond_s = f"{var} {'>' if kind == 'gt' else '<'} {t}"
        then_s, else_s = rng.choice(
            [(f"{var} - {k}", f"{var} + {k}"), (f"{var} * 2", f"{var} - {k}"), (f"{var} + {k}", f"{var} * {k}")]
        )
    cond = _ev(cond_s, **{var: v})
    then_v = _ev(then_s, **{var: v})
    else_v = _ev(else_s, **{var: v})
    result = then_v if cond else else_v
    both = _ev(else_s, **{var: then_v})  # "both branches ran"
    code = f"{var} = {v}\nif {cond_s}:\n    {var} = {then_s}\nelse:\n    {var} = {else_s}\nprint({var})"
    distractors = [str(else_v if cond else then_v), str(v), str(both), str(result + 1), str(result - 1)]
    why = (
        f"`{cond_s}` is {cond} when `{var}` is {v}, so only the "
        f"{'`if`' if cond else '`else`'} branch runs: `{var} = {then_s if cond else else_s}` "
        f"makes it {result}. The other branch is skipped entirely."
    )
    return _output(code, EASY, distractors, why, rng)


_LADDERS = [
    ("score", ("fail", "pass", "honors")),
    ("temp", ("cold", "warm", "hot")),
    ("speed", ("slow", "fast", "very fast")),
    ("points", ("bronze", "silver", "gold")),
    ("battery", ("low", "okay", "full")),
    ("height", ("short", "tall", "giant")),
]


@generator(TOPIC, EASY)
def gen_elif_first_match(rng: random.Random) -> Question:
    """if/elif/else where two conditions are True: only the FIRST true branch runs."""
    name, (low, mid, high) = rng.choice(_LADDERS)
    lo = rng.randint(2, 8) * 5
    hi = lo + rng.randint(2, 6) * 5
    upward = rng.random() < 0.6
    op = rng.choice([">", ">="] if upward else ["<", "<="])
    both_true = rng.random() < 0.8
    if upward:
        strict, loose = (f"{name} {op} {hi}", high), (f"{name} {op} {lo}", mid)
        if both_true:
            v = hi if op == ">=" and rng.random() < 0.3 else hi + rng.randint(1, 15)
        else:
            v = rng.randint(lo + 1, hi - 1)
        other = low
    else:
        strict, loose = (f"{name} {op} {lo}", low), (f"{name} {op} {hi}", mid)
        if both_true:
            v = lo if op == "<=" and rng.random() < 0.3 else lo - rng.randint(1, 9)
        else:
            v = rng.randint(lo + 1, hi - 1)
        other = high
    first, second = (loose, strict) if rng.random() < 0.6 else (strict, loose)
    code = (
        f"{name} = {v}\nif {first[0]}:\n    print(\"{first[1]}\")\n"
        f"elif {second[0]}:\n    print(\"{second[1]}\")\nelse:\n    print(\"{other}\")"
    )
    c1 = _ev(first[0], **{name: v})
    c2 = _ev(second[0], **{name: v})
    distractors = [second[1], f"{first[1]}\n{second[1]}", other, first[1]]
    if c1 and c2:
        why = (
            f"Both `{first[0]}` and `{second[0]}` are True for {v}, but an if/elif chain runs only "
            f"the FIRST branch whose condition is True and skips the rest, so it prints `{first[1]}`."
        )
    elif c1:
        why = f"`{first[0]}` is True for {v}, so the first branch runs and the rest of the chain is skipped."
    else:
        why = (
            f"`{first[0]}` is False for {v}, so Python moves on to the `elif`: `{second[0]}` is "
            f"{c2}, so it prints `{second[1] if c2 else other}`."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_bool_pair(rng: random.Random) -> Question:
    """and / or / not on simple comparisons — print two results."""
    name = rng.choice(["x", "n", "age", "score", "temp", "level"])
    v = rng.randint(3, 20)
    shapes = rng.sample(["and", "or", "not", rng.choice(["and", "or"])], 2)
    exprs, misreads, details = [], [], []
    ops = ("<", ">", "<=", ">=", "==", "!=")
    for shape in shapes:
        if shape == "not":
            a_val = rng.random() < 0.5
            a = _atom(rng, name, v, a_val, ops)
            exprs.append(f"not {a}")
            misreads.append(a_val)  # forgot that `not` flips it
            details.append(f"not {a_val}")
        else:
            a_val, b_val = rng.choice([(True, False), (False, True), (True, False), (False, True),
                                       (True, True), (False, False)])
            a = _atom(rng, name, v, a_val, ops)
            b = _atom(rng, name, v, b_val, ops)
            exprs.append(f"{a} {shape} {b}")
            other = "or" if shape == "and" else "and"
            misreads.append(_ev(f"{a_val} {other} {b_val}"))  # mixed up and/or
            details.append(f"{a_val} {shape} {b_val}")
    code = f"{name} = {v}\nprint({exprs[0]}, {exprs[1]})"
    values = [_ev(e, **{name: v}) for e in exprs]
    misread = f"{misreads[0]} {misreads[1]}"
    why = (
        "`and` is True only if BOTH sides are True, `or` if at least ONE side is True, and `not` flips "
        f"the value. Here `{exprs[0]}` is {details[0]} → {values[0]}, and `{exprs[1]}` is "
        f"{details[1]} → {values[1]}."
    )
    return _output(code, EASY, [misread, *_bool_rows(2, rng)], why, rng)


_FALSY = ["0", '""', "[]", "None", "0.0"]
_TRUTHY_TRICKS = {
    '"0"': "a non-empty string (it contains the character 0)",
    '" "': "a non-empty string (a space is still a character)",
    '"False"': "a non-empty string, not the value `False`",
    "[0]": "a list with one item, so it is not empty",
    "-1": "a non-zero number (negative numbers are truthy too)",
    '"None"': "a non-empty string, not the value `None`",
    "[None]": "a list with one item, so it is not empty",
}


@generator(TOPIC, EASY)
def gen_falsy_value(rng: random.Random) -> Question:
    """Which value is falsy / truthy? (0, "", [], None vs "0", " ", [0], -1 ...)"""
    want_falsy = rng.random() < 0.5
    if want_falsy:
        correct = rng.choice(sorted(_FALSY))
        wrong = rng.sample(sorted(_TRUTHY_TRICKS), 5)
        prompt = rng.choice([
            "Which of these values is falsy (counts as `False` in an `if`)?",
            "`if value:` SKIPS its block when `value` is which of these?",
        ])
        trick = wrong[0]
        why = (
            f"The falsy values are zero, empty strings/lists and `None`, so `{correct}` is the falsy one. "
            f"The others are truthy — for example `{trick}` is {_TRUTHY_TRICKS[trick]}."
        )
    else:
        correct = rng.choice(sorted(_TRUTHY_TRICKS))
        wrong = rng.sample(sorted(_FALSY), 5)
        prompt = rng.choice([
            "Which of these values is truthy (counts as `True` in an `if`)?",
            "`if value:` RUNS its block when `value` is which of these?",
        ])
        why = (
            f"`{correct}` is {_TRUTHY_TRICKS[correct]}. The others — zero, empty strings or lists "
            "and `None` — are all falsy."
        )
    # Verify by evaluation: exactly one choice has the wanted truthiness.
    if bool(_ev(correct)) == want_falsy or any(bool(_ev(w)) != want_falsy for w in wrong):
        raise GenerationError("truthiness pools are inconsistent")
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_ternary_value(rng: random.Random) -> Question:
    """`A if condition else B` — which value is picked?"""
    shape = rng.choice(["numeric", "numeric", "pick", "label"])
    if shape == "numeric":
        var = rng.choice(["points", "n", "x", "level", "price"])
        res = rng.choice(["result", "bonus", "y", "new"])
        v = rng.randint(2, 20)
        k = rng.randint(2, 9)
        t = v + rng.choice([-3, -1, 0, 1, 3])
        cond = rng.choice([f"{var} > {t}", f"{var} < {t}", f"{var} % 2 == 0", f"{var} >= {t}"])
        a_s, b_s = rng.choice([
            (f"{var} * 2", f"{var} + {k}"),
            (f"{var} - {k}", f"{var} + {k}"),
            (f"{var} * {k}", f"{var} - {k}"),
            (f"{var} // 2", f"{var} * 3"),
        ])
        c = _ev(cond, **{var: v})
        a_v, b_v = _ev(a_s, **{var: v}), _ev(b_s, **{var: v})
        result = a_v if c else b_v
        code = f"{var} = {v}\n{res} = {a_s} if {cond} else {b_s}\nprint({res})"
        distractors = [str(b_v if c else a_v), str(c), str(v), str(result + 1), str(not c)]
        why = (
            f"`A if condition else B` gives A when the condition is True, otherwise B. "
            f"`{cond}` is {c} for {v}, so `{res}` is `{a_s if c else b_s}` = {result}."
        )
    elif shape == "pick":
        a, b = rng.sample(range(1, 30), 2)
        names = rng.choice([("a", "b"), ("x", "y"), ("left", "right"), ("p1", "p2")])
        want_big = rng.random() < 0.5
        op = rng.choice([">", ">="] if want_big else ["<", "<="])
        res = "bigger" if want_big else "smaller"
        code = (
            f"{names[0]} = {a}\n{names[1]} = {b}\n"
            f"{res} = {names[0]} if {names[0]} {op} {names[1]} else {names[1]}\nprint({res})"
        )
        c = _CMP[op](a, b)
        result = a if c else b
        distractors = [str(b if c else a), str(c), str(not c), str(a + b), names[0]]
        why = (
            f"`{a} {op} {b}` is {c}, so the expression picks "
            f"{'the value before `if`' if c else 'the value after `else`'}: `{names[0] if c else names[1]}`, "
            f"which is {result}."
        )
    else:
        var, true_w, false_w, cond_fmt = rng.choice([
            ("n", "even", "odd", "{v} % 2 == 0"),
            ("age", "adult", "minor", "{v} >= 18"),
            ("score", "pass", "fail", "{v} >= 50"),
            ("temp", "hot", "cool", "{v} > 25"),
        ])
        if var == "n":
            v = rng.randint(2, 30)
        else:
            pivot = int(cond_fmt.split()[-1])
            v = pivot + rng.choice([-3, -1, 0, 0, 1, 4])
        cond = cond_fmt.format(v=var)
        res = rng.choice(["label", "kind", "status"])
        c = _ev(cond, **{var: v})
        word = true_w if c else false_w
        other = false_w if c else true_w
        code = f'{var} = {v}\n{res} = "{true_w}" if {cond} else "{false_w}"\nprint({var}, {res})'
        distractors = [f"{v} {other}", f"{v} {c}", word, f"{v} {true_w} {false_w}"]
        why = (
            f"`{cond}` is {c} for {v}, so the conditional expression gives "
            f"{'the value before `if`' if c else 'the value after `else`'}, `\"{word}\"`."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_membership_check(rng: random.Random) -> Question:
    """`in` / `not in` with strings (substring, case-sensitive) and lists (equal items)."""
    shape = rng.choice(["string", "list", "guests"])
    if shape == "guests":
        guests = rng.sample(["Ava", "Ben", "Cara", "Dev", "Eli", "Fay"], 3)
        kind = rng.choice(["present", "absent", "case"])
        if kind == "present":
            name = rng.choice(guests)
        elif kind == "absent":
            name = rng.choice(["Gus", "Hana", "Ivy", "Jon"])
        else:
            name = rng.choice(guests).lower()
        lst = rng.choice(["guests", "invited", "players"])
        code = f'{lst} = {_src(guests)}\nname = "{name}"\nif name not in {lst}:\n    {lst}.append(name)\nprint({lst})'
        added = repr(guests + [name])
        same = repr(guests)
        distractors = [same if name not in guests else added, repr(guests[:-1]),
                       repr(guests + [name.capitalize()]), repr([name] + guests)]
        if name in guests:
            why = f'`"{name}"` is already in the list, so `name not in {lst}` is False and nothing is appended.'
        elif kind == "case":
            why = (
                f'`in` compares exactly, and case matters: `"{name}"` is not equal to '
                f'`"{name.capitalize()}"`, so `name not in {lst}` is True and `"{name}"` is appended.'
            )
        else:
            why = f'`"{name}"` is not in the list, so `name not in {lst}` is True and it gets appended.'
        return _output(code, EASY, distractors, why, rng)

    probes = []
    if shape == "string":
        word = rng.choice(["banana", "python", "rocket", "pixel", "orange", "planet", "monkey", "letter"])
        holder = rng.choice(["word", "text", "s"])
        kinds = rng.sample(["sub", "sub", "missing", "case", "reversed"], 2)
        for kind in kinds:
            i = rng.randint(0, len(word) - 3)
            piece = word[i:i + rng.randint(2, 3)]
            if kind == "sub":
                probe = piece
            elif kind == "case":
                probe = piece.capitalize() if piece[0].isalpha() else piece.upper()
            elif kind == "reversed":
                probe = piece[::-1]
                if probe in word:
                    probe = piece + "z"
            else:
                probe = rng.choice(["z", "q", "x", "zz", "ab"])
                if probe in word:
                    probe = "qz"
            probes.append(probe)
        setup = f'{holder} = "{word}"'
        naive = [p.lower() in word.lower() for p in probes]
        rule = "On a string, `in` checks for a substring, and it is case-sensitive."
    else:
        items = rng.sample(["cat", "dog", "fish", "bird", "frog", "duck"], 3)
        holder = rng.choice(["pets", "animals", "zoo"])
        kinds = rng.sample(["item", "item", "part", "case", "missing"], 2)
        for kind in kinds:
            item = rng.choice(items)
            if kind == "item":
                probe = item
            elif kind == "part":
                probe = item[:2]
            elif kind == "case":
                probe = item.capitalize()
            else:
                probe = rng.choice(["cow", "pig", "ant", "bee"])
            probes.append(probe)
        setup = f"{holder} = {_src(items)}"
        naive = [any(p.lower() in it for it in items) for p in probes]
        rule = (
            "On a list, `in` checks whether some ITEM is equal to the value — part of an item "
            "doesn't count, and case matters."
        )
    negate = [rng.random() < 0.35 for _ in probes]
    parts = [f'"{p}" {"not in" if n else "in"} {holder}' for p, n in zip(probes, negate)]
    code = f"{setup}\nprint({parts[0]}, {parts[1]})"
    misread = " ".join(str(v != n) for v, n in zip(naive, negate))
    actual = run_code(code).output
    why = f"{rule} So `{parts[0]}` and `{parts[1]}` give {actual.replace(' ', ' and ')}."
    return _output(code, EASY, [misread, *_bool_rows(2, rng)], why, rng)


# ==========================================================================
# MEDIUM
# ==========================================================================


def _chain_trace(blocks: list[tuple[str, str]], var: str, value: int) -> tuple[list[int], list[str]]:
    """Which blocks run for ``var == value`` (no mutation); plus a phrase per block."""
    ran, phrases = [], []
    chain_done = False
    for i, (kw, cond) in enumerate(blocks):
        if kw == "if":
            chain_done = False
        if kw == "elif" and chain_done:
            phrases.append(f"`elif {cond}` is skipped (its chain already ran a branch)")
            continue
        if _ev(cond, **{var: value}):
            ran.append(i)
            chain_done = True
            phrases.append(f"`{kw} {cond}` is True and runs")
        else:
            phrases.append(f"`{kw} {cond}` is False")
    return ran, phrases


def _cond_on(rng: random.Random, var: str, value: int, kinds: list[str]) -> list[str]:
    conds = []
    for kind in kinds:
        if kind == "gt":
            conds.append(f"{var} > {max(0, value + rng.randint(-6, 2))}")
        elif kind == "lt":
            conds.append(f"{var} < {value + rng.randint(-2, 6)}")
        elif kind == "ge":
            conds.append(f"{var} >= {max(0, value + rng.randint(-6, 1))}")
        else:
            conds.append(f"{var} % {int(kind[3:])} == 0")
    return conds


@generator(TOPIC, MEDIUM)
def gen_if_vs_elif(rng: random.Random) -> Question:
    """Separate `if`s are all checked; an `elif` is skipped once its chain has run."""
    var = rng.choice(["n", "x", "num", "level"])
    use_points = rng.random() < 0.5
    patterns = [("if", "elif"), ("elif", "if"), ("if", "elif"), ("elif", "if"), ("if", "if")]
    for _ in range(100):
        v = rng.randint(4, 24)
        kinds = rng.sample(["gt", "lt", "ge", "mod2", "mod3", "mod5", "gt"], 3)
        conds = _cond_on(rng, var, v, kinds)
        if len(set(conds)) < 3:
            continue
        truth = [_ev(c, **{var: v}) for c in conds]
        if not truth[0] or sum(truth) < 2:
            continue
        kws = rng.choice(patterns)
        has_else = not use_points and rng.random() < 0.5

        def render(pattern: tuple[str, str]) -> str:
            keywords = ["if", *pattern]
            if use_points:
                lines = [f"{var} = {v}", "points = 0"]
                for kw, cond, inc in zip(keywords, conds, (1, 10, 100)):
                    lines += [f"{kw} {cond}:", f"    points += {inc}"]
                lines.append("print(points)")
            else:
                lines = [f"{var} = {v}"]
                for kw, cond, word in zip(keywords, conds, "ABC"):
                    lines += [f"{kw} {cond}:", f'    print("{word}")']
                if has_else:
                    lines += ["else:", '    print("D")']
            return "\n".join(lines)

        code = render(kws)
        correct = _run(code)
        alts = [_run(render(p)) for p in [("if", "if"), ("elif", "elif"), ("if", "elif"), ("elif", "if")]]
        if len({a for a in alts if a != correct}) >= 2:
            break
    else:
        raise GenerationError("could not build an if/elif question")
    if use_points:
        every = sum(inc for inc, t in zip((1, 10, 100), truth) if t)
        extras = [str(every), "1", "111", "0", "11", "101"]
    else:
        every = "\n".join(w for w, t in zip("ABC", truth) if t)
        extras = [every, "A", "A\nB\nC", "A\nD"]
    blocks = list(zip(["if", *kws], conds))
    _, phrases = _chain_trace(blocks, var, v)
    why = (
        "An `elif` is only checked if the `if`/`elif` above it in the SAME chain were all False; a plain "
        f"`if` starts a new chain and is always checked. For {var} = {v}: " + "; ".join(phrases) + "."
    )
    return _output(code, MEDIUM, [*alts, *extras], why, rng)


# (outer flag, inner flag, inner message, else-message if the else is outer / inner, last line)
_NESTED_FLAGS = [
    ("logged_in", "is_admin", "admin panel", ("please log in", "user page"), "home"),
    ("has_ticket", "is_vip", "VIP lounge", ("buy a ticket", "main hall"), "enjoy"),
    ("is_open", "has_stock", "selling", ("closed", "sold out"), "next"),
    ("raining", "windy", "storm", ("dry", "drizzle"), "report done"),
]
_NESTED_NUMS = [
    ("temp", "hot", "warm", "cold"),
    ("score", "great", "good", "low"),
    ("size", "huge", "big", "small"),
    ("speed", "racing", "moving", "parked"),
]


@generator(TOPIC, MEDIUM)
def gen_dangling_else(rng: random.Random) -> Question:
    """Nested ifs: an `else` belongs to the `if` at the SAME indentation."""
    outer_else = rng.random() < 0.6
    if rng.random() < 0.5:
        outer, inner, inner_msg, else_msgs, final = rng.choice(_NESTED_FLAGS)
        else_msg = else_msgs[0] if outer_else else else_msgs[1]
        if outer_else:
            a, b = rng.choice([(True, False), (True, False), (False, True), (True, True)])
        else:
            a, b = rng.choice([(False, True), (False, False), (False, True), (True, False)])
        header = f"{outer} = {a}\n{inner} = {b}\n"
        cond_outer, cond_inner = outer, inner
        env = {outer: a, inner: b}
    else:
        name, big, mid, small = rng.choice(_NESTED_NUMS)
        t1 = rng.randint(2, 6) * 5
        t2 = t1 + rng.randint(2, 5) * 5
        inner_msg = big
        else_msg = small if outer_else else mid
        final = "done"
        roll = rng.random()
        if outer_else:
            v = rng.randint(t1 + 1, t2) if roll < 0.65 else (rng.randint(t1 - 9, t1) if roll < 0.85 else t2 + 3)
        else:
            v = rng.randint(t1 - 9, t1) if roll < 0.6 else (rng.randint(t1 + 1, t2) if roll < 0.85 else t2 + 3)
        header = f"{name} = {v}\n"
        cond_outer, cond_inner = f"{name} > {t1}", f"{name} > {t2}"
        env = {name: v}

    def render(attach_outer: bool) -> str:
        body = f"if {cond_outer}:\n    if {cond_inner}:\n        print(\"{inner_msg}\")\n"
        if attach_outer:
            body += f"else:\n    print(\"{else_msg}\")\n"
        else:
            body += f"    else:\n        print(\"{else_msg}\")\n"
        return header + body + f'print("{final}")'

    code = render(outer_else)
    swapped = _run(render(not outer_else))
    distractors = [
        swapped,
        f"{inner_msg}\n{final}",
        f"{else_msg}\n{final}",
        final,
        else_msg,
        f"{inner_msg}\n{else_msg}\n{final}",
    ]
    o_val, i_val = _ev(cond_outer, **env), _ev(cond_inner, **env)
    owner = f"`if {cond_outer}`" if outer_else else f"`if {cond_inner}`"
    if outer_else:
        detail = (
            f"`{cond_outer}` is {o_val}, so the else {'is skipped' if o_val else 'runs'}"
            + (f"; inside, `{cond_inner}` is {i_val}" if o_val else "")
        )
    else:
        detail = (
            f"`{cond_outer}` is {o_val}"
            + (f", and inside it `{cond_inner}` is {i_val}" if o_val
               else ", so nothing inside it runs — not even the else")
        )
    why = (
        f"An `else` pairs with the `if` at the same indentation, so this `else` belongs to {owner}. "
        f"Here {detail}. The last `print` is not indented, so it always runs."
    )
    return _output(code, MEDIUM, distractors, why, rng)


_SC_VALUES = [("0", 0), ("None", None), ("[]", []), ("3", 3), ("7", 7), ('"hi"', "hi"), ('"ok"', "ok"), ("[5]", [5])]


@generator(TOPIC, MEDIUM)
def gen_short_circuit_value(rng: random.Random) -> Question:
    """`and` / `or` return one of their operands, not necessarily True/False."""
    shape = rng.choice(["default", "pair", "pair", "guard"])
    if shape == "default":
        name, fallback = rng.choice([
            ("name", '"Guest"'), ("nickname", '"Anonymous"'), ("count", '"none"'), ("title", '"Untitled"'),
            ("color", '"black"'), ("limit", "10"),
        ])
        if name in ("count", "limit"):
            lit = rng.choice(["0", "0", "None", str(rng.randint(2, 9))])
        else:
            lit = rng.choice(['""', '""', "None", f'"{rng.choice(["Sam", "Mia", "red", "Zed"])}"'])
        res = rng.choice(["shown", "display", "value", "result"])
        code = f"{name} = {lit}\n{res} = {name} or {fallback}\nprint({res})"
        val = _ev(lit)
        fb = _ev(fallback)
        distractors = ["True", "False", str(fb) if val else str(val) if val != "" else NOTHING_PRINTED,
                       f"{val} {fb}" if val else "None"]
        why = (
            "`x or y` returns `x` itself if `x` is truthy, otherwise it returns `y` — it does not turn "
            f"them into True/False. `{lit}` is {'truthy' if val else 'falsy'}, so `{res}` is "
            f"`{lit if val else fallback}`."
        )
        return _output(code, MEDIUM, distractors, why, rng)

    if shape == "guard":
        items = rng.choice([[], [], [rng.randint(1, 9), rng.randint(1, 9)], ["a", "b"]])
        lst = rng.choice(["items", "queue", "scores", "data"])
        code = f"{lst} = {_src(items)}\nfirst = {lst} and {lst}[0]\nprint(first)"
        distractors = (
            [error_choice("IndexError"), "None", "False", "0"] if not items
            else ["True", str(items), "None", error_choice("IndexError")]
        )
        why = (
            "`and` stops at the first falsy operand and returns it. "
            + (f"`{lst}` is empty (falsy), so `{lst}[0]` is never evaluated — no IndexError — and "
               "`first` is the empty list itself."
               if not items else
               f"`{lst}` is non-empty (truthy), so `and` evaluates and returns `{lst}[0]`, which is {items[0]!r}.")
        )
        return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)

    names = rng.choice([("a", "b"), ("x", "y"), ("left", "right")])
    for _ in range(50):
        (la, va), (lb, vb) = rng.sample(_SC_VALUES, 2)
        if bool(va) != bool(vb) or rng.random() < 0.25:
            break
    exprs = rng.choice([("or", "and"), ("and", "or"), ("or", "or"), ("and", "and")])
    if exprs[0] == exprs[1]:
        parts = [f"{names[0]} {exprs[0]} {names[1]}", f"{names[1]} {exprs[0]} {names[0]}"]
    else:
        parts = [f"{names[0]} {exprs[0]} {names[1]}", f"{names[0]} {exprs[1]} {names[1]}"]
    env = {names[0]: va, names[1]: vb}
    results = [_ev(p, **env) for p in parts]
    code = f"{names[0]} = {la}\n{names[1]} = {lb}\nprint({parts[0]}, {parts[1]})"
    as_bools = f"{bool(results[0])} {bool(results[1])}"
    alt = [[str(va), str(vb), str(bool(r))] for r in results]
    combos = [f"{x} {y}" for x in alt[0] for y in alt[1]]
    rng.shuffle(combos)
    why = (
        "`or` returns the first truthy operand (or the last one if none are truthy); `and` returns the "
        f"first falsy operand (or the last one). With `{names[0]} = {la}` and `{names[1]} = {lb}`: "
        f"`{parts[0]}` → `{results[0]!r}`, `{parts[1]}` → `{results[1]!r}`."
    )
    return _output(code, MEDIUM, [as_bools, *combos], why, rng)


def _chain_misread(a: int, op1: str, b: int, op2: str, c: int) -> bool:
    """`(a op1 b) op2 c` — the left-to-right misreading of a chained comparison."""
    return _CMP[op2](int(_CMP[op1](a, b)), c)


@generator(TOPIC, MEDIUM)
def gen_chained_comparison(rng: random.Random) -> Question:
    """`a < b < c` means `a < b and b < c` — not `(a < b) < c`."""
    if rng.random() < 0.35:
        name, labels = rng.choice([
            ("age", ("child", "teen", "adult")), ("temp", ("cold", "mild", "hot")),
            ("score", ("C", "B", "A")), ("speed", ("slow", "normal", "fast")),
        ])
        a = rng.randint(0, 5)
        b = a + rng.randint(5, 15)
        c = b + rng.randint(5, 15)
        op_lo, op_hi = rng.choice([("<=", "<"), ("<", "<="), ("<=", "<=")])
        v = rng.choice([b, c, b, c, a, rng.randint(a + 1, c - 1)])
        code = (
            f"{name} = {v}\nif {a} {op_lo} {name} {op_hi} {b}:\n    print(\"{labels[0]}\")\n"
            f"elif {b} {op_lo} {name} {op_hi} {c}:\n    print(\"{labels[1]}\")\n"
            f"else:\n    print(\"{labels[2]}\")"
        )
        distractors = [*labels, f"{labels[0]}\n{labels[1]}", f"{labels[1]}\n{labels[2]}"]
        r1 = f"{a} {op_lo} {v} and {v} {op_hi} {b}"
        why = (
            f"`{a} {op_lo} {name} {op_hi} {b}` means `{r1}` — both comparisons must hold. Watch the "
            f"boundaries: `<` excludes the end value and `<=` includes it, so {v} prints `{_run(code)}`."
        )
        return _output(code, MEDIUM, distractors, why, rng)

    name = rng.choice(["x", "n", "age", "temp"])
    for _ in range(200):
        lo = rng.randint(0, 6)
        hi = lo + rng.randint(4, 12)
        v = rng.choice([rng.randint(lo + 1, hi - 1), hi + rng.randint(1, 5), lo, hi])
        op_lo, op_hi = rng.choice([("<", "<"), ("<=", "<"), ("<", "<=")])
        e1 = f"{lo} {op_lo} {name} {op_hi} {hi}"
        r1 = _CMP[op_lo](lo, v) and _CMP[op_hi](v, hi)
        m1 = _chain_misread(lo, op_lo, v, op_hi, hi)
        p, q, r = rng.randint(1, 9), rng.randint(1, 9), rng.randint(1, 9)
        o1, o2 = rng.choice([(">", ">"), ("<", ">"), (">", "<"), ("==", "=="), ("<", "<")])
        e2 = f"{p} {o1} {q} {o2} {r}"
        r2 = _CMP[o1](p, q) and _CMP[o2](q, r)
        m2 = _chain_misread(p, o1, q, o2, r)
        if r2 != m2 and (r1, r2) != (m1, m2):
            break
    else:
        raise GenerationError("no chained comparison found")
    if rng.random() < 0.5:
        e1, e2, r1, r2, m1, m2 = e2, e1, r2, r1, m2, m1
        first_is_lit = True
    else:
        first_is_lit = False
    code = f"{name} = {v}\nprint({e1}, {e2})"
    lit, lit_r = (e1, r1) if first_is_lit else (e2, r2)
    ps = lit.split()
    why = (
        f"A chain like `a < b < c` means `a < b and b < c`, NOT `(a < b) < c`. So `{lit}` means "
        f"`{ps[0]} {ps[1]} {ps[2]} and {ps[2]} {ps[3]} {ps[4]}`, which is {lit_r} — reading it as "
        f"`({ps[0]} {ps[1]} {ps[2]}) {ps[3]} {ps[4]}` would compare True/False (1/0) with {ps[4]}."
    )
    return _output(code, MEDIUM, [f"{m1} {m2}", *_bool_rows(2, rng)], why, rng)


_FLAG_SETS = [
    ("is_open", "has_key", "alarm_on"),
    ("raining", "has_umbrella", "is_cold"),
    ("logged_in", "is_admin", "is_banned"),
    ("hungry", "has_food", "is_late"),
    ("sunny", "weekend", "tired"),
]
# (expression, how a left-to-right reader groups it, how Python groups it)
_PREC_SHAPES = [
    ("{x} or {y} and {z}", "({x} or {y}) and {z}", "{x} or ({y} and {z})"),
    ("{x} and {y} or {z}", "{x} and ({y} or {z})", "({x} and {y}) or {z}"),
    ("not {x} and {y}", "not ({x} and {y})", "(not {x}) and {y}"),
    ("not {x} or {y}", "not ({x} or {y})", "(not {x}) or {y}"),
    ("{x} or not {y} and {z}", "({x} or not {y}) and {z}", "{x} or ((not {y}) and {z})"),
    ("not {x} or {y} and {z}", "(not {x} or {y}) and {z}", "(not {x}) or ({y} and {z})"),
    ("({x} or {y}) and {z}", "({x} or {y}) and {z}", "({x} or {y}) and {z}"),
    ("not ({x} and {y})", "not ({x} and {y})", "not ({x} and {y})"),
    ("{x} and not {y}", "{x} and not {y}", "{x} and (not {y})"),
]


@generator(TOPIC, MEDIUM)
def gen_logic_precedence(rng: random.Random) -> Question:
    """`not` binds tighter than `and`, which binds tighter than `or`."""
    names = list(rng.choice(_FLAG_SETS))
    for _ in range(100):
        vals = [rng.random() < 0.5 for _ in names]
        if len(set(vals)) < 2:
            continue
        env = dict(zip(names, vals))
        target = rng.random() < 0.5
        cands = []
        for expr_f, misread_f, explicit_f in _PREC_SHAPES:
            for perm in itertools.permutations(names):
                fill = dict(zip("xyz", perm))
                expr = expr_f.format(**fill)
                cands.append((expr, _ev(expr, **env), _ev(misread_f.format(**fill), **env),
                              explicit_f.format(**fill)))
        traps = [c for c in cands if c[1] == target and c[2] != target]
        wrong_traps = [c for c in cands if c[1] != target and c[2] == target]
        wrong_plain = [c for c in cands if c[1] != target and c[2] != target]
        if traps and len(wrong_traps) >= 1 and len(wrong_traps) + len(wrong_plain) >= 3:
            break
    else:
        raise GenerationError("no precedence question found")
    correct = rng.choice(traps)
    rng.shuffle(wrong_traps)
    rng.shuffle(wrong_plain)
    k = rng.choice([1, 2, 2])
    wrong = [c[0] for c in wrong_traps[:k] + wrong_plain + wrong_traps[k:]]
    setup = "\n".join(f"{n} = {v}" for n, v in env.items())
    why = (
        f"`not` binds tightest, then `and`, then `or`. So `{correct[0]}` means "
        f"`{correct[3]}`, which is {target} (grouping it left to right would give {correct[2]})."
    )
    return which_expression_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which expression evaluates to `{target}`?",
        setup=setup,
        target=target,
        correct_expr=correct[0],
        wrong_exprs=wrong,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_which_value_branch(rng: random.Random) -> Question:
    """Reverse reasoning: which value of n reaches a given branch of an if/elif/else?"""
    labels = rng.choice([("A", "B", "C"), ("red", "green", "blue"), ("gold", "silver", "bronze"),
                         ("ping", "pong", "pass")])
    t = rng.randint(4, 12)
    k = rng.choice([3, 5])
    lo = rng.randint(2, 6)
    hi = lo + rng.randint(4, 8)
    cond1, cond2 = rng.choice([
        (f"n > {t} and n % 2 == 0", f"n > {t}"),
        (f"n % {k} == 0", "n % 2 == 0"),
        (f"n < {lo} or n > {hi}", f"n == {lo} or n == {hi}"),
        (f"{lo} < n < {hi}", f"n >= {hi}"),
        (f"not n > {t}", "n % 2 == 1"),
        (f"n % 2 == 0 or n > {t}", f"n > {lo}"),
        (f"n >= {t} or n == {lo}", f"n % {k} == 0"),
    ])
    code = (
        f"if {cond1}:\n    print(\"{labels[0]}\")\nelif {cond2}:\n    print(\"{labels[1]}\")\n"
        f"else:\n    print(\"{labels[2]}\")"
    )
    top = max(t, hi) + 7
    groups: dict[str, list[int]] = {lab: [] for lab in labels}
    for n in range(0, top):
        groups[run_code(f"n = {n}\n{code}").output].append(n)
    total = sum(len(g) for g in groups.values())
    order = [lab for lab in (labels[1], labels[1], labels[2], labels[0])
             if groups[lab] and total - len(groups[lab]) >= 3]
    if not order:
        raise GenerationError("not enough candidate values")
    target = rng.choice(order)
    others = [n for lab in labels if lab != target for n in groups[lab]]
    v = rng.choice(groups[target])

    def c1(n: int) -> bool:
        return bool(_ev(cond1, n=n))

    def c2(n: int) -> bool:
        return bool(_ev(cond2, n=n))

    if target == labels[1]:
        traps = [n for n in groups[labels[0]] if c2(n)]
    elif target == labels[2]:
        traps = [n for n in others if abs(n - v) <= 3]
    else:
        traps = [n for n in groups[labels[1]] if abs(n - v) <= 4]
    rng.shuffle(traps)
    rng.shuffle(others)
    picked: list[int] = []
    one_per_group = [rng.choice(groups[lab]) for lab in labels if lab != target and groups[lab]]
    for n in traps[:1] + one_per_group + others:
        if n not in picked:
            picked.append(n)
    if c1(v):
        trace = f"`{cond1}` is True"
    else:
        trace = f"`{cond1}` is False and `{cond2}` is {c2(v)}"
    why = f"With `n = {v}`, {trace}, so it prints `{target}`."
    if target == labels[1] and traps and traps[0] in picked[:3]:
        why += (
            f" A value like {traps[0]} also makes `{cond2}` True, but `{cond1}` is True for it first, so "
            f"it prints `{labels[0]}`."
        )
    # Verify: exactly one offered value prints the target.
    choices = [v, *picked[:3]]
    hits = [n for n in choices if run_code(f"n = {n}\n{code}").output == target]
    if hits != [v]:
        raise GenerationError("ambiguous value question")
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which value of `n` makes this code print `{target}`?",
        correct=str(v),
        distractors=[str(n) for n in picked],
        explanation=why,
        rng=rng,
        code=code,
    )


@generator(TOPIC, MEDIUM)
def gen_grade_loop(rng: random.Random) -> Question:
    """Loop over scores through an if/elif/else ladder — boundaries and branch order."""
    hi = rng.choice([90, 85, 80, 75])
    mid = hi - rng.choice([10, 15])
    op = rng.choice([">=", ">=", ">"])
    letters = rng.choice([("A", "B", "C"), ("A", "B", "C"), ("H", "M", "L")])
    wrong_order = rng.random() < 0.3
    n = rng.randint(3, 4)
    scores = [rng.choice([hi, mid]), rng.randint(hi + 1, 100), rng.randint(mid - 12, mid - 1),
              rng.randint(mid + 1, hi - 1), rng.choice([hi, mid])]
    scores = rng.sample(scores, n)
    acc = rng.choice(["grades", "result", "report"])

    def render(cmp: str, desc: bool, kw2: str = "elif") -> str:
        first, second = ((hi, letters[0]), (mid, letters[1])) if desc else ((mid, letters[1]), (hi, letters[0]))
        return (
            f'{acc} = ""\nfor score in {scores}:\n'
            f"    if score {cmp} {first[0]}:\n        {acc} += \"{first[1]}\"\n"
            f"    {kw2} score {cmp} {second[0]}:\n        {acc} += \"{second[1]}\"\n"
            f"    else:\n        {acc} += \"{letters[2]}\"\nprint({acc})"
        )

    code = render(op, not wrong_order)
    correct = _run(code)
    flipped = ">" if op == ">=" else ">="
    distractors = [
        _run(render(op, True)) if wrong_order else _run(render(flipped, True)),
        _run(render(flipped, not wrong_order)),
        _run(render(op, not wrong_order, "if")),
        correct[:-1],
        _run(render(flipped, wrong_order)),
        correct[::-1],
    ]
    # Fallbacks: one letter changed, boundary scores first.
    swaps = [
        (s not in (hi, mid), correct[:i] + alt + correct[i + 1:])
        for i, s in enumerate(scores)
        for alt in letters
        if alt != correct[i]
    ]
    distractors += [text for _, text in sorted(swaps, key=lambda p: p[0])]
    if wrong_order:
        why = (
            f"`score {op} {mid}` is checked FIRST, so every score that passes it gets `{letters[1]}` — even "
            f"the top ones. The `elif score {op} {hi}` branch can never run: any score that passes it "
            f"already passed `score {op} {mid}`."
        )
    else:
        bset = [s for s in scores if s in (hi, mid)]
        if bset:
            b = bset[0]
            tail = (f"`{op}` {'includes' if op == '>=' else 'excludes'} the boundary, so the score {b} "
                    f"gets `{correct[scores.index(b)]}`.")
        else:
            b = next(s for s in scores if mid < s < hi or s < mid)
            tail = f"For example {b} fails `score {op} {hi}` and gets `{correct[scores.index(b)]}`."
        why = f"Each score adds exactly one letter: the first true condition wins. {tail}"
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_none_vs_falsy(rng: random.Random) -> Question:
    """`not x` is True for 0, "", [] AND None; `x is None` only for None."""
    name = rng.choice(["value", "result", "data", "answer"])
    lit = rng.choice(["0", "None", '""', "[]", "None", "0", str(rng.randint(1, 9)), '"no"'])
    words = rng.choice([("empty", "missing"), ("falsy", "none"), ("blank", "absent")])
    end = rng.choice(["done", "checked", "end"])
    swapped = rng.random() < 0.4
    checks = [(f"not {name}", words[0]), (f"{name} is None", words[1])]
    if swapped:
        checks.reverse()
    code = (
        f"{name} = {lit}\nif {checks[0][0]}:\n    print(\"{checks[0][1]}\")\n"
        f"if {checks[1][0]}:\n    print(\"{checks[1][1]}\")\nprint(\"{end}\")"
    )
    val = _ev(lit)
    first, second = checks[0][1], checks[1][1]
    distractors = [
        f"{first}\n{second}\n{end}",
        f"{words[0]}\n{end}",
        f"{words[1]}\n{end}",
        end,
        f"{first}\n{second}",
    ]
    if val is None:
        why = (
            f"`None` is falsy, so `not {name}` is True — and `{name} is None` is True as well. "
            "Both separate `if`s run."
        )
    elif not val:
        why = (
            f"`{lit}` is falsy, so `not {name}` is True. But it is not `None`, so `{name} is None` is "
            "False — `is None` checks for exactly `None`, not for any falsy value."
        )
    else:
        why = f"`{lit}` is truthy and is not `None`, so neither `if` runs; only the last print does."
    return _output(code, MEDIUM, distractors, why, rng)


# ==========================================================================
# HARD
# ==========================================================================

_CHECKERS = [
    ("is_big", "n > {t}", "checking"),
    ("is_even", "n % 2 == 0", "testing"),
    ("is_positive", "n > 0", "check"),
    ("is_small", "n < {t}", "look at"),
]
_SC_SHAPES = [
    ("not {A} or {B}", "not ({A} or {B})"),
    ("{A} or {B} and {C}", "({A} or {B}) and {C}"),
    ("{A} and {B} or {C}", "{A} and ({B} or {C})"),
    ("not {A} and {B}", "not ({A} and {B})"),
    ("{A} and {B} and {C}", None),
    ("{A} or {B} or {C}", None),
]


@generator(TOPIC, HARD)
def gen_short_circuit_calls(rng: random.Random) -> Question:
    """Function calls with print side effects inside and/or: which calls actually happen?"""
    fn, rule_f, msg = rng.choice(_CHECKERS)
    yes, no = rng.choice([("yes", "no"), ("go", "stop"), ("ok", "fail"), ("pass", "block")])
    for _ in range(200):
        t = rng.randint(3, 7)
        rule = rule_f.format(t=t)
        shape, misread = rng.choice(_SC_SHAPES)
        nargs = shape.count("{")
        lo = -5 if fn == "is_positive" else 1
        args = [rng.randint(lo, 9) for _ in range(nargs)]
        calls = {k: f"{fn}({a})" for k, a in zip("ABC", args)}
        cond = shape.format(**calls)
        head = f'def {fn}(n):\n    print("{msg}", n)\n    return {rule}\n\n\n'

        def render(c: str) -> str:
            return head + f'if {c}:\n    print("{yes}")\nelse:\n    print("{no}")'

        code = render(cond)
        correct = _run(code)
        result = correct.split("\n")[-1]
        eager_calls = "\n".join(f"{msg} {a}" for a in args)
        eager = f"{eager_calls}\n{result}"
        misread_out = _run(render(misread.format(**calls))) if misread else correct
        # Some call must be skipped, and it must take real tracing: 2+ calls or a precedence trap.
        if eager == correct or (correct.count("\n") < 2 and misread_out == correct):
            continue
        distractors = [eager, misread_out]
        flipped = no if result == yes else yes
        distractors += [
            f"{eager_calls}\n{flipped}",
            "\n".join(correct.split("\n")[:-1] + [flipped]),
            result,
            f"{msg} {args[0]}\n{result}",
        ]
        break
    else:
        raise GenerationError("no short-circuit question found")
    called = [f"`{fn}({line.split()[-1]})`" for line in correct.split("\n")[:-1]]
    why = (
        "`and`/`or` evaluate left to right and stop as soon as the answer is known: `and` stops at a "
        "False operand, `or` stops at a True one, so the remaining calls never happen."
    )
    if misread:
        why += f" `{'not' if 'not' in shape else 'and'}` binds tighter, so this is `{_python_group(shape, calls)}`."
    why += f" Only {', '.join(called)} actually ran."
    return _output(code, HARD, distractors, why, rng)


def _python_group(shape: str, calls: dict[str, str]) -> str:
    groups = {
        "{A} or {B} and {C}": "{A} or ({B} and {C})",
        "{A} and {B} or {C}": "({A} and {B}) or {C}",
        "not {A} and {B}": "(not {A}) and {B}",
        "not {A} or {B}": "(not {A}) or {B}",
    }
    return groups.get(shape, shape).format(**calls)


@generator(TOPIC, HARD)
def gen_none_check_order(rng: random.Random) -> Question:
    """0 is a valid result but falsy: `if pos:` vs `is None` checks, and check order."""
    if rng.random() < 0.55:
        items = rng.sample(["ant", "bee", "cat", "dog", "eel", "fox", "gnu"], 3)
        where = rng.choice(["first", "first", "first", "other", "missing"])
        if where == "first":
            target = items[0]
        elif where == "other":
            target = rng.choice(items[1:])
        else:
            target = rng.choice(["owl", "yak", "elk"])
        check = rng.choice(["truthy", "truthy", "not", "is_not_none", "is_none"])
        cond, found_first = {
            "truthy": ("if pos:", True),
            "not": ("if not pos:", False),
            "is_not_none": ("if pos is not None:", True),
            "is_none": ("if pos is None:", False),
        }[check]
        found = '    print("found at", pos)'
        missing = '    print("not found")'
        branches = f"{found}\nelse:\n{missing}" if found_first else f"{missing}\nelse:\n{found}"
        code = (
            "def find(items, target):\n    for i, item in enumerate(items):\n        if item == target:\n"
            f"            return i\n\n\npos = find({_src(items)}, \"{target}\")\n{cond}\n{branches}"
        )
        idx = items.index(target) if target in items else None
        intended = f"found at {idx}" if idx is not None else "not found"
        distractors = [intended, "not found", "found at 0", "found at None", f"found at {(idx or 0) + 1}",
                       "found at -1"]
        if check in ("truthy", "not") and idx == 0:
            why = (
                f"`find` returns 0 because `\"{target}\"` is at index 0 — but 0 is falsy, so "
                f"`{cond[:-1]}` treats it like \"not found\". Use `pos is not None` to tell 0 apart from `None`."
            )
        elif idx is None:
            why = (
                "The loop finishes without returning, so `find` returns `None` (the default return "
                "value), which takes the \"not found\" branch."
            )
        else:
            why = (
                f"`find` returns {idx}. "
                + ("`is None` / `is not None` checks only for `None`, so " if check.startswith("is") else
                   f"{idx} is truthy, so ")
                + f"the code correctly prints `found at {idx}`."
            )
        return _output(code, HARD, distractors, why, rng)

    fruit = rng.sample(["apple", "pear", "plum", "kiwi", "lime", "fig"], 3)
    stock = {fruit[0]: 0, fruit[1]: rng.randint(2, 9)}
    none_first = rng.random() < 0.35
    if none_first:
        item = rng.choice([fruit[0], fruit[2], fruit[1]])
    else:
        item = rng.choice([fruit[2], fruit[2], fruit[0]])
    var = rng.choice(["qty", "count", "left"])
    checks = [(f"not {var}", "sold out"), (f"{var} is None", "unknown item")]
    if none_first:
        checks.reverse()
    dict_src = "{" + ", ".join(f'"{k}": {v}' for k, v in stock.items()) + "}"
    code = (
        f"stock = {dict_src}\n{var} = stock.get(\"{item}\")\n"
        f"if {checks[0][0]}:\n    print(\"{checks[0][1]}\")\nelif {checks[1][0]}:\n    print(\"{checks[1][1]}\")\n"
        f"else:\n    print({var}, \"left\")"
    )
    distractors = ["unknown item", "sold out", "None left", "0 left"]
    # `.get` never raises, but students often expect a KeyError for a missing key.
    distractors.insert(rng.randint(1, 3), error_choice("KeyError"))
    if item not in stock and not none_first:
        why = (
            f"`stock.get(\"{item}\")` returns `None`, and `None` is falsy, so `not {var}` is True and it "
            f"prints \"sold out\". The `elif {var} is None` branch can never run — check `is None` FIRST."
        )
    elif item not in stock:
        why = f"`stock.get(\"{item}\")` returns `None` (no KeyError with `.get`), and `{var} is None` is checked first."
    elif stock[item] == 0:
        why = (
            f"`{var}` is 0, which is falsy but not `None`, so "
            + (f"`{var} is None` is False and `not {var}` is True: \"sold out\"." if none_first
               else f"`not {var}` is True: \"sold out\".")
        )
    else:
        why = f"`{var}` is {stock[item]}: not `None` and truthy, so both checks are False and the `else` runs."
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_AO_VALUES = [("0", 0), ("None", None), ("[]", []), ("5", 5), ('"hi"', "hi"), ("[3]", [3]), ("7", 7),
              ('"ok"', "ok")]
# (expression, left-to-right misreading, how Python groups it as a tree)
_AO_SHAPES = [
    ("{a} or {b} and {c}", "({a} or {b}) and {c}", ("or", "a", ("and", "b", "c"))),
    ("{a} and {b} or {c}", "{a} and ({b} or {c})", ("or", ("and", "a", "b"), "c")),
    ("not {a} or {b}", "not ({a} or {b})", ("or", ("not", "a"), "b")),
    ("not {a} and {b}", "not ({a} and {b})", ("and", ("not", "a"), "b")),
    ("{a} or not {b} and {c}", "({a} or not {b}) and {c}", ("or", "a", ("and", ("not", "b"), "c"))),
]


def _tree_src(node, fill: dict[str, str], top: bool = True) -> str:
    """Fully grouped source of an and/or/not tree, e.g. ``a or (b and c)``."""
    if isinstance(node, str):
        return fill[node]
    if node[0] == "not":
        text = f"not {_tree_src(node[1], fill, False)}"
        return text if top else f"({text})"
    text = f"{_tree_src(node[1], fill, False)} {node[0]} {_tree_src(node[2], fill, False)}"
    return text if top else f"({text})"


def _tree_trace(node, fill: dict[str, str], env: dict[str, object], steps: list[str]) -> object:
    """Evaluate the tree left to right like Python does, recording each short-circuit decision."""
    if isinstance(node, str):
        return env[fill[node]]
    if node[0] == "not":
        return not _tree_trace(node[1], fill, env, steps)
    op, left, right = node
    lv = _tree_trace(left, fill, env, steps)
    stop = bool(lv) if op == "or" else not lv
    kind = "truthy" if lv else "falsy"
    if stop:
        steps.append(f"`{_tree_src(left, fill)}` is `{lv!r}` ({kind}), so `{op}` returns it")
        return lv
    steps.append(f"`{_tree_src(left, fill)}` is `{lv!r}` ({kind}), so `{op}` returns its right side")
    return _tree_trace(right, fill, env, steps)


@generator(TOPIC, HARD)
def gen_and_or_values(rng: random.Random) -> Question:
    """Precedence + returned operand values, and the `cond and X or Y` pseudo-ternary bug."""
    if rng.random() < 0.4:
        var = rng.choice(["count", "lives", "score", "stock"])
        v = rng.choice([0, 0, 0, rng.randint(1, 9)])
        cond = rng.choice([f"{var} >= 0", f"{var} < 10", f"{var} != 5"])
        default = rng.choice(['"invalid"', '"none"', "-1", '"max"'])
        res = rng.choice(["label", "shown", "result"])
        code = f"{var} = {v}\n{res} = {cond} and {var} or {default}\nprint({res})"
        intended = str(v)
        dflt = str(_ev(default))
        distractors = [intended, "True", "False", dflt, f"{v} {dflt}"]
        if v == 0:
            why = (
                f"`{cond}` is True, so `and` returns `{var}`, which is 0 — falsy! So `or` moves on and "
                f"returns {default}. `cond and A or B` breaks when A is falsy; use `A if cond else B`."
            )
        else:
            why = (
                f"`{cond}` is True, so `and` returns `{var}` ({v}), which is truthy, so `or` returns it "
                "without looking at the right side."
            )
        return _output(code, HARD, distractors, why, rng)

    names = rng.choice([("a", "b", "c"), ("x", "y", "z"), ("p", "q", "r")])
    fill = dict(zip("abc", names))
    for _ in range(300):
        expr_f, mis_f, tree = rng.choice(_AO_SHAPES)
        picks = [rng.choice(_AO_VALUES) for _ in range(3)]
        env = {n: val for n, (_, val) in zip(names, picks)}
        expr = expr_f.format(**fill)
        actual = _ev(expr, **env)
        misread = _ev(mis_f.format(**fill), **env)
        if str(actual) != str(misread) and not isinstance(actual, bool) or (
            isinstance(actual, bool) and str(actual) != str(misread) and rng.random() < 0.2
        ):
            break
    else:
        raise GenerationError("no and/or value question found")
    used = [n for n in names if re.search(rf"\b{n}\b", expr)]
    setup = "\n".join(f"{n} = {lit}" for n, (lit, _) in zip(names, picks) if n in used)
    code = f"{setup}\nprint({expr})"
    distractors = [str(misread), str(bool(actual)), str(not bool(actual))]
    distractors += [str(env[n]) for n in used]
    distractors += [repr(actual), *(str(val) for _, val in _AO_VALUES)]  # fallbacks
    steps: list[str] = []
    if _tree_trace(tree, fill, env, steps) != actual:
        raise GenerationError("trace disagrees with Python")
    why = (
        f"`not` binds tightest, then `and`, then `or`, so this means `{_tree_src(tree, fill)}`. "
        f"Left to right: " + "; ".join(steps) + f" — giving `{actual!r}`. `and`/`or` return an operand, "
        "not just True/False."
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_branch_mutation(rng: random.Random) -> Question:
    """Branches that change the variable later conditions test (if vs elif matters)."""
    var = rng.choice(["x", "n", "level", "count"])
    for _ in range(300):
        v = rng.randint(3, 15)
        kinds = [rng.choice(["gt", "lt", "even", "eq"]) for _ in range(3)]
        blocks = []
        for kind in kinds:
            t = v + rng.randint(-4, 4)
            cond = {"gt": f"{var} > {t}", "lt": f"{var} < {t}", "even": f"{var} % 2 == 0",
                    "eq": f"{var} == {t}"}[kind]
            k = rng.randint(2, 5)
            body = rng.choice([f"{var} -= {k}", f"{var} += {k}", f"{var} *= {k}", f"{var} //= 2"])
            blocks.append((cond, body))
        if len({c for c, _ in blocks}) < 3:
            continue
        kws = ["if", *rng.choice([("elif", "if"), ("if", "elif"), ("elif", "if"), ("if", "if")])]

        def render(keywords: list[str], frozen: bool = False) -> str:
            lines = [f"{var} = {v}"]
            if frozen:  # every condition looks at the ORIGINAL value (a common misreading)
                lines.append(f"start = {var}")
            for kw, (cond, body) in zip(keywords, blocks):
                c = cond.replace(var, "start", 1) if frozen else cond
                lines += [f"{kw} {c}:", f"    {body}"]
            lines.append(f"print({var})")
            return "\n".join(lines)

        code = render(kws)
        correct = _run(code)
        alts = [
            _run(render(kws, frozen=True)),
            _run(render(["if", "if", "if"])),
            _run(render(["if", "elif", "elif"])),
        ]
        ran = _mutation_trace(kws, blocks, var, v)
        mutated_then_tested = any(r[0] == "ran" for r in ran[:-1]) and sum(r[0] != "skipped" for r in ran[1:]) >= 1
        if len({a for a in alts if a != correct}) >= 2 and mutated_then_tested and "-" not in correct:
            break
    else:
        raise GenerationError("no mutation question found")
    trace = []
    for (status, value), kw, (cond, body) in zip(ran, kws, blocks):
        if status == "skipped":
            trace.append(f"`elif {cond}` skipped")
        elif status == "ran":
            trace.append(f"`{cond}` True → `{body}` → {value}")
        else:
            trace.append(f"`{cond}` False")
    why = (
        f"A new `if` re-tests the CURRENT value, while an `elif` is skipped once its chain has run. "
        f"Trace from {var} = {v}: " + "; ".join(trace) + "."
    )
    extra = [_run(render(p)) for p in (["if", "elif", "if"], ["if", "if", "elif"])]
    extra.append(_run("\n".join(code.split("\n")[:-3] + [f"print({var})"])))  # forgot the last block
    nearby = [str(int(correct) + d) for d in (1, -1, 2, -2) if int(correct) + d >= 0]
    return _output(code, HARD, [*alts, *extra, str(v), *nearby], why, rng)


def _mutation_trace(kws: list[str], blocks: list[tuple[str, str]], var: str, v: int) -> list[tuple[str, int]]:
    out = []
    value = v
    chain_done = False
    for kw, (cond, body) in zip(kws, blocks):
        if kw == "if":
            chain_done = False
        if kw == "elif" and chain_done:
            out.append(("skipped", value))
            continue
        if _ev(cond, **{var: value}):
            res = run_code(f"{var} = {value}\n{body}")
            value = res.namespace[var]
            chain_done = True
            out.append(("ran", value))
        else:
            out.append(("false", value))
    return out


@generator(TOPIC, HARD)
def gen_ternary_precedence(rng: random.Random) -> Question:
    """`a + b if c else d` is `(a + b) if c else d` — the whole left side is the 'then' value."""
    shape = rng.choice(["arith", "arith", "greet", "else_arith"])
    if shape == "greet":
        name_v = rng.choice(['""', '""', '""', rng.choice(['"Sam"', '"Mia"', '"Leo"'])])
        prefix, fallback = rng.choice([
            ('"Hi, "', '"Guest"'), ('"Hello "', '"stranger"'), ('"Dear "', '"Customer"'), ('"@"', '"anon"'),
        ])
        res = rng.choice(["greeting", "label", "msg"])
        code = f"name = {name_v}\n{res} = {prefix} + name if name else {fallback}\nprint({res})"
        p, f, nv = _ev(prefix), _ev(fallback), _ev(name_v)
        misread = p + (nv if nv else f)
        distractors = [misread, p.rstrip(), error_choice("SyntaxError"), f, error_choice("TypeError")]
        why = (
            "The conditional expression has the LOWEST precedence, so this is "
            f"`({prefix} + name) if name else {fallback}` — not `{prefix} + (name if name else {fallback})`. "
            + ("`name` is empty (falsy), so the result is just the fallback, without the prefix."
               if not nv else f"`name` is truthy, so the result is the whole `{prefix} + name`.")
        )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)

    a, b, c = rng.sample(range(2, 10), 3)
    op = rng.choice(["+", "*", "-"])
    names = rng.choice([("base", "bonus"), ("price", "tax"), ("x", "y"), ("width", "extra")])
    flag = rng.choice(["vip", "member", "ready", "flag"])
    f_val = rng.random() < (0.2 if shape == "arith" else 0.85)
    res = rng.choice(["total", "result", "value"])
    setup = f"{names[0]} = {a}\n{names[1]} = {b}\n{flag} = {f_val}\n"
    if shape == "arith":
        expr = f"{names[0]} {op} {names[1]} if {flag} else {c}"
        actual = _ev(f"{a} {op} {b}") if f_val else c
        misread = _ev(f"{a} {op} ({b} if {f_val} else {c})")
        grouping = f"({names[0]} {op} {names[1]}) if {flag} else {c}"
        other = c if f_val else _ev(f"{a} {op} {b}")
    else:
        expr = f"{c} if {flag} else {names[0]} {op} {names[1]}"
        actual = c if f_val else _ev(f"{a} {op} {b}")
        misread = _ev(f"({c} if {f_val} else {a}) {op} {b}")
        grouping = f"{c} if {flag} else ({names[0]} {op} {names[1]})"
        other = _ev(f"{a} {op} {b}") if f_val else c
    code = f"{setup}{res} = {expr}\nprint({res})"
    distractors = [str(misread), str(other), str(a), str(b), str(actual + 1), str(f_val)]
    why = (
        f"`X if cond else Y` has lower precedence than `{op}`, so Python reads this as `{grouping}`. "
        f"`{flag}` is {f_val}, so `{res}` is {actual}."
    )
    return _output(code, HARD, distractors, why, rng)


_FB_WORDS = [("Fizz", "Buzz"), ("Foo", "Bar"), ("Ping", "Pong")]


@generator(TOPIC, HARD)
def gen_fizzbuzz_order(rng: random.Random) -> Question:
    """FizzBuzz-style chains where the ORDER of the checks (or if vs elif) matters."""
    d1, d2 = rng.choice([(3, 5), (2, 3), (2, 5), (3, 4)])
    both_d = d1 * d2
    w1, w2 = rng.choice(_FB_WORDS)
    if rng.random() < 0.5:
        end = rng.randint(both_d + 1, 2 * both_d + 3)
        order = rng.choice(["last", "last", "first", "middle", "ifs"])
        names = rng.choice([("fizz", "buzz", "both"), ("f", "b", "fb"), ("c1", "c2", "c12")])

        def render(kind: str, stop: int) -> str:
            checks = {
                "one": (f"n % {d1} == 0", f"{names[0]} += 1"),
                "two": (f"n % {d2} == 0", f"{names[1]} += 1"),
                "both": (f"n % {both_d} == 0", f"{names[2]} += 1"),
            }
            seq = {"last": ["one", "two", "both"], "first": ["both", "one", "two"],
                   "middle": ["one", "both", "two"], "ifs": ["one", "two", "both"]}[kind]
            lines = [f"{names[0]} = {names[1]} = {names[2]} = 0", f"for n in range(1, {stop}):"]
            for i, key in enumerate(seq):
                kw = "if" if i == 0 or kind == "ifs" else "elif"
                cond, body = checks[key]
                lines += [f"    {kw} {cond}:", f"        {body}"]
            lines.append(f"print({names[0]}, {names[1]}, {names[2]})")
            return "\n".join(lines)

        code = render(order, end)
        others = [k for k in ["first", "last", "ifs", "middle"] if k != order]
        distractors = [_run(render(k, end)) for k in others]
        distractors += [_run(render(order, stop)) for stop in (end + 1, end - 1, end + 2, end - 2)]
        distractors += [_run(render(k, stop)) for k in others for stop in (end + 1, end - 1)]
        multiples = [n for n in range(both_d, end, both_d)]
        if order in ("last", "middle"):
            why = (
                f"Every multiple of {both_d} ({', '.join(map(str, multiples))}) is also a multiple of {d1}, so "
                f"the earlier `n % {d1} == 0` branch catches it and the `n % {both_d}` check is never "
                f"reached. `range(1, {end})` stops at {end - 1}."
            )
        elif order == "first":
            why = (
                f"The `n % {both_d}` check comes first, so multiples of {both_d} count only in `{names[2]}`; the "
                f"`elif`s then handle the remaining multiples of {d1} and {d2}. `range(1, {end})` stops at {end - 1}."
            )
        else:
            why = (
                f"These are separate `if`s, so every check runs for every `n`: a multiple of {both_d} adds 1 "
                f"to all three counters. `range(1, {end})` stops at {end - 1}."
            )
        return _output(code, HARD, distractors, why, rng)

    order = rng.choice(["last", "ifs", "first", "ifs"])
    for _ in range(100):
        start = rng.randint(max(1, both_d - 4), both_d)
        stop = start + rng.randint(4, 5)
        if not start <= both_d < stop:
            continue

        def render(kind: str, s: int, e: int) -> str:
            lines = ["out = []", f"for n in range({s}, {e}):"]
            if kind == "ifs":
                lines += [f"    if n % {d1} == 0:", f'        out.append("{w1}")',
                          f"    if n % {d2} == 0:", f'        out.append("{w2}")',
                          "    else:", "        out.append(n)"]
            else:
                checks = [(f"n % {d1} == 0", f'"{w1}"'), (f"n % {d2} == 0", f'"{w2}"'),
                          (f"n % {both_d} == 0", f'"{w1}{w2}"')]
                if kind == "first":
                    checks = [checks[2], checks[0], checks[1]]
                for i, (cond, val) in enumerate(checks):
                    lines += [f"    {'if' if i == 0 else 'elif'} {cond}:", f"        out.append({val})"]
                lines += ["    else:", "        out.append(n)"]
            lines.append("print(out)")
            return "\n".join(lines)

        code = render(order, start, stop)
        correct = _run(code)
        others = [k for k in ["first", "last", "ifs"] if k != order]
        distractors = [_run(render(k, start, stop)) for k in others]
        distractors += [_run(render(order, start, stop + 1)), _run(render(order, start + 1, stop))]
        if _fits(correct) and sum(_fits(d) and d != correct for d in distractors) >= 3:
            break
    else:
        raise GenerationError("fizzbuzz output too long")
    if order == "ifs":
        why = (
            f"The two checks are separate `if`s and the `else` belongs only to the second one. So a "
            f"multiple of {d1} that isn't a multiple of {d2} appends `\"{w1}\"` AND then the number itself; "
            f"{both_d} appends both words."
        )
    elif order == "last":
        why = (
            f"{both_d} is a multiple of {d1}, so the first branch catches it and appends `\"{w1}\"`; the "
            f"`n % {both_d}` check can never be reached. Only one branch of an if/elif chain runs."
        )
    else:
        why = (
            f"The `n % {both_d}` check comes first, so {both_d} becomes `\"{w1}{w2}\"`; other numbers fall "
            f"through to the `{d1}`/`{d2}` checks or the `else`. `range({start}, {stop})` stops at {stop - 1}."
        )
    return _output(code, HARD, distractors, why, rng)


_TF_FALSY = [("0", 0), ('""', ""), ("[]", []), ("None", None), ("0.0", 0.0)]
_TF_TRICKY = [('"0"', "0"), ('" "', " "), ('"False"', "False"), ("[0]", [0]), ("[None]", [None]),
              ("-1", -1), ('"None"', "None")]


@generator(TOPIC, HARD)
def gen_truthy_filter(rng: random.Random) -> Question:
    """Filter a list of tricky values with `if v:`, `if not v:` or `if v is not None:`."""
    for _ in range(100):
        falsy = rng.sample(_TF_FALSY, rng.randint(2, 3))
        tricky = rng.sample(_TF_TRICKY, rng.randint(2, 3))
        values = falsy + tricky
        rng.shuffle(values)
        check = rng.choice(["truthy", "truthy", "falsy", "not_none"])
        if check == "not_none" and not any(lit == "None" for lit, _ in values):
            continue
        cond = {"truthy": "v", "falsy": "not v", "not_none": "v is not None"}[check]
        lst = rng.choice(["values", "items", "data"])
        count_mode = rng.random() < 0.25
        acc = rng.choice(["count", "total"] if count_mode else ["kept", "picked", "out"])
        src = "[" + ", ".join(lit for lit, _ in values) + "]"
        if count_mode:
            code = f"{lst} = {src}\n{acc} = 0\nfor v in {lst}:\n    if {cond}:\n        {acc} += 1\nprint({acc})"
        else:
            code = f"{lst} = {src}\n{acc} = []\nfor v in {lst}:\n    if {cond}:\n        {acc}.append(v)\nprint({acc})"
        if len(src) + 12 > 79:
            continue

        def show(pred) -> str:
            kept = [val for _, val in values if pred(val)]
            return str(len(kept)) if count_mode else repr(kept)

        tricky_ids = [id(val) for _, val in tricky]

        def misjudged(*which: int):
            """Truthiness as a student who thinks the chosen tricky values are falsy sees it."""
            ids = {tricky_ids[i] for i in which}
            return lambda x: bool(x) and id(x) not in ids

        every = tuple(range(len(tricky)))
        if check == "truthy":
            cands = [show(misjudged(0)), show(misjudged(*every)), show(misjudged(1)),
                     show(lambda x: not x), show(lambda x: x is not None)]
        elif check == "falsy":
            cands = [show(lambda x: not misjudged(*every)(x)), show(lambda x: not misjudged(0)(x)),
                     show(lambda x: not misjudged(1)(x)), show(bool), show(lambda x: x is None)]
        else:
            cands = [show(bool), show(lambda x: x is not None and x != "None"),
                     show(lambda x: True), show(lambda x: x is None), show(misjudged(*every))]
        correct = _run(code)
        if all(_fits(c) for c in cands + [correct]) and len({c for c in cands if c != correct}) >= 3:
            break
    else:
        raise GenerationError("no truthiness filter question found")
    trick_lits = ", ".join(f"`{lit}`" for lit, _ in tricky)
    if check == "not_none":
        others = ", ".join(f"`{lit}`" for lit, _ in falsy if lit != "None")
        why = (
            f"`v is not None` only filters out `None` itself — it is NOT the same as `if v:`. Falsy "
            f"values like {others} are not `None`, so they still pass."
        )
    else:
        reasons = []
        if any(isinstance(val, str) for _, val in tricky):
            reasons.append("a non-empty string is truthy whatever it says")
        if any(isinstance(val, list) for _, val in tricky):
            reasons.append("a non-empty list is truthy whatever it holds")
        if any(isinstance(val, int) for _, val in tricky):
            reasons.append("any non-zero number is truthy")
        falsy_lits = ", ".join(f"`{lit}`" for lit, _ in falsy)
        why = (
            f"Only zero, empty strings/lists and `None` are falsy — here {falsy_lits}. {trick_lits} "
            f"{'are' if len(tricky) > 1 else 'is'} truthy: " + "; ".join(reasons) + "."
        )
    return _output(code, HARD, cands, why, rng)
