"""Question generators for the "dicts" topic (Dictionaries).

Covers lookup by key (not by position, not by value), ``KeyError``, ``get``
with and without a default, adding vs overwriting keys, ``len``, ``in`` checking
KEYS only, iterating over keys / ``values()`` / ``items()`` in insertion order,
the counting pattern, ``pop``/``popitem``/``del``, ``update``, nested dicts,
``max``/``sorted``/``sum`` working on keys, order-insensitive equality, and the
harder gotchas: duplicate keys (first position, last value), ``1``/``1.0``/
``True`` being one key, unhashable keys, aliasing vs (shallow) copies, changing
a dict's size while looping over it, ``setdefault``, grouping and inverting.
"""

from __future__ import annotations

import itertools
import random

from ..base import (
    EASY,
    HARD,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    MEDIUM,
    NAMES,
    NOTHING_PRINTED,
    GenerationError,
    Question,
    build_question,
    error_choice,
    generator,
    int_distractors,
    output_question,
    run_code,
    which_expression_question,
)

TOPIC = "dicts"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
KEY_ERROR = error_choice("KeyError")
TYPE_ERROR = error_choice("TypeError")
INDEX_ERROR = error_choice("IndexError")
NAME_ERROR = error_choice("NameError")
RUNTIME_ERROR = error_choice("RuntimeError")
BLANK = "___"


# --------------------------------------------------------------------------
# Data pools
# --------------------------------------------------------------------------

_FRUITS = ["apple", "pear", "kiwi", "plum", "fig", "lime", "mango", "peach", "grape", "lemon"]
_COLORS = ["red", "blue", "green", "gold", "pink", "gray", "teal"]
_ITEMS = ["pen", "cap", "map", "cup", "book", "lamp", "mug", "bag"]
_SETTINGS = ["level", "lives", "speed", "size", "volume", "width"]

# (dict name, key pool, min value, max value, loop name for keys, loop name for values)
_INT_THEMES = [
    ("prices", _FRUITS, 1, 9, "fruit", "price"),
    ("stock", _FRUITS, 2, 15, "fruit", "qty"),
    ("ages", NAMES, 8, 16, "name", "age"),
    ("points", NAMES, 1, 20, "name", "pts"),
    ("votes", _COLORS, 1, 12, "color", "n"),
]

