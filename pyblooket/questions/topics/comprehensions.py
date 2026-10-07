"""Question generators for the "comprehensions" topic (Comprehensions).

Covers list comprehensions (transforms, filters, ``range`` bounds and the
``len`` of the result), where the condition goes (``[a if c else b for ...]``
vs ``[a for ... if c]``), nested ``for`` clauses and their order, nested
comprehensions (tables, transposing, rows that stay empty), dict
comprehensions (key collisions, inverting a dict), set comprehensions,
generator expressions with ``sum``/``any``/``all``/``max``, generator
exhaustion, ``enumerate``/``zip`` inside comprehensions, the private scope of
the loop variable, rows built by a comprehension vs shared rows, and
rewriting a loop as a comprehension.
"""

from __future__ import annotations

import random

from ..base import (
    EASY,
    HARD,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    MEDIUM,
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

TOPIC = "comprehensions"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
TYPE_ERROR = error_choice("TypeError")
VALUE_ERROR = error_choice("ValueError")
KEY_ERROR = error_choice("KeyError")
NAME_ERROR = error_choice("NameError")
STOP_ITERATION = error_choice("StopIteration")
BLANK = "___"


# --------------------------------------------------------------------------
# Private helpers & pools
# --------------------------------------------------------------------------

# Collection name -> (loop variable name, words).  Every pool has words of
# length 3, 4 and 5 (and nothing longer) so length-based filters always work.
_WORD_POOLS = {
    "fruits": ("fruit", ["fig", "kiwi", "plum", "pear", "lime", "mango", "grape", "peach", "melon", "lemon"]),
    "pets": ("pet", ["cat", "dog", "hen", "fish", "bird", "frog", "pony", "duck", "goat", "mouse"]),
    "colors": ("color", ["red", "tan", "blue", "pink", "gold", "gray", "teal", "green", "white", "black"]),
    "words": ("word", ["sun", "sky", "moon", "star", "rain", "snow", "wind", "mist", "cloud", "storm"]),
}
# Collection name -> loop variable name, for lists of numbers.
_NUM_POOLS = [("nums", "n"), ("values", "x"), ("scores", "score"), ("ages", "age")]
_PEOPLE = ["Ava", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon"]
# Names grouped by first letter (for first-letter key collisions).
_NAMES_BY_INITIAL = {
    "A": ["Ava", "Amy", "Abe"],
    "B": ["Ben", "Bo", "Bea"],
    "C": ["Cal", "Cara", "Cy"],
    "D": ["Dev", "Dan", "Dot"],
    "E": ["Eli", "Eve", "Ed"],
}


def _src(value) -> str:
    """Python source for ``value`` (strings double-quoted, containers recursively)."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join(_src(v) for v in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(_src(v) for v in value) + ("," if len(value) == 1 else "") + ")"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_src(k)}: {_src(v)}" for k, v in value.items()) + "}"
    return repr(value)


def _and(values) -> str:
    """'1', '1 and 2', '1, 2 and 3'."""
    words = [str(v) for v in values]
    if not words:
        return "nothing"
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _bare(items) -> str:
    """A list shown WITHOUT quotes around its strings (a common misreading)."""
    return "[" + ", ".join(str(i) for i in items) + "]"


def _fake_dict(pairs) -> str:
    """A 'dict' that shows every key/value pair, duplicates included (not real output)."""
    return "{" + ", ".join(f"{k!r}: {v!r}" for k, v in pairs) + "}"


def _fits(choice: str) -> bool:
    lines = choice.split("\n")
    return (
        bool(choice.strip())
        and len(lines) <= MAX_CHOICE_LINES
        and all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines)
    )


def _run(code: str) -> str | None:
    """What ``code`` prints, or None if it raises (used to compute distractors)."""
    res = run_code(code)
    return None if res.error else res.output


def _mutants(code: str, swaps) -> list[str]:
    """Outputs of ``code`` after each (old, new) text swap: a slip students make."""
    outs = []
    for old, new in swaps:
        if old in code:
            out = _run(code.replace(old, new))
            if out:
                outs.append(out)
    return outs


def _with_error(rng: random.Random, distractors: list, err: str, p: float = 0.4) -> list:
    """Sometimes slip an error choice in among the top distractors, so questions
    whose answer IS an error don't stand out as the only ones offering one."""
    out = list(distractors)
    if rng.random() < p:
        out.insert(rng.randint(0, 2), err)
    else:
        out.append(err)
    return out


def _out(
    code: str,
    difficulty: int,
    distractors: list,
    explanation: str,
    rng: random.Random,
    *,
    prompt: str = PRINT,
    allow_error: bool = False,
) -> Question:
    ds = [d if isinstance(d, str) else str(d) for d in distractors]
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[d for d in ds if _fits(d)],
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _which(
    setup: str,
    difficulty: int,
    target,
    correct: str,
    wrongs: list[str],
    explanation: str,
    rng: random.Random,
    prompt: str | None = None,
) -> Question:
    return which_expression_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt or f"Which expression evaluates to `{target!r}`?",
        setup=setup,
        target=target,
        correct_expr=correct,
        wrong_exprs=[w for w in wrongs if _fits(w)],
        explanation=explanation,
        rng=rng,
    )


def _words(rng: random.Random, k: int, *, one_of_each_length: bool = False) -> tuple[str, str, list[str]]:
    """A collection name, its loop variable and ``k`` distinct words."""
    var = rng.choice(list(_WORD_POOLS))
    item, pool = _WORD_POOLS[var]
    if not one_of_each_length:
        return var, item, rng.sample(pool, k)
    words = [rng.choice([w for w in pool if len(w) == size]) for size in (3, 4, 5)]
    words += rng.sample([w for w in pool if w not in words], k - 3)
    rng.shuffle(words)
    return var, item, words


def _nums(rng: random.Random, k: int, lo: int = 1, hi: int = 20) -> tuple[str, str, list[int]]:
    """A collection name, its loop variable and ``k`` distinct ints in [lo, hi)."""
    var, item = rng.choice(_NUM_POOLS)
    return var, item, rng.sample(range(lo, hi), k)


def _mixed_parity(rng: random.Random, k: int, hi: int = 20) -> list[int]:
    """``k`` distinct ints in [1, hi) with at least two evens and two odds."""
    n_even = rng.randint(2, k - 2)
    nums = rng.sample(range(2, hi, 2), n_even) + rng.sample(range(1, hi, 2), k - n_even)
    rng.shuffle(nums)
    return nums


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_transform(rng: random.Random) -> Question:
    """[expr for x in ...]: apply an expression to every item (range bounds, //, str methods)."""
    style = rng.choice(["range", "range", "list", "words", "words"])
    if style == "range":
        n = rng.randint(3, 5)
        v = rng.choice(["i", "n", "x"])
        name = rng.choice(["result", "values", "numbers"])
        kind = rng.choice(["mul", "add", "square"])
        k = rng.randint(2, 5)
        if kind == "mul":
            expr, f, slip = f"{v} * {k}", (lambda x: x * k), (lambda x: x + k)
        elif kind == "add":
            expr, f, slip = f"{v} + {k}", (lambda x: x + k), (lambda x: x * k)
        else:
            expr, f, slip = f"{v} ** 2", (lambda x: x**2), (lambda x: x * 2)
        code = f"{name} = [{expr} for {v} in range({n})]\nprint({name})"
        distractors = [
            [f(x) for x in range(1, n + 1)],
            [f(x) for x in range(n + 1)],
            [slip(x) for x in range(n)],
            list(range(n)),
            [f(x) for x in range(1, n)],
        ]
        why = (
            f"`range({n})` gives {_and(range(n))}: it starts at 0 and stops BEFORE {n}. "
            f"The comprehension computes `{expr}` for each of them and collects the results in a list."
        )
    elif style == "list":
        var, item, nums = _nums(rng, 4, 1, 10)
        if all(x % 2 == 0 for x in nums) or all(x % 2 for x in nums):
            nums[0] += 1
        kind = rng.choice(["half", "parity", "mul"])
        if kind == "half":
            name, expr = "halves", f"{item} // 2"
            distractors = [
                _bare([x / 2 for x in nums]),
                [x % 2 for x in nums],
                nums,
                [x * 2 for x in nums],
            ]
            why = (
                f"`{expr}` is floor division, so each number is halved and rounded down "
                f"(e.g. {nums[0]} // 2 is {nums[0] // 2}); `/` would give floats like {nums[0] / 2}."
            )
        elif kind == "parity":
            name, expr = "remainders", f"{item} % 2"
            distractors = [
                [x // 2 for x in nums],
                [x % 2 == 0 for x in nums],
                [x for x in nums if x % 2],
                nums,
            ]
            why = (
                f"`{expr}` is the remainder after dividing by 2: 1 for odd numbers and 0 for even "
                f"ones. A comprehension WITHOUT an `if` keeps one result per item ({len(nums)} here)."
            )
        else:
            k = rng.randint(2, 4)
            name, expr = "scaled", f"{item} * {k}"
            distractors = [
                [x + k for x in nums],
                nums,
                [x**k for x in nums],
                str(sum(x * k for x in nums)),
            ]
            why = (
                f"The comprehension builds a NEW list holding `{expr}` for each item of `{var}`, "
                f"in the same order: {nums[0]} * {k} is {nums[0] * k}, and so on."
            )
        code = f"{var} = {_src(nums)}\n{name} = [{expr} for {item} in {var}]\nprint({name})"
    else:
        var, item, words = _words(rng, 3)
        kind = rng.choice(["upper", "len", "first", "last"])
        if kind == "upper":
            name, expr = "loud", f"{item}.upper()"
            result = [w.upper() for w in words]
            distractors = [_bare(result), [w.capitalize() for w in words], words, " ".join(result)]
            why = (
                f"`{expr}` returns an upper-case copy of each string, and printing a list shows its "
                f"strings WITH quotes, e.g. {result[0]!r}."
            )
        elif kind == "len":
            name, expr = "lengths", f"len({item})"
            distractors = [
                [len(words)] * len(words),
                str(len(words)),
                words,
                [len(w) - 1 for w in words],
            ]
            why = (
                f"`len({item})` is evaluated for each string in `{var}`, giving one length per word "
                f"(e.g. {words[0]!r} has {len(words[0])} letters); it is not the length of the list."
            )
        elif kind == "first":
            name, expr = "initials", f"{item}[0]"
            distractors = [[w[1] for w in words], _bare([w[0] for w in words]), [w[-1] for w in words], words]
            why = (
                f"String indexes start at 0, so `{item}[0]` is the FIRST letter of each word "
                f"(e.g. {words[0]!r} gives {words[0][0]!r})."
            )
        else:
            name, expr = "endings", f"{item}[-1]"
            distractors = [
                [w[0] for w in words],
                [w[-2] for w in words],
                _bare([w[-1] for w in words]),
                words,
            ]
            why = (
                f"Index -1 means the LAST character, so `{item}[-1]` takes the final letter of each "
                f"word (e.g. {words[0]!r} gives {words[0][-1]!r})."
            )
        code = f"{var} = {_src(words)}\n{name} = [{expr} for {item} in {var}]\nprint({name})"
    return _out(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_filter(rng: random.Random) -> Question:
    """[x for x in ... if cond]: keep only the items whose condition is True."""
    style = rng.choice(["parity", "compare", "length", "letter"])
    if style == "parity":
        var, item, _ = _nums(rng, 1)
        nums = _mixed_parity(rng, 5)
        want_even = rng.random() < 0.5
        cond = f"{item} % 2 == {0 if want_even else 1}"
        name = "evens" if want_even else "odds"
        keep = (lambda x: x % 2 == 0) if want_even else (lambda x: x % 2 == 1)
        distractors = [
            [x for x in nums if not keep(x)],
            [keep(x) for x in nums],
            [x % 2 for x in nums],
            nums,
        ]
        data = nums
        why = (
            f"The `if {cond}` clause keeps only the {'even' if want_even else 'odd'} numbers, "
            f"in their original order; the others are skipped, not replaced."
        )
    elif style == "compare":
        var, item, nums = _nums(rng, 5, 1, 30)
        k = sorted(nums)[rng.randint(1, 3)]
        op = rng.choice([">", ">=", "<", "<="])
        ops = {
            ">": lambda x: x > k,
            ">=": lambda x: x >= k,
            "<": lambda x: x < k,
            "<=": lambda x: x <= k,
        }
        flip = {">": ">=", ">=": ">", "<": "<=", "<=": "<"}[op]
        keep = ops[op]
        cond = f"{item} {op} {k}"
        name = "big" if op in (">", ">=") else "small"
        distractors = [
            [x for x in nums if ops[flip](x)],
            [x for x in nums if not keep(x)],
            [keep(x) for x in nums],
            nums,
        ]
        data = nums
        why = (
            f"Only items where `{cond}` is True are kept. {k} itself is "
            f"{'kept' if keep(k) else 'NOT kept'}, because `{k} {op} {k}` is {keep(k)}."
        )
    elif style == "length":
        var, item, words = _words(rng, 5, one_of_each_length=True)
        op, k = rng.choice(
            [(">", 3), (">", 4), (">=", 4), (">=", 5), ("<", 4), ("<", 5), ("<=", 3), ("<=", 4)]
        )
        ops = {
            ">": lambda w: len(w) > k,
            ">=": lambda w: len(w) >= k,
            "<": lambda w: len(w) < k,
            "<=": lambda w: len(w) <= k,
        }
        flip = {">": ">=", ">=": ">", "<": "<=", "<=": "<"}[op]
        keep = ops[op]
        cond = f"len({item}) {op} {k}"
        name = "long_words" if op in (">", ">=") else "short_words"
        distractors = [
            [w for w in words if ops[flip](w)],
            [w for w in words if not keep(w)],
            [len(w) for w in words if keep(w)],
            words,
        ]
        data = words
        why = (
            f"The comprehension keeps a word only when `{cond}` is True. Words with exactly {k} "
            f"letters are {'kept' if keep('x' * k) else 'dropped'} because of the `{op}`."
        )
    else:
        var, item, words = _words(rng, 4)
        letters = sorted({c for w in words for c in w if 0 < sum(c in x for x in words) < len(words)})
        if not letters:
            raise GenerationError("no letter splits the words")
        ch = rng.choice(letters)
        cond = f'"{ch}" in {item}'
        name = f"with_{ch}"

        def keep(w: str) -> bool:
            return ch in w

        distractors = [
            [w for w in words if not keep(w)],
            [keep(w) for w in words],
            [w for w in words if w.startswith(ch)],
            words,
        ]
        data = words
        why = (
            f"`{cond}` is True when the letter {ch!r} appears anywhere in the word, so only "
            f"{_and(repr(w) for w in words if keep(w))} {'is' if sum(map(keep, words)) == 1 else 'are'} kept."
        )
    code = f"{var} = {_src(data)}\n{name} = [{item} for {item} in {var} if {cond}]\nprint({name})"
    return _out(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_len_of_result(rng: random.Random) -> Question:
    """len() of a comprehension: transforms keep the count, filters shrink it, range stops early."""
    style = rng.choice(["transform", "multiples", "vowels"])
    if style == "transform":
        a = rng.randint(0, 3)
        m = rng.randint(3, 6)
        b = a + m
        k = rng.choice([2, 3, 10])
        name = {2: "doubled", 3: "tripled", 10: "tens"}[k]
        rng_src = f"range({b})" if a == 0 else f"range({a}, {b})"
        code = f"{name} = [x * {k} for x in {rng_src}]\nprint(len({name}))"
        answer = m
        distractors = [m + 1, m * k, (b - 1) * k, b if a else m - 1, m - 1]
        why = (
            f"`{rng_src}` produces {m} numbers ({a} up to {b - 1}), and a comprehension without "
            f"an `if` makes exactly one item per input. Multiplying changes the values, not how many."
        )
    elif style == "multiples":
        k = rng.choice([3, 4, 5])
        m = rng.randint(3, 6)
        b = k * m
        start0 = rng.random() < 0.4
        rng_src = f"range({b})" if start0 else f"range(1, {b})"
        code = f"multiples = [n for n in {rng_src} if n % {k} == 0]\nprint(len(multiples))"
        hits = [n for n in range(0 if start0 else 1, b) if n % k == 0]
        answer = len(hits)
        if start0:
            distractors = [answer - 1, answer + 1, b, b // k + 1]
            why = (
                f"The multiples of {k} in `{rng_src}` are {_and(hits)}. Don't forget 0 "
                f"(`0 % {k}` is 0), and {b} itself is excluded because `range` stops before it."
            )
        else:
            distractors = [answer + 1, b - 1, answer - 1, b]
            why = (
                f"The multiples of {k} in `{rng_src}` are {_and(hits)}. {b} is NOT included "
                f"because `range` stops before its end value."
            )
    else:
        word = rng.choice(
            [
                "banana",
                "papaya",
                "avocado",
                "coconut",
                "tomato",
                "potato",
                "cocoa",
                "noodle",
                "balloon",
                "kiwi",
            ]
        )
        letter = rng.choice(["ch", "c", "letter"])
        code = (
            f'word = "{word}"\n'
            f'vowels = [{letter} for {letter} in word if {letter} in "aeiou"]\n'
            "print(len(vowels))"
        )
        found = [c for c in word if c in "aeiou"]
        answer = len(found)
        distractors = [len(set(found)), len(word) - answer, len(word), answer + 1]
        why = (
            f"A list comprehension keeps EVERY matching character, repeats included: "
            f"{_and(repr(c) for c in found)}, so the list has {answer} items."
        )
    return _out(code, EASY, distractors + int_distractors(answer, rng), why, rng)


@generator(TOPIC, EASY)
def gen_set_comprehension(rng: random.Random) -> Question:
    """{expr for x in ...} builds a set: duplicates collapse (printed via sorted/len)."""
    style = rng.choice(["remainders", "lengths", "letters", "count"])
    if style == "remainders":
        var, item, _ = _nums(rng, 1)
        if rng.random() < 0.6:
            k = rng.choice([3, 4])
            nums = rng.sample(range(1, 25), 5)
            name, expr = "remainders", f"{item} % {k}"
            values = [x % k for x in nums]
        else:
            tens = rng.sample(range(1, 6), rng.randint(2, 3))
            slots = tens + [rng.choice(tens) for _ in range(5 - len(tens))]
            nums = [t * 10 + u for t, u in zip(slots, rng.sample(range(10), 5))]
            rng.shuffle(nums)
            name, expr = "tens", f"{item} // 10"
            values = [x // 10 for x in nums]
        data = nums
        show = f"sorted({name})"
    elif style == "lengths":
        var, item, _ = _words(rng, 1)
        pool = _WORD_POOLS[var][1]
        words = rng.sample(pool, 4)
        while len({len(w) for w in words}) == len(words):
            words = rng.sample(pool, 4)
        name = "sizes"
        expr = f"len({item})"
        values = [len(w) for w in words]
        data = words
        show = f"sorted({name})"
    elif style == "letters":
        word = rng.choice(["banana", "pepper", "kitten", "cocoa", "bubble", "letter", "puppy", "coffee"])
        code = f'letters = {{ch for ch in "{word}"}}\nprint(sorted(letters))'
        result = sorted(set(word))
        distractors = [sorted(word), list(dict.fromkeys(word)), list(word), len(result)]
        why = (
            f"A set keeps each value only once, so the {len(word)} letters of {word!r} collapse to "
            f"{len(result)} distinct ones; `sorted` returns them as a list in alphabetical order."
        )
        return _out(code, EASY, distractors, why, rng)
    else:
        var, item, _ = _nums(rng, 1)
        base = rng.sample(range(1, 10), 3)
        nums = base + rng.sample(base, 2)
        rng.shuffle(nums)
        k = rng.choice([2, 3, 10])
        code = f"{var} = {_src(nums)}\nscaled = {{{item} * {k} for {item} in {var}}}\nprint(len(scaled))"
        answer = len(set(nums))
        distractors = [len(nums), len(nums) * k, answer * k, answer - 1, answer + 1]
        why = (
            f"`{var}` has {len(nums)} items but only {answer} distinct values. The set comprehension "
            f"keeps each result once, so `scaled` has {answer} elements."
        )
        return _out(code, EASY, distractors, why, rng)
    distinct_first = list(dict.fromkeys(values))
    code = f"{var} = {_src(data)}\n{name} = {{{expr} for {item} in {var}}}\nprint({show})"
    distinct = sorted(set(values))
    distractors = [
        sorted(values),
        distinct_first,
        "{" + ", ".join(map(str, distinct)) + "}",
        values,
        len(set(values)),
        distinct[::-1],
    ]
    why = (
        f"The values computed are {_and(values)}, but a set keeps each value only once; "
        f"`sorted` then returns the distinct values as an ascending list: {sorted(set(values))}."
    )
    return _out(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_dict_comprehension(rng: random.Random) -> Question:
    """{key: value for ...}: what the keys and values are; looking one up."""
    style = rng.choice(["lengths", "squares", "lookup", "items"])
    if style == "lengths":
        var, item, words = _words(rng, 3, one_of_each_length=True)
        name = "sizes"
        code = f"{var} = {_src(words)}\n{name} = {{{item}: len({item}) for {item} in {var}}}\nprint({name})"
        distractors = [
            {len(w): w for w in words},
            [(w, len(w)) for w in words],
            [len(w) for w in words],
            {w: len(words) for w in words},
        ]
        why = (
            f"In `{{{item}: len({item}) ...}}` the part before the colon is the KEY (the word) "
            f"and the part after it is the VALUE (its length), e.g. {words[0]!r}: {len(words[0])}."
        )
        return _out(code, EASY, distractors, why, rng)
    if style == "squares":
        a = rng.choice([0, 1])
        b = rng.randint(3, 5)
        op, f = rng.choice(
            [("n * n", lambda n: n * n), ("n * 2", lambda n: n * 2), ("n + 10", lambda n: n + 10)]
        )
        rng_src = f"range({b})" if a == 0 else f"range(1, {b})"
        code = f"table = {{n: {op} for n in {rng_src}}}\nprint(table)"
        lo = a
        distractors = [
            {n: f(n) for n in range(lo, b + 1)},
            {n: f(n) for n in range(1 - lo, b + 1 - lo)} if lo == 0 else {n: f(n) for n in range(b)},
            {f(n): n for n in range(lo, b)},
            [f(n) for n in range(lo, b)],
        ]
        why = (
            f"`{rng_src}` gives {_and(range(lo, b))} (not {b}), and each number becomes a key "
            f"whose value is `{op}`."
        )
        return _out(code, EASY, distractors, why, rng)
    if style == "lookup":
        b = rng.randint(4, 6)
        j = rng.randint(1, b)
        op, f = rng.choice(
            [("n * n", lambda n: n * n), ("n * 10", lambda n: n * 10), ("n * 3", lambda n: n * 3)]
        )
        code = f"table = {{n: {op} for n in range({b})}}\nprint(table[{j}])"
        if j < b:
            distractors = _with_error(rng, [f(j + 1), j, f(j - 1), f(j) + 1], KEY_ERROR, p=0.6)
            why = (
                f"The keys are {_and(range(b))}, so `table[{j}]` looks up KEY {j} (not a position) "
                f"and gets its value `{op.replace('n', str(j))}` = {f(j)}."
            )
        else:
            distractors = [f(j), f(j - 1), "None", j]
            why = (
                f"`range({b})` stops before {b}, so the keys are only {_and(range(b))}. Looking up a "
                f"missing key with `[]` raises a KeyError."
            )
        return _out(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    goods = rng.sample(["tea", "jam", "pie", "bun", "egg", "nut"], 3)
    prices = {g: rng.randint(2, 9) for g in goods}
    k = rng.choice([2, 3, 10])
    code = (
        f"prices = {_src(prices)}\n"
        f"new_prices = {{item: cost * {k} for item, cost in prices.items()}}\n"
        "print(new_prices)"
    )
    distractors = [
        prices,
        {v * k: g for g, v in prices.items()},
        [v * k for v in prices.values()],
        {g * k: v for g, v in prices.items()},
    ]
    why = (
        f"`prices.items()` yields (key, value) pairs that unpack into `item` and `cost`; the new "
        f"dict keeps each key and multiplies its value by {k}."
    )
    return _out(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_comprehension_type(rng: random.Random) -> Question:
    """[] makes a list, {x} a set, {k: v} a dict and () a generator (not a tuple!)."""
    kind = rng.choice(["list", "set", "dict", "generator", "generator"])
    name = rng.choice(["data", "result", "output", "things"])
    if rng.random() < 0.5:
        v = rng.choice(["n", "x", "i"])
        source = f"range({rng.randint(3, 6)})"
        expr = rng.choice([f"{v} * 2", f"{v} + 1", f"{v} ** 2", f"{v} % 2"])
        pair = rng.choice([f"{v}: {v} * 2", f"{v}: {v} ** 2", f"{v}: str({v})"])
    else:
        _, v, words = _words(rng, 3)
        source = _src(words)
        expr = rng.choice([f"{v}.upper()", f"len({v})", f"{v}[0]"])
        pair = rng.choice([f"{v}: len({v})", f"{v}[0]: {v}", f"{v}: {v}.upper()"])
    body = pair if kind == "dict" else expr
    left, right = {"list": "[]", "set": "{}", "dict": "{}", "generator": "()"}[kind]
    code = f"{name} = {left}{body} for {v} in {source}{right}\nprint(type({name}))"
    others = {
        "list": ["tuple", "set", "generator", "dict"],
        "set": ["dict", "list", "tuple", "generator"],
        "dict": ["set", "list", "tuple", "generator"],
        "generator": ["tuple", "list", "set", "dict"],
    }[kind]
    why = {
        "list": "Square brackets around a comprehension build a list.",
        "set": (
            "Curly braces around a single expression (no `key: value`) build a SET; "
            "only the `key: value` form builds a dict."
        ),
        "dict": "Curly braces with a `key: value` pair before the `for` build a dict.",
        "generator": (
            "There is no tuple comprehension: parentheses make a generator expression, which "
            "produces its values lazily. Use `tuple(...)` around it to get a tuple."
        ),
    }[kind]
    return _out(code, EASY, [f"<class '{t}'>" for t in others], why, rng)


@generator(TOPIC, EASY)
def gen_sum_generator(rng: random.Random) -> Question:
    """sum(expr for x in ...): a generator expression fed straight into sum()."""
    style = rng.choice(["range", "lengths", "filtered"])
    if style == "range":
        a = rng.randint(1, 3)
        b = a + rng.randint(3, 4)
        k = rng.choice([2, 3, 10])
        code = f"total = sum(n * {k} for n in range({a}, {b}))\nprint(total)"
        answer = sum(n * k for n in range(a, b))
        distractors = [
            sum(n * k for n in range(a, b + 1)),
            sum(range(a, b)),
            [n * k for n in range(a, b)],
            sum(n * k for n in range(a + 1, b)),
        ]
        why = (
            f"`range({a}, {b})` gives {_and(range(a, b))} (it stops before {b}); each is multiplied "
            f"by {k} and `sum` adds the results: {' + '.join(str(n * k) for n in range(a, b))} = {answer}."
        )
    elif style == "lengths":
        var, item, words = _words(rng, rng.randint(3, 4))
        code = f"{var} = {_src(words)}\ntotal = sum(len({item}) for {item} in {var})\nprint(total)"
        lengths = [len(w) for w in words]
        answer = sum(lengths)
        distractors = [len(words), lengths, max(lengths), answer + 1]
        why = (
            f"The generator expression yields each word's length ({_and(lengths)}) and `sum` adds "
            f"them up to {answer}; `len({var})` would only count the words."
        )
    else:
        var, item, nums = _nums(rng, 5, 1, 20)
        k = sorted(nums)[rng.randint(1, 2)]
        code = f"{var} = {_src(nums)}\ntotal = sum({item} for {item} in {var} if {item} > {k})\nprint(total)"
        picked = [x for x in nums if x > k]
        answer = sum(picked)
        distractors = [
            sum(x for x in nums if x >= k),
            sum(nums),
            len(picked),
            sum(x for x in nums if x <= k),
        ]
        why = (
            f"Only values greater than {k} reach `sum`: {_and(picked)}, giving {answer}. "
            f"{k} itself is skipped because `{k} > {k}` is False."
        )
    return _out(code, EASY, distractors + int_distractors(answer, rng), why, rng)


# ==========================================================================
# MEDIUM
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_if_else_vs_filter(rng: random.Random) -> Question:
    """[a if c else b for x in xs] keeps every item; [a for x in xs if c] drops some."""
    var, item, nums = _nums(rng, 5, 1, 16)
    k = sorted(nums)[rng.randint(1, 3)]
    cond = f"{item} > {k}"
    big = [x for x in nums if x > k]
    form = rng.choice(["zero", "label", "filter", "pick", "pick"])
    head = f"{var} = {_src(nums)}\n"
    if form == "zero":
        code = head + f"result = [{item} if {cond} else 0 for {item} in {var}]\nprint(result)"
        distractors = [
            big,
            [0 if x > k else x for x in nums],
            [x if x >= k else 0 for x in nums],
            [x if x < k else 0 for x in nums],
        ]
        why = (
            f"An `if ... else` BEFORE the `for` is a conditional expression applied to every item, "
            f"so the result still has {len(nums)} items: values not greater than {k} become 0."
        )
        return _out(code, MEDIUM, distractors, why, rng)
    if form == "label":
        yes, no = rng.choice([("big", "small"), ("high", "low"), ("yes", "no"), ("pass", "fail")])
        code = head + f'labels = ["{yes}" if {cond} else "{no}" for {item} in {var}]\nprint(labels)'
        distractors = [
            [no if x > k else yes for x in nums],
            [yes for x in nums if x > k],
            [yes if x >= k else no for x in nums],
            [x > k for x in nums],
        ]
        why = (
            f"Each item is replaced by {yes!r} or {no!r}, so all {len(nums)} items stay. "
            f"{k} gets {no!r} because `{k} > {k}` is False."
        )
        return _out(code, MEDIUM, distractors, why, rng)
    if form == "filter":
        m = rng.choice([2, 10])
        code = head + f"result = [{item} * {m} for {item} in {var} if {cond}]\nprint(result)"
        distractors = [
            [x * m if x > k else x for x in nums],
            [x * m if x > k else 0 for x in nums],
            big,
            [x * m for x in nums if x >= k],
        ]
        why = (
            f"An `if` AFTER the `for` is a filter: items not greater than {k} are dropped "
            f"entirely (not kept unchanged), and only {_and(big)} are multiplied by {m}."
        )
        return _out(code, MEDIUM, distractors, why, rng)
    setup = head.strip()
    if rng.random() < 0.5:
        target = [x if x > k else 0 for x in nums]
        correct = f"[{item} if {cond} else 0 for {item} in {var}]"
        wrongs = [
            f"[{item} for {item} in {var} if {cond} else 0]",
            f"[{item} for {item} in {var} if {cond}]",
            f"[0 if {cond} else {item} for {item} in {var}]",
            f"[{item} if {item} >= {k} else 0 for {item} in {var}]",
            f"[{cond} for {item} in {var}]",
        ]
        why = (
            f"To REPLACE some items (keeping all {len(nums)}), the `if ... else` goes before the "
            f"`for`. An `else` after the `for` is a SyntaxError, and a trailing `if` alone filters."
        )
    else:
        target = big
        correct = f"[{item} for {item} in {var} if {cond}]"
        wrongs = [
            f"[{item} if {cond} for {item} in {var}]",
            f"[{item} if {cond} else 0 for {item} in {var}]",
            f"[{cond} for {item} in {var}]",
            f"[{item} for {item} in {var} if {item} >= {k}]",
            f"[{item} for {item} in {var} if {item} < {k}]",
        ]
        why = (
            f"A filter goes AFTER the `for`: `if {cond}` drops the other items. An `if` without "
            f"`else` before the `for` is a SyntaxError, and `[{cond} ...]` collects booleans."
        )
    return _which(setup, MEDIUM, target, correct, wrongs, why, rng)


@generator(TOPIC, MEDIUM)
def gen_nested_loop_order(rng: random.Random) -> Question:
    """Several for clauses nest left to right: the first is the OUTER loop."""
    style = rng.choice(["codes", "flatten", "count"])
    if style == "codes":
        n_letters, n_digits = rng.choice([(2, 2), (2, 3), (3, 2)])
        letters = "".join(rng.sample("ABCDEFGHJKMNPRSTXYZ", n_letters))
        digits = "".join(sorted(rng.sample("123456789", n_digits)))
        code = f'codes = [letter + digit for letter in "{letters}" for digit in "{digits}"]\nprint(codes)'
        correct = [a + b for a in letters for b in digits]
        distractors = [
            [a + b for b in digits for a in letters],
            [a + b for a, b in zip(letters, digits)],
            [b + a for a in letters for b in digits],
            [[a + b for b in digits] for a in letters],
        ]
        why = (
            f"`for` clauses nest left to right, so `letter` is the OUTER loop: every digit is paired "
            f"with {letters[0]!r} first ({_and(repr(c) for c in correct[:n_digits])}) before moving on."
        )
        return _out(code, MEDIUM, distractors, why, rng)
    if style == "flatten":
        rows, cols = rng.choice([(3, 2), (2, 3)])
        while True:
            vals = rng.sample(range(1, 20), rows * cols)
            grid = [vals[r * cols : (r + 1) * cols] for r in range(rows)]
            kind = rng.choice(["even", "big"])
            if kind == "even":
                keep, cond = (lambda x: x % 2 == 0), "x % 2 == 0"
                name = "evens"
            else:
                k = sorted(vals)[len(vals) // 2]
                keep, cond = (lambda x, k=k: x > k), f"x > {k}"
                name = "big"
            row_major = [x for row in grid for x in row if keep(x)]
            col_major = [grid[r][c] for c in range(cols) for r in range(rows) if keep(grid[r][c])]
            if 2 <= len(row_major) < len(vals) and row_major != col_major:
                break
        code = f"grid = {grid}\n{name} = [x for row in grid for x in row if {cond}]\nprint({name})"
        distractors = [
            col_major,
            [[x for x in row if keep(x)] for row in grid],
            [x for row in grid for x in row],
            [row for row in grid if any(keep(x) for x in row)],
        ]
        why = (
            "The first `for` takes each row, the second walks through that row, and the `if` "
            "filters single values. The result is ONE flat list in reading order, row by row."
        )
        return _out(code, MEDIUM, distractors, why, rng)
    m, n = rng.choice([(2, 3), (3, 2), (2, 4), (4, 2), (3, 4)])
    va, vb = rng.choice([("a", "b"), ("i", "j"), ("row", "col")])
    pairs = [(a, b) for a in range(m) for b in range(n)]
    alt = [(a, b) for b in range(n) for a in range(m)]
    idx = rng.choice([i for i in range(1, m * n - 1) if pairs[i] != alt[i]])
    code = f"pairs = [({va}, {vb}) for {va} in range({m}) for {vb} in range({n})]\nprint(len(pairs), pairs[{idx}])"
    total = m * n
    distractors = [
        f"{total} {alt[idx]}",
        f"{total} {pairs[idx - 1]}",
        f"{m + n} {pairs[idx]}",
        f"{total} {pairs[idx + 1]}",
        f"{m + n} {alt[idx]}",
    ]
    why = (
        f"The inner loop over `{vb}` runs completely for each `{va}`, giving {m} x {n} = {total} pairs "
        f"in the order {pairs[0]}, {pairs[1]}, ...; index {idx} is the {_ordinal(idx + 1)} pair, {pairs[idx]}."
    )
    return _out(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_dict_key_collision(rng: random.Random) -> Question:
    """Repeated keys in a dict comprehension: the LAST value wins, at the FIRST key's spot."""
    style = rng.choice(["length", "initial", "mod", "count"])
    if style == "length":
        var, item, _ = _words(rng, 1)
        pool = _WORD_POOLS[var][1]
        for _ in range(100):
            words = rng.sample(pool, 4)
            keys = [len(w) for w in words]
            if len(set(keys)) in (2, 3):
                break
        else:
            raise GenerationError("no colliding word lengths")
        name = "by_length"
        code = f"{var} = {_src(words)}\n{name} = {{len({item}): {item} for {item} in {var}}}\nprint({name})"
        pairs = [(len(w), w) for w in words]
    elif style == "initial":
        letters = rng.sample(list(_NAMES_BY_INITIAL), 2)
        names = rng.sample(_NAMES_BY_INITIAL[letters[0]], 2) + rng.sample(
            _NAMES_BY_INITIAL[letters[1]], rng.randint(1, 2)
        )
        rng.shuffle(names)
        name = "by_initial"
        code = f"names = {_src(names)}\n{name} = {{name[0]: name for name in names}}\nprint({name})"
        pairs = [(w[0], w) for w in names]
    else:
        var, item, _ = _nums(rng, 1)
        k = 3
        for _ in range(100):
            nums = rng.sample(range(1, 20), 5)
            keys = [x % k for x in nums]
            if len(set(keys)) in (2, 3):
                break
        name = "by_remainder"
        pairs = [(x % k, x) for x in nums]
        if style == "count":
            dup_key = rng.choice([key for key in set(keys) if keys.count(key) > 1])
            code = (
                f"{var} = {_src(nums)}\n{name} = {{{item} % {k}: {item} for {item} in {var}}}\n"
                f"print(len({name}), {name}[{dup_key}])"
            )
            last = {key: v for key, v in pairs}
            first = {}
            for key, v in pairs:
                first.setdefault(key, v)
            distractors = _with_error(
                rng,
                [
                    f"{len(nums)} {last[dup_key]}",
                    f"{len(last)} {first[dup_key]}",
                    f"{len(nums)} {first[dup_key]}",
                    f"{len(last)} {[v for key, v in pairs if key == dup_key]}",
                ],
                KEY_ERROR,
                p=0.3,
            )
            why = (
                f"The keys are the remainders {_and(keys)}, so only {len(last)} distinct keys survive. "
                f"Each repeated key is overwritten, so key {dup_key} ends up holding the LAST "
                f"number with that remainder, {last[dup_key]}."
            )
            return _out(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
        code = f"{var} = {_src(nums)}\n{name} = {{{item} % {k}: {item} for {item} in {var}}}\nprint({name})"
    last = {key: v for key, v in pairs}
    first: dict = {}
    for key, v in pairs:
        first.setdefault(key, v)
    last_order = {key: last[key] for key in reversed(list(dict.fromkeys(k for k, _ in reversed(pairs))))}
    grouped: dict = {}
    for key, v in pairs:
        grouped.setdefault(key, []).append(v)
    distractors = _with_error(
        rng, [str(first), _fake_dict(pairs), str(last_order), str(grouped)], KEY_ERROR, p=0.3
    )
    keys = [key for key, _ in pairs]
    dup = next(key for key in keys if keys.count(key) > 1)
    why = (
        f"Assigning to an existing key REPLACES its value, so key {dup!r} keeps only the last value, "
        f"{last[dup]!r}. The key stays at the position where it was FIRST inserted."
    )
    return _out(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_enumerate_zip(rng: random.Random) -> Question:
    """enumerate (starts at 0 unless told otherwise) and zip (stops at the shortest) in comprehensions."""
    style = rng.choice(["index_mul", "numbered", "zip_short", "dict_zip", "no_enumerate", "positions"])
    if style == "index_mul":
        var, item, nums = _nums(rng, 4, 1, 10)
        code = f"{var} = {_src(nums)}\nresult = [i * {item} for i, {item} in enumerate({var})]\nprint(result)"
        distractors = _with_error(
            rng,
            [[(i + 1) * x for i, x in enumerate(nums)], [x * x for x in nums], list(range(len(nums)))],
            TYPE_ERROR,
        )
        why = (
            f"`enumerate` yields (index, item) pairs starting at index 0, so the first item "
            f"{nums[0]} is multiplied by 0, the next by 1, and so on."
        )
    elif style == "numbered":
        var, item, words = _words(rng, 3)
        start = rng.choice([None, 1])
        args = f"{var}" if start is None else f"{var}, 1"
        s = 0 if start is None else 1
        sep = rng.choice(["-", ":", "."])
        code = (
            f"{var} = {_src(words)}\n"
            f'labels = [f"{{i}}{sep}{{{item}}}" for i, {item} in enumerate({args})]\n'
            "print(labels)"
        )
        distractors = _with_error(
            rng,
            [
                [f"{i}{sep}{w}" for i, w in enumerate(words, 1 - s)],
                [f"{w}{sep}{i}" for i, w in enumerate(words, s)],
                [f"{i}{sep}{w}" for i, w in enumerate(words, 2 - s)],
            ],
            VALUE_ERROR,
        )
        why = (
            f"`enumerate({args})` numbers the items starting at {s}"
            + (" (the default)" if start is None else " because of the second argument")
            + f", and each pair unpacks into `i` and `{item}`."
        )
    elif style == "zip_short":
        xs = rng.sample(range(1, 10), rng.randint(3, 4))
        ys = [d * 10 for d in rng.sample(range(1, 10), len(xs) + rng.choice([-1, 1]))]
        code = f"xs = {xs}\nys = {ys}\nsums = [x + y for x, y in zip(xs, ys)]\nprint(sums)"
        longer = xs if len(xs) > len(ys) else ys
        n = min(len(xs), len(ys))
        sums = [x + y for x, y in zip(xs, ys)]
        distractors = [
            VALUE_ERROR,
            sums + [longer[-1]],
            [x + y for x in xs for y in ys],
            [x + y for x, y in zip(xs[1:], ys[1:])],
        ]
        why = (
            f"`zip` pairs items position by position and STOPS at the shorter list, so only "
            f"{n} sums are made; the extra {longer[-1]} is silently ignored (no error)."
        )
    elif style == "dict_zip":
        people = rng.sample(_PEOPLE, 3)
        scores = rng.sample(range(5, 10), 2)
        code = (
            f"names = {_src(people)}\nscores = {scores}\n"
            "table = {name: score for name, score in zip(names, scores)}\nprint(table)"
        )
        distractors = [
            _fake_dict(list(zip(people, scores)) + [(people[2], None)]),
            VALUE_ERROR,
            {s: p for p, s in zip(people, scores)},
            _fake_dict(list(zip(people, scores)) + [(people[2], 0)]),
        ]
        why = (
            f"`zip` stops as soon as the shorter list (`scores`, {len(scores)} items) runs out, so "
            f"{people[2]!r} never gets paired and is left out of the dict."
        )
    elif style == "no_enumerate":
        var, item, nums = _nums(rng, 3, 2, 10)
        code = f"{var} = {_src(nums)}\nresult = [i * {item} for i, {item} in {var}]\nprint(result)"
        distractors = [
            [i * x for i, x in enumerate(nums)],
            VALUE_ERROR,
            [(i + 1) * x for i, x in enumerate(nums)],
            [x * x for x in nums],
        ]
        why = (
            f"Without `enumerate`, each item of `{var}` is a single int such as {nums[0]}, and an "
            f"int cannot be unpacked into `i, {item}`, so Python raises a TypeError."
        )
    else:
        var, item, nums = _nums(rng, 5, 1, 20)
        k = sorted(nums)[rng.randint(1, 3)]
        code = (
            f"{var} = {_src(nums)}\n"
            f"positions = [i for i, {item} in enumerate({var}) if {item} > {k}]\n"
            "print(positions)"
        )
        hits = [i for i, x in enumerate(nums) if x > k]
        distractors = _with_error(
            rng,
            [[x for x in nums if x > k], [i + 1 for i in hits], [(i, nums[i]) for i in hits]],
            TYPE_ERROR,
        )
        why = (
            f"The comprehension collects `i`, the INDEX, for each item greater than {k}; indexes "
            f"start at 0, so the matches {_and(nums[i] for i in hits)} sit at positions {_and(hits)}."
        )
    return _out(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_generator_reductions(rng: random.Random) -> Question:
    """any/all/max/sum over generator expressions (incl. sum(1 for ...) and summing booleans)."""
    style = rng.choice(["any_all", "max_len", "count_ones", "sum_bools"])
    var, item, nums = _nums(rng, 5, 1, 20)
    head = f"{var} = {_src(nums)}\n"
    if style == "any_all":
        lo, hi = min(nums), max(nums)
        any_true = rng.random() < 0.5
        all_true = rng.random() < 0.5
        a = rng.choice(sorted(nums)[1:]) - 1 if any_true else hi + rng.randint(0, 2)
        b = lo - rng.randint(1, 2) if all_true else rng.choice(sorted(nums)[1:4])
        code = head + (
            f"has_big = any({item} > {a} for {item} in {var})\n"
            f"all_big = all({item} > {b} for {item} in {var})\n"
            "print(has_big, all_big)"
        )
        r_any = any(x > a for x in nums)
        r_all = all(x > b for x in nums)
        combos = [f"{r_any} {not r_all}", f"{not r_any} {r_all}", f"{not r_any} {not r_all}"]
        why = (
            f"`any` is True if AT LEAST ONE item is greater than {a} "
            f"({'e.g. ' + str(max(nums)) if r_any else 'none is'}); `all` is True only if EVERY item is "
            f"greater than {b} ({'the smallest is ' + str(lo) if r_all else str(lo) + ' is not'})."
        )
        return _out(code, MEDIUM, combos, why, rng)
    if style == "max_len":
        var, item, words = _words(rng, 4)
        code = f"{var} = {_src(words)}\nprint(max(len({item}) for {item} in {var}))"
        lengths = [len(w) for w in words]
        longest = max(words, key=len)
        answer = max(lengths)
        distractors = [longest, len(words), sum(lengths), min(lengths), max(words)]
        why = (
            f"The generator expression yields the lengths {_and(lengths)}, so `max` returns the "
            f"largest NUMBER, {answer}, not the word {longest!r} itself."
        )
        return _out(code, MEDIUM, distractors + int_distractors(answer, rng), why, rng)
    if style == "count_ones":
        nums = _mixed_parity(rng, 5)
        head = f"{var} = {_src(nums)}\n"
        odd = rng.random() < 0.5
        cond = f"{item} % 2 == 1" if odd else f"{item} % 2 == 0"
        hits = [x for x in nums if (x % 2 == 1) == odd]
        code = head + f"count = sum(1 for {item} in {var} if {cond})\nprint(count)"
        answer = len(hits)
        distractors = [sum(hits), len(nums), len(nums) - answer, 1]
        why = (
            f"The generator yields the number 1 (not the item) for each match: "
            f"{_and(hits)} match, so `sum` adds {answer} ones and gives {answer}."
        )
        return _out(code, MEDIUM, distractors + int_distractors(answer, rng), why, rng)
    k = sorted(nums)[rng.randint(1, 3)]
    code = head + f"print(sum({item} > {k} for {item} in {var}))"
    hits = [x for x in nums if x > k]
    answer = len(hits)
    distractors = [sum(hits), TYPE_ERROR, "True", len(nums) - answer]
    why = (
        f"`{item} > {k}` produces True or False, and `True` counts as 1 when summed, so the result "
        f"is how many items are greater than {k}: {answer}."
    )
    return _out(
        code,
        MEDIUM,
        distractors + int_distractors(answer, rng),
        why,
        rng,
        prompt=PRINT_OR_ERROR,
        allow_error=True,
    )


@generator(TOPIC, MEDIUM)
def gen_loop_equivalent(rng: random.Random) -> Question:
    """Which comprehension builds the same list as this for loop?"""
    style = rng.choice(["filter_map", "if_else", "nested"])
    prompt = "Which comprehension builds the same list as `result`?"
    if style == "filter_map":
        var, item, _ = _nums(rng, 1)
        nums = _mixed_parity(rng, 5)
        cond = rng.choice([f"{item} % 2 == 0", f"{item} % 2 == 1"])
        expr = rng.choice([f"{item} * 10", f"{item} + 1", f"{item} * {item}"])
        setup = (
            f"{var} = {_src(nums)}\nresult = []\nfor {item} in {var}:\n"
            f"    if {cond}:\n        result.append({expr})"
        )
        correct = f"[{expr} for {item} in {var} if {cond}]"
        wrongs = [
            f"[{expr} if {cond} for {item} in {var}]",
            f"[{expr} if {cond} else {item} for {item} in {var}]",
            f"[{item} for {item} in {var} if {cond}]",
            f"[{expr} for {item} in {var}]",
            f"[{cond} for {item} in {var}]",
        ]
        why = (
            f"The loop appends `{expr}` only when `{cond}`; in a comprehension the value goes first "
            f"and the filter `if {cond}` goes after the `for`."
        )
    elif style == "if_else":
        var, item, nums = _nums(rng, 5, 1, 16)
        k = sorted(nums)[rng.randint(1, 3)]
        other = rng.choice(["0", f"-{item}", "None"])
        setup = (
            f"{var} = {_src(nums)}\nresult = []\nfor {item} in {var}:\n    if {item} > {k}:\n"
            f"        result.append({item})\n    else:\n        result.append({other})"
        )
        correct = f"[{item} if {item} > {k} else {other} for {item} in {var}]"
        wrongs = [
            f"[{item} for {item} in {var} if {item} > {k} else {other}]",
            f"[{item} for {item} in {var} if {item} > {k}]",
            f"[{other} if {item} > {k} else {item} for {item} in {var}]",
            f"[{item} if {item} > {k} else {other} for {item} in {var} if {item} > {k}]",
        ]
        why = (
            f"Every item produces something (either `{item}` or `{other}`), so this needs a conditional "
            f"expression BEFORE the `for`, not a filter after it."
        )
    else:
        xs = rng.sample(range(1, 6), rng.randint(2, 3))
        ys = rng.sample(range(6, 10), 5 - len(xs))
        setup = (
            f"xs = {xs}\nys = {ys}\nresult = []\nfor a in xs:\n    for b in ys:\n"
            "        result.append((a, b))"
        )
        correct = "[(a, b) for a in xs for b in ys]"
        wrongs = [
            "[(a, b) for b in ys for a in xs]",
            "[(a, b) for a, b in zip(xs, ys)]",
            "[[(a, b) for b in ys] for a in xs]",
            "[(a, b) for a in xs if b in ys]",
        ]
        why = (
            "Write the `for` clauses in the same order as the loops: the outer loop (`for a in xs`) "
            "comes first. Swapping them changes the order of the pairs."
        )
    target = run_code(setup).namespace["result"]
    return _which(setup, MEDIUM, target, correct, wrongs, why, rng, prompt=prompt)


@generator(TOPIC, MEDIUM)
def gen_fill_blank(rng: random.Random) -> Question:
    """Which expression completes the comprehension so it prints the given list? (verified by running)."""
    style = rng.choice(["filter", "transform", "words"])
    if style == "filter":
        var, item, _ = _nums(rng, 1)
        nums = _mixed_parity(rng, 5, 16)
        k = sorted(nums)[rng.randint(1, 3)]
        i = item
        near = {
            f"{i} % 2 == 0": [f"{i} % 2", f"{i} % 2 == 1", f"{i} // 2 == 0", f"{i} > {k}"],
            f"{i} % 2 == 1": [f"{i} % 2 == 0", f"{i} // 2 == 1", f"{i} > {k}", f"{i} % 1 == 0"],
            f"{i} > {k}": [f"{i} >= {k}", f"{i} < {k}", f"{i} <= {k}", f"{i} % 2 == 0"],
            f"{i} >= {k}": [f"{i} > {k}", f"{i} <= {k}", f"{i} < {k}", f"{i} % 2 == 1"],
            f"{i} < {k}": [f"{i} <= {k}", f"{i} > {k}", f"{i} >= {k}", f"{i} % 2 == 0"],
        }
        correct = rng.choice(list(near))
        template = f"{var} = {_src(nums)}\npicked = [{i} for {i} in {var} if {BLANK}]\nprint(picked)"
    elif style == "transform":
        var, item, _ = _nums(rng, 1)
        nums = _mixed_parity(rng, 4, 16)
        i = item
        near = {
            f"{i} // 2": [f"{i} / 2", f"{i} % 2", f"{i} - 2"],
            f"{i} / 2": [f"{i} // 2", f"{i} % 2", f"{i} - 2"],
            f"{i} % 2": [f"{i} // 2", f"{i} / 2", f"{i} - 2"],
            f"{i} % 3": [f"{i} // 3", f"{i} - 3", f"{i} % 2"],
            f"{i} // 3": [f"{i} % 3", f"{i} - 3", f"{i} // 2"],
        }
        correct = rng.choice(list(near))
        template = f"{var} = {_src(nums)}\nresult = [{BLANK} for {i} in {var}]\nprint(result)"
    else:
        var, item, words = _words(rng, 3)
        i = item
        near = {
            f"{i}[0].upper()": [f"{i}.upper()", f"{i}[1].upper()", f"{i}[0]", f"{i}[-1].upper()"],
            f"{i}[-1]": [f"{i}[0]", f"{i}[1]", f"{i}[-2]", f"{i}[:-1]"],
            f"{i}[:2]": [f"{i}[1:2]", f"{i}[0:1]", f"{i}[2:]", f"{i}[1:3]"],
            f"{i}[1:]": [f"{i}[2:]", f"{i}[:1]", f"{i}[1]", f"{i}[:-1]"],
            f"{i}.capitalize()": [f"{i}.upper()", f"{i}[0].upper()", f"{i}.title()[0]", f"{i}[0]"],
        }
        correct = rng.choice(list(near))
        template = f"{var} = {_src(words)}\nresult = [{BLANK} for {i} in {var}]\nprint(result)"
    target = _run(template.replace(BLANK, correct))
    if not target:
        raise GenerationError("blank template failed")
    wrongs = []
    outputs = {}
    for cand in near[correct]:
        out = _run(template.replace(BLANK, cand))
        if out != target:
            wrongs.append(cand)
            outputs[cand] = out
    if len(wrongs) < 3:
        raise GenerationError("not enough wrong fillers")
    w0 = wrongs[0]
    why = f"With `{correct}` the comprehension prints `{target}`. " + (
        f"`{w0}` would print `{outputs[w0]}` instead."
        if outputs[w0] and len(outputs[w0]) <= 40
        else f"`{w0}` would not give that output."
    )
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which choice fills the blank `{BLANK}` so the code prints `{target}`?",
        correct=correct,
        distractors=wrongs,
        explanation=why,
        rng=rng,
        code=template,
    )


@generator(TOPIC, MEDIUM)
def gen_variable_scope(rng: random.Random) -> Question:
    """A comprehension's loop variable is private to it (unlike a for loop's)."""
    style = rng.choice(["shadow", "shadow", "after_comp", "after_comp", "loop_vs_comp"])
    if style == "shadow":
        v = rng.choice(["x", "n", "i"])
        outer = rng.randint(5, 20)
        n = rng.randint(3, 4)
        expr, f = rng.choice(
            [(f"{v} * {v}", lambda t: t * t), (f"{v} + 1", lambda t: t + 1), (f"{v} * 2", lambda t: t * 2)]
        )
        code = f"{v} = {outer}\nresult = [{expr} for {v} in range({n})]\nprint({v}, result)"
        res = [f(t) for t in range(n)]
        distractors = [
            f"{n - 1} {res}",
            f"{outer} {[f(outer)] * n}",
            f"{n} {res}",
            NAME_ERROR,
        ]
        why = (
            f"The `{v}` inside the comprehension is its own local variable: it runs over "
            f"{_and(range(n))} without touching the outer `{v}`, which is still {outer}."
        )
    elif style == "after_comp":
        people = rng.sample(_PEOPLE, 3)
        var = rng.choice(["name", "person"])
        method = rng.choice(["upper", "lower"])
        pre = rng.random() < 0.5
        other = rng.choice([p for p in _PEOPLE if p not in people])
        code = (
            f'{var} = "{other}"\n' if pre else ""
        ) + f"names = {_src(people)}\nchanged = [{var}.{method}() for {var} in names]\nprint({var})"
        last = people[-1]
        distractors = [last, getattr(last, method)(), NAME_ERROR if pre else "None", people[0]]
        if pre:
            why = (
                f"The comprehension's `{var}` is private to the comprehension, so after it finishes "
                f"`{var}` still refers to the outer value {other!r}."
            )
        else:
            why = (
                f"A comprehension's loop variable does not leak out (unlike a `for` loop's), so "
                f"`{var}` was never defined at the top level and `print({var})` raises a NameError."
            )
    else:
        n = rng.randint(3, 5)
        m = rng.randint(4, 8)
        which = rng.choice(["i", "j"])
        code = (
            f"total = 0\nfor i in range({n}):\n    total += i\n"
            f"evens = [j for j in range({m}) if j % 2 == 0]\nprint({which})"
        )
        if which == "i":
            distractors = [NAME_ERROR, n, 0, sum(range(n))]
            why = (
                f"A `for` loop's variable stays defined after the loop and keeps its last value: "
                f"`range({n})` ends at {n - 1}, so `i` is {n - 1}."
            )
        else:
            evens = [j for j in range(m) if j % 2 == 0]
            distractors = [max(evens), m - 1, evens, m, n - 1, 0]
            why = (
                "Unlike a `for` loop's variable, the `j` in a comprehension exists only inside the "
                "comprehension, so `print(j)` raises a NameError."
            )
    return _out(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


# ==========================================================================
# HARD
# ==========================================================================


@generator(TOPIC, HARD)
def gen_generator_exhaustion(rng: random.Random) -> Question:
    """A generator can be consumed only once: second passes, `in`, next() and break all use it up."""
    style = rng.choice(["sum_twice", "list_twice", "in_check", "next_rest", "max_after_sum", "break_rest"])
    if style == "sum_twice":
        a, b = rng.randint(1, 2), rng.randint(4, 5)
        expr, f, name = rng.choice(
            [
                ("n * n", lambda n: n * n, "squares"),
                ("n * 2", lambda n: n * 2, "doubles"),
                ("n + 10", lambda n: n + 10, "shifted"),
            ]
        )
        code = f"{name} = ({expr} for n in range({a}, {b}))\nprint(sum({name}))\nprint(sum({name}))"
        s = sum(f(n) for n in range(a, b))
        distractors = [f"{s}\n{s}", STOP_ITERATION, f"{s}\n{2 * s}", f"{s}\nNone"]
        why = (
            f"The first `sum` pulls every value out of the generator ({s}). A generator can't be "
            f"rewound, so the second `sum` sees nothing and returns 0 (no error)."
        )
    elif style == "list_twice":
        var, item, _ = _nums(rng, 1)
        nums = _mixed_parity(rng, 5)
        keep_even = rng.random() < 0.5
        cond = f"{item} % 2 == {0 if keep_even else 1}"
        name = "evens" if keep_even else "odds"
        picked = [x for x in nums if (x % 2 == 0) == keep_even]
        code = (
            f"{var} = {_src(nums)}\n{name} = ({item} for {item} in {var} if {cond})\n"
            f"print(list({name}))\nprint(list({name}))"
        )
        distractors = [f"{picked}\n{picked}", STOP_ITERATION, f"{picked}\nNone", f"{picked}\n{picked * 2}"]
        why = (
            "The first `list(...)` exhausts the generator. A generator doesn't remember its values, "
            "so the second `list(...)` gets nothing and prints `[]`; only a list could be reused."
        )
    elif style == "in_check":
        a = rng.randint(1, 2)
        b = a + rng.randint(5, 6)
        k = rng.choice([2, 3])
        values = [n * k for n in range(a, b)]
        present = rng.random() < 0.65
        target = (
            rng.choice(values[1:-2])
            if present
            else rng.choice([v for v in range(values[1], values[-1]) if v not in values])
        )
        name = rng.choice(["gen", "values", "multiples"])
        code = f"{name} = (n * {k} for n in range({a}, {b}))\nprint({target} in {name})\nprint(list({name}))"
        if present:
            rest = values[values.index(target) + 1 :]
            distractors = [
                f"True\n{values}",
                f"True\n{values[values.index(target) :]}",
                "True\n[]",
                f"False\n{rest}",
            ]
            why = (
                f"`in` pulls values from the generator until it finds {target}, consuming everything up "
                f"to and including it; `list` then gets only what is left: {rest}."
            )
        else:
            distractors = [f"False\n{values}", "False\nNone", STOP_ITERATION, f"True\n{values}"]
            why = (
                f"{target} is not one of the values, so `in` has to consume the WHOLE generator while "
                f"searching; nothing is left for `list`, which returns `[]`."
            )
    elif style == "next_rest":
        var, item, words = _words(rng, 3)
        method = rng.choice(["upper", "capitalize"])
        changed = [getattr(w, method)() for w in words]
        code = (
            f"{var} = {_src(words)}\nchanged = ({item}.{method}() for {item} in {var})\n"
            f"first = next(changed)\nrest = list(changed)\nprint(first, rest)"
        )
        distractors = [
            f"{changed[0]} {changed}",
            f"{[changed[0]]} {changed[1:]}",
            f"{changed[0]} []",
            TYPE_ERROR,
        ]
        why = (
            f"`next` takes ONE value ({changed[0]!r}) out of the generator, so `list` only receives "
            f"the remaining {len(words) - 1} values."
        )
    elif style == "max_after_sum":
        a, b = rng.randint(1, 2), rng.randint(4, 6)
        k = rng.choice([2, 3, 5])
        brackets = rng.choice(["()", "[]"])
        name = rng.choice(["scores", "points", "values"])
        vals = [n * k for n in range(a, b)]
        code = (
            f"{name} = {brackets[0]}n * {k} for n in range({a}, {b}){brackets[1]}\n"
            f"total = sum({name})\nprint(total, max({name}))"
        )
        if brackets == "()":
            distractors = [f"{sum(vals)} {max(vals)}", f"{sum(vals)} 0", STOP_ITERATION, f"{sum(vals)} None"]
            why = (
                "`sum` already consumed the generator, so `max` receives an EMPTY sequence, and "
                "`max()` of nothing raises a ValueError."
            )
        else:
            distractors = [VALUE_ERROR, STOP_ITERATION, f"{sum(vals)} 0", f"{sum(vals)} {vals[0]}"]
            why = (
                f"Square brackets build a real list, which can be looped over any number of times, "
                f"so both `sum` ({sum(vals)}) and `max` ({max(vals)}) see all the values."
            )
    else:
        k = rng.choice([2, 3])
        b = 7
        vals = [x * k for x in range(1, b)]
        stop = rng.choice(vals[1:-2])
        limit = stop - 1
        code = (
            f"nums = (x * {k} for x in range(1, {b}))\nfor n in nums:\n"
            f"    if n > {limit}:\n        break\nprint(list(nums))"
        )
        rest = vals[vals.index(stop) + 1 :]
        distractors = [
            f"{vals[vals.index(stop) :]}",
            f"{vals}",
            "[]",
            f"{vals[: vals.index(stop)]}",
            NAME_ERROR,
        ]
        why = (
            f"The loop pulls values from the generator until {stop} triggers the `break`; those "
            f"values are gone, so `list(nums)` only gets the rest: {rest}."
        )
    return _out(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_dependent_nested(rng: random.Random) -> Question:
    """Nested for clauses where the inner range depends on the outer variable, or a filter pairs them."""
    style = rng.choice(["triangle", "repeat", "pair_sum"])
    if style == "triangle":
        lo, hi = rng.choice([1, 1, 2]), 4
        outer = list(range(lo, hi))
        inner_kind = rng.choice(["below", "upto", "rest"])
        if inner_kind == "below":
            inner_src, inner, wide = "range(a)", (lambda a: range(a)), (lambda a: range(a + 1))
        elif inner_kind == "upto":
            inner_src, inner, wide = (
                "range(1, a + 1)",
                (lambda a: range(1, a + 1)),
                (lambda a: range(1, a + 2)),
            )
        else:
            inner_src, inner, wide = f"range(a, {hi})", (lambda a: range(a, hi)), (lambda a: range(a, hi + 1))
        expr, g = rng.choice([("a * 10 + b", lambda a, b: a * 10 + b), ("(a, b)", lambda a, b: (a, b))])
        correct = [g(a, b) for a in outer for b in inner(a)]
        if not _fits(str(correct)):
            expr, g = "a * 10 + b", (lambda a, b: a * 10 + b)
            correct = [g(a, b) for a in outer for b in inner(a)]
        code = f"result = [{expr} for a in range({lo}, {hi}) for b in {inner_src}]\nprint(result)"
        all_b = sorted({b for a in outer for b in inner(a)})
        by_b = [g(a, b) for b in all_b for a in outer if b in inner(a)]
        fixed = [g(a, b) for a in outer for b in inner(outer[-1])]
        distractors = [
            by_b,
            [g(a, b) for a in outer for b in wide(a)],
            fixed,
            [g(a, b + 1) for a in outer for b in inner(a)],
            [g(a, b) for a in outer[:-1] for b in inner(a)],
            [g(a, b) for a in outer for b in inner(a) if a != b],
        ]
        why = (
            f"The outer `a` takes {_and(outer)}; for EACH `a` the inner `{inner_src}` is rebuilt "
            f"using that `a`, so the inner loop runs a different number of times on each pass."
        )
    elif style == "repeat" and rng.random() < 0.5:
        letters = rng.sample("abcdegkmrstxyz", 3)
        counts = [rng.randint(1, 3) for _ in letters]
        counts[rng.randrange(3)] = 0
        code = (
            f"letters = {_src(letters)}\ncounts = {counts}\n"
            "result = [ch for ch, n in zip(letters, counts) for _ in range(n)]\nprint(result)"
        )
        pairs = list(zip(letters, counts))
        distractors = [
            [ch * n for ch, n in pairs],
            [ch for r in range(3) for ch, n in pairs if r < n],
            [ch for ch, n in pairs for _ in range(max(n, 1))],
            [ch for ch, n in pairs for _ in range(n + 1)],
            [ch for ch, n in pairs if n],
        ]
        why = (
            "For each (letter, count) pair the inner loop runs `count` times, adding the letter "
            "once per pass, so a letter with count 0 disappears completely and the result is ONE flat "
            "list of single letters."
        )
    elif style == "repeat":
        s = rng.choice([1, 2])
        n = rng.choice([4, 5]) if s == 1 else 5
        name = rng.choice(["result", "stacked", "repeated"])
        code = f"{name} = [x for x in range({s}, {n}) for _ in range(x)]\nprint({name})"
        xs = list(range(s, n))
        correct = [x for x in xs for _ in range(x)]
        distractors = [
            [x for r in range(max(xs)) for x in xs if r < x],
            [r for x in xs for r in range(x)],
            xs,
            [x for x in xs for _ in range(x + 1)],
        ]
        why = (
            f"For each `x` in {_and(xs)} the inner loop runs `x` times and adds `x` each time, "
            f"so {xs[0]} appears {xs[0]} time{'s' if xs[0] > 1 else ''}, {xs[1]} appears {xs[1]} times, and so on."
        )
    else:
        nums = sorted(rng.sample(range(1, 8), 4))
        sums = sorted({a + b for a in nums for b in nums})
        target = rng.choice([t for t in sums if 2 <= sum(1 for a in nums for b in nums if a + b == t) <= 4])
        code = (
            f"nums = {nums}\npairs = [(a, b) for a in nums for b in nums if a + b == {target}]\nprint(pairs)"
        )
        correct = [(a, b) for a in nums for b in nums if a + b == target]
        distractors = [
            [(a, b) for a in nums for b in nums if a + b == target and a < b],
            [(a, b) for b in nums for a in nums if a + b == target],
            [(a, b) for a in nums for b in nums if a + b == target and a <= b],
            [(a, b) for a in nums for b in nums if a + b == target and a != b],
            [(a, b) for a in nums for b in nums if a + b == target and a > b],
        ]
        why = (
            f"Both loops run over ALL of `nums`, so every ordered pair is tested: "
            f"{_and(str(p) for p in correct)} each sum to {target}. `a` is the outer loop, so the pairs "
            f"come out ordered by `a`."
        )
    return _out(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_invert_dict(rng: random.Random) -> Question:
    """Building a dict from pairs with repeated keys (inverting, counting): entries silently merge."""
    style = rng.choice(["invert", "invert_len", "pairs_sum", "count"])
    if style in ("invert", "invert_len"):
        people = rng.sample(_PEOPLE, 4)
        for _ in range(100):
            grades = [rng.choice("ABC") for _ in people]
            if len(set(grades)) in (2, 3):
                break
        orig = dict(zip(people, grades))
        code = f"grades = {_src(orig)}\nby_grade = {{grade: name for name, grade in grades.items()}}\n"
        pairs = [(g, p) for p, g in orig.items()]
        last = dict(pairs)
        first: dict = {}
        for g, p in pairs:
            first.setdefault(g, p)
        if style == "invert":
            code += "print(by_grade)"
            last_order = {g: last[g] for g in reversed(list(dict.fromkeys(g for g, _ in reversed(pairs))))}
            grouped: dict = {}
            for g, p in pairs:
                grouped.setdefault(g, []).append(p)
            distractors = _with_error(
                rng, [str(first), str(last_order), _fake_dict(pairs), str(grouped)], KEY_ERROR, p=0.3
            )
            dup = next(g for g in grades if grades.count(g) > 1)
            times = grades.count(dup)
            why = (
                f"{_and(p for p, g in orig.items() if g == dup)} {'both' if times == 2 else 'all'} have "
                f"grade {dup!r}, so key {dup!r} is assigned {'twice' if times == 2 else f'{times} times'}: "
                f"the last name, {last[dup]!r}, overwrites the earlier "
                f"{'one' if times == 2 else 'ones'}, but the key keeps its first position."
            )
        else:
            code += "print(len(grades), len(by_grade))"
            distractors = _with_error(
                rng,
                ["4 4", f"{len(last)} {len(last)}", f"{len(last)} 4", f"4 {len(last) - 1}"],
                KEY_ERROR,
                p=0.3,
            )
            why = (
                f"Inverting turns the grades into keys, and keys must be unique: there are only "
                f"{len(last)} different grades, so names sharing a grade overwrite each other."
            )
    elif style == "pairs_sum":
        keys = rng.sample(["a", "b", "c", "x", "y", "z"], 2)
        dup = keys[0]
        vals = rng.sample(range(1, 10), 3)
        pairs = [(dup, vals[0]), (keys[1], vals[1]), (dup, vals[2])]
        if rng.random() < 0.5:
            pairs[0], pairs[1] = pairs[1], pairs[0]
        code = f"pairs = {_src(pairs)}\nd = {{key: value for key, value in pairs}}\nprint(d, sum(d.values()))"
        last = dict(pairs)
        first: dict = {}
        for k, v in pairs:
            first.setdefault(k, v)
        acc: dict = {}
        for k, v in pairs:
            acc[k] = acc.get(k, 0) + v
        last_order = {k: last[k] for k in reversed(list(dict.fromkeys(k for k, _ in reversed(pairs))))}
        distractors = _with_error(
            rng,
            [
                f"{first} {sum(first.values())}",
                f"{acc} {sum(acc.values())}",
                f"{last_order} {sum(last.values())}" if last_order != last else f"{last} {sum(vals)}",
                f"{_fake_dict(pairs)} {sum(vals)}",
            ],
            KEY_ERROR,
            p=0.3,
        )
        why = (
            f"Key {dup!r} appears twice; the second assignment REPLACES the first value (values are "
            f"not added), so `d[{dup!r}]` is {last[dup]} and the sum is {sum(last.values())}."
        )
    else:
        base = rng.sample(["hi", "yo", "ok", "no", "go", "up"], 3)
        words = [base[0], base[1], base[0], base[2], base[1], base[0]]
        rest = words[1:]
        rng.shuffle(rest)
        words = [words[0]] + rest
        code = f"words = {_src(words)}\ncounts = {{w: words.count(w) for w in words}}\nprint(counts)"
        counts = {w: words.count(w) for w in words}
        last_order = {w: counts[w] for w in reversed(list(dict.fromkeys(reversed(words))))}
        distractors = _with_error(
            rng,
            [
                _fake_dict((w, words.count(w)) for w in words),
                [words.count(w) for w in words],
                {w: 1 for w in words},
                last_order,
            ],
            KEY_ERROR,
            p=0.25,
        )
        why = (
            f"The comprehension runs {len(words)} times, but repeated words reuse the same key, so "
            f"only {len(counts)} keys remain (in first-seen order), each mapped to its count."
        )
    return _out(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_independent_rows(rng: random.Random) -> Question:
    """Rows built by a comprehension are separate lists, unless every row is the same object."""
    rows, cols = rng.choice([(2, 3), (3, 2), (3, 3), (2, 2)])
    i, j = rng.randrange(rows), rng.randrange(cols)
    style = rng.choice(["fresh", "nested", "same_row", "copied_row", "multiply"])
    fill = rng.choice([0, 0, "."])
    v = rng.randint(1, 9) if fill == 0 else rng.choice(["X", "O", "#"])
    fill_src = _src(fill)
    if style == "fresh":
        build = f"grid = [[{fill_src}] * {cols} for _ in range({rows})]"
        shared = False
    elif style == "nested":
        build = f"grid = [[{fill_src} for _ in range({cols})] for _ in range({rows})]"
        shared = False
    elif style == "same_row":
        build = f"row = [{fill_src}] * {cols}\ngrid = [row for _ in range({rows})]"
        shared = True
    elif style == "copied_row":
        copy = rng.choice(["row.copy()", "row[:]", "list(row)"])
        build = f"row = [{fill_src}] * {cols}\ngrid = [{copy} for _ in range({rows})]"
        shared = False
    else:
        build = f"grid = [[{fill_src}] * {cols}] * {rows}"
        shared = True
    code = f"{build}\ngrid[{i}][{j}] = {_src(v)}\nprint(grid)"

    def make(shared_rows: bool, r: int, c: int) -> str:
        g = [[fill] * cols for _ in range(rows)]
        for rr in range(rows):
            if (rr == r or shared_rows) and 0 <= c < cols:
                g[rr][c] = v
        return str(g)

    distractors = [
        make(not shared, i, j),
        make(shared, j, i) if j < rows and i < cols else make(shared, i, cols - 1 - j),
        make(not shared, j, i) if j < rows and i < cols else make(not shared, i, cols - 1 - j),
        str([[v] * cols if r == i else [fill] * cols for r in range(rows)]),
        str([[fill] * cols for _ in range(rows)]),
    ]
    if shared:
        why = (
            "Every row in `grid` is the SAME list object"
            + (" (`row` itself is added each time)" if style == "same_row" else " (`*` copies references)")
            + f", so changing `grid[{i}][{j}]` shows up in every row."
        )
    else:
        why = (
            "The comprehension builds a NEW list on every pass, so the rows are independent and "
            f"`grid[{i}][{j}] = {_src(v)}` changes only row {i}."
        )
    return _out(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_pipeline_trace(rng: random.Random) -> Question:
    """Trace a list comp -> dict comp -> generator expression pipeline."""
    for _ in range(200):
        nums = rng.sample(range(2, 25), 6)
        kind = rng.choice(["odd", "even", "big"])
        if kind == "odd":
            name1, cond1, keep = "odds", "n % 2 == 1", (lambda x: x % 2 == 1)
        elif kind == "even":
            name1, cond1, keep = "evens", "n % 2 == 0", (lambda x: x % 2 == 0)
        else:
            k1 = sorted(nums)[2]
            name1, cond1, keep = "big", f"n > {k1}", (lambda x, k1=k1: x > k1)
        op = rng.choice(["//", "//", "%"])
        d = rng.choice([2, 3]) if op == "//" else rng.choice([3, 4, 5])
        name2 = {("//", 2): "halves", ("//", 3): "thirds"}.get((op, d), "remainders")
        kept = [x for x in nums if keep(x)]
        vals = [x // d if op == "//" else x % d for x in kept]
        if not 3 <= len(kept) <= 5 or len(set(vals)) < 3:
            continue
        t = sorted(vals)[len(vals) // 2 - 1 + rng.randint(0, 1)]
        if t not in vals or not any(v > t for v in vals) or vals.count(t) > 2:
            continue
        agg = rng.choice(["sum", "sum", "max", "len"])
        break
    else:
        raise GenerationError("could not build a pipeline")
    if agg == "len":
        last = f"print(len([v for v in {name2}.values() if v > {t}]))"
    else:
        last = f"print({agg}(v for v in {name2}.values() if v > {t}))"
    code = (
        f"nums = {nums}\n{name1} = [n for n in nums if {cond1}]\n"
        f"{name2} = {{n: n {op} {d} for n in {name1}}}\n{last}"
    )
    res = run_code(code)
    if res.error:
        raise GenerationError(f"pipeline raised {res.error}")
    swaps = [
        (f" > {t}", f" >= {t}"),
        (".values()", ".keys()"),
        (f" if v > {t}", ""),
        (f"n {op} {d}", f"n {'%' if op == '//' else '//'} {d}"),
        (f"if {cond1}", f"if not {cond1}"),
        (f"n {op} {d}", f"n / {d}") if op == "//" else ("", ""),
    ]
    distractors = [o for o in _mutants(code, swaps) if o != res.output]
    answer = int(res.output)
    passed = [v for v in vals if v > t]
    near = [answer + 1, answer - 1, answer + 2, answer + t, answer - 2]
    why = (
        f"`{name1}` is {kept}; `{name2}` maps each of them to `n {op} {d}`, giving the values "
        f"{_and(vals)}. "
        + (f"Only {passed[0]} is" if len(passed) == 1 else f"The values {_and(passed)} are")
        + f" greater than {t}, so "
        + {"sum": "`sum` gives", "max": "`max` gives", "len": "the list has length"}[agg]
        + f" {answer}."
    )
    return _out(code, HARD, distractors + [n for n in near if n >= 0], why, rng)


@generator(TOPIC, HARD)
def gen_filter_then_transform(rng: random.Random) -> Question:
    """[A if C else B for x in xs if F]: the trailing filter runs FIRST, on the original values."""
    for _ in range(200):
        nums = rng.sample(range(1, 16), 6)
        d1 = rng.choice([2, 3])
        c1 = f"n % {d1} == 0"
        a_expr = rng.choice(["n // 2", "n * 10", "-n"])
        b_expr = rng.choice(["n", "n * 3", "0"])
        k = sorted(nums)[rng.randint(1, 3)]
        op = rng.choice([">", "<", "!="])
        flt = f"n {op} {k}"
        code = (
            f"nums = {nums}\nresult = [{a_expr} if {c1} else {b_expr} for n in nums if {flt}]\nprint(result)"
        )
        out = _run(code)
        kept = [n for n in nums if (n > k if op == ">" else n < k if op == "<" else n != k)]
        hits = [n for n in kept if n % d1 == 0]
        if out and 2 <= len(kept) <= 5 and 0 < len(hits) < len(kept):
            break
    else:
        raise GenerationError("could not build a filter/transform question")
    after = (
        f"nums = {nums}\n"
        f"result = [m for m in [{a_expr} if {c1} else {b_expr} for n in nums] if {flt.replace('n', 'm')}]\n"
        "print(result)"
    )
    distractors = _mutants(
        code,
        [
            (f" for n in nums if {flt}]", " for n in nums]"),
            (f"[{a_expr} if {c1} else {b_expr}", f"[{b_expr} if {c1} else {a_expr}"),
            ("n // 2", "n / 2"),
            (f"if {flt}]", f"if not {flt}]"),
        ],
    )
    alt = _run(after)
    if alt:
        distractors.insert(1, alt)
    why = (
        f"The trailing `if {flt}` filters the ORIGINAL numbers first, keeping {_and(kept)}. "
        f"Then each kept number goes through `{a_expr} if {c1} else {b_expr}`."
    )
    return _out(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_nested_comprehension(rng: random.Random) -> Question:
    """A comprehension inside a comprehension builds a list of lists (tables, transposing, row filters)."""
    style = rng.choice(["table", "transpose", "row_filter"])
    if style == "table":
        R, C = rng.choice([(2, 3), (3, 2), (2, 4), (3, 3)])
        expr, f = rng.choice(
            [
                ("r * c", lambda r, c: r * c),
                ("r + c", lambda r, c: r + c),
                ("r * 10 + c", lambda r, c: r * 10 + c),
            ]
        )
        code = f"table = [[{expr} for c in range(1, {C + 1})] for r in range(1, {R + 1})]\nprint(table)"
        correct = [[f(r, c) for c in range(1, C + 1)] for r in range(1, R + 1)]
        distractors = [
            [[f(r, c) for r in range(1, R + 1)] for c in range(1, C + 1)],
            [f(r, c) for r in range(1, R + 1) for c in range(1, C + 1)],
            [[f(r, c) for c in range(1, C)] for r in range(1, R)],
            [[f(r, c) for c in range(C)] for r in range(R)],
        ]
        why = (
            f"The OUTER comprehension (over `r`) makes one row per `r`, and each row is the inner list "
            f"over `c`. So there are {R} rows of {C} values: {correct[0]} first."
        )
    elif style == "transpose":
        R, C = rng.choice([(2, 3), (3, 2)])
        vals = rng.sample(range(1, 10), R * C)
        matrix = [vals[r * C : (r + 1) * C] for r in range(R)]
        code = (
            f"matrix = {matrix}\n"
            "flipped = [[row[i] for row in matrix] for i in range(len(matrix[0]))]\n"
            "print(flipped)"
        )
        correct = [[row[i] for row in matrix] for i in range(C)]
        distractors = [
            matrix,
            [row[i] for i in range(C) for row in matrix],
            [x for row in matrix for x in row],
            [row[::-1] for row in matrix],
            [[row[i] for row in matrix[::-1]] for i in range(C)],
        ]
        why = (
            f"For each column index `i` (0 to {C - 1}), the inner comprehension collects `row[i]` from "
            f"every row, so column {0} becomes the first new row {correct[0]}: the matrix is transposed."
        )
    else:
        for _ in range(100):
            vals = rng.sample(range(1, 20), 9)
            matrix = [vals[r * 3 : (r + 1) * 3] for r in range(3)]
            k = rng.randint(6, 14)
            rows_kept = [[x for x in row if x > k] for row in matrix]
            if any(not r for r in rows_kept) and sum(1 for r in rows_kept if r) >= 2:
                break
        else:
            raise GenerationError("no row filter with an empty row")
        code = f"grid = {matrix}\nbig = [[x for x in row if x > {k}] for row in grid]\nprint(big)"
        distractors = [
            [r for r in rows_kept if r],
            [x for row in matrix for x in row if x > k],
            [row for row in matrix if any(x > k for x in row)],
            [[x if x > k else 0 for x in row] for row in matrix],
        ]
        why = (
            f"The inner comprehension filters WITHIN each row, but the outer one still produces one "
            f"list per row, so a row with nothing above {k} becomes an empty list `[]`."
        )
    return _out(code, HARD, distractors, why, rng)
