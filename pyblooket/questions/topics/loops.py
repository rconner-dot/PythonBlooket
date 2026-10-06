"""Question generators for the "loops" topic (Loops).

Covers ``range`` (start/stop/step, counting down, empty ranges), accumulator
loops, ``while`` loops with counters and with two variables, ``break`` and
``continue``, ``for``/``while`` ... ``else``, nested loops (iteration counts,
order, inner ranges that depend on the outer variable, ``break`` leaving only
the inner loop), ``enumerate``, looping over strings, the loop variable's value
after a loop, the loop header being evaluated only once, and the classic
off-by-one traps.
"""

from __future__ import annotations

import random

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
    error_choice,
    generator,
    int_distractors,
    output_question,
    run_code,
    which_expression_question,
)

TOPIC = "loops"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
FOREVER = "(the loop never ends)"
SYNTAX_ERROR = error_choice("SyntaxError")
BLANK = "____"


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
    lines = [line.rstrip() for line in choice.strip("\n").split("\n")]
    return (
        bool(choice.strip())
        and len(lines) <= MAX_CHOICE_LINES
        and all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines)
    )


def _usable(distractors) -> list[str]:
    """Drop distractors that would not fit on a choice button."""
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


def _seq(values, style: str) -> str:
    """Show a sequence the way a list print / ``end=" "`` loop / one-per-line loop would."""
    values = list(values)
    if style == "list":
        return str(values)
    sep = " " if style == "spaced" else "\n"
    return sep.join(str(v) for v in values)


def _nums(correct: int, cands, rng: random.Random, *, allow_negative: bool = False) -> list[str]:
    """Misconception-based numeric distractors first, then nearby integers."""
    out = [c for c in cands if c != correct and (allow_negative or c >= 0)]
    out += [c for c in map(int, int_distractors(correct, rng)) if allow_negative or c >= 0]
    return [str(c) for c in out]


def _strlist(items) -> str:
    """A list of strings written the way we'd type it (double quotes)."""
    return "[" + ", ".join(f'"{s}"' for s in items) + "]"


def _plus(values) -> str:
    return " + ".join(str(v) for v in values)


def _commas(values) -> str:
    return ", ".join(str(v) for v in values)


_LOOP_VARS = ["i", "n", "k", "x", "num"]
_MESSAGES = ['"Hi!"', '"Go!"', '"Python"', '"Loop!"', '"tick"', '"Hello"', '"Yay"']
_SHORT_WORDS = [
    "cat", "dog", "sun", "code", "loop", "jump", "frog", "star", "moon", "lime",
    "pixel", "tiger", "lemon", "mango", "orbit", "quest", "candy", "robot",
]
# Words with a repeated letter -> the letters worth counting in them.
_REPEAT_WORDS = {
    "banana": "an",
    "pepper": "pe",
    "coffee": "fe",
    "letter": "te",
    "balloon": "lo",
    "cherry": "r",
    "mississippi": "sip",
    "committee": "mte",
    "bookkeeper": "oek",
    "assessment": "se",
    "cocoa": "co",
    "tattoo": "to",
    "referee": "er",
}
# Words where "first occurrence", "last occurrence", "drop adjacent repeats" and
# "letters that appear once" all give different strings.
_DEDUPE_WORDS = [
    "banana", "letter", "mississippi", "bookkeeper", "assessment", "tattoo", "referee",
    "success", "grammar", "bubble", "parallel", "papaya", "tomato", "potato", "sassafras",
]
_DISTINCT_WORDS = [
    "python", "rocket", "tiger", "lemon", "mango", "orbit", "quest", "candy",
    "pixel", "snake", "planet", "dragon", "castle", "friend", "lucky", "magic",
]


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_range_values(rng: random.Random) -> Question:
    """Which numbers does range(stop) / range(start, stop) / range(start, stop, step) give?"""
    form = rng.choice(["stop", "start_stop", "start_stop", "step", "step"])
    if form == "stop":
        start, stop, step = 0, rng.randint(3, 6), 1
        args = str(stop)
    elif form == "start_stop":
        start = rng.randint(1, 6)
        stop = start + rng.randint(3, 5)
        step = 1
        args = f"{start}, {stop}"
    else:
        start = rng.randint(0, 5)
        step = rng.randint(2, 4)
        # Offset 0 makes the stop land exactly on a step: very tempting to include it.
        stop = start + step * rng.randint(3, 4) + rng.choice([0, 0, 1])
        args = f"{start}, {stop}, {step}"
    values = list(range(start, stop, step))
    style = rng.choice(["list", "spaced", "lines"] if len(values) <= 5 else ["list", "spaced"])
    v = rng.choice(_LOOP_VARS)
    if style == "list":
        code = f"print(list(range({args})))"
    elif style == "spaced":
        code = f'for {v} in range({args}):\n    print({v}, end=" ")'
    else:
        code = f"for {v} in range({args}):\n    print({v})"
    one_more = values + [values[-1] + step]
    if form == "stop":
        wrong = [range(1, stop + 1), one_more, range(1, stop), values[:-1]]
        why = (
            f"`range({stop})` starts at 0 and stops just *before* {stop}, so it gives "
            f"{stop} numbers: 0 up to {stop - 1}."
        )
    elif form == "start_stop":
        wrong = [one_more, range(start + 1, stop + 1), range(start + 1, stop), values[:-1]]
        why = (
            f"`range({args})` includes the start value {start} but stops just *before* "
            f"{stop}, so the last number is {stop - 1}."
        )
    else:
        wrong = [one_more, values[:-1], values[1:], range(start + step, stop + 1, step), range(start, stop)]
        why = (
            f"`range({args})` starts at {start} and adds {step} while the value is still "
            f"below {stop}. The stop value is never included, so the last number is {values[-1]}."
        )
    return _output(code, EASY, [_seq(w, style) for w in wrong], why, rng)


