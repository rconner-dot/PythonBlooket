"""Question generators for the "lists" topic (Lists).

Covers indexing (including negative indexes and IndexError), item assignment,
``append``/``insert``/``extend``, ``pop``/``remove``/``del`` and what they
return, ``in``/``count``/``index``, ``+`` and ``*``, slicing (steps, copies,
slice assignment), ``sort()`` vs ``sorted()``, comparing lists, nested lists,
and the classic mutation gotchas: aliasing vs copying, shallow copies, ``+=``
vs ``+``, shared rows from ``[[0] * n] * m``, functions that mutate their
argument, and modifying a list while looping over it.
"""

from __future__ import annotations

import random

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    NAMES,
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

TOPIC = "lists"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
INDEX_ERROR = error_choice("IndexError")
VALUE_ERROR = error_choice("ValueError")
TYPE_ERROR = error_choice("TypeError")
ATTRIBUTE_ERROR = error_choice("AttributeError")
RUNTIME_ERROR = error_choice("RuntimeError")
BLANK = "___"
BOOL_PAIRS = ["True True", "True False", "False True", "False False"]


# --------------------------------------------------------------------------
# Private helpers & pools
# --------------------------------------------------------------------------

# Variable name -> words that fit it.  No word appears in two pools.
_WORD_POOLS = {
    "fruits": ["apple", "kiwi", "plum", "pear", "fig", "lime", "mango", "grape", "peach", "melon"],
    "pets": ["cat", "dog", "fish", "bird", "frog", "rabbit", "pony", "duck", "mouse", "snake"],
    "colors": ["red", "blue", "green", "pink", "gold", "gray", "teal", "white", "black", "olive"],
    "snacks": ["chips", "nuts", "toast", "jelly", "fries", "cake", "pizza", "taco", "bagel", "cookie"],
    "tools": ["saw", "drill", "tape", "nail", "glue", "rope", "hammer", "wrench", "ruler", "brush"],
    "cities": ["Oslo", "Rome", "Paris", "Lima", "Cairo", "Tokyo", "Delhi", "Seoul", "Quito", "Dubai"],
}
_NUM_VARS = ["nums", "scores", "values", "data", "ages", "marks", "points", "levels"]
_PAIRS = [("a", "b"), ("first", "second"), ("left", "right"), ("mine", "yours"), ("old", "new")]
_ALIAS_PAIRS = [
    ("original", "backup"),
    ("a", "b"),
    ("mine", "yours"),
    ("team", "squad"),
    ("today", "tomorrow"),
    ("before", "after"),
    ("plan", "draft"),
]


def _src(value) -> str:
    """Python source for ``value`` (strings double-quoted, lists recursively)."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join(_src(v) for v in value) + "]"
    return repr(value)


def _show(*values) -> str:
    """Exactly what ``print(*values)`` prints."""
    return " ".join(str(v) for v in values)


def _lines(*values) -> str:
    """What one ``print(v)`` per value prints."""
    return "\n".join(str(v) for v in values)


def _run(code: str) -> str:
    """The choice text for what ``code`` prints, or the error it raises."""
    res = run_code(code)
    if res.error:
        return error_choice(res.error)
    return res.output if res.output else NOTHING_PRINTED


def _output(
    code: str,
    difficulty: int,
    distractors: list,
    explanation: str,
    rng: random.Random,
    *,
    prompt: str = PRINT,
    allow_error: bool = False,
) -> Question:
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[d if isinstance(d, str) else str(d) for d in distractors],
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _value_question(
    code: str, var: str, difficulty: int, distractors: list, explanation: str, rng: random.Random
) -> Question:
    """'What is the value of ``var`` after this code runs?' (answer found by running it)."""
    res = run_code(code)
    if res.error or var not in res.namespace:
        raise GenerationError(f"value question snippet failed: {res.error}")
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=f"What is the value of `{var}` after this code runs?",
        correct=repr(res.namespace[var]),
        distractors=[repr(d) for d in distractors],
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _with_error(rng: random.Random, distractors: list, err: str, p: float = 0.35) -> list:
    """Sometimes slip an error choice in among the top distractors, so questions
    whose answer IS an error don't stand out as the only ones offering one."""
    out = list(distractors)
    if rng.random() < p:
        out.insert(rng.randint(1, 2), err)
    else:
        out.append(err)
    return out


def _items(rng: random.Random, k: int, kind: str | None = None) -> tuple[str, list]:
    """A variable name and ``k`` distinct items (words or two-digit numbers)."""
    kind = kind or rng.choice(["num", "word"])
    if kind == "word":
        var = rng.choice(list(_WORD_POOLS))
        return var, rng.sample(_WORD_POOLS[var], k)
    return rng.choice(_NUM_VARS), rng.sample(range(10, 100), k)


def _fresh(rng: random.Random, items: list):
    """A new value of the same kind as ``items`` that isn't in it."""
    if isinstance(items[0], str):
        pool = next(p for p in _WORD_POOLS.values() if items[0] in p)
    elif max(items) < 10:
        pool = range(1, 10)
    else:
        pool = range(10, 100)
    return rng.choice([v for v in pool if v not in items])


def _rep(items: list, i: int, v) -> list:
    out = list(items)
    out[i] = v
    return out


def _ins(items: list, i: int, v) -> list:
    out = list(items)
    out.insert(i, v)
    return out


def _without(items: list, i: int) -> list:
    out = list(items)
    del out[i]
    return out


def _drop_value(items: list, v) -> list:
    out = list(items)
    if v in out:
        out.remove(v)
    return out


def _and(values: list) -> str:
    """'1', '1 and 2', '1, 2 and 3'."""
    words = [str(v) for v in values]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def _from_end(k: int) -> str:
    """'the last item', 'the 2nd item from the end', ..."""
    return "the last item" if k == 1 else f"the {_ordinal(k)} item from the end"


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _confusable(rng: random.Random, n: int, i: int) -> list[int]:
    """``n`` distinct digits where the VALUE ``i`` is present but not at INDEX ``i``,
    so mixing up "index i" and "value i" gives a different (wrong) answer."""
    vals = rng.sample(range(10), n)
    others = [k for k in range(n) if k != i]
    if i not in vals:
        vals[rng.choice(others)] = i
    elif vals[i] == i:
        j = rng.choice(others)
        vals[i], vals[j] = vals[j], vals[i]
    return vals


