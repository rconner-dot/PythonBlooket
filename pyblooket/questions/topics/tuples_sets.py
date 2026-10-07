"""Question generators for the "tuples_sets" topic (Tuples & Sets).

Tuples: indexing and slicing (a slice is still a tuple), packing, unpacking
and the ``a, b = b, a`` swap, immutability (``TypeError`` /
``AttributeError``), the one-item tuple ``(5,)`` vs the plain value ``(5)``,
``+`` and ``*``, ``count``/``index``, lexicographic comparison and ordering,
star unpacking, simultaneous assignment in loops and mutable lists inside
tuples.

Sets: duplicates vanish, ``add``/``discard``/``remove`` (``KeyError``),
membership, ``| & - ^`` and their method names, ``set()`` vs ``{}``,
subset/superset comparisons, the "seen set" idiom and hashability (tuples can
be set elements and dict keys, lists cannot).

Snippets never print a set directly: they print ``sorted(...)``, ``len(...)``
or membership tests, so the output never depends on hash order.
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
    eval_expr,
    generator,
    int_distractors,
    output_question,
    run_code,
    which_expression_question,
)

TOPIC = "tuples_sets"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
TYPE_ERROR = error_choice("TypeError")
INDEX_ERROR = error_choice("IndexError")
VALUE_ERROR = error_choice("ValueError")
KEY_ERROR = error_choice("KeyError")
ATTRIBUTE_ERROR = error_choice("AttributeError")
BLANK = "___"


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _lit(value: object) -> str:
    """``value`` as PEP 8 style source code (strings in double quotes)."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, tuple):
        return _tuple_lit(value)
    if isinstance(value, list):
        return _list_lit(value)
    return repr(value)


def _items(values) -> str:
    return ", ".join(_lit(v) for v in values)


def _tuple_lit(values) -> str:
    values = list(values)
    if len(values) == 1:
        return f"({_items(values)},)"
    return f"({_items(values)})"


def _list_lit(values) -> str:
    return f"[{_items(values)}]"


def _set_lit(values) -> str:
    values = list(values)
    return "{" + _items(values) + "}" if values else "set()"


def _set_display(values) -> str:
    """A set of ints written in sorted order, e.g. ``{1, 4, 9}``."""
    values = sorted(set(values))
    return "{" + ", ".join(str(v) for v in values) + "}" if values else "set()"


def _p(*values: object) -> str:
    """Exactly what ``print(*values)`` shows."""
    return " ".join(str(v) for v in values)


def _run(code: str) -> str:
    """The choice text for what ``code`` prints, or the error it raises."""
    res = run_code(code)
    if res.error:
        return error_choice(res.error)
    return res.output if res.output else NOTHING_PRINTED


def _out(
    code: str,
    difficulty: int,
    distractors: list,
    explanation: str,
    rng: random.Random,
    *,
    allow_error: bool = False,
    prompt: str | None = None,
) -> Question:
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[str(d) for d in distractors],
        explanation=explanation,
        rng=rng,
        prompt=prompt or (PRINT_OR_ERROR if allow_error else PRINT),
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
        distractors=[str(d) for d in distractors],
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _flips(bools: list[bool]) -> list[str]:
    """Wrong answers for a line of printed booleans: flip one at a time, then all."""
    out = []
    for i in range(len(bools)):
        out.append(_p(*[not b if j == i else b for j, b in enumerate(bools)]))
    out.append(_p(*[not b for b in bools]))
    return out


_INT_NAMES = ["nums", "scores", "ages", "temps", "values", "points"]
_WORD_POOLS = {
    "colors": ["red", "blue", "green", "pink", "gold", "gray", "teal", "navy"],
    "fruits": ["apple", "pear", "kiwi", "mango", "lemon", "plum", "fig", "lime"],
    "pets": ["cat", "dog", "fish", "bird", "frog", "hamster", "rabbit", "turtle"],
    "cities": ["Paris", "Rome", "Oslo", "Lima", "Cairo", "Tokyo", "Dublin", "Delhi"],
}
_SHORT_POOLS = ["colors", "fruits"]


def _tuple_data(rng: random.Random, n: int, words: bool | None = None) -> tuple[str, list]:
    """A variable name and ``n`` distinct items (ints or words) for a tuple."""
    if words is None:
        words = rng.random() < 0.5
    if words:
        name = rng.choice(list(_WORD_POOLS))
        return name, rng.sample(_WORD_POOLS[name], n)
    return rng.choice(_INT_NAMES), rng.sample(range(1, 50), n)


def _dup_list(rng: random.Random, distinct: int, extra: int, hi: int = 20) -> list[int]:
    """A shuffled list of ``distinct`` different ints plus ``extra`` repeats."""
    vals = rng.sample(range(1, hi), distinct)
    nums = vals + [rng.choice(vals) for _ in range(extra)]
    rng.shuffle(nums)
    return nums


def _first_order(values: list) -> list:
    """Distinct values in order of first appearance."""
    return list(dict.fromkeys(values))


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_tuple_indexing(rng: random.Random) -> Question:
    """Indexes (positive and negative), slices (still a tuple!) and out of range."""
    n = rng.randint(4, 6)
    name, items = _tuple_data(rng, n)
    t = tuple(items)
    head = f"{name} = {_tuple_lit(items)}\n"
    shape = rng.choices(["pos", "neg", "slice", "out"], weights=[3, 3, 4, 2])[0]
    if shape == "pos":
        i = rng.randint(1, n - 2)
        code = head + f"print({name}[{i}])"
        distractors = [t[i - 1], t[i + 1], INDEX_ERROR, t[-i], t[0]]
        why = (
            f"Tuple indexes start at 0, just like list indexes, so `{name}[{i}]` is the "
            f"{_ordinal(i + 1)} item: {t[i]!r}."
        )
    elif shape == "neg":
        i = rng.randint(1, 3)
        code = head + f"print({name}[-{i}])"
        distractors = [t[-i - 1], t[i], INDEX_ERROR, t[i - 1], t[-i + 1]]
        where = "the last item" if i == 1 else f"the {_ordinal(i)} item from the end"
        why = (
            f"Negative indexes count back from the end, starting at `-1` for the last item, "
            f"so `{name}[-{i}]` is {where}: {t[-i]!r}."
        )
    elif shape == "slice":
        a = rng.randint(0, n - 3)
        length = rng.randint(1, min(3, n - 1 - a))
        b = a + length
        code = head + f"print({name}[{a}:{b}])"
        part = t[a:b]
        distractors = [f"({part[0]!r})", str(part[0])] if length == 1 else []
        distractors += [str(list(part)), str(t[a : b + 1]), str(t[a + 1 : b + 1]), INDEX_ERROR]
        why = (
            f"Slicing a tuple gives a new tuple. `{name}[{a}:{b}]` takes the items at indexes "
            f"{a} up to (but not including) {b}, giving {part}."
        )
        if length == 1:
            why += " A one-item tuple is always shown with a trailing comma."
    else:
        idx = rng.choice([str(n), f"len({name})"])
        code = head + f"print({name}[{idx}])"
        distractors = [t[-1], "None", t[0], TYPE_ERROR, NOTHING_PRINTED]
        why = (
            f"`{name}` has {n} items, so its valid indexes are 0 to {n - 1}. Index {n} is one "
            "past the end, so Python raises `IndexError`."
        )
    return _out(code, EASY, distractors, why, rng, allow_error=True)


_PAIR_NAMES = [("a", "b"), ("x", "y"), ("left", "right"), ("first", "second"), ("p", "q")]
_TRIPLE_NAMES = [("a", "b", "c"), ("x", "y", "z"), ("p", "q", "r")]


@generator(TOPIC, EASY)
def gen_unpacking_swap(rng: random.Random) -> Question:
    """Tuple packing, unpacking by position, the one-line swap and count mismatches."""
    shape = rng.choice(["swap", "swap_value", "unpack", "unpack", "mismatch", "pack"])
    if shape == "swap":
        x, y = rng.choice(_PAIR_NAMES)
        va, vb = rng.sample(range(1, 20), 2)
        code = f"{x} = {va}\n{y} = {vb}\n{x}, {y} = {y}, {x}\nprint({x}, {y})"
        why = (
            f"The right side `{y}, {x}` is packed into the tuple ({vb}, {va}) BEFORE anything "
            f"is assigned, so `{x}` gets {vb} and `{y}` gets {va}: the values are swapped."
        )
        return _out(code, EASY, [_p(va, vb), _p(vb, vb), _p(va, va), (vb, va)], why, rng)
    if shape == "swap_value":
        names = rng.choice(_TRIPLE_NAMES)
        vals = rng.sample(range(1, 20), 3)
        init = dict(zip(names, vals))
        i, j = rng.sample(range(3), 2)
        p, q = names[i], names[j]
        target = rng.choice([p, q])
        other = q if target == p else p
        third = names[3 - i - j]
        code = f"{', '.join(names)} = {', '.join(map(str, vals))}\n{p}, {q} = {q}, {p}"
        distractors = [init[target], init[third], (init[q], init[p]), "None"]
        why = (
            f"Both values on the right are read first (`{q}` is {init[q]}, `{p}` is {init[p]}) "
            f"and then assigned, so `{p}` and `{q}` swap: `{target}` ends up with "
            f"{init[other]}, the old value of `{other}`."
        )
        return _value_question(code, target, EASY, distractors, why, rng)
    if shape == "unpack":
        if rng.random() < 0.5:
            names = ("name", "age", "city")
            vals = (rng.choice(NAMES), rng.randint(9, 17), rng.choice(_WORD_POOLS["cities"]))
            var = rng.choice(["record", "person", "student"])
        else:
            names = ("x", "y", "z")
            vals = tuple(rng.sample(range(1, 20), 3))
            var = rng.choice(["point", "coords", "pos"])
        a, b = rng.sample(range(3), 2)
        code = (
            f"{var} = {_tuple_lit(vals)}\n{', '.join(names)} = {var}\nprint({names[a]}, {names[b]})"
        )
        rev = vals[::-1]
        distractors = [_p(rev[a], rev[b]), _p(vals[b], vals[a]), VALUE_ERROR, vals, _p(*vals)]
        why = (
            f"Unpacking assigns by position: `{names[0]}` gets {vals[0]!r}, `{names[1]}` gets "
            f"{vals[1]!r} and `{names[2]}` gets {vals[2]!r}. Then `print` shows `{names[a]}` "
            f"and `{names[b]}` in that order."
        )
        return _out(code, EASY, distractors, why, rng, allow_error=True)
    if shape == "mismatch":
        x, y, z = rng.choice(_TRIPLE_NAMES)
        vals = rng.sample(range(1, 20), 3)
        if rng.random() < 0.5:
            code = f"{x}, {y} = {_tuple_lit(vals)}\nprint({x}, {y})"
            distractors = [_p(*vals[:2]), _p(vals[0], tuple(vals[1:])), TYPE_ERROR, INDEX_ERROR]
            why = (
                "There are 2 names on the left but 3 values on the right. Unpacking needs the "
                "counts to match exactly, so Python raises `ValueError` (too many values)."
            )
        else:
            code = f"{x}, {y}, {z} = {_tuple_lit(vals[:2])}\nprint({x}, {y}, {z})"
            distractors = [_p(*vals[:2], None), _p(*vals[:2]), TYPE_ERROR, INDEX_ERROR]
            why = (
                "There are 3 names on the left but only 2 values. Unpacking needs the counts to "
                "match exactly; missing names are NOT filled with `None`, Python raises "
                "`ValueError`."
            )
        return _out(code, EASY, distractors, why, rng, allow_error=True)
    vals = rng.sample(range(1, 20), rng.choice([2, 2, 3]))
    var = rng.choice(
        ["pair", "point", "size", "result"]
        if len(vals) == 2
        else ["point", "result", "dims", "rgb"]
    )
    code = f"{var} = {', '.join(map(str, vals))}\nprint({var})"
    why = (
        f"It's the commas, not parentheses, that make a tuple: `{var} = "
        f"{', '.join(map(str, vals))}` packs the values into the tuple {tuple(vals)}, and "
        "printing a tuple shows its parentheses."
    )
    return _out(
        code, EASY, [_p(*vals), list(vals), TYPE_ERROR, vals[0]], why, rng, allow_error=True
    )