@generator(TOPIC, EASY)
def gen_count_printed_lines(rng: random.Random) -> Question:
    """How many times does the loop body run? (range forms, strings, indentation)."""
    msg = rng.choice(_MESSAGES)
    v = rng.choice(["i", "n", "k", "x"])
    shape = rng.choice(["stop", "start_stop", "step", "string", "indent", "indent"])
    if shape == "stop":
        n = rng.randint(3, 9)
        code = f"for {v} in range({n}):\n    print({msg})"
        answer, cands = n, [n + 1, n - 1, 1]
        why = f"`range({n})` produces {n} values (0 up to {n - 1}), so the loop body runs {n} times."
    elif shape == "start_stop":
        a = rng.randint(2, 6)
        b = a + rng.randint(3, 7)
        code = f"for {v} in range({a}, {b}):\n    print({msg})"
        answer, cands = b - a, [b - a + 1, b, b - a - 1]
        why = (
            f"`range({a}, {b})` gives the numbers {a} up to {b - 1}: that is "
            f"{b} - {a} = {b - a} values, so the body runs {b - a} times."
        )
    elif shape == "step":
        a = rng.randint(0, 3)
        step = rng.randint(2, 3)
        b = a + step * rng.randint(3, 5) + rng.randint(0, step - 1)
        values = list(range(a, b, step))
        code = f"for {v} in range({a}, {b}, {step}):\n    print({msg})"
        answer = len(values)
        cands = [answer + 1, b - a, answer - 1, (b - a) // step]
        why = (
            f"`range({a}, {b}, {step})` gives {_commas(values)} ({answer} values), "
            f"so the body runs {answer} times."
        )
    elif shape == "string":
        word = rng.choice(WORDS)
        code = f'for ch in "{word}":\n    print({msg})'
        answer, cands = len(word), [1, len(word) - 1, len(word) + 1]
        why = (
            f'A `for` loop over a string runs once per character, and "{word}" has '
            f"{len(word)} characters."
        )
    else:
        n = rng.randint(2, 5)
        inside = rng.random() < 0.5
        last = '    print("Done")' if inside else 'print("Done")'
        code = f"for {v} in range({n}):\n    print({msg})\n{last}"
        if inside:
            answer, cands = 2 * n, [n + 1, n, 2 * n + 1]
            why = (
                f"Both `print` lines are indented, so both are inside the loop and run on "
                f"each of the {n} passes: 2 × {n} = {2 * n} lines."
            )
        else:
            answer, cands = n + 1, [2 * n, n, n + 2]
            why = (
                f'Only the indented line is inside the loop, so it prints {n} times. '
                f'`print("Done")` is not indented, so it runs once after the loop: {n} + 1 = {n + 1}.'
            )
    res = run_code(code)
    printed = len(res.output.split("\n")) if res.output else 0
    if res.error or printed != answer:
        raise GenerationError(f"line count mismatch for {code!r}")
    return _choice(
        difficulty=EASY,
        prompt="How many lines does this code print?",
        code=code,
        correct=str(answer),
        distractors=_nums(answer, cands, rng),
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_accumulator(rng: random.Random) -> Question:
    """Running total / product / repeated add / doubling / string building."""
    v = rng.choice(["i", "n", "k"])
    acc = rng.choice(["total", "result", "acc", "answer"])
    shape = rng.choice(["sum", "product", "repeat", "double", "concat"])
    if shape == "sum":
        a = rng.randint(1, 3)
        b = a + rng.randint(3, 5)
        values = list(range(a, b))
        s = sum(values)
        code = f"{acc} = 0\nfor {v} in range({a}, {b}):\n    {acc} += {v}\nprint({acc})"
        distractors = _nums(s, [s + b, s - values[-1], len(values), b - 1], rng)
        why = (
            f"The loop adds {_commas(values)} (it stops before {b}), so `{acc}` ends at "
            f"{_plus(values)} = {s}."
        )
    elif shape == "product":
        b = rng.randint(4, 6)
        values = list(range(1, b))
        p = 1
        for x in values:
            p *= x
        code = f"{acc} = 1\nfor {v} in range(1, {b}):\n    {acc} *= {v}\nprint({acc})"
        distractors = _nums(p, [p * b, p // values[-1], sum(values), 0], rng)
        why = (
            f"`{acc}` starts at 1 and is multiplied by {_commas(values)} in turn "
            f"(the range stops before {b}): {' * '.join(map(str, values))} = {p}."
        )
    elif shape == "repeat":
        start = rng.randint(1, 9)
        step = rng.randint(2, 5)
        k = rng.randint(3, 5)
        ans = start + k * step
        code = f"{acc} = {start}\nfor {v} in range({k}):\n    {acc} += {step}\nprint({acc})"
        distractors = _nums(
            ans, [start + (k - 1) * step, start + (k + 1) * step, k * step, start + step], rng
        )
        why = (
            f"`range({k})` makes the body run {k} times and each pass adds {step}: "
            f"{start} + {k} × {step} = {ans}."
        )
    elif shape == "double":
        start = rng.randint(1, 3)
        k = rng.randint(3, 5)
        ans = start * 2**k
        code = f"{acc} = {start}\nfor {v} in range({k}):\n    {acc} *= 2\nprint({acc})"
        distractors = _nums(
            ans, [start * 2 ** (k - 1), start * 2 * k, start * 2 ** (k + 1), start + 2 * k], rng
        )
        chain = " → ".join(str(start * 2**j) for j in range(k + 1))
        why = f"The body runs {k} times and each pass doubles `{acc}`: {chain}."
    else:
        s_name = rng.choice(["s", "text", "digits", "out"])
        n = rng.randint(3, 6)
        ans = "".join(str(i) for i in range(n))
        code = f'{s_name} = ""\nfor {v} in range({n}):\n    {s_name} += str({v})\nprint({s_name})'
        distractors = [
            "".join(str(i) for i in range(1, n + 1)),
            "".join(str(i) for i in range(n + 1)),
            str(sum(range(n))),
            " ".join(str(i) for i in range(n)),
        ]
        why = (
            f"`+=` on a string glues the new text onto the end, and `range({n})` gives "
            f"0 up to {n - 1}, so `{s_name}` grows to \"{ans}\"."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_string_loop(rng: random.Random) -> Question:
    """Looping over the characters of a string: end=, counting, filtering."""
    shape = rng.choice(["sep", "count", "filter"])
    c = rng.choice(["ch", "letter", "c"])
    if shape == "sep":
        word = rng.choice(_SHORT_WORDS)
        sep = rng.choice(["-", "*", ".", "|"])
        code = f'for {c} in "{word}":\n    print({c}, end="{sep}")'
        distractors = [sep.join(word), sep + sep.join(word), word + sep, "\n".join(word), word]
        why = (
            f'`end="{sep}"` replaces the usual newline, so "{sep}" is printed after *every* '
            f"character, including the last one."
        )
    elif shape == "count":
        word = rng.choice(list(_REPEAT_WORDS))
        t = rng.choice(_REPEAT_WORDS[word])
        ans = word.count(t)
        code = (
            f'count = 0\nfor {c} in "{word}":\n    if {c} == "{t}":\n'
            f"        count += 1\nprint(count)"
        )
        distractors = _nums(ans, [ans - 1, ans + 1, len(word), word.index(t)], rng)
        why = (
            f'The loop checks each of the {len(word)} characters and adds 1 whenever it is '
            f'"{t}". "{word}" contains {ans} of them.'
        )
    else:
        word = rng.choice([w for w in WORDS + _DISTINCT_WORDS if len(w) >= 4])
        keep_vowels = rng.random() < 0.5
        op = "in" if keep_vowels else "not in"
        kept = "".join(ch for ch in word if (ch in "aeiou") == keep_vowels)
        other = "".join(ch for ch in word if (ch in "aeiou") != keep_vowels)
        code = f'for {c} in "{word}":\n    if {c} {op} "aeiou":\n        print({c}, end="")'
        distractors = [other, word, "\n".join(kept), kept[::-1], kept[:-1]]
        what = "vowels" if keep_vowels else "consonants"
        why = (
            f'`{c} {op} "aeiou"` is True only for the {what}, so only "{kept}" is printed; '
            f'`end=""` keeps the letters together on one line.'
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_while_basics(rng: random.Random) -> Question:
    """Countdown with a while loop, or the value that finally stops the loop."""
    name = rng.choice(["n", "count", "x", "num"])
    shape = rng.choice(["countdown", "countdown", "double", "add"])
    if shape == "countdown":
        k = rng.randint(3, 5)
        cond, low = rng.choice([(f"{name} > 0", 1), (f"{name} >= 1", 1), (f"{name} >= 0", 0), (f"{name} > 1", 2)])
        code = f"{name} = {k}\nwhile {cond}:\n    print({name})\n    {name} -= 1"
        wrong = [range(k, -1, -1), range(k, 0, -1), range(k, 1, -1), range(k - 1, low - 2, -1), range(k - 1, low - 1, -1)]
        distractors = [_seq(w, "lines") for w in wrong] + [_seq(range(k, low - 1, -1), "spaced")]
        why = (
            f"The condition is checked before every pass. `{name}` is printed while `{cond}` "
            f"is true, so {low} is the last value printed; at {low - 1} the loop stops."
        )
    elif shape == "double":
        start = rng.randint(1, 3)
        powers = [start * 2**j for j in range(7)]
        limit = rng.choice([p for p in range(start * 4 + 1, start * 32) if p not in powers])
        ans = next(p for p in powers if p >= limit)
        code = f"{name} = {start}\nwhile {name} < {limit}:\n    {name} *= 2\nprint({name})"
        distractors = _nums(ans, [ans // 2, limit, ans * 2, limit - 1], rng)
        chain = " → ".join(str(p) for p in powers if p <= ans)
        why = (
            f"The loop doubles `{name}` while it is below {limit}: {chain}. The last doubling "
            f"pushes it past {limit}, the condition becomes false, and {ans} is printed."
        )
    else:
        step = rng.randint(2, 5)
        limit = rng.randint(8, 25)
        ans = -(-limit // step) * step
        code = f"{name} = 0\nwhile {name} < {limit}:\n    {name} += {step}\nprint({name})"
        distractors = _nums(ans, [ans - step, limit, ans + step, limit - 1], rng)
        why = (
            f"`{name}` grows by {step} while it is below {limit}. At {ans - step} the condition "
            f"is still true, so it adds {step} once more to reach {ans}, and then the loop stops."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_break_or_continue(rng: random.Random) -> Question:
    """A simple loop over a list where one condition triggers break or continue."""
    keyword = rng.choice(["break", "continue"])
    size = rng.randint(4, 5)
    idx = rng.randint(1, size - 2)
    kind = rng.choice(["names", "equal", "greater", "even"])
    if kind == "names":
        lst, v = rng.choice([("names", "name"), ("friends", "friend"), ("players", "player")])
        items = rng.sample(NAMES, size)
        cond = f'{v} == "{items[idx]}"'
        literal = _strlist(items)
    else:
        lst, v = rng.choice([("nums", "n"), ("values", "x"), ("scores", "score")])
        if kind == "equal":
            items = rng.sample(range(1, 20), size)
            cond = f"{v} == {items[idx]}"
        elif kind == "greater":
            t = rng.randint(5, 12)
            small = rng.sample(range(1, t + 1), size)
            big = rng.sample(range(t + 1, t + 10), size)
            items = [small[i] if i < idx or i == size - 1 or rng.random() < 0.5 else big[i] for i in range(size)]
            items[idx] = big[idx]
            cond = f"{v} > {t}"
        else:
            odd = rng.sample(range(1, 20, 2), size)
            even = rng.sample(range(2, 21, 2), size)
            items = [odd[i] if i < idx or i == size - 1 or rng.random() < 0.5 else even[i] for i in range(size)]
            items[idx] = even[idx]
            cond = f"{v} % 2 == 0"
        literal = str(items)
    code = f"{lst} = {literal}\nfor {v} in {lst}:\n    if {cond}:\n        {keyword}\n    print({v})"
    hits = [run_code(f"{v} = {x!r}\nhit = {cond}").namespace["hit"] for x in items]
    first = hits.index(True)
    stopped = items[:first]
    skipped = [x for x, h in zip(items, hits) if not h]
    matches = [x for x, h in zip(items, hits) if h]
    with_trigger = items[: first + 1]
    if keyword == "break":
        wrong = [with_trigger, skipped, items, matches]
        why = (
            f"`break` ends the whole loop the first time `{cond}` is true (at {items[first]}), "
            f"so only the items before it are printed."
        )
    else:
        wrong = [stopped, items, matches, with_trigger]
        why = (
            f"`continue` skips the rest of the body for that one item, then the loop carries "
            f"on, so every item except those where `{cond}` is true gets printed."
        )
    return _output(code, EASY, [_seq(w, "lines") for w in wrong], why, rng)


# ==========================================================================
# MEDIUM
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_counting_down(rng: random.Random) -> Question:
    """range with a negative step, and range(big, small) being empty."""
    shape = rng.choice(["list", "loop", "empty", "which"])
    start = rng.randint(6, 15)
    step = rng.choice([1, 2, 2, 3, 3, 4])
    count = rng.randint(3, 5 if step > 1 else 4)
    stop = start - step * count + rng.choice([0, 0, -1])
    values = list(range(start, stop, -step))
    last = values[-1]
    neg = f"-{step}"
    if shape == "which":
        correct = f"list(range({start}, {stop}, {neg}))"
        up = "" if step == 1 else f", {step}"
        wrong = [
            f"list(range({start}, {last}, {neg}))",
            f"list(range({last}, {start + 1}{up}))",
            f"list(range({start}, {stop}{up}))",
            f"list(range({start - 1}, {stop}, {neg}))",
            f"list(range({start}, {stop - step}, {neg}))",
        ]
        return which_expression_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=f"Which expression evaluates to `{values}`?",
            setup="",
            target=values,
            correct_expr=correct,
            wrong_exprs=wrong,
            explanation=(
                f"A negative step counts down from {start}, and the stop value {stop} is "
                f"excluded, so the last value is {last}. `range({last}, {start + 1}{up})` "
                f"has the same numbers but in increasing order."
            ),
            rng=rng,
        )
    v = rng.choice(_LOOP_VARS)
    if shape == "empty":
        stop = rng.randint(0, start - 4)
        args = f"{start}, {stop}"
        wrong = [range(start, stop, -1), range(start, stop - 1, -1), range(stop, start), range(stop, start + 1)]
        why = (
            f"Without a step, `range` counts *up* by 1. It starts at {start}, which is "
            f"already past {stop}, so the range is empty. Counting down needs a negative "
            f"step: `range({start}, {stop}, -1)`."
        )
    else:
        args = f"{start}, {stop}, {neg}"
        wrong = [
            values + [last - step],
            values[:-1],
            list(range(last, start + 1, step)),
            [],
            list(range(start - 1, stop, -step)),
        ]
        why = (
            f"With step {neg}, `range` counts *down* from {start} and stops before reaching "
            f"{stop} (the stop is excluded just like when counting up), so the last value is {last}."
        )
    if shape == "loop":
        code = f'for {v} in range({args}):\n    print({v}, end=" ")'
        style = "spaced"
    else:
        code = f"print(list(range({args})))"
        style = "list"
    return _output(code, MEDIUM, [_seq(w, style) for w in wrong], why, rng)


@generator(TOPIC, MEDIUM)
def gen_loop_variable_after(rng: random.Random) -> Question:
    """What value does the loop variable hold once the loop is over (for vs while)?"""
    shape = rng.choice(["total", "step", "contrast"])
    v = rng.choice(["i", "n", "k"])
    if shape == "total":
        n = rng.randint(4, 8)
        start = rng.choice([0, 1])
        args = str(n) if start == 0 else f"1, {n}"
        values = list(range(start, n))
        s = sum(values)
        last = n - 1
        code = f"total = 0\nfor {v} in range({args}):\n    total += {v}\nprint({v}, total)"
        distractors = [
            f"{n} {s}", f"{n} {s + n}", f"{last - 1} {s - last}", f"{last} {s - last}", f"{last} {s + n}",
        ]
        why = (
            f"After a `for` loop, `{v}` keeps the *last* value the range gave it, {last} — it "
            f"never becomes the stop value {n}. The total is {_plus(values)} = {s}."
        )
    elif shape == "step":
        a = rng.randint(0, 5)
        step = rng.randint(2, 4)
        stop = a + step * rng.randint(3, 4) + rng.randint(0, step - 1)
        values = list(range(a, stop, step))
        c, last = len(values), values[-1]
        code = f"count = 0\nfor {v} in range({a}, {stop}, {step}):\n    count += 1\nprint(count, {v})"
        distractors = [
            f"{c} {stop}", f"{c} {last + step}", f"{c + 1} {last + step}", f"{c - 1} {last}", f"{c + 1} {stop}",
        ]
        why = (
            f"The range gives {_commas(values)} ({c} values). When the loop ends, `{v}` still "
            f"holds the last of them, {last}; it never takes the value {last + step}."
        )
    else:
        n = rng.randint(3, 7)
        code = (
            f"steps = 0\nfor i in range({n}):\n    steps += 1\n"
            f"j = 0\nwhile j < {n}:\n    j += 1\nprint(i, j, steps)"
        )
        distractors = [
            f"{n} {n} {n}", f"{n - 1} {n - 1} {n}", f"{n} {n - 1} {n}", f"{n - 1} {n} {n - 1}",
        ]
        why = (
            f"The `for` loop hands `i` the values 0 to {n - 1} and then stops, leaving `i` at "
            f"{n - 1}. The `while` loop only stops once `j < {n}` is false, i.e. after `j` "
            f"has been raised to {n}. Both loops ran {n} times."
        )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_enumerate(rng: random.Random) -> Question:
    """enumerate: index/value pairs, the start argument, tuples, weighted sums."""
    shape = rng.choice(["pairs", "tuple", "find", "weighted"])
    if shape in ("pairs", "tuple"):
        lst, item = rng.choice([("items", "item"), ("tools", "tool"), ("pets", "pet"), ("words", "word")])
        pool = {
            "items": ["pen", "cup", "map", "hat", "key", "box"],
            "tools": ["saw", "drill", "file", "tape", "rope"],
            "pets": ["cat", "dog", "fish", "bird", "frog"],
            "words": ["red", "blue", "gold", "pink", "teal"],
        }[lst]
        if shape == "pairs":
            things = rng.sample(pool, 3)
            start = rng.choice([0, 1, 1])
            enum = f"enumerate({lst})" if start == 0 else rng.choice(
                [f"enumerate({lst}, 1)", f"enumerate({lst}, start=1)"]
            )
            code = f"{lst} = {_strlist(things)}\nfor i, {item} in {enum}:\n    print(i, {item})"
            other = 1 - start
            distractors = [
                "\n".join(f"{i} {t}" for i, t in enumerate(things, other)),
                "\n".join(f"{t} {i}" for i, t in enumerate(things, start)),
                "\n".join(f"({i}, '{t}')" for i, t in enumerate(things, start)),
                "\n".join(f"{i} {t}" for i, t in enumerate(things, start + 2)),
            ]
            why = (
                f"`enumerate` produces (index, item) pairs with the index counting from {start}"
                + (" (the default)" if start == 0 else " because of the start argument")
                + f"; unpacking into `i, {item}` lets `print` show them separated by a space."
            )
        else:
            things = rng.sample(pool, rng.choice([2, 3]))
            code = f"{lst} = {_strlist(things)}\nfor pair in enumerate({lst}):\n    print(pair)"
            distractors = [
                "\n".join(f"{i} {t}" for i, t in enumerate(things)),
                "\n".join(f"({i}, {t})" for i, t in enumerate(things)),
                "\n".join(f"('{t}', {i})" for i, t in enumerate(things)),
                "\n".join(f"({i}, '{t}')" for i, t in enumerate(things, 1)),
            ]
            why = (
                "Without unpacking, each item from `enumerate` is one tuple `(index, value)`, "
                "and printing a tuple shows its repr: parentheses, a comma and quotes around strings."
            )
        return _output(code, MEDIUM, distractors, why, rng)
    if shape == "find":
        word = rng.choice([w for w, letters in _REPEAT_WORDS.items() if len(w) <= 8])
        t = rng.choice([ch for ch in _REPEAT_WORDS[word] if 2 <= word.count(ch) <= 3])
        start = rng.choice([0, 1])
        brk = rng.random() < 0.5
        enum = f'enumerate("{word}")' if start == 0 else f'enumerate("{word}", start=1)'
        code = f'for i, ch in {enum}:\n    if ch == "{t}":\n        print(i)'
        if brk:
            code += "\n        break"
        pos = [i for i, ch in enumerate(word, start) if ch == t]
        shifted = [p + (1 if start == 0 else -1) for p in pos]
        if brk:
            distractors = [str(shifted[0]), "\n".join(map(str, pos)), str(pos[-1]), str(len(pos))]
            distractors += _nums(pos[0], [pos[0] + 2, pos[0] - 2], rng)
            why = (
                f'Counting from {start}, the first "{t}" in "{word}" is at index {pos[0]}. '
                f"`break` stops the loop right after printing it."
            )
        else:
            distractors = ["\n".join(map(str, shifted)), str(pos[0]), str(shifted[0]), str(len(pos))]
            why = (
                f'With no `break`, the loop prints the index of *every* "{t}" in "{word}", '
                f"counting from {start}: {_commas(pos)}."
            )
        return _output(code, MEDIUM, distractors, why, rng)
    nums = rng.sample(range(1, 10), 4)
    start = rng.choice([0, 1])
    enum = "enumerate(nums)" if start == 0 else "enumerate(nums, 1)"
    code = f"nums = {nums}\ntotal = 0\nfor i, n in {enum}:\n    total += i * n\nprint(total)"
    ans = sum(i * n for i, n in enumerate(nums, start))
    other = sum(i * n for i, n in enumerate(nums, 1 - start))
    terms = " + ".join(f"{i}*{n}" for i, n in enumerate(nums, start))
    distractors = _nums(ans, [other, sum(nums), sum(range(start, start + 4)), ans + nums[-1]], rng)
    why = (
        f"`enumerate` pairs each value with its index, counting from {start}, so the total "
        f"is {terms} = {ans}."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_nested_loops(rng: random.Random) -> Question:
    """Nested loops: total iterations, which loop varies fastest, triangle patterns."""
    shape = rng.choice(["count", "order", "order", "triangle"])
    if shape == "count":
        a = rng.randint(3, 5)
        b = rng.randint(2, 5)
        outer_args, outer_n, outer_stop = rng.choice([(str(a), a, a), (f"1, {a}", a - 1, a)])
        inner_args, inner_n, inner_stop = rng.choice(
            [(str(b), b, b), (f"1, {b + 1}", b, b + 1), (f"1, {b}", b - 1, b)]
        )
        if inner_n < 2:
            inner_args, inner_n, inner_stop = str(b + 1), b + 1, b + 1
        ans = outer_n * inner_n
        code = (
            f"count = 0\nfor i in range({outer_args}):\n    for j in range({inner_args}):\n"
            f"        count += 1\nprint(count)"
        )
        distractors = _nums(
            ans,
            [
                outer_stop * inner_stop,  # read each stop value as the number of passes
                outer_n + inner_n,  # added instead of multiplied
                (outer_n + 1) * inner_n,
                outer_n * (inner_n + 1),
                (outer_n - 1) * inner_n,
                ans + outer_n,
            ],
            rng,
        )
        why = (
            f"The inner loop runs {inner_n} times for *each* of the {outer_n} passes of the "
            f"outer loop: {outer_n} × {inner_n} = {ans}."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    if shape == "order":
        r = rng.randint(2, 3)
        letters = rng.choice(["ab", "xy", "AB", "XO", "pq"])
        o, c = rng.choice([("i", "ch"), ("n", "letter"), ("row", "col")])
        start = rng.choice([0, 1])
        args = str(r) if start == 0 else f"1, {r + 1}"
        outer = list(range(start, start + r))
        code = f'for {o} in range({args}):\n    for {c} in "{letters}":\n        print({o}, {c})'

        def show(pairs):
            return "\n".join(f"{x} {y}" for x, y in pairs)

        distractors = [
            show((x, y) for y in letters for x in outer),
            show(zip(outer, letters)),
            show((outer[0], y) for y in letters),
            show((x, letters[0]) for x in outer),
        ]
        why = (
            f"The inner loop runs *completely* for each value of the outer variable: with "
            f"`{o}` = {outer[0]} it prints both letters, then `{o}` becomes {outer[1]} and the "
            f"inner loop starts over from \"{letters[0]}\"."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    n = rng.randint(3, 5)
    item = rng.choice(['"*"', '"#"', "j"])
    inner = rng.choice(["i + 1", f"{n} - i"])

    def tri(inner_expr: str, item_expr: str) -> str:
        return (
            f"for i in range({n}):\n    for j in range({inner_expr}):\n"
            f'        print({item_expr}, end="")\n    print()'
        )

    code = tri(inner, item)
    alts = [tri(x, item) for x in ["i + 1", f"{n} - i", str(n), "i + 2"] if x != inner]
    if item == "j":
        alts.append(tri(inner, "j + 1"))
        alts.append(tri(inner, "i"))
    distractors = [_run(a) for a in alts]
    rows = "1, 2, 3 …" if inner == "i + 1" else f"{n}, {n - 1}, {n - 2} …"
    why = (
        f"For each `i`, the inner loop runs `range({inner})` times, so the rows have "
        f"{rows} items; `end=\"\"` keeps a row together and the bare `print()` ends it."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_continue_accumulate(rng: random.Random) -> Question:
    """Accumulating with continue skipping some items (vs break / no skip)."""
    shape = rng.choice(["mod", "mod", "negatives", "letters"])
    if shape == "mod":
        m = rng.choice([2, 3, 3, 4])
        k = rng.randint(m + 3, 10)
        inclusive = rng.random() < 0.5
        args = f"1, {k + 1}" if inclusive else f"1, {k}"
        vals = list(range(1, k + 1 if inclusive else k))
        v = rng.choice(["n", "i", "x"])
        code = (
            f"total = 0\nfor {v} in range({args}):\n    if {v} % {m} == 0:\n        continue\n"
            f"    total += {v}\nprint(total)"
        )
        kept = [x for x in vals if x % m]
        skipped = [x for x in vals if x % m == 0]
        ans = sum(kept)
        before = sum(range(1, m))
        cands = [before, sum(vals), sum(skipped), ans - kept[-1], ans + vals[-1] + 1]
        why = (
            f"`continue` jumps straight to the next number, skipping `total += {v}` for "
            f"{_commas(skipped)}. The loop keeps going, so total = {_plus(kept)} = {ans}."
        )
    elif shape == "negatives":
        size = 5
        nums = [rng.randint(1, 9) for _ in range(size)]
        neg_pos = rng.sample(range(1, size), 2)
        for p in neg_pos:
            nums[p] = -rng.randint(1, 9)
        code = (
            f"total = 0\nfor n in {nums}:\n    if n < 0:\n        continue\n"
            f"    total += n\nprint(total)"
        )
        kept = [x for x in nums if x >= 0]
        ans = sum(kept)
        first_neg = min(neg_pos)
        cands = [sum(nums[:first_neg]), sum(nums), sum(abs(x) for x in nums), sum(x for x in nums if x < 0)]
        why = (
            f"`continue` skips only the negative numbers and the loop carries on, so "
            f"total = {_plus(kept)} = {ans}."
        )
    else:
        word = rng.choice([w for w in WORDS + _DISTINCT_WORDS if 5 <= len(w) <= 7])
        vowels = [ch for ch in word if ch in "aeiou"]
        ans = len(word) - len(vowels)
        first_vowel = next(i for i, ch in enumerate(word) if ch in "aeiou")
        code = (
            f'count = 0\nfor ch in "{word}":\n    if ch in "aeiou":\n        continue\n'
            f"    count += 1\nprint(count)"
        )
        cands = [len(vowels), len(word), first_vowel, ans - 1]
        why = (
            f'`continue` skips `count += 1` for each vowel ({_commas(vowels)}), so only the '
            f'{ans} consonants of "{word}" are counted.'
        )
    return _output(code, MEDIUM, _nums(ans, cands, rng, allow_negative=True), why, rng)


@generator(TOPIC, MEDIUM)
def gen_digit_while(rng: random.Random) -> Question:
    """while n > 0 with % 10 and // 10 or // 2: digit sums, digit counts, halving."""
    shape = rng.choice(["digit_sum", "count_digits", "halve"])
    if shape == "digit_sum":
        num = rng.randint(102, 9876)
        digits = [int(d) for d in str(num)]
        s = sum(digits)
        code = (
            f"n = {num}\ntotal = 0\nwhile n > 0:\n    total += n % 10\n    n //= 10\n"
            f"print(total, n)"
        )
        distractors = [
            f"{s} {digits[0]}", f"{s - digits[0]} {digits[0]}", f"{s} {num}",
            f"{s - digits[-1]} 0", f"{len(digits)} 0",
        ]
        why = (
            f"Each pass adds the last digit (`n % 10`) and then chops it off (`n //= 10`). "
            f"The loop only stops when `n` reaches 0, so every digit is added: "
            f"{_plus(digits)} = {s}."
        )
    elif shape == "count_digits":
        k = rng.randint(2, 5)
        num = rng.randint(10 ** (k - 1), 10**k - 1)
        first = int(str(num)[0])
        cond = rng.choice(["n > 0", "n >= 1", "n >= 10", "n > 9"])
        code = f"n = {num}\ncount = 0\nwhile {cond}:\n    n //= 10\n    count += 1\nprint(count, n)"
        distractors = [f"{k} 0", f"{k - 1} {first}", f"{k} {first}", f"{k - 1} 0", f"{k + 1} 0"]
        if cond in ("n > 0", "n >= 1"):
            why = (
                f"Each `n //= 10` removes one digit. The loop keeps going until `n` is 0, so "
                f"it runs once per digit: {k} times."
            )
        else:
            why = (
                f"Each `n //= 10` removes one digit, but `{cond}` is false as soon as `n` is a "
                f"single digit, so the loop stops at {first} after {k - 1} passes."
            )
    else:
        num = rng.randint(10, 80)
        cond = rng.choice(["n > 1", "n > 1", "n > 0"])
        code = f"n = {num}\nsteps = 0\nwhile {cond}:\n    n //= 2\n    steps += 1\nprint(steps, n)"
        chain = [num]
        while chain[-1] > 1:
            chain.append(chain[-1] // 2)
        s = len(chain) - 1
        if cond == "n > 0":
            chain.append(0)
            s += 1
        final = chain[-1]
        distractors = [
            f"{s + 1} {0 if final else 1}", f"{s - 1} {chain[-2]}", f"{s} {1 - final}",
            f"{s + 1} {final}", f"{num // 2} {final}",
        ]
        why = (
            f"Tracing `n`: {' → '.join(map(str, chain))}. That is {s} halvings; the loop "
            f"stops once `{cond}` is false, which happens when `n` is {final}."
        )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_off_by_one_blank(rng: random.Random) -> Question:
    """Which range(...) / while condition completes the loop to print exactly the target?"""
    shape = rng.choice(["up", "down", "while"])
    v = rng.choice(["i", "n", "k"])
    if shape == "while":
        start = rng.randint(0, 3)
        step = rng.choice([1, 1, 2, 3])
        count = rng.randint(3, 5)
        last = start + step * (count - 1)
        target = list(range(start, last + 1, step))
        code = f'{v} = {start}\nwhile {BLANK}:\n    print({v}, end=" ")\n    {v} += {step}'
        correct = rng.choice([f"{v} <= {last}", f"{v} < {last + 1}"])
        # All candidates are upper bounds on an increasing variable, so every one terminates.
        wrong = [
            f"{v} < {last}", f"{v} <= {last + step}", f"{v} > {last}", f"{v} <= {last - 1}",
            f"{v} < {last + step + 1}",
        ]
        why = (
            f"The body runs while the condition is true. `{correct}` is still true when `{v}` "
            f"is {last} and false once it becomes {last + step}, so {last} is the last value "
            f"printed. `{v} < {last}` would stop one value too early."
        )
    elif shape == "up":
        start = rng.randint(0, 5)
        step = rng.choice([1, 2, 2, 3, 5])
        count = rng.randint(3, 5)
        last = start + step * (count - 1)
        target = list(range(start, last + 1, step))
        st = "" if step == 1 else f", {step}"
        code = f'for {v} in {BLANK}:\n    print({v}, end=" ")'
        correct = f"range({start}, {last + 1}{st})"
        wrong = [
            f"range({start}, {last}{st})",
            f"range({start}, {last + step + 1}{st})",
            f"range({start + 1}, {last + 1}{st})" if step > 1 else f"range({start - 1}, {last}{st})",
            f"range({start}, {last + 1})" if step > 1 else f"range({start + 1}, {last + 2})",
            f"range({last + 1})",
        ]
        why = (
            f"`{correct}` starts at {start} and stops *before* {last + 1}, so {last} is the "
            f"last value printed. Using {last} as the stop would leave {last} out."
        )
    else:
        start = rng.randint(5, 12)
        count = rng.randint(3, 5)
        step = rng.choice([s for s in (1, 1, 2, 3) if start - s * (count - 1) >= 0])
        last = start - step * (count - 1)
        target = list(range(start, last - 1, -step))
        code = f'for {v} in {BLANK}:\n    print({v}, end=" ")'
        correct = f"range({start}, {last - 1}, -{step})"
        up = "" if step == 1 else f", {step}"
        wrong = [
            f"range({start}, {last}, -{step})",
            f"range({last}, {start + 1}{up})",
            f"range({start}, {last - 1})",
            f"range({start + 1}, {last}, -{step})",
            f"range({start}, {last - 1}, {step})",
        ]
        why = (
            f"To count down you need a negative step, and the stop must be one *past* the "
            f"last value you want: `{correct}` stops before {last - 1}, so {last} is printed last."
        )
    want = " ".join(map(str, target))

    def prints(choice: str) -> str:
        res = run_code(code.replace(BLANK, choice))
        return "ERR" if res.error else res.output.rstrip()

    if prints(correct) != want:
        raise GenerationError(f"{correct!r} does not print {want!r}")
    distractors = [w for w in wrong if prints(w) != want]
    return _choice(
        difficulty=MEDIUM,
        prompt=f"Which choice fills the blank so the code prints `{want}`?",
        code=code,
        correct=correct,
        distractors=distractors,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_two_variable_while(rng: random.Random) -> Question:
    """A while loop whose condition compares two variables that both change."""
    a, b = rng.choice([("low", "high"), ("a", "b"), ("left", "right"), ("x", "y")])
    with_steps = rng.random() < 0.4
    for _ in range(100):
        mult = rng.random() < 0.3
        x0 = rng.randint(1, 3) if mult else rng.randint(0, 4)
        sx = 2 if mult else rng.randint(2, 4)
        y0 = rng.randint(10, 24)
        sy = rng.randint(1, 3)

        def step_x(x):
            return x * sx if mult else x + sx

        states = [(x0, y0)]
        while states[-1][0] < states[-1][1]:
            x, y = states[-1]
            states.append((step_x(x), y - sy))
        if 3 <= len(states) - 1 <= 4:
            break
    else:
        raise GenerationError("no suitable two-variable loop")
    op_x = f"{a} *= {sx}" if mult else f"{a} += {sx}"
    lines = [f"{a}, {b} = {x0}, {y0}"]
    if with_steps:
        lines.append("steps = 0")
    lines += [f"while {a} < {b}:", f"    {op_x}", f"    {b} -= {sy}"]
    if with_steps:
        lines.append("    steps += 1")
        lines.append(f"print(steps, {a}, {b})")
    else:
        lines.append(f"print({a}, {b})")
    code = "\n".join(lines)
    n = len(states) - 1
    x, y = states[-1]
    more = (step_x(x), y - sy)

    def show(k, state):
        return f"{k} {state[0]} {state[1]}" if with_steps else f"{state[0]} {state[1]}"

    distractors = [
        show(n - 1, states[-2]),  # stopped one pass early
        show(n + 1, more),  # one pass too many
        show(n, (x, y + sy)),  # thought the loop quit before the last `-=` line
        show(n, (y, x)),
        show(n, (x, y - sy)),
        show(n + 1, (x, y)),
    ]
    trace = " → ".join(f"({p}, {q})" for p, q in states)
    why = (
        f"The condition is only checked at the top of each pass. Tracing ({a}, {b}): "
        f"{trace}. After {n} passes `{a} < {b}` is false, so the loop stops."
    )
    return _output(code, MEDIUM, distractors, why, rng)


# ==========================================================================
# HARD
# ==========================================================================


def _search_else_code(lst: str, nums, v: str, cond: str, *, brk: bool = True, mode: str = "loop") -> str:
    """A for/else search; ``mode`` re-attaches the else block to simulate misconceptions."""
    lines = [f"{lst} = {nums}", f"for {v} in {lst}:", f"    if {cond}:", f'        print("found", {v})']
    if brk:
        lines.append("        break")
    if mode == "loop":
        lines += ["else:", '    print("no match")']
    elif mode == "if":
        lines += ["    else:", '        print("no match")']
    elif mode == "always":
        lines.append('print("no match")')
    lines.append('print("done")')
    return "\n".join(lines)


@generator(TOPIC, HARD)
def gen_loop_else(rng: random.Random) -> Question:
    """for/else and while/else: the else block runs only when no break happened."""
    shape = rng.choice(["search", "search", "prime", "while"])
    rule = "A loop's `else` block runs only if the loop finishes without hitting `break`."
    if shape == "search":
        lst, v = rng.choice([("nums", "n"), ("values", "x"), ("scores", "s")])
        found = rng.random() < 0.6
        size = 4
        if rng.random() < 0.5:
            k = rng.randint(3, 7)
            cond = f"{v} % {k} == 0"
            misses = [x for x in range(1, 40) if x % k]
            hits = [x for x in range(k, 40, k)]
        else:
            t = rng.randint(10, 20)
            cond = f"{v} > {t}"
            misses = list(range(1, t + 1))
            hits = list(range(t + 1, t + 15))
        nums = rng.sample(misses, size)
        if found:
            idx = rng.randint(1, size - 1)
            picks = rng.sample(hits, 2)
            nums[idx] = picks[0]
            if idx < size - 1 and rng.random() < 0.5:
                nums[rng.randint(idx + 1, size - 1)] = picks[1]
        code = _search_else_code(lst, nums, v, cond)
        alts = [
            _search_else_code(lst, nums, v, cond, mode="always"),
            _search_else_code(lst, nums, v, cond, mode="if"),
            _search_else_code(lst, nums, v, cond, brk=False),
            _search_else_code(lst, nums, v, cond, mode="none"),
        ]
        outs = [_run(c) for c in alts]
        if found:
            distractors = [outs[0], outs[1], outs[2], SYNTAX_ERROR]
            why = (
                f"{rule} Here `break` ran as soon as `{cond}` was true, so "
                f'"no match" was skipped and the loop went straight on to `print("done")`.'
            )
        else:
            distractors = [outs[3], outs[1], SYNTAX_ERROR, "no match"]
            why = (
                f"{rule} No value made `{cond}` true, so `break` never ran: the loop finished "
                f'normally, the `else` block printed "no match", and then "done" was printed.'
            )
    elif shape == "prime":
        composite = rng.random() < 0.7
        if composite:
            num = rng.choice([n for n in range(15, 80) if any(n % d == 0 for d in range(2, n)) and n % 2])
        else:
            num = rng.choice([n for n in range(11, 60) if all(n % d for d in range(2, n))])

        def prime_code(stop: str = "n", *, brk: bool = True, mode: str = "loop") -> str:
            lines = [f"n = {num}", f"for d in range(2, {stop}):", "    if n % d == 0:",
                     '        print(n, "=", d, "*", n // d)']
            if brk:
                lines.append("        break")
            if mode == "loop":
                lines += ["else:", '    print(n, "is prime")']
            elif mode == "always":
                lines.append('print(n, "is prime")')
            return "\n".join(lines)

        code = prime_code()
        if composite:
            d = next(d for d in range(2, num) if num % d == 0)
            distractors = [
                _run(prime_code(mode="always")), _run(prime_code(brk=False)),
                f"{num} is prime", SYNTAX_ERROR,
            ]
            why = (
                f"{rule} {num} % {d} == 0, so the loop prints the factors and `break`s, "
                f'which skips the `else` block: "is prime" is never printed.'
            )
        else:
            distractors = [NOTHING_PRINTED, _run(prime_code("n + 1")), SYNTAX_ERROR, f"{num} = 1 * {num}"]
            why = (
                f"{rule} No `d` from 2 to {num - 1} divides {num}, so `break` never runs; the "
                f"loop ends normally and the `else` block prints that {num} is prime."
            )
    else:
        start = rng.randint(10, 20)
        step = rng.randint(2, 4)
        seq = list(range(start - step, -step, -step))  # values n takes after each `n -= step`
        positive = [x for x in seq if x > 0]
        hit = rng.random() < 0.55 and len(positive) >= 2
        if hit:
            bad = rng.choice(positive[1:])
        else:
            bad = rng.choice([x for x in range(1, start) if x not in seq])
        name = rng.choice(["n", "fuel", "steps", "count"])

        def while_code(mode: str = "loop") -> str:
            lines = [f"{name} = {start}", f"while {name} > 0:", f"    {name} -= {step}",
                     f"    if {name} == {bad}:", f'        print("stopped at", {name})', "        break"]
            if mode == "loop":
                lines += ["else:", f'    print("finished at", {name})']
            elif mode == "always":
                lines.append(f'print("finished at", {name})')
            return "\n".join(lines)

        code = while_code()
        final = seq[-1]
        if hit:
            distractors = [
                _run(while_code("always")), f"finished at {final}", f"stopped at {bad}\nfinished at {final}",
                SYNTAX_ERROR,
            ]
            why = (
                f"{rule} `{name}` reaches {bad}, so the loop prints \"stopped at {bad}\" and "
                f"`break`s, which skips the `else` block entirely."
            )
        else:
            distractors = [NOTHING_PRINTED, f"finished at {final + step}", f"finished at {bad}",
                           "finished at 0", SYNTAX_ERROR]
            why = (
                f"{rule} `{name}` goes {_commas([start] + seq)} and never equals {bad}, so the "
                f"loop stops when `{name} > 0` becomes false and the `else` block runs."
            )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_nested_break(rng: random.Random) -> Question:
    """break inside a nested loop exits only the innermost loop."""
    a = rng.randint(3, 4)
    b = rng.randint(3, 5)
    kind = rng.choice(["fixed", "gt", "eq", "sum"])
    if kind == "fixed":
        k = rng.randint(1, b - 2)
        cond, pred = f"j == {k}", (lambda i, j: j == k)
    elif kind == "gt":
        cond, pred = "j > i", (lambda i, j: j > i)
    elif kind == "eq":
        cond, pred = "j == i", (lambda i, j: j == i)
    else:
        t = rng.randint(2, a + b - 3)
        cond, pred = f"i + j >= {t}", (lambda i, j: i + j >= t)
    add_j = rng.random() < 0.35
    acc = "total" if add_j else "count"
    inc = "j" if add_j else "1"
    code = (
        f"{acc} = 0\nfor i in range({a}):\n    for j in range({b}):\n        if {cond}:\n"
        f"            break\n        {acc} += {inc}\nprint({acc})"
    )

    def sim(mode: str):
        total, per = 0, []
        for i in range(a):
            row = 0
            for j in range(b):
                if pred(i, j):
                    if mode == "inner":
                        break
                    if mode == "all":
                        return total + row, per
                    if mode == "continue":
                        continue
                row += j if add_j else 1
            total += row
            per.append(row)
        return total, per

    ans, per = sim("inner")
    cands = [sim("all")[0], sim("continue")[0], sim("none")[0], per[0], ans + per[-1]]
    why = (
        f"`break` only exits the inner `for j` loop; the outer loop still runs all {a} passes. "
        f"For i = 0 to {a - 1} the inner loop adds {_commas(per)}, so the result is {ans}."
    )
    return _output(code, HARD, _nums(ans, cands, rng), why, rng)


@generator(TOPIC, HARD)
def gen_dependent_nested(rng: random.Random) -> Question:
    """Nested loops whose inner range depends on the outer variable (triangular counts)."""
    add_j = rng.random() < 0.35
    n = rng.randint(3, 5) if add_j else rng.randint(4, 7)
    outer_from_one = rng.random() < 0.3
    outer = f"1, {n + 1}" if outer_from_one else str(n)
    inners = ["i", "i + 1", f"i, {n}", f"i + 1, {n}"]
    if outer_from_one:
        inners = ["i", "i + 1", f"i, {n + 1}", f"{n + 1} - i"]
    inner = rng.choice(inners)
    acc = "total" if add_j else "count"
    inc = "j" if add_j else "1"

    def make(inner_args: str, outer_args: str = outer) -> str:
        return (
            f"{acc} = 0\nfor i in range({outer_args}):\n    for j in range({inner_args}):\n"
            f"        {acc} += {inc}\nprint({acc})"
        )

    code = make(inner)
    alts = [make(x) for x in inners if x != inner] + [make(str(n))]
    distractors = [_run(c) for c in alts]
    outer_vals = list(range(1, n + 1)) if outer_from_one else list(range(n))
    parts = []
    for i in outer_vals:
        js = list(eval(f"range({inner})", {"i": i}))  # noqa: S307 - our own constant expression
        parts.append(sum(js) if add_j else len(js))
    ans = sum(parts)
    distractors += _nums(ans, [n * n, ans + n, ans - parts[-1]], rng)
    what = "adds" if add_j else "runs"
    unit = "" if add_j else " times"
    why = (
        f"The inner range depends on `i`, so the inner loop {what} {_commas(parts)}{unit} on "
        f"successive passes of the outer loop: {_plus(parts)} = {ans}."
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_simultaneous_update(rng: random.Random) -> Question:
    """Loops that update two variables at once with tuple assignment (a, b = b, a + b)."""
    shape = rng.choice(["fib", "gcd", "for"])
    if shape == "fib":
        a, b = rng.choice([("a", "b"), ("x", "y"), ("prev", "curr")])
        a0, b0 = rng.randint(0, 2), rng.randint(1, 3)
        limit = rng.randint(15, 60)
        states = [(a0, b0)]
        while states[-1][1] < limit:
            p, q = states[-1]
            states.append((q, p + q))
        if len(states) < 4:
            raise GenerationError("too few iterations")
        code = f"{a}, {b} = {a0}, {b0}\nwhile {b} < {limit}:\n    {a}, {b} = {b}, {a} + {b}\nprint({a}, {b})"
        split = f"{a}, {b} = {a0}, {b0}\nwhile {b} < {limit}:\n    {a} = {b}\n    {b} = {a} + {b}\nprint({a}, {b})"
        p, q = states[-1]
        distractors = [_run(split), f"{states[-2][0]} {states[-2][1]}", f"{q} {p + q}", f"{q} {p}"]
        trace = " → ".join(f"({x}, {y})" for x, y in states)
        why = (
            f"`{a}, {b} = {b}, {a} + {b}` evaluates both right-hand values using the *old* "
            f"`{a}` and `{b}` before assigning. Trace: {trace}; then `{b} < {limit}` is false."
        )
    elif shape == "gcd":
        g = rng.randint(2, 12)
        p, q = rng.choice([(p, q) for p in range(2, 10) for q in range(2, 10) if p != q and _gcd(p, q) == 1])
        x, y = g * p, g * q
        cond = rng.choice(["b != 0", "b > 0"])
        code = f"a, b = {x}, {y}\nwhile {cond}:\n    a, b = b, a % b\nprint(a)"
        split = f"a, b = {x}, {y}\nwhile {cond}:\n    a = b\n    b = a % b\nprint(a)"
        states = [(x, y)]
        while states[-1][1] != 0:
            s, t = states[-1]
            states.append((t, s % t))
        distractors = [_run(split), str(states[-2][0]), str(x % y), "0", str(min(x, y)), str(abs(x - y))]
        distractors += _nums(g, [1, 2 * g], rng)
        trace = " → ".join(f"({s}, {t})" for s, t in states)
        why = (
            f"Both new values are computed from the old pair before either is assigned. "
            f"Trace (a, b): {trace}. When `b` hits 0 the loop stops and `a` is {g}."
        )
    else:
        p, q = rng.sample(range(1, 8), 2)
        k = rng.randint(2, 4)
        lhs, rhs1, rhs2 = rng.choice([
            ("x, y", "y", "x + y"),
            ("x, y", "x + y", "x"),
            ("x, y", "y", "x * 2"),
            ("x, y", "y + 1", "x"),
        ])
        code = f"x, y = {p}, {q}\nfor _ in range({k}):\n    {lhs} = {rhs1}, {rhs2}\nprint(x, y)"
        split = f"x, y = {p}, {q}\nfor _ in range({k}):\n    x = {rhs1}\n    y = {rhs2}\nprint(x, y)"
        fewer = f"x, y = {p}, {q}\nfor _ in range({k - 1}):\n    {lhs} = {rhs1}, {rhs2}\nprint(x, y)"
        more = f"x, y = {p}, {q}\nfor _ in range({k + 1}):\n    {lhs} = {rhs1}, {rhs2}\nprint(x, y)"
        res = run_code(code)
        fx, fy = res.namespace["x"], res.namespace["y"]
        distractors = [_run(split), _run(fewer), _run(more), f"{fy} {fx}"]
        states = [(p, q)]
        for _ in range(k):
            x, y = states[-1]
            states.append((eval(rhs1, {"x": x, "y": y}), eval(rhs2, {"x": x, "y": y})))  # noqa: S307
        trace = " → ".join(f"({s}, {t})" for s, t in states)
        why = (
            f"`{lhs} = {rhs1}, {rhs2}` computes both right-hand values from the *old* `x` and "
            f"`y`, then assigns them together. Over {k} passes: {trace}."
        )
    return _output(code, HARD, distractors, why, rng)


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


@generator(TOPIC, HARD)
def gen_header_evaluated_once(rng: random.Random) -> Question:
    """The for header is evaluated once; changing n / the loop variable / the string inside doesn't affect it."""
    shape = rng.choice(["range_n", "loop_var", "loop_var", "string"])
    if shape == "range_n":
        k = rng.randint(3, 6)
        inc = rng.choice([1, 2, 3])
        name = rng.choice(["n", "size", "limit"])
        code = f"{name} = {k}\nfor i in range({name}):\n    {name} += {inc}\nprint({name})"
        ans = k + k * inc
        distractors = [FOREVER] + _nums(
            ans, [k + (k - 1) * inc, k + (k + 1) * inc, k + inc, k * inc], rng
        )
        why = (
            f"`range({name})` is evaluated once, when the loop starts, so it is `range({k})` and "
            f"the body runs exactly {k} times, no matter how `{name}` changes: "
            f"{k} + {k} × {inc} = {ans}."
        )
    elif shape == "loop_var":
        start = rng.choice([0, 1])
        stop = start + rng.randint(3, 4)
        op, val = rng.choice([("*=", 10), ("+=", 5), ("+=", 10), ("*=", 2), ("*=", 3)])
        if start == 0 and op == "*=":
            start = 1
            stop += 1
        args = str(stop) if start == 0 else f"{start}, {stop}"
        code = f'for i in range({args}):\n    i {op} {val}\n    print(i, end=" ")'
        persistent = (
            f"i = {start}\nwhile i < {stop}:\n    i {op} {val}\n    print(i, end=\" \")\n    i += 1"
        )
        ignored = " ".join(str(i) for i in range(start, stop))
        correct_vals = run_code(code).output.split()
        distractors = [
            _run(persistent), ignored, " ".join(correct_vals[:-1]), FOREVER,
            " ".join(correct_vals[1:]),
        ]
        why = (
            f"At the start of every pass the `for` loop assigns `i` the *next value from the "
            f"range*, overwriting whatever the body did to it. So `i {op} {val}` only affects "
            f"the current pass: {_commas(correct_vals)}."
        )
    else:
        word = rng.choice([w for w in _SHORT_WORDS if len(w) <= 4])
        transform = rng.choice(["ch.upper()", "ch * 2", '"!"'])
        name = rng.choice(["word", "text", "s"])
        code = f'{name} = "{word}"\nfor ch in {name}:\n    {name} += {transform}\nprint({name})'
        extra = {"ch.upper()": word.upper(), "ch * 2": "".join(c * 2 for c in word), '"!"': "!" * len(word)}
        first = {"ch.upper()": word[0].upper(), "ch * 2": word[0] * 2, '"!"': "!"}
        distractors = [FOREVER, word + first[transform], word, extra[transform], word + extra[transform] * 2]
        why = (
            f'The `for` loop grabbed the original string "{word}" when it started. `+=` makes '
            f"`{name}` refer to a *new* string, but the loop keeps walking the original "
            f"{len(word)} characters, so it runs {len(word)} times and then stops."
        )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_string_build_trace(rng: random.Random) -> Question:
    """Trace a loop that builds a string: prepend vs append, dedupe, walking backwards."""
    shape = rng.choice(["alternate", "dedupe", "backwards"])
    if shape == "alternate":
        word = rng.choice([w for w in _DISTINCT_WORDS if 5 <= len(w) <= 6])
        parity = rng.choice([0, 1])

        def build(par: int) -> str:
            return (
                f'result = ""\nfor i, ch in enumerate("{word}"):\n    if i % 2 == {par}:\n'
                f"        result += ch\n    else:\n        result = ch + result\nprint(result)"
            )

        code = build(parity)
        steps, cur = [], ""
        for i, ch in enumerate(word):
            cur = cur + ch if i % 2 == parity else ch + cur
            steps.append(cur)
        distractors = [_run(build(1 - parity)), word[::-1], word, word[parity::2] + word[1 - parity::2]]
        why = (
            f"`result += ch` adds to the end, while `result = ch + result` puts the letter at "
            f"the front. Step by step: {' → '.join(steps)}."
        )
    elif shape == "dedupe":
        adjacent = rng.random() < 0.35
        word = rng.choice(_DEDUPE_WORDS)
        first_seen = "".join(dict.fromkeys(word))
        last_seen = "".join(reversed(list(dict.fromkeys(reversed(word)))))
        runs = "".join(ch for i, ch in enumerate(word) if i == 0 or ch != word[i - 1])
        singles = "".join(ch for ch in word if word.count(ch) == 1) or None
        if adjacent and runs == word:
            adjacent = False
        if adjacent:
            cond = "not result or ch != result[-1]"
            distractors = [first_seen, word, last_seen, singles]
            why = (
                "`ch != result[-1]` only compares with the *last* letter added, so a letter is "
                f"dropped only when it repeats the one right before it: {runs}."
            )
        else:
            cond = "ch not in result"
            distractors = [last_seen, runs, singles, word]
            why = (
                "`ch not in result` is True only the first time each letter appears, so every "
                f"letter is kept once, in order of first appearance: {first_seen}."
            )
        code = f'result = ""\nfor ch in "{word}":\n    if {cond}:\n        result += ch\nprint(result)'
    else:
        word = rng.choice([w for w in _DISTINCT_WORDS if 5 <= len(w) <= 6])
        step = rng.choice([1, 2])
        stop = rng.choice([-1, 0])
        n = len(word)
        code = (
            f'word = "{word}"\nresult = ""\nfor i in range(len(word) - 1, {stop}, -{step}):\n'
            f"    result += word[i]\nprint(result)"
        )
        idx = list(range(n - 1, stop, -step))
        other_stop = 0 if stop == -1 else -1
        other_idx = list(range(n - 1, other_stop, -step))
        distractors = [
            "".join(word[i] for i in other_idx),
            "".join(word[i] for i in range(n - 2, stop, -step)),
            word[::-1] if step == 2 else word[::-2],
            "".join(word[i] for i in idx)[::-1],
        ]
        why = (
            f"`range({n - 1}, {stop}, -{step})` gives the indexes {_commas(idx)} — it counts down "
            f"and stops *before* {stop}"
            + (", so index 0 is included." if stop == -1 else ", so index 0 is never reached.")
        )
    return _output(code, HARD, distractors, why, rng)