# (dict name, full mapping, loop name for keys, loop name for values)
_STR_THEMES = [
    (
        "capitals",
        {
            "France": "Paris",
            "Japan": "Tokyo",
            "Italy": "Rome",
            "Peru": "Lima",
            "Egypt": "Cairo",
            "Spain": "Madrid",
            "Cuba": "Havana",
            "Norway": "Oslo",
        },
        "country",
        "city",
    ),
    (
        "sounds",
        {
            "cat": "meow",
            "dog": "woof",
            "cow": "moo",
            "owl": "hoot",
            "duck": "quack",
            "bee": "buzz",
            "lion": "roar",
            "pig": "oink",
            "sheep": "baa",
        },
        "animal",
        "sound",
    ),
    (
        "colors",
        {
            "lime": "green",
            "plum": "purple",
            "lemon": "yellow",
            "cherry": "red",
            "kiwi": "brown",
            "berry": "blue",
            "peach": "orange",
        },
        "fruit",
        "color",
    ),
]


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _lit(value) -> str:
    """``value`` written as PEP 8 style source code (double-quoted strings)."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join(_lit(x) for x in value) + "]"
    if isinstance(value, tuple):
        inner = ", ".join(_lit(x) for x in value)
        return f"({inner},)" if len(value) == 1 else f"({inner})"
    if isinstance(value, dict):
        return _src(value)
    return repr(value)


def _src(d: dict) -> str:
    return "{" + ", ".join(f"{_lit(k)}: {_lit(v)}" for k, v in d.items()) + "}"


def _assign(var: str, d: dict) -> str:
    """``var = {...}`` on one line, or one pair per line if that is too long."""
    line = f"{var} = {_src(d)}"
    if len(line) <= 72 or not d:
        return line
    body = "".join(f"    {_lit(k)}: {_lit(v)},\n" for k, v in d.items())
    return f"{var} = {{\n{body}}}"


def _pairs_repr(pairs) -> str:
    """How Python would print a dict holding ``pairs`` (duplicates allowed)."""
    return "{" + ", ".join(f"{k!r}: {v!r}" for k, v in pairs) + "}"


def _lines(values) -> str:
    return "\n".join(str(v) for v in values)


def _run(code: str) -> str:
    """The choice text for what ``code`` prints, or the error it raises."""
    res = run_code(code)
    if res.error:
        return error_choice(res.error)
    return res.output if res.output else NOTHING_PRINTED


def _fits(choice: str) -> bool:
    lines = choice.strip("\n").split("\n")
    return (
        bool(choice.strip())
        and len(lines) <= MAX_CHOICE_LINES
        and all(len(line.rstrip()) <= MAX_CHOICE_LINE_LEN for line in lines)
    )


def _usable(distractors) -> list[str]:
    """Stringify distractors and drop any that would not fit on a button."""
    out = []
    for d in distractors:
        if d is None:
            continue
        d = str(d)
        if d == "":
            d = NOTHING_PRINTED
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
    prompt: str = "What does this code print?",
    allow_error: bool = False,
) -> Question:
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=_usable(distractors),
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _value_question(
    code: str,
    var: str,
    difficulty: int,
    distractors,
    explanation: str,
    rng: random.Random,
) -> Question:
    """'What is the value of `var` after this code runs?' - verified by running it."""
    res = run_code(code)
    if res.error or var not in res.namespace:
        raise GenerationError(f"snippet failed ({res.error}):\n{code}")
    correct = repr(res.namespace[var])
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=f"What is the value of `{var}` after this code runs?",
        correct=correct,
        distractors=_usable(distractors),
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _int_dict(rng: random.Random, n: int):
    """A themed str -> int dict with distinct values.

    Returns ``(var, d, spare, key_name, val_name)`` where ``spare`` is a key
    from the same pool that is NOT in ``d``.
    """
    var, pool, lo, hi, key_name, val_name = rng.choice(_INT_THEMES)
    keys = rng.sample(pool, n + 1)
    vals = rng.sample(range(lo, hi + 1), n)
    return var, dict(zip(keys[:n], vals)), keys[n], key_name, val_name


def _str_dict(rng: random.Random, n: int):
    """A themed str -> str dict; same return shape as :func:`_int_dict`."""
    var, mapping, key_name, val_name = rng.choice(_STR_THEMES)
    keys = rng.sample(sorted(mapping), n + 1)
    return var, {k: mapping[k] for k in keys[:n]}, keys[n], key_name, val_name


def _any_dict(rng: random.Random, n: int):
    return _int_dict(rng, n) if rng.random() < 0.6 else _str_dict(rng, n)


def _bools(values) -> str:
    return " ".join(str(v) for v in values)


def _bool_distractors(correct, misconception, rng: random.Random) -> list[str]:
    """All other True/False combinations, the likely misconception first."""
    others = [
        list(c)
        for c in itertools.product([True, False], repeat=len(correct))
        if list(c) != list(correct) and list(c) != list(misconception)
    ]
    rng.shuffle(others)
    return [_bools(misconception)] + [_bools(c) for c in others]


def _derangement(rng: random.Random, n: int) -> list[int]:
    """A shuffled ``range(n)`` where no number sits at its own position."""
    while True:
        perm = list(range(n))
        rng.shuffle(perm)
        if all(p != i for i, p in enumerate(perm)):
            return perm


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_lookup(rng: random.Random) -> Question:
    """Square brackets look up a KEY: not a position, not a value; missing -> KeyError."""
    shape = rng.choices(["key", "int_keys", "missing", "by_value"], weights=[4, 3, 2, 2])[0]
    if shape == "int_keys":
        n = rng.choice([3, 4])
        keys = _derangement(rng, n)
        vals = rng.sample(NAMES, n)
        var = rng.choice(["seats", "lockers", "lanes", "desks"])
        d = dict(zip(keys, vals))
        k = rng.randrange(n)
        code = f"{_assign(var, d)}\nprint({var}[{k}])"
        distractors = [vals[k], vals[k - 1], INDEX_ERROR, KEY_ERROR, str(k)]
        why = (
            f"`{var}[{k}]` looks up the KEY {k}, not position {k}. The pair "
            f"`{k}: {_lit(d[k])}` is in the dictionary, so it prints {d[k]}."
        )
    else:
        var, d, spare, _, _ = _any_dict(rng, 3)
        keys = list(d)
        k = rng.choice(keys)
        v = d[k]
        others = [d[x] for x in keys if x != k]
        if shape == "key":
            code = f"{_assign(var, d)}\nprint({var}[{_lit(k)}])"
            distractors = [k, KEY_ERROR, *others]
            rng.shuffle(distractors)
            why = (
                f"Square brackets look up a key and give back the value stored with it, "
                f"so `{var}[{_lit(k)}]` is {v!r}."
            )
        elif shape == "missing":
            code = f"{_assign(var, d)}\nprint({var}[{_lit(spare)}])"
            distractors = [
                "None",
                "0" if isinstance(v, int) else NOTHING_PRINTED,
                INDEX_ERROR,
                NAME_ERROR,
                NOTHING_PRINTED,
            ]
            why = (
                f"{spare!r} is not a key in `{var}`, so `{var}[{_lit(spare)}]` raises a "
                f"KeyError. Only `.get()` quietly returns None for a missing key."
            )
        else:  # by_value
            code = f"{_assign(var, d)}\nprint({var}[{_lit(v)}])"
            positional = others[0]
            if isinstance(v, int) and v < len(keys):
                positional = d[keys[v]]
            distractors = [k, "None", positional, INDEX_ERROR, NOTHING_PRINTED]
            why = (
                f"{v!r} is a VALUE in `{var}`, not a key. Lookups only go from key to "
                f"value, so `{var}[{_lit(v)}]` raises a KeyError."
            )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_get(rng: random.Random) -> Question:
    """``get`` returns None (or the default) for a missing key instead of crashing."""
    shape = rng.choices(
        ["exists", "missing", "missing_default", "exists_default", "plus"],
        weights=[2, 2, 2, 2, 3],
    )[0]
    if shape == "plus":
        var, d, spare, _, _ = _int_dict(rng, 3)
        sub = rng.choice(["exists", "missing0", "missing_none"])
        k = rng.choice(list(d)) if sub == "exists" else spare
        default = ", 0" if sub == "missing0" or (sub == "exists" and rng.random() < 0.5) else ""
        n = rng.choice(["n", "count", "amount"])
        code = f"{_assign(var, d)}\n{n} = {var}.get({_lit(k)}{default})\nprint({n} + 1)"
        if sub == "exists":
            distractors = [str(d[k]), "1", TYPE_ERROR, KEY_ERROR]
            why = (
                f"{k!r} is a key, so `get` returns its value {d[k]}"
                + (" (the default 0 is ignored)" if default else "")
                + f", and {d[k]} + 1 is {d[k] + 1}."
            )
        elif sub == "missing0":
            distractors = [TYPE_ERROR, KEY_ERROR, "None", str(rng.choice(list(d.values())) + 1)]
            why = f"{k!r} is missing, so `get` returns the default 0, and 0 + 1 is 1."
        else:
            distractors = ["1", KEY_ERROR, "None", "0"]
            why = (
                f"{k!r} is missing, so `get` returns None. `get` does not crash, but the "
                f"next line does: `None + 1` raises a TypeError."
            )
        return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)

    var, d, spare, _, _ = _any_dict(rng, 3)
    k = rng.choice(list(d))
    v = d[k]
    other = rng.choice([x for x in d.values() if x != v])
    if isinstance(v, int):
        default = rng.choice([0, 0, -1, 99])
    else:
        default = rng.choice(["unknown", "?", "n/a"])
    if shape == "exists":
        code = f"{_assign(var, d)}\nprint({var}.get({_lit(k)}))"
        distractors = ["None", k, other, KEY_ERROR]
        why = f"{k!r} is a key in `{var}`, so `get` returns its value, {v!r}."
    elif shape == "missing":
        code = f"{_assign(var, d)}\nprint({var}.get({_lit(spare)}))"
        distractors = [KEY_ERROR, NOTHING_PRINTED, "0" if isinstance(v, int) else "False", spare]
        why = (
            f"{spare!r} is not a key. Unlike `{var}[{_lit(spare)}]`, `get` does not raise "
            f"a KeyError: with no default given it returns None, and `print` shows None."
        )
    elif shape == "missing_default":
        code = f"{_assign(var, d)}\nprint({var}.get({_lit(spare)}, {_lit(default)}))"
        distractors = ["None", KEY_ERROR, spare, NOTHING_PRINTED]
        why = (
            f"{spare!r} is not a key, so `get` returns the default you passed as its "
            f"second argument: {default!r}."
        )
    else:
        code = f"{_assign(var, d)}\nprint({var}.get({_lit(k)}, {_lit(default)}))"
        distractors = [str(default), "None", k, KEY_ERROR]
        why = (
            f"The default {default!r} is only used when the key is missing. {k!r} IS a "
            f"key, so `get` returns its value, {v!r}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_assign_key(rng: random.Random) -> Question:
    """``d[k] = v`` overwrites an existing key in place, or adds a new key at the end."""
    shape = rng.choice(["overwrite", "add", "increment"])
    if shape == "add":
        var, d, spare, _, _ = _any_dict(rng, 3)
        if isinstance(next(iter(d.values())), str):
            var, d, spare, _, _ = _str_dict(rng, 2)
            nv = dict(next(t[1] for t in _STR_THEMES if t[0] == var))[spare]
        else:
            nv = rng.choice([x for x in range(1, 13) if x not in d.values()])
        items = list(d.items())
        code = f"{_assign(var, d)}\n{var}[{_lit(spare)}] = {_lit(nv)}\nprint({var})"
        distractors = [
            _pairs_repr([(spare, nv)] + items),
            repr(dict(sorted(items + [(spare, nv)]))),
            repr(d),
            _pairs_repr(items[:1] + [(spare, nv)] + items[1:]),
        ]
        why = (
            f"Assigning to a key that doesn't exist yet adds a new pair. Dictionaries keep "
            f"insertion order, so {spare!r}: {nv!r} goes at the end."
        )
        return _output(code, EASY, distractors, why, rng)

    var, d, _, _, _ = _int_dict(rng, 3)
    items = list(d.items())
    keys = list(d)
    k = rng.choice(keys[:-1]) if rng.random() < 0.8 else keys[-1]
    v = d[k]
    if shape == "overwrite":
        nv = rng.choice([x for x in range(1, 13) if x not in d.values()])
        code = f"{_assign(var, d)}\n{var}[{_lit(k)}] = {nv}\nprint({var})"
        new_val = nv
        why = (
            f"{k!r} is already a key, so the assignment REPLACES its value: {k!r} keeps its "
            f"place but now maps to {nv}. A dictionary never holds the same key twice."
        )
        extra = [_pairs_repr((x, v + nv if x == k else y) for x, y in items)]
    else:
        nv = rng.choice([x for x in range(2, 6) if x != v])
        new_val = v + nv
        code = f"{_assign(var, d)}\n{var}[{_lit(k)}] += {nv}\nprint({var})"
        why = (
            f"`{var}[{_lit(k)}] += {nv}` reads the current value {v}, adds {nv}, and stores "
            f"{v + nv} back under the same key, in the same position."
        )
        extra = [_pairs_repr((x, nv if x == k else y) for x, y in items)]
    moved = _pairs_repr([p for p in items if p[0] != k] + [(k, new_val)])
    dup = _pairs_repr(items + [(k, nv)])
    distractors = [moved, dup] if rng.random() < 0.5 else [dup, moved]
    distractors += extra + [repr(d), _pairs_repr(items + [(k, new_val)])]
    if shape == "increment":
        distractors = extra + distractors
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_len(rng: random.Random) -> Question:
    """``len`` counts key-value pairs (not items inside values, not keys + values)."""
    shape = rng.choice(["list_values", "str_values", "build"])
    if shape == "list_values":
        k = rng.choice([2, 3])
        teams = rng.sample(_COLORS, k)
        sizes = [rng.randint(1, 3) for _ in teams]
        if sum(sizes) == k:
            sizes[0] = 2
        names = rng.sample(NAMES, sum(sizes))
        d, i = {}, 0
        for team, size in zip(teams, sizes):
            d[team] = names[i : i + size]
            i += size
        total = sum(sizes)
        code = f"{_assign('teams', d)}\nprint(len(teams))"
        distractors = [total, k + total, 2 * k, total + 1, k + 1]
        why = (
            f"`len` of a dictionary counts its key-value pairs. `teams` has {k} keys, so "
            f"the answer is {k}, no matter how many names are inside the lists."
        )
    elif shape == "str_values":
        var, d, _, _, _ = _str_dict(rng, 3)
        key = rng.choice(list(d))
        val = d[key]
        code = f"{_assign(var, d)}\nprint(len({var}), len({var}[{_lit(key)}]))"
        distractors = [
            f"6 {len(val)}",
            f"3 {len(key)}",
            "3 1",
            f"{len(val)} 3",
            f"6 {len(key)}",
            f"2 {len(val)}",
            f"3 {len(val) + 2}",
        ]
        why = (
            f"`len({var})` counts the 3 key-value pairs. `{var}[{_lit(key)}]` is the "
            f"string {val!r}, and `len` of a string counts its {len(val)} characters."
        )
    else:
        var = rng.choice(["inventory", "cart", "bag"])
        items = rng.sample(_ITEMS, 4)
        start = {x: rng.randint(1, 5) for x in items[: rng.choice([0, 1, 2])]}
        new_keys = [x for x in items if x not in start][:2]
        # Three assignments: two new keys, plus one key assigned a second time.
        repeated = rng.choice(list(start) + new_keys)
        order = new_keys + [repeated]
        rng.shuffle(order)
        values = rng.sample(range(1, 10), 3)
        lines = [_assign(var, start)]
        lines += [f"{var}[{_lit(t)}] = {val}" for t, val in zip(order, values)]
        lines.append(f"print(len({var}))")
        code = "\n".join(lines)
        final = len(start) + 2
        distractors = [final + 1, final - 1, final + 2, sum(values)]
        why = (
            f"Assigning to a key that already exists ({repeated!r}) replaces its value "
            f"instead of adding a pair, so `{var}` ends up with {final} keys."
        )
    return _output(code, EASY, [str(x) for x in distractors], why, rng)


@generator(TOPIC, EASY)
def gen_in_checks(rng: random.Random) -> Question:
    """``in`` on a dict checks the KEYS only; use ``.values()`` to search values."""
    var, d, spare, _, _ = _any_dict(rng, 3)
    keys = list(d)
    k, k2 = rng.sample(keys, 2)
    v = d[rng.choice([x for x in keys if x != k])]
    pool = [
        (f"{_lit(k)} in {var}", True, False),
        (f"{_lit(v)} in {var}.values()", True, False),
        (f"{_lit(spare)} in {var}", False, False),
        (f"{_lit(k2)} not in {var}", False, False),
        (f"{_lit(k)} in {var}.values()", False, True),
    ]
    must = (f"{_lit(v)} in {var}", False, True)
    extras = rng.sample(pool, rng.choice([1, 1, 2]))
    picks = [must] + extras
    rng.shuffle(picks)
    printer = f"print({', '.join(p[0] for p in picks)})"
    if len(printer) > 79:
        picks = [p for p in picks if p is must or p is extras[0]]
        printer = f"print({', '.join(p[0] for p in picks)})"
    code = f"{_assign(var, d)}\n{printer}"
    correct = [p[1] for p in picks]
    # Misconception: `in` also looks at the values (and `.values()` at the keys).
    wrong = [(not p[1]) if p[2] else p[1] for p in picks]
    why = (
        f"`in` on a dictionary only checks its KEYS. {v!r} is a value, not a key, so "
        f"`{_lit(v)} in {var}` is False; `{var}.values()` is what you search for values."
    )
    return _output(code, EASY, _bool_distractors(correct, wrong, rng), why, rng)


@generator(TOPIC, EASY)
def gen_iterate(rng: random.Random) -> Question:
    """Looping over a dict gives keys; ``values()`` gives values; ``items()`` gives pairs."""
    var, d, _, key_name, val_name = _any_dict(rng, 3)
    form = rng.choice(["keys", "keys_method", "values", "items_pair", "items_tuple"])
    if form == "keys":
        loop = f"for x in {var}:\n    print(x)"
    elif form == "keys_method":
        loop = f"for x in {var}.keys():\n    print(x)"
    elif form == "values":
        loop = f"for x in {var}.values():\n    print(x)"
    elif form == "items_pair":
        loop = f"for {key_name}, {val_name} in {var}.items():\n    print({key_name}, {val_name})"
    else:
        loop = f"for pair in {var}.items():\n    print(pair)"
    code = f"{_assign(var, d)}\n{loop}"
    as_keys = _lines(d)
    as_values = _lines(d.values())
    as_pairs = _lines(f"{k} {v}" for k, v in d.items())
    as_tuples = _lines(repr(p) for p in d.items())
    distractors = [as_keys, as_values, as_pairs, as_tuples, _lines(sorted(d)), repr(d)]
    if form.startswith("keys"):
        rng.shuffle(distractors)
    why = {
        "keys": "Looping directly over a dictionary gives its KEYS, in insertion order.",
        "keys_method": "`.keys()` gives the keys, in the order they were inserted.",
        "values": "`.values()` gives just the values, in insertion order.",
        "items_pair": (
            "`.items()` gives (key, value) pairs; unpacking them into two loop variables "
            "and printing both puts a space between key and value."
        ),
        "items_tuple": (
            "`.items()` gives (key, value) TUPLES. With a single loop variable each pair "
            "stays a tuple, so it prints with parentheses and quotes."
        ),
    }[form]
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_which_expression(rng: random.Random) -> Question:
    """Pick the expression that produces a given value (lookup / get / in)."""
    shape = rng.choice(["value", "value", "true", "none"])
    if shape == "value":
        var, d, spare, _, _ = _any_dict(rng, 3)
        keys = list(d)
        i = rng.randrange(3)
        k = keys[i]
        v = d[k]
        other = rng.choice([x for x in keys if x != k])
        correct = f"{var}[{_lit(k)}]" if rng.random() < 0.7 else f"{var}.get({_lit(k)})"
        wrong = [
            f"{var}[{_lit(v)}]",
            f"{var}[{i}]",
            f"{var}.get({_lit(v)})",
            f"{var}[{_lit(other)}]",
            f"{var}[{k}]",
            f"{_lit(k)} in {var}",
        ]
        rng.shuffle(wrong)
        target = v
        why = (
            f"You look a value up by its KEY: {k!r} is the key paired with {v!r}. "
            f"Dictionaries can't be indexed by position or searched by value."
        )
    elif shape == "true":
        var, d, spare, _, _ = _str_dict(rng, 3)
        k, k2 = rng.sample(list(d), 2)
        v = d[k2]
        if rng.random() < 0.5:
            correct = f"{_lit(k)} in {var}"
        else:
            correct = f"{_lit(v)} in {var}.values()"
        wrong = [
            f"{_lit(v)} in {var}",
            f"{_lit(k)} in {var}.values()",
            f"{_lit(spare)} in {var}",
            f"{_lit(k.lower())} in {var}",
            f"{var}[{_lit(k)}] == {_lit(k)}",
        ]
        rng.shuffle(wrong)
        target = True
        why = (
            f"`in` on a dict checks keys and `in ... .values()` checks values. {k!r} is a "
            f"key and {v!r} is a value, so only `{correct}` is True."
        )
    else:
        var, d, spare, _, _ = _int_dict(rng, 3)
        k = rng.choice(list(d))
        correct = f"{var}.get({_lit(spare)})"
        wrong = [
            f"{var}[{_lit(spare)}]",
            f"{var}.get({_lit(spare)}, 0)",
            f"{var}.get({_lit(k)})",
            f"{_lit(spare)} in {var}",
        ]
        rng.shuffle(wrong)
        target = None
        why = (
            f"{spare!r} is not a key: `get` with no default returns None, while square "
            f"brackets raise a KeyError and `in` gives False (not None)."
        )
    return which_expression_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Which expression evaluates to `{target!r}`?",
        setup=_assign(var, d),
        target=target,
        correct_expr=correct,
        wrong_exprs=wrong,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# MEDIUM
# ==========================================================================

_COUNT_WORDS = [
    "banana",
    "cocoa",
    "pepper",
    "letter",
    "coffee",
    "bubble",
    "cookie",
    "llama",
    "hello",
    "tomato",
    "papaya",
    "kitten",
    "puppy",
    "mammal",
    "teepee",
    "tattoo",
    "baobab",
    "seesaw",
    "goggle",
    "access",
    "toffee",
    "rococo",
    "lolly",
]


def _count_seq(rng: random.Random):
    """A word (count its letters) or a list of colors (count the votes)."""
    if rng.random() < 0.5:
        word = rng.choice(_COUNT_WORDS)
        return f'word = "{word}"', "word", "ch", list(word)
    colors = rng.sample(_COLORS, rng.choice([2, 3]))
    while True:
        seq = [rng.choice(colors) for _ in range(rng.choice([5, 6]))]
        if len(set(seq)) == len(colors) and len(set(seq)) < len(seq):
            break
    return f"votes = {_lit(seq)}", "votes", "v", seq


def _tally(seq) -> dict:
    out: dict = {}
    for x in seq:
        out[x] = out.get(x, 0) + 1
    return out


@generator(TOPIC, MEDIUM)
def gen_counting(rng: random.Random) -> Question:
    """The counting pattern ``counts[x] = counts.get(x, 0) + 1`` (or its if/else form)."""
    setup, seq_name, loop_var, seq = _count_seq(rng)
    counts_name = rng.choice(["counts", "tally", "freq"])
    if rng.random() < 0.6:
        body = f"    {counts_name}[{loop_var}] = {counts_name}.get({loop_var}, 0) + 1"
        how = f"`{counts_name}.get({loop_var}, 0)` is 0 the first time an item is seen"
    else:
        body = (
            f"    if {loop_var} in {counts_name}:\n"
            f"        {counts_name}[{loop_var}] += 1\n"
            f"    else:\n"
            f"        {counts_name}[{loop_var}] = 1"
        )
        how = "the first time an item is seen it is set to 1"
    counts = _tally(seq)
    nd = len(counts)
    repeated = [k for k, c in counts.items() if c > 1]
    target = rng.choice(repeated)
    c = counts[target]
    out = rng.choice(["dict", "dict", "key", "len"])
    if out == "dict":
        printer = f"print({counts_name})"
        distractors = [
            repr({k: 1 for k in counts}),
            repr(_tally(seq[:-1])),
            repr({k: v + 1 for k, v in counts.items()}),
            repr(dict(sorted(counts.items()))),
        ]
        rng.shuffle(distractors)
        distractors.append(repr({k: v - 1 for k, v in counts.items()}))
        why = (
            f"{how.capitalize()}, and every later time it goes up by 1, so each item ends "
            f"with how often it appears. Keys appear in the order first seen, e.g. "
            f"{target!r} appears {c} times."
        )
    elif out == "key":
        printer = f"print({counts_name}[{_lit(target)}])"
        distractors = [str(c - 1), str(c + 1), "1", str(len(seq))]
        why = (
            f"{how.capitalize()}; each later time it goes up by 1. {target!r} appears "
            f"{c} times, so its count is {c}."
        )
    else:
        printer = f"print(len({counts_name}), {counts_name}[{_lit(target)}])"
        distractors = [
            f"{len(seq)} {c}",
            f"{nd} {c - 1}",
            f"{len(seq)} {c - 1}",
            f"{nd} 1",
            f"{nd} {c + 1}",
        ]
        why = (
            f"`len` counts the {nd} distinct keys, not the {len(seq)} items looped over. "
            f"{target!r} appears {c} times, so its count is {c}."
        )
    code = f"{setup}\n{counts_name} = {{}}\nfor {loop_var} in {seq_name}:\n{body}\n{printer}"
    return _output(code, MEDIUM, distractors, why, rng)


def _compare(x: int, op: str, t: int) -> bool:
    return {">": x > t, ">=": x >= t, "<": x < t, "<=": x <= t}[op]


_FLIP = {">": ">=", ">=": ">", "<": "<=", "<=": "<"}


@generator(TOPIC, MEDIUM)
def gen_items_loop(rng: random.Random) -> Question:
    """Trace a loop over ``.items()`` that filters, counts or finds the best key."""
    var, d, _, key_name, val_name = _int_dict(rng, 4)
    head = f"{_assign(var, d)}\n"
    loop = f"for {key_name}, {val_name} in {var}.items():\n"
    shape = rng.choice(["sum", "keys", "count", "best"])
    if shape == "best":
        biggest = rng.random() < 0.6
        best = max(d, key=d.get) if biggest else min(d, key=d.get)
        sign, start, word = (">", 0, "largest") if biggest else ("<", 100, "smallest")
        rec = "high" if biggest else "low"
        code = (
            head
            + f'best = ""\n{rec} = {start}\n'
            + loop
            + f"    if {val_name} {sign} {rec}:\n"
            + f"        {rec} = {val_name}\n"
            + f"        best = {key_name}\n"
        )
        keys = list(d)
        ranked = sorted(d, key=d.get, reverse=biggest)
        distractors = [
            str(d[best]),
            repr(keys[-1]),
            repr(ranked[1]),
            repr(ranked[-1]),
            repr(keys[0]),
            repr(max(d)),
            repr(ranked[2]),
        ]
        why = (
            f"`best` is only updated when a value beats the {word} seen so far, so it ends "
            f"as the key with the {word} value: {best!r} ({d[best]})."
        )
        return _value_question(code.rstrip("\n"), "best", MEDIUM, distractors, why, rng)

    vals = sorted(d.values())
    op = rng.choice([">", ">=", "<", "<="])
    t = rng.choice(vals[1:3])
    if rng.random() < 0.3 and vals[2] - vals[1] > 1:
        t = rng.randint(vals[1] + 1, vals[2] - 1)
    match = [k for k, v in d.items() if _compare(v, op, t)]
    flip = [k for k, v in d.items() if _compare(v, _FLIP[op], t)]
    rest = [k for k in d if k not in match]
    cond = f"    if {val_name} {op} {t}:\n"
    boundary = (
        f" ({t} itself {'counts' if _compare(t, op, t) else 'does not count'} because of `{op}`)"
        if t in d.values()
        else ""
    )
    if shape == "sum":
        code = head + "total = 0\n" + loop + cond + f"        total += {val_name}"
        s = sum(d[k] for k in match)
        distractors = [
            sum(d[k] for k in flip),
            sum(d.values()),
            sum(d[k] for k in rest),
            len(match),
            *int_distractors(s, rng),
        ]
        why = (
            f"Only the values {op} {t} are added{boundary}: "
            f"{' + '.join(str(d[k]) for k in match)} = {s}."
        )
        return _value_question(code, "total", MEDIUM, [str(x) for x in distractors], why, rng)
    if shape == "count":
        code = head + "count = 0\n" + loop + cond + "        count += 1"
        distractors = [
            len(flip),
            sum(d[k] for k in match),
            len(rest),
            len(match) + 1,
            len(d),
            len(match) - 1,
        ]
        why = (
            f"`count` goes up once for each value {op} {t}{boundary}: "
            f"{', '.join(str(d[k]) for k in match)}, so it ends at {len(match)}."
        )
        return _value_question(code, "count", MEDIUM, [str(x) for x in distractors], why, rng)
    code = head + "picked = []\n" + loop + cond + f"        picked.append({key_name})"
    distractors = [
        repr([d[k] for k in match]),
        repr(flip),
        repr(rest),
        repr(list(d)),
        repr(sorted(match)),
    ]
    why = (
        f"`.items()` gives each key with its value, in insertion order. The KEYS whose "
        f"value is {op} {t}{boundary} are appended: {match}."
    )
    return _value_question(code, "picked", MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_pop(rng: random.Random) -> Question:
    """``pop`` returns the value and removes the key; defaults; ``del``; ``popitem``."""
    shape = rng.choice(
        ["pop", "pop", "default_missing", "missing", "default_existing", "del", "popitem"]
    )
    var, d, spare, _, _ = (_any_dict if shape in ("pop", "popitem") else _int_dict)(rng, 3)
    keys = list(d)
    k = rng.choice(keys)
    v = d[k]
    rest = repr({x: y for x, y in d.items() if x != k})
    full = repr(d)
    res = rng.choice(["n", "removed", "x"])
    head = _assign(var, d)
    if shape == "pop":
        code = f"{head}\n{res} = {var}.pop({_lit(k)})\nprint({res}, {var})"
        distractors = [f"{k} {rest}", f"{v} {full}", f"{(k, v)!r} {rest}", f"None {rest}"]
        why = (
            f"`pop` removes the key {k!r} from the dictionary AND returns its value, "
            f"so `{res}` is {v!r} and only the other pairs are left."
        )
    elif shape == "default_missing":
        code = f"{head}\n{res} = {var}.pop({_lit(spare)}, 0)\nprint({res}, {var})"
        distractors = [
            KEY_ERROR,
            f"None {full}",
            f"0 { {**d, spare: 0}!r}",
            f"{spare} {full}",
        ]
        why = (
            f"{spare!r} is not a key, so `pop` returns the default 0 instead of raising a "
            f"KeyError. Nothing is removed (or added), so `{var}` is unchanged."
        )
    elif shape == "missing":
        code = f"{head}\n{res} = {var}.pop({_lit(spare)})\nprint({res}, {var})"
        distractors = [f"None {full}", f"0 {full}", INDEX_ERROR, f"{spare} {full}"]
        why = (
            f"{spare!r} is not a key and no default was given, so `pop` raises a KeyError "
            f"(unlike `get`, which would return None)."
        )
    elif shape == "default_existing":
        code = f"{head}\n{res} = {var}.pop({_lit(k)}, 0)\nprint({res}, {var})"
        distractors = [f"0 {rest}", f"0 {full}", f"{v} {full}", KEY_ERROR]
        why = (
            f"The default is only used for a missing key. {k!r} exists, so `pop` removes "
            f"it and returns its value, {v}."
        )
    elif shape == "del":
        code = f"{head}\ndel {var}[{_lit(k)}]\nprint({var}.get({_lit(k)}), len({var}))"
        distractors = [f"{v} 3", KEY_ERROR, "None 3", f"{v} 2"]
        why = (
            f"`del` removes the key {k!r} completely, leaving 2 pairs. Asking `get` for a "
            f"missing key returns None rather than raising a KeyError."
        )
    else:
        last = (keys[-1], d[keys[-1]])
        first = (keys[0], d[keys[0]])
        code = f"{head}\nlast = {var}.popitem()\nprint(last, len({var}))"
        distractors = [
            f"{first!r} 2",
            f"{last[1]!r} 2",
            f"{last!r} 3",
            f"{last[0]!r} 2",
            f"{first!r} 3",
        ]
        why = (
            f"`popitem()` removes and returns the most recently inserted pair as a "
            f"(key, value) tuple, here {last!r}, leaving 2 pairs."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_update(rng: random.Random) -> Question:
    """``a.update(b)``: b's values win, existing keys keep their place, returns None."""
    a_name, b_name = rng.choice(
        [("settings", "changes"), ("defaults", "custom"), ("base", "extra"), ("old", "new")]
    )
    keys = rng.sample(_SETTINGS, 5)
    na = rng.choice([2, 3])
    a = {k: rng.randint(1, 9) for k in keys[:na]}
    overlap = rng.choice(keys[: na - 1]) if rng.random() < 0.8 else keys[na - 1]
    b = {
        overlap: rng.choice([x for x in range(1, 10) if x != a[overlap]]),
        keys[na]: rng.randint(1, 9),
    }
    if rng.random() < 0.5:
        b = dict(reversed(list(b.items())))
    shape = rng.choice(["target", "target", "reverse", "result", "lens"])
    if shape == "reverse":
        target, source, t_name, s_name = b, a, b_name, a_name
    else:
        target, source, t_name, s_name = a, b, a_name, b_name
    merged = {**target, **source}
    t_items, s_items = list(target.items()), list(source.items())
    keep_old = {**{k: v for k, v in source.items()}, **target}
    keep_old = {k: keep_old[k] for k in merged}
    moved = _pairs_repr([p for p in t_items if p[0] not in source] + s_items)
    head = f"{_assign(a_name, a)}\n{_assign(b_name, b)}\n"
    if shape == "result":
        code = head + f"result = {a_name}.update({b_name})\nprint(result)"
        distractors = [repr(merged), repr(b), repr(a), repr(keep_old)]
        why = (
            f"`update` changes `{a_name}` in place and returns None, so `result` is None. "
            f"(Afterwards `{a_name}` itself would be {merged!r}.)"
        )
    elif shape == "lens":
        code = head + f"{a_name}.update({b_name})\nprint(len({a_name}), len({b_name}))"
        distractors = [
            f"{len(a) + len(b)} {len(b)}",
            f"{len(merged)} 0",
            f"{len(a)} {len(b)}",
            f"{len(merged)} {len(merged)}",
        ]
        why = (
            f"`update` copies `{b_name}`'s pairs into `{a_name}`: {overlap!r} is overwritten "
            f"and only one new key is added, so `{a_name}` has {len(merged)} keys. "
            f"`{b_name}` itself is not changed."
        )
    else:
        code = head + f"{t_name}.update({s_name})\nprint({t_name})"
        distractors = [
            repr(keep_old),
            moved,
            _pairs_repr(t_items + s_items),
            repr(target),
            _pairs_repr(
                (k, v + source[k] if k in source and k in target else v) for k, v in merged.items()
            ),
        ]
        why = (
            f"`{t_name}.update({s_name})` copies every pair from `{s_name}` into "
            f"`{t_name}`. The shared key {overlap!r} keeps its position but takes "
            f"`{s_name}`'s value ({source[overlap]}); new keys go on the end."
        )
    return _output(code, MEDIUM, distractors, why, rng)