@generator(TOPIC, EASY)
def gen_tuple_immutable(rng: random.Random) -> Question:
    """Tuples can't be changed in place, but you can build a new one."""
    shape = rng.choices(["assign", "append", "concat", "convert"], weights=[2, 2, 2, 2])[0]
    words = shape != "convert" and rng.random() < 0.5
    name, items = _tuple_data(rng, 3, words=words)
    t = tuple(items)
    if words:
        new = rng.choice([w for w in _WORD_POOLS[name] if w not in items])
    else:
        new = rng.choice([v for v in range(1, 50) if v not in items])
    head = f"{name} = {_tuple_lit(items)}\n"
    if shape == "assign":
        i = rng.randint(0, 2)
        changed = t[:i] + (new,) + t[i + 1 :]
        code = head + f"{name}[{i}] = {_lit(new)}\nprint({name})"
        distractors = [changed, t, ATTRIBUTE_ERROR, list(changed), INDEX_ERROR]
        why = (
            f"Tuples are immutable: once created their items can't be replaced, so "
            f"`{name}[{i}] = {_lit(new)}` raises `TypeError` and the `print` never runs."
        )
    elif shape == "append":
        code = head + f"{name}.append({_lit(new)})\nprint({name})"
        distractors = [t + (new,), TYPE_ERROR, list(t) + [new], t]
        why = (
            "Tuples can't grow, so they have no `append` method at all. Calling a method that "
            "doesn't exist raises `AttributeError`."
        )
    elif shape == "concat":
        code = head + f"{name} = {name} + ({_lit(new)},)\nprint({name})"
        distractors = [TYPE_ERROR, t + ((new,),), t, ATTRIBUTE_ERROR]
        why = (
            f"`+` doesn't change the old tuple: it builds a NEW tuple {t + (new,)} and the "
            f"name `{name}` is pointed at it. Creating new tuples is always allowed."
        )
    else:
        i = rng.randint(0, 2)
        changed = t[:i] + (new,) + t[i + 1 :]
        if rng.random() < 0.5:
            code = (
                head + f"as_list = list({name})\nas_list[{i}] = {new}\n{name} = tuple(as_list)\n"
                f"print({name})"
            )
            distractors = [TYPE_ERROR, list(changed), t, ATTRIBUTE_ERROR]
            why = (
                f"Lists ARE mutable, so the usual workaround is: copy into a list, change it, "
                f"then build a new tuple with `tuple(as_list)`, giving {changed}."
            )
        else:
            code = head + f"as_list = list({name})\nas_list[{i}] = {new}\nprint(as_list, {name})"
            distractors = [_p(list(changed), changed), TYPE_ERROR, _p(list(t), t), _p(changed, t)]
            why = (
                f"`list({name})` makes a separate, mutable copy. Changing `as_list[{i}]` is fine, "
                f"but the original tuple is untouched: {t}."
            )
    return _out(code, EASY, distractors, why, rng, allow_error=True)


_REPEAT_WORDS = [
    "banana",
    "letter",
    "coffee",
    "bubble",
    "cookie",
    "balloon",
    "kitten",
    "pepper",
    "tomato",
    "rabbit",
    "papaya",
    "cheese",
    "puppy",
    "hello",
    "apple",
    "mammal",
]


@generator(TOPIC, EASY)
def gen_set_duplicates(rng: random.Random) -> Question:
    """A set keeps only one copy of each value."""
    shape = rng.choice(["lens", "sorted", "chars", "literal"])
    name = rng.choice(["nums", "scores", "votes", "codes", "rolls"])
    if shape == "lens":
        nums = _dup_list(rng, rng.randint(3, 4), rng.randint(2, 3))
        n, u = len(nums), len(set(nums))
        code = f"{name} = {nums}\nunique = set({name})\nprint(len({name}), len(unique))"
        distractors = [_p(n, n), _p(u, u), _p(u, n), _p(n, n - u), _p(n, u - 1)]
        why = (
            f"`set({name})` keeps one copy of each value, so the {n} items shrink to the {u} "
            f"distinct values {_set_display(nums)}. The original list is unchanged."
        )
    elif shape == "sorted":
        for _ in range(50):
            nums = _dup_list(rng, rng.randint(3, 4), rng.randint(2, 3))
            if _first_order(nums) != sorted(set(nums)):
                break
        uniq = sorted(set(nums))
        once = [v for v in uniq if nums.count(v) == 1]
        code = f"{name} = {nums}\nprint(sorted(set({name})))"
        distractors = [sorted(nums), _first_order(nums), _set_display(uniq), once]
        why = (
            f"`set({name})` drops the repeats, leaving {len(uniq)} distinct values, and "
            f"`sorted()` returns them as a new list in increasing order: {uniq}."
        )
    elif shape == "chars":
        word = rng.choice(_REPEAT_WORDS)
        d = len(set(word))
        once = sum(1 for c in set(word) if word.count(c) == 1)
        code = f'letters = set("{word}")\nprint(len(letters))'
        distractors = [len(word), d - 1, once, d + 1, len(word) - 1, d + 2, d - 2]
        why = (
            f"`set()` of a string makes a set of its characters, and repeats collapse into one. "
            f"{word!r} has {len(word)} letters but only {d} different ones."
        )
    else:
        nums = _dup_list(rng, rng.randint(3, 4), rng.randint(1, 3), hi=12)
        n, u = len(nums), len(set(nums))
        code = f"{name} = {{{', '.join(map(str, nums))}}}\nprint(len({name}))"
        distractors = [n, n - u, u - 1, u + 1, u + 2, u - 2]
        why = (
            f"The literal lists {n} values, but a set can't hold duplicates, so only the {u} "
            f"distinct values {_set_display(nums)} are kept."
        )
    return _out(code, EASY, distractors, why, rng)


_SET_WORD_VARS = [("pets", "pets"), ("colors", "colors"), ("fruits", "fruits"), ("tags", "colors")]


