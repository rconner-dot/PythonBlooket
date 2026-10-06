"""Question generators for the "strings" topic (Strings).

Covers indexing (including negative indexes), slicing with steps, ``len``,
concatenation and repetition, ``in``/``startswith``/``endswith``, the common
str methods (upper/lower/title/capitalize/replace/find/index/count/strip/
split/join), immutability and "methods return a NEW string", lexicographic
comparison and sorting, f-string format specs, and the classic gotchas:
``strip()`` takes a *set* of characters, ``split()`` vs ``split(" ")`` and
empty fields, negative-step slice bounds and non-overlapping ``count()``.
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

TOPIC = "strings"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
TYPE_ERROR = error_choice("TypeError")
INDEX_ERROR = error_choice("IndexError")
VALUE_ERROR = error_choice("ValueError")
ATTRIBUTE_ERROR = error_choice("AttributeError")
BLANK = "___"


# --------------------------------------------------------------------------
# Private helpers & word pools
# --------------------------------------------------------------------------


def _lit(text: str) -> str:
    """``text`` as a PEP 8 style (double-quoted) string literal."""
    if '"' in text or "\\" in text or "\n" in text:
        return repr(text)
    return f'"{text}"'


def _list_lit(items: list[str]) -> str:
    """A list of strings written as source code with double quotes."""
    return "[" + ", ".join(_lit(x) for x in items) + "]"


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
    prompt: str = "What does this code print?",
    allow_error: bool = False,
) -> Question:
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[str(d) for d in distractors],
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _distinct(word: str) -> bool:
    return len(set(word)) == len(word)


# Words whose letters are all different, so every index names a unique letter.
_SHORT_WORDS = [
    w
    for w in (
        "python", "rocket", "planet", "garden", "silver", "monkey", "candle",
        "orange", "tiger", "lemon", "mango", "orbit", "snake", "pixel", "dragon",
        "wizard", "falcon", "basket", "magic", "storm", "jungle", "cloud",
        "frost", "violet", "castle", "pirate", "spider", "bright", "number",
    )
    if _distinct(w)
]
_LONG_WORDS = [
    w
    for w in (
        "keyboard", "dolphins", "blackout", "trampoline", "pathfinder",
        "campground", "chipmunk", "flamingo", "sandwich", "graphics", "computer",
        "dumplings", "blueprint", "playground", "jackpot", "skyline",
        "lumberjack", "education", "factory", "algorithm", "spectrum",
        "republic", "triangle", "workday",
    )
    if _distinct(w) and len(w) >= 7
]
# Words with at least one repeated letter (for count/find/replace).
_REPEAT_WORDS = [
    "banana", "cocoa", "pepper", "letter", "coffee", "bubble", "cookie",
    "balloon", "kitten", "summer", "yellow", "tomato", "potato", "rabbit",
    "parrot", "papaya", "cheese", "puppy", "success", "address", "giraffe",
    "llama", "hello", "apple", "butter", "dinner", "classroom", "mammal",
]
_SMALL_WORDS = [
    "ice", "cream", "hot", "dog", "big", "cat", "red", "sky", "blue", "moon",
    "fast", "car", "good", "day", "new", "game", "top", "score", "sun", "hat",
    "pink", "fox", "map", "star", "fish", "tree",
]
_WORD_VARS = ["word", "text", "name", "label", "item"]


def _repeated_letters(word: str) -> list[str]:
    return [c for c in sorted(set(word)) if word.count(c) >= 2]


def _letters_not_in(word: str, pool: str = "aeioustrnlmdgkpbz") -> list[str]:
    return [c for c in pool if c not in word]


def _indexes(word: str, ch: str) -> list[int]:
    return [i for i, c in enumerate(word) if c == ch]


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_indexing(rng: random.Random) -> Question:
    """Positive and negative indexes, first/last character, index out of range."""
    word = rng.choice(_SHORT_WORDS)
    var = rng.choice(_WORD_VARS)
    n = len(word)
    head = f"{var} = {_lit(word)}\n"
    shape = rng.choices(["pos", "neg", "ends", "len", "out"], weights=[3, 3, 2, 2, 2])[0]
    if shape == "pos":
        i = rng.randint(1, n - 2)
        code = head + f"print({var}[{i}])"
        distractors = [word[i - 1], word[i + 1], INDEX_ERROR, word[(i + 2) % n], word[-i]]
        why = (
            f"Indexes start at 0, so `{var}[0]` is {word[0]!r} and index {i} is the "
            f"{_ordinal(i + 1)} character: {word[i]!r}."
        )
    elif shape == "neg":
        i = rng.randint(1, 3)
        code = head + f"print({var}[-{i}])"
        distractors = [word[-i - 1], word[i], INDEX_ERROR, word[i - 1], word[(1 - i) % n]]
        why = (
            f"Negative indexes count from the end, with -1 being the last character, so "
            f"`{var}[-{i}]` is the {_ordinal(i)} character from the end: {word[-i]!r}."
        )
    elif shape == "ends":
        code = head + f"print({var}[0], {var}[-1])"
        distractors = [
            f"{word[0]} {word[-2]}", f"{word[1]} {word[-1]}", INDEX_ERROR,
            f"{word[1]} {word[-2]}", f"{word[-1]} {word[0]}",
        ]
        why = (
            f"`{var}[0]` is the first character ({word[0]!r}) and `{var}[-1]` is the last "
            f"({word[-1]!r}); `print` puts a space between them."
        )
    elif shape == "len":
        k = rng.randint(1, 3)
        code = head + f"print({var}[len({var}) - {k}])"
        distractors = [
            word[n - k - 1], word[n - k + 1] if k > 1 else INDEX_ERROR, INDEX_ERROR,
            word[k], word[k - 1],
        ]
        why = (
            f"`len({var})` is {n}, so this is `{var}[{n - k}]`, which is {word[n - k]!r}. "
            f"The last valid index is {n - 1}, one less than the length."
        )
    else:
        idx = rng.choice([str(n), f"len({var})"])
        code = head + f"print({var}[{idx}])"
        distractors = [word[-1], word[0], word[-2], NOTHING_PRINTED]
        why = (
            f"{word!r} has {n} characters, so its valid indexes are 0 to {n - 1}. "
            f"Index {n} is one past the end, so Python raises an IndexError."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_len(rng: random.Random) -> Question:
    """len() counts every character: spaces, punctuation, joined and repeated strings."""
    shape = rng.choice(["phrase", "greeting", "concat", "repeat"])
    if shape == "phrase":
        w1, w2 = rng.sample(_SMALL_WORDS, 2)
        text = f"{w1} {w2}"
        var = rng.choice(["phrase", "msg", "text", "caption"])
        code = f"{var} = {_lit(text)}\nprint(len({var}))"
        n = len(text)
        distractors = [n - 1, n + 1, 2, n - 2, len(w1), n + 2]
        why = (
            f"`len` counts every character, including the space: "
            f"{len(w1)} + 1 + {len(w2)} = {n}."
        )
    elif shape == "greeting":
        hello = rng.choice(["Hi", "Hey", "Hello", "Yo"])
        name = rng.choice(NAMES)
        punct = rng.choice(["!", "?", "."])
        text = f"{hello}, {name}{punct}"
        letters = sum(c.isalpha() for c in text)
        n = len(text)
        code = f"greeting = {_lit(text)}\nprint(len(greeting))"
        distractors = [letters, n - 1, n + 1, letters + 1, n - 2]
        why = (
            f"`len` counts every character in {text!r}: the {letters} letters plus the "
            f"comma, the space and the {punct!r}, so {n} in total."
        )
    elif shape == "concat":
        a, b = rng.sample(_SMALL_WORDS, 2)
        code = f"a = {_lit(a)}\nb = {_lit(b)}\nprint(len(a + b))"
        total = len(a) + len(b)
        distractors = [total + 1, 2, total - 1, len(a), len(b), total + 2]
        why = (
            f"`a + b` joins the strings with nothing in between ({a + b!r}), so its "
            f"length is {len(a)} + {len(b)} = {total}."
        )
    else:
        w = rng.choice(["ha", "ab", "na", "go", "boo", "la", "hey", "ok"])
        k = rng.randint(2, 4)
        code = f"sound = {_lit(w)}\nprint(len(sound * {k}))"
        distractors = [len(w) + k, len(w), k, len(w) * k + 1, len(w) * (k - 1), len(w) * k - 1, len(w) * (k + 1)]
        why = (
            f"`sound * {k}` repeats {w!r} {k} times ({w * k!r}), so the length is "
            f"{len(w)} × {k} = {len(w) * k}."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_basic_slicing(rng: random.Random) -> Question:
    """[a:b], [:b], [a:], [-k:] — the stop index is excluded."""
    word = rng.choice([w for w in _SHORT_WORDS + _LONG_WORDS if len(w) >= 6])
    var = rng.choice(_WORD_VARS)
    n = len(word)
    head = f"{var} = {_lit(word)}\n"
    shape = rng.choice(["mid", "mid", "head", "tail", "last", "which"])
    if shape in ("mid", "which"):
        a = rng.randint(1, 3)
        b = rng.randint(a + 2, min(n - 1, a + 4))
        target = word[a:b]
        if shape == "which":
            wrong = [
                f"{var}[{a}:{b + 1}]", f"{var}[{a + 1}:{b + 1}]", f"{var}[{a - 1}:{b}]",
                f"{var}[{a}:{b - 1}]", f"{var}[{a + 1}:{b}]", f"{var}[{a - 1}:{b - 1}]",
            ]
            rng.shuffle(wrong)
            return which_expression_question(
                topic=TOPIC,
                difficulty=EASY,
                prompt=f"Which expression evaluates to `{target!r}`?",
                setup=f"{var} = {_lit(word)}",
                target=target,
                correct_expr=f"{var}[{a}:{b}]",
                wrong_exprs=wrong,
                explanation=(
                    f"{target!r} starts at index {a} ({word[a]!r}) and ends at index {b - 1}. "
                    f"A slice stops just BEFORE its stop index, so you need `{var}[{a}:{b}]`."
                ),
                rng=rng,
            )
        code = head + f"print({var}[{a}:{b}])"
        distractors = [
            word[a:b + 1], word[a - 1:b - 1], word[a + 1:b + 1], word[a - 1:b], word[a + 1:b],
        ]
        why = (
            f"A slice includes the start index but stops just BEFORE the stop index, so "
            f"`{var}[{a}:{b}]` is indexes {a} to {b - 1}: {target!r}."
        )
    elif shape == "head":
        b = rng.randint(2, n - 2)
        code = head + f"print({var}[:{b}])"
        distractors = [word[:b + 1], word[:b - 1], word[b:], word[1:b + 1]]
        why = (
            f"Leaving out the start means 'from the beginning', and the slice stops before "
            f"index {b}, so you get the first {b} characters: {word[:b]!r}."
        )
    elif shape == "tail":
        a = rng.randint(2, n - 2)
        code = head + f"print({var}[{a}:])"
        distractors = [word[a + 1:], word[:a], word[a - 1:], word[a:-1]]
        why = (
            f"Leaving out the stop means 'to the end', so `{var}[{a}:]` starts at index {a} "
            f"({word[a]!r}) and keeps everything after it: {word[a:]!r}."
        )
    else:
        k = rng.randint(2, 4)
        code = head + f"print({var}[-{k}:])"
        distractors = [word[:-k], word[-k - 1:], word[-k:-1], word[-k + 1:]]
        why = (
            f"`-{k}` is the {_ordinal(k)} character from the end and the empty stop runs to "
            f"the end, so you get the last {k} characters: {word[-k:]!r}."
        )
    return _output(code, EASY, distractors, why, rng)


_PHRASES = [
    ("good", "day"), ("big", "cat"), ("hot", "dog"), ("blue", "moon"), ("red", "car"),
    ("high", "score"), ("new", "game"), ("snow", "ball"), ("pizza", "time"),
    ("space", "race"), ("happy", "dance"), ("ice", "cream"), ("game", "over"),
    ("level", "up"), ("hello", "world"), ("star", "fish"), ("good", "luck"),
]


def _mixed_case_phrase(rng: random.Random) -> str:
    """A two-word phrase where some letter after the first is uppercase."""
    w1, w2 = rng.choice(_PHRASES)
    style = rng.choice(["lT", "lU", "TU", "Ul", "UT"])
    fmt = {"l": str.lower, "T": str.capitalize, "U": str.upper}
    return f"{fmt[style[0]](w1)} {fmt[style[1]](w2)}"


@generator(TOPIC, EASY)
def gen_case_methods(rng: random.Random) -> Question:
    """upper / lower / title / capitalize on a mixed-case phrase."""
    phrase = _mixed_case_phrase(rng)
    var = rng.choice(["msg", "phrase", "text", "label", "slogan"])
    method = rng.choice(["upper", "lower", "title", "capitalize"])
    res = {m: getattr(phrase, m)() for m in ("upper", "lower", "title", "capitalize", "swapcase")}
    first_up = phrase[0].upper() + phrase[1:]
    order = {
        "upper": [res["title"], first_up, phrase, res["capitalize"], res["swapcase"]],
        "lower": [res["capitalize"], phrase, phrase[0].lower() + phrase[1:], res["title"], res["swapcase"]],
        "title": [res["capitalize"], first_up, res["upper"], phrase, res["swapcase"]],
        "capitalize": [res["title"], first_up, res["upper"], phrase, res["lower"]],
    }[method]
    if rng.random() < 0.3:
        code = f"print({_lit(phrase)}.{method}())"
    else:
        code = f"{var} = {_lit(phrase)}\nprint({var}.{method}())"
    why = {
        "upper": "`upper()` returns a copy with every letter in uppercase.",
        "lower": "`lower()` returns a copy with every letter in lowercase.",
        "title": (
            "`title()` makes the first letter of EACH word uppercase and all the other "
            "letters lowercase."
        ),
        "capitalize": (
            "`capitalize()` makes only the very first character uppercase and ALL the rest "
            "lowercase, even the start of the second word."
        ),
    }[method] + f" So {phrase!r} becomes {res[method]!r}."
    return _output(code, EASY, order, why, rng)


_COMPOUNDS = [
    ("sun", "flower"), ("rain", "bow"), ("foot", "ball"), ("cup", "cake"),
    ("star", "fish"), ("pop", "corn"), ("tooth", "brush"), ("snow", "man"),
    ("butter", "fly"), ("note", "book"), ("pan", "cake"), ("fire", "work"),
]


@generator(TOPIC, EASY)
def gen_concat_repeat(rng: random.Random) -> Question:
    """+ joins, * repeats, print(a, b) adds a space, and strings can't be subtracted."""
    shape = rng.choice(["plus", "comma", "repeat", "mixed", "minus"])
    if shape in ("plus", "comma"):
        a, b = rng.choice(_COMPOUNDS)
        x, y = rng.choice([("first", "second"), ("left", "right"), ("start", "end"), ("a", "b")])
        head = f"{x} = {_lit(a)}\n{y} = {_lit(b)}\n"
        if shape == "plus":
            code = head + f"print({x} + {y})"
            distractors = [f"{a} {b}", TYPE_ERROR, f"{b}{a}", f"{x}{y}", f"{a}+{b}"]
            why = (
                f"`+` glues two strings together exactly as they are, with no space added, "
                f"so {a!r} + {b!r} is {a + b!r}."
            )
        else:
            code = head + f"print({x}, {y})"
            distractors = [f"{a}{b}", f"{a}, {b}", TYPE_ERROR, f"{x} {y}"]
            why = (
                "When you pass several values to `print` separated by commas, it prints them "
                f"with ONE space between them: `{a} {b}`."
            )
    elif shape == "repeat":
        s = rng.choice(["ha", "na", "go", "boo", "la", "yo", "hip"])
        k = rng.randint(2, 4)
        code = f"sound = {_lit(s)}\nprint(sound * {k})"
        distractors = [" ".join([s] * k), f"{s}{k}", TYPE_ERROR, s[:-1] + s[-1] * k, s * (k + 1)]
        why = f"`*` repeats a string: {s!r} * {k} is {s!r} written {k} times in a row, with no spaces."
    elif shape == "mixed":
        a = rng.choice(["ha", "wow", "yes", "go", "hi", "no"])
        b = rng.choice(["!", "?", "."])
        k = rng.randint(2, 3)
        code = f"print({_lit(a)} + {_lit(b)} * {k})"
        distractors = [(a + b) * k, a * k + b, f"{a}{b}{k}", TYPE_ERROR]
        why = (
            f"`*` happens before `+` (just like in maths), so `{_lit(b)} * {k}` makes "
            f"{b * k!r} first, which is then joined onto {a!r}."
        )
    else:
        word = rng.choice(["glass", "class", "boss", "grass", "dress", "chess", "cats", "dogs", "hats"])
        code = f"word = {_lit(word)}\nprint(word - \"s\")"
        distractors = [word[:-1], word.replace("s", ""), word, VALUE_ERROR]
        why = (
            "Strings support `+` (join) and `*` (repeat) but not `-`, so subtracting one "
            "string from another raises a TypeError. Use slicing or `replace()` instead."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


def _substring_check(rng: random.Random, word: str, var: str, kind: str) -> tuple[str, str]:
    """A boolean expression about ``word`` and a short reason for its value."""
    n = len(word)
    if kind == "in_true":
        k = rng.randint(2, 3)
        i = rng.randint(0, n - k)
        sub = word[i:i + k]
        return f"{_lit(sub)} in {var}", f"{sub!r} appears as one connected block inside {word!r}"
    if kind == "in_gap":
        for _ in range(30):
            i = rng.randint(0, n - 3)
            sub = word[i] + word[i + 2]
            if sub not in word:
                return (
                    f"{_lit(sub)} in {var}",
                    f"its letters are in {word!r} but not next to each other",
                )
        kind = "in_case"
    if kind == "in_case":
        sub = word[: rng.randint(2, 3)].capitalize()
        return f"{_lit(sub)} in {var}", f"`in` is case-sensitive and {word!r} has a lowercase {word[0]!r}"
    if kind == "starts_true":
        k = rng.randint(2, 3)
        return (
            f"{var}.startswith({_lit(word[:k])})",
            f"{word!r} does start with {word[:k]!r}",
        )
    if kind == "starts_false":
        k = rng.randint(2, 3)
        sub = word[:k].capitalize()
        return (
            f"{var}.startswith({_lit(sub)})",
            f"case matters and {word!r} starts with lowercase {word[:k]!r}",
        )
    if kind == "ends_true":
        k = rng.randint(2, 3)
        return f"{var}.endswith({_lit(word[-k:])})", f"{word!r} does end with {word[-k:]!r}"
    # ends_false: the START of the word, which it does not end with
    k = rng.randint(2, 3)
    sub = word[:k]
    if word.endswith(sub):
        raise GenerationError("word ends with its own prefix")
    return f"{var}.endswith({_lit(sub)})", f"{word!r} starts with {sub!r} but does not end with it"


@generator(TOPIC, EASY)
def gen_substring_checks(rng: random.Random) -> Question:
    """`in`, startswith, endswith — contiguous, case-sensitive substring tests."""
    word = rng.choice([w for w in _SHORT_WORDS + _LONG_WORDS if 5 <= len(w) <= 8])
    var = rng.choice(["word", "text", "name", "city"])
    kinds = ["in_true", "in_gap", "in_case", "starts_true", "starts_false", "ends_true", "ends_false"]
    k1, k2 = rng.sample(kinds, 2)
    while {k1, k2} == {"in_case", "starts_false"}:  # don't test the same idea twice
        k1, k2 = rng.sample(kinds, 2)
    checks = [_substring_check(rng, word, var, k) for k in (k1, k2)]
    code = f"{var} = {_lit(word)}\n" + "\n".join(f"print({expr})" for expr, _ in checks)
    combos = [f"{x}\n{y}" for x in ("True", "False") for y in ("True", "False")]
    setup = f"{var} = {_lit(word)}\n"
    parts = [f"`{expr}` is {_run(setup + f'print({expr})')}: {reason}" for expr, reason in checks]
    return _output(code, EASY, combos, "; ".join(parts) + ".", rng)


@generator(TOPIC, EASY)
def gen_find_count(rng: random.Random) -> Question:
    """count() of a letter, find() of the first match, find() of a missing letter (-1)."""
    word = rng.choice(_REPEAT_WORDS)
    var = rng.choice(["word", "text", "item"])
    head = f"{var} = {_lit(word)}\n"
    shape = rng.choice(["count", "find", "missing"])
    if shape == "count":
        ch = rng.choice(_repeated_letters(word))
        c = word.count(ch)
        code = head + f"print({var}.count({_lit(ch)}))"
        distractors = [c - 1, c + 1, word.find(ch), VALUE_ERROR, len(word)]
        where = ", ".join(str(i) for i in _indexes(word, ch))
        why = f"`count` returns how many times {ch!r} appears in {word!r}: {c} times (at indexes {where})."
    elif shape == "find":
        ch = rng.choice(_repeated_letters(word))
        first = word.find(ch)
        code = head + f"print({var}.find({_lit(ch)}))"
        distractors = [first + 1, word.rfind(ch), word.count(ch), -1, VALUE_ERROR]
        why = (
            f"`find` returns the index of the FIRST match, counting from 0. {ch!r} first "
            f"appears at index {first} of {word!r}."
        )
    else:
        ch = rng.choice(_letters_not_in(word))
        code = head + f"print({var}.find({_lit(ch)}))"
        distractors = [VALUE_ERROR, 0, "None", "False", len(word)]
        why = (
            f"{ch!r} does not appear in {word!r}. When `find` has no match it returns -1 "
            "instead of raising an error."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_REPLACE_SENTENCES = [
    ("the cat sat on the mat", "at", ["og", "ip", "un"]),
    ("one fish two fish", "fish", ["cat", "frog", "bird"]),
    ("tick tock tick tock", "tick", ["tap", "ding", "tip"]),
    ("red bed red sled", "red", ["blue", "big"]),
    ("I scream you scream", "scream", ["sing", "shout", "laugh"]),
    ("row row row your boat", "row", ["sail", "zoom"]),
    ("knock knock who is there", "knock", ["tap", "ring"]),
    ("no news is good news", "news", ["mail", "jokes"]),
]


def _replace_last(text: str, old: str, new: str) -> str:
    i = text.rfind(old)
    return text[:i] + new + text[i + len(old):]


@generator(TOPIC, EASY)
def gen_replace(rng: random.Random) -> Question:
    """replace() swaps EVERY occurrence, not just the first."""
    if rng.random() < 0.55:
        text = rng.choice(_REPEAT_WORDS)
        old = rng.choice(_repeated_letters(text))
        new = rng.choice(_letters_not_in(text, "aeiouxyz"))
        var = rng.choice(["word", "text", "item"])
    else:
        text, old, news = rng.choice(_REPLACE_SENTENCES)
        new = rng.choice(news)
        var = rng.choice(["sentence", "line", "lyric"])
    code = f"{var} = {_lit(text)}\nprint({var}.replace({_lit(old)}, {_lit(new)}))"
    correct = text.replace(old, new)
    distractors = [
        text.replace(old, new, 1), text, _replace_last(text, old, new), text.replace(old, ""),
    ]
    why = (
        f"`replace` swaps EVERY occurrence of {old!r} for {new!r}, not just the first one, "
        f"giving {correct!r}."
    )
    return _output(code, EASY, distractors, why, rng)


# ==========================================================================
# MEDIUM
# ==========================================================================


def _slice_src(start, stop, step=None) -> str:
    src = f"{'' if start is None else start}:{'' if stop is None else stop}"
    if step is not None:
        src += f":{step}"
    return src


@generator(TOPIC, MEDIUM)
def gen_step_slicing(rng: random.Random) -> Question:
    """Steps and negative bounds: [::2], [1::2], [::-1], [1:-1], [:-k], [a:b:2]."""
    word = rng.choice(_LONG_WORDS)
    var = rng.choice(_WORD_VARS)
    n = len(word)
    shape = rng.choice(["evens", "odds", "reverse", "trim", "drop", "ranged"])
    if shape == "evens":
        spec = (None, None, 2)
        wrong = [(1, None, 2), (None, 2, None), (None, None, 3), (2, None, 2), (None, -1, 2)]
        why = f"`[::2]` starts at index 0 and takes every 2nd character (indexes 0, 2, 4, …)"
    elif shape == "odds":
        spec = (1, None, 2)
        wrong = [(None, None, 2), (2, None, 2), (1, 2, None), (1, None, 3), (1, -1, 2)]
        why = f"`[1::2]` starts at index 1 and takes every 2nd character (indexes 1, 3, 5, …)"
    elif shape == "reverse":
        spec = (None, None, -1)
        wrong = [(-1, 0, -1), (None, -1, None), (-2, None, -1), (-1, None, None), (None, None, 1)]
        why = "A step of -1 walks backwards from the last character all the way to the first"
    elif shape == "trim":
        spec = (1, -1, None)
        wrong = [(1, None, None), (None, -1, None), (2, -2, None), (1, -2, None), (2, -1, None)]
        why = "`[1:-1]` starts at index 1 and stops just before the last character, dropping BOTH ends"
    elif shape == "drop":
        k = rng.randint(2, 3)
        spec = (None, -k, None)
        wrong = [(-k, None, None), (None, -k - 1, None), (None, -k + 1, None), (None, k, None)]
        why = f"`[:-{k}]` runs from the start up to (not including) index -{k}, dropping the last {k} characters"
    else:
        a = rng.randint(1, 2)
        b = rng.randint(a + 4, n - 1)
        spec = (a, b, 2)
        wrong = [(a, b + 1, 2), (a + 1, b, 2), (a, b, None), (a, b, 3), (a - 1, b, 2)]
        picked = ", ".join(str(i) for i in range(a, b, 2))
        why = f"`[{a}:{b}:2]` starts at index {a} and takes every 2nd index while staying below {b}: {picked}"
    target = word[slice(*spec)]
    src = _slice_src(*spec)
    why += f", so `{var}[{src}]` is {target!r}."
    if rng.random() < 0.35:
        wrong_exprs = [f"{var}[{_slice_src(*w)}]" for w in wrong]
        rng.shuffle(wrong_exprs)
        return which_expression_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=f"Which expression evaluates to `{target!r}`?",
            setup=f"{var} = {_lit(word)}",
            target=target,
            correct_expr=f"{var}[{src}]",
            wrong_exprs=wrong_exprs,
            explanation=why,
            rng=rng,
        )
    code = f"{var} = {_lit(word)}\nprint({var}[{src}])"
    distractors = [word[slice(*w)] for w in wrong]
    distractors = [d for d in distractors if d]
    return _output(code, MEDIUM, distractors, why, rng)


_SWAPS = [
    ("cat", "b"), ("dog", "l"), ("pen", "t"), ("sun", "f"), ("hot", "p"), ("lake", "c"),
    ("milk", "s"), ("rose", "n"), ("bell", "t"), ("game", "n"), ("fish", "d"),
    ("book", "c"), ("ring", "k"), ("moon", "s"), ("rain", "p"), ("mice", "r"),
    ("cold", "g"), ("wall", "b"),
]


@generator(TOPIC, MEDIUM)
def gen_immutability(rng: random.Random) -> Question:
    """Strings can't be changed in place — but you can build a new one."""
    word, letter = rng.choice(_SWAPS)
    new = letter + word[1:]
    var = rng.choice(["word", "text", "pet"])
    head = f"{var} = {_lit(word)}\n"
    shape = rng.choice(["item", "append", "rebuild", "listconv", "iadd"])
    if shape == "item":
        code = head + f"{var}[0] = {_lit(letter)}\nprint({var})"
        distractors = [new, word, VALUE_ERROR, letter + word]
        why = (
            f"Strings are immutable: you can read `{var}[0]` but you cannot assign to it, so "
            f"`{var}[0] = {_lit(letter)}` raises a TypeError before anything is printed."
        )
    elif shape == "append":
        suffix = "!" if word[-1] in "sh" else "s"
        code = head + f"{var}.append({_lit(suffix)})\nprint({var})"
        distractors = [word + suffix, TYPE_ERROR, word, str(list(word + suffix))]
        why = (
            "Strings have no `append` method (that's a list method), so Python raises an "
            f"AttributeError. To get a longer string, build a new one with `{var} + {_lit(suffix)}`."
        )
    elif shape == "rebuild":
        code = head + f"{var} = {_lit(letter)} + {var}[1:]\nprint({var})"
        distractors = [TYPE_ERROR, letter + word, word, letter + word[2:]]
        why = (
            f"This doesn't modify the old string: it builds a NEW string from {letter!r} and "
            f"`{var}[1:]` ({word[1:]!r}) and rebinds `{var}` to it, giving {new!r}."
        )
    elif shape == "listconv":
        code = (
            head + f"letters = list({var})\nletters[0] = {_lit(letter)}\n"
            'print("".join(letters))'
        )
        distractors = [TYPE_ERROR, word, str(list(new)), " ".join(new)]
        why = (
            f"`list({var})` makes a list of characters, and lists ARE mutable, so "
            f"`letters[0] = {_lit(letter)}` works; `\"\".join(letters)` glues them back into {new!r}."
        )
    else:
        suffix = rng.choice(["s", "!", "?"])
        code = head + f"{var} += {_lit(suffix)}\nprint({var}, len({var}))"
        grown = word + suffix
        distractors = [f"{word} {len(word)}", TYPE_ERROR, f"{grown} {len(word)}", ATTRIBUTE_ERROR]
        why = (
            f"`{var} += {_lit(suffix)}` is allowed: it creates a NEW string {grown!r} and rebinds "
            f"`{var}` to it (the old string is untouched). Its length is {len(grown)}."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_CITIES = [
    "new york", "cape town", "hong kong", "san diego", "las vegas", "el paso",
    "buenos aires", "abu dhabi", "rio grande", "kuala lumpur",
]
_METHODS = {
    "upper": str.upper,
    "title": str.title,
    "capitalize": str.capitalize,
}


@generator(TOPIC, MEDIUM)
def gen_methods_return_new(rng: random.Random) -> Question:
    """`s.upper()` on its own line does nothing to `s` — methods return NEW strings."""
    shape = rng.choice(["two_vars", "replace", "print_call"])
    if shape == "two_vars":
        city = rng.choice(_CITIES)
        m1, m2 = rng.sample(list(_METHODS), 2)
        f1, f2 = _METHODS[m1], _METHODS[m2]
        new_var = rng.choice(["fancy", "styled", "shown", "result"])
        code = f"city = {_lit(city)}\ncity.{m1}()\n{new_var} = city.{m2}()\nprint(city)\nprint({new_var})"
        mutated = f1(city)
        distractors = [
            f"{mutated}\n{f2(mutated)}",  # the bare call changed city
            f"{f2(mutated)}\n{f2(mutated)}",  # every call changes city
            f"{f2(mutated)}\nNone",  # methods mutate and return None, like list.sort()
            f"{city}\n{city}",
        ]
        why = (
            f"`city.{m1}()` builds a new string but the result is thrown away, so `city` "
            f"is still {city!r}. Only `{new_var}` keeps a result: {f2(city)!r}."
        )
    elif shape == "replace":
        word = rng.choice([w for w in _REPEAT_WORDS if len(set(w)) >= 3])
        c1 = rng.choice(_repeated_letters(word))
        c2 = rng.choice([c for c in sorted(set(word)) if c != c1])
        n1, n2 = rng.sample(_letters_not_in(word, "aeiouxyzkm"), 2)
        var = rng.choice(["word", "text", "snack"])
        code = (
            f"{var} = {_lit(word)}\n{var}.replace({_lit(c1)}, {_lit(n1)})\nprint({var})\n"
            f"{var} = {var}.replace({_lit(c2)}, {_lit(n2)})\nprint({var})"
        )
        w1 = word.replace(c1, n1)
        right2 = word.replace(c2, n2)
        distractors = [
            f"{w1}\n{w1.replace(c2, n2)}",
            f"{word}\n{w1.replace(c2, n2)}",
            f"{word}\n{word}",
            f"{w1}\n{right2}",
        ]
        why = (
            f"Line 2 calls `replace` but never stores the result, so `{var}` is unchanged "
            f"({word!r}). Line 4 assigns the result back, so `{var}` becomes {right2!r}."
        )
    else:
        word = rng.choice(["code", "loop", "snake", "tiger", "pixel", "lemon", "quest"])
        method = rng.choice(["upper", "capitalize"])
        fn = _METHODS[method]
        var = rng.choice(["word", "name", "pet"])
        extra = rng.choice(["!", "?", "..."])
        code = (
            f"{var} = {_lit(word)}\nprint({var}.{method}() + {_lit(extra)})\n"
            f"print({var})"
        )
        distractors = [
            f"{fn(word)}{extra}\n{fn(word)}",
            f"{fn(word)}{extra}\n{fn(word)}{extra}",
            f"{word}{extra}\n{word}",
            f"{fn(word)}{extra}\nNone",
        ]
        why = (
            f"`{var}.{method}()` returns a NEW string ({fn(word)!r}) that is used once in the "
            f"first `print`; `{var}` itself still refers to {word!r}."
        )
    return _output(code, MEDIUM, distractors, why, rng)


_SPLIT_DOMAINS = {
    "colors": ["red", "green", "blue", "pink", "gold", "gray", "teal", "navy"],
    "fruits": ["fig", "kiwi", "lime", "pear", "plum", "date", "apple", "mango"],
    "pets": ["cat", "dog", "fish", "bird", "frog", "hamster", "rabbit"],
}
_SENTENCES = [
    "the quick brown fox", "we love to code", "cats sleep all day",
    "pizza is the best", "time flies so fast", "keep calm and code on",
    "python is really fun",
]


@generator(TOPIC, MEDIUM)
def gen_split_join(rng: random.Random) -> Question:
    """split() returns a list, join() puts the separator only between items."""
    shape = rng.choice(["split", "words", "join", "roundtrip", "join_chars", "join_ints"])
    if shape == "split":
        domain = rng.choice(list(_SPLIT_DOMAINS))
        items = rng.sample(_SPLIT_DOMAINS[domain], 3)
        sep = rng.choice([",", ";", "-", "/"])
        line = sep.join(items)
        code = f"{domain} = {_lit(line)}\nprint({domain}.split({_lit(sep)}))"
        distractors = ["[" + ", ".join(items) + "]", str([line]), " ".join(items), TYPE_ERROR]
        why = (
            f"`split({_lit(sep)})` cuts the string at every {sep!r} and returns a LIST of the "
            "pieces; printing a list shows each string in quotes."
        )
    elif shape == "words":
        sentence = rng.choice(_SENTENCES)
        words = sentence.split()
        idx = rng.choice([1, 2, -1])
        code = (
            f"sentence = {_lit(sentence)}\nwords = sentence.split()\n"
            f"print(len(words), words[{idx}])"
        )
        k = len(words)
        distractors = [
            f"{k} {words[idx - 1]}", f"{len(sentence)} {sentence[idx]}",
            f"{k - 1} {words[idx]}", f"{k} {words[(idx + 1) % k]}",
        ]
        why = (
            f"`split()` with no argument splits on spaces and gives a list of {k} words; "
            f"index {idx} of that LIST is the word {words[idx]!r}."
        )
    elif shape == "join":
        domain = rng.choice(list(_SPLIT_DOMAINS))
        items = rng.sample(_SPLIT_DOMAINS[domain], 3)
        sep = rng.choice(["-", ", ", " + ", "/", "_", " & "])
        joined = sep.join(items)
        code = f"{domain} = {_list_lit(items)}\nprint({_lit(sep)}.join({domain}))"
        distractors = [joined + sep, str(items), "".join(items), sep.strip() + sep.join(items)]
        why = (
            f"`{_lit(sep)}.join(...)` puts the separator BETWEEN the items only, never "
            f"before the first or after the last, giving {joined!r}."
        )
    elif shape == "roundtrip":
        parts = rng.sample(["home", "user", "docs", "music", "photos", "games", "notes", "school"], 3)
        sep1, sep2 = rng.choice([(".", "/"), ("-", "/"), ("/", "."), ("_", " "), (",", ";")])
        text = sep1.join(parts)
        code = f"path = {_lit(text)}\nprint({_lit(sep2)}.join(path.split({_lit(sep1)})))"
        distractors = [str(parts), text, sep2.join(parts) + sep2, "".join(parts)]
        why = (
            f"`split({_lit(sep1)})` breaks the string into the list {parts}, then "
            f"`{_lit(sep2)}.join(...)` glues those pieces back together with {sep2!r} between them."
        )
    elif shape == "join_chars":
        word = rng.choice(["code", "loop", "cat", "python", "star", "byte"])
        sep = rng.choice(["-", ".", "*", "|"])
        code = f"word = {_lit(word)}\nprint({_lit(sep)}.join(word))"
        distractors = [word, TYPE_ERROR, sep.join(word) + sep, sep + word + sep]
        why = (
            "`join` accepts any iterable of strings, and looping over a string gives its "
            f"characters, so {sep!r} goes between every letter: {sep.join(word)!r}."
        )
    else:
        nums = rng.sample(range(1, 10), 3)
        sep = rng.choice(["+", ", ", "-"])
        code = f"nums = {nums}\nprint({_lit(sep)}.join(nums))"
        as_text = sep.join(str(n) for n in nums)
        distractors = [as_text, str(sum(nums)) if sep == "+" else str(nums), str(nums), "".join(map(str, nums))]
        why = (
            "`join` only accepts strings, and this list holds ints, so Python raises a "
            "TypeError. You would need to convert first, e.g. `map(str, nums)`."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


def _fixed(value_milli: int, places: int) -> str:
    """Render ``value_milli / 1000`` truncated to ``places`` decimals (no rounding)."""
    scaled = value_milli // 10 ** (3 - places)
    whole, frac = divmod(scaled, 10**places)
    return f"{whole}.{frac:0{places}d}"


@generator(TOPIC, MEDIUM)
def gen_fstring_format(rng: random.Random) -> Question:
    """f-strings: :.2f rounding, :03d zero padding, expressions in braces, a missing f."""
    shape = rng.choice(["decimals", "zeropad", "expr", "missing_f"])
    if shape == "decimals":
        whole = rng.randint(1, 99)
        d1, d2 = rng.randint(0, 9), rng.randint(0, 9)
        d3 = rng.choice([1, 2, 3, 4, 6, 7, 8, 9])
        literal = f"{whole}.{d1}{d2}{d3}"
        milli = whole * 1000 + d1 * 100 + d2 * 10 + d3
        places = rng.choice([1, 2, 2])
        var, label = rng.choice(
            [("price", "Price: $"), ("total", "Total: "), ("speed", "Speed: "), ("avg", "Average: ")]
        )
        code = f'{var} = {literal}\nprint(f"{label}{{{var}:.{places}f}}")'
        correct = format(float(literal), f".{places}f")
        trunc = _fixed(milli, places)
        bumped = _fixed(milli + 10 ** (3 - places), places)
        other = format(float(literal), f".{3 - places}f")
        distractors = [label + d for d in (trunc, literal, bumped, other, _fixed(milli, places - 1 or 1))]
        why = (
            f"`:.{places}f` shows the float with exactly {places} decimal place"
            f"{'s' if places > 1 else ''}, ROUNDING (not cutting off) the rest, so "
            f"{literal} becomes {correct}."
        )
    elif shape == "zeropad":
        width = rng.choice([3, 4, 5])
        num = rng.randint(1, 99 if width > 3 else 9 * rng.choice([1, 11]))
        if len(str(num)) >= width:
            num = rng.randint(1, 9)
        prefix, var = rng.choice([("ID-", "num"), ("#", "ticket"), ("Room ", "room"), ("Player ", "player")])
        code = f'{var} = {num}\nprint(f"{prefix}{{{var}:0{width}d}}")'
        padded = str(num).zfill(width)
        distractors = [
            prefix + str(num), prefix + str(num).ljust(width, "0"), prefix + "0" * width + str(num),
            prefix + str(num).zfill(width + 1), prefix + str(num).zfill(width - 1),
        ]
        why = (
            f"`:0{width}d` formats the integer at least {width} characters wide, padding on "
            f"the LEFT with zeros, so {num} becomes {padded}."
        )
    elif shape == "expr":
        x, y = rng.choice([("a", "b"), ("x", "y"), ("w", "h")])
        a, b = rng.randint(2, 9), rng.randint(2, 9)
        op = rng.choice(["+", "*"])
        result = a + b if op == "+" else a * b
        code = (
            f"{x} = {a}\n{y} = {b}\n"
            f'print(f"{{{x}}} {op} {{{y}}} = {{{x} {op} {y}}}")'
        )
        distractors = [
            f"{{{x}}} {op} {{{y}}} = {{{x} {op} {y}}}",
            f"{a} {op} {b} = {x} {op} {y}",
            f"{x} {op} {y} = {result}",
            f"{a} {op} {b} = {a}{b}",
        ]
        why = (
            "Inside an f-string, anything in `{}` is evaluated as Python code, so "
            f"`{{{x} {op} {y}}}` becomes {result}; the text outside the braces is printed as-is."
        )
    else:
        name = rng.choice(NAMES)
        v2, val, tail = rng.choice(
            [("age", rng.randint(9, 16), "years old"), ("coins", rng.randint(3, 50), "coins"),
             ("score", rng.randint(10, 99), "points")]
        )
        verb = "is" if v2 == "age" else "has"
        template = f"{{name}} {verb} {{{v2}}} {tail}"
        code = f"name = {_lit(name)}\n{v2} = {val}\nprint({_lit(template)})"
        distractors = [
            f"{name} {verb} {val} {tail}",
            f"name {verb} {v2} {tail}",
            f"{{{name}}} {verb} {{{val}}} {tail}",
            error_choice("NameError"),
        ]
        why = (
            "There is no `f` before the opening quote, so this is an ordinary string: the "
            "braces are printed literally and no variables are substituted."
        )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_loop_build(rng: random.Random) -> Question:
    """Trace a short for-loop that builds or counts over a string."""
    shape = rng.choice(["reverse", "count", "filter", "upper_vowels"])
    if shape == "reverse":
        word = rng.choice(["stop", "drawer", "parts", "smart", "plan", "star", "time", "live", "code", "spin"])
        code = (
            f"word = {_lit(word)}\nresult = \"\"\nfor ch in word:\n"
            "    result = ch + result\nprint(result)"
        )
        distractors = [word, word[:-1][::-1], word[1:][::-1], word[-1]]
        steps = ", ".join(repr(word[:i + 1][::-1]) for i in range(min(3, len(word))))
        why = (
            f"Each character is put in FRONT of what has been built so far ({steps}, …), "
            f"so the string comes out reversed: {word[::-1]!r}."
        )
    elif shape == "count":
        word = rng.choice(
            ["education", "banana", "computer", "programming", "elephant", "umbrella",
             "avocado", "television", "keyboard", "dinosaur"]
        )
        negate = rng.random() < 0.35
        cond = "not in" if negate else "in"
        var = rng.choice(["count", "total", "hits"])
        code = (
            f"word = {_lit(word)}\n{var} = 0\nfor ch in word:\n"
            f"    if ch {cond} \"aeiou\":\n        {var} += 1\nprint({var})"
        )
        vowels = [c for c in word if c in "aeiou"]
        c = len(word) - len(vowels) if negate else len(vowels)
        unique = len({ch for ch in word if (ch not in "aeiou") == negate})
        distractors = [unique, c + 1, c - 1, len(word) - c, len(word)]
        kind = "consonants" if negate else "vowels"
        why = (
            f"The loop adds 1 for every character that is {cond} 'aeiou' — repeats count "
            f"each time. {word!r} has {c} {kind}."
        )
    elif shape == "filter":
        word = rng.choice([w for w in _REPEAT_WORDS if len(w) <= 8])
        ch = rng.choice(_repeated_letters(word))
        code = (
            f"word = {_lit(word)}\nresult = \"\"\nfor ch in word:\n"
            f"    if ch != {_lit(ch)}:\n        result += ch\nprint(result)"
        )
        correct = word.replace(ch, "")
        distractors = [ch * word.count(ch), word, word.replace(ch, "", 1), correct[::-1]]
        why = (
            f"Only characters that are NOT {ch!r} get added to `result`, so every {ch!r} is "
            f"skipped and the rest keep their order: {correct!r}."
        )
    else:
        word = rng.choice(["banana", "potato", "tomato", "papaya", "piano", "radio", "camera", "volcano"])
        code = (
            f"word = {_lit(word)}\nresult = \"\"\nfor ch in word:\n"
            "    if ch in \"aeiou\":\n        result += ch.upper()\n"
            "    else:\n        result += ch\nprint(result)"
        )
        correct = "".join(c.upper() if c in "aeiou" else c for c in word)
        distractors = [
            "".join(c if c in "aeiou" else c.upper() for c in word),
            word.upper(),
            "".join(c.upper() for c in word if c in "aeiou"),
            word,
        ]
        why = (
            "Vowels are added in uppercase and every other character is added unchanged by "
            f"the `else`, so {word!r} becomes {correct!r}."
        )
    return _output(code, MEDIUM, distractors, why, rng)


_FRUIT_WORDS = ["apple", "banana", "cherry", "grape", "kiwi", "lemon", "mango", "peach", "plum", "melon", "orange"]
_PREFIX_PAIRS = [
    ("car", "card"), ("plan", "planet"), ("rock", "rocket"), ("snow", "snowman"),
    ("foot", "football"), ("pin", "pine"), ("star", "start"), ("art", "artist"),
    ("ten", "tent"), ("hat", "hatch"), ("cat", "catch"), ("sun", "sunny"),
]
_LATER_PAIRS = [
    ("cart", "cast"), ("bake", "bike"), ("ship", "shop"), ("pin", "pit"), ("tap", "tan"),
    ("rock", "rose"), ("lamp", "lamb"), ("note", "nose"), ("bear", "beer"), ("snow", "snap"),
]


def _two_initials(rng: random.Random) -> list[str]:
    """Two fruit words with different first letters."""
    while True:
        pair = rng.sample(_FRUIT_WORDS, 2)
        if pair[0][0] != pair[1][0]:
            return pair


def _comparison(rng: random.Random, kind: str) -> tuple[str, str, str, bool]:
    """(left, op, right, gotcha) for one string comparison of the given kind."""
    op = rng.choice(["<", ">"])
    if kind == "case":
        lo, hi = sorted(_two_initials(rng))
        pair = [hi.capitalize(), lo]
        rng.shuffle(pair)
        return pair[0], op, pair[1], True
    if kind == "digits":
        small = rng.randint(2, 9)
        big = rng.choice([n for n in range(10, 100) if str(n)[0] < str(small)])
        pair = [str(big), str(small)]
        rng.shuffle(pair)
        return pair[0], op, pair[1], True
    if kind == "prefix":
        pair = list(rng.choice(_PREFIX_PAIRS))
        rng.shuffle(pair)
        return pair[0], op, pair[1], False
    if kind == "later":
        pair = list(rng.choice(_LATER_PAIRS))
        rng.shuffle(pair)
        return pair[0], op, pair[1], False
    a, b = _two_initials(rng)
    return a, op, b, False


def _comparison_reason(left: str, op: str, right: str) -> str:
    value = left < right if op == "<" else left > right
    i = 0
    while i < min(len(left), len(right)) and left[i] == right[i]:
        i += 1
    expr = f"`{_lit(left)} {op} {_lit(right)}` is {value}"
    if i == min(len(left), len(right)):
        shorter = left if len(left) < len(right) else right
        return f"{expr}: {shorter!r} is the start of the other word, and the shorter one comes first"
    lo, hi = sorted((left[i], right[i]))
    if lo.isupper() and hi.islower():
        return f"{expr}: every uppercase letter comes before every lowercase one, so {lo!r} < {hi!r}"
    if lo.isdigit() and hi.isdigit():
        return f"{expr}: strings compare character by character, not as numbers, and {lo!r} < {hi!r}"
    where = "first letters decide" if i == 0 else f"first difference (index {i}) decides"
    return f"{expr}: the {where} it, and {lo!r} < {hi!r}"


@generator(TOPIC, MEDIUM)
def gen_compare_strings(rng: random.Random) -> Question:
    """Lexicographic comparison: case, digit strings, prefixes, first difference."""
    gotcha = rng.choice(["case", "digits"])
    other = rng.choice(["prefix", "later", "plain", "case" if gotcha == "digits" else "digits"])
    kinds = [gotcha, other]
    rng.shuffle(kinds)
    comps = [_comparison(rng, k) for k in kinds]
    if comps[0][0::2] == comps[1][0::2]:
        raise GenerationError("duplicate comparison")
    code = "\n".join(f"print({_lit(l)} {op} {_lit(r)})" for l, op, r, _ in comps)
    combos = [f"{x}\n{y}" for x in ("True", "False") for y in ("True", "False")]
    why = "; ".join(_comparison_reason(l, op, r) for l, op, r, _ in comps) + "."
    return _output(code, MEDIUM, combos, why, rng)


@generator(TOPIC, MEDIUM)
def gen_fill_blank(rng: random.Random) -> Question:
    """Pick the slice / method / separator that makes the code print a target."""
    shape = rng.choice(["slice", "method", "join", "search"])
    if shape == "slice":
        word = rng.choice(_LONG_WORDS)
        var = rng.choice(_WORD_VARS)
        n = len(word)
        a = rng.randint(1, n - 5)
        b = a + rng.randint(2, 3)
        if rng.random() < 0.3:
            correct = f"{a - n}:{b - n}"
        else:
            correct = f"{a}:{b}"
        cands = [
            f"{a}:{b - 1}", f"{a + 1}:{b + 1}", f"{a - 1}:{b - 1}", f"{a}:{b + 1}",
            f"{a + 1}:{b}", f"{a - 1}:{b}", f"{b}:{a}",
        ]
        template = f"{var} = {_lit(word)}\nprint({var}[{BLANK}])"
        why = (
            f"The slice must start at index {a} ({word[a]!r}) and stop just BEFORE index {b}"
            + (f" (which is {b - n} counting from the end)" if correct.startswith("-") else "")
            + f", so `{var}[{correct}]` prints {word[a:b]}."
        )
    elif shape == "method":
        phrase = _mixed_case_phrase(rng)
        method = rng.choice(["upper", "lower", "title", "capitalize", "swapcase"])
        correct = method
        cands = ["upper", "lower", "title", "capitalize", "swapcase", "strip"]
        var = rng.choice(["msg", "phrase", "text"])
        template = f"{var} = {_lit(phrase)}\nprint({var}.{BLANK}())"
        why = {
            "upper": "`upper()` makes every letter uppercase",
            "lower": "`lower()` makes every letter lowercase",
            "title": "`title()` capitalizes the first letter of every word and lowercases the rest",
            "capitalize": "`capitalize()` uppercases only the first character and lowercases everything else",
            "swapcase": "`swapcase()` flips the case of every letter",
        }[method] + f", turning {phrase!r} into {getattr(phrase, method)()!r}."
    elif shape == "join":
        domain = rng.choice(list(_SPLIT_DOMAINS))
        items = rng.sample(_SPLIT_DOMAINS[domain], 3)
        seps = [", ", ",", " ", "", "-", " - ", "/", " / "]
        sep = rng.choice(seps)
        correct = _lit(sep)
        cands = [_lit(s) for s in seps]
        rng.shuffle(cands)
        template = f"{domain} = {_list_lit(items)}\nprint({BLANK}.join({domain}))"
        why = (
            f"`join` puts its string between each pair of items, so to get {sep.join(items)!r} "
            f"the separator must be exactly {sep!r}."
        )
    else:
        word = rng.choice([w for w in _REPEAT_WORDS if len(w) >= 5])
        ch = rng.choice(_repeated_letters(word))
        method = rng.choice(["count", "find", "rfind"])
        correct = method
        cands = ["count", "find", "rfind", "index", "startswith", "endswith"]
        var = rng.choice(["word", "text"])
        template = f"{var} = {_lit(word)}\nprint({var}.{BLANK}({_lit(ch)}))"
        where = ", ".join(str(i) for i in _indexes(word, ch))
        why = (
            f"{ch!r} appears at indexes {where} of {word!r}: `count` gives how many "
            f"({word.count(ch)}), `find` the first index ({word.find(ch)}) and `rfind` the "
            f"last ({word.rfind(ch)})."
        )
    target = _run(template.replace(BLANK, correct))
    if target.startswith("Error:") or target == NOTHING_PRINTED:
        raise GenerationError("blank's correct answer does not print")
    wrong = [
        c for c in cands
        if c != correct and _run(template.replace(BLANK, c)) != target
    ]
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which choice fills the blank (`{BLANK}`) so that the code prints `{target}`?",
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
        code=template,
    )


_SEARCH_TEXTS = [
    "banana", "hello world", "good food", "cocoa", "rabbit", "pepper",
    "abracadabra", "tomato", "coconut", "mississippi", "bookkeeper", "see the sea",
]


@generator(TOPIC, MEDIUM)
def gen_search_methods(rng: random.Random) -> Question:
    """find(sub, start), rfind, index of a substring, and index() raising ValueError."""
    text = rng.choice(_SEARCH_TEXTS)
    var = rng.choice(["text", "word", "msg"])
    head = f"{var} = {_lit(text)}\n"
    shape = rng.choice(["find_start", "index_missing", "index_present", "rfind", "find_sub"])
    letters = [c for c in _repeated_letters(text) if c != " "]
    if shape == "find_start":
        ch = rng.choice(letters)
        pos = _indexes(text, ch)
        start = rng.randint(pos[0] + 1, pos[-1])
        result = text.find(ch, start)
        code = head + f"print({var}.find({_lit(ch)}, {start}))"
        distractors = [pos[0], result - start, -1, result + 1, VALUE_ERROR]
        why = (
            f"The second argument tells `find` where to START searching. From index {start} "
            f"onward, the first {ch!r} is at index {result} (indexes still count from the "
            "start of the whole string)."
        )
    elif shape == "index_missing":
        ch = rng.choice(_letters_not_in(text, "zqxjvwyk"))
        code = head + f"print({var}.index({_lit(ch)}))"
        distractors = [-1, INDEX_ERROR, "None", 0]
        why = (
            f"{ch!r} isn't in {text!r}. Unlike `find` (which returns -1), `index` raises a "
            "ValueError when the substring is not found."
        )
    elif shape == "index_present":
        ch = rng.choice(letters)
        pos = _indexes(text, ch)
        code = head + f"print({var}.index({_lit(ch)}))"
        distractors = [pos[0] + 1, pos[-1], VALUE_ERROR, text.count(ch), -1]
        why = (
            f"`index` works like `find` when the text IS present: it returns the first "
            f"position of {ch!r}, which is index {pos[0]}."
        )
    elif shape == "rfind":
        ch = rng.choice(letters)
        pos = _indexes(text, ch)
        code = head + f"print({var}.rfind({_lit(ch)}))"
        distractors = [pos[0], pos[-1] - len(text), text.count(ch), pos[-1] + 1, VALUE_ERROR]
        why = (
            f"`rfind` searches from the right and returns the index of the LAST {ch!r}, "
            f"but the index is still counted from the left: {pos[-1]}."
        )
    else:
        starts = [i for i in range(1, len(text) - 2) if text[i] != " " and text[i + 1] != " "]
        i = rng.choice(starts)
        sub = text[i:i + rng.choice([2, 3])]
        if " " in sub:
            sub = sub.replace(" ", "")
        first = text.find(sub)
        code = head + f"print({var}.find({_lit(sub)}))"
        distractors = [first + 1, first + len(sub) - 1, first + len(sub), -1, VALUE_ERROR]
        why = (
            f"For a multi-character substring, `find` returns the index where the FIRST "
            f"match starts: {sub!r} first begins at index {first}."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


# ==========================================================================
# HARD
# ==========================================================================


def _neg_spec(rng: random.Random, n: int, kind: str):
    if kind == "down":
        b = rng.randint(0, n - 5)
        a = rng.randint(b + 3, min(n - 1, b + 5))
        return (a, b, -1)
    if kind == "negdown":
        i = rng.randint(1, 2)
        j = i + rng.randint(3, 4)
        return (-i, -j, -1)
    if kind == "from":
        return (rng.randint(2, 4), None, -1)
    if kind == "to":
        return (None, rng.randint(n - 6, n - 4), -1)
    start = rng.choice([None, n - 2])
    step = -3 if n - 1 >= 8 and rng.random() < 0.4 else -2
    return (start, None, step)


def _neg_models(n: int, spec) -> dict[str, list[int]]:
    """Index lists for the right answer and common misreadings of a negative-step slice."""
    start, stop, step = slice(*spec).indices(n)
    correct = list(range(start, stop, step))
    inc_stop = correct + [stop] if step == -1 and stop >= 0 else correct
    return {
        "correct": correct,
        "inc_stop": inc_stop,
        "exc_start": correct[1:],
        "shift": [i - 1 for i in correct if i - 1 >= 0],
        "forward": sorted(correct),
    }


@generator(TOPIC, HARD)
def gen_negative_step_slices(rng: random.Random) -> Question:
    """Slices with a negative step: start is included, stop excluded, walking left."""
    word = rng.choice(_LONG_WORDS)
    var = rng.choice(_WORD_VARS)
    n = len(word)
    if rng.random() < 0.3:
        a, b, _ = _neg_spec(rng, n, "down")
        if b == 0:
            b = 1
            a = max(a, 4)
        target = word[a:b:-1]
        wrong = [
            f"{var}[{b}:{a}:-1]", f"{var}[{a}:{b - 1}:-1]", f"{var}[{a - 1}:{b}:-1]",
            f"{var}[{a + 1}:{b + 1}:-1]", f"{var}[{a - 1}:{b - 1}:-1]", f"{var}[{b + 1}:{a + 1}]",
        ]
        rng.shuffle(wrong)
        return which_expression_question(
            topic=TOPIC,
            difficulty=HARD,
            prompt=f"Which expression evaluates to `{target!r}`?",
            setup=f"{var} = {_lit(word)}",
            target=target,
            correct_expr=f"{var}[{a}:{b}:-1]",
            wrong_exprs=wrong,
            explanation=(
                f"With step -1 the slice starts AT the start index and walks left, stopping just "
                f"BEFORE the stop index. {target!r} runs from index {a} down to {b + 1}, so the "
                f"slice is `{var}[{a}:{b}:-1]`."
            ),
            rng=rng,
        )
    kinds = rng.sample(["down", "negdown", "from", "to", "step"], 2)
    specs = [_neg_spec(rng, n, k) for k in kinds]
    models = [_neg_models(n, s) for s in specs]
    if any(len(m["correct"]) < 3 for m in models):
        raise GenerationError("slice too short")

    def render(name_per_line: list[str]) -> str | None:
        lines = ["".join(word[i] for i in m[name]) for m, name in zip(models, name_per_line)]
        return "\n".join(lines) if all(lines) else None

    names = ["inc_stop", "exc_start", "shift", "forward"]
    candidates = [render([nm, nm]) for nm in names]
    candidates += [render(["correct", nm]) for nm in names] + [render([nm, "correct"]) for nm in names]
    distractors = [c for c in candidates if c]
    code = f"{var} = {_lit(word)}\n" + "\n".join(f"print({var}[{_slice_src(*s)}])" for s in specs)
    traces = []
    for s, m in zip(specs, models):
        shown = [i - n for i in m["correct"]] if s[0] is not None and s[0] < 0 else m["correct"]
        idx = ", ".join(str(i) for i in shown)
        got = "".join(word[i] for i in m["correct"])
        traces.append(f"`{var}[{_slice_src(*s)}]` takes indexes {idx} ({got!r})")
    why = (
        "With a negative step a slice starts AT its start index (default: the last character) "
        "and walks left, stopping just BEFORE its stop index. So " + " and ".join(traces) + "."
    )
    return _output(code, HARD, distractors, why, rng)


_STRIP_FILES = {
    ".txt": (
        ["report", "budget", "draft", "chart", "receipt", "script", "test", "index", "toast"],
        ["photo", "notes", "menu", "story", "plan", "music", "song", "data"],
    ),
    ".csv": (
        ["music", "notes", "basics", "scores", "class", "sales"],
        ["report", "budget", "data", "plan", "story", "menu"],
    ),
    ".py": (
        ["happy", "copy", "story", "sleepy", "party", "spy"],
        ["main", "game", "utils", "helper", "robot", "menu"],
    ),
}
_STRIP_WORDS = [
    "banana", "abracadabra", "mississippi", "tomato", "papaya", "racecar",
    "seashells", "cocoa", "eleven", "alfalfa", "assess", "barbara",
]


def _remove_affixes(text: str, chars: str) -> str:
    """The 'strip removes that exact substring' misconception."""
    if text.startswith(chars):
        text = text[len(chars):]
    if text.endswith(chars):
        text = text[: -len(chars)]
    return text


@generator(TOPIC, HARD)
def gen_strip_chars(rng: random.Random) -> Question:
    """strip/rstrip(chars) removes any of those CHARACTERS from the ends, not a suffix."""
    if rng.random() < 0.55:
        ext = rng.choice(list(_STRIP_FILES))
        gotchas, safes = _STRIP_FILES[ext]
        n_got = rng.choice([1, 1, 2])
        stems = rng.sample(gotchas, n_got) + rng.sample(safes, rng.choice([1, 2]) if n_got == 1 else 1)
        rng.shuffle(stems)
        files = [s + ext for s in stems]
        code = (
            f"files = {_list_lit(files)}\nfor name in files:\n"
            f"    print(name.rstrip({_lit(ext)}))"
        )
        distractors = [
            "\n".join(stems),
            "\n".join("".join(c for c in f if c not in ext) for f in files),
            "\n".join(files),
            "\n".join(s[:-1] for s in stems),
        ]
        bad = next(f for f, s in zip(files, stems) if f.rstrip(ext) != s)
        why = (
            f"`rstrip({_lit(ext)})` does not remove the suffix {ext!r}: it removes ANY of the "
            f"characters {', '.join(repr(c) for c in sorted(set(ext)))} from the right until it "
            f"hits a different one. So {bad!r} also loses its last letter(s) and becomes "
            f"{bad.rstrip(ext)!r}, while names ending in other letters keep them."
        )
    else:
        for _ in range(100):
            word = rng.choice(_STRIP_WORDS)
            calls = []
            for method in rng.sample(["strip", "lstrip", "rstrip"], 2):
                if method == "rstrip":
                    chars = word[-2:]
                elif method == "lstrip":
                    chars = word[:2]
                else:
                    chars = rng.choice([word[:2], word[-2:], word[0] + word[-1]])
                chars = "".join(rng.sample(chars, len(chars))) if len(set(chars)) > 1 else chars
                calls.append((method, chars))
            results = [getattr(word, m)(c) for m, c in calls]
            if all(r and r != word for r in results) and results[0] != results[1]:
                break
        else:
            raise GenerationError("uninteresting strip")
        var = rng.choice(["word", "text"])
        code = f"{var} = {_lit(word)}\n" + "\n".join(f"print({var}.{m}({_lit(c)}))" for m, c in calls)

        def model(fn) -> str | None:
            lines = [fn(m, c) for m, c in calls]
            return "\n".join(lines) if all(lines) else None

        def affix(m: str, c: str) -> str:
            if m == "lstrip":
                return word[len(c):] if word.startswith(c) else word
            if m == "rstrip":
                return word[: -len(c)] if word.endswith(c) else word
            return _remove_affixes(word, c)

        def once(m: str, c: str) -> str:
            left = 1 if m != "rstrip" and word[0] in c else 0
            right = len(word) - 1 if m != "lstrip" and word[-1] in c else len(word)
            return word[left:right]

        distractors = [
            model(affix),
            model(once),
            model(lambda m, c: "".join(ch for ch in word if ch not in c)),
            model(lambda m, c: word.strip(c)),
            model(lambda m, c: word),
        ]
        distractors = [d for d in distractors if d]
        why = (
            "The argument to `strip`/`lstrip`/`rstrip` is a SET of characters, not a substring: "
            "Python keeps removing any of those characters from the end(s) until it meets one "
            "that isn't in the set. " + "; ".join(
                f"`{m}({_lit(c)})` gives {r!r}" for (m, c), r in zip(calls, results)
            ) + "."
        )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_split_edge_cases(rng: random.Random) -> Question:
    """Empty fields from split(","), split() vs split(" "), doubled separators."""
    shape = rng.choice(["fields", "spaces", "doubled"])
    if shape == "fields":
        k = rng.randint(4, 6)
        values = [str(rng.randint(1, 9)) for _ in range(k)]
        empties = set(rng.sample(range(1, k), rng.randint(1, 2)))
        fields = ["" if i in empties else v for i, v in enumerate(values)]
        line = ",".join(fields)
        name = rng.choice(["line", "row", "record"])
        code = (
            f"{name} = {_lit(line)}\nparts = {name}.split(\",\")\nprint(len(parts))\n"
            "filled = 0\nfor part in parts:\n    if part:\n        filled += 1\nprint(filled)"
        )
        full = k - len(empties)
        trailing = 1 if fields[-1] == "" else 0
        distractors = [
            f"{full}\n{full}", f"{k}\n{k}", f"{k - trailing}\n{full}" if trailing else f"{k - 1}\n{full}",
            f"{k + 1}\n{full}", f"{k}\n{full + 1}",
        ]
        why = (
            f"`split(\",\")` makes a piece for every gap between commas, keeping EMPTY strings "
            f"where two commas touch or the line ends with one: {fields}, so {k} parts. "
            f"Empty strings are falsy, so only {full} parts count as filled."
        )
    elif shape == "spaces":
        words = rng.sample(["big", "red", "dog", "hot", "tea", "sun", "day", "fun", "cat"], rng.randint(2, 3))
        lead, trail = rng.randint(0, 2), rng.randint(0, 2)
        gaps = [rng.randint(1, 3) for _ in words[1:]]
        if lead == 0 and trail == 0 and all(g == 1 for g in gaps):
            gaps[0] = 2
        text = " " * lead + "".join(w + " " * g for w, g in zip(words, gaps + [0])) + " " * trail
        m = len(text.split(" "))
        w = len(words)
        code = f"text = {_lit(text)}\nprint(len(text.split()))\nprint(len(text.split(\" \")))"
        distractors = [
            f"{w}\n{w}", f"{m}\n{m}", f"{w}\n{text.count(' ')}", f"{w}\n{m - 1}", f"{w}\n{m + 1}",
        ]
        why = (
            f"`split()` with no argument splits on RUNS of whitespace and ignores spaces at "
            f"the ends ({w} words), but `split(\" \")` splits at EVERY single space, so each "
            f"extra or edge space adds an empty string: {m} pieces."
        )
    else:
        domain = rng.choice(list(_SPLIT_DOMAINS))
        items = rng.sample([x for x in _SPLIT_DOMAINS[domain] if len(x) <= 5], 3)
        sep = rng.choice(["-", ",", ";", "|"])
        mode = rng.choice(["all", "one"])
        if mode == "all":
            data = (sep * 2).join(items)
        else:
            data = items[0] + sep * 2 + items[1] + sep + items[2]
        code = f"data = {_lit(data)}\nprint(data.split({_lit(sep)}))"
        result = data.split(sep)
        distractors = [
            str(items),
            str([x for part in data.split(sep) for x in ([part] if part else [sep])]),
            str(data.split(sep * 2)) if mode == "one" else str([data]),
            str(result[:-1]),
            str([data]),
        ]
        why = (
            f"`split({_lit(sep)})` cuts at EVERY {sep!r}. Between two {sep!r} characters in a row "
            f"there is nothing, so an empty string '' appears in the list: {result}."
        )
    return _output(code, HARD, distractors, why, rng)


_DOUBLE_WORDS = [
    "bookkeeper", "balloon", "committee", "mississippi", "coffee", "address",
    "letter", "bubble", "goodness", "happiness", "llama", "sleepless", "aardvark",
    "keepsake", "puppy", "yellow", "success", "carroll", "woodpecker",
]


@generator(TOPIC, HARD)
def gen_index_loop_trace(rng: random.Random) -> Question:
    """Index-based loops: i % k patterns, word[i] == word[i + 1], range counting down."""
    shape = rng.choice(["pattern", "pattern", "pairs", "backward"])
    if shape == "pattern":
        word = rng.choice(_LONG_WORDS)
        k = rng.choice([2, 2, 3])
        r = rng.choice([0, 1])
        action = rng.choice(["upper", "star"])
        then_code = "word[i].upper()" if action == "upper" else '"*"'
        code = (
            f"word = {_lit(word)}\nresult = \"\"\nfor i in range(len(word)):\n"
            f"    if i % {k} == {r}:\n        result += {then_code}\n"
            "    else:\n        result += word[i]\nprint(result)"
        )

        def build(select, keep_else: bool = True) -> str:
            out = []
            for i, ch in enumerate(word):
                if select(i):
                    out.append(ch.upper() if action == "upper" else "*")
                elif keep_else:
                    out.append(ch)
            return "".join(out)

        correct = build(lambda i: i % k == r)
        distractors = [
            build(lambda i: (i + 1) % k == r),  # counted positions from 1
            build(lambda i: i % k != r),  # swapped the branches
            build(lambda i: i % k == r, keep_else=False),  # ignored the else
            build(lambda i: (i - 1) % k == r),
            build(lambda i: True),  # changed every character
            word,
        ]
        hits = ", ".join(str(i) for i in range(len(word)) if i % k == r)
        why = (
            f"`i` is the index (starting at 0), and `i % {k} == {r}` is true for indexes "
            f"{hits}; those characters are changed and the `else` copies the rest, giving {correct!r}."
        )
        return _output(code, HARD, distractors, why, rng)
    if shape == "pairs":
        word = rng.choice(_DOUBLE_WORDS)
        buggy = rng.random() < 0.35
        stop = "len(word)" if buggy else "len(word) - 1"
        code = (
            f"word = {_lit(word)}\ncount = 0\nfor i in range({stop}):\n"
            "    if word[i] == word[i + 1]:\n        count += 1\nprint(count)"
        )
        pairs = [word[i:i + 2] for i in range(len(word) - 1) if word[i] == word[i + 1]]
        c = len(pairs)
        if buggy:
            distractors = [c, c + 1, 2 * c, c - 1 if c > 1 else c + 2, 0]
            why = (
                f"`range(len(word))` lets `i` reach the last index {len(word) - 1}, and then "
                f"`word[i + 1]` is `word[{len(word)}]`, which is past the end. The IndexError "
                "happens inside the loop, so `print` never runs."
            )
        else:
            repeats = len(word) - len(set(word))
            distractors = [c + 1, INDEX_ERROR, 2 * c, repeats, c - 1]
            why = (
                "The loop compares each character with the next one; `range(len(word) - 1)` "
                f"stops early so `word[i + 1]` stays in range. The matching pairs are "
                f"{', '.join(repr(p) for p in pairs)}, so count is {c}."
            )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)
    word = rng.choice(_LONG_WORDS)
    n = len(word)
    s0 = rng.choice([1, 2])
    stop = rng.choice([0, -1])
    step = -3 if n - s0 >= 7 and rng.random() < 0.35 else -2
    start_src = f"len(word) - {s0}"
    code = (
        f"word = {_lit(word)}\nresult = \"\"\nfor i in range({start_src}, {stop}, {step}):\n"
        "    result += word[i]\nprint(result)"
    )
    idxs = list(range(n - s0, stop, step))
    if len(idxs) < 3:
        raise GenerationError("too short")

    def pick(indexes) -> str:
        return "".join(word[i] for i in indexes)

    distractors = [
        pick(range(n - s0, stop - 1 if stop == 0 else -1, step)),  # stop treated as inclusive
        pick(range(n - s0 - 1, stop, step)),  # started one earlier
        pick(sorted(idxs)),  # forgot it goes backwards
        pick(range(n - s0 + 1, stop, step)) if s0 > 1 else INDEX_ERROR,
        NOTHING_PRINTED if stop == -1 else pick(range(n - s0, 1, step)),
    ]
    why = (
        f"`range({n - s0}, {stop}, {step})` counts down from {n - s0} in steps of {abs(step)} "
        f"and stops BEFORE reaching {stop} (in `range`, {stop} is just a number, not 'the end'): "
        f"indexes {', '.join(str(i) for i in idxs)}, giving {pick(idxs)!r}."
    )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


_ALIAS_NAMES = [("word", "saved"), ("name", "backup"), ("text", "original"), ("msg", "old_msg")]
_ALIAS_BASES = ["snow", "sun", "rain", "star", "moon", "cup", "pan", "fire", "sea", "home"]
_ALIAS_SUFFIXES = ["man", "fall", "light", "day", "ball", "fish", "!", "s"]


def _alias_sim(base: str, names: tuple[str, str], ops, *, share: bool, iadd_inplace: bool,
               call_inplace: bool, assign_inplace: bool = False) -> str:
    """Run ``ops`` under a (possibly wrong) mental model of how strings behave.

    ``share``: ``b = a`` makes both names use one storage cell.  The ``*_inplace``
    flags say whether ``+=``, a bare method call, or ``x = x.method()`` write into
    that shared cell (wrong for strings) instead of rebinding / doing nothing.
    """
    a, b = names
    cells = {a: [base]}
    cells[b] = cells[a] if share else [base]
    for kind, var, fn, _src in ops:
        if kind == "iadd":
            if iadd_inplace:
                cells[var][0] += fn
            else:
                cells[var] = [cells[var][0] + fn]
        elif kind == "call":
            if call_inplace:
                cells[var][0] = fn(cells[var][0])
        elif assign_inplace:
            cells[var][0] = fn(cells[var][0])
        else:
            cells[var] = [fn(cells[var][0])]
    return f"{cells[a][0]} {cells[b][0]}"


@generator(TOPIC, HARD)
def gen_alias_immutability(rng: random.Random) -> Question:
    """Two names for one string, then +=, discarded method calls and reassignment."""
    names = rng.choice(_ALIAS_NAMES)
    a, b = names
    base, other = rng.sample(_ALIAS_BASES, 2)
    suffix = rng.choice(_ALIAS_SUFFIXES)
    methods = [
        (str.upper, ".upper()"),
        (str.capitalize, ".capitalize()"),
        (lambda s, x=base, y=other: s.replace(x, y), f".replace({_lit(base)}, {_lit(other)})"),
    ]
    rng.shuffle(methods)
    # One +=, one discarded call, and one more call that is either discarded or assigned.
    ops = [
        ("iadd", rng.choice(names), suffix, None),
        ("call", rng.choice(names), *methods[0]),
        (rng.choice(["assign", "assign", "call"]), rng.choice(names), *methods[1]),
    ]
    rng.shuffle(ops)
    lines = [f"{a} = {_lit(base)}", f"{b} = {a}"]
    for kind, var, fn, src in ops:
        if kind == "iadd":
            lines.append(f"{var} += {_lit(fn)}")
        elif kind == "call":
            lines.append(f"{var}{src}")
        else:
            lines.append(f"{var} = {var}{src}")
    lines.append(f"print({a}, {b})")
    code = "\n".join(lines)
    correct = _alias_sim(base, names, ops, share=True, iadd_inplace=False, call_inplace=False)
    if _run(code) != correct:
        raise GenerationError("alias model disagrees with Python")
    models = [
        # Bare method calls change the string (the most common slip).
        dict(share=False, iadd_inplace=False, call_inplace=True),
        # "b = a means b IS a": every change shows up under both names.
        dict(share=True, iadd_inplace=True, call_inplace=True, assign_inplace=True),
        # Strings behave like lists: += and bare calls mutate the shared object.
        dict(share=True, iadd_inplace=True, call_inplace=True),
        # Aliasing shares +=, but bare calls are (correctly) discarded.
        dict(share=True, iadd_inplace=True, call_inplace=False, assign_inplace=True),
        dict(share=True, iadd_inplace=True, call_inplace=False),
        dict(share=True, iadd_inplace=False, call_inplace=True),
    ]
    final_a, final_b = correct.split(" ")
    distractors = [_alias_sim(base, names, ops, **m) for m in models]
    distractors += [f"{final_b} {final_a}", f"{final_a} {final_a}", f"{final_b} {final_b}", f"{base} {base}"]
    assigned = [f"`{v} = {v}{src}`" for kind, v, _fn, src in ops if kind == "assign"]
    kept = f" (only {assigned[0]} keeps its result)" if assigned else ""
    why = (
        f"`{b} = {a}` makes both names refer to the same string, but strings can't change: "
        f"`+=` builds a NEW string and rebinds only that one name, and a method call whose "
        f"result isn't assigned is thrown away{kept}. So `{a}` ends as {final_a!r} and "
        f"`{b}` as {final_b!r}."
    )
    return _output(code, HARD, distractors, why, rng)


_SORT_WORDS = ["apple", "banana", "cherry", "grape", "kiwi", "lemon", "mango", "peach", "plum", "fig", "date", "lime", "pear"]


@generator(TOPIC, HARD)
def gen_sorting_strings(rng: random.Random) -> Question:
    """Sorting / max / min of strings: uppercase first, digit strings are not numbers."""
    shape = rng.choice(["mixed", "numeric", "maxmin", "chars"])
    if shape in ("mixed", "maxmin"):
        for _ in range(50):
            words = rng.sample(_SORT_WORDS, 4)
            if len({w[0] for w in words}) < 4:
                continue
            order = sorted(words)
            caps = rng.sample(order[1:], rng.choice([1, 2]))
            words = [w.capitalize() if w in caps else w for w in words]
            if sorted(words) != sorted(words, key=str.lower):
                break
        else:
            raise GenerationError("no interesting word mix")
        var = rng.choice(["fruits", "words", "items"])
        if shape == "mixed":
            if rng.random() < 0.5:
                code = f"{var} = {_list_lit(words)}\n{var}.sort()\nprint({var})"
            else:
                code = f"{var} = {_list_lit(words)}\nprint(sorted({var}))"
            distractors = [
                str(sorted(words, key=str.lower)),
                str(sorted(words, key=lambda w: (w[0].isupper(), w))),
                str(sorted(words, reverse=True)),
                str(words),
                str(sorted(words, key=str.lower, reverse=True)),
                str(sorted(words, key=len)),
            ]
            why = (
                "Strings sort by character codes, and EVERY uppercase letter comes before every "
                f"lowercase one ('Z' < 'a'), so the capitalized words go first: {sorted(words)}."
            )
        else:
            code = f"{var} = {_list_lit(words)}\nprint(max({var}), min({var}))"
            ci_max, ci_min = max(words, key=str.lower), min(words, key=str.lower)
            longest = max(words, key=len)
            shortest = min(words, key=len)
            distractors = [
                f"{ci_max} {ci_min}", f"{longest} {shortest}", f"{min(words)} {max(words)}",
                f"{ci_min} {ci_max}",
            ]
            why = (
                "`max` and `min` compare strings alphabetically by character code (not by "
                "length), and uppercase letters come before lowercase ones, so "
                f"the max is {max(words)!r} and the min is {min(words)!r}."
            )
    elif shape == "numeric":
        for _ in range(50):
            nums = [rng.randint(2, 9), rng.randint(10, 99), rng.randint(10, 99), rng.randint(100, 999)]
            if len(set(nums)) == 4 and sorted(map(str, nums)) != [str(x) for x in sorted(nums)]:
                break
        rng.shuffle(nums)
        strs = [str(x) for x in nums]
        var = rng.choice(["scores", "codes", "levels"])
        code = f"{var} = {_list_lit(strs)}\nprint(sorted({var}))"
        distractors = [
            str([str(x) for x in sorted(nums)]),
            str(sorted(nums)),
            str(sorted(strs, reverse=True)),
            str(strs),
        ]
        x, y = next((p, q) for p in strs for q in strs if p < q and int(p) > int(q))
        why = (
            "These are strings, so they are compared character by character from the left, "
            f"not as numbers: {x!r} comes before {y!r} because {x[0]!r} < {y[0]!r}. "
            f"Sorted: {sorted(strs)}."
        )
    else:
        word = rng.choice(["Banana", "Hello", "Python", "Zebra", "Mango", "Tiger", "Pizza", "Llama", "Robot", "Kiwi"])
        code = f"word = {_lit(word)}\nprint(sorted(word))"
        distractors = [
            str(sorted(word, key=str.lower)),
            "".join(sorted(word)),
            str(sorted(set(word))),
            str(sorted(word, reverse=True)),
            str(sorted(word.lower())),
        ]
        why = (
            "`sorted()` on a string returns a LIST of its characters in order, and the "
            f"uppercase {word[0]!r} sorts before every lowercase letter."
        )
    return _output(code, HARD, distractors, why, rng)


_OVERLAP_TEXTS = [
    ("banana", "ana"), ("abababa", "aba"), ("aaaa", "aa"), ("aaaaa", "aa"),
    ("mississippi", "issi"), ("lalala", "lala"), ("nanana", "nana"), ("cocococo", "coco"),
    ("hahaha", "haha"), ("yoyoyo", "oyo"),
]
_FIND_ALL_TEXTS = _OVERLAP_TEXTS + [
    ("banana", "an"), ("mississippi", "ss"), ("hello yellow fellow", "ello"),
    ("tic tac toe", "t"), ("cocoa coconut", "co"), ("bookkeeper", "e"),
]


def _overlap_count(text: str, sub: str) -> int:
    return sum(1 for i in range(len(text)) if text.startswith(sub, i))


@generator(TOPIC, HARD)
def gen_find_occurrences(rng: random.Random) -> Question:
    """find(sub, start) loops and count()'s NON-overlapping matches."""
    var = rng.choice(["text", "s", "word"])
    if rng.random() < 0.5:
        text, sub = rng.choice(_FIND_ALL_TEXTS)
        jump = rng.choice(["1", f"len({_lit(sub)})"]) if len(sub) > 1 else "1"
        code = (
            f"{var} = {_lit(text)}\npositions = []\npos = {var}.find({_lit(sub)})\n"
            f"while pos != -1:\n    positions.append(pos)\n"
            f"    pos = {var}.find({_lit(sub)}, pos + {jump})\nprint(positions)"
        )
        overlapping = [i for i in range(len(text)) if text.startswith(sub, i)]
        non_overlap = []
        i = text.find(sub)
        while i != -1:
            non_overlap.append(i)
            i = text.find(sub, i + len(sub))
        correct = overlapping if jump == "1" else non_overlap
        other = non_overlap if jump == "1" else overlapping
        distractors = [
            str(other), str([p + 1 for p in correct]), str(correct + [-1]),
            str(correct[:1]), str([p + len(sub) - 1 for p in correct]),
        ]
        moved = "one character after the start of" if jump == "1" else "right after the end of"
        why = (
            f"Each pass records `pos`, then searches again starting {moved} the last match; "
            "when `find` returns -1 the loop stops (so -1 is never appended). "
            f"That finds {sub!r} at {correct}."
        )
        return _output(code, HARD, distractors, why, rng)
    text, sub = rng.choice(_OVERLAP_TEXTS)
    cnt, ov = text.count(sub), _overlap_count(text, sub)
    first, last = text.find(sub), text.rfind(sub)
    code = f"{var} = {_lit(text)}\nprint({var}.count({_lit(sub)}))\nprint({var}.find({_lit(sub)}), {var}.rfind({_lit(sub)}))"
    distractors = [
        f"{ov}\n{first} {last}", f"{cnt}\n{first} {last + len(sub) - 1}", f"{ov}\n{first + 1} {last + 1}",
        f"{cnt}\n{first} {first}", f"{cnt}\n{last} {first}",
    ]
    why = (
        f"`count` counts NON-overlapping matches: after a match it continues searching after the "
        f"end of it, so it finds {cnt} (counting overlaps would give {ov}). `find` returns where "
        f"the first match starts ({first}) and `rfind` where the last one starts ({last})."
    )
    return _output(code, HARD, distractors, why, rng)