_PETS = ["cat", "dog", "fish", "owl", "frog", "duck"]


@generator(TOPIC, MEDIUM)
def gen_nested(rng: random.Random) -> Question:
    """Dicts of dicts and dicts of lists: chained lookups, order of keys, shared inner objects."""
    shape = rng.choice(["dd_lookup", "dd_order", "dd_alias", "dl_index", "dl_range", "dl_append"])
    if shape.startswith("dd"):
        var = rng.choice(["students", "kids", "members"])
        people = rng.sample(NAMES, 2)
        ages = rng.sample(range(9, 16), 2)
        pets = rng.sample(_PETS, 2)
        d = {p: {"age": a, "pet": pet} for p, a, pet in zip(people, ages, pets)}
        who = rng.randrange(2)
        name, other = people[who], people[1 - who]
        head = _assign(var, d)
        if shape == "dd_lookup":
            field, other_field = rng.choice([("age", "pet"), ("pet", "age")])
            code = f"{head}\nprint({var}[{_lit(name)}][{_lit(field)}])"
            distractors = [d[other][field], d[name][other_field], KEY_ERROR, repr(d[name])]
            why = (
                f"Read it left to right: `{var}[{_lit(name)}]` is the inner dict "
                f"{d[name]!r}, and `[{_lit(field)}]` then looks up {d[name][field]!r} in it."
            )
        elif shape == "dd_order":
            code = f'{head}\nprint({var}["pet"][{_lit(name)}])'
            distractors = [d[name]["pet"], "None", d[other]["pet"], TYPE_ERROR]
            why = (
                f'The outer keys are names, so `{var}["pet"]` fails first: "pet" is a key '
                f"of the INNER dicts only. The lookups must go in order: "
                f'`{var}[{_lit(name)}]["pet"]`.'
            )
        else:
            alias = name.lower()
            n = rng.randint(1, 3)
            code = (
                f'{head}\n{alias} = {var}[{_lit(name)}]\n{alias}["age"] += {n}\n'
                f'print({var}[{_lit(name)}]["age"])'
            )
            age = d[name]["age"]
            distractors = [age, KEY_ERROR, age + 2 * n, n]
            why = (
                f"`{alias}` is not a copy: it names the SAME inner dict that is stored in "
                f"`{var}`, so adding {n} through `{alias}` changes {age} to {age + n} there too."
            )
        return _output(
            code,
            MEDIUM,
            [str(x) for x in distractors],
            why,
            rng,
            prompt=PRINT_OR_ERROR,
            allow_error=True,
        )
    k = rng.choice([2, 3]) if shape != "dl_append" else 2
    teams = rng.sample(_COLORS, k)
    sizes = [rng.randint(2, 3) for _ in teams]
    names = rng.sample(NAMES, sum(sizes))
    d, i = {}, 0
    for team, size in zip(teams, sizes):
        d[team] = names[i : i + size]
        i += size
    team = rng.choice(teams)
    other = rng.choice([x for x in teams if x != team])
    members = d[team]
    head = _assign("teams", d)
    if shape == "dl_index":
        idx = rng.randrange(len(members))
        code = f"{head}\nprint(teams[{_lit(team)}][{idx}])"
        distractors = [
            members[idx - 1] if idx else members[1],
            d[other][idx % len(d[other])],
            KEY_ERROR,
            members[(idx + 1) % len(members)],
            repr(members),
        ]
        why = (
            f"`teams[{_lit(team)}]` is the list {members!r}; then `[{idx}]` is a normal "
            f"list index (starting at 0), giving {members[idx]!r}."
        )
    elif shape == "dl_range":
        idx = len(members)
        code = f"{head}\nprint(teams[{_lit(team)}][{idx}])"
        distractors = [
            members[-1],
            KEY_ERROR,
            "None",
            d[other][0] if len(d[other]) > idx else d[other][-1],
        ]
        why = (
            f"`teams[{_lit(team)}]` is the list {members!r}, which has {len(members)} "
            f"items with indexes 0 to {len(members) - 1}, so index {idx} raises an IndexError."
        )
    else:
        new = rng.choice([x for x in NAMES if x not in names])
        code = (
            f"{head}\nteams[{_lit(team)}].append({_lit(new)})\n"
            f"print(len(teams), len(teams[{_lit(team)}]))"
        )
        m = len(members)
        total = sum(sizes) + 1
        distractors = [f"3 {m + 1}", f"2 {m}", f"{total} {m + 1}", f"3 {m}", f"{total} {m}"]
        why = (
            f"`append` changes the list stored under {team!r}, so it now has {m + 1} names, "
            f"but `teams` still has just 2 keys."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_fill_blank(rng: random.Random) -> Question:
    """Pick the code that completes a dict snippet (counting, views, get/pop/setdefault, keys)."""
    shape = rng.choice(["count_call", "count_default", "view", "methods", "key"])
    if shape in ("count_call", "count_default"):
        setup, seq_name, loop_var, _ = _count_seq(rng)
        c = rng.choice(["counts", "tally"])
        if shape == "count_call":
            line = f"    {c}[{loop_var}] = {BLANK} + 1"
            correct = f"{c}.get({loop_var}, 0)"
            cands = [
                f"{c}.get({loop_var})",
                f"{c}[{loop_var}]",
                f"{c}.get({loop_var}, 1)",
                f"{c}.get(0, {loop_var})",
                f"{c}.get({loop_var}, -1)",
            ]
            why = (
                f"`{c}.get({loop_var}, 0)` gives the current count, or 0 for an item not seen "
                f"yet. `{c}[{loop_var}]` would raise a KeyError on the first item and "
                f"`.get({loop_var})` would give None, and None + 1 is a TypeError."
            )
        else:
            line = f"    {c}[{loop_var}] = {c}.get({loop_var}, {BLANK}) + 1"
            correct = "0"
            cands = ["1", "None", "-1", loop_var, "False"]
            why = (
                "The default is what `get` returns for an item not counted yet. Starting "
                "from 0, the first sighting stores 0 + 1 = 1; a default of 1 would make "
                "every count one too high."
            )
        template = f"{setup}\n{c} = {{}}\nfor {loop_var} in {seq_name}:\n{line}\nprint({c})"
    elif shape == "view":
        var, d, _, _, _ = _any_dict(rng, rng.choice([2, 3]))
        correct = rng.choice(["keys", "values", "items"])
        cands = ["keys", "values", "items", "copy", "popitem"]
        template = f"{_assign(var, d)}\nprint(list({var}.{BLANK}()))"
        why = (
            "`keys()` gives the keys, `values()` the values and `items()` (key, value) "
            f"tuples, so `{correct}` is the one that produces this list."
        )
    elif shape == "methods":
        var, d, spare, _, _ = _int_dict(rng, 2)
        k = rng.choice(list(d))
        correct = rng.choice(["get", "pop", "setdefault"])
        cands = ["get", "pop", "setdefault", "update", "items"]
        template = (
            f"{_assign(var, d)}\n"
            f"a = {var}.{BLANK}({_lit(k)}, 0)\n"
            f"b = {var}.{BLANK}({_lit(spare)}, 0)\n"
            f"print(a, b, {var})"
        )
        why = {
            "get": (
                "`get` only reads: it returns the value (or the default) and never "
                "changes the dict."
            ),
            "pop": (
                f"`pop` returns the value AND removes the key, so {k!r} disappears; for a "
                f"missing key it returns the default."
            ),
            "setdefault": (
                f"`setdefault` returns an existing value unchanged, but a missing key "
                f"({spare!r}) is INSERTED with the default."
            ),
        }[correct]
    else:
        var, d, spare, _, _ = _int_dict(rng, rng.choice([2, 3]))
        keys = list(d)
        i = rng.randrange(len(keys))
        k = keys[i]
        nv = rng.choice([x for x in range(1, 20) if x not in d.values()])
        correct = _lit(k)
        cands = [k, str(i), str(d[k]), "-1", _lit(spare)]
        template = f"{_assign(var, d)}\n{var}[{BLANK}] = {nv}\nprint({var})"
        why = (
            f"To change a value you assign to its KEY, the string {k!r}. A number in the "
            f"brackets is not a position: it would add a brand-new key instead."
        )
    target = _run(template.replace(BLANK, correct))
    if target.startswith("Error:") or "\n" in target:
        raise GenerationError("blank's correct answer does not print one line")
    wrong = [x for x in cands if x != correct and _run(template.replace(BLANK, x)) != target]
    n_blanks = template.count(BLANK)
    blank_word = "both blanks" if n_blanks > 1 else "the blank"
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which choice fills {blank_word} (`{BLANK}`) so that the code prints `{target}`?",
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
        code=template,
    )