@generator(TOPIC, EASY)
def gen_set_add_membership(rng: random.Random) -> Question:
    """``add`` ignores values already present; ``in`` checks membership."""
    shape = rng.choice(["adds", "member", "sorted"])
    if shape == "adds":
        var, pool_name = rng.choice(_SET_WORD_VARS)
        pool = _WORD_POOLS[pool_name]
        base = rng.sample(pool, 3)
        others = [w for w in pool if w not in base]
        adds = [rng.choice(base), rng.choice(others)]
        if rng.random() < 0.5:
            adds.append(rng.choice(base + others))
        rng.shuffle(adds)
        code = (
            f"{var} = {_set_lit(base)}\n"
            + "".join(f"{var}.add({_lit(w)})\n" for w in adds)
            + f"print(len({var}))"
        )
        result = len(set(base) | set(adds))
        dups, have = [], set(base)
        for w in adds:
            if w in have:
                dups.append(w)
            have.add(w)
        distractors = [
            len(base) + len(adds),
            len(base),
            result + 1,
            result - 1,
            result + 2,
            result - 2,
        ]
        why = (
            f"A set never stores duplicates: adding {', '.join(repr(w) for w in dups)} (already "
            f"there) changes nothing, so the set grows from {len(base)} to {result} items."
        )
        return _out(code, EASY, distractors, why, rng)
    if shape == "member":
        var, pool_name = rng.choice(_SET_WORD_VARS)
        pool = _WORD_POOLS[pool_name]
        base = rng.sample(pool, rng.randint(2, 3))
        new = rng.choice([w for w in pool if w not in base])
        gone = rng.choice(base)
        ask = rng.choice([gone, gone, new])
        final = (set(base) | {new}) - {gone}
        code = (
            f"{var} = {_set_lit(base)}\n{var}.add({_lit(new)})\n{var}.discard({_lit(gone)})\n"
            f"print({_lit(ask)} in {var}, len({var}))"
        )
        inside, size = ask in final, len(final)
        distractors = [
            _p(not inside, size),
            _p(inside, size + 1),
            _p(not inside, size + 1),
            _p(inside, size - 1),
        ]
        why = (
            f"`add` put {new!r} in and `discard` took {gone!r} out, so {ask!r} is "
            f"{'still' if inside else 'no longer'} a member and the set has {size} items."
        )
        return _out(code, EASY, distractors, why, rng)
    var = rng.choice(["nums", "ids", "seen", "codes"])
    base = rng.sample(range(1, 15), rng.randint(2, 3))
    old = rng.choice(base)
    new = rng.choice([v for v in range(1, 15) if v not in base])
    adds = [old, new]
    rng.shuffle(adds)
    code = (
        f"{var} = {_set_lit(base)}\n"
        + "".join(f"{var}.add({v})\n" for v in adds)
        + f"print(sorted({var}))"
    )
    final = sorted(set(base) | {new})
    distractors = [sorted(base + adds), base + adds, _set_display(final), sorted(base)]
    why = (
        f"{old} is already in the set, so adding it again does nothing; {new} is new and "
        f"gets added. `sorted()` lists the {len(final)} members in order: {final}."
    )
    return _out(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_tuple_concat_repeat(rng: random.Random) -> Question:
    """``+`` joins tuples, ``*`` repeats them; neither adds numbers item by item."""
    shape = rng.choices(["concat", "repeat", "add_one", "add_int"], weights=[3, 3, 2, 2])[0]
    if shape == "concat":
        a = tuple(rng.sample(range(1, 10), 2))
        b = tuple(rng.sample(range(1, 10), rng.randint(1, 2)))
        n1, n2 = rng.choice([("a", "b"), ("front", "back"), ("first", "second"), ("left", "right")])
        code = f"{n1} = {_tuple_lit(a)}\n{n2} = {_tuple_lit(b)}\nprint({n1} + {n2})"
        summed = tuple(x + y for x, y in zip(a, b))
        distractors = [(a, b), summed, list(a + b), TYPE_ERROR, b + a]
        why = (
            f"`+` on two tuples joins (concatenates) them into one new tuple: {a + b}. It "
            "never adds the numbers inside."
        )
    elif shape == "repeat":
        k = rng.randint(2, 3)
        name = rng.choice(["t", "pattern", "row", "pair"])
        t = tuple(rng.sample(range(0, 10), rng.choice([1, 2, 2])))
        code = f"{name} = {_tuple_lit(t)}\nprint({name} * {k})"
        times = tuple(x * k for x in t)
        each = tuple(x for x in t for _ in range(k))
        distractors = [times, (t,) * k, each, list(t * k), TYPE_ERROR]
        why = (
            f"`{name} * {k}` repeats the WHOLE tuple {k} times, end to end, giving {t * k}. "
            "The numbers inside are not multiplied."
        )
    elif shape == "add_one":
        t = tuple(rng.sample(range(1, 10), 2))
        x = rng.choice([v for v in range(1, 10) if v not in t])
        name = rng.choice(["t", "data", "nums", "point"])
        code = f"{name} = {_tuple_lit(t)}\n{name} = {name} + ({x},)\nprint({name}, len({name}))"
        distractors = [_p(t + ((x,),), 3), TYPE_ERROR, _p(t, 2), _p(t + (x,), 2)]
        why = (
            f"`({x},)` is a one-item tuple, so `+` joins it on the end and the name is pointed "
            f"at the new 3-item tuple {t + (x,)}."
        )
    else:
        t = tuple(rng.sample(range(1, 10), 2))
        x = rng.choice([v for v in range(1, 10) if v not in t])
        name = rng.choice(["t", "data", "nums", "point"])
        code = f"{name} = {_tuple_lit(t)}\nprint({name} + {x})"
        distractors = [t + (x,), tuple(v + x for v in t), t, INDEX_ERROR]
        why = (
            f"`+` can only join a tuple to another tuple. {x} is an int, so Python raises "
            f"`TypeError`; you would need `{name} + ({x},)`."
        )
    return _out(code, EASY, distractors, why, rng, allow_error=True)


# ==========================================================================
# MEDIUM
# ==========================================================================

_SINGLE_LOOPS = [
    ("drinks", "drink", ["tea", "milk", "soda", "juice", "cocoa"]),
    ("snacks", "snack", ["chips", "nuts", "fruit", "corn"]),
    ("pets", "pet", ["cat", "dog", "fish", "bird"]),
]


@generator(TOPIC, MEDIUM)
def gen_single_item_tuple(rng: random.Random) -> Question:
    """``(5)`` is just 5 in brackets; only the trailing comma in ``(5,)`` makes a tuple."""
    shape = rng.choice(["multiply", "len_word", "len_int", "types", "loop"])
    comma = rng.random() < 0.5
    if shape == "multiply":
        n = rng.randint(2, 9)
        k = rng.randint(2, 3)
        a, b = rng.choice([("a", "b"), ("x", "y"), ("p", "q"), ("first", "second")])
        code = f"{a} = ({n})\n{b} = ({n},)\nprint({a} * {k}, {b} * {k})"
        tup = (n,) * k
        distractors = [_p(tup, tup), _p(n * k, n * k), _p(n * k, (n * k,)), _p((n * k,), tup)]
        why = (
            f"Brackets alone don't make a tuple: `({n})` is just the int {n}, so `{a} * {k}` "
            f"is {n * k}. The trailing comma in `({n},)` makes a one-item tuple, and `*` "
            f"repeats it: {tup}."
        )
        return _out(code, MEDIUM, distractors, why, rng, allow_error=True)
    if shape == "len_word":
        var, pool = rng.choice(
            [
                ("names", NAMES),
                ("fruits", _WORD_POOLS["fruits"][:6]),
                ("cities", _WORD_POOLS["cities"]),
            ]
        )
        word = rng.choice([w for w in pool if len(w) >= 3])
        lit = f"({_lit(word)},)" if comma else f"({_lit(word)})"
        code = f"{var} = {lit}\nprint(len({var}))"
        L = len(word)
        if comma:
            distractors = [L, 2, TYPE_ERROR, 0]
            why = (
                f"The trailing comma makes `{var}` a tuple holding one string, so its length "
                "is 1 (the number of items, not letters)."
            )
        else:
            distractors = [1, TYPE_ERROR, L + 2, 2]
            why = (
                f"Without a trailing comma, `({_lit(word)})` is just the string {word!r} in "
                f"brackets, so `len` counts its {L} characters. A one-item tuple needs `,`."
            )
        return _out(code, MEDIUM, distractors, why, rng, allow_error=True)
    if shape == "len_int":
        n = rng.randint(2, 9)
        var = rng.choice(["count", "total", "size", "x"])
        code = f"{var} = ({n}{',' if comma else ''})\nprint(len({var}))"
        if comma:
            distractors = [TYPE_ERROR, n, 2, 0]
            why = f"`({n},)` is a tuple with ONE item, so `len` gives 1."
        else:
            distractors = [1, n, ATTRIBUTE_ERROR, 0]
            why = (
                f"`({n})` is just the int {n} in brackets, not a tuple, and ints have no "
                f"length, so `len` raises `TypeError`. A one-item tuple needs a comma: `({n},)`."
            )
        return _out(code, MEDIUM, distractors, why, rng, allow_error=True)
    if shape == "types":
        if rng.random() < 0.5:
            val, inner = str(rng.randint(2, 9)), "<class 'int'>"
        else:
            word = rng.choice(["hi", "ok", "yes", "go"])
            val, inner = f'"{word}"', "<class 'str'>"
        a, b = rng.choice([("a", "b"), ("x", "y"), ("p", "q")])
        tup = "<class 'tuple'>"
        code = f"{a} = ({val})\n{b} = ({val},)\nprint(type({a}), type({b}))"
        distractors = [_p(tup, tup), _p(inner, inner), _p(tup, inner), _p(inner, "<class 'list'>")]
        why = (
            f"Brackets around a single value just group it, so `{a}` is the plain value "
            f"{val}. Only the trailing comma in `({val},)` makes `{b}` a tuple."
        )
        return _out(code, MEDIUM, distractors, why, rng, allow_error=True)
    plural, single, pool = rng.choice(_SINGLE_LOOPS)
    word = rng.choice(pool)
    lit = f"({_lit(word)},)" if comma else f"({_lit(word)})"
    code = f"{plural} = {lit}\nfor {single} in {plural}:\n    print({single})"
    chars = "\n".join(word)
    if comma:
        distractors = [chars, f"({word!r},)", word[0], TYPE_ERROR]
        why = (
            f"`{lit}` is a tuple with ONE item (the comma makes it a tuple), so the loop runs "
            f"once and prints {word!r}."
        )
    else:
        distractors = [word, f"({word!r})", word[0], TYPE_ERROR]
        why = (
            f"Without a comma, `{lit}` is just the string {word!r}, and looping over a string "
            f"visits each character, printing {len(word)} lines."
        )
    return _out(code, MEDIUM, distractors, why, rng, allow_error=True)


_SET_NAME_PAIRS = [("a", "b"), ("x", "y"), ("mine", "yours"), ("club", "team"), ("left", "right")]
_SET_OPS = {
    "|": ("union", "every value that is in EITHER set (or both)"),
    "&": ("intersection", "only the values that are in BOTH sets"),
    "-": ("difference", "the values in the first set that are NOT in the second"),
    "^": ("symmetric_difference", "the values in exactly ONE of the sets, not both"),
}
_OP_CONFUSIONS = {
    "|": ["+", "&", "^", "-"],
    "&": ["^", "|", "-", "rev"],
    "-": ["rev", "^", "&", "|"],
    "^": ["|", "&", "-", "rev"],
}


def _two_sets(rng: random.Random) -> tuple[list[int], list[int]]:
    """Two overlapping sets of small ints, each with some values of its own."""
    n_common, n_a, n_b = rng.randint(1, 2), rng.randint(2, 3), rng.randint(1, 3)
    vals = rng.sample(range(1, 13), n_common + n_a + n_b)
    common, a_only, b_only = (
        vals[:n_common],
        vals[n_common : n_common + n_a],
        vals[n_common + n_a :],
    )
    a, b = common + a_only, common + b_only
    rng.shuffle(a)
    rng.shuffle(b)
    return a, b


def _apply(op: str, a: list[int], b: list[int]) -> list[int]:
    sa, sb = set(a), set(b)
    return {
        "|": lambda: sorted(sa | sb),
        "&": lambda: sorted(sa & sb),
        "-": lambda: sorted(sa - sb),
        "^": lambda: sorted(sa ^ sb),
        "rev": lambda: sorted(sb - sa),
        "+": lambda: sorted(a + b),
    }[op]()


@generator(TOPIC, MEDIUM)
def gen_set_operations(rng: random.Random) -> Question:
    """Union, intersection, difference and symmetric difference (operators and methods)."""
    a, b = _two_sets(rng)
    A, B = rng.choice(_SET_NAME_PAIRS)
    op = rng.choice(list(_SET_OPS))
    method, desc = _SET_OPS[op]
    result = _apply(op, a, b)
    setup = f"{A} = {_set_lit(a)}\n{B} = {_set_lit(b)}"
    style = rng.choices(["output", "which", "blank"], weights=[3, 2, 2])[0]
    if style == "output":
        use_method = rng.random() < 0.3
        expr = f"{A}.{method}({B})" if use_method else f"{A} {op} {B}"
        code = f"{setup}\nprint(sorted({expr}))"
        distractors = [_apply(c, a, b) for c in _OP_CONFUSIONS[op]]
        same = f" (the same as `{A} {op} {B}`)" if use_method else ""
        why = f"`{expr}`{same} keeps {desc}: {result}. `sorted()` returns them as a list."
        return _out(code, MEDIUM, distractors, why, rng)
    if style == "which":
        wrong = [f"sorted({A} {o} {B})" for o in _OP_CONFUSIONS[op] if o in _SET_OPS]
        wrong.append(f"sorted({B} - {A})")
        rng.shuffle(wrong)
        why = f"`{A} {op} {B}` keeps {desc}, which is {result}."
        return which_expression_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=f"Which expression evaluates to `{result}`?",
            setup=setup,
            target=result,
            correct_expr=f"sorted({A} {op} {B})",
            wrong_exprs=wrong,
            explanation=why,
            rng=rng,
        )
    template = f"{setup}\nprint(sorted({A}.{BLANK}({B})))"
    target = _run(template.replace(BLANK, method))
    cands = [_SET_OPS[o][0] for o in _OP_CONFUSIONS[op] if o in _SET_OPS]
    wrong = [c for c in cands if _run(template.replace(BLANK, c)) != target]
    why = f"`{A}.{method}({B})` (the method form of `{A} {op} {B}`) keeps {desc}: {result}."
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which method fills the blank (`{BLANK}`) so that the code prints `{target}`?",
        correct=method,
        distractors=wrong,
        explanation=why,
        rng=rng,
        code=template,
    )


