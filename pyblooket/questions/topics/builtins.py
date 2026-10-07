"""Question generators for the "builtins" topic (Built-in Functions).

Covers ``len``, ``sum`` (with a start value, on ``range``, averages), ``min`` /
``max`` (on strings, with ``key=``, on empty sequences), ``sorted`` (``reverse=``,
``key=len/abs/str.lower``, strings vs ints, upper vs lower case), ``reversed``,
``zip`` (stops at the shortest), ``enumerate`` (``start=``), ``map`` / ``filter``
(lazy iterators that need ``list()`` and get used up), ``abs``, ``round``
(banker's rounding), ``any`` / ``all`` (including empty iterables),
``isinstance`` (``bool`` is a subclass of ``int``), ``divmod``, ``chr`` / ``ord``,
``int()`` / ``float()`` / ``str()`` conversions and the types builtins return.
"""

from __future__ import annotations

import itertools
import math
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

TOPIC = "builtins"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
TYPE_ERROR = error_choice("TypeError")
VALUE_ERROR = error_choice("ValueError")
INDEX_ERROR = error_choice("IndexError")
ZERO_DIV_ERROR = error_choice("ZeroDivisionError")


# --------------------------------------------------------------------------
# Private helpers & pools
# --------------------------------------------------------------------------

# Variable name -> lowercase words that fit it.  No word appears in two pools.
_WORD_POOLS = {
    "fruits": [
        "apple",
        "kiwi",
        "plum",
        "pear",
        "fig",
        "lime",
        "mango",
        "grape",
        "peach",
        "melon",
        "banana",
        "cherry",
    ],
    "pets": ["cat", "dog", "fish", "bird", "frog", "rabbit", "pony", "duck", "mouse", "hamster", "turtle"],
    "colors": ["red", "blue", "green", "pink", "gold", "gray", "teal", "white", "black", "orange", "purple"],
    "snacks": [
        "chips",
        "nuts",
        "toast",
        "jelly",
        "fries",
        "cake",
        "pizza",
        "taco",
        "bagel",
        "cookie",
        "popcorn",
    ],
    "tools": ["saw", "drill", "tape", "nail", "glue", "rope", "hammer", "wrench", "ruler", "brush"],
}
_SINGULAR = {"fruits": "fruit", "pets": "pet", "colors": "color", "snacks": "snack", "tools": "tool"}
_ALL_WORDS = [w for pool in _WORD_POOLS.values() for w in pool]
_NUM_VARS = ["nums", "scores", "values", "data", "ages", "marks", "points", "levels"]