def _builtin_dict(rng: random.Random):
    """A str -> int dict whose key order, sorted order and value order all differ."""
    for _ in range(100):
        var, d, _, _, _ = _int_dict(rng, rng.choice([3, 4]))
        keys = list(d)
        best, worst = max(d, key=d.get), min(d, key=d.get)
        if (
            keys != sorted(keys)
            and best != max(keys)
            and worst != min(keys)
            and sorted(keys) != sorted(d, key=d.get)
        ):
            return var, d
    raise GenerationError("no suitable dict")


@generator(TOPIC, MEDIUM)
def gen_dict_builtins(rng: random.Random) -> Question:
    """``max``/``min``/``sorted``/``list``/``sum`` on a dict work on its KEYS."""
    var, d = _builtin_dict(rng)
    keys = list(d)
    shape = rng.choice(["max", "min", "sorted", "list", "max_key", "sum"])
    best, worst = max(d, key=d.get), min(d, key=d.get)
    if shape in ("max", "min"):
        fn = max if shape == "max" else min
        k = fn(keys)
        by_val = best if shape == "max" else worst
        code = f"{_assign(var, d)}\nprint({shape}({var}))"
        distractors = [
            str(fn(d.values())),
            by_val,
            f"{(by_val, d[by_val])!r}",
            (min if shape == "max" else max)(keys),
            f"{(k, d[k])!r}",
        ]
        edge, size = ("last", "biggest") if shape == "max" else ("first", "smallest")
        why = (
            f"Looping over a dict gives its KEYS, so `{shape}({var})` compares the keys as "
            f"strings and returns the alphabetically {edge} one, {k!r}, not the key with "
            f"the {size} value."
        )
    elif shape == "sorted":
        code = f"{_assign(var, d)}\nprint(sorted({var}))"
        distractors = [
            repr(sorted(d.values())),
            repr(sorted(d, key=d.get)),
            repr(keys),
            repr(sorted(d.items())),
            repr(sorted(keys, reverse=True)),
        ]
        why = (
            f"`sorted({var})` sorts the KEYS (alphabetically, since they are strings) and "
            f"returns them as a new list; the values are not involved."
        )
    elif shape == "list":
        code = f"{_assign(var, d)}\nprint(list({var}))"
        distractors = [
            repr(sorted(keys)),
            repr(list(d.values())),
            repr(list(d.items())),
            repr(d),
        ]
        why = f"`list({var})` makes a list of the dict's KEYS, in insertion order."
    elif shape == "max_key":
        code = f"{_assign(var, d)}\nprint(max({var}, key={var}.get))"
        distractors = [max(keys), str(d[best]), worst, f"{(best, d[best])!r}"]
        why = (
            f"`max` still returns a KEY, but `key={var}.get` makes it compare the keys by "
            f"their values, so the result is the key with the largest value: {best!r} ({d[best]})."
        )
    else:
        code = f"{_assign(var, d)}\nprint(sum({var}))"
        distractors = [str(sum(d.values())), KEY_ERROR, "0", str(len(d))]
        why = (
            f"`sum({var})` loops over the dict, which gives its KEYS. They are strings, and "
            f"adding strings to 0 raises a TypeError; `sum({var}.values())` would give "
            f"{sum(d.values())}."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_equality(rng: random.Random) -> Question:
    """Dict ``==`` compares pairs and ignores order; lists of keys/values do not."""
    a_name, b_name = rng.choice(
        [("a", "b"), ("mine", "yours"), ("cart1", "cart2"), ("before", "after")]
    )
    _, a, spare, _, _ = _int_dict(rng, 3)
    items = list(a.items())
    shape = rng.choice(["reordered", "reordered", "changed", "reordered_changed", "extra"])
    b_items = items[:]
    if shape != "changed":
        while b_items == items:
            rng.shuffle(b_items)
    if shape in ("changed", "reordered_changed"):
        j = rng.randrange(3)
        k, v = b_items[j]
        b_items[j] = (k, v + rng.choice([1, 2, -1]))
        why = (
            f"Dicts are equal only if every key maps to the same value: {k!r} is {v} in "
            f"`{a_name}` but {b_items[j][1]} in `{b_name}`, so `{a_name} == {b_name}` is False."
        )
    elif shape == "extra":
        b_items.append((spare, rng.randint(1, 9)))
        why = (
            f"`{b_name}` has an extra key, {spare!r}, so the dicts do not hold the same pairs "
            f"and `{a_name} == {b_name}` is False."
        )
    else:
        why = (
            f"Both dicts hold exactly the same key-value pairs. Dict equality ignores the "
            f"order they were written in, so `{a_name} == {b_name}` is True."
        )
    b = dict(b_items)
    pool = {
        f"list({a_name}) == list({b_name})": ("`list(...)` keeps the keys' insertion order"),
        f"sorted({a_name}) == sorted({b_name})": (
            "`sorted(...)` puts the keys in alphabetical order"
        ),
        f"list({a_name}.values()) == list({b_name}.values())": (
            "lists of values are compared in order"
        ),
    }
    head = f"{_assign(a_name, a)}\n{_assign(b_name, b)}\n"
    for n_others in (2, 1):
        others = rng.sample(sorted(pool), n_others)
        exprs = [f"{a_name} == {b_name}"] + others
        rng.shuffle(exprs)
        printer = f"print({', '.join(exprs)})"
        if len(printer) <= 79:
            break
    code = head + printer
    ns = {a_name: a, b_name: b}
    correct = [eval(e, ns) for e in exprs]  # our own, fixed expressions
    # Misconception: dict equality depends on the order the pairs were written in.
    eq_expr = f"{a_name} == {b_name}"
    wrong = [
        (list(a.items()) == list(b.items())) if e == eq_expr else val
        for e, val in zip(exprs, correct)
    ]
    if wrong == correct:
        wrong = [(not val) if e == eq_expr else val for e, val in zip(exprs, correct)]
    detail = "; ".join(pool[e] for e in others)
    why += " " + detail[0].upper() + detail[1:] + "."
    return _output(code, MEDIUM, _bool_distractors(correct, wrong, rng), why, rng)


# ==========================================================================
# HARD
# ==========================================================================

_ONE_FAMILY = [1, 1.0, True]
_ZERO_FAMILY = [0, 0.0, False]
_TYPE_LABELS = {int: "int", float: "float", bool: "bool"}


def _merge(seq, mode: str = "python", same=None) -> list:
    """Simulate inserting ``(key, value)`` pairs under a (mis)understanding of dicts.

    python: an equal key keeps its first spelling and position, value replaced.
    new_key: the latest spelling of the key replaces the old one in place.
    move: the key is removed and re-added at the end.
    first: the first value wins.
    separate: every pair is kept.
    """
    same = same or (lambda a, b: a == b)
    out: list = []
    for k, v in seq:
        idx = next((i for i, (k2, _) in enumerate(out) if same(k2, k)), None)
        if idx is None or mode == "separate":
            out.append([k, v])
        elif mode == "python":
            out[idx][1] = v
        elif mode == "new_key":
            out[idx] = [k, v]
        elif mode == "move":
            out.pop(idx)
            out.append([k, v])
    return out


@generator(TOPIC, HARD)
def gen_number_keys(rng: random.Random) -> Question:
    """``1``, ``1.0`` and ``True`` (or ``0``, ``0.0``, ``False``) are the SAME dict key."""
    family = rng.choice([_ONE_FAMILY, _ZERO_FAMILY])
    chain = " == ".join(repr(x) for x in family)
    shape = rng.choice(["literal", "assign", "count", "lookup"])
    if shape == "lookup":
        base_keys = [True, False] if rng.random() < 0.5 else [1, 0]
        labels = ("yes", "no") if base_keys[0] is True else ("one", "zero")
        d = dict(zip(base_keys, labels))
        hit = base_keys[0] if family is _ONE_FAMILY else base_keys[1]
        old = d[hit]
        k_set, k_get = rng.sample([x for x in family if type(x) is not type(hit)], 2)
        new = (
            rng.choice(["uno", "won", "same"])
            if family is _ONE_FAMILY
            else rng.choice(["none", "nil", "same"])
        )
        var = rng.choice(["answers", "lookup", "table"])
        code = (
            f"{_assign(var, d)}\n{var}[{k_set!r}] = {_lit(new)}\n"
            f"print({var}[{k_get!r}], len({var}))"
        )
        distractors = [f"{old} 3", f"{old} 2", KEY_ERROR, f"{new} 3"]
        why = (
            f"`{chain}` is True and these numbers hash the same, so `{var}[{k_set!r}]` "
            f"overwrites the existing key {hit!r} (still 2 keys), and `{var}[{k_get!r}]` "
            f"finds that same key: {new!r}."
        )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)

    members = rng.sample(family, rng.choice([2, 3, 3]))
    other_key = rng.choice([2, "x"]) if family is _ONE_FAMILY else rng.choice([1, "x"])
    if shape == "count":
        seq = list(family) + [other_key]
        rng.shuffle(seq)
        if rng.random() < 0.5:
            seq.insert(rng.randrange(len(seq) + 1), other_key)
        code = (
            f"counts = {{}}\nfor x in {_lit(seq)}:\n"
            f"    counts[x] = counts.get(x, 0) + 1\nprint(counts)"
        )
        pairs = [(x, 1) for x in seq]

        def tally(mode, same=None):
            same = same or (lambda a, b: a == b)
            out: list = []
            for x in seq:
                idx = next((i for i, (k2, _) in enumerate(out) if same(k2, x)), None)
                if idx is None:
                    out.append([x, 1])
                elif mode == "ignore":
                    continue
                elif mode == "move":
                    out.append([x, out.pop(idx)[1] + 1])
                else:
                    out[idx][1] += 1
                    if mode == "new_key":
                        out[idx][0] = x
            return _pairs_repr(out)

        def strict(a, b) -> bool:
            return type(a) is type(b) and a == b

        def bool_apart(a, b) -> bool:
            return a == b and (type(a) is bool) == (type(b) is bool)

        distractors = [
            tally("python", strict),
            tally("python", bool_apart),
            tally("new_key"),
            tally("move"),
            tally("ignore"),
            _pairs_repr(pairs),
        ]
        first = next(x for x in seq if x in family)
        why = (
            f"`{chain}` is True and these values hash the same, so they all count toward "
            f"ONE key. The key keeps the spelling it was first stored with ({first!r})."
        )
        return _output(code, HARD, distractors, why, rng)

    labels = [_TYPE_LABELS[type(x)] for x in members]
    seq = list(zip(members, labels))
    if rng.random() < 0.6:
        seq.insert(rng.randrange(len(seq) + 1), (other_key, "other"))
    var = rng.choice(["d", "table", "seen"])
    if shape == "literal":
        setup = f"{var} = {{" + ", ".join(f"{_lit(k)}: {_lit(v)}" for k, v in seq) + "}"
    else:
        setup = f"{var} = {{}}\n" + "\n".join(f"{var}[{_lit(k)}] = {_lit(v)}" for k, v in seq)
    with_len = rng.random() < 0.5
    code = setup + (f"\nprint(len({var}), {var})" if with_len else f"\nprint({var})")

    def show(mode):
        m = _merge(seq, mode)
        return (f"{len(m)} " if with_len else "") + _pairs_repr(m)

    distractors = [show("new_key"), show("separate"), show("move"), show("first")]
    first = next(k for k, _ in seq if k in family)
    last_label = [v for k, v in seq if k in family][-1]
    why = (
        f"`{chain}` is True and equal numbers hash the same, so the dict treats them as ONE "
        f"key. A repeated key keeps its first spelling and position ({first!r}) but its "
        f"value is replaced, ending as {last_label!r}."
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_order_trace(rng: random.Random) -> Question:
    """Insertion order through overwrite / del / re-add, and duplicate keys in a literal."""
    var, d, spare, _, _ = _int_dict(rng, 3)
    keys = list(d)
    used = set(d.values())

    def fresh() -> int:
        val = rng.choice([x for x in range(1, 21) if x not in used])
        used.add(val)
        return val

    if rng.random() < 0.35:
        a, b = keys[0], keys[1]
        v1, v2, v3 = d[a], d[b], fresh()
        pairs = [(a, v1), (b, v2), (a, v3)]
        if rng.random() < 0.5:
            pairs.insert(2, (keys[2], d[keys[2]]))
        literal = "{" + ", ".join(f"{_lit(k)}: {_lit(v)}" for k, v in pairs) + "}"
        bump = rng.randint(1, 3)
        code = (
            f"{var} = {literal}\n{var}[{_lit(b)}] += {bump}\n"
            f"{var}[{_lit(spare)}] = {var}[{_lit(a)}] + {var}[{_lit(b)}]\nprint({var})"
        )

        def finish(merged):
            m = [list(p) for p in merged]
            vals = {k: v for k, v in m}
            for p in m:
                if p[0] == b:
                    p[1] += bump
            vals = {k: v for k, v in m}
            return _pairs_repr(m + [[spare, vals[a] + vals[b]]])

        raw = [list(p) for p in pairs]
        for p in raw:
            if p[0] == b:
                p[1] += bump
        distractors = [
            finish(_merge(pairs, "first")),
            finish(_merge(pairs, "move")),
            _pairs_repr(raw + [[spare, v3 + v2 + bump]]),
            _pairs_repr([[b, v2 + bump], [a, v1]] + [[spare, v1 + v2 + bump]]),
        ]
        why = (
            f"When a dict literal repeats a key, the LAST value wins ({a!r} is {v3}) but the "
            f"key keeps its FIRST position. So {spare!r} gets {v3} + {v2 + bump} = "
            f"{v3 + v2 + bump} and is added at the end."
        )
        return _output(code, HARD, distractors, why, rng)

    ow = rng.choice(keys[:2])
    dk = keys[1] if ow == keys[0] else keys[0]
    ops = [("del", dk, None), ("set", dk, fresh())]
    ops.insert(rng.randint(0, 2), ("set", ow, fresh()))
    if rng.random() < 0.5:
        ops.insert(rng.randint(0, len(ops)), ("set", spare, fresh()))
    lines = [_assign(var, d)]
    for op, k, v in ops:
        if op == "set":
            lines.append(f"{var}[{_lit(k)}] = {v}")
        elif rng.random() < 0.6:
            lines.append(f"del {var}[{_lit(k)}]")
        else:
            lines.append(f"{var}.pop({_lit(k)})")
    lines.append(f"print({var})")
    code = "\n".join(lines)

    def simulate(move_on_set: bool) -> list:
        out = [[k, v] for k, v in d.items()]
        for op, k, v in ops:
            idx = next((i for i, p in enumerate(out) if p[0] == k), None)
            if op == "del":
                out.pop(idx)
            elif idx is None:
                out.append([k, v])
            elif move_on_set:
                out.pop(idx)
                out.append([k, v])
            else:
                out[idx][1] = v
        return out

    real = simulate(False)
    rank = {k: i for i, k in enumerate(keys + [spare])}
    restored = sorted(real, key=lambda p: rank[p[0]])
    no_overwrite = [[k, d[k] if k == ow else v] for k, v in real]
    distractors = [
        _pairs_repr(simulate(True)),
        _pairs_repr(restored),
        _pairs_repr(sorted(real)),
        _pairs_repr(no_overwrite),
    ]
    why = (
        f"Assigning to an existing key ({ow!r}) changes its value but keeps its position. "
        f"Deleting {dk!r} removes it completely, so assigning it again adds it as a NEW key "
        f"at the end."
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_hashable_keys(rng: random.Random) -> Question:
    """Keys must be hashable: tuples work, lists (or tuples holding lists) raise TypeError."""
    shape = rng.choice(
        ["list_key", "list_key", "tuple_key", "tuple_key", "nested", "list_value", "snapshot"]
    )
    places = rng.sample(["tree", "rock", "pond", "cave", "hut", "gold"], 3)
    x, y = rng.sample(range(10), 2)
    x2, y2 = rng.sample([n for n in range(10) if n not in (x, y)], 2)
    if shape == "list_key":
        code = (
            f"grid = {{}}\nspot = [{x}, {y}]\ngrid[spot] = {_lit(places[0])}\n"
            f"spot.append({x2})\nprint(grid)"
        )
        distractors = [
            f"{{[{x}, {y}, {x2}]: {places[0]!r}}}",
            f"{{[{x}, {y}]: {places[0]!r}}}",
            f"{{({x}, {y}): {places[0]!r}}}",
            KEY_ERROR,
        ]
        why = (
            "Dict keys must be hashable (unchangeable). A list can change, so using "
            "`spot` as a key raises a TypeError right away; a tuple would work."
        )
    elif shape == "tuple_key":
        code = (
            f"grid = {{}}\ngrid[({x}, {y})] = {_lit(places[0])}\n"
            f"grid[({x2}, {y2})] = {_lit(places[1])}\n"
            f"grid[({x}, {y})] = {_lit(places[2])}\n"
            f"print(len(grid), grid[({x}, {y})])"
        )
        distractors = [TYPE_ERROR, f"3 {places[2]}", f"2 {places[0]}", KEY_ERROR, f"3 {places[0]}"]
        why = (
            f"Tuples are immutable, so they work fine as keys. `({x}, {y})` is assigned twice, "
            f"so its value is replaced with {places[2]!r} and the dict has 2 keys."
        )
    elif shape == "nested":
        name = rng.choice(NAMES)
        scores = rng.sample(range(70, 100), 2)
        code = (
            f"key = ({_lit(name)}, {scores})\nresults = {{}}\n"
            f'results[key] = "pass"\nprint(results[key])'
        )
        distractors = ["pass", KEY_ERROR, f"{{('{name}', {scores}): 'pass'}}", "None"]
        why = (
            "A tuple is only hashable if everything inside it is. This tuple holds a "
            "list, so using it as a key raises a TypeError."
        )
    elif shape == "list_value":
        name = rng.choice(NAMES)
        scores = rng.sample(range(70, 100), 3)
        code = (
            f"grades = {{}}\ngrades[{_lit(name)}] = {scores[:2]}\n"
            f"grades[{_lit(name)}].append({scores[2]})\nprint(grades)"
        )
        distractors = [
            TYPE_ERROR,
            f"{{{name!r}: {scores[:2]}}}",
            f"{{{name!r}: {scores[:2]}, {name!r}: [{scores[2]}]}}",
            error_choice("AttributeError"),
        ]
        why = (
            f"Only KEYS must be hashable; values can be anything, including lists. "
            f"`grades[{_lit(name)}]` is the list itself, so `append` adds {scores[2]} to it."
        )
    else:
        code = (
            f"spot = [{x}, {y}]\ngrid = {{tuple(spot): {_lit(places[0])}}}\n"
            f"spot.append({x2})\nprint(grid)"
        )
        distractors = [
            f"{{({x}, {y}, {x2}): {places[0]!r}}}",
            TYPE_ERROR,
            f"{{[{x}, {y}, {x2}]: {places[0]!r}}}",
            f"{{[{x}, {y}]: {places[0]!r}}}",
        ]
        why = (
            f"`tuple(spot)` makes a NEW tuple `({x}, {y})`, which is a valid key. Appending "
            f"to the list afterwards does not change that tuple."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_copy_alias(rng: random.Random) -> Question:
    """``b = a`` shares one dict; ``a.copy()`` / ``dict(a)`` are separate but SHALLOW."""
    shape = rng.choice(["flat", "flat", "shallow", "shallow", "rebind"])
    if shape == "flat":
        var, d, spare, _, _ = _int_dict(rng, 3)
        k = rng.choice(list(d))
        v = d[k]
        nv = rng.choice([x for x in range(1, 21) if x not in d.values()])
        sv = rng.randint(1, 9)
        how = rng.choice(["", ".copy()", "dict"])
        rhs = f"dict({var})" if how == "dict" else f"{var}{how}"
        code = (
            f"{_assign(var, d)}\nbackup = {rhs}\nbackup[{_lit(k)}] = {nv}\n"
            f"{var}[{_lit(spare)}] = {sv}\nprint(len(backup), {var}[{_lit(k)}])"
        )
        combos = [f"4 {nv}", f"3 {v}", f"4 {v}", f"3 {nv}", f"3 {v + nv}"]
        if how == "":
            why = (
                f"`backup = {var}` does not copy anything: both names refer to the SAME dict. "
                f"So the change through `backup` shows in `{var}` ({nv}), and the key added "
                f"through `{var}` shows in `backup` (4 keys)."
            )
        else:
            why = (
                f"`{rhs}` makes a separate dict, so changing `backup` leaves `{var}[{_lit(k)}]` "
                f"at {v}, and the key added to `{var}` does not appear in `backup` (3 keys)."
            )
        return _output(code, HARD, combos, why, rng)
    if shape == "shallow":
        teams = rng.sample(_COLORS, 2)
        names = rng.sample(NAMES, 4)
        d = {teams[0]: [names[0]], teams[1]: [names[1]]}
        how = rng.choices([".copy()", "dict", ""], weights=[3, 2, 1])[0]
        rhs = "dict(teams)" if how == "dict" else f"teams{how}"
        code = (
            f"{_assign('teams', d)}\nbackup = {rhs}\n"
            f"backup[{_lit(teams[0])}].append({_lit(names[2])})\n"
            f"backup[{_lit(teams[1])}] = [{_lit(names[3])}]\nprint(teams)"
        )
        appended = [names[0], names[2]]
        combos = [
            {teams[0]: appended, teams[1]: [names[1]]},
            {teams[0]: [names[0]], teams[1]: [names[1]]},
            {teams[0]: appended, teams[1]: [names[3]]},
            {teams[0]: [names[0]], teams[1]: [names[3]]},
        ]
        if how == "":
            why = (
                "`backup = teams` is just a second name for the same dict, so BOTH changes "
                "made through `backup` show up in `teams`."
            )
        else:
            why = (
                f"`{rhs}` is a SHALLOW copy: a new dict whose values are the same list "
                f"objects. Appending mutates the shared list, so `teams` sees it; assigning a "
                f"new list to `backup[{_lit(teams[1])}]` only changes `backup`."
            )
        return _output(code, HARD, [repr(c) for c in combos], why, rng)
    var, d, spare, _, _ = _int_dict(rng, 2)
    k = rng.choice(list(d))
    nv = rng.choice([x for x in range(1, 21) if x not in d.values()])
    sv = rng.randint(1, 9)
    code = (
        f"{_assign(var, d)}\nother = {var}\nother = {{{_lit(k)}: {nv}}}\n"
        f"other[{_lit(spare)}] = {sv}\nprint({var})"
    )
    distractors = [
        repr({k: nv, spare: sv}),
        repr({**d, spare: sv}),
        repr({**d, k: nv}),
        repr({**d, k: nv, spare: sv}),
    ]
    why = (
        f"`other = {var}` first makes both names share one dict, but the next line points "
        f"`other` at a brand-new dict. Changes made after that only affect the new dict, so "
        f"`{var}` is unchanged."
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_modify_while_looping(rng: random.Random) -> Question:
    """Deleting keys while looping over a dict raises RuntimeError; loop over a list copy."""
    var, d0, _, key_name, _ = _int_dict(rng, 4)
    zeros = rng.sample(range(4), rng.choice([1, 2]))
    d = {k: (0 if i in zeros else v) for i, (k, v) in enumerate(d0.items())}
    filtered = {k: v for k, v in d.items() if v != 0}
    # Misconception borrowed from lists: removing an item makes the loop skip the next one.
    skipped = list(d.items())
    i = 0
    while i < len(skipped):
        if skipped[i][1] == 0:
            skipped.pop(i)
        i += 1
    shape = rng.choice(["direct", "direct", "keys_view", "snapshot", "snapshot", "values"])
    head = _assign(var, d)
    if shape in ("direct", "keys_view", "snapshot"):
        source = {"direct": var, "keys_view": f"{var}.keys()", "snapshot": f"list({var})"}[shape]
        remove = f"del {var}[{key_name}]" if rng.random() < 0.6 else f"{var}.pop({key_name})"
        code = (
            f"{head}\nfor {key_name} in {source}:\n    if {var}[{key_name}] == 0:\n"
            f"        {remove}\nprint({var})"
        )
        if shape == "snapshot":
            distractors = [RUNTIME_ERROR, _pairs_repr(skipped), repr(d), KEY_ERROR]
            why = (
                f"`list({var})` is a separate snapshot of the keys taken before the loop, so "
                f"removing keys from `{var}` inside the loop is safe: every 0 is removed."
            )
        else:
            distractors = [repr(filtered), _pairs_repr(skipped), KEY_ERROR, repr(d)]
            looped = (
                f"The loop walks over `{var}` itself"
                if shape == "direct"
                else f"`{var}.keys()` is a live view of `{var}`, not a copy"
            )
            why = (
                f"{looped}, so removing a key changes the dict's size in the middle of the "
                f"loop and Python raises a RuntimeError. Loop over `list({var})` instead."
            )
    else:
        refill = rng.randint(5, 9)
        code = (
            f"{head}\nfor {key_name} in {var}:\n    if {var}[{key_name}] == 0:\n"
            f"        {var}[{key_name}] = {refill}\nprint({var})"
        )
        distractors = [RUNTIME_ERROR, repr(d), repr(filtered), KEY_ERROR]
        why = (
            "Changing the VALUE of a key that already exists does not change the dict's "
            f"size, so it is allowed while looping: every 0 becomes {refill}."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_ANIMALS = [
    "cat",
    "cow",
    "crab",
    "bee",
    "bear",
    "bat",
    "duck",
    "deer",
    "dog",
    "fox",
    "frog",
    "seal",
    "swan",
    "owl",
    "goat",
    "hawk",
    "hen",
    "lion",
    "elk",
    "eel",
    "pig",
    "puma",
]


@generator(TOPIC, HARD)
def gen_grouping(rng: random.Random) -> Question:
    """Grouping into lists with ``setdefault`` / ``if not in`` - and the overwrite bug."""
    by = rng.choice(["len", "first"])
    if by == "len":
        three = [w for w in _ANIMALS if len(w) == 3]
        four = [w for w in _ANIMALS if len(w) == 4]
        n3 = rng.choice([2, 3])
        words = rng.sample(three, n3) + rng.sample(four, 5 - n3)
        key_expr = "len({w})"
        key_fn = len
    else:
        letters = sorted({w[0] for w in _ANIMALS if sum(x[0] == w[0] for x in _ANIMALS) >= 2})
        a, b = rng.sample(letters, 2)
        pa = [w for w in _ANIMALS if w[0] == a]
        pb = [w for w in _ANIMALS if w[0] == b]
        na = min(len(pa), rng.choice([2, 3]))
        words = rng.sample(pa, na) + rng.sample(pb, min(len(pb), 5 - na))
        key_expr = "{w}[0]"

        def key_fn(text: str) -> str:
            return text[0]

    while True:
        rng.shuffle(words)
        if key_fn(words[-1]) != key_fn(words[0]) or rng.random() < 0.3:
            break
    w = rng.choice(["w", "word"])
    g = rng.choice(["groups", "by_key"])
    key = key_expr.format(w=w)
    body = rng.choice(["setdefault", "setdefault", "if_not_in", "overwrite"])
    if body == "setdefault":
        lines = f"    {g}.setdefault({key}, []).append({w})"
    elif body == "if_not_in":
        lines = f"    if {key} not in {g}:\n        {g}[{key}] = []\n    {g}[{key}].append({w})"
    else:
        lines = f"    {g}[{key}] = [{w}]"
    code = f"animals = {_lit(words)}\n{g} = {{}}\nfor {w} in animals:\n{lines}\nprint({g})"

    def group(seq):
        out: dict = {}
        for x in seq:
            out.setdefault(key_fn(x), []).append(x)
        return out

    full = group(words)
    last_only = {k: [v[-1]] for k, v in full.items()}
    first_only = {k: [v[0]] for k, v in full.items()}
    distractors = [
        repr(full),
        repr(last_only),
        repr(dict(sorted(full.items()))),
        repr(group(words[:-1])),
        repr(first_only),
        repr({k: v[1:] or v for k, v in full.items()}),
    ]
    if body == "overwrite":
        distractors = [
            repr(full),
            repr(first_only),
            repr(dict(sorted(last_only.items()))),
        ] + distractors
        why = (
            f"`{g}[{key}] = [{w}]` REPLACES the list every time a key repeats, so each key "
            f"only keeps the last word that had it. To collect them all you must append to "
            f"the existing list."
        )
    elif body == "setdefault":
        why = (
            f"`setdefault({key}, [])` inserts an empty list only the FIRST time a key is seen "
            f"and otherwise returns the existing list, so every word is appended to its "
            f"group. Keys appear in the order first seen."
        )
    else:
        why = (
            "A new list is created only when the key is missing; after that each word is "
            "appended to the existing list. Keys appear in the order first seen."
        )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_setdefault_trace(rng: random.Random) -> Question:
    """``get`` never inserts; ``setdefault`` inserts only missing keys and never overwrites."""
    var, pool, lo, hi, _, _ = rng.choice(_INT_THEMES)
    names = rng.sample(pool, 4)
    vals = rng.sample(range(lo, hi + 1), 2)
    d = dict(zip(names[:2], vals))
    existing = rng.choice(names[:2])
    miss_get, miss_sd = names[2], names[3]
    defaults = rng.sample([x for x in range(10) if x not in vals], 3)
    ops = [
        ("get", miss_get, defaults[0]),
        ("setdefault", miss_sd, defaults[1]),
        ("setdefault", existing, defaults[2]),
    ]
    rng.shuffle(ops)
    lines = [_assign(var, d)]
    for name, (method, k, dflt) in zip("abc", ops):
        lines.append(f"{name} = {var}.{method}({_lit(k)}, {dflt})")
    lines += ["print(a, b, c)", f"print({var})"]
    code = "\n".join(lines)

    def model(sd_overwrites=False, get_inserts=False, sd_no_insert=False):
        state = dict(d)
        results = []
        for method, k, dflt in ops:
            if method == "get":
                results.append(state.get(k, dflt))
                if get_inserts and k not in state:
                    state[k] = dflt
            elif k in state:
                if sd_overwrites:
                    state[k] = dflt
                results.append(state[k])
            else:
                if not sd_no_insert:
                    state[k] = dflt
                results.append(dflt)
        return " ".join(str(r) for r in results) + "\n" + repr(state)

    distractors = [
        model(sd_overwrites=True),
        model(get_inserts=True),
        model(sd_no_insert=True),
        model(sd_overwrites=True, get_inserts=True),
        model(get_inserts=True, sd_no_insert=True),
    ]
    why = (
        f"`get` only reads, so {miss_get!r} is never added. `setdefault` returns the existing "
        f"value for {existing!r} ({d[existing]}) without changing it, and only for the missing "
        f"key {miss_sd!r} does it insert the default ({defaults[1]})."
    )
    return _output(code, HARD, distractors, why, rng)


_INVERT_THEMES = [
    (
        "colors",
        "by_color",
        "fruit",
        "color",
        {
            "apple": "red",
            "cherry": "red",
            "lime": "green",
            "pear": "green",
            "lemon": "yellow",
            "banana": "yellow",
            "plum": "purple",
            "grape": "purple",
        },
    ),
    ("grades", "by_grade", "name", "grade", None),
    ("houses", "by_house", "name", "house", None),
]


@generator(TOPIC, HARD)
def gen_invert(rng: random.Random) -> Question:
    """Inverting a dict: duplicate values collide, so the last (or first) key wins."""
    var, inv, k_name, v_name, mapping = rng.choice(_INVERT_THEMES)
    while True:
        if mapping:
            keys = rng.sample(sorted(mapping), 3)
            d = {k: mapping[k] for k in keys}
        else:
            letters = ["A", "B", "C"] if var == "grades" else ["red", "blue", "gold"]
            keys = rng.sample(NAMES, 4)
            d = {k: rng.choice(letters) for k in keys}
        distinct = len(set(d.values()))
        if 2 <= distinct < len(d):
            break
    guarded = rng.random() < 0.35
    body = f"    {inv}[{v_name}] = {k_name}"
    if guarded:
        body = f"    if {v_name} not in {inv}:\n    " + body
    head = f"{_assign(var, d)}\n{inv} = {{}}\nfor {k_name}, {v_name} in {var}.items():\n{body}\n"
    pairs = [(v, k) for k, v in d.items()]
    last = {}
    for v, k in pairs:
        last[v] = k
    first = {}
    for v, k in pairs:
        first.setdefault(v, k)
    moved = _merge(pairs, "move")
    dup_val = next(v for v in last if last[v] != first[v])
    right = first if guarded else last
    wrong = last if guarded else first
    if rng.random() < 0.6:
        code = head + f"print({inv})"
        partial: dict = {}
        for v, k in pairs[:-1]:
            if not guarded or v not in partial:
                partial[v] = k
        distractors = [
            repr(wrong),
            _pairs_repr(pairs),
            _pairs_repr(moved),
            repr(dict(sorted(right.items()))),
            repr(partial),
            repr(dict(sorted(wrong.items()))),
            repr(d),
        ] + [repr({**right, dup_val: k}) for v, k in pairs if v == dup_val]
        distractors.append(repr({v: k for k, v in reversed(list(d.items()))}))
    else:
        code = head + f"print(len({inv}), {inv}[{_lit(dup_val)}])"
        distractors = [
            f"{len(d)} {right[dup_val]}",
            f"{distinct} {wrong[dup_val]}",
            f"{len(d)} {wrong[dup_val]}",
            f"{distinct + 1} {right[dup_val]}",
        ]
    if guarded:
        why = (
            f"Several keys share the value {dup_val!r}. The `if ... not in` check only lets "
            f"the FIRST one in, so {dup_val!r} maps to {first[dup_val]!r}; the result has "
            f"{distinct} keys."
        )
    else:
        why = (
            f"Several keys share the value {dup_val!r}, so `{inv}[{_lit(dup_val)}]` is assigned "
            f"more than once and the LAST assignment wins ({last[dup_val]!r}), keeping the "
            f"key's original position. Only {distinct} keys remain."
        )
    return _output(code, HARD, distractors, why, rng)