_COUNT_POOLS = [
    ("votes", ["yes", "no", "maybe", "skip"]),
    ("moves", ["up", "down", "left", "right"]),
    ("answers", ["A", "B", "C", "D"]),
    ("days", ["Mon", "Tue", "Wed", "Fri"]),
]


@generator(TOPIC, MEDIUM)
def gen_count_index(rng: random.Random) -> Question:
    """``count`` counts every match, ``index`` finds the FIRST one (or raises)."""
    if rng.random() < 0.5:
        name = rng.choice(["rolls", "nums", "scores", "codes"])
        pool = rng.sample(range(1, 10), 4)
    else:
        name, pool = rng.choice(_COUNT_POOLS)
        pool = rng.sample(pool, 4)
    vals, missing = pool[:3], pool[3]
    n = rng.randint(6, 7)
    items = vals + [rng.choice(vals) for _ in range(n - 3)]
    rng.shuffle(items)
    t = tuple(items)
    repeated = [v for v in vals if t.count(v) >= 2]
    if not repeated:
        raise GenerationError("no repeated value")
    x = rng.choice(repeated)
    c, i = t.count(x), t.index(x)
    spots = [j for j, v in enumerate(t) if v == x]
    head = f"{name} = {_tuple_lit(items)}\n"
    shape = rng.choices(["count_index", "index", "missing", "next"], weights=[3, 2, 3, 2])[0]
    if shape == "count_index":
        code = head + f"print({name}.count({_lit(x)}), {name}.index({_lit(x)}))"
        distractors = [
            _p(i, c),
            _p(c, spots[-1]),
            _p(c, i + 1),
            _p(c - 1, i),
            _p(c, spots[1]),
            _p(c + 1, i),
            _p(i + 1, c),
            _p(c, i + 2),
        ]
        why = (
            f"`count` counts EVERY occurrence of {x!r} ({c}), while `index` returns the "
            f"position of the FIRST one, counting from 0: {i}."
        )
    elif shape == "index":
        code = head + f"print({name}.index({_lit(x)}))"
        distractors = [spots[-1], i + 1, spots[1], c, VALUE_ERROR, i + 2, INDEX_ERROR]
        why = (
            f"{x!r} appears at indexes {', '.join(map(str, spots))}, but `index` stops at the "
            f"FIRST match, so it returns {i}."
        )
    elif shape == "missing":
        if rng.random() < 0.6:
            code = head + f"print({name}.index({_lit(missing)}))"
            distractors = ["-1", "None", "0", INDEX_ERROR, KEY_ERROR]
            why = (
                f"{missing!r} isn't in the tuple. Unlike `str.find`, `index` never returns -1: "
                "it raises `ValueError` when the value is missing."
            )
        else:
            code = head + f"print({name}.count({_lit(missing)}))"
            distractors = [VALUE_ERROR, "-1", "None", "1"]
            why = (
                f"{missing!r} isn't in the tuple, so it occurs 0 times. `count` simply returns "
                "0; only `index` raises an error for a missing value."
            )
    else:
        firsts = [v for v in repeated if t.index(v) < n - 1]
        if not firsts:
            raise GenerationError("no usable value")
        x = rng.choice(firsts)
        i = t.index(x)
        spots = [j for j, v in enumerate(t) if v == x]
        pos = rng.choice(["i", "spot"])
        code = head + f"{pos} = {name}.index({_lit(x)})\nprint({name}[{pos} + 1])"
        last_next = t[spots[-1] + 1] if spots[-1] + 1 < n else INDEX_ERROR
        distractors = [
            last_next,
            t[i],
            t[i + 2] if i + 2 < n else INDEX_ERROR,
            t[i - 1],
            i + 1,
            VALUE_ERROR,
            INDEX_ERROR,
            i + 2,
        ]
        why = (
            f"`index` finds the FIRST {x!r}, at index {i}, so `{name}[{i + 1}]` is the item "
            f"right after it: {t[i + 1]!r}."
        )
    return _out(code, MEDIUM, distractors, why, rng, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_tuple_comparison(rng: random.Random) -> Question:
    """Tuples compare item by item from the left; the first difference decides."""
    shape = rng.choice(["max", "length", "which"])
    if shape == "max":
        a1 = rng.randint(1, 8)
        if rng.random() < 0.35:
            x, y = rng.sample(range(1, 10), 2)
            p, q = (a1, x), (a1, y)
        else:
            b1 = a1 + rng.randint(1, 3)
            small = rng.randint(0, 5)
            p, q = (a1, small + (b1 - a1) + rng.randint(2, 4)), (b1, small)
        if rng.random() < 0.5:
            p, q = q, p
        n1, n2 = rng.choice([("p", "q"), ("first", "second"), ("v1", "v2"), ("home", "away")])
        code = (
            f"{n1} = {_tuple_lit(p)}\n{n2} = {_tuple_lit(q)}\nprint({n1} < {n2}, max({n1}, {n2}))"
        )
        lt, mx, mn = p < q, max(p, q), min(p, q)
        elem = tuple(map(max, p, q))
        distractors = [_p(not lt, mn), _p(lt, elem), _p(not lt, mx), _p(lt, mn)]
        if p[0] != q[0]:
            why = (
                "Tuples compare item by item from the left and the first difference decides. "
                f"The first items already differ ({p[0]} vs {q[0]}), so `{n1} < {n2}` is {lt} "
                f"and `max` returns {mx}; the second items are never looked at."
            )
        else:
            why = (
                "Tuples compare item by item from the left. The first items tie "
                f"({p[0]}), so the second items decide ({p[1]} vs {q[1]}): `{n1} < {n2}` is "
                f"{lt} and `max` returns {mx}."
            )
        return _out(code, MEDIUM, distractors, why, rng)
    if shape == "length":
        a, b, c = rng.randint(1, 9), rng.randint(1, 8), rng.randint(0, 9)
        pool = [
            ("a < b", True),
            ("c < b", False),
            ("b < c", True),
            ("b < a", False),
            ("a < c", True),
        ]
        e1, e2 = rng.sample(pool, 2)
        code = (
            f"a = {_tuple_lit((a, b))}\nb = {_tuple_lit((a, b, c))}\nc = {_tuple_lit((a, b + 1))}\n"
            f"print({e1[0]}, {e2[0]})"
        )
        correct = [e1[1], e2[1]]
        why = (
            "Tuples compare like words in a dictionary: item by item, first difference wins. "
            "`a` is the start of `b`, so the shorter `a < b`. `c` differs from both at index 1 "
            f"({b + 1} > {b}), so `a < c` and `b < c`, even though `b` is longer."
        )
        return _out(code, MEDIUM, _flips(correct), why, rng)
    x = rng.randint(1, 8)
    y = rng.choice([v for v in range(3, 10) if v != x])
    p, q, r = (x, y), (x, y + rng.randint(1, 3)), (x + rng.randint(1, 2), rng.randint(0, y - 1))
    setup = f"p = {_tuple_lit(p)}\nq = {_tuple_lit(q)}\nr = {_tuple_lit(r)}"
    exprs = [
        "p < q",
        "q < p",
        "p < r",
        "r < p",
        "q < r",
        "r < q",
        "p > q",
        "r > q",
        f"p == {_tuple_lit((y, x))}",
        "max(p, r) == r",
        "min(q, r) == r",
    ]
    truths = {e: eval_expr(e, setup) for e in exprs}
    true_ones = [e for e in exprs if truths[e] is True]
    traps = [e for e in ["r < p", "r < q", "q < p", "min(q, r) == r"] if truths[e] is False]
    others = [e for e in exprs if truths[e] is False and e not in traps]
    rng.shuffle(traps)
    rng.shuffle(others)
    correct = rng.choice(true_ones)
    why = (
        f"Compare from the left: `{correct}` is True. `r` has the biggest FIRST item "
        f"({r[0]}), so it is the largest tuple even though its second item ({r[1]}) is small; "
        f"`p` and `q` tie at index 0 so index 1 decides ({p[1]} < {q[1]})."
    )
    return which_expression_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Which expression evaluates to `True`?",
        setup=setup,
        target=True,
        correct_expr=correct,
        wrong_exprs=traps[:2] + others,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_empty_set_vs_dict(rng: random.Random) -> Question:
    """``{}`` is an empty dict; an empty set is written ``set()``."""
    shape = rng.choice(["add", "set_add", "types", "equal"])
    var = rng.choice(["seen", "tags", "ids", "visited", "used"])
    if shape == "add":
        x = rng.randint(1, 20)
        code = f"{var} = {{}}\n{var}.add({x})\nprint(len({var}))"
        distractors = ["1", TYPE_ERROR, "0", KEY_ERROR]
        why = (
            "`{}` creates an empty DICTIONARY, not an empty set, and dicts have no `add` "
            "method, so Python raises `AttributeError`. Write `set()` for an empty set."
        )
        return _out(code, MEDIUM, distractors, why, rng, allow_error=True)
    if shape == "set_add":
        vals = rng.sample(range(1, 20), rng.randint(2, 3))
        adds = vals + [rng.choice(vals)] * rng.randint(1, 2)
        rng.shuffle(adds)
        code = (
            f"{var} = set()\n" + "".join(f"{var}.add({v})\n" for v in adds) + f"print(len({var}))"
        )
        distractors = [len(adds), ATTRIBUTE_ERROR, len(vals) - 1, len(adds) - 1, TYPE_ERROR]
        why = (
            f"`set()` really is an empty set, so `add` works. {len(adds)} values are added but "
            f"repeats are ignored, leaving {len(vals)} distinct values."
        )
        return _out(code, MEDIUM, distractors, why, rng, allow_error=True)
    if shape == "types":
        n = rng.randint(1, 9)
        pair = [("{}", "dict"), rng.choice([("set()", "set"), (f"{{{n}}}", "set")])]
        rng.shuffle(pair)
        (l1, t1), (l2, t2) = pair
        code = f"a = {l1}\nb = {l2}\nprint(type(a), type(b))"
        cls = {"dict": "<class 'dict'>", "set": "<class 'set'>"}
        combos = [_p(cls[u], cls[v]) for u in ("set", "dict") for v in ("set", "dict")]
        distractors = [c for c in combos if c != _p(cls[t1], cls[t2])]
        distractors.append(_p("<class 'tuple'>", cls[t2]))
        why = (
            "Empty braces `{}` make an empty dict (dicts came first). Braces WITH values, like "
            f"`{{{n}}}`, make a set, and `set()` is the way to make an empty set."
        )
        return _out(code, MEDIUM, distractors, why, rng, allow_error=True)
    pool = [("len(a) == len(b)", True), ("a == b", False), ("type(a) == type(b)", False)]
    e1, e2 = rng.sample(pool, 2)
    a_name, b_name = "a", "b"
    code = f"{a_name} = {{}}\n{b_name} = set()\nprint({e1[0]}, {e2[0]})"
    why = (
        "Both are empty, so their lengths match, but `{}` is an empty dict while `set()` is "
        "an empty set. A dict never equals a set, and their types differ."
    )
    return _out(code, MEDIUM, _flips([e1[1], e2[1]]), why, rng)


@generator(TOPIC, MEDIUM)
def gen_remove_vs_discard(rng: random.Random) -> Question:
    """``remove`` raises KeyError for a missing value; ``discard`` silently does nothing."""
    var = rng.choice(["s", "ids", "seats", "codes", "nums"])
    current = set(rng.sample(range(1, 10), 4))
    start = sorted(current)
    rng.shuffle(start)
    outside = [v for v in range(1, 10) if v not in current]
    raising = rng.random() < 0.45
    gone, keep_out = rng.sample(sorted(current), 2)
    miss1, miss2, new = rng.sample(outside, 3)
    ops = [("discard", miss1), ("remove", gone)]
    if raising:
        ops.append(("remove", miss2))
    else:
        ops.append(rng.choice([("add", new), ("discard", keep_out), ("add", keep_out)]))
    rng.shuffle(ops)
    lines = [f"{var} = {_set_lit(start)}"] + [f"{var}.{m}({v})" for m, v in ops]
    printer = f"print(sorted({var}))"
    code = "\n".join(lines + [printer])
    lenient = code.replace(f".remove({miss2})", f".discard({miss2})")
    skips = []
    for i in range(1, len(lines)):
        skips.append(_run("\n".join(lines[:i] + lines[i + 1 :] + [printer])))
    if raising:
        distractors = [_run(lenient), VALUE_ERROR, *skips, sorted(current), INDEX_ERROR]
        why = (
            f"`discard` quietly ignores a value that isn't there, but `remove` insists: "
            f"`{var}.remove({miss2})` raises `KeyError` because {miss2} was never in the set."
        )
    else:
        distractors = [KEY_ERROR, *skips, sorted(current), VALUE_ERROR]
        why = (
            f"`{var}.discard({miss1})` does nothing because {miss1} isn't there (no error), "
            f"and `remove({gone})` works because {gone} IS there. Only `remove` of a missing "
            "value raises `KeyError`."
        )
    return _out(code, MEDIUM, distractors, why, rng, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_loop_unpacking(rng: random.Random) -> Question:
    """Unpacking tuples in a ``for`` loop header."""
    shape = rng.choice(["filter", "best", "fix"])
    if shape == "fix":
        pairs = [tuple(rng.sample(range(1, 10), 2)) for _ in range(3)]
        if all(a < b for a, b in pairs) or all(a > b for a, b in pairs):
            pairs[0] = pairs[0][::-1]
        code = (
            f"pairs = {_list_lit(pairs)}\nfixed = []\nfor low, high in pairs:\n"
            "    if low > high:\n        low, high = high, low\n"
            "    fixed.append((low, high))\nprint(fixed)"
        )
        correct = [(min(p), max(p)) for p in pairs]
        distractors = [
            [p[::-1] for p in pairs],
            pairs,
            [(max(p), min(p)) for p in pairs],
            [p[::-1] if p[0] < p[1] else p for p in pairs],
        ]
        why = (
            "Each pair is unpacked into `low` and `high`; when they're in the wrong order the "
            f"swap `low, high = high, low` fixes them, so every pair ends up ascending: {correct}."
        )
        return _out(code, MEDIUM, distractors, why, rng)
    names = rng.sample(NAMES, rng.randint(3, 4))
    if shape == "filter":
        scores = rng.sample(range(2, 10), len(names))
        k = rng.choice(sorted(scores)[1:-1])
        records = list(zip(names, scores))
        op = rng.choice([">=", ">", "<=", "<"])
        flip = {">=": ">", ">": ">=", "<=": "<", "<": "<="}[op]
        test = {
            ">=": lambda s: s >= k,
            ">": lambda s: s > k,
            "<=": lambda s: s <= k,
            "<": lambda s: s < k,
        }
        picked = [n for n, s in records if test[op](s)]
        code = (
            f"results = {_list_lit(records)}\nchosen = []\nfor name, score in results:\n"
            f"    if score {op} {k}:\n        chosen.append(name)\nprint(chosen)"
        )
        distractors = [
            [n for n, s in records if test[flip](s)],
            [s for n, s in records if test[op](s)],
            [n for n, s in records if not test[op](s)],
            names,
        ]
        why = (
            "Each `(name, score)` tuple is unpacked in the loop header. The names whose score "
            f"passes `score {op} {k}` are {picked}; note the score of exactly {k} is "
            f"{'kept' if test[op](k) else 'left out'} by `{op}`."
        )
        return _out(code, MEDIUM, distractors, why, rng)
    top = rng.randint(7, 9)
    lows = rng.sample(range(2, top), len(names) - 2)
    scores = lows + [top, top]
    rng.shuffle(scores)
    records = list(zip(names, scores))
    code = (
        f'results = {_list_lit(records)}\nbest_name, best = "", 0\n'
        "for name, score in results:\n    if score > best:\n"
        "        best_name, best = name, score\nprint(best_name, best)"
    )
    tied = [n for n, s in records if s == top]
    low_name, low = min(records, key=lambda r: r[1])
    distractors = [
        _p(tied[-1], top),
        _p(records[-1][0], records[-1][1]),
        _p(low_name, low),
        _p(records[0][0], records[0][1]),
        *(_p(nm, sc) for nm, sc in records),
        _p(tied[0], 0),
        _p('""', 0),
    ]
    why = (
        f"{tied[0]} and {tied[1]} both have {top}, but the test is `score > best`: when "
        f"{tied[1]} comes along, {top} > {top} is False, so the FIRST top scorer, {tied[0]}, stays."
    )
    return _out(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_subset_equality(rng: random.Random) -> Question:
    """Subset/superset comparisons and order-free set equality."""
    shape = rng.choice(["subset", "subset", "order"])
    if shape == "order":
        vals = rng.sample(range(1, 10), 3)
        other = vals[1:] + vals[:1] if rng.random() < 0.5 else vals[::-1]
        kinds = rng.sample(["set", "tuple", "list"], 2)
        if "set" not in kinds:
            kinds[0] = "set"
        lit = {"set": _set_lit, "tuple": _tuple_lit, "list": _list_lit}
        parts = [f"{lit[k](vals)} == {lit[k](other)}" for k in kinds]
        code = f"print({parts[0]}, {parts[1]})"
        correct = [k == "set" for k in kinds]
        why = (
            "Sets have no order, so two sets with the same members are equal however they are "
            "written. Tuples and lists are sequences: same items in a different order are NOT "
            "equal."
        )
        return _out(code, MEDIUM, _flips(correct), why, rng)
    A, B = rng.choice([("a", "b"), ("mine", "yours"), ("team", "club"), ("x", "y")])
    big = rng.sample(range(1, 10), rng.randint(4, 5))
    if rng.random() < 0.3:
        small = big[1:] + big[:1]
        relation = "equal"
    else:
        small = rng.sample(big, rng.randint(2, len(big) - 1))
        relation = "proper"
    if rng.random() < 0.5:
        a_vals, b_vals, a_small = small, big, True
    else:
        a_vals, b_vals, a_small = big, small, False
    S, L = (A, B) if a_small else (B, A)
    pool = [
        f"{S} <= {L}",
        f"{S} < {L}",
        f"{L} <= {S}",
        f"{L} > {S}",
        f"{S}.issubset({L})",
        f"{L}.issuperset({S})",
        f"{A} == {B}",
        f"{L} < {S}",
    ]
    exprs = rng.sample(pool, 3)
    setup = f"{A} = {_set_lit(a_vals)}\n{B} = {_set_lit(b_vals)}"
    code = f"{setup}\nprint({', '.join(exprs)})"
    correct = [bool(eval_expr(e, setup)) for e in exprs]
    if relation == "equal":
        why = (
            f"`{A}` and `{B}` hold exactly the same values (order doesn't matter), so they are "
            "equal and each is a subset (`<=`, `issubset`) and superset of the other, but "
            "neither is a PROPER subset (`<`), which needs the other to have something extra."
        )
    else:
        why = (
            f"Every value of `{S}` is also in `{L}`, which has extra values. So `{S} <= {L}` "
            f"(`{S}.issubset({L})`), `{L}.issuperset({S})` and the proper-subset test "
            f"`{S} < {L}` are all True, while `{L} <= {S}` and `{A} == {B}` are False."
        )
    return _out(code, MEDIUM, _flips(correct), why, rng)


# ==========================================================================
# HARD
# ==========================================================================

_STAR_PATTERNS = [
    (["first"], "rest", []),
    ([], "rest", ["last"]),
    (["first"], "middle", ["last"]),
    (["a", "b"], "rest", []),
    (["head"], "body", ["tail"]),
    (["low"], "mid", ["high"]),
]


@generator(TOPIC, HARD)
def gen_star_unpacking(rng: random.Random) -> Question:
    """``a, *b, c = ...``: the starred name always gets a LIST (possibly empty)."""
    shape = rng.choices(["pattern", "value", "short", "string", "rotate"], weights=[3, 2, 2, 2, 2])[
        0
    ]
    if shape in ("pattern", "value"):
        pre, star, post = rng.choice(_STAR_PATTERNS)
        words = rng.random() < 0.3
        if words:
            name = rng.choice(_SHORT_POOLS)
            items = rng.sample(_WORD_POOLS[name], 4)
        else:
            name, items = _tuple_data(rng, rng.randint(4, 6), words=False)
        n = len(items)
        mid = items[len(pre) : n - len(post)]
        lhs = ", ".join(pre + [f"*{star}"] + post)
        code = f"{name} = {_tuple_lit(items)}\n{lhs} = {name}"
        why = (
            f"The plain names take one item each from the ends; the starred `{star}` collects "
            f"everything left over, and it is always a LIST: {mid}."
        )
        if shape == "value":
            distractors = [tuple(mid), items[len(pre) :], mid[0], list(items)]
            if post:
                distractors.insert(2, items[len(pre) : n - len(post) + 1])
            distractors = [repr(d) for d in distractors]
            return _value_question(code, star, HARD, distractors, why, rng)
        pre_v, post_v = items[: len(pre)], items[n - len(post) :]
        code += f"\nprint({', '.join(pre + [star] + post)})"
        distractors = [
            _p(*pre_v, tuple(mid), *post_v),
            VALUE_ERROR,
            _p(*pre_v, mid[0], *post_v),
            _p(*pre_v, items[len(pre) :], *post_v),
            _p(*pre_v, *mid, *post_v),
        ]
        return _out(code, HARD, distractors, why, rng, allow_error=True)
    if shape == "short":
        size = rng.choice([1, 2, 2, 3])
        vals = rng.sample(range(1, 20), size)
        name = rng.choice(["data", "values", "nums"])
        code = (
            f"{name} = {_tuple_lit(vals)}\nfirst, *middle, last = {name}\n"
            "print(first, middle, last)"
        )
        if size == 3:
            x, y, z = vals
            distractors = [_p(x, y, z), _p(x, (y,), z), VALUE_ERROR, _p(x, [], z)]
            why = (
                f"`first` and `last` take {x} and {z}; `*middle` collects what's left as a "
                f"list: [{y}]."
            )
        elif size == 2:
            x, y = vals
            distractors = [VALUE_ERROR, _p(x, None, y), _p(x, (), y), _p(x, [y], y)]
            why = (
                f"`first` and `last` use up both values ({x} and {y}), so the starred "
                "`middle` gets nothing left over: an empty list `[]`, not an error."
            )
        else:
            (x,) = vals
            distractors = [_p(x, [], x), _p(x, [], None), _p(x, None, None), TYPE_ERROR]
            why = (
                "A starred name can be empty, but `first` and `last` each need a value of their "
                "own. With only one value to unpack, Python raises `ValueError`."
            )
        return _out(code, HARD, distractors, why, rng, allow_error=True)
    if shape == "string":
        word = rng.choice(["code", "loop", "snake", "pixel", "tiger", "lemon", "quest", "python"])
        pre, star, post = rng.choice(_STAR_PATTERNS[:3])
        lhs = ", ".join(pre + [f"*{star}"] + post)
        code = f'{lhs} = "{word}"\nprint({", ".join(pre + [star] + post)})'
        n = len(word)
        pre_v, post_v = list(word[: len(pre)]), list(word[n - len(post) :])
        mid = word[len(pre) : n - len(post)]
        distractors = [
            _p(*pre_v, mid, *post_v),
            _p(*pre_v, tuple(mid), *post_v),
            _p(*pre_v, [mid], *post_v),
            VALUE_ERROR,
        ]
        why = (
            f"Unpacking works on any iterable, and a string iterates over its characters. The "
            f"starred `{star}` gathers the leftover characters into a list: {list(mid)}."
        )
        return _out(code, HARD, distractors, why, rng, allow_error=True)
    vals = rng.sample(range(1, 10), 4)
    name = rng.choice(["nums", "queue", "order", "turns"])
    t = tuple(vals)
    right, left = (t[-1],) + t[:-1], t[1:] + t[:1]
    if rng.random() < 0.5:
        code = (
            f"{name} = {_tuple_lit(vals)}\n*front, last = {name}\n"
            f"{name} = (last, *front)\nprint({name})"
        )
        distractors = [(t[-1], list(t[:-1])), left, t[::-1], t]
        why = (
            f"`*front, last` gives `last` = {t[-1]} and `front` = {list(t[:-1])}. Inside a "
            f"tuple display, `*front` spreads the list back out, so the result is {right}: "
            "everything rotated one step right."
        )
    else:
        code = (
            f"{name} = {_tuple_lit(vals)}\nfirst, *rest = {name}\n"
            f"{name} = (*rest, first)\nprint({name})"
        )
        distractors = [(list(t[1:]), t[0]), right, t[::-1], t]
        why = (
            f"`first, *rest` gives `first` = {t[0]} and `rest` = {list(t[1:])}. Inside a tuple "
            f"display, `*rest` spreads the list back out, so the result is {left}: everything "
            "rotated one step left."
        )
    return _out(code, HARD, distractors, why, rng, allow_error=True)


@generator(TOPIC, HARD)
def gen_mutable_in_tuple(rng: random.Random) -> Question:
    """A tuple can't be changed, but a list INSIDE it can (and may be shared)."""
    shape = rng.choice(["append", "item", "assign_after", "alias", "list_copy"])
    if rng.random() < 0.5 and shape in ("append", "assign_after"):
        label = rng.choice(["Reds", "Blues", "Owls", "Hawks", "Foxes"])
        members = rng.sample(NAMES, 3)
        first, inner, new = label, members[:2], members[2]
        other = rng.choice([w for w in ["Reds", "Blues", "Owls", "Hawks", "Foxes"] if w != label])
        var = "team"
    else:
        first, a, b, new, other = rng.sample(range(1, 20), 5)
        inner = [a, b]
        var = rng.choice(["t", "record", "entry", "box"])
    head = f"{var} = ({_lit(first)}, {_list_lit(inner)})\n"
    grown = (first, inner + [new])
    if shape == "append":
        code = head + f"{var}[1].append({_lit(new)})\nprint({var})"
        distractors = [TYPE_ERROR, (first, inner), (first, inner, new), ATTRIBUTE_ERROR]
        why = (
            f"The tuple itself never changes: it still holds the same two objects. But "
            f"`{var}[1]` is a LIST, and lists are mutable, so `append` changes it in place: "
            f"{grown}."
        )
    elif shape == "item":
        code = head + f"{var}[1][0] = {_lit(new)}\nprint({var})"
        changed = (first, [new] + inner[1:])
        distractors = [TYPE_ERROR, (first, inner), (new, inner), (first, [new] + inner)]
        why = (
            f"`{var}[1][0] = ...` doesn't replace an item of the tuple; it replaces an item of "
            f"the list stored inside it, which is allowed: {changed}."
        )
    elif shape == "assign_after":
        code = head + f"{var}[1].append({_lit(new)})\n{var}[0] = {_lit(other)}\nprint({var})"
        distractors = [(other, inner + [new]), grown, ATTRIBUTE_ERROR, (first, inner)]
        why = (
            f"Appending to the inner list works, but `{var}[0] = ...` tries to replace an item "
            "of the tuple itself, which raises `TypeError` before anything is printed."
        )
    elif shape == "alias":
        a, b, c, d, e = rng.sample(range(1, 20), 5)
        lst = rng.choice(["nums", "items", "data"])
        code = (
            f"{lst} = [{a}, {b}]\npair = ({lst}, {c})\n{lst}.append({d})\n{lst} = [{e}]\n"
            "print(pair)"
        )
        distractors = [([e], c), ([a, b], c), ([e, d], c), TYPE_ERROR]
        why = (
            f"`pair` holds the same list object as `{lst}`, so `append({d})` shows up inside "
            f"`pair`. Then `{lst} = [{e}]` just points the NAME at a new list; the tuple still "
            f"holds the old one: {([a, b, d], c)}."
        )
    else:
        code = (
            head + f"items = list({var})\nitems[0] = {_lit(other)}\n"
            f"items[1].append({_lit(new)})\nprint({var})"
        )
        distractors = [(first, inner), (other, inner + [new]), TYPE_ERROR, [other, inner + [new]]]
        why = (
            f"`list({var})` is a new list holding the SAME objects. Replacing `items[0]` only "
            f"changes the new list, but `items[1]` IS the list inside `{var}`, so the append "
            f"shows up there: {grown}."
        )
    return _out(code, HARD, distractors, why, rng, allow_error=True)


_TRACE_NOTES = [
    ("discard_missing", "`discard` of a value that isn't there does nothing (no error)."),
    ("add_old", "`add` of a value that is already there changes nothing."),
    ("iand", "`&=` keeps only the values that are also in the right-hand set."),
    ("isub", "`-=` removes the listed values that are present and ignores the rest."),
    ("update", "`update` adds each item of the list, skipping ones already there."),
    ("ior", "`|=` adds every value from the right-hand set that isn't already there."),
    ("remove_old", "`remove` works here because the value is present."),
]
_TRACE_KINDS = [
    "add_new",
    "add_old",
    "discard_missing",
    "discard_old",
    "remove_old",
    "update",
    "ior",
    "isub",
    "iand",
]


@generator(TOPIC, HARD)
def gen_set_trace(rng: random.Random) -> Question:
    """Trace a set through several mutating methods and in-place operators."""
    var = rng.choice(["s", "ids", "pool", "codes", "seen"])
    current = set(rng.sample(range(1, 10), 3))
    start = sorted(current)
    rng.shuffle(start)
    lines = [f"{var} = {_set_lit(start)}"]
    states = [_set_display(current)]
    kinds = rng.sample(_TRACE_KINDS, rng.randint(4, 5))
    raising_at = rng.randrange(1, len(kinds)) if rng.random() < 0.25 else None
    raise_line = None
    used = []
    for idx, kind in enumerate(kinds):
        inside = sorted(current)
        outside = [v for v in range(1, 13) if v not in current]
        if idx == raising_at:
            x = rng.choice(outside)
            raise_line = (len(lines), x)
            lines.append(f"{var}.remove({x})")
            continue
        if kind in ("discard_old", "remove_old", "isub", "iand") and len(current) <= 2:
            kind = "add_new"
        used.append(kind)
        if kind == "add_new":
            x = rng.choice(outside)
            current.add(x)
            lines.append(f"{var}.add({x})")
        elif kind == "add_old":
            lines.append(f"{var}.add({rng.choice(inside)})")
        elif kind == "discard_missing":
            lines.append(f"{var}.discard({rng.choice(outside)})")
        elif kind in ("discard_old", "remove_old"):
            x = rng.choice(inside)
            current.discard(x)
            lines.append(f"{var}.{kind.split('_')[0]}({x})")
        elif kind in ("update", "ior"):
            pair = [rng.choice(inside), rng.choice(outside)]
            rng.shuffle(pair)
            current |= set(pair)
            lines.append(
                f"{var}.update({pair})" if kind == "update" else f"{var} |= {_set_lit(pair)}"
            )
        elif kind == "isub":
            pair = [rng.choice(inside), rng.choice(outside)]
            rng.shuffle(pair)
            current -= set(pair)
            lines.append(f"{var} -= {_set_lit(pair)}")
        else:
            keep = rng.sample(inside, len(inside) - 1) + [rng.choice(outside)]
            rng.shuffle(keep)
            current &= set(keep)
            lines.append(f"{var} &= {_set_lit(keep)}")
        states.append(_set_display(current))
    printer = f"print(sorted({var}))" if rng.random() < 0.6 else f"print(len({var}), sorted({var}))"
    code = "\n".join(lines + [printer])
    skips = [_run("\n".join(lines[:i] + lines[i + 1 :] + [printer])) for i in range(1, len(lines))]
    rng.shuffle(skips)
    trace = " → ".join(states)
    if raise_line is not None:
        at, x = raise_line
        lenient = lines[:at] + [f"{var}.discard({x})"] + lines[at + 1 :]
        partial = _run("\n".join(lines[:at] + [printer]))
        distractors = [
            _run("\n".join(lenient + [printer])),
            partial,
            VALUE_ERROR,
            *skips,
            INDEX_ERROR,
        ]
        why = (
            f"Tracing `{var}`: {' → '.join(states[:at])}. Then `{var}.remove({x})` raises "
            f"`KeyError` because {x} isn't in the set (`discard` would have ignored it), so "
            "nothing is printed."
        )
    else:
        distractors = skips[:2] + [KEY_ERROR] + skips[2:] + [VALUE_ERROR, INDEX_ERROR]
        notes = [note for kind, note in _TRACE_NOTES if kind in used][:2]
        why = f"Tracing `{var}` line by line: {trace}. " + " ".join(notes)
    return _out(code, HARD, distractors, why, rng, allow_error=True)


_PAIR_UPDATES = [
    ("{b}", "{a} + {b}"),
    ("{a} + {b}", "{a}"),
    ("{b}", "{a} * 2"),
    ("{b} + 1", "{a}"),
    ("{b} + 1", "{a} * 2"),
]
_STEP_UPDATES = [
    ("{y}", "{x}"),
    ("{y}", "{x} + {y}"),
    ("{x} + {y}", "{x}"),
    ("{y} * 2", "{x}"),
    ("{x} - {y}", "{y} + 1"),
    ("{y}", "{x} * 2"),
]


@generator(TOPIC, HARD)
def gen_simultaneous_assignment(rng: random.Random) -> Question:
    """``a, b = b, a + b`` evaluates the whole right side BEFORE assigning."""
    shape = rng.choice(["loop", "steps", "gcd", "rotate"])
    if shape == "loop":
        a, b = rng.choice([("a", "b"), ("x", "y"), ("prev", "curr")])
        x0, y0 = rng.randint(0, 3), rng.randint(1, 4)
        n = rng.randint(3, 4)
        e1, e2 = (e.format(a=a, b=b) for e in rng.choice(_PAIR_UPDATES))

        def build(times: int, sequential: bool = False) -> str:
            body = f"    {a} = {e1}\n    {b} = {e2}" if sequential else f"    {a}, {b} = {e1}, {e2}"
            return f"{a}, {b} = {x0}, {y0}\nfor _ in range({times}):\n{body}\nprint({a}, {b})"

        code = build(n)
        res = run_code(code)
        va, vb = res.namespace[a], res.namespace[b]
        distractors = [
            _run(build(n, sequential=True)),
            _run(build(n - 1)),
            _run(build(n + 1)),
            _p(vb, va),
            _run(build(n - 2)),
            _p(x0, y0),
        ]
        states = " → ".join(f"({_run(build(k)).replace(' ', ', ')})" for k in range(n + 1))
        why = (
            f"In `{a}, {b} = {e1}, {e2}` the whole right side is worked out using the OLD "
            f"values before either name changes. ({a}, {b}) goes {states}."
        )
        return _out(code, HARD, distractors, why, rng)
    if shape == "steps":
        x, y = rng.choice([("x", "y"), ("a", "b"), ("m", "n")])
        x0, y0 = rng.sample(range(1, 8), 2)
        steps = [tuple(e.format(x=x, y=y) for e in u) for u in rng.sample(_STEP_UPDATES, 3)]
        head = f"{x}, {y} = {x0}, {y0}\n"
        printer = f"print({x}, {y})"
        code = head + "".join(f"{x}, {y} = {e1}, {e2}\n" for e1, e2 in steps) + printer
        seq = head + "".join(f"{x} = {e1}\n{y} = {e2}\n" for e1, e2 in steps) + printer
        short = head + "".join(f"{x}, {y} = {e1}, {e2}\n" for e1, e2 in steps[:2]) + printer
        res = run_code(code)
        vx, vy = res.namespace[x], res.namespace[y]
        partial = (
            head
            + f"{x} = {steps[0][0]}\n{y} = {steps[0][1]}\n"
            + "".join(f"{x}, {y} = {e1}, {e2}\n" for e1, e2 in steps[1:])
            + printer
        )
        distractors = [_run(seq), _run(partial), _p(vy, vx), _run(short)]
        distractors += int_distractors(vx, rng)
        distractors = [d if " " in d else _p(d, vy) for d in map(str, distractors)]
        states = " → ".join(
            "("
            + _run(
                head + "".join(f"{x}, {y} = {e1}, {e2}\n" for e1, e2 in steps[:k]) + printer
            ).replace(" ", ", ")
            + ")"
            for k in range(len(steps) + 1)
        )
        why = (
            "Each line evaluates BOTH expressions on the right using the old values, then "
            f"assigns them together. ({x}, {y}) goes {states}."
        )
        return _out(code, HARD, distractors, why, rng)
    if shape == "gcd":
        g = rng.randint(2, 9)
        m, k = rng.choice(
            [
                (5, 3),
                (7, 4),
                (8, 3),
                (7, 2),
                (9, 4),
                (5, 2),
                (7, 5),
                (8, 5),
                (9, 7),
                (4, 3),
                (7, 3),
                (9, 2),
            ]
        )
        A, B = g * m, g * k
        if rng.random() < 0.3:
            A, B = B, A
        a, b = rng.choice([("a", "b"), ("x", "y"), ("big", "small")])
        loop_body = f"    {a}, {b} = {b}, {a} % {b}\n"
        seq_body = f"    {a} = {b}\n    {b} = {a} % {b}\n"
        tmpl = (
            f"{a}, {b} = {A}, {B}\nsteps = 0\nwhile {b} > 0:\n{{body}}    steps += 1\n"
            f"print({a}, steps)"
        )
        code = tmpl.format(body=loop_body)
        res = run_code(code)
        ga, st = res.namespace[a], res.namespace["steps"]
        distractors = [_run(tmpl.format(body=seq_body)), _p(ga, st - 1), _p(0, st), _p(ga, st + 1)]
        why = (
            f"Each pass sets `{a}` to the old `{b}` and `{b}` to the old `{a} % {b}`, both "
            f"computed before assigning. The values shrink until `{b}` is 0 after {st} passes, "
            f"leaving {ga} (the greatest common divisor) in `{a}`."
        )
        return _out(code, HARD, distractors, why, rng)
    names = rng.choice([("a", "b", "c"), ("x", "y", "z"), ("p", "q", "r")])
    if rng.random() < 0.5:
        vals = [f'"{v}"' for v in rng.sample(NAMES, 3)]
    else:
        vals = [str(v) for v in rng.sample(range(1, 10), 3)]
    n = rng.randint(2, 5)
    a, b, c = names

    def rot(times: int, body: str) -> str:
        return (
            f"{a}, {b}, {c} = {', '.join(vals)}\nfor _ in range({times}):\n{body}\n"
            f"print({a}, {b}, {c})"
        )

    sim = f"    {a}, {b}, {c} = {b}, {c}, {a}"
    code = rot(n, sim)
    distractors = [
        _run(rot(n, f"    {a} = {b}\n    {b} = {c}\n    {c} = {a}")),
        _run(rot(n, f"    {a}, {b}, {c} = {c}, {a}, {b}")),
        _run(rot(n - 1, sim)),
        _run(rot(n + 1, sim)),
    ]
    why = (
        f"Each pass shifts every value one place left at once (`{a}` takes `{b}`'s value, `{b}` "
        f"takes `{c}`'s, `{c}` takes the OLD `{a}`). Three passes make a full circle, so "
        f"{n} passes act like {n % 3}, giving {_run(code)}."
    )
    return _out(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_tuple_ordering(rng: random.Random) -> Question:
    """max/min/sorted on tuples compare the FIRST item first, ties go to the next."""
    shape = rng.choice(["name_first", "tie", "versions", "sorted"])
    if shape == "name_first":
        for _ in range(50):
            names = rng.sample(NAMES, rng.choice([3, 4]))
            scores = rng.sample(range(60, 100), len(names))
            records = list(zip(names, scores))
            if max(records) != max(records, key=lambda r: r[1]) and (
                min(records) != min(records, key=lambda r: r[1])
            ):
                break
        else:
            raise GenerationError("could not separate name order from score order")
        func = rng.choice(["max", "min"])
        pick = max if func == "max" else min
        code = f"players = {_list_lit(records)}\nprint({func}(players))"
        by_score = pick(records, key=lambda r: r[1])
        distractors = [
            by_score,
            records[0],
            records[-1],
            (by_score[1], by_score[0]),
            pick(records, key=lambda r: -r[1]),
            *records,
        ]
        why = (
            "Tuples compare by their FIRST item, which here is the NAME, so `"
            f"{func}` picks the name that comes {'last' if func == 'max' else 'first'} "
            f"alphabetically, {pick(records)}, regardless of the score."
        )
        return _out(code, HARD, distractors, why, rng)
    if shape == "tie":
        names = sorted(rng.sample(NAMES, 4))
        func = rng.choice(["max", "min"])
        tie = rng.randint(85, 95) if func == "max" else rng.randint(60, 70)
        others = rng.sample(range(71, 84), 2)
        lo_name, hi_name = names[0], names[-1]
        mid_names = names[1:3]
        rng.shuffle(mid_names)
        tied_wrong, tied_right = (lo_name, hi_name) if func == "max" else (hi_name, lo_name)
        records = [
            (tie, tied_wrong),
            (others[0], mid_names[0]),
            (tie, tied_right),
            (others[1], mid_names[1]),
        ]
        if rng.random() < 0.5:
            records = records[1:] + records[:1]
        var = rng.choice(["results", "scores", "entries"])
        code = f"{var} = {_list_lit(records)}\nprint({func}({var}))"
        pick = max if func == "max" else min
        correct = pick(records)
        distractors = [(tie, tied_wrong), records[-1], records[0], *records]
        why = (
            f"Both tied records start with {tie}, so the comparison moves on to the second "
            f"item, the names: {tied_right!r} is {'later' if func == 'max' else 'earlier'} "
            f"alphabetically than {tied_wrong!r}, so `{func}` returns {correct}."
        )
        return _out(code, HARD, distractors, why, rng)
    if shape == "versions":
        major = rng.randint(2, 4)
        p1, p2, p4 = rng.sample(range(0, 13), 3)
        small = rng.randint(2, 8)
        big = max(p1, p2, p4) + rng.randint(1, 4)
        nine, ten, low, old = (
            (major, 9, p1),
            (major, 10, p2),
            (major, small, big),
            (major - 1, 12, p4),
        )
        vs = [nine, ten, low, old]
        rng.shuffle(vs)
        func = rng.choice(["max", "min"])
        code = f"versions = {_list_lit(vs)}\nprint({func}(versions))"
        if func == "max":
            distractors = [nine, old, low, vs[-1]]
            why = (
                f"Tuples compare left to right: {old} loses at once because its first number "
                f"is only {major - 1}. The rest tie on {major}, so the second numbers decide, as "
                f"NUMBERS: 10 > 9 > {small}. (As text, '9' would beat '10'.) So `max` is {ten}."
            )
        else:
            distractors = [low, ten, nine, vs[0]]
            why = (
                f"Tuples compare left to right and the first number decides first: {old} is the "
                f"only one starting with {major - 1}, so it is the smallest, even though its "
                "later numbers are big."
            )
        return _out(code, HARD, distractors, why, rng)
    for _ in range(100):
        firsts = rng.sample(range(1, 8), 3)
        tied = firsts[0]
        s_hi, s_lo, s3, s4 = rng.sample(range(0, 10), 4)
        if s_hi < s_lo:
            s_hi, s_lo = s_lo, s_hi
        pairs = [(tied, s_hi), (firsts[1], s3), (tied, s_lo), (firsts[2], s4)]
        rng.shuffle(pairs)
        i, j = pairs.index((tied, s_hi)), pairs.index((tied, s_lo))
        if i > j:
            pairs[i], pairs[j] = pairs[j], pairs[i]
        traps = [sorted(pairs, key=lambda p: p[0]), sorted(pairs, key=lambda p: p[1]), pairs]
        if sorted(pairs) not in traps and len({str(t) for t in traps}) == 3:
            break
    else:
        raise GenerationError("could not build distinct sort traps")
    var = rng.choice(["pairs", "points", "moves"])
    code = f"{var} = {_list_lit(pairs)}\nprint(sorted({var}))"
    distractors = [*traps, sorted(pairs, reverse=True)]
    why = (
        f"`sorted` orders tuples by their first item, and only when those tie (the two "
        f"starting with {tied}) does it look at the second item ({s_lo} < {s_hi}). Result: "
        f"{sorted(pairs)}."
    )
    return _out(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_seen_set(rng: random.Random) -> Question:
    """The "seen" set idiom: dedupe in order, collect repeats, find the first repeat."""
    shape = rng.choice(["dedup", "repeats", "first_repeat"])
    words = rng.random() < 0.4
    for _ in range(200):
        if words:
            vals = rng.sample(NAMES, 4)
        else:
            vals = rng.sample(range(1, 10), 4)
        n = rng.randint(6, 7)
        items = vals + [rng.choice(vals[:3]) for _ in range(n - 4)]
        rng.shuffle(items)
        first = _first_order(items)
        dup_vals = [v for v in first if items.count(v) >= 2]
        seen: set = set()
        repeats = []
        for v in items:
            if v in seen:
                repeats.append(v)
            seen.add(v)
        last_order = _first_order(items[::-1])[::-1]
        ok = first != sorted(first) and first != last_order and len(repeats) >= 2
        ok = ok and max(items.count(v) for v in vals) <= 3
        if shape == "repeats":
            ok = ok and 2 <= len(set(repeats)) < len(repeats) and repeats != dup_vals
        if shape == "first_repeat":
            ok = ok and repeats[0] != dup_vals[0]
        if ok:
            break
    else:
        raise GenerationError("could not build a suitable list")
    var, item = ("visitors", "name") if words else ("nums", "n")
    head = f"{var} = {_list_lit(items)}\nseen = set()\n"
    if shape == "dedup":
        code = (
            head + f"unique = []\nfor {item} in {var}:\n    if {item} not in seen:\n"
            f"        seen.add({item})\n        unique.append({item})\nprint(unique)"
        )
        once = [v for v in items if items.count(v) == 1]
        distractors = [sorted(first), last_order, once, items]
        why = (
            "Each value is appended only the first time it's met (afterwards it's in `seen`), "
            f"so the list keeps first-appearance order: {first}. The set only remembers what "
            "was seen; it never decides the order."
        )
    elif shape == "repeats":
        code = (
            head + f"repeats = []\nfor {item} in {var}:\n    if {item} in seen:\n"
            f"        repeats.append({item})\n    seen.add({item})\nprint(repeats)"
        )
        all_occ = [v for v in items if v in dup_vals]
        distractors = [_first_order(repeats), dup_vals, all_occ, items]
        triple = next(v for v in dup_vals if items.count(v) == 3)
        why = (
            "A value is appended every time it shows up AFTER its first appearance (by then "
            f"it's in `seen`), so {triple!r}, which appears 3 times, is appended twice. In order "
            f"of those later appearances: {repeats}."
        )
    else:
        code = (
            head + f"for {item} in {var}:\n    if {item} in seen:\n        print({item})\n"
            f"        break\n    seen.add({item})"
        )
        distractors = [dup_vals[0], "\n".join(map(str, repeats)), repeats[-1], NOTHING_PRINTED]
        why = (
            f"The loop stops at the first value that was ALREADY seen: {repeats[0]!r}. "
            f"{dup_vals[0]!r} appears first in the list, but its second copy comes later."
        )
    return _out(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_hashable(rng: random.Random) -> Question:
    """Tuples can be set members and dict keys; lists (even inside a tuple) can't."""
    shape = rng.choice(["tuple_set", "normalize", "add_list", "tuple_with_list", "dict_keys"])
    if shape == "tuple_set":
        for _ in range(50):
            base = [tuple(rng.sample(range(0, 4), 2)) for _ in range(3)]
            if len(set(base)) == 3 and len({tuple(sorted(p)) for p in base}) == 3:
                break
        else:
            raise GenerationError("no distinct pairs")
        visits = base + [rng.choice(base), base[0][::-1]]
        rng.shuffle(visits)
        var = rng.choice(["visits", "moves", "cells"])
        code = f"{var} = {_list_lit(visits)}\nplaces = set({var})\nprint(len({var}), len(places))"
        u = len(set(visits))
        same = len({tuple(sorted(p)) for p in visits})
        distractors = [_p(5, same), _p(5, 5), TYPE_ERROR, _p(u, u)]
        why = (
            "Tuples are immutable, so they can go in a set, and two tuples are duplicates only "
            f"if they have the same items in the same ORDER, so {base[0]} and {base[0][::-1]} "
            f"are different. That leaves {u} distinct tuples."
        )
        return _out(code, HARD, distractors, why, rng, allow_error=True)
    if shape == "normalize":
        for _ in range(50):
            edges = [tuple(rng.sample(range(1, 5), 2)) for _ in range(5)]
            raw, norm = len(set(edges)), len({tuple(sorted(e)) for e in edges})
            if 1 < norm < raw:
                break
        else:
            raise GenerationError("no good edge list")
        code = (
            f"edges = {_list_lit(edges)}\nunique = set()\nfor a, b in edges:\n"
            "    unique.add((min(a, b), max(a, b)))\nprint(len(unique))"
        )
        distractors = [raw, len(edges), TYPE_ERROR, norm - 1]
        ex = next(e for e in edges if e[0] > e[1] and e[::-1] in edges)
        why = (
            f"Each pair is stored smallest-first, so `{ex}` and `{ex[::-1]}` both become "
            f"`{ex[::-1]}` and the set keeps it once. Of {len(edges)} pairs, only {norm} are "
            "different once order is ignored."
        )
        return _out(code, HARD, distractors, why, rng, allow_error=True)
    if shape == "add_list":
        a, b, c, d = rng.sample(range(1, 10), 4)
        var = rng.choice(["pairs", "spots", "seen"])
        code = f"{var} = set()\n{var}.add(({a}, {b}))\n{var}.add([{c}, {d}])\nprint(len({var}))"
        distractors = ["2", "3", "1", ATTRIBUTE_ERROR]
        why = (
            "Set members must be hashable (unchangeable). The tuple is fine, but a list can "
            "change (it is unhashable), so `add([...])` raises `TypeError`."
        )
        return _out(code, HARD, distractors, why, rng, allow_error=True)
    if shape == "tuple_with_list":
        a, b, c = rng.sample(range(1, 10), 3)
        ok = rng.random() < 0.4
        inner = f"({b}, {c})" if ok else f"[{b}, {c}]"
        code = f"key = ({a}, {inner})\ngroups = {{key}}\nprint(len(groups))"
        if ok:
            distractors = [TYPE_ERROR, "2", "3", "0"]
        else:
            distractors = ["1", "2", "3", ATTRIBUTE_ERROR]
        why = "A tuple is hashable only if everything inside it is hashable. " + (
            "This tuple holds only numbers and another tuple, so it can go in a set "
            "(as ONE member)."
            if ok
            else "This tuple contains a list, so putting it in a set raises `TypeError`."
        )
        return _out(code, HARD, distractors, why, rng, allow_error=True)
    cells = []
    while len(cells) < 2:
        cell = tuple(rng.sample(range(0, 3), 2))
        if cell not in cells and cell[::-1] not in cells:
            cells.append(cell)
    first, second = rng.sample(["X", "O"], 2)
    third = rng.choice(["X", "O"])
    target = rng.choice([cells[0], cells[0][::-1]])
    code = (
        f'board = {{}}\nboard[{cells[0]}] = "{first}"\nboard[{cells[1]}] = "{second}"\n'
        f'board[{cells[0]}] = "{third}"\nprint(len(board), {target} in board)'
    )
    present = target == cells[0]
    distractors = [_p(3, present), _p(2, not present), TYPE_ERROR, _p(3, not present)]
    why = (
        f"Tuples work as dict keys. Assigning to `board[{cells[0]}]` a second time replaces "
        "its value instead of adding a key, so there are 2 keys. "
        + (
            f"{target} is one of them."
            if present
            else f"{target} is NOT a key: {cells[0]} and {target} are different tuples."
        )
    )
    return _out(code, HARD, distractors, why, rng, allow_error=True)