def _src(value) -> str:
    """Python source for ``value`` (strings double-quoted, lists/tuples recursively)."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join(_src(v) for v in value) + "]"
    return repr(value)


def _lines(values) -> str:
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
        distractors=[d for d in (x if isinstance(x, str) else str(x) for x in distractors) if _fits(d)],
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _fits(choice: str) -> bool:
    """Whether a distractor fits the choice-card limits (too-long ones are just skipped)."""
    lines = choice.split("\n")
    return len(lines) <= MAX_CHOICE_LINES and all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines)


def _pick_words(rng: random.Random, k: int, pred=None) -> tuple[str, list[str]]:
    """A pool name (used as the variable name) and ``k`` distinct words from it."""
    for _ in range(200):
        var = rng.choice(list(_WORD_POOLS))
        words = rng.sample(_WORD_POOLS[var], k)
        if pred is None or pred(words):
            return var, words
    raise GenerationError("could not pick suitable words")


def _unsorted(rng: random.Random, items: list, key=None) -> list:
    """``items`` shuffled so it is neither ascending nor descending."""
    out = list(items)
    for _ in range(100):
        rng.shuffle(out)
        if out != sorted(out, key=key) and out != sorted(out, key=key, reverse=True):
            return out
    raise GenerationError("could not shuffle into an unsorted order")


def _bools(values, sep: str = " ") -> str:
    return sep.join(str(v) for v in values)


def _bool_combos(correct: list[bool], naive: list[bool] | None = None, sep: str = " ") -> list[str]:
    """Other True/False combinations: the naive one first, then by fewest flips."""
    out = []
    if naive is not None:
        out.append(_bools(naive, sep))
    combos = list(itertools.product([True, False], repeat=len(correct)))
    combos.sort(key=lambda c: sum(a != b for a, b in zip(c, correct)))
    out.extend(_bools(c, sep) for c in combos)
    return out


def _cls(name: str) -> str:
    return f"<class '{name}'>"


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_len_basics(rng: random.Random) -> Question:
    """len counts characters (spaces too), list items (not letters), top-level items only; ints have no len."""
    shape = rng.choice(["phrase", "list", "nested", "number"])
    if shape == "phrase":
        var = rng.choice(["msg", "text", "title", "label"])
        w1, w2 = rng.sample(_ALL_WORDS, 2)
        phrase = f"{w1} {w2}"
        n = len(phrase)
        code = f"{var} = {_src(phrase)}\nprint(len({var}))"
        return _output(
            code,
            EASY,
            [n - 1, n + 1, 2, len(w1), n - 2],
            f"`len` counts every character, and the space is a character too: "
            f"{len(w1)} + 1 + {len(w2)} = {n}.",
            rng,
        )
    if shape == "list":
        var, words = _pick_words(rng, rng.randint(3, 5))
        n = len(words)
        chars = sum(len(w) for w in words)
        code = f"{var} = {_src(words)}\nprint(len({var}))"
        return _output(
            code,
            EASY,
            [chars, n - 1, n + 1, len(words[0]), len(words[-1])],
            f"`len` of a list counts its items, not the letters inside them: `{var}` holds {n} strings.",
            rng,
        )
    if shape == "nested":
        var = rng.choice(["grid", "rows", "groups", "teams"])
        sizes = [rng.randint(1, 3) for _ in range(rng.randint(2, 3))]
        if max(sizes) == 1:
            sizes[rng.randrange(len(sizes))] = rng.randint(2, 3)
        grid = [[rng.randint(1, 9) for _ in range(s)] for s in sizes]
        n, total = len(grid), sum(sizes)
        code = f"{var} = {grid}\nprint(len({var}))"
        return _output(
            code,
            EASY,
            [total, n + 1, sizes[0], n - 1, total + n],
            f"`len` only counts the top-level items. `{var}` holds {n} inner lists; the "
            f"{total} numbers inside them are not counted separately.",
            rng,
        )
    var = rng.choice(["year", "code", "pin", "score"])
    num = rng.randint(10, 99999)
    digits = len(str(num))
    if rng.random() < 0.5:
        code = f"{var} = {num}\nprint(len(str({var})))"
        distractors = [TYPE_ERROR, digits - 1, digits + 1, num, sum(map(int, str(num)))]
        why = (
            f'`str({var})` turns {num} into the string `"{num}"`, and `len` counts its '
            f"{digits} characters."
        )
    else:
        code = f"{var} = {num}\nprint(len({var}))"
        distractors = [digits, 1, VALUE_ERROR, num]
        why = (
            f"Integers have no length, so `len({var})` raises a TypeError. Converting first, "
            f"`len(str({var}))`, would give {digits}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_sum_min_max(rng: random.Random) -> Question:
    """sum / max / min / max - min on a short list (sometimes with negatives)."""
    var = rng.choice(_NUM_VARS)
    k = rng.randint(4, 5)
    if rng.random() < 0.35:
        for _ in range(100):
            nums = rng.sample([v for v in range(-9, 10) if v != 0], k)
            if any(v < 0 for v in nums) and any(v > 0 for v in nums):
                break
    else:
        nums = rng.sample(range(1, 20), k)
    lo, hi, total = min(nums), max(nums), sum(nums)
    func = rng.choice(["sum", "max", "min", "spread"])
    head = f"{var} = {nums}\n"
    if func == "sum":
        code = head + f"print(sum({var}))"
        distractors = [total - nums[-1], total - nums[0], hi, len(nums), *int_distractors(total, rng)]
        why = f"`sum` adds every item: {' + '.join(map(str, nums))} = {total}.".replace("+ -", "- ")
    elif func == "max":
        code = head + f"print(max({var}))"
        distractors = [nums[-1], lo, nums[0], max(nums, key=abs), total, len(nums), *int_distractors(hi, rng)]
        why = f"`max` returns the largest item, wherever it is in the list: {hi}."
    elif func == "min":
        code = head + f"print(min({var}))"
        distractors = [min(nums, key=abs), nums[0], hi, nums[-1], len(nums), *int_distractors(lo, rng)]
        why = f"`min` returns the smallest item: {lo}." + (
            " Negative numbers are smaller than every positive one." if lo < 0 else ""
        )
    else:
        code = head + f"print(max({var}) - min({var}))"
        distractors = [hi + lo, nums[-1] - nums[0], lo - hi, hi, *int_distractors(hi - lo, rng)]
        why = f"`max({var})` is {hi} and `min({var})` is {lo}, so the difference is {hi} - {lo} = {hi - lo}."
        why = why.replace("- -", "+ ")
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_sorted_basics(rng: random.Random) -> Question:
    """sorted ascending / reverse=True / on words, and sorted() does not change the original."""
    mode = rng.choices(["asc", "desc", "words", "unchanged"], weights=[3, 3, 3, 2])[0]
    if mode == "words":
        var, words = _pick_words(rng, 4, pred=lambda ws: len({w[0] for w in ws}) == 4)
        words = _unsorted(rng, words)
        code = f"{var} = {_src(words)}\nprint(sorted({var}))"
        distractors = [
            words,
            sorted(words, reverse=True),
            sorted(words, key=len),
            words[::-1],
            sorted(words, key=len, reverse=True),
        ]
        why = f"`sorted` on strings puts them in alphabetical order, giving {sorted(words)}."
        return _output(code, EASY, distractors, why, rng)

    var = rng.choice(_NUM_VARS)
    nums = _unsorted(rng, rng.sample(range(1, 30), rng.randint(4, 5)))
    asc, desc = sorted(nums), sorted(nums, reverse=True)
    head = f"{var} = {nums}\n"
    if mode == "asc":
        code = head + f"print(sorted({var}))"
        distractors = [desc, nums, nums[::-1]]
        why = f"`sorted` returns a new list with the items in ascending (smallest-first) order: {asc}."
    elif mode == "desc":
        code = head + f"print(sorted({var}, reverse=True))"
        distractors = [nums[::-1], asc, nums]
        why = (
            f"`reverse=True` makes `sorted` order the items largest-first: {desc}. It sorts "
            "first and then flips; it does not just reverse the original order."
        )
    else:
        code = head + f"sorted({var})\nprint({var})"
        distractors = [asc, desc, "None", nums[::-1]]
        why = (
            f"`sorted` builds and returns a NEW list; it never changes `{var}`. Here the result "
            f"is thrown away, so `{var}` is still {nums}."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_abs_round(rng: random.Random) -> Question:
    """abs() of a difference / sum of abs values, round() to an int or to n decimal places."""
    mode = rng.choice(["abs_diff", "abs_sum", "round_int", "round_digits"])
    if mode == "abs_diff":
        a, b = sorted(rng.sample(range(1, 25), 2))
        x, y = rng.choice([("start", "end"), ("low", "high"), ("a", "b"), ("before", "after")])
        code = f"{x} = {a}\n{y} = {b}\nprint(abs({x} - {y}))"
        distractors = [a - b, a + b, -(a + b), b - a + 1]
        why = f"`{x} - {y}` is {a - b}, and `abs` removes the minus sign, giving {b - a}."
    elif mode == "abs_sum":
        a = -rng.randint(1, 12)
        b = rng.choice([1, -1]) * rng.randint(1, 12)
        x, y = rng.choice([("a", "b"), ("x", "y"), ("left", "right"), ("dx", "dy")])
        code = f"{x} = {a}\n{y} = {b}\nprint(abs({x}) + abs({y}))"
        ans = abs(a) + abs(b)
        distractors = [a + b, abs(a + b), -ans, abs(a) - abs(b), *int_distractors(ans, rng)]
        why = (
            f"`abs` gives the distance from zero, so `abs({a})` is {abs(a)} and `abs({b})` is {abs(b)}; "
            f"together {ans}."
        )
    elif mode == "round_int":
        n = rng.randint(1, 20)
        d = rng.choice([1, 2, 3, 4, 6, 7, 8, 9])
        var = rng.choice(["price", "temp", "height", "speed", "score"])
        code = f"{var} = {n}.{d}\nprint(round({var}))"
        r, other = (n + 1, n) if d > 5 else (n, n + 1)
        distractors = [other, f"{r}.0", f"{n}.{d}", f"{other}.0"]
        why = (
            f"`round` with one argument rounds to the nearest whole number and returns an int: "
            f"{n}.{d} is closer to {r}" + (" (so it rounds up)." if d > 5 else ", so it does not round up.")
        )
    else:
        n = rng.randint(0, 9)
        k = rng.choice([1, 2])
        digits = [rng.randint(1, 8) for _ in range(k)]
        digits.append(rng.choice([1, 2, 3, 4, 6, 7, 8]))
        if rng.random() < 0.5:
            digits.append(rng.randint(1, 9))
        text = f"{n}." + "".join(map(str, digits))
        up = digits[k] > 5
        kept = digits[: k - 1] + [digits[k - 1] + (1 if up else 0)]
        other = digits[: k - 1] + [digits[k - 1] + (0 if up else 1)]
        var = rng.choice(["pi_ish", "weight", "ratio", "distance", "price"])
        code = f"{var} = {text}\nprint(round({var}, {k}))"
        ans = f"{n}." + "".join(map(str, kept))
        distractors = [
            f"{n}." + "".join(map(str, other)),
            f"{n}." + "".join(map(str, digits[: k + 1])),
            str(round(float(text))),
            text,
        ]
        why = (
            f"`round({var}, {k})` keeps {k} digit{'s' if k > 1 else ''} after the decimal point. "
            f"The next digit is {digits[k]}, so it rounds {'up' if up else 'down'} to {ans}."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_type_conversion(rng: random.Random) -> Question:
    """int("12") + 3 vs "12" + 3, str(a) + str(b), int(3.9) truncates, float("2.5") * 2."""
    mode = rng.choice(["int_plus", "str_concat", "int_trunc", "float_times", "str_plus_int"])
    if mode == "int_plus":
        a, b = rng.randint(10, 60), rng.randint(2, 9)
        var = rng.choice(["count", "age", "qty", "total"])
        code = f"{var} = {_src(str(a))}\nprint(int({var}) + {b})"
        distractors = [f"{a}{b}", TYPE_ERROR, f"{a + b}.0", VALUE_ERROR]
        why = (
            f'`int({var})` turns the string `"{a}"` into the number {a}, so this is ordinary addition: {a} '
            f'+ {b} = {a + b}.'
        )
    elif mode == "str_concat":
        a, b = rng.sample(range(1, 10), 2)
        x, y = rng.choice([("a", "b"), ("x", "y"), ("first", "second"), ("tens", "ones")])
        code = f"{x} = {a}\n{y} = {b}\nprint(str({x}) + str({y}))"
        distractors = [a + b, f"{a} {b}", TYPE_ERROR, f"{b}{a}"]
        why = (
            f'`str` turns each number into text, and `+` on strings joins them: `"{a}" + "{b}"` is '
            f'`"{a}{b}"`.'
        )
    elif mode == "int_trunc":
        n, d = rng.randint(1, 30), rng.randint(5, 9)
        var = rng.choice(["price", "temp", "height", "speed"])
        code = f"{var} = {n}.{d}\nprint(int({var}))"
        distractors = [n + 1, f"{n}.{d}", f"{n}.0", VALUE_ERROR]
        why = (
            f"`int()` on a float just chops off the decimal part (it does not round), so `int({n}.{d})` is "
            f"{n}."
        )
    elif mode == "float_times":
        n = rng.randint(1, 9)
        var = rng.choice(["size", "rate", "width", "dose"])
        code = f"{var} = {_src(f'{n}.5')}\nprint(float({var}) * 2)"
        ans = n * 2 + 1
        distractors = [ans, f"{n}.5{n}.5", TYPE_ERROR, f"{ans}.5"]
        why = (
            f"`float({var})` converts the string to the number {n}.5, and {n}.5 * 2 = {ans}.0 (a float "
            "stays a float)."
        )
    else:
        a, b = rng.randint(10, 60), rng.randint(2, 9)
        var = rng.choice(["count", "age", "qty", "total"])
        code = f"{var} = {_src(str(a))}\nprint({var} + {b})"
        distractors = [a + b, f"{a}{b}", VALUE_ERROR, f"{a + b}.0"]
        why = (
            f'`{var}` is the string `"{a}"`, and Python will not add a string and an int, so this '
            f"raises a TypeError. Use `int({var}) + {b}` to get {a + b}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_enumerate_basics(rng: random.Random) -> Question:
    """enumerate gives (index, item) pairs starting at 0."""
    mode = rng.choice(["loop", "string", "list", "find"])
    if mode == "string":
        word = rng.choice(["hi", "hey", "cat", "sun", "map", "dog", "zip", "owl", "pie"])
        code = f"for i, ch in enumerate({_src(word)}):\n    print(i, ch)"
        distractors = [
            _lines(f"{i + 1} {c}" for i, c in enumerate(word)),
            _lines(f"{c} {i}" for i, c in enumerate(word)),
            _lines(f"({i}, {c!r})" for i, c in enumerate(word)),
            _lines(range(len(word))),
        ]
        why = (
            "`enumerate` pairs each character with its index, counting from 0, and the loop unpacks each "
            "pair into `i` and `ch`."
        )
        return _output(code, EASY, distractors, why, rng)

    var, items = _pick_words(rng, rng.randint(2, 3))
    item = _SINGULAR[var]
    head = f"{var} = {_src(items)}\n"
    if mode == "loop":
        code = head + f"for i, {item} in enumerate({var}):\n    print(i, {item})"
        distractors = [
            _lines(f"{i + 1} {w}" for i, w in enumerate(items)),
            _lines(f"{w} {i}" for i, w in enumerate(items)),
            _lines(f"({i}, {w!r})" for i, w in enumerate(items)),
            _lines(items),
        ]
        why = (
            "`enumerate` gives (index, item) pairs and counts from 0 by default, so the first line is `0 "
            + items[0]
            + "`."
        )
    elif mode == "list":
        code = head + f"print(list(enumerate({var})))"
        distractors = [
            list(enumerate(items, 1)),
            [(w, i) for i, w in enumerate(items)],
            [[i, w] for i, w in enumerate(items)],
            list(range(len(items))),
        ]
        why = f"`enumerate` produces (index, item) tuples starting at index 0: {list(enumerate(items))}."
    else:
        target = rng.randrange(len(items))
        word = items[target]
        code = head + f"for i, {item} in enumerate({var}):\n    if {item} == {_src(word)}:\n        print(i)"
        distractors = [target + 1, word, f"{target} {word}", target - 1 if target else len(items)]
        why = (
            f"`enumerate` counts from 0, and {word!r} is item number {target} in that count, so `{target}` "
            "is printed."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_pick_builtin(rng: random.Random) -> Question:
    """Which of len / max / min / sum gives a target value?"""
    var = rng.choice(_NUM_VARS)
    for _ in range(100):
        nums = rng.sample(range(1, 15), rng.randint(3, 5))
        vals = {"len": len(nums), "max": max(nums), "min": min(nums), "sum": sum(nums)}
        if len(set(vals.values())) == 4:
            break
    else:
        raise GenerationError("could not pick distinct len/max/min/sum")
    func = rng.choice(list(vals))
    target = vals[func]
    wrong = [f"{f}({var})" for f in vals if f != func] + [f"{var}[-1]", f"{var}[0]"]
    rng.shuffle(wrong)
    return which_expression_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Which expression evaluates to `{target}`?",
        setup=f"{var} = {nums}",
        target=target,
        correct_expr=f"{func}({var})",
        wrong_exprs=wrong,
        explanation=(
            f"`len` counts the items ({vals['len']}), `max` gives the largest ({vals['max']}), "
            f"`min` the smallest ({vals['min']}) and `sum` adds them all ({vals['sum']}), "
            f"so `{func}({var})` is the one equal to {target}."
        ),
        rng=rng,
    )


# ==========================================================================
# MEDIUM
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_sorted_key(rng: random.Random) -> Question:
    """sorted with key=len (stable ties), key=abs, key=len + reverse=True: key compares, items stay."""
    mode = rng.choice(["len", "abs", "len_rev"])
    if mode == "abs":
        var = rng.choice(["nums", "deltas", "changes", "offsets"])
        for _ in range(100):
            nums = [rng.choice([1, -1]) * v for v in rng.sample(range(1, 15), rng.randint(4, 5))]
            if 1 <= sum(v < 0 for v in nums) < len(nums):
                break
        nums = _unsorted(rng, nums, key=abs)
        by_abs = sorted(nums, key=abs)
        code = f"{var} = {nums}\nprint(sorted({var}, key=abs))"
        distractors = [sorted(abs(v) for v in nums), sorted(nums), sorted(nums, key=abs, reverse=True), nums]
        why = (
            f"`key=abs` makes `sorted` COMPARE the absolute values, but it still returns the "
            f"original numbers (signs included): {by_abs}."
        )
        return _output(code, MEDIUM, distractors, why, rng)

    rev = mode == "len_rev"
    if rev:
        var, words = _pick_words(rng, 4, pred=lambda ws: len({len(w) for w in ws}) == 4)
    else:
        var, words = _pick_words(rng, rng.randint(4, 5), pred=lambda ws: len({len(w) for w in ws}) >= 3)
    words = _unsorted(rng, words, key=len)
    if rev:
        code = f"{var} = {_src(words)}\nprint(sorted({var}, key=len, reverse=True))"
        ans = sorted(words, key=len, reverse=True)
        distractors = [
            sorted(len(w) for w in words)[::-1],
            sorted(words, key=len),
            sorted(words, reverse=True),
            words[::-1],
            words,
        ]
        why = f"`key=len` compares the words by length and `reverse=True` puts the longest first: {ans}."
    else:
        code = f"{var} = {_src(words)}\nprint(sorted({var}, key=len))"
        ans = sorted(words, key=len)
        distractors = [
            sorted(words, key=lambda w: (len(w), w)),
            sorted(len(w) for w in words),
            sorted(words),
            sorted(words, key=len, reverse=True),
            words,
        ]
        why = f"`key=len` makes `sorted` order the words by length, shortest first: {ans}."
        if len({len(w) for w in words}) < len(words):
            why += " Words of equal length keep their original order (sorting is stable)."
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_zip_shortest(rng: random.Random) -> Question:
    """zip pairs items up and silently stops at the shorter input; zip objects have no len()."""
    mode = rng.choice(["loop", "list", "dict", "len"])
    short = rng.randint(2, 3)
    long_ = short + rng.randint(1, 2)
    if mode == "loop":
        names_first = rng.random() < 0.6
        n_names, n_scores = (long_, short) if names_first else (short, long_)
        names = rng.sample(NAMES, n_names)
        scores = [rng.randint(50, 99) for _ in range(n_scores)]
        code = (
            f"names = {_src(names)}\nscores = {scores}\n"
            "for name, score in zip(names, scores):\n    print(name, score)"
        )
        lines = [f"{a} {b}" for a, b in zip(names, scores)]
        padded = lines + [
            f"{names[i] if i < n_names else None} {scores[i] if i < n_scores else None}"
            for i in range(short, long_)
        ]
        distractors = [_lines(padded), INDEX_ERROR, VALUE_ERROR, _lines(lines[:-1])]
        why = (
            f"`zip` stops as soon as the shorter list runs out. `{'scores' if names_first else 'names'}` "
            f"has only {short} items, so only {short} pairs are printed and no error occurs."
        )
    elif mode == "list":
        letters = list("abcdefgh"[: rng.choice([short, long_])])
        rng.shuffle(letters)
        nums = rng.sample(range(1, 10), long_ if len(letters) == short else short)
        a, b = ("letters", "nums") if rng.random() < 0.5 else ("nums", "letters")
        first, second = (letters, nums) if a == "letters" else (nums, letters)
        code = f"letters = {_src(letters)}\nnums = {nums}\nprint(list(zip({a}, {b})))"
        pairs = list(zip(first, second))
        padded = list(itertools.zip_longest(first, second))
        distractors = [
            padded,
            [list(p) for p in pairs],
            list(zip(*pairs)) if pairs else [],
            INDEX_ERROR,
        ]
        why = (
            "`zip` builds tuples from items at the same position and stops at the shorter input, giving "
            f"{len(pairs)} tuples: {pairs}."
        )
    elif mode == "dict":
        names = rng.sample(NAMES, long_)
        ages = rng.sample(range(10, 18), short)
        code = f"names = {_src(names)}\nages = {ages}\nprint(dict(zip(names, ages)))"
        pairs = list(zip(names, ages))
        padded = dict(itertools.zip_longest(names, ages))
        distractors = [padded, INDEX_ERROR, pairs, {v: k for k, v in pairs}]
        why = (
            f"`zip` stops after {short} pairs because `ages` is shorter, so the extra name is dropped: "
            f"{dict(pairs)}."
        )
    else:
        word = rng.choice(["code", "loop", "snake", "tiger", "lemon", "python", "planet", "banana"])
        nums = rng.sample(range(1, 10), short)
        if rng.random() < 0.6:
            code = f"word = {_src(word)}\nnums = {nums}\nprint(len(list(zip(word, nums))))"
            distractors = [len(word), TYPE_ERROR, len(word) + short, short * 2]
            why = (
                "`zip` pairs one letter with one number and stops when `nums` runs out, so there are "
                f"{short} pairs."
            )
        else:
            code = f"word = {_src(word)}\nnums = {nums}\nprint(len(zip(word, nums)))"
            distractors = [short, len(word), VALUE_ERROR, len(word) + short]
            why = (
                "`zip` returns a lazy zip object, not a list, and it has no length, so `len()` raises "
                f"a TypeError. `len(list(zip(word, nums)))` would give {short}."
            )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_enumerate_trace(rng: random.Random) -> Question:
    """enumerate(start=1): positions shift but no item is skipped; trace a loop that uses the position."""
    mode = rng.choice(["even_pos", "filter_print", "list"])
    if mode == "even_pos":
        var = rng.choice(_NUM_VARS)
        nums = rng.sample(range(1, 20), rng.randint(4, 6))
        step = rng.choice([2, 3])
        code = (
            f"{var} = {nums}\ntotal = 0\n"
            f"for pos, value in enumerate({var}, start=1):\n"
            f"    if pos % {step} == 0:\n        total += value\nprint(total)"
        )
        ans = sum(v for p, v in enumerate(nums, 1) if p % step == 0)
        zero_based = sum(v for p, v in enumerate(nums) if p % step == 0)
        skip_first = sum(v for p, v in enumerate(nums[1:], 1) if p % step == 0)
        distractors = [zero_based, skip_first, sum(nums) - ans, sum(nums), *int_distractors(ans, rng)]
        picked = [(p, v) for p, v in enumerate(nums, 1) if p % step == 0]
        why = (
            f"With `start=1` the first item is position 1, so the positions divisible by {step} are "
            f"{', '.join(str(p) for p, _ in picked)}, holding {', '.join(str(v) for _, v in picked)}: "
            f"the total is {ans}."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    if mode == "filter_print":
        var, words = _pick_words(rng, rng.randint(4, 5), pred=lambda ws: len({len(w) for w in ws}) >= 2)
        limit = rng.choice(sorted({len(w) for w in words})[:-1])
        item = _SINGULAR[var]
        body = f"    if len({item}) > {limit}:\n        print(pos, {item})"
        code = f"{var} = {_src(words)}\nfor pos, {item} in enumerate({var}, start=1):\n" + body
        variants = [
            code.replace(", start=1)", ")"),
            code.replace(f"enumerate({var}, start=1)", f"enumerate({var}[1:], start=1)"),
            code.replace(f" > {limit}", f" >= {limit}"),
        ]
        kept = [w for w in words if len(w) > limit]
        renumbered = _lines(f"{i} {w}" for i, w in enumerate(kept, 1))
        distractors = [
            _run(variants[0]),
            renumbered,
            _run(variants[1]),
            _run(variants[2]),
            _lines(f"{i} {w}" for i, w in enumerate(words, 1)),
            _lines(kept),
        ]
        hits = [f"{p} {w}" for p, w in enumerate(words, 1) if len(w) > limit]
        why = (
            f"`start=1` only changes the numbering: {words[0]!r} is position 1, {words[1]!r} is 2, and so on, "
            f"and no item is skipped. Only words longer than {limit} letters are printed, each with its "
            f"position in the whole list: {', '.join(hits)}."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    word = rng.choice(["abc", "hey", "cat", "sun", "map", "owl", "zip", "pie", "jog"])
    start = rng.randint(1, 2)
    code = f"print(list(enumerate({_src(word)}, start={start})))"
    ans = list(enumerate(word, start))
    distractors = [
        list(enumerate(word[start:], start)),
        list(enumerate(word)),
        [(c, i) for i, c in ans],
        list(enumerate(word, start + 1)),
    ]
    why = (
        f"`start={start}` only sets the first number; every letter is still included, so the pairs are {ans}."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_map_filter(rng: random.Random) -> Question:
    """map(int, ...) converts, map(len, ...) transforms, filter keeps items vs map returns the True/False results."""
    mode = rng.choice(["map_int", "map_len", "filter", "map_pred"])
    if mode == "map_int":
        a, b, c = rng.sample(range(2, 40), 3)
        i, j = rng.sample(range(3), 2)
        vals = [a, b, c]
        code = (
            f"values = {_src([str(v) for v in vals])}\nnums = list(map(int, values))\n"
            f"print(nums[{i}] + nums[{j}])"
        )
        distractors = [f"{vals[i]}{vals[j]}", TYPE_ERROR, f"{vals[i]} {vals[j]}", a + b + c]
        why = (
            f"`map(int, values)` applies `int` to each string, so `nums` is {vals} (real numbers), "
            f"and {vals[i]} + {vals[j]} = {vals[i] + vals[j]}."
        )
        return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    if mode == "map_len":
        var, words = _pick_words(rng, rng.randint(3, 4), pred=lambda ws: len({len(w) for w in ws}) > 1)
        lens = [len(w) for w in words]
        code = f"{var} = {_src(words)}\nprint(list(map(len, {var})))"
        distractors = [sum(lens), sorted(lens), len(words), words]
        why = (
            f"`map(len, {var})` calls `len` on each word in order, and `list()` collects the results: {lens}."
        )
        return _output(code, MEDIUM, distractors, why, rng)

    preds = {
        "is_even": ("n % 2 == 0", lambda n: n % 2 == 0),
        "is_odd": ("n % 2 == 1", lambda n: n % 2 == 1),
        "is_big": ("n > 10", lambda n: n > 10),
        "is_small": ("n < 5", lambda n: n < 5),
    }
    name = rng.choice(list(preds))
    cond, fn = preds[name]
    for _ in range(100):
        nums = rng.sample(range(1, 20), rng.randint(4, 5))
        if 0 < sum(map(fn, nums)) < len(nums):
            break
    head = f"def {name}(n):\n    return {cond}\n\n\nnums = {nums}\n"
    kept = [n for n in nums if fn(n)]
    flags = [fn(n) for n in nums]
    if mode == "filter":
        code = head + f"print(list(filter({name}, nums)))"
        distractors = [flags, [n for n in nums if not fn(n)], len(kept), nums]
        why = (
            f"`filter` keeps the items for which `{name}` returns True, so the result is {kept}. "
            "(`map` would give the True/False results instead.)"
        )
    else:
        code = head + f"print(list(map({name}, nums)))"
        distractors = [kept, [not f for f in flags], len(kept), [n for n in nums if not fn(n)]]
        why = (
            f"`map` calls `{name}` on every item and keeps what it RETURNS, which is True or False: "
            f"{flags}. (`filter` is the one that keeps the items themselves.)"
        )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_min_max_strings(rng: random.Random) -> Question:
    """max/min on strings compare alphabetically, not by length; key=len changes that (first wins ties)."""
    mode = rng.choice(["max_words", "min_words", "max_key_len", "min_letter"])
    if mode == "min_letter":
        word = rng.choice(
            ["python", "snake", "rocket", "tiger", "lemon", "orbit", "quest", "pixel", "mango", "candy"]
        )
        code = f"word = {_src(word)}\nprint(min(word))"
        distractors = [word[0], max(word), word[-1], sorted(word)[1], *sorted(set(word))]
        why = (
            f"`min` on a string compares its characters alphabetically; the earliest letter in {word!r} is "
            f"{min(word)!r}."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    if mode == "max_words":
        var, words = _pick_words(
            rng, 4, pred=lambda ws: max(ws) != max(ws, key=len) and len({w[0] for w in ws}) == 4
        )
        code = f"{var} = {_src(words)}\nprint(max({var}))"
        distractors = [max(words, key=len), words[-1], min(words), words[0], *words]
        why = (
            f"Strings are compared alphabetically (letter by letter), not by length, so the "
            f'"largest" is the one that comes last in the dictionary: {max(words)!r}.'
        )
    elif mode == "min_words":
        var, words = _pick_words(
            rng, 4, pred=lambda ws: min(ws) != min(ws, key=len) and len({w[0] for w in ws}) == 4
        )
        code = f"{var} = {_src(words)}\nprint(min({var}))"
        distractors = [min(words, key=len), words[0], max(words), words[-1], *words]
        why = (
            f"Strings are compared alphabetically, not by length, so `min` returns the word that "
            f"comes first in the dictionary: {min(words)!r}."
        )
    else:

        def ok(ws):
            longest = max(len(w) for w in ws)
            return max(ws) != max(ws, key=len) and sum(len(w) == longest for w in ws) <= 2

        var, words = _pick_words(rng, 4, pred=ok)
        words = _unsorted(rng, words, key=len) if len({len(w) for w in words}) > 1 else words
        longest = [w for w in words if len(w) == max(map(len, words))]
        code = f"{var} = {_src(words)}\nprint(max({var}, key=len))"
        distractors = [longest[-1], max(words), len(longest[0]), min(words, key=len), words[-1], *words]
        why = f"`key=len` makes `max` compare lengths, and it returns the word itself: {longest[0]!r}."
        if len(longest) > 1:
            why += f" {longest[0]!r} and {longest[1]!r} tie, and `max` returns the FIRST one it finds."
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_divmod(rng: random.Random) -> Question:
    """divmod(a, b) returns the tuple (a // b, a % b); unpack it for hours/minutes etc."""
    mode = rng.choice(["tuple", "time", "pack"])
    if mode == "tuple":
        for _ in range(100):
            b = rng.randint(3, 9)
            a = rng.randint(b + 1, 60)
            q, r = divmod(a, b)
            if r and q != r:
                break
        code = f"print(divmod({a}, {b}))"
        distractors = [(r, q), f"{q} {r}", [q, r], (q + 1, r), (q, r + 1)]
        why = f"`divmod({a}, {b})` returns a tuple of `{a} // {b}` and `{a} % {b}`: ({q}, {r})."
    elif mode == "time":
        total = rng.choice([v for v in range(61, 300) if v % 60 and v % 60 != v // 60])
        h, m = divmod(total, 60)
        var = rng.choice(["minutes", "duration", "length", "runtime"])
        code = f"{var} = {total}\nhours, mins = divmod({var}, 60)\nprint(hours, mins)"
        distractors = [
            f"{m} {h}",
            f"({h}, {m})",
            *([f"{total / 60} {m}"] if len(str(total / 60)) <= 5 else []),
            f"{h + 1} {m}",
            f"{h} {m + 1}",
        ]
        why = (
            f"`divmod({total}, 60)` gives ({h}, {m}): {h} whole hour{'s' if h > 1 else ''} (`{total} // 60`) "
            f"and {m} minutes left over (`{total} % 60`), unpacked in that order."
        )
    else:
        thing, size, box = rng.choice(
            [
                ("eggs", 6, "cartons"),
                ("pencils", 12, "packs"),
                ("players", 5, "teams"),
                ("cookies", 8, "bags"),
            ]
        )
        for _ in range(100):
            n = rng.randint(size + 1, size * 6)
            full, left = divmod(n, size)
            if left and full != left:
                break
        code = f"{thing} = {n}\n{box}, left = divmod({thing}, {size})\nprint({box}, left)"
        distractors = [f"{left} {full}", f"{full + 1} {left}", f"{full + 1} 0", f"({full}, {left})"]
        why = (
            f"`divmod({n}, {size})` returns ({full}, {left}): {full} full groups of {size} and {left} left "
            "over, unpacked in that order."
        )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_reversed(rng: random.Random) -> Question:
    """reversed() flips the order (it does not sort) and gives an iterator, so wrap it in list() or join it."""
    mode = rng.choice(["list", "join", "range", "sorted_then"])
    if mode == "list":
        var = rng.choice(_NUM_VARS)
        nums = _unsorted(rng, rng.sample(range(1, 30), rng.randint(4, 5)))
        code = f"{var} = {nums}\nprint(list(reversed({var})))"
        distractors = [sorted(nums, reverse=True), nums, sorted(nums)]
        why = (
            "`reversed` just walks the list from the back; it does not sort anything. So the result is "
            f"{nums[::-1]}."
        )
    elif mode == "join":
        word = rng.choice(
            ["python", "snake", "rocket", "tiger", "lemon", "orbit", "pixel", "mango", "candy", "planet"]
        )
        code = f'word = {_src(word)}\nprint("".join(reversed(word)))'
        distractors = [
            list(reversed(word)),
            word,
            "".join(sorted(word, reverse=True)),
            word[-1] + word[1:-1] + word[0],
            "".join(sorted(word)),
        ]
        why = (
            '`reversed(word)` yields the letters last-to-first, and `"".join` glues them back into one '
            f'string: {word[::-1]!r}.'
        )
    elif mode == "range":
        a = rng.randint(0, 5)
        b = a + rng.randint(3, 5)
        code = f"print(list(reversed(range({a}, {b}))))"
        ans = list(range(b - 1, a - 1, -1))
        distractors = [list(range(b, a - 1, -1)), list(range(b, a, -1)), list(range(a, b)), ans[:-1]]
        why = (
            f"`range({a}, {b})` is {list(range(a, b))} (the end {b} is excluded), and `reversed` walks it "
            f"backwards: {ans}."
        )
    else:
        var = rng.choice(_NUM_VARS)
        nums = _unsorted(rng, rng.sample(range(1, 30), rng.randint(4, 5)))
        code = f"{var} = {nums}\nprint(list(reversed(sorted({var}))))"
        distractors = [nums[::-1], sorted(nums), nums]
        why = (
            f"`sorted` runs first, giving {sorted(nums)}; then `reversed` flips that sorted list to "
            f"{sorted(nums, reverse=True)}."
        )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_int_conversion(rng: random.Random) -> Question:
    """int("3.9") is a ValueError, int(float("3.9")) truncates, "7" * 2 vs int("7") * 2, mixing str and int."""
    mode = rng.choice(["int_of_float_str", "int_float_str", "repeat", "sum_two", "float_plus", "str_plus"])
    n, d = rng.randint(2, 20), rng.choice([25, 5, 75, 9, 8, 4])
    text = f"{n}.{d}"
    var = rng.choice(["text", "entry", "reading", "raw"])
    if mode == "int_of_float_str":
        code = f"{var} = {_src(text)}\nprint(int({var}))"
        distractors = [n, n + 1, text, TYPE_ERROR]
        why = (
            f'`int()` can convert a string only if it looks like a whole number. `"{text}"` has a '
            f"decimal point, so it raises a ValueError (`int(float({var}))` would give {n})."
        )
    elif mode == "int_float_str":
        code = f"{var} = {_src(text)}\nprint(int(float({var})))"
        distractors = [VALUE_ERROR, n + 1, text, f"{n}.0"]
        why = (
            f"`float({var})` turns the string into {text}, and `int()` on a float drops the decimal part "
            f"(no rounding), giving {n}."
        )
    elif mode == "repeat":
        k = rng.randint(2, 9)
        times = rng.randint(2, 3)
        code = f"digit = {_src(str(k))}\nprint(digit * {times}, int(digit) * {times})"
        distractors = [
            f"{k * times} {k * times}",
            f"{str(k) * times} {str(k) * times}",
            TYPE_ERROR,
            f"{k * times} {str(k) * times}",
        ]
        why = (
            f'`digit` is a string, so `* {times}` repeats it: `"{str(k) * times}"`. After `int(digit)` it is '
            f"the number {k}, and {k} * {times} = {k * times}."
        )
    elif mode == "sum_two":
        a = rng.randint(10, 40)
        f_int, f_dec = rng.randint(2, 9), rng.randint(5, 9)
        code = f"count = {_src(str(a))}\nextra = {f_int}.{f_dec}\nprint(int(count) + int(extra))"
        distractors = [a + f_int + 1, f"{a + f_int}.{f_dec}", VALUE_ERROR, f"{a}{f_int}"]
        why = (
            f"`int(count)` is {a} and `int({f_int}.{f_dec})` truncates to {f_int} (no rounding up), so the "
            f"sum is {a + f_int}."
        )
    elif mode == "float_plus":
        a, b = rng.randint(1, 9), rng.randint(1, 9)
        code = f"x = {_src(str(a))}\ny = {_src(str(b))}\nprint(float(x) + int(y))"
        distractors = [a + b, f"{a}{b}", TYPE_ERROR, f"{a}.0{b}"]
        why = f"`float(x)` is {a}.0 and `int(y)` is {b}; adding a float and an int gives a float: {a + b}.0."
    else:
        a, b = rng.randint(1, 9), rng.randint(1, 9)
        code = f"x = {_src(str(a))}\ny = {_src(str(b))}\nprint(int(x) + y)"
        distractors = [a + b, f"{a}{b}", VALUE_ERROR, f"{a + b}.0"]
        why = (
            f'`int(x)` is the number {a}, but `y` is still the string `"{b}"`, and an int plus a '
            "string raises a TypeError. Both sides need converting."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_return_types(rng: random.Random) -> Question:
    """What type does a builtin return? round() -> int, round(x, 1) -> float, sorted(str) -> list, ..."""
    case = rng.choice(["round", "round_nd", "sorted", "divmod", "sum_float", "abs_float", "zip", "min_mixed"])
    if case == "round":
        x = f"{rng.randint(1, 20)}.{rng.randint(1, 9)}"
        setup = f"price = {x}\nresult = round(price)"
        ans, wrong = "int", ["float", "str", "tuple"]
        why = f"`round` with ONE argument returns an `int` ({round(float(x))}), even though {x} is a float."
    elif case == "round_nd":
        x = f"{rng.randint(1, 20)}.{rng.randint(11, 99)}"
        setup = f"price = {x}\nresult = round(price, 1)"
        ans, wrong = "float", ["int", "str", "tuple"]
        why = (
            "With a second argument, `round` keeps decimal places and returns a `float`: "
            f"{round(float(x), 1)}."
        )
    elif case == "sorted":
        word = rng.choice(["cab", "tiger", "lemon", "pixel", "mango", "candy", "orbit"])
        setup = f"word = {_src(word)}\nresult = sorted(word)"
        ans, wrong = "list", ["str", "tuple", "NoneType"]
        why = (
            f'`sorted` ALWAYS returns a list, even for a string: {sorted(word)}. Use `"".join(...)` to get '
            'a string back.'
        )
    elif case == "divmod":
        a, b = rng.randint(10, 50), rng.randint(3, 9)
        setup = f"result = divmod({a}, {b})"
        ans, wrong = "tuple", ["int", "list", "float"]
        why = f"`divmod` returns BOTH the quotient and the remainder packed in a tuple: {divmod(a, b)}."
    elif case == "sum_float":
        a, b = rng.randint(0, 9), rng.randint(0, 9)
        setup = f"prices = [{a}.5, {b}.5]\nresult = sum(prices)"
        ans, wrong = "float", ["int", "list", "str"]
        why = f"Adding floats gives a float, even when the total is a whole number: {a + b + 1}.0."
    elif case == "abs_float":
        a = rng.randint(1, 20)
        setup = f"change = -{a}.0\nresult = abs(change)"
        ans, wrong = "float", ["int", "str", "bool"]
        why = f"`abs` keeps the type of its argument, so `abs(-{a}.0)` is the float {a}.0, not the int {a}."
    elif case == "zip":
        names = rng.sample(NAMES, 2)
        nums = rng.sample(range(1, 10), 2)
        setup = f"pairs = list(zip({_src(names)}, {nums}))\nresult = pairs[0]"
        ans, wrong = "tuple", ["list", "str", "dict"]
        why = (
            "`list(...)` makes the outer list, but each item `zip` produces is a tuple: "
            f"{list(zip(names, nums))[0]}."
        )
    else:
        ints = rng.sample(range(2, 10), 2)
        fl = rng.randint(1, 9) + 0.5
        vals = [*ints, fl]
        rng.shuffle(vals)
        setup = f"nums = {vals}\nresult = min(nums)"
        ans = "float" if min(vals) == fl else "int"
        wrong = ["int" if ans == "float" else "float", "list", "str"]
        why = (
            f"`min` returns one of the items unchanged; the smallest here is {min(vals)}, which is "
            f"{'an' if ans == 'int' else 'a'} `{ans}`."
        )
    code = setup + "\nprint(type(result))"
    res = run_code(code)
    if res.output != _cls(ans):
        raise GenerationError(f"type mismatch: {res.output}")
    return _output(code, MEDIUM, [_cls(w) for w in wrong], why, rng)


@generator(TOPIC, MEDIUM)
def gen_chr_ord(rng: random.Random) -> Question:
    """ord() gives a character's code, chr() turns a code back into a character: shifting letters."""
    mode = rng.choice(["shift", "shift", "distance", "next"])
    if mode == "shift":
        for _ in range(100):
            word = rng.choice(
                ["cat", "dog", "hip", "bed", "sun", "map", "pet", "jog", "web", "fox", "owl", "pig", "cub"]
            )
            k = rng.choice([1, 2, -1])
            if all("a" <= chr(ord(c) + k) <= "z" and "a" <= chr(ord(c) - k) <= "z" for c in word):
                break
        else:
            raise GenerationError("no shiftable word")

        def shift(w, by):
            return "".join(chr(ord(c) + by) for c in w)

        op = f"+ {k}" if k > 0 else f"- {-k}"
        code = (
            f'word = {_src(word)}\nresult = ""\nfor ch in word:\n'
            f"    result += chr(ord(ch) {op})\nprint(result)"
        )
        distractors = [
            shift(word, -k),
            shift(word[0], k) + word[1:],
            word,
            shift(word, k + (1 if k > 0 else -1)),
        ]
        direction = "forward" if k > 0 else "back"
        why = (
            f"`ord(ch) {op}` moves each letter's code {abs(k)} place{'s' if abs(k) > 1 else ''} {direction} in the "
            f"alphabet and `chr` turns it back into a letter, so {word!r} becomes {shift(word, k)!r}."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    if mode == "distance":
        a, b = sorted(rng.sample("abcdefghijklmnopqrstuvwxyz", 2))
        dist = ord(b) - ord(a)
        if rng.random() < 0.5:
            code = f"start = {_src(a)}\nend = {_src(b)}\nprint(ord(end) - ord(start))"
            distractors = [dist + 1, dist - 1, TYPE_ERROR, -dist]
            why = (
                f"Letter codes are consecutive, so {b!r} is {dist} codes after {a!r}: the difference is "
                f"{dist}."
            )
        else:
            code = f'letter = {_src(b)}\nprint(ord(letter) - ord("a") + 1)'
            pos = ord(b) - ord("a") + 1
            distractors = [pos - 1, pos + 1, TYPE_ERROR, 26 - pos]
            why = (
                f"`ord(letter) - ord(\"a\")` is {pos - 1} (how far {b!r} is past 'a'), and adding 1 gives "
                f"its alphabet position, {pos}."
            )
        return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    k = rng.randint(2, 4)
    letter = rng.choice(
        [c for c in "abcdefghijklmnopqrstuvwxyz" if "a" <= chr(ord(c) - k) and chr(ord(c) + k + 1) <= "z"]
    )
    code = f"letter = {_src(letter)}\nprint(chr(ord(letter) + {k}))"
    ans = chr(ord(letter) + k)
    distractors = [chr(ord(ans) - 1), chr(ord(ans) + 1), chr(ord(letter) - k), TYPE_ERROR]
    why = (
        f"`ord` turns {letter!r} into its number code, `+ {k}` moves {k} letters on, and `chr` turns the "
        f"code back into a letter: {ans!r}."
    )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_sum_variants(rng: random.Random) -> Question:
    """sum with a start value, sum(range(...)) excludes the end, average is a float, sum of a string fails."""
    mode = rng.choice(["start", "range", "average", "digits"])
    if mode == "start":
        var = rng.choice(_NUM_VARS)
        nums = rng.sample(range(1, 15), rng.randint(3, 4))
        start = rng.choice([10, 20, 50, 100])
        total = sum(nums)
        code = f"{var} = {nums}\nprint(sum({var}, {start}))"
        distractors = [total, TYPE_ERROR, total + start * len(nums), total - start]
        why = (
            f"The second argument of `sum` is the starting value, so it computes {start} + {total} = "
            f"{start + total}."
        )
        return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    if mode == "range":
        a = rng.randint(0, 3)
        b = a + rng.randint(3, 6)
        code = f"print(sum(range({a}, {b})))"
        ans = sum(range(a, b))
        distractors = [
            ans + b,
            ans - a if a else ans - (b - 1),
            b - a,
            sum(range(a + 1, b + 1)),
            *int_distractors(ans, rng),
        ]
        why = f"`range({a}, {b})` stops BEFORE {b}, so this adds {' + '.join(map(str, range(a, b)))} = {ans}."
        return _output(code, MEDIUM, distractors, why, rng)
    if mode == "average":
        var = rng.choice(_NUM_VARS)
        k = rng.choice([2, 4])
        nums = rng.sample(range(1, 20), k)
        if rng.random() < 0.5:
            nums[-1] += (-sum(nums)) % k  # make the mean a whole number
        total = sum(nums)
        code = f"{var} = {nums}\nprint(sum({var}) / len({var}))"
        mean = total / k
        whole = total % k == 0
        distractors = [
            total // k,
            total,
            f"{total // k}.0" if not whole else f"{mean + 0.5}",
            *(f"{mean + d}" for d in (1, -1, 0.5, -0.5)),
        ]
        why = f"`sum` is {total} and `len` is {k}; `/` always gives a float, so the result is {mean}."
        return _output(code, MEDIUM, distractors, why, rng)
    num = rng.randint(100, 9999)
    var = rng.choice(["code", "pin", "year", "number"])
    digit_sum = sum(map(int, str(num)))
    if rng.random() < 0.55:
        code = f"{var} = {_src(str(num))}\nprint(sum(map(int, {var})))"
        distractors = [num, TYPE_ERROR, len(str(num)), *int_distractors(digit_sum, rng)]
        why = (
            f"`map(int, {var})` turns each character into a digit, and `sum` adds them: "
            f"{' + '.join(str(num))} = {digit_sum}."
        )
    else:
        code = f"{var} = {_src(str(num))}\nprint(sum({var}))"
        distractors = [digit_sum, num, VALUE_ERROR, len(str(num))]
        why = (
            f'`sum` starts at 0 and tries `0 + "{str(num)[0]}"`, which raises a TypeError: you can\'t '
            f"add numbers and strings. `sum(map(int, {var}))` would give {digit_sum}."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


# ==========================================================================
# HARD
# ==========================================================================


def _half_up(x: float) -> int:
    return math.floor(x + 0.5)


@generator(TOPIC, HARD)
def gen_round_bankers(rng: random.Random) -> Question:
    """round() uses round-half-to-even: round(2.5) == 2 but round(3.5) == 4."""
    mode = rng.choice(["pair", "map", "total"])

    def ties(k):
        """``k`` distinct x.5 values including at least one even and one odd whole part."""
        for _ in range(100):
            ints = rng.sample(range(0, 10), k)
            if any(i % 2 == 0 for i in ints) and any(i % 2 for i in ints):
                return [i + 0.5 for i in ints]
        raise GenerationError("no tie values")

    if mode == "pair":
        vals = ties(rng.choice([2, 3]))
        code = "print(" + ", ".join(f"round({v})" for v in vals) + ")"
        ans = [round(v) for v in vals]
        swapped = [_half_up(v) if round(v) != _half_up(v) else int(v) for v in vals]
        distractors = [
            _bools(_half_up(v) for v in vals),
            _bools(swapped),
            _bools(int(v) for v in vals),
            _bools(float(a) for a in ans),
        ]
    elif mode == "map":
        vals = ties(2)
        n_plain = rng.choice([1, 2])
        for _ in range(n_plain):
            vals.append(rng.randint(0, 9) + rng.choice([0.2, 0.3, 0.4, 0.6, 0.7, 0.8]))
        rng.shuffle(vals)
        var = rng.choice(["values", "readings", "prices", "scores"])
        code = f"{var} = {vals}\nprint(list(map(round, {var})))"
        ans = [round(v) for v in vals]
        distractors = [
            [_half_up(v) for v in vals],
            [int(v) for v in vals],
            [
                (
                    _half_up(v)
                    if v % 1 == 0.5 and round(v) != _half_up(v)
                    else (int(v) if v % 1 == 0.5 else round(v))
                )
                for v in vals
            ],
            [float(a) for a in ans],
        ]
    else:
        vals = ties(rng.choice([3, 3, 4]))
        var = rng.choice(["prices", "weights", "times", "scores"])
        code = f"{var} = {vals}\ntotal = 0\nfor x in {var}:\n" f"    total += round(x)\nprint(total)"
        ans_total = sum(round(v) for v in vals)
        distractors = [
            sum(_half_up(v) for v in vals),
            sum(int(v) for v in vals),
            sum(vals),
            round(sum(vals)),
            *int_distractors(ans_total, rng, spread=2),
        ]
        ans = [round(v) for v in vals]
    evens = [v for v in vals if v % 1 == 0.5 and int(v) % 2 == 0]
    odds = [v for v in vals if v % 1 == 0.5 and int(v) % 2 == 1]
    why = (
        "Python's `round` uses round-half-to-even (banker's rounding): a value exactly halfway goes to "
        f"the nearest EVEN whole number, so `round({evens[0]})` rounds down to {round(evens[0])} while "
        f"`round({odds[0]})` rounds up to {round(odds[0])}."
    )
    if mode == "total":
        why += f" The rounded values are {', '.join(map(str, ans))}, which add up to {sum(ans)}."
    return _output(code, HARD, distractors, why, rng)


_TRUTH_POOL = [
    # (source, truthy, what students often assume)
    ("0", False, False),
    ("3", True, True),
    ("7", True, True),
    ("-2", True, False),
    ('""', False, False),
    ('"0"', True, False),
    ('" "', True, False),
    ('"no"', True, True),
    ("[]", False, False),
    ("[0]", True, False),
    ("None", False, False),
    ("0.0", False, False),
    ('"False"', True, False),
]


@generator(TOPIC, HARD)
def gen_any_all(rng: random.Random) -> Question:
    """any/all use truthiness: all([]) is True, any([]) is False, "0" and [0] are truthy."""
    mode = rng.choice(["lists", "lists", "groups"])
    if mode == "lists":
        for _ in range(200):
            a = rng.sample(_TRUTH_POOL, rng.randint(2, 4))
            b = rng.sample(_TRUTH_POOL, rng.randint(2, 4))
            tricky = sum(t != n for _, t, n in a + b)
            if rng.random() < 0.25:
                a = []
            calls = [("all", "a", a), ("any", "b", b)]
            if rng.random() < 0.4:
                calls.append(rng.choice([("any", "a", a), ("all", "b", b)]))
            truth = [all(t for _, t, _ in v) if f == "all" else any(t for _, t, _ in v) for f, _, v in calls]
            naive = [
                (bool(v) and all(n for _, _, n in v)) if f == "all" else any(n for _, _, n in v)
                for f, _, v in calls
            ]
            if (tricky or not a) and truth != naive:
                break
        else:
            raise GenerationError("no tricky any/all lists")
        code = (
            f"a = [{', '.join(s for s, _, _ in a)}]\nb = [{', '.join(s for s, _, _ in b)}]\n"
            f"print({', '.join(f'{f}({v})' for f, v, _ in calls)})"
        )
        distractors = _bool_combos(truth, naive)
        notes = []
        if not a:
            notes.append("`all([])` is True because an empty list has no falsy item.")
        surprises = sorted({s for s, t, n in a + b if t != n})
        if surprises:
            listed = ", ".join(f"`{x}`" for x in surprises)
            notes.append(
                f"{listed} {'is' if len(surprises) == 1 else 'are'} truthy: only zeros, empty "
                "strings/lists and `None` are falsy."
            )
        why = (
            "`all` is True when no item is falsy; `any` is True when at least one item is truthy. "
            + " ".join(notes)
        )
        return _output(code, HARD, distractors, why, rng)

    groups = [[]]
    groups.append(rng.sample(range(1, 9), rng.randint(1, 3)))
    mixed = rng.sample(range(1, 9), rng.randint(1, 2))
    mixed.insert(rng.randint(0, len(mixed)), 0)
    groups.append(mixed)
    rng.shuffle(groups)
    var = rng.choice(["groups", "batches", "rows", "teams"])
    code = f"{var} = {groups}\nfor g in {var}:\n    print(all(g), any(g))"

    def show(all_fn, any_fn):
        return _lines(f"{all_fn(g)} {any_fn(g)}" for g in groups)

    distractors = [
        show(lambda g: bool(g) and all(g), any),
        show(lambda g: bool(g) and all(g), lambda g: bool(g) and all(g)),
        show(lambda g: bool(g), lambda g: bool(g)),
        show(any, all),
        show(all, all),
    ]
    why = (
        "`all([])` is True (there is no falsy item to fail it) while `any([])` is False (there is no truthy item). "
        f"A list containing 0, like {mixed}, has `all` False but `any` True."
    )
    return _output(code, HARD, distractors, why, rng)


_ISINSTANCE_CHECKS = [
    # (expression template, value, what students often assume, why)
    (
        "isinstance(True, int)",
        True,
        False,
        "`bool` is a subclass of `int`, so `isinstance(True, int)` is True.",
    ),
    ("type(True) == int", False, True, "`type(True)` is exactly `bool`, so `type(True) == int` is False."),
    (
        "isinstance(False, int)",
        True,
        False,
        "`bool` is a subclass of `int`, so `isinstance(False, int)` is True.",
    ),
    (
        "isinstance({n}, bool)",
        False,
        False,
        "An ordinary int like {n} is not a bool (only True and False are).",
    ),
    ("isinstance({n}, float)", False, True, "{n} is an int, not a float; `isinstance` does not convert."),
    ("isinstance({n}.0, int)", False, True, "{n}.0 is a float even though it is a whole number."),
    ("isinstance({n}.5, float)", True, True, "{n}.5 is a float."),
    ('isinstance("{n}", int)', False, True, '`"{n}"` is a string, not an int.'),
    ("type({n}) == int", True, True, "`type({n})` is exactly `int`."),
]


@generator(TOPIC, HARD)
def gen_bool_is_int(rng: random.Random) -> Question:
    """bool is a subclass of int: isinstance(True, int), sum of booleans, counting ints in a mixed list."""
    mode = rng.choice(["checks", "sum_flags", "count"])
    if mode == "checks":
        for _ in range(100):
            idx = rng.sample(range(len(_ISINSTANCE_CHECKS)), rng.choice([2, 3]))
            if any(i < 3 for i in idx) and not {0, 2} <= set(idx):
                break
        picks = [_ISINSTANCE_CHECKS[i] for i in idx]
        n = rng.randint(2, 9)
        exprs = [p[0].format(n=n) for p in picks]
        truth = [p[1] for p in picks]
        naive = [p[2] for p in picks]
        if len(exprs) == 2:
            code = f"print({', '.join(exprs)})"
            sep = " "
        else:
            code = "\n".join(f"print({e})" for e in exprs)
            sep = "\n"
        distractors = _bool_combos(truth, naive if naive != truth else None, sep)
        why = " ".join(p[3].format(n=n) for p in picks)
        return _output(code, HARD, distractors, why, rng)
    if mode == "sum_flags":
        flags = [rng.random() < 0.6 for _ in range(rng.randint(4, 6))]
        if not any(flags):
            flags[0] = True
        var = rng.choice(["flags", "answers", "passed", "checks"])
        if rng.random() < 0.5:
            code = f"{var} = {flags}\nprint(sum({var}))"
            ans = sum(flags)
            distractors = [TYPE_ERROR, len(flags), "True", len(flags) - ans]
            why = (
                "`True` behaves like 1 and `False` like 0 (`bool` is a subclass of `int`), so `sum` counts "
                f"the Trues: {ans}."
            )
        else:
            extra = rng.randint(2, 9)
            code = f"{var} = {flags}\nprint(sum({var}) + {var}.count(False) * {extra})"
            ans = sum(flags) + flags.count(False) * extra
            distractors = [TYPE_ERROR, sum(flags), len(flags) * extra, *int_distractors(ans, rng)]
            why = (
                f"`sum({var})` counts each True as 1, giving {sum(flags)}, and `{var}.count(False)` is "
                f"{flags.count(False)}, so the total is {sum(flags)} + {flags.count(False)} * {extra} = {ans}."
            )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    pool = [
        ("3", "int"),
        ("7", "int"),
        ("12", "int"),
        ("True", "bool"),
        ("False", "bool"),
        ("2.5", "float"),
        ("4.0", "float"),
        ('"4"', "str"),
        ('"9"', "str"),
    ]
    for _ in range(100):
        items = rng.sample(pool, rng.randint(5, 6))
        kinds = [k for _, k in items]
        if "bool" in kinds and "int" in kinds and ("float" in kinds or "str" in kinds):
            break
    rng.shuffle(items)
    target = "int"
    code = (
        f"values = [{', '.join(s for s, _ in items)}]\ncount = 0\nfor v in values:\n"
        f"    if isinstance(v, {target}):\n        count += 1\nprint(count)"
    )
    n_int, n_bool = kinds.count("int"), kinds.count("bool")
    n_float, n_str = kinds.count("float"), kinds.count("str")
    distractors = [
        n_int,
        n_int + n_bool + n_float,
        n_int + n_str + n_bool,
        n_int + n_float,
        len(items),
        *int_distractors(n_int + n_bool, rng, spread=2),
    ]
    why = (
        f"`isinstance(v, int)` is True for the {n_int} real ints AND for the {n_bool} bool"
        f"{'s' if n_bool > 1 else ''}, because `bool` is a subclass of `int`. Floats like 4.0 and strings "
        f'like "4" don\'t count, so the total is {n_int + n_bool}.'
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_sorted_strings(rng: random.Random) -> Question:
    """Strings sort character by character: "10" < "9", and uppercase comes before lowercase."""
    mode = rng.choice(["digits", "max_digits", "key_str", "case", "case_lower"])
    if mode in ("digits", "max_digits", "key_str"):
        for _ in range(100):
            nums = [rng.randint(2, 9), rng.randint(10, 99), rng.randint(10, 99), rng.randint(100, 999)]
            if (
                len(set(nums)) == 4
                and sorted(nums) != sorted(nums, key=str)
                and max(nums, key=str) != max(nums)
            ):
                break
        nums = _unsorted(rng, nums)
        if mode == "key_str":
            code = f"nums = {nums}\nprint(sorted(nums, key=str))"
            ans = sorted(nums, key=str)
            distractors = [sorted(nums), [str(v) for v in ans], sorted(nums, key=str, reverse=True), nums]
            why = (
                "`key=str` compares the numbers as TEXT, character by character, so "
                f'`"{ans[0]}"` comes before `"{ans[-1]}"` just like words in a dictionary; the '
                f"items themselves stay ints: {ans}."
            )
            return _output(code, HARD, distractors, why, rng)
        codes = [str(v) for v in nums]
        var = rng.choice(["codes", "labels", "ids", "tags"])
        if mode == "digits":
            code = f"{var} = {_src(codes)}\nprint(sorted({var}))"
            ans = sorted(codes)
            distractors = [sorted(codes, key=int), sorted(nums), sorted(codes, reverse=True), codes]
            why = (
                "These are strings, so they are compared character by character, not as numbers: "
                f'`"{ans[0]}"` comes first because its first character is smallest, giving {ans}.'
            )
        else:
            code = f"{var} = {_src(codes)}\nprint(max({var}))"
            distractors = [max(nums), TYPE_ERROR, min(codes), codes[-1], min(nums), *codes]
            why = (
                f'Comparing strings looks at the first character first, and `"{max(codes)[0]}"` beats every '
                f'other first digit, so `"{max(codes)}"` is the max even though {max(nums)} is the biggest number.'
            )
            return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
        return _output(code, HARD, distractors, why, rng)

    def ok(ws):
        return len({w[0] for w in ws}) == len(ws)

    var, words = _pick_words(rng, 4, pred=ok)
    for _ in range(100):
        caps = rng.sample(range(4), rng.choice([1, 2]))
        mixed = [w.capitalize() if i in caps else w for i, w in enumerate(words)]
        if sorted(mixed) != sorted(mixed, key=str.lower):
            break
    else:
        raise GenerationError("no case-sensitive difference")
    mixed = _unsorted(rng, mixed, key=str.lower)
    if mode == "case":
        code = f"{var} = {_src(mixed)}\nprint(sorted({var}))"
        ans = sorted(mixed)
        distractors = [
            sorted(mixed, key=str.lower),
            sorted(mixed, reverse=True),
            mixed,
            sorted(w.lower() for w in mixed),
        ]
        why = (
            "Strings compare by character code, and every uppercase letter comes before every lowercase "
            f"letter, so the capitalised words come first: {ans}."
        )
    else:
        code = f"{var} = {_src(mixed)}\nprint(sorted({var}, key=str.lower))"
        ans = sorted(mixed, key=str.lower)
        distractors = [
            sorted(mixed),
            sorted(w.lower() for w in mixed),
            sorted(mixed, key=str.lower, reverse=True),
            mixed,
        ]
        why = (
            "`key=str.lower` compares lowercase copies, so case is ignored when ordering, but the original "
            f"strings (capitals included) are what end up in the result: {ans}."
        )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_empty_errors(rng: random.Random) -> Question:
    """Which builtins cope with an empty list? max/min raise ValueError, sum is 0, average divides by zero."""
    mode = rng.choice(["max_passing", "average", "mix"])
    if mode == "max_passing":
        cutoff = rng.choice([50, 60, 70, 80])
        empty = rng.random() < 0.5
        k = rng.randint(3, 4)
        if empty:
            scores = rng.sample(range(20, cutoff), k)
        else:
            n_pass = rng.randint(2, k - 1)
            scores = rng.sample(range(20, cutoff), k - n_pass) + rng.sample(range(cutoff, 100), n_pass)
            rng.shuffle(scores)
        code = (
            f"scores = {scores}\npassing = []\nfor s in scores:\n    if s >= {cutoff}:\n"
            f"        passing.append(s)\nprint(len(passing), max(passing))"
        )
        passing = [s for s in scores if s >= cutoff]
        if empty:
            distractors = ["0 0", "0 None", INDEX_ERROR, f"0 {max(scores)}", TYPE_ERROR]
            why = (
                f"No score reaches {cutoff}, so `passing` stays empty. `max` of an empty list has no answer "
                "and raises a ValueError (before `print` can show anything)."
            )
        else:
            distractors = [
                VALUE_ERROR,
                f"{len(passing)} {min(passing)}",
                f"{len(scores)} {max(passing)}",
                f"{len(passing)} {sum(passing)}",
            ]
            why = (
                f"Scores of at least {cutoff} are {passing}, so there are {len(passing)} of them and the "
                f"largest is {max(passing)}."
            )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    if mode == "average":
        limit = rng.choice([20, 25, 30])
        empty = rng.random() < 0.5
        k = rng.randint(3, 4)
        if empty:
            temps = rng.sample(range(5, limit + 1), k)
        else:
            temps = rng.sample(range(5, limit + 1), k - 2) + rng.sample(range(limit + 1, 40), 2)
            rng.shuffle(temps)
        code = (
            f"temps = {temps}\nwarm = []\nfor t in temps:\n    if t > {limit}:\n"
            f"        warm.append(t)\nprint(sum(warm) / len(warm))"
        )
        warm = [t for t in temps if t > limit]
        if empty:
            distractors = ["0.0", "0", VALUE_ERROR, "None"]
            why = (
                f"No temperature is above {limit}, so `warm` is empty: `sum(warm)` is 0 and `len(warm)` is 0, "
                "and 0 / 0 raises a ZeroDivisionError."
            )
        else:
            mean = sum(warm) / len(warm)
            distractors = [
                ZERO_DIV_ERROR,
                sum(warm) // len(warm) if mean % 1 else int(mean),
                sum(temps) / len(temps),
                sum(warm),
            ]
            why = f"Only {warm} are above {limit}, so the average is {sum(warm)} / {len(warm)} = {mean}."
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)

    # mix: several builtins on an empty list in a single print
    real = {"len": "0", "sum": "0", "sorted": "[]", "any": "False", "all": "True"}
    guess = {"sum": "None", "sorted": "None", "any": "None", "all": "False"}  # common wrong guesses
    var = rng.choice(["data", "items", "scores", "results"])
    funcs = rng.sample(list(real), 3)
    if rng.random() < 0.5:
        funcs[rng.randrange(3)] = rng.choice(["max", "min"])
    code = f"{var} = []\nprint({', '.join(f'{f}({var})' for f in funcs)})"

    def show(overrides):
        return " ".join(overrides.get(f, real.get(f, "None")) for f in funcs)

    bad = [f for f in funcs if f not in real]
    if bad:
        distractors = [
            show({"all": "False"}),
            show({bad[0]: "0"}),
            show({}),
            TYPE_ERROR,
            INDEX_ERROR,
        ]
        why = (
            f"`len`, `sum`, `sorted`, `any` and `all` all have an answer for an empty list, but `{bad[0]}` "
            f"does not: `{bad[0]}([])` raises a ValueError, so `print` never runs."
        )
    else:
        flips = [show({f: guess[f]}) for f in sorted(funcs, key=lambda f: f != "all") if f in guess]
        distractors = [*flips[:1], VALUE_ERROR, *flips[1:], show(guess), TYPE_ERROR]
        why = (
            "All of these cope with an empty list: `len` and `sum` give 0, `sorted` gives [], `any` gives "
            "False and `all` gives True (no item fails the test). Only `max`/`min` would raise."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_iterator_exhaustion(rng: random.Random) -> Question:
    """map/zip/reversed/filter objects are one-shot iterators: the second pass sees nothing."""
    source = rng.choice(["map_len", "map_abs", "zip", "reversed", "filter"])
    keep = rng.random() < 0.3  # wrap in list(): then both passes see everything
    if source == "map_len":
        var, words = _pick_words(rng, 3)
        head = f"{var} = {_src(words)}\n"
        it_name, expr = "lengths", f"map(len, {var})"
        consumers = ["sum", "list", "max"]
    elif source == "map_abs":
        var = rng.choice(["changes", "deltas", "moves"])
        nums = [rng.choice([1, -1]) * v for v in rng.sample(range(1, 10), 3)]
        head = f"{var} = {nums}\n"
        it_name, expr = "sizes", f"map(abs, {var})"
        consumers = ["sum", "list", "max", "sorted"]
    elif source == "zip":
        names = rng.sample(NAMES, 2)
        nums = rng.sample(range(1, 10), 2)
        head = f"names = {_src(names)}\nnums = {nums}\n"
        it_name, expr = "pairs", "zip(names, nums)"
        consumers = ["list", "dict", "len_list"]
    elif source == "reversed":
        var = rng.choice(_NUM_VARS)
        nums = rng.sample(range(1, 20), 3)
        head = f"{var} = {nums}\n"
        it_name, expr = "backwards", f"reversed({var})"
        consumers = ["list", "sum", "max"]
    else:
        word = rng.choice(["a1b2c3", "x7y8", "r2d2", "c3po", "4ab5", "m9n0p1"])
        head = f"text = {_src(word)}\n"
        it_name, expr = "digits", "filter(str.isdigit, text)"
        consumers = ["list", "len_list"]
    first = rng.choice(consumers)
    second = rng.choice([c for c in consumers if c not in ("max", "min")])

    def body(make: str, listy: bool) -> str:
        def call(c):
            if c == "len_list":
                return f"len({it_name})" if listy else f"len(list({it_name}))"
            if c == "list" and listy:
                return it_name
            return f"{c}({it_name})"

        return head + f"{it_name} = {make}\nprint({call(first)})\nprint({call(second)})"

    as_list = body(f"list({expr})", True)
    as_iter = body(expr, False)
    code = as_list if keep else as_iter
    first_line = _run(as_list).split("\n")[0]
    distractors = [
        _run(as_iter) if keep else _run(as_list),
        f"{first_line}\nNone",
        TYPE_ERROR,
        _run(body("[]", True)),
    ]
    if keep:
        why = (
            f"`list({expr})` stores the results in a real list, which can be read as many times as you "
            "like, so both prints see all the items."
        )
    else:
        why = (
            f"`{expr.split('(')[0]}` returns a one-shot iterator, not a list. The first `print` uses up all of "
            f"its items, so the second pass over `{it_name}` finds it empty."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_sort_key_blank(rng: random.Random) -> Question:
    """Which key= gives the shown order? Compare len, str.lower, last letter, abs, str, ..."""
    blank = "___"
    use_words = rng.random() < 0.55
    if use_words:
        keys = {
            "len": "compares lengths (ties keep their original order)",
            "str.lower": "compares the words ignoring case",
            "None": (
                "means no key function, so the normal string order is used "
                "(every capital letter comes before every lowercase one)"
            ),
            "lambda w: w[-1]": "compares the LAST letters",
            "lambda w: -len(w)": "puts the longest words first (ties keep their original order)",
            "lambda w: w[1]": "compares the SECOND letters",
        }
    else:
        keys = {
            "abs": "compares the numbers without their signs",
            "None": "means no key function, so the numbers are sorted normally",
            "lambda n: -n": "puts the largest number first",
            "lambda n: -abs(n)": "puts the numbers furthest from zero first",
            "lambda n: n % 2": (
                "puts even numbers (key 0) before odd ones (key 1), otherwise keeping the original order"
            ),
        }
    for _ in range(100):
        if use_words:
            var, words = _pick_words(
                rng, 4, pred=lambda ws: len({w[0] for w in ws}) == 4 and len({w[-1] for w in ws}) == 4
            )
            caps = rng.sample(range(4), rng.choice([1, 2]))
            items = [w.capitalize() if i in caps else w for i, w in enumerate(words)]
            rng.shuffle(items)
        else:
            var = rng.choice(["nums", "deltas", "changes"])
            items = [rng.choice([1, -1]) * v for v in rng.sample(range(2, 30), 4)]
            if not 0 < sum(v < 0 for v in items) < 4 or len({abs(v) for v in items}) < 4:
                continue
        head = f"{var} = {_src(items)}\n"
        outputs = {}
        for k in keys:
            res = run_code(head + f"print(sorted({var}, key={k}))")
            if not res.error:
                outputs[k] = res.output
        unique = [k for k in outputs if list(outputs.values()).count(outputs[k]) == 1]
        if len(set(outputs.values())) >= 4 and unique and items != sorted(items):
            break
    else:
        raise GenerationError("not enough distinguishable keys")
    correct = rng.choice(unique)
    target = outputs[correct]
    wrong = [k for k in outputs if outputs[k] != target]
    rng.shuffle(wrong)
    code = head + f"result = sorted({var}, key={blank})\nprint(result)  # {target}"
    return build_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Which key fills the blank so the code prints the list shown in the comment?",
        correct=correct,
        distractors=wrong,
        explanation=f"`key={correct}` {keys[correct]}, which gives {target}.",
        rng=rng,
        code=code,
    )


@generator(TOPIC, HARD)
def gen_zip_enumerate_trace(rng: random.Random) -> Question:
    """enumerate(zip(...), start=1) with a condition: zip stops early, positions count every pair."""
    n_scores = rng.randint(3, 4)
    names = rng.sample(NAMES, n_scores + 1)
    limit = rng.choice([70, 75, 80, 85])
    for _ in range(100):
        scores = [rng.randint(55, 99) for _ in range(n_scores)]
        hits = [s > limit for s in scores]
        if 0 < sum(hits) < n_scores and not hits[0]:
            break
    else:
        raise GenerationError("no good scores")
    var_a = "names"
    code = (
        f"{var_a} = {_src(names)}\nscores = {scores}\n"
        f"for rank, (name, score) in enumerate(zip({var_a}, scores), start=1):\n"
        f"    if score > {limit}:\n        print(rank, name)"
    )
    picked = [(i, n) for i, (n, s) in enumerate(zip(names, scores), 1) if s > limit]
    zero_based = _lines(f"{i - 1} {n}" for i, n in picked)
    renumbered = _lines(f"{j} {n}" for j, (_, n) in enumerate(picked, 1))
    with_score = _lines(f"{i} {n} {scores[i - 1]}" for i, n in picked)
    shifted = _lines(f"{i} {names[i]}" for i, _ in picked)
    distractors = [renumbered, zero_based, shifted, VALUE_ERROR, with_score]
    why = (
        f"`zip` pairs the first {n_scores} names with the {n_scores} scores (the extra name {names[-1]!r} is "
        "dropped), and `enumerate(..., start=1)` numbers EVERY pair, so each printed rank is the pair's "
        f"position in the whole list: {', '.join(f'{i} {n}' for i, n in picked)}."
    )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