def _unsorted(rng: random.Random, items: list) -> list:
    """``items`` shuffled so it is neither ascending nor descending."""
    out = list(items)
    for _ in range(50):
        rng.shuffle(out)
        if out != sorted(out) and out != sorted(out, reverse=True):
            return out
    raise GenerationError("could not shuffle into an unsorted order")


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_indexing(rng: random.Random) -> Question:
    """Positive and negative indexes, len - 1 is the last index, IndexError past the end."""
    var, items = _items(rng, rng.randint(4, 5))
    n = len(items)
    head = f"{var} = {_src(items)}\n"
    shape = rng.choices(["pos", "neg", "ends", "len", "out"], weights=[3, 3, 2, 2, 2])[0]
    if shape == "pos":
        i = rng.randint(1, n - 2)
        code = head + f"print({var}[{i}])"
        distractors = _with_error(rng, [items[i - 1], items[i + 1], items[-i], items[0]], INDEX_ERROR)
        why = (
            f"Indexes start at 0, so `{var}[0]` is {items[0]!r} and `{var}[{i}]` is the "
            f"{_ordinal(i + 1)} item: {items[i]!r}."
        )
    elif shape == "neg":
        k = rng.randint(1, 3)
        code = head + f"print({var}[-{k}])"
        distractors = _with_error(
            rng, [items[-k - 1], items[k], items[k - 1] if k > 1 else items[1], items[0]], INDEX_ERROR
        )
        why = (
            f"Negative indexes count from the end and `-1` is the last item, so `{var}[-{k}]` "
            f"is {_from_end(k)}: {items[-k]!r}."
        )
    elif shape == "ends":
        code = head + f"print({var}[0], {var}[-1])"
        distractors = _with_error(
            rng,
            [
                _show(items[1], items[-1]),
                _show(items[0], items[-2]),
                _show(items[1], items[-2]),
                _show(items[-1], items[0]),
            ],
            INDEX_ERROR,
        )
        why = (
            f"`{var}[0]` is the first item ({items[0]!r}) and `{var}[-1]` is the last one "
            f"({items[-1]!r}); `print` separates them with a space."
        )
    elif shape == "len":
        k = rng.randint(1, 2)
        code = head + f"print({var}[len({var}) - {k}])"
        distractors = [
            items[n - k - 1],
            items[n - k + 1] if k > 1 else INDEX_ERROR,
            items[k],
            INDEX_ERROR,
            items[k - 1],
        ]
        why = (
            f"`len({var})` is {n}, so this is `{var}[{n - k}]`, which is {items[n - k]!r}. "
            f"The last valid index is {n - 1}, one less than the length."
        )
    else:
        idx = rng.choice([str(n), f"len({var})"])
        code = head + f"print({var}[{idx}])"
        distractors = [items[-1], "None", items[0], NOTHING_PRINTED]
        why = (
            f"`{var}` has {n} items, so its valid indexes are 0 to {n - 1}. Index {n} is one "
            f"past the end, so Python raises an IndexError."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_change_item(rng: random.Random) -> Question:
    """Assigning to lst[i] replaces one item (no insert); assigning past the end fails."""
    shape = rng.choice(["pos", "pos", "neg", "aug", "copy", "out"])
    var, items = _items(rng, rng.randint(3, 5))
    n = len(items)
    v = _fresh(rng, items)
    head = f"{var} = {_src(items)}\n"
    as_value = False
    if shape == "pos":
        i = rng.randrange(n)
        code = head + f"{var}[{i}] = {_src(v)}"
        off_by_one = _rep(items, i - 1, v) if i > 0 else _rep(items, 1, v)
        distractors = [_ins(items, i, v), off_by_one, items, items + [v]]
        why = (
            f"Assigning to `{var}[{i}]` REPLACES the item at index {i} ({items[i]!r}) with "
            f"{v!r}. Nothing is inserted, so the list still has {n} items."
        )
        as_value = rng.random() < 0.4
    elif shape == "neg":
        k = rng.randint(1, 2)
        code = head + f"{var}[-{k}] = {_src(v)}"
        distractors = [_rep(items, n - k - 1, v), _rep(items, k - 1, v), _ins(items, n - k, v), items + [v]]
        why = (
            f"`{var}[-{k}]` is {_from_end(k)} ({items[-k]!r}), and "
            f"assigning to it replaces that item with {v!r}."
        )
        as_value = rng.random() < 0.4
    elif shape == "aug":
        i = rng.randrange(n)
        if isinstance(v, str):
            code = head + f'{var}[{i}] += "s"'
            changed = _rep(items, i, items[i] + "s")
            distractors = [
                items + ["s"],
                TYPE_ERROR,
                [w + "s" for w in items],
                _rep(items, i - 1 if i else 1, items[i - 1 if i else 1] + "s"),
            ]
            why = (
                f'`{var}[{i}] += "s"` means `{var}[{i}] = {var}[{i}] + "s"`: it builds the '
                f"string {changed[i]!r} and stores it back in slot {i}. Only that one item changes."
            )
        else:
            d = rng.randint(1, 9)
            code = head + f"{var}[{i}] += {d}"
            changed = _rep(items, i, items[i] + d)
            j = i - 1 if i else 1
            distractors = [
                [x + d for x in items],
                _rep(items, i, d),
                _rep(items, j, items[j] + d),
                items + [d],
            ]
            why = (
                f"`{var}[{i}] += {d}` means `{var}[{i}] = {var}[{i}] + {d}`, so only index {i} "
                f"changes: {items[i]} becomes {items[i] + d}."
            )
        code += f"\nprint({var})"
    elif shape == "copy":
        if rng.random() < 0.5:
            code = head + f"{var}[0] = {var}[-1]\nprint({var})"
            changed = _rep(items, 0, items[-1])
            distractors = [
                [items[-1]] + items[1:-1] + [items[0]],
                _rep(items, -1, items[0]),
                items,
                [items[-1]] + items,
            ]
            why = (
                f"The right side is read first: `{var}[-1]` is {items[-1]!r}. That value is then "
                f"stored at index 0, replacing {items[0]!r}. It's a copy, not a swap, so the "
                f"last item is unchanged."
            )
        else:
            code = head + f"{var}[-1] = {var}[0]\nprint({var})"
            changed = _rep(items, -1, items[0])
            distractors = [
                [items[-1]] + items[1:-1] + [items[0]],
                _rep(items, 0, items[-1]),
                items,
                items + [items[0]],
            ]
            why = (
                f"The right side is read first: `{var}[0]` is {items[0]!r}. That value is then "
                f"stored in the last slot, replacing {items[-1]!r}. It's a copy, not a swap, so "
                f"the first item is unchanged."
            )
    else:
        idx = rng.choice([str(n), f"len({var})"])
        code = head + f"{var}[{idx}] = {_src(v)}\nprint({var})"
        distractors = [items + [v], _rep(items, n - 1, v), items, [v] + items]
        why = (
            f"The valid indexes of `{var}` are 0 to {n - 1}. Assigning to index {n} doesn't "
            f"add a new item, it raises an IndexError; use `{var}.append(...)` to grow a list."
        )
    if as_value:
        return _value_question(code, var, EASY, [d for d in distractors if isinstance(d, list)], why, rng)
    if shape in ("pos", "neg"):
        code += f"\nprint({var})"
        distractors = _with_error(rng, distractors, INDEX_ERROR)
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_append_insert(rng: random.Random) -> Question:
    """append adds at the end; insert(i, x) puts x AT index i and shifts the rest right."""
    var, items = _items(rng, rng.randint(3, 4))
    n = len(items)
    v = _fresh(rng, items)
    head = f"{var} = {_src(items)}\n"
    shape = rng.choice(["append", "insert", "insert", "front", "count", "both"])
    if shape == "append":
        code = head + f"{var}.append({_src(v)})\nprint({var})"
        distractors = [[v] + items, _rep(items, n - 1, v), items, "None"]
        why = (
            f"`append` adds its argument as a new item at the END of the list, so {v!r} goes "
            f"after {items[-1]!r} and the list grows to {n + 1} items."
        )
    elif shape == "insert":
        i = rng.randint(1, n - 1)
        code = head + f"{var}.insert({i}, {_src(v)})\nprint({var})"
        distractors = [_ins(items, i + 1, v), _rep(items, i, v), _ins(items, i - 1, v), items + [v]]
        why = (
            f"`insert({i}, {v!r})` puts {v!r} AT index {i}, in front of {items[i]!r} (the old "
            f"item at index {i}), which shifts one place right. Nothing is replaced."
        )
    elif shape == "front":
        code = head + f"{var}.insert(0, {_src(v)})\nprint({var})"
        distractors = [items + [v], _rep(items, 0, v), _ins(items, 1, v), items]
        why = (
            f"Index 0 is the front of the list, so `insert(0, {v!r})` puts {v!r} before every "
            f"existing item and the list grows to {n + 1} items."
        )
    elif shape == "count":
        w = _fresh(rng, items + [v])
        code = head + f"{var}.append({_src(v)})\n{var}.append({_src(w)})\nprint(len({var}))"
        distractors = [n + 1, n, n + 3, 2, n + 4]
        why = (
            f"`{var}` starts with {n} items and each `append` adds exactly one, so its length "
            f"is {n} + 2 = {n + 2}."
        )
    else:
        w = _fresh(rng, items + [v])
        code = head + f"{var}.append({_src(v)})\n{var}.insert(0, {_src(w)})\nprint({var})"
        distractors = [
            [v] + items + [w],
            items + [v, w],
            [w] + items[1:] + [v],
            [w, v] + items,
        ]
        why = (
            f"`append` puts {v!r} at the end, then `insert(0, {w!r})` puts {w!r} at the very "
            f"front, shifting everything else one place right."
        )
    return _output(code, EASY, distractors, why, rng)


def _membership_probe(rng: random.Random, kind: str, items: list[str], pool: list[str], used: set):
    """A value to test with ``in``, the list word it is based on, and why the result is what it is."""
    free = [w for w in items if w not in used]
    if kind == "part":
        longs = [w for w in free if len(w) >= 5 and w[:3] not in items]
        if longs:
            w = rng.choice(longs)
            p = w[:3]
            return (
                p,
                w,
                f"{p!r} is only part of {w!r}, and `in` on a list compares WHOLE items, so it is False",
            )
        kind = "out"
    if kind == "case":
        w = rng.choice(free)
        p = w.lower() if w[0].isupper() else w.capitalize()
        return p, w, f"{p!r} is not equal to {w!r} (string comparison is case-sensitive), so it is False"
    if kind == "in":
        w = rng.choice(free)
        return w, w, f"{w!r} is one of the items, so it is True"
    w = rng.choice([x for x in pool if x not in items and x not in used])
    return w, w, f"{w!r} is not in the list at all, so it is False"


@generator(TOPIC, EASY)
def gen_membership_count(rng: random.Random) -> Question:
    """`in` compares whole items; count() and index() (first match, ValueError if missing)."""
    shape = rng.choice(["in", "in", "count", "count_missing", "index", "index_missing"])
    if shape == "in":
        var = rng.choice(list(_WORD_POOLS))
        pool = _WORD_POOLS[var]
        items = rng.sample(pool, 4)
        kinds = ["in", "part", "case", "out"]
        k1, k2 = rng.choices(kinds, weights=[3, 2, 2, 1], k=2)
        used: set = set()
        p1, base, why1 = _membership_probe(rng, k1, items, pool, used)
        used.add(base)
        p2, _base, why2 = _membership_probe(rng, k2, items, pool, used)
        code = f"{var} = {_src(items)}\nprint({_src(p1)} in {var}, {_src(p2)} in {var})"
        why = f"`in` checks whether any item EQUALS the value: {why1}; {why2}."
        return _output(code, EASY, BOOL_PAIRS, why, rng)

    var = rng.choice(_NUM_VARS)
    v = rng.randint(1, 9)
    others = [x for x in range(1, 10) if x != v]
    if shape == "count":
        c = rng.randint(2, 3)
        items = rng.sample(others, 6 - c) + [v] * c
        rng.shuffle(items)
        code = f"{var} = {items}\nprint({var}.count({v}))"
        distractors = _with_error(rng, [items.index(v), c + 1, len(items), c - 1, v], VALUE_ERROR, 0.25)
        why = f"`count({v})` returns how many items are equal to {v}; it appears {c} times in `{var}`."
    elif shape == "count_missing":
        items = rng.sample(others, 5)
        w = rng.choice([x for x in others if x not in items])
        code = f"{var} = {items}\nprint({var}.count({w}))"
        distractors = [VALUE_ERROR, "-1", "None", "False"]
        why = (
            f"{w} isn't in `{var}`, and `count` never raises an error: it just returns how "
            f"many times the value appears, which is 0."
        )
    elif shape == "index":
        items = rng.sample(others, 3)
        p1 = rng.randint(0, 2)
        p2 = rng.randint(p1 + 2, 4)
        items.insert(p1, v)
        items.insert(p2, v)
        code = f"{var} = {items}\nprint({var}.index({v}))"
        distractors = _with_error(rng, [p2, p1 + 1, 2, p2 + 1], VALUE_ERROR, 0.25)
        why = (
            f"{v} is at indexes {p1} and {p2}, and `index` returns the position of the FIRST "
            f"match, so it prints {p1}."
        )
    else:
        items = rng.sample(others, 5)
        w = rng.choice([x for x in others if x not in items])
        code = f"{var} = {items}\nprint({var}.index({w}))"
        distractors = ["-1", "None", INDEX_ERROR, "0"]
        why = (
            f"{w} isn't in `{var}`. Unlike `count`, `index` raises a ValueError when the value "
            f"is missing (it does NOT return -1 like a string's `find`)."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_concat_repeat(rng: random.Random) -> Question:
    """+ joins two lists and * repeats a list; neither does element-wise math."""
    x, y = rng.choice(_PAIRS)
    a = rng.sample(range(1, 10), rng.randint(2, 3))
    b = rng.sample(range(1, 10), rng.randint(2, 3))
    shape = rng.choice(["plus", "plus", "times", "fill", "len", "plus_int"])
    if shape == "plus":
        code = f"{x} = {a}\n{y} = {b}\nprint({x} + {y})"
        elementwise = [p + q for p, q in zip(a, b)]
        distractors = [elementwise if len(a) == len(b) else b + a, [a, b], b + a, elementwise]
        distractors = _with_error(rng, distractors, TYPE_ERROR)
        why = (
            f"`+` on two lists makes a new list: the items of `{x}` followed by the items of "
            f"`{y}`. It never adds the numbers together."
        )
    elif shape == "times":
        k = rng.randint(2, 3)
        code = f"{x} = {a}\nprint({x} * {k})"
        distractors = _with_error(rng, [[v * k for v in a], [a] * k, a], TYPE_ERROR)
        why = (
            f"`* {k}` repeats the whole list {k} times, end to end. To multiply each number "
            f"you would need a loop."
        )
    elif shape == "fill":
        v = rng.randint(0, 9)
        k = rng.randint(3, 5)
        name = rng.choice(["row", "slots", "counts", "tally"])
        code = f"{name} = [{v}] * {k}\nprint({name})"
        distractors = [[v * k], [v, k], [[v]] * k, [v] * (k + 1)]
        why = (
            f"`[{v}] * {k}` repeats the one-item list {k} times, giving {k} copies of {v}. "
            f"It's a common way to build a list of a fixed size."
        )
    elif shape == "len":
        if rng.random() < 0.5:
            ans = len(a) + len(b)
            code = f"{x} = {a}\n{y} = {b}\nprint(len({x} + {y}))"
            distractors = [2, len(a) * len(b), ans + 1, ans - 1, len(a)]
            why = f"`{x} + {y}` is one list holding all {len(a)} + {len(b)} = {ans} items."
        else:
            k = rng.randint(2, 4)
            ans = len(a) * k
            code = f"{x} = {a}\nprint(len({x} * {k}))"
            distractors = [len(a) + k, len(a), k, ans + 1]
            why = (
                f"`{x} * {k}` repeats all {len(a)} items {k} times, so it holds {len(a)} × {k} = {ans} items."
            )
        distractors = _with_error(rng, distractors, TYPE_ERROR, 0.2)
    else:
        v = rng.randint(1, 9)
        code = f"{x} = {a}\nprint({x} + {v})"
        distractors = [a + [v], [e + v for e in a], a, [v] + a]
        why = (
            f"`+` can only join a list with another list. `{x} + {v}` mixes a list and an int, "
            f"so Python raises a TypeError; write `{x} + [{v}]` or use `append` instead."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_basic_slicing(rng: random.Random) -> Question:
    """[a:b], [:b], [a:], [-k:]; the stop index is excluded and a slice is always a list."""
    var, items = _items(rng, rng.randint(5, 6), rng.choice(["num", "num", "word"]))
    n = len(items)
    head = f"{var} = {_src(items)}\n"
    shape = rng.choice(["mid", "mid", "head", "tail", "last", "single", "which"])
    if shape in ("mid", "which"):
        a = rng.randint(1, 2)
        b = rng.randint(a + 2, min(n - 1, a + 3))
        target = items[a:b]
        if shape == "which":
            wrong = [
                f"{var}[{a}:{b - 1}]",
                f"{var}[{a + 1}:{b + 1}]",
                f"{var}[{a - 1}:{b}]",
                f"{var}[{a + 1}:{b}]",
                f"{var}[{a - 1}:{b - 1}]",
                f"{var}[{a}:{b + 1}]",
            ]
            rng.shuffle(wrong)
            return which_expression_question(
                topic=TOPIC,
                difficulty=EASY,
                prompt=f"Which expression evaluates to `{target}`?",
                setup=head.strip(),
                target=target,
                correct_expr=f"{var}[{a}:{b}]",
                wrong_exprs=wrong,
                explanation=(
                    f"The wanted items sit at indexes {a} to {b - 1}. A slice stops just BEFORE "
                    f"its stop index, so you need `{var}[{a}:{b}]`."
                ),
                rng=rng,
            )
        code = head + f"print({var}[{a}:{b}])"
        distractors = [
            items[a : b + 1],
            items[a - 1 : b - 1],
            items[a + 1 : b + 1],
            items[a - 1 : b],
            items[a + 1 : b],
        ]
        why = (
            f"A slice includes the start index but stops just BEFORE the stop index, so "
            f"`{var}[{a}:{b}]` holds the items at indexes {a} to {b - 1}."
        )
    elif shape == "head":
        b = rng.randint(2, n - 2)
        code = head + f"print({var}[:{b}])"
        distractors = [items[: b + 1], items[: b - 1], items[b:], items[1 : b + 1]]
        why = (
            f"Leaving out the start means 'from the beginning', and the slice stops before "
            f"index {b}, so you get the first {b} items."
        )
    elif shape == "tail":
        a = rng.randint(2, n - 2)
        code = head + f"print({var}[{a}:])"
        distractors = [items[a + 1 :], items[a - 1 :], items[:a], items[a:-1]]
        why = (
            f"Leaving out the stop means 'to the end', so `{var}[{a}:]` starts at index {a} "
            f"({items[a]!r}) and keeps everything after it."
        )
    elif shape == "last":
        k = rng.randint(2, 3)
        code = head + f"print({var}[-{k}:])"
        distractors = [items[:-k], items[-k - 1 :], items[-k:-1], items[-k + 1 :]]
        why = (
            f"`-{k}` is the {_ordinal(k)} item from the end and the empty stop runs to the "
            f"end, so `{var}[-{k}:]` is the last {k} items."
        )
    else:
        i = rng.randint(0, n - 2)
        x = items[i]
        code = head + f"print({var}[{i}])\nprint({var}[{i}:{i + 1}])"
        distractors = [_lines(x, x), _lines([x], [x]), _lines(x, items[i : i + 2]), _lines([x], x)]
        why = (
            f"An index gives you the item itself ({x!r}), but a slice always gives back a "
            f"LIST, even when it holds just one item."
        )
    return _output(code, EASY, distractors, why, rng)


# ==========================================================================
# MEDIUM
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_append_extend(rng: random.Random) -> Question:
    """append adds ONE item (maybe a list), extend / += add each item; insert(-1, x)."""
    shape = rng.choice(["method", "method", "combo", "string", "insert_neg", "blank"])
    var = rng.choice(_NUM_VARS)
    if shape == "method":
        a = rng.sample(range(1, 10), rng.randint(2, 3))
        b = rng.sample(range(10, 20), 2)
        method = rng.choice(["append", "extend"])
        if rng.random() < 0.5:
            code = f"{var} = {a}\n{var}.{method}({b})\nprint(len({var}), {var})"
        else:
            code = f"{var} = {a}\nextra = {b}\n{var}.{method}(extra)\nprint(len({var}), {var})"
        distractors = [
            _show(len(a) + 1, a + [b]),
            _show(len(a) + 2, a + b),
            _show(len(a) + 1, a + b),
            _show(len(a) + 2, a + [b]),
            _show(len(a), a),
        ]
        why = (
            f"`append` adds its argument as ONE item, so the whole list {b} becomes a single nested "
            f"item and the length goes up by 1."
            if method == "append"
            else f"`extend` adds each item of {b} separately, so the list grows by 2 and stays flat."
        )
    elif shape == "combo":
        a = rng.sample(range(1, 10), 2)
        b = rng.sample(range(10, 20), 2)
        c = rng.randint(20, 29)
        first, second = rng.choice([("+=", "append"), ("append", "+=")])
        lines = [f"{var} = {a}"]
        notes = []
        for op, arg in ((first, b), (second, [c])):
            if op == "+=":
                lines.append(f"{var} += {arg}")
                notes.append(f"`{var} += {arg}` works like `extend`, adding the item(s) of {arg} separately")
            else:
                lines.append(f"{var}.append({arg})")
                notes.append(f"`append({arg})` adds the list {arg} as ONE nested item")
        code = "\n".join(lines + [f"print({var})"])
        distractors = [a + b + [c], [*a, b, [c]], [*a, b, c], a + b + [[c]], a + [b + [c]]]
        why = notes[0][0].upper() + notes[0][1:] + ", while " + notes[1] + "."
    elif shape == "string":
        var, items = _items(rng, 2, "word")
        word = rng.choice([w for w in _WORD_POOLS[var] if w not in items and len(w) <= 5])
        method = rng.choice(["extend", "+=", "append"])
        stmt = f"{var} += {_src(word)}" if method == "+=" else f"{var}.{method}({_src(word)})"
        if rng.random() < 0.6:
            code = f"{var} = {_src(items)}\n{stmt}\nprint({var})"
            distractors = [items + [word], items + list(word), items + [list(word)], TYPE_ERROR]
        else:
            code = f"{var} = {_src(items)}\n{stmt}\nprint(len({var}))"
            distractors = [3, 2 + len(word), 2, TYPE_ERROR, len(word)]
        if method == "append":
            why = (
                f"`append` adds its argument as one item, so the whole string {word!r} becomes the 3rd item."
            )
        else:
            why = (
                f"`{method}` adds each item of the iterable it is given, and iterating over the "
                f"string {word!r} gives its {len(word)} letters, so each letter becomes its own item."
            )
    elif shape == "insert_neg":
        a = rng.sample(range(10, 100), rng.randint(3, 4))
        v = _fresh(rng, a)
        code = f"{var} = {a}\n{var}.insert(-1, {v})\nprint({var})"
        distractors = [a + [v], _rep(a, -1, v), _ins(a, len(a) - 2, v), [v] + a]
        why = (
            f"`insert(i, x)` puts x in front of the item currently at index i. Index -1 is the "
            f"last item ({a[-1]}), so {v} lands just BEFORE it, not at the end."
        )
    else:
        a = rng.sample(range(1, 10), rng.randint(2, 3))
        b = rng.sample(range(10, 20), 2)
        correct = rng.choice(["append", "extend"])
        template = f"{var} = {a}\n{var}.{BLANK}({b})\nprint({var})"
        target = _run(template.replace(BLANK, correct))
        cands = ["extend" if correct == "append" else "append", "insert", "index", "remove", "count"]
        wrong = [c for c in cands if _run(template.replace(BLANK, c)) != target]
        why = (
            f"To get {target} the list {b} must be added as ONE nested item, which is what `append` does."
            if correct == "append"
            else f"To get {target} each item of {b} must be added separately, which is what `extend` does."
        )
        return build_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=f"Which method fills the blank (`{BLANK}`) so the code prints `{target}`?",
            correct=correct,
            distractors=wrong,
            explanation=why,
            rng=rng,
            code=template,
        )
    prompt = PRINT_OR_ERROR if shape == "string" else PRINT
    return _output(code, MEDIUM, distractors, why, rng, prompt=prompt, allow_error=shape == "string")


@generator(TOPIC, MEDIUM)
def gen_pop_remove_del(rng: random.Random) -> Question:
    """pop(i) uses an INDEX and returns the item; remove(x) uses a VALUE and returns None; del."""
    var = rng.choice(_NUM_VARS)
    shape = rng.choice(
        ["pop_i", "pop_i", "pop_last", "remove_dup", "del", "remove_returns", "remove_missing"]
    )
    if shape == "pop_i":
        i = rng.randint(1, 3)
        items = _confusable(rng, 5, i)
        name = rng.choice(["x", "item", "removed", "taken"])
        code = f"{var} = {items}\n{name} = {var}.pop({i})\nprint({name})\nprint({var})"
        distractors = [
            _lines(i, _drop_value(items, i)),
            _lines("None", _without(items, i)),
            _lines(items[i - 1], _without(items, i - 1)),
            _lines(items[-1], items[:-1]),
            _lines(_without(items, i), _without(items, i)),
        ]
        why = (
            f"`pop({i})` removes the item at INDEX {i} (that's {items[i]}, not the value {i}) and "
            f"returns it, so `{name}` is {items[i]}."
        )
    elif shape == "pop_last":
        items = rng.sample(range(10, 100), rng.randint(4, 5))
        n = len(items)
        name = rng.choice(["last", "top", "x"])
        code = f"{var} = {items}\n{name} = {var}.pop()\nprint({name}, len({var}))"
        distractors = [
            _show(items[0], n - 1),
            _show(items[-1], n),
            _show("None", n - 1),
            _show(items[-2], n - 1),
        ]
        why = (
            f"With no argument, `pop()` removes the LAST item ({items[-1]}) and returns it; the "
            f"list shrinks from {n} to {n - 1} items."
        )
    elif shape == "remove_dup":
        v = rng.randint(0, 4)
        others = rng.sample([x for x in range(10) if x != v], 3)
        p1 = rng.randint(0, 1)
        p2 = rng.randint(p1 + 2, 4)
        items = list(others)
        items.insert(p1, v)
        items.insert(p2, v)
        code = f"{var} = {items}\n{var}.remove({v})\nprint({var})"
        distractors = [
            [x for x in items if x != v],
            _without(items, p2),
            _without(items, v),
            VALUE_ERROR,
        ]
        why = (
            f"`remove({v})` deletes only the FIRST item equal to {v} (at index {p1}); the other "
            f"{v} stays. It looks for a value, not an index."
        )
    elif shape == "del":
        i = rng.randint(1, 3)
        items = _confusable(rng, 5, i)
        code = f"{var} = {items}\ndel {var}[{i}]\nprint({var})"
        distractors = _with_error(
            rng,
            [_drop_value(items, i), _without(items, i - 1), _without(items, i + 1), items[:i]],
            INDEX_ERROR,
            0.25,
        )
        why = (
            f"`del {var}[{i}]` deletes the item at INDEX {i}, which is {items[i]}; everything "
            f"after it moves one place left."
        )
    elif shape == "remove_returns":
        items = rng.sample(range(10, 100), 4)
        v = rng.choice(items)
        name = rng.choice(["result", "gone", "out"])
        code = f"{var} = {items}\n{name} = {var}.remove({v})\nprint({name})"
        distractors = [v, _drop_value(items, v), "True", items.index(v)]
        why = (
            f"`remove` changes the list in place and returns None, so `{name}` is None even though "
            f"{v} really was removed. (`pop` is the one that returns the removed item.)"
        )
    else:
        items = rng.sample(range(10), 5)
        w = rng.choice([x for x in range(5) if x not in items] or [x for x in range(10) if x not in items])
        code = f"{var} = {items}\n{var}.remove({w})\nprint({var})"
        distractors = [items, _without(items, w) if w < len(items) else items[:-1], INDEX_ERROR, "None"]
        why = (
            f"`remove` looks for a VALUE. There is no {w} in `{var}`, so it raises a ValueError "
            f"(it doesn't quietly do nothing, and it never treats {w} as an index)."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_sort_vs_sorted(rng: random.Random) -> Question:
    """sort() sorts in place and returns None; sorted() returns a new list; reverse() just flips."""
    if rng.random() < 0.6:
        var = rng.choice(_NUM_VARS)
        items = _unsorted(rng, rng.sample(range(1, 30), rng.randint(4, 5)))
    else:
        var = rng.choice([k for k in _WORD_POOLS])
        items = _unsorted(rng, rng.sample(_WORD_POOLS[var], 4))
    asc, desc = sorted(items), sorted(items, reverse=True)
    head = f"{var} = {_src(items)}\n"
    shape = rng.choice(
        [
            "sort_none",
            "self_assign",
            "sorted_orig",
            "sorted_orig",
            "reverse_flag",
            "chain",
            "reverse",
            "types",
        ]
    )
    if shape == "types":
        first, second = (f"sorted({var})", f"{var}.sort()")
        if rng.random() < 0.5:
            code = head + f"a = {first}\nb = {second}\nprint(type(a), type(b))"
        else:
            code = head + f"a = {second}\nb = {first}\nprint(type(a), type(b))"
        combos = [
            _show(f"<class '{x}'>", f"<class '{y}'>")
            for x in ("list", "NoneType")
            for y in ("list", "NoneType")
        ]
        why = (
            f"`sorted({var})` returns a new list, while `{var}.sort()` sorts in place and returns "
            f"None, whose type is `NoneType`."
        )
        return _output(code, MEDIUM, combos, why, rng)
    if shape == "sort_none":
        name = rng.choice(["result", "ordered", "tidy"])
        code = head + f"{name} = {var}.sort()\nprint({name})"
        distractors = [asc, items, desc, TYPE_ERROR]
        why = (
            f"`sort()` rearranges `{var}` itself and returns None, so `{name}` is None. Use "
            f"`sorted({var})` when you want the sorted list back as a value."
        )
    elif shape == "self_assign":
        code = head + f"{var} = {var}.sort()\nprint({var})"
        distractors = [asc, items, desc, TYPE_ERROR]
        why = (
            f"`{var}.sort()` sorts the list in place but returns None, and that None is then "
            f"assigned back to `{var}` - the sorted list is lost."
        )
    elif shape == "sorted_orig":
        name = rng.choice(["ordered", "ranked", "tidy"])
        code = head + f"{name} = sorted({var})\nprint({var})\nprint({name})"
        distractors = [_lines(asc, asc), _lines(items, "None"), _lines(asc, items), _lines(items, items)]
        why = (
            f"`sorted({var})` builds and returns a NEW sorted list and leaves `{var}` untouched, "
            f"so `{var}` keeps its original order."
        )
    elif shape == "reverse_flag":
        rev = rng.random() < 0.5
        flag = "reverse=True" if rev else ""
        code = head + f"{var}.sort({flag})\nprint({var}[0], {var}[-1])"
        right, other = (desc, asc) if rev else (asc, desc)
        distractors = [
            _show(other[0], other[-1]),
            _show(items[0], items[-1]),
            TYPE_ERROR,
            _show(items[-1], items[0]),
            ATTRIBUTE_ERROR,
        ]
        if isinstance(items[0], str):
            direction = "Z to A" if rev else "A to Z"
        else:
            direction = "largest to smallest" if rev else "smallest to largest"
        why = (
            f"`sort({flag})` sorts the list in place from {direction}, so afterwards index 0 "
            f"holds {right[0]!r} and index -1 holds {right[-1]!r}."
        )
    elif shape == "chain":
        code = head + f"first = {var}.sort()[0]\nprint(first)"
        distractors = [asc[0], items[0], "None", ATTRIBUTE_ERROR]
        why = (
            f"`{var}.sort()` returns None, so `[0]` tries to index None and Python raises a "
            f"TypeError. `sorted({var})[0]` would work."
        )
    else:
        code = head + f"{var}.reverse()\nprint({var})"
        distractors = [desc, asc, "None", items]
        why = (
            f"`reverse()` just flips the current order in place (last item first); it does not "
            f"sort, so the result is {items[::-1]}, not a descending sort."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_alias_vs_copy(rng: random.Random) -> Question:
    """b = a gives a second NAME for the same list; a[:], a.copy(), list(a) make a new list."""
    a_name, b_name = rng.choice(_ALIAS_PAIRS)
    _var, items = _items(rng, 3)
    v = _fresh(rng, items)
    how = rng.choice(["alias", "alias", "slice", "copy", "list"])
    make = {"alias": a_name, "slice": f"{a_name}[:]", "copy": f"{a_name}.copy()", "list": f"list({a_name})"}[
        how
    ]
    head = f"{a_name} = {_src(items)}\n{b_name} = {make}\n"
    if rng.random() < 0.7:
        who, other = rng.choice([(b_name, a_name), (b_name, a_name), (a_name, b_name)])
        if rng.random() < 0.5:
            stmt = f"{who}.append({_src(v)})"
            changed = items + [v]
        else:
            i = rng.randrange(3)
            stmt = f"{who}[{i}] = {_src(v)}"
            changed = _rep(items, i, v)
        code = head + f"{stmt}\nprint({a_name})\nprint({b_name})"
        both = _lines(changed, changed)
        sep = _lines(items, changed) if who == b_name else _lines(changed, items)
        flipped = _lines(changed, items) if who == b_name else _lines(items, changed)
        distractors = [both, sep, flipped, _lines(items, items)]
        if how == "alias":
            why = (
                f"`{b_name} = {a_name}` copies nothing: both names refer to the SAME list, so the "
                f"change made through `{who}` shows up when you print `{other}` too."
            )
        else:
            why = (
                f"`{make}` builds a NEW list with the same items, so changing `{who}` leaves "
                f"`{other}` exactly as it was."
            )
        return _output(code, MEDIUM, distractors, why, rng)
    grow = rng.random() < 0.4
    code = (
        head
        + (f"{b_name}.append({_src(v)})\n" if grow else "")
        + f"print({a_name} == {b_name}, {a_name} is {b_name})"
    )
    if how == "alias":
        why = (
            f"`is` asks whether two names refer to the very same object, and after `{b_name} = {a_name}` "
            f"they do, so `is` is True; `==` compares contents, which are identical"
            + (" (the append changed the one shared list)." if grow else ".")
        )
    else:
        why = f"`{make}` is a different list object, so `is` is False. `==` compares contents: " + (
            f"`{b_name}` now has an extra item, so they're not equal."
            if grow
            else "the items are the same, so it's True."
        )
    return _output(code, MEDIUM, BOOL_PAIRS, why, rng)


def _grid_src(name: str, grid: list) -> str:
    if len(grid) <= 2 and len(_src(grid)) < 40:
        return f"{name} = {_src(grid)}"
    return "\n".join([f"{name} = ["] + [f"    {_src(row)}," for row in grid] + ["]"])


@generator(TOPIC, MEDIUM)
def gen_nested_indexing(rng: random.Random) -> Question:
    """grid[row][col], len of a 2D list, rows as lists, and `in` on a nested list."""
    shape = rng.choice(["cell", "cell", "neg", "row", "len", "in", "which", "jagged"])
    name = rng.choice(["grid", "matrix", "board", "table", "rows"])
    r = rng.randint(2, 3)
    c = rng.choice([k for k in (2, 3, 4) if k != r])
    vals = rng.sample(range(1, 30), r * c)
    grid = [vals[k * c : (k + 1) * c] for k in range(r)]
    head = _grid_src(name, grid) + "\n"
    if shape == "cell":
        ri, ci = rng.randrange(r), rng.randrange(c)
        code = head + f"print({name}[{ri}][{ci}])"
        swapped = grid[ci][ri] if ci < r and ri < c else INDEX_ERROR
        distractors = [
            swapped,
            grid[ri - 1][ci - 1] if ri and ci else grid[(ri + 1) % r][ci],
            grid[ri][(ci + 1) % c],
            grid[(ri + 1) % r][ci],
            INDEX_ERROR,
        ]
        why = (
            f"`{name}[{ri}]` is row {ri}: {grid[ri]}. Then `[{ci}]` picks index {ci} of that row, "
            f"which is {grid[ri][ci]}. The first index is the row, the second the column."
        )
    elif shape == "neg":
        ri, ci = rng.choice([(-1, 0), (0, -1), (-1, -1), (-1, 1), (1, -1), (-2, -1)][: 6 if r == 3 else 5])
        code = head + f"print({name}[{ri}][{ci}])"
        distractors = [
            grid[ci][ri] if -r <= ci < r and -c <= ri < c else grid[ri][ci - 1],
            grid[ri][ci - 1],
            grid[ri - 1][ci],
            grid[0][0],
            grid[-1][-1],
        ]
        why = (
            f"`{name}[{ri}]` is the row {grid[ri]}, and `[{ci}]` of that row is {grid[ri][ci]}. "
            f"Negative indexes count from the end at both levels."
        )
    elif shape == "row":
        ri = rng.randrange(min(r, c))
        code = head + f"print({name}[{ri}])"
        column = [row[ri] for row in grid]
        distractors = [column, grid[ri - 1] if ri else grid[1], grid[ri][0], grid[ri][:-1], INDEX_ERROR]
        why = (
            f"With just one index you get a whole row, and row {ri} is the list {grid[ri]} "
            f"(the column would need a loop: {column})."
        )
    elif shape == "len":
        code = head + f"print(len({name}), len({name}[0]))"
        distractors = [_show(c, r), _show(r * c, c), _show(r, r * c), _show(r * c, r * c)]
        why = (
            f"`{name}` is a list of {r} rows, so `len({name})` is {r}; `{name}[0]` is one row "
            f"with {c} items, so its length is {c}."
        )
    elif shape == "in":
        ri, ci = rng.randrange(r), rng.randrange(c)
        v = grid[ri][ci]
        other = rng.choice([k for k in range(r) if k != ri])
        second, second_ok = rng.choice(
            [
                (f"{v} in {name}[{ri}]", True),
                (f"{v} in {name}[{other}]", False),
                (f"{_src(grid[ri])} in {name}", True),
            ]
        )
        code = head + f"print({v} in {name}, {second})"
        why = (
            f"The items of `{name}` are the ROWS (lists), not the numbers inside them, so "
            f"`{v} in {name}` is False even though {v} is in row {ri}; `{second}` is {second_ok}."
        )
        return _output(code, MEDIUM, BOOL_PAIRS, why, rng)
    elif shape == "which":
        ri, ci = rng.randrange(r), rng.randrange(c)
        target = grid[ri][ci]
        correct = f"{name}[{ri}][{ci}]"
        note = ""
        if ri == r - 1 and rng.random() < 0.5:
            correct = f"{name}[-1][{ci}]"
            note = " (`-1` picks the last row)"
        wrong = [
            f"{name}[{ci}][{ri}]",
            f"{name}[{ri + 1}][{ci + 1}]",
            f"{name}[{ri}][{ci + 1}]",
            f"{name}[{ri - 1}][{ci}]",
            f"{name}[{ri}, {ci}]",
            f"{name}[{ri + 1}][{ci}]",
        ]
        rng.shuffle(wrong)
        return which_expression_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=f"Which expression evaluates to `{target}`?",
            setup=head.strip(),
            target=target,
            correct_expr=correct,
            wrong_exprs=wrong,
            explanation=(
                f"{target} is in row {ri} (`{name}[{ri}]` is {grid[ri]}) at index {ci} of that row, "
                f"so you index the row first and then the column{note}."
            ),
            rng=rng,
        )
    else:
        people = rng.sample(NAMES, 6)
        sizes = rng.choice([[2, 3, 1], [3, 1, 2], [1, 2, 3], [2, 1, 3], [3, 2, 1]])
        teams, k = [], 0
        for s in sizes:
            teams.append(people[k : k + s])
            k += s
        name = rng.choice(["teams", "groups", "squads"])
        head = _grid_src(name, teams) + "\n"
        ti = rng.randrange(3)
        if rng.random() < 0.5:
            code = head + f"print(len({name}), len({name}[{ti}]))"
            distractors = [
                _show(6, sizes[ti]),
                _show(sizes[ti], 3),
                _show(3, 6),
                _show(len(teams[ti - 1]) and 3, sizes[ti - 1]),
            ]
            why = (
                f"`{name}` holds 3 inner lists, so its length is 3 no matter how many names are "
                f"inside them; `{name}[{ti}]` is {teams[ti]}, which has {sizes[ti]} "
                f"item{'s' if sizes[ti] > 1 else ''}."
            )
        else:
            code = head + f"print({name}[{ti}][-1])"
            row = teams[ti]
            distractors = [
                row[0] if len(row) > 1 else teams[ti - 1][-1],
                teams[-1][ti] if ti < len(teams[-1]) else INDEX_ERROR,
                teams[ti - 1][-1],
                row,
                people[-1],
            ]
            why = f"`{name}[{ti}]` is {row}, and `[-1]` is the last name in that inner list: {row[-1]!r}."
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_loop_update(rng: random.Random) -> Question:
    """Changing the loop variable doesn't change the list; changing nums[i] does."""
    var = rng.choice(_NUM_VARS)
    items = rng.sample(range(1, 10), rng.randint(3, 4))
    loop = rng.choice(["x", "n", "num", "value"])
    shape = rng.choice(["loopvar", "loopvar", "loopvar_x", "index", "prefix", "prefix", "front"])
    if shape in ("loopvar", "loopvar_x"):
        k = rng.randint(2, 3)
        op, f = rng.choice(
            [
                (f"{loop} = {loop} * {k}", lambda x: x * k),
                (f"{loop} *= {k}", lambda x: x * k),
                (f"{loop} += {k * 5}", lambda x: x + k * 5),
            ]
        )
        changed = [f(x) for x in items]
        if shape == "loopvar":
            code = f"{var} = {items}\nfor {loop} in {var}:\n    {op}\nprint({var})"
            distractors = [changed, items[:-1] + [changed[-1]], [changed[0]] + items[1:], "None"]
        else:
            code = f"{var} = {items}\nfor {loop} in {var}:\n    {op}\nprint({loop}, {var})"
            distractors = [_show(changed[-1], changed), _show(items[-1], items), _show(items[-1], changed)]
        why = (
            f"Each pass, `{loop}` is just a name for the current number. `{op}` makes `{loop}` "
            f"refer to a NEW number and never touches the list, so `{var}` is unchanged"
            + (f" (while `{loop}` ends up as {changed[-1]})." if shape == "loopvar_x" else ".")
        )
    elif shape == "index":
        k = rng.randint(2, 3)
        code = f"{var} = {items}\nfor i in range(len({var})):\n    {var}[i] = {var}[i] * {k}\nprint({var})"
        changed = [x * k for x in items]
        distractors = [items, changed[:-1] + items[-1:], items[:1] + changed[1:], INDEX_ERROR]
        why = (
            f"`range(len({var}))` gives every index 0 to {len(items) - 1}, and assigning to "
            f"`{var}[i]` replaces the item stored in the list, so every number is multiplied by {k}."
        )
    elif shape == "prefix":
        code = f"{var} = {items}\nfor i in range(1, len({var})):\n    {var}[i] = {var}[i] + {var}[i - 1]\nprint({var})"
        running, pair = [items[0]], [items[0]]
        for i in range(1, len(items)):
            running.append(running[-1] + items[i])
            pair.append(items[i] + items[i - 1])
        distractors = [pair, running[1:] + [running[-1] + items[-1]], items, [sum(items)] * len(items)]
        why = (
            f"Each step adds the item before it, and that item was ALREADY updated on the "
            f"previous step, so the list becomes running totals: {running}."
        )
    else:
        code = (
            f"{var} = {items}\nresult = []\nfor {loop} in {var}:\n    result.insert(0, {loop})\nprint(result)"
        )
        distractors = [items, [items[-1]], items[1:] + items[:1], [items[0]]]
        why = (
            f"Each number is inserted at index 0, in FRONT of the ones added before it, so "
            f"the last number processed ({items[-1]}) ends up first: the list comes out reversed."
        )
    return _output(
        code,
        MEDIUM,
        distractors,
        why,
        rng,
        prompt=PRINT_OR_ERROR if shape == "index" else PRINT,
        allow_error=shape == "index",
    )


@generator(TOPIC, MEDIUM)
def gen_step_slicing(rng: random.Random) -> Question:
    """Slices with steps, [::-1], [1:-1], and slicing past the end never raising."""
    var, items = _items(rng, rng.randint(6, 7), rng.choice(["num", "num", "word"]))
    if isinstance(items[0], str):
        items = items[:6]
    n = len(items)
    head = f"{var} = {_src(items)}\n"
    shape = rng.choice(["step", "step", "rev", "inner", "negrange", "beyond"])
    prompt = PRINT
    if shape == "step":
        a = rng.randint(0, 1)
        k = rng.randint(2, 3)
        if rng.random() < 0.5:
            sl = f"{a}::{k}" if a else f"::{k}"
            res = items[a::k]
        else:
            b = rng.randint(a + k + 1, n - 1)
            sl = f"{a}:{b}:{k}"
            res = items[a:b:k]
        code = head + f"print({var}[{sl}])"
        distractors = [
            items[a + 1 :: k],
            items[a :: k + 1],
            items[a : a + k],
            items[a :: k - 1] if k > 2 else items[a + 1 :: k + 1],
        ]
        why = (
            f"`[{sl}]` starts at index {a} and then takes every {_ordinal(k)} item (step {k}), "
            f"so it picks indexes {', '.join(str(i) for i in range(n)[a::k] if items[i] in res)}."
        )
    elif shape == "rev":
        code = head + f"print({var}[::-1])\nprint({var})"
        rev = items[::-1]
        distractors = [
            _lines(rev, rev),
            _lines(sorted(items, reverse=True), items),
            _lines(items, rev),
            _lines(items, items),
        ]
        why = (
            f"`{var}[::-1]` walks the list backwards and returns a NEW reversed list. Slicing never "
            f"changes the original, so `{var}` prints in its original order."
        )
    elif shape == "inner":
        code = head + f"print({var}[1:-1])"
        distractors = [items[1:], items[:-1], items[1:-2], items[2:-1]]
        why = (
            "`[1:-1]` starts at index 1 and stops just BEFORE the last item (index -1), so it "
            "drops the first and last items."
        )
    elif shape == "negrange":
        k = rng.randint(3, 4)
        code = head + f"print({var}[-{k}:-1])"
        distractors = [items[-k:], items[-k + 1 :], items[-k - 1 : -1], items[-k:-2]]
        why = (
            f"`-{k}` is the {_ordinal(k)} item from the end, and the slice stops just BEFORE "
            f"index -1 (the last item), so it gives {k - 1} items."
        )
    else:
        prompt = PRINT_OR_ERROR
        a = rng.randint(n - 3, n - 2)
        stop = rng.choice([10, 20, 50, 100])
        code = head + f"print({var}[{a}:{stop}])"
        distractors = [INDEX_ERROR, items[a:-1], items[a : a + 1], "[]"]
        why = (
            f"Indexing past the end raises an IndexError, but SLICING never does: a stop index "
            f"beyond the end is just clipped to the length ({n}), so you get everything from index {a} on."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=prompt, allow_error=prompt == PRINT_OR_ERROR)


@generator(TOPIC, MEDIUM)
def gen_compare_lists(rng: random.Random) -> Question:
    """== compares item by item (order matters); < compares lexicographically, not by length/sum."""
    x, y = rng.choice(_PAIRS)
    shape = rng.choice(["order", "lexi", "prefix"])
    if shape == "order":
        a = rng.sample(range(1, 10), 3)
        b = _unsorted(rng, a) if rng.random() < 0.5 else a[::-1]
        if b == a:
            b = a[1:] + a[:1]
        z = {"a": "c", "first": "third", "left": "middle", "mine": "theirs", "old": "same"}[x]
        exprs = [(f"{x} == {y}", False), (f"{x} == {z}", True), (f"{x} != {y}", True), (f"{x} != {z}", False)]
        e1 = rng.choice(exprs[:1] + exprs[2:3])
        e2 = rng.choice([exprs[1], exprs[3]])
        if rng.random() < 0.5:
            e1, e2 = e2, e1
        code = f"{x} = {a}\n{y} = {b}\n{z} = {a}\nprint({e1[0]}, {e2[0]})"
        why = (
            f"`==` compares lists item by item in order: `{x}` and `{y}` hold the same numbers in "
            f"a different order, so they are NOT equal, while `{x}` and `{z}` match exactly "
            f"(even though they are two separate lists)."
        )
    elif shape == "lexi":
        p = rng.randint(1, 5)
        lo = [p] + [rng.randint(6, 9) for _ in range(rng.randint(2, 3))]
        hi = [p + rng.randint(1, 3), rng.randint(0, 2)]
        a, b = (lo, hi) if rng.random() < 0.5 else (hi, lo)
        ops = rng.choice([("<", ">"), (">", "<"), ("<", "=="), (">", "!=")])
        code = f"{x} = {a}\n{y} = {b}\nprint({x} {ops[0]} {y}, {x} {ops[1]} {y})"
        why = (
            f"Lists are compared item by item and the FIRST difference decides: {lo[0]} < {hi[0]}, "
            f"so {lo} < {hi}, even though {lo} is longer and has bigger numbers later on."
        )
    else:
        a = rng.sample(range(1, 10), 2)
        b = a + [rng.randint(0, 9)]
        if rng.random() < 0.5:
            x, y = y, x
            a, b = b, a
        short, long_ = (x, y) if len(a) < len(b) else (y, x)
        ops = rng.choice([("<", ">"), (">", "=="), ("<", "!="), ("<=", ">=")])
        code = f"{x} = {a}\n{y} = {b}\nprint({x} {ops[0]} {y}, {x} {ops[1]} {y})"
        why = (
            f"All the items of `{short}` match the start of `{long_}`, and when one list runs out "
            f"first, the shorter list counts as smaller, so `{short} < {long_}` is True."
        )
    return _output(code, MEDIUM, BOOL_PAIRS, why, rng)


# ==========================================================================
# HARD
# ==========================================================================


@generator(TOPIC, HARD)
def gen_shared_rows(rng: random.Random) -> Question:
    """[[0] * c] * r repeats ONE row object; a comprehension builds separate rows."""
    name = rng.choice(["grid", "board", "table", "matrix"])
    r, c = rng.randint(2, 3), rng.randint(2, 3)
    if rng.random() < 0.3:
        fill, v, w = ".", "X", "O"
    else:
        fill, (v, w) = 0, rng.sample(range(1, 10), 2)
    i, j = rng.randrange(r), rng.randrange(c)
    shape = rng.choice(["mult", "mult", "comp", "row_var", "empty", "replace", "replace"])
    by_rows = shape != "row_var" and rng.random() < 0.4
    printer = f"for line in {name}:\n    print(line)" if by_rows else f"print({name})"

    def fmt(grid: list) -> str:
        return _lines(*grid) if by_rows else str(grid)

    blank = [[fill] * c for _ in range(r)]
    separate = [list(row) for row in blank]
    separate[i][j] = v
    shared = [_rep(row, j, v) for row in blank]
    mult = f"{name} = [[{_src(fill)}] * {c}] * {r}"
    if shape in ("mult", "comp"):
        if shape == "mult":
            code = f"{mult}\n{name}[{i}][{j}] = {_src(v)}\n{printer}"
            distractors = [fmt(separate), fmt(blank), TYPE_ERROR, INDEX_ERROR]
            why = (
                f"`[[{_src(fill)}] * {c}] * {r}` does not build {r} rows: it repeats a reference to ONE "
                f"row list {r} times. So setting `{name}[{i}][{j}]` changes that shared row, and every "
                f"row shows {v!r} at index {j}."
            )
        else:
            code = f"{name} = [[{_src(fill)}] * {c} for _ in range({r})]\n{name}[{i}][{j}] = {_src(v)}\n{printer}"
            distractors = [fmt(shared), fmt(blank), TYPE_ERROR, INDEX_ERROR]
            why = (
                f"The comprehension runs `[{_src(fill)}] * {c}` once per row, creating {r} separate "
                f"lists, so `{name}[{i}][{j}] = {v!r}` changes only row {i}."
            )
    elif shape == "row_var":
        k = rng.randint(2, 3)
        build = f"[row] * {k}" if rng.random() < 0.5 else "[" + ", ".join(["row"] * k) + "]"
        blank, shared = blank[:1] * k, [_rep(blank[0], j, v)] * k
        if rng.random() < 0.5:
            change, touched = f"row[{j}] = {_src(v)}", "`row`"
            first_only = [shared[0]] + blank[1:]
        else:
            ii = rng.randrange(k)
            change, touched = f"{name}[{ii}][{j}] = {_src(v)}", f"`{name}[{ii}]`"
            first_only = [shared[0] if x == ii else blank[0] for x in range(k)]
        code = f"row = [{_src(fill)}] * {c}\n{name} = {build}\n{change}\nprint({name})"
        distractors = [str(blank), str(first_only), TYPE_ERROR, str([_rep(blank[0], j, v)] + blank[1:])]
        why = (
            f"`{build}` puts the SAME list object `row` into `{name}` {k} times - no copies are made. "
            f"Changing it through {touched} therefore shows up in every row."
        )
    elif shape == "empty":
        code = f"{name} = [[]] * {r}\n{name}[{i}].append({_src(v)})\n{printer}"
        alone = [[] for _ in range(r)]
        alone[i] = [v]
        distractors = [
            fmt(alone),
            fmt([[] for _ in range(r)]),
            ATTRIBUTE_ERROR,
            fmt([[v]] + [[] for _ in range(r - 1)]),
        ]
        why = (
            f"`[[]] * {r}` holds {r} references to ONE empty list, so appending {v!r} to "
            f"`{name}[{i}]` appends to that single shared list, which every slot shows."
        )
    else:
        if r == 2:
            r = 3
            blank = [[fill] * c for _ in range(r)]
            mult = f"{name} = [[{_src(fill)}] * {c}] * {r}"
            i = rng.randrange(r)
        k = rng.choice([x for x in range(r) if x != i])
        code = f"{mult}\n{name}[{i}] = [{_src(v)}] * {c}\n{name}[{k}][{j}] = {_src(w)}\n{printer}"
        new_row = [v] * c
        real = [new_row if x == i else _rep(blank[0], j, w) for x in range(r)]
        independent = [
            new_row if x == i else (_rep(blank[0], j, w) if x == k else blank[0]) for x in range(r)
        ]
        all_shared = [_rep(new_row, j, w) for _ in range(r)]
        w_everywhere = [_rep(new_row, j, w) if x == i else _rep(blank[0], j, w) for x in range(r)]
        if fmt(real) != _run(code):
            raise GenerationError("shared-row model disagrees with Python")
        distractors = [fmt(independent), fmt(all_shared), fmt(w_everywhere), TYPE_ERROR]
        why = (
            f"At first every row is the same list object. `{name}[{i}] = ...` puts a brand-new list "
            f"into slot {i} only, but the other slots still share the original row, so setting "
            f"`{name}[{k}][{j}]` changes every row except row {i}."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


def _pattern_with_pair(rng: random.Random, n: int) -> list[bool]:
    """``n`` booleans with 2-4 Trues, at least two of them adjacent, last one False-able."""
    for _ in range(200):
        pat = [rng.random() < 0.5 for _ in range(n)]
        if 2 <= sum(pat) <= 4 and any(pat[k] and pat[k + 1] for k in range(n - 2)):
            return pat
    raise GenerationError("no pattern")


@generator(TOPIC, HARD)
def gen_modify_while_iterating(rng: random.Random) -> Question:
    """Removing/popping/appending while a for loop walks the same list."""
    var = rng.choice(_NUM_VARS)
    loop = rng.choice(["x", "n", "num", "value"])
    shape = rng.choice(["remove", "remove", "del_index", "grow", "pop"])
    if shape in ("remove", "del_index"):
        kind = rng.choice(["even", "odd", "big", "small"])
        if kind in ("even", "odd"):
            evens, odds = list(range(2, 21, 2)), list(range(1, 20, 2))
            match_pool, other_pool = (evens, odds) if kind == "even" else (odds, evens)
            test = "{} % 2 == 0" if kind == "even" else "{} % 2 == 1"
        else:
            k = rng.randint(4, 6) * 2
            big, small = list(range(k + 1, k + 15)), list(range(1, k))
            match_pool, other_pool = (big, small) if kind == "big" else (small, big)
            test = "{} > " + str(k) if kind == "big" else "{} < " + str(k)
        pat = _pattern_with_pair(rng, 6)
        hits = iter(rng.sample(match_pool, sum(pat)))
        misses = iter(rng.sample(other_pool, 6 - sum(pat)))
        items = [next(hits) if p else next(misses) for p in pat]
        matches = [x for x, p in zip(items, pat) if p]
        naive = [x for x, p in zip(items, pat) if not p]
        skipped_model = list(items)
        for x in skipped_model:  # the real (skipping) behaviour, simulated by Python itself
            if x in matches:
                skipped_model.remove(x)
        if shape == "remove":
            code = (
                f"{var} = {items}\nfor {loop} in {var}:\n    if {test.format(loop)}:\n"
                f"        {var}.remove({loop})\nprint({var})"
            )
            survivors = [x for x in skipped_model if x in matches]
            distractors = [naive, RUNTIME_ERROR, _drop_value(items, matches[0]), items]
            why = (
                f"Removing an item shifts everything after it one place left, but the loop still moves "
                f"on to the next position, so the item right after each removed one is never checked. "
                f"That's why {_and(survivors)} survived."
            )
        elif rng.random() < 0.6:
            code = (
                f"{var} = {items}\nfor i in range(len({var})):\n    if {test.format(f'{var}[i]')}:\n"
                f"        del {var}[i]\nprint({var})"
            )
            distractors = [naive, skipped_model, RUNTIME_ERROR, items]
            why = (
                f"`range(len({var}))` is worked out ONCE, as `range(6)`, before anything is deleted. "
                f"Each deletion makes the list shorter, so near the end `{var}[i]` points past the "
                f"last item and raises an IndexError."
            )
        else:
            code = (
                f"{var} = {items}\nfor i in range(len({var}) - 1, -1, -1):\n"
                f"    if {test.format(f'{var}[i]')}:\n        del {var}[i]\nprint({var})"
            )
            distractors = [INDEX_ERROR, skipped_model, items, RUNTIME_ERROR]
            why = (
                "This loop walks the indexes BACKWARDS (5, 4, ..., 0). Deleting an item only shifts "
                "the items after it, which were already checked, so nothing is skipped or out of "
                "range and every match is removed."
            )
    elif shape == "grow":
        halving = rng.random() < 0.5
        k = 2 if halving else rng.randint(3, 4)

        def f(x: int) -> int:
            return x // 2 if halving else x - k

        def ok(x: int) -> bool:
            return x % 2 == 0 if halving else x > k

        if halving:
            big = rng.choice([8, 12, 16, 20, 24, 28, 40, 44])
            test, step = f"{loop} % 2 == 0", f"{loop} // 2"
            other = rng.choice([1, 3, 5, 7, 9, 11])
        else:
            big = rng.randint(3 * k + 1, 4 * k - 1)
            test, step = f"{loop} > {k}", f"{loop} - {k}"
            other = rng.randint(1, k)
        items = [big, other] if rng.random() < 0.5 else [other, big]
        code = f"{var} = {items}\nfor {loop} in {var}:\n    if {test}:\n        {var}.append({step})\nprint({var})"
        naive = items + [f(x) for x in items if ok(x)]
        chain = [big]
        while ok(chain[-1]):
            chain.append(f(chain[-1]))
        right_after = []
        for x in items:
            right_after += chain if x == big else [x]
        distractors = [naive, RUNTIME_ERROR, items, right_after]
        why = (
            f"A `for` loop keeps going until it reaches the CURRENT end of the list, so the numbers "
            f"appended during the loop get visited too: {' -> '.join(map(str, chain))}. It stops once "
            f"an appended number fails the test `{test}`."
        )
    else:
        n = rng.randint(4, 5)
        var, items = _items(rng, n)
        if isinstance(items[0], str):
            loop = rng.choice(["item", "x", "word"])
        front = rng.random() < 0.5
        code = (
            f"{var} = {_src(items)}\nseen = []\nfor {loop} in {var}:\n    seen.append({loop})\n"
            f"    {var}.pop({'0' if front else ''})\nprint(seen)\nprint({var})"
        )
        res = run_code(code)
        seen, left = res.namespace["seen"], res.namespace[var]
        half = (n + 1) // 2
        distractors = [
            _lines(items, []),
            RUNTIME_ERROR,
            _lines(items[:half], items[half:]),
            _lines(items[:half], items[: n - half]),
            _lines(seen, []),
            _lines(items, left),
        ]
        if front:
            why = (
                f"The loop walks positions 0, 1, 2, ... while each `pop(0)` shifts the remaining items "
                f"left, so every other item is skipped: the loop only sees {seen}. It stops when its "
                f"position reaches the list's current length."
            )
        else:
            why = (
                f"The loop walks positions 0, 1, 2, ... and stops when the position reaches the list's "
                f"CURRENT length. Each pass also pops an item off the end, so after {len(seen)} passes "
                f"the position catches up with the shrinking list."
            )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_slice_assignment(rng: random.Random) -> Question:
    """Assigning to a slice splices: it can grow, shrink, insert or delete; steps must match."""
    var = rng.choice(_NUM_VARS)
    items = rng.sample(range(1, 10), 5)
    new = rng.sample(range(10, 100, 10), 3)
    shape = rng.choice(["grow", "grow", "insert", "delete", "index_vs_slice", "extended", "shrink"])
    if shape == "grow":
        a, w = rng.randint(1, 2), rng.randint(1, 2)
        new = new[: w + 1] if w == 2 else new[: rng.randint(2, 3)]
        k = len(new)
        code = f"{var} = {items}\n{var}[{a}:{a + w}] = {new}\nprint({var})"
        distractors = [
            items[:a] + new + items[a + k :],
            items[:a] + new[:w] + items[a + w :],
            items[:a] + [new] + items[a + w :],
            VALUE_ERROR,
        ]
        why = (
            f"Assigning to the slice `[{a}:{a + w}]` removes {items[a : a + w]} and puts "
            f"ALL {k} new items in their place, so the list grows from 5 to {5 - w + k} items."
        )
    elif shape == "insert":
        a = rng.randint(1, 4)
        new = new[:2]
        code = f"{var} = {items}\n{var}[{a}:{a}] = {new}\nprint({var})"
        distractors = [
            items[:a] + new + items[a + 1 :],
            items[:a] + [new] + items[a:],
            items[:a] + new + items[a + 2 :],
            VALUE_ERROR,
        ]
        why = (
            f"`[{a}:{a}]` is an EMPTY slice (it starts and stops at index {a}), so nothing is removed: "
            f"the new items are simply inserted in front of {items[a]}."
        )
    elif shape == "delete":
        a = rng.randint(1, 2)
        b = a + rng.randint(2, 3)
        code = f"{var} = {items}\n{var}[{a}:{b}] = []\nprint({var})"
        distractors = [
            items[:a] + [[]] + items[b:],
            items[:a] + items[b + 1 :],
            items,
            items[:a] + [[]] * (b - a) + items[b:],
        ]
        why = (
            f"Assigning an empty list to `[{a}:{b}]` replaces those {b - a} items "
            f"({items[a:b]}) with nothing, so they are deleted - just like `del {var}[{a}:{b}]`."
        )
    elif shape == "index_vs_slice":
        a = rng.randint(1, 3)
        new = new[:2]
        code = f"{var} = {items}\n{var}[{a}] = {new}\nprint({var})"
        distractors = [
            items[:a] + new + items[a + 1 :],
            items[:a] + new + items[a:],
            VALUE_ERROR,
            TYPE_ERROR,
        ]
        why = (
            f"Without a colon, `{var}[{a}]` is ONE slot, so the whole list {new} is stored there as a "
            f"single nested item. Only slice assignment (`{var}[{a}:{a + 1}] = ...`) splices items in."
        )
    elif shape == "extended":
        good = rng.random() < 0.5
        new = new if good else new[:2]
        code = f"{var} = {items}\n{var}[::2] = {new}\nprint({var})"
        stepped = list(items)
        for idx, val in zip(range(0, 5, 2), new):
            stepped[idx] = val
        if good:
            distractors = [
                new + items[3:],
                VALUE_ERROR,
                [items[0], new[0], items[1], new[1], items[2], new[2]],
                [items[0]] + new + items[4:],
            ]
            why = (
                f"`{var}[::2]` refers to indexes 0, 2 and 4, and exactly 3 new values are given, so "
                f"each of those positions is replaced in turn."
            )
        else:
            distractors = [
                stepped,
                new + items[2:],
                items[:1] + new + items[3:],
                [new[0], items[1], new[1]] + items[3:],
            ]
            why = (
                "A slice with a step (`[::2]`) picks exactly 3 fixed positions here (0, 2, 4), so it must "
                "be given exactly 3 values. Giving 2 raises a ValueError; only plain `[a:b]` slices can "
                "change a list's length."
            )
    else:
        a = rng.randint(0, 1)
        b = a + 3
        v = new[0]
        code = f"{var} = {items}\n{var}[{a}:{b}] = [{v}]\nprint({var})"
        distractors = [
            _rep(items, a, v),
            items[:a] + [v] + items[b - 1 :],
            VALUE_ERROR,
            items[:a] + [v] * 3 + items[b:],
        ]
        why = (
            f"The three items {items[a:b]} at indexes {a}..{b - 1} are replaced by the single item {v}, "
            f"so the list shrinks from 5 to 3 items."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_INPLACE_OPS = {"iadd": 3, "append": 1, "imul": 1}
_REBIND_OPS = {"add": 3, "mul": 1}


def _alias_trace(items: list, ops: list, *, iadd_rebinds=False, plus_inplace=False, shared=True) -> tuple:
    """Run ``ops`` on ``b`` (where ``b = a``) under a possibly-wrong mental model."""
    a = list(items)
    b = a if shared else list(a)
    for kind, v in ops:
        if kind == "append":
            b.append(v)
        elif (kind == "iadd" and not iadd_rebinds) or (kind == "add" and plus_inplace):
            b += [v]
        elif kind in ("iadd", "add"):
            b = b + [v]
        elif (kind == "imul" and not iadd_rebinds) or (kind == "mul" and plus_inplace):
            b *= 2
        else:
            b = b * 2
    return a, b


@generator(TOPIC, HARD)
def gen_iadd_vs_add(rng: random.Random) -> Question:
    """With b = a: += / append / *= change the shared list, b = b + [...] makes a new one."""
    a_name, b_name = rng.choice(_ALIAS_PAIRS)
    items = rng.sample(range(1, 10), rng.randint(2, 3))
    vals = rng.sample(range(10, 30), 2)
    inplace = rng.choices(list(_INPLACE_OPS), weights=list(_INPLACE_OPS.values()))[0]
    rebind = rng.choices(list(_REBIND_OPS), weights=list(_REBIND_OPS.values()))[0]
    if inplace == "imul" and rebind == "mul":
        rebind = "add"
    ops = [(inplace, vals[0]), (rebind, vals[1])]
    rng.shuffle(ops)
    src = {
        "iadd": "{b} += [{v}]",
        "append": "{b}.append({v})",
        "imul": "{b} *= 2",
        "add": "{b} = {b} + [{v}]",
        "mul": "{b} = {b} * 2",
    }
    lines = [f"{a_name} = {items}", f"{b_name} = {a_name}"]
    lines += [src[k].format(b=b_name, v=v) for k, v in ops]
    code = "\n".join(lines + [f"print({a_name})", f"print({b_name})"])
    real = _alias_trace(items, ops)
    if _lines(*real) != _run(code):
        raise GenerationError("alias model disagrees with Python")
    models = [
        _alias_trace(items, ops, iadd_rebinds=True),
        _alias_trace(items, ops, plus_inplace=True),
        _alias_trace(items, ops, shared=False),
        (real[1], real[0]),
        (items, items),
    ]
    in_src = src[inplace].format(b=b_name, v=vals[0])
    re_src = src[rebind].format(b=b_name, v=vals[1])
    if ops[0][0] == inplace:
        order = (
            f"`{in_src}` runs first and changes that shared list in place, so `{a_name}` sees it. "
            f"Then `{re_src}` builds a NEW list and points only `{b_name}` at it."
        )
    else:
        order = (
            f"`{re_src}` runs first: it builds a NEW list and points only `{b_name}` at it, so the "
            f"later `{in_src}` changes that new list and `{a_name}` never sees it."
        )
    why = f"`{b_name} = {a_name}` makes both names refer to ONE list. " + order
    return _output(code, HARD, [_lines(*m) for m in models], why, rng)


def _shallow_apply(lst: list, op: tuple) -> None:
    kind = op[0]
    if kind == "append_inner":
        lst[op[1]].append(op[2])
    elif kind == "set_inner":
        lst[op[1]][op[2]] = op[3]
    elif kind == "set_outer":
        lst[op[1]] = list(op[2])
    else:
        lst.append(list(op[1]))


@generator(TOPIC, HARD)
def gen_shallow_copy(rng: random.Random) -> Question:
    """A copy of a nested list is shallow: inner lists are shared, the outer list is not."""
    a_name, b_name = rng.choice(_ALIAS_PAIRS)
    rows = [rng.sample(range(1, 10), 2) for _ in range(2)]
    how = rng.choice(["copy", "slice", "list"])
    make = {"slice": f"{a_name}[:]", "copy": f"{a_name}.copy()", "list": f"list({a_name})"}[how]
    v, w = rng.sample(range(10, 100), 2)
    i, k = rng.randrange(2), rng.randrange(2)
    inner = rng.choice([("append_inner", i, v), ("set_inner", i, rng.randrange(2), v)])
    outer = rng.choice([("set_outer", k, [w, w + 1]), ("append_outer", [w, w + 1])])
    ops = [inner, outer]
    rng.shuffle(ops)
    src = {
        "append_inner": lambda op: f"{b_name}[{op[1]}].append({op[2]})",
        "set_inner": lambda op: f"{b_name}[{op[1]}][{op[2]}] = {op[3]}",
        "set_outer": lambda op: f"{b_name}[{op[1]}] = {op[2]}",
        "append_outer": lambda op: f"{b_name}.append({op[1]})",
    }
    code = "\n".join(
        [f"{a_name} = {rows}", f"{b_name} = {make}"]
        + [src[op[0]](op) for op in ops]
        + [f"print({a_name})", f"print({b_name})"]
    )

    def model(mode: str) -> str:
        a = [list(r) for r in rows]
        if mode == "alias":
            b = a
        elif mode == "shallow":
            b = list(a)
        else:
            b = [list(r) for r in a]
        for op in ops:
            _shallow_apply(b, op)
            if mode == "outer_shared" and op[0] in ("set_outer", "append_outer"):
                _shallow_apply(a, op)
        return _lines(a, b)

    correct = model("shallow")
    if correct != _run(code):
        raise GenerationError("shallow-copy model disagrees with Python")
    real_a, real_b = correct.split("\n")
    distractors = [model("deep"), model("alias"), model("outer_shared"), _lines(real_b, real_a)]
    replaced_first = ops[0][0] == "set_outer" and inner[1] == ops[0][1]
    detail = (
        f" Here `{b_name}[{inner[1]}]` was replaced BEFORE the inner change, so that change went into "
        f"the new row and `{a_name}` didn't see it."
        if replaced_first
        else ""
    )
    why = (
        f"`{make}` is a SHALLOW copy: a new outer list holding the very same inner lists. Changing "
        f"an inner list through `{b_name}` shows up in `{a_name}`, but replacing or adding a whole "
        f"row only affects `{b_name}`.{detail}"
    )
    return _output(code, HARD, distractors, why, rng)


_MUTATE_SRC = {
    "append": "{p}.append({v})",
    "setfirst": "{p}[0] = {v}",
    "iadd": "{p} += [{v}]",
    "insert": "{p}.insert(0, {v})",
}
_REBIND_SRC = {"plus": "{p} = {p} + [{v}]", "fresh": "{p} = [{v}]", "tail": "{p} = {p}[1:]"}


def _apply_func_op(lst: list, kind: str, v: int, inplace: bool) -> list:
    """Apply one function-body statement; returns the (possibly new) local list."""
    if kind == "append":
        lst.append(v)
    elif kind == "setfirst":
        lst[0] = v
    elif kind == "iadd":
        lst += [v]
    elif kind == "insert":
        lst.insert(0, v)
    else:
        new = {"plus": lst + [v], "fresh": [v], "tail": lst[1:]}[kind]
        if not inplace:
            return new
        lst[:] = new
    return lst


@generator(TOPIC, HARD)
def gen_function_mutation(rng: random.Random) -> Question:
    """A function can change the caller's list in place, but rebinding its parameter can't."""
    fname = rng.choice(["update", "process", "tweak", "adjust", "change"])
    p = rng.choice(["items", "lst", "values"])
    var = rng.choice(["nums", "scores", "data", "marks"])
    items = rng.sample(range(1, 10), 3)
    vals = rng.sample(range(10, 100), 3)
    muts = rng.sample(list(_MUTATE_SRC), 2)
    reb = rng.choice(list(_REBIND_SRC))
    returns = rng.random() < 0.5
    bodies = [[muts[0], reb, muts[1]], [muts[0], reb, muts[1]], [reb, muts[0]]]
    if returns:
        bodies.append([muts[0], reb])
    body = rng.choice(bodies)
    stmts = list(zip(body, vals))
    lines = [f"def {fname}({p}):"]
    for kind, v in stmts:
        lines.append("    " + {**_MUTATE_SRC, **_REBIND_SRC}[kind].format(p=p, v=v))
    if returns:
        lines.append(f"    return {p}")
    lines += ["", "", f"{var} = {items}"]
    lines += (
        [f"result = {fname}({var})", f"print({var})", "print(result)"]
        if returns
        else [f"{fname}({var})", f"print({var})"]
    )
    code = "\n".join(lines)

    def model(mode: str) -> str:
        caller = list(items)
        local = list(caller) if mode == "copy" else caller
        for kind, v in stmts:
            if mode == "skip_rebind" and kind in _REBIND_SRC:
                continue
            local = _apply_func_op(local, kind, v, inplace=(mode in ("inplace", "stop")))
            if mode == "stop" and kind in _REBIND_SRC:
                break
        return _lines(caller, local) if returns else str(caller)

    correct = model("real")
    if correct != _run(code):
        raise GenerationError("function model disagrees with Python")
    distractors = [model("inplace"), model("copy"), model("skip_rebind")]
    if returns:
        c_line, r_line = correct.split("\n")
        distractors += [_lines(r_line, r_line), _lines(r_line, c_line), _lines(c_line, c_line)]
    distractors += [
        model("stop"),
        str(items + [v for k, v in stmts if k in ("append", "iadd")]),
        str(items[::-1]),
    ]
    reb_src = _REBIND_SRC[reb].format(p=p, v=dict(stmts)[reb])
    if body[0] == reb:
        detail = (
            f"`{reb_src}` runs first and points `{p}` at a NEW list, so nothing the function "
            f"changes afterwards reaches `{var}`."
        )
    else:
        detail = (
            f"So the change(s) before `{reb_src}` reach `{var}`, but that line builds a NEW list and "
            f"points only the local name `{p}` at it, so nothing after it affects `{var}`."
        )
    why = f"Inside `{fname}`, `{p}` starts as a second name for the caller's list `{var}`. " + detail
    return _output(code, HARD, distractors, why, rng)


def _trace_ops(rng: random.Random, start: list[int]) -> list[tuple]:
    """A random sequence of valid list operations on ``start``."""
    lst = list(start)
    ops: list[tuple] = []
    kinds = ["append", "insert", "pop_i", "pop", "remove", "del", "set", "extend"]
    weights = [2, 3, 3, 1, 3, 2, 1, 2]
    while len(ops) < 4:
        kind = rng.choices(kinds, weights=weights)[0]
        if any(k == kind for k, *_ in ops) and kind not in ("pop_i", "remove"):
            continue
        n = len(lst)
        fresh = [x for x in range(10) if x not in lst]
        if kind == "append":
            op = ("append", rng.choice(fresh))
        elif kind == "insert":
            op = ("insert", rng.randint(1, n - 1), rng.choice(fresh))
        elif kind == "pop_i":
            idx = [i for i in range(1, n) if i in lst and lst[i] != i] or list(range(1, n))
            op = ("pop_i", rng.choice(idx))
        elif kind == "pop":
            op = ("pop",)
        elif kind == "remove":
            vals = [x for x in lst if x < n and lst[x] != x] or lst
            op = ("remove", rng.choice(vals))
        elif kind == "del":
            op = ("del", rng.randint(0, n - 1))
        elif kind == "set":
            op = ("set", rng.randint(0, n - 1), rng.choice(fresh))
        else:
            op = ("extend", rng.sample(fresh, 2))
        if len(lst) <= 3 and kind in ("pop_i", "pop", "remove", "del"):
            continue
        _trace_apply(lst, op, set())
        ops.append(op)
    return ops


def _trace_apply(lst: list, op: tuple, slips: set) -> None:
    """Apply ``op`` to ``lst``; ``slips`` names misconceptions to apply instead."""
    kind = op[0]
    if kind == "append":
        lst.append(op[1])
    elif kind == "insert":
        lst.insert(op[1] + 1 if "insert_after" in slips else op[1], op[2])
    elif kind in ("pop_i", "del"):
        i = op[1]
        if "index_is_value" in slips and i in lst:
            lst.remove(i)
        else:
            del lst[i]
    elif kind == "pop":
        lst.pop(0 if "pop_front" in slips else -1)
    elif kind == "remove":
        v = op[1]
        if "value_is_index" in slips and v < len(lst):
            del lst[v]
        else:
            lst.remove(v)
    elif kind == "set":
        lst.insert(op[1], op[2]) if "set_inserts" in slips else lst.__setitem__(op[1], op[2])
    else:
        if "extend_nests" in slips:
            lst.append(list(op[1]))
        else:
            lst.extend(op[1])


@generator(TOPIC, HARD)
def gen_operation_trace(rng: random.Random) -> Question:
    """Trace a sequence of list methods where index-vs-value mix-ups are tempting."""
    var = rng.choice(_NUM_VARS)
    start = rng.sample(range(10), 5)
    ops = _trace_ops(rng, start)
    src = {
        "append": lambda o: f"{var}.append({o[1]})",
        "insert": lambda o: f"{var}.insert({o[1]}, {o[2]})",
        "pop_i": lambda o: f"{var}.pop({o[1]})",
        "pop": lambda o: f"{var}.pop()",
        "remove": lambda o: f"{var}.remove({o[1]})",
        "del": lambda o: f"del {var}[{o[1]}]",
        "set": lambda o: f"{var}[{o[1]}] = {o[2]}",
        "extend": lambda o: f"{var}.extend({o[1]})",
    }
    code = "\n".join([f"{var} = {start}"] + [src[o[0]](o) for o in ops] + [f"print({var})"])

    def trace(slips: set, skip: int | None = None) -> list:
        lst = list(start)
        for o in [o for n, o in enumerate(ops) if n != skip]:
            for attempt in (slips, set()):
                trial = list(lst)
                try:
                    _trace_apply(trial, o, attempt)
                except (ValueError, IndexError):
                    continue
                lst = trial
                break
        return lst

    states, lst = [list(start)], list(start)
    for o in ops:
        _trace_apply(lst, o, set())
        states.append(list(lst))
    if str(lst) != _run(code):
        raise GenerationError("trace model disagrees with Python")
    distractors = [
        trace({"index_is_value", "value_is_index"}),
        trace({"index_is_value"}),
        trace({"value_is_index"}),
        trace({"insert_after"}),
        trace({"extend_nests"}),
        trace({"set_inserts"}),
        trace({"pop_front"}),
        trace(set(), skip=len(ops) - 1),
        trace(set(), skip=0),
        trace(set(), skip=1),
        list(reversed(lst)),
    ]
    used = {o[0] for o in ops}
    rules = []
    if used & {"pop_i", "del"} and "remove" in used:
        rules.append("`pop(i)` and `del` take an INDEX while `remove(x)` takes a VALUE")
    elif used & {"pop_i", "del"}:
        rules.append("`pop(i)` and `del` take an INDEX, not a value")
    elif "remove" in used:
        rules.append("`remove(x)` deletes the first item EQUAL to x, not index x")
    if "insert" in used:
        rules.append("`insert(i, x)` puts x in front of the item at index i")
    why = (
        "Step by step the list goes "
        + " -> ".join(str(s) for s in states)
        + ". "
        + ("Remember: " + "; ".join(rules) + "." if rules else "")
    ).strip()
    return _output(code, HARD, distractors, why, rng)
