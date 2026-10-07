"""Question generators for the "recursion" topic (Recursion).

Covers tracing simple recursive functions (factorial, sums, powers, repeated
addition, string and list recursion by slicing), base cases (the value they
must return, which call reaches them first, and what happens when they are
missing, unreachable or skipped over: ``RecursionError`` / ``IndexError``),
counting calls, the call stack unwinding (printing before vs after the
recursive call, values printed on the way back up), digit and binary
recursion, Euclid's gcd, mutual recursion, recursion over nested lists, tree
recursion with two recursive calls (naive Fibonacci call counts, choice
trees) and the classic forgotten ``return`` in the recursive case.
"""

from __future__ import annotations

import math
import random

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
    int_distractors,
    output_question,
    run_code,
    which_expression_question,
)

TOPIC = "recursion"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
VALUE_OF_RESULT = "What is the value of `result` after this code runs?"
BLANK = "____"
RECURSION_ERROR = error_choice("RecursionError")
TYPE_ERROR = error_choice("TypeError")
INDEX_ERROR = error_choice("IndexError")
MAX_SNIPPET_LINES = 14

# Short words with no repeated letters (so misreadings give distinct answers).
_WORDS = [
    "cat", "dog", "sun", "code", "star", "frog", "lime", "fish", "wolf", "crab",
    "tiger", "lemon", "mango", "pixel", "plant", "quest", "snake", "chair",
]
_SHORT_WORDS = [w for w in _WORDS if len(w) <= 4]


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _lines(*parts) -> str:
    return "\n".join(str(p) for p in parts)


def _seq(values, sep: str = "\n") -> str:
    return sep.join(str(v) for v in values)


def _prog(*blocks: str) -> str:
    """Join top-level blocks (defs, main code) with two blank lines, as PEP 8 asks."""
    code = "\n\n\n".join(b.strip("\n") for b in blocks)
    if len(code.split("\n")) > MAX_SNIPPET_LINES:
        raise GenerationError(f"snippet too long:\n{code}")
    return code


def _norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in str(s).strip("\n").split("\n"))


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
    """Stringify distractors and drop any that would not fit on a choice button."""
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


def _nums(cands, correct: int, rng: random.Random) -> list:
    """Misconception-based candidates first, then nearby integers as a fallback."""
    return [*cands, *int_distractors(correct, rng)]


def _output(
    code: str,
    difficulty: int,
    distractors,
    explanation: str,
    rng: random.Random,
    *,
    prompt: str = PRINT,
    allow_error: bool = False,
    expect=None,
) -> Question:
    """``output_question`` plus a self-check: if ``expect`` is given, the snippet must
    really print it (the explanation is written from that value)."""
    if expect is not None:
        expect = str(expect)
        if _norm(_run(code)) != _norm(expect or NOTHING_PRINTED):
            raise GenerationError(f"expected {expect!r}, got {_run(code)!r}:\n{code}")
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


def _lit(value) -> str:
    """A value written the way our snippets write it (double-quoted strings)."""
    if isinstance(value, str):
        return '"' + value + '"'
    return repr(value)


def _call(fname: str, *args) -> str:
    return fname + "(" + ", ".join(_lit(a) for a in args) + ")"


def _trace(defs: str, fname: str, call: str):
    """Evaluate ``call`` with ``fname`` instrumented.

    Returns ``(calls, returns, value)`` where ``calls`` / ``returns`` list the
    argument tuples in the order the calls started / finished.
    """
    probe = _lines(
        defs,
        "_calls, _returns = [], []",
        f"_inner = {fname}",
        f"def {fname}(*args):",
        "    _calls.append(args)",
        "    result = _inner(*args)",
        "    _returns.append(args)",
        "    return result",
        f"_value = {call}",
    )
    res = run_code(probe)
    if res.error:
        raise GenerationError(f"trace raised {res.error}")
    ns = res.namespace
    return ns["_calls"], ns["_returns"], ns["_value"]


def _value_of(code: str, name: str):
    res = run_code(code)
    if res.error:
        raise GenerationError(f"snippet raised {res.error}")
    return res.namespace[name]


def _blank_question(
    *,
    difficulty: int,
    template: str,
    correct: str,
    candidates,
    prompt: str,
    explanation: str,
    rng: random.Random,
) -> Question:
    """'Which choice fills the blank so the code prints X?' verified by running every choice.

    ``prompt`` / ``explanation`` may contain ``{target}``, replaced by what the
    completed program prints.  Candidates that would also print the target are
    dropped, so exactly one choice is right.
    """
    target = _run(template.replace(BLANK, correct))
    if target.startswith("Error:") or target == NOTHING_PRINTED or "\n" in target:
        raise GenerationError(f"bad target {target!r}")
    wrong: list[str] = []
    for cand in candidates:
        if cand == correct or cand in wrong:
            continue
        if _norm(_run(template.replace(BLANK, cand))) == _norm(target):
            continue  # would also be right
        wrong.append(cand)
    return _choice(
        difficulty=difficulty,
        prompt=prompt.replace("{target}", target),
        code=template,
        correct=correct,
        distractors=wrong,
        explanation=explanation.replace("{target}", target),
        rng=rng,
    )


def _main_line(rng: random.Random, call: str) -> str:
    """``print(call)``, or store the result first."""
    if rng.random() < 0.7:
        return f"print({call})"
    var = rng.choice(["result", "answer", "value"])
    return f"{var} = {call}\nprint({var})"


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_trace_linear(rng: random.Random) -> Question:
    """Trace a one-call-per-level recursion (factorial, sum, power, ...) with small numbers."""
    shape = rng.choice(["factorial", "sum_to", "power", "multiply", "step_sum"])
    p = rng.choice(["n", "num", "k"])
    if shape == "factorial":
        fname = rng.choice(["factorial", "fact"])
        k = rng.randint(3, 5)
        cond = rng.choice([f"{p} == 1", f"{p} <= 1", f"{p} == 0"])
        defs = _lines(
            f"def {fname}({p}):",
            f"    if {cond}:",
            "        return 1",
            f"    return {p} * {fname}({p} - 1)",
        )
        call = f"{fname}({k})"
        answer = math.factorial(k)
        cands = [math.factorial(k - 1), k * (k + 1) // 2, k * (k - 1), math.factorial(k + 1), k]
        chain = " * ".join(str(i) for i in range(k, 0, -1))
        why = (
            f"`{fname}({k})` returns {k} * `{fname}({k - 1})`, and each call does the same with a "
            f"smaller number until the base case returns 1. So the result is {chain} = {answer}."
        )
    elif shape == "sum_to":
        fname = rng.choice(["sum_to", "add_up", "total"])
        k = rng.randint(3, 6)
        b = rng.choice([0, 1])
        defs = _lines(
            f"def {fname}({p}):",
            f"    if {p} == {b}:",
            f"        return {b}",
            f"    return {p} + {fname}({p} - 1)",
        )
        call = f"{fname}({k})"
        answer = k * (k + 1) // 2
        cands = [answer - k, answer + k + 1, k + (k - 1), math.factorial(k), answer - 1, k]
        chain = " + ".join(str(i) for i in range(k, b - 1, -1))
        why = (
            f"`{fname}({k})` returns {k} + `{fname}({k - 1})`, and so on down to the base case "
            f"`{fname}({b})`, which returns {b}. Adding everything up: {chain} = {answer}."
        )
    elif shape == "power":
        bp, ep = rng.choice([("base", "exp"), ("x", "n"), ("b", "e")])
        b, e = rng.choice([(2, 3), (2, 4), (2, 5), (3, 2), (3, 4), (4, 2), (4, 3), (5, 2), (5, 3), (6, 2)])
        defs = _lines(
            f"def power({bp}, {ep}):",
            f"    if {ep} == 0:",
            "        return 1",
            f"    return {bp} * power({bp}, {ep} - 1)",
        )
        call = f"power({b}, {e})"
        answer = b ** e
        cands = [b ** (e - 1), b * e, e ** b, b ** (e + 1), b + e]
        chain = " * ".join([str(b)] * e)
        why = (
            f"Each call multiplies by `{bp}` once and lowers `{ep}` by 1; when `{ep}` reaches 0 "
            f"the base case returns 1. So {b} is multiplied {e} times: {chain} = {answer}."
        )
    elif shape == "multiply":
        fname = rng.choice(["multiply", "times"])
        a = rng.randint(3, 9)
        b = rng.randint(2, 4)
        defs = _lines(
            f"def {fname}(a, b):",
            "    if b == 0:",
            "        return 0",
            f"    return a + {fname}(a, b - 1)",
        )
        call = f"{fname}({a}, {b})"
        answer = a * b
        cands = [a * (b - 1), a + b, a * (b + 1), a, a + b + 1]
        chain = " + ".join([str(a)] * b)
        why = (
            f"Each call adds `a` ({a}) once and calls itself with `b - 1`. That happens {b} times "
            f"before `b` reaches 0 (which adds 0): {chain} = {answer}."
        )
    else:
        fname = rng.choice(["skip_sum", "step_sum", "every_other"])
        k = rng.randint(5, 10)
        defs = _lines(
            f"def {fname}({p}):",
            f"    if {p} <= 0:",
            "        return 0",
            f"    return {p} + {fname}({p} - 2)",
        )
        call = f"{fname}({k})"
        terms = list(range(k, 0, -2))
        answer = sum(terms)
        cands = [k * (k + 1) // 2, answer - terms[-1], k + (k - 2), answer + k + 2, answer - 1, k]
        why = (
            f"The argument drops by 2 each call ({', '.join(map(str, terms))}), and once it is 0 "
            f"or less the base case returns 0. So the result is "
            f"{' + '.join(map(str, terms))} = {answer}."
        )
    code = _prog(defs, _main_line(rng, call))
    return _output(code, EASY, _nums(cands, answer, rng), why, rng, expect=answer)


@generator(TOPIC, EASY)
def gen_countdown(rng: random.Random) -> Question:
    """Printing *before* the recursive call shows values in the order the calls happen."""
    shape = rng.choice(["lines", "message", "one_line", "step", "count_up"])
    fname = rng.choice(["countdown", "count_down", "blast_off"])
    msg = rng.choice(["Go!", "Liftoff!", "Done!", "Blast off!"])
    if shape == "lines":
        k = rng.randint(2, 5)
        cond = rng.choice(["n == 0", "n < 1", "n <= 0"])
        defs = _lines(
            f"def {fname}(n):",
            f"    if {cond}:",
            "        return",
            "    print(n)",
            f"    {fname}(n - 1)",
        )
        main = f"{fname}({k})"
        seq = list(range(k, 0, -1))
        expect = _seq(seq)
        distractors = [
            _seq(seq + [0]),
            _seq(seq[::-1]),
            _seq(seq[:-1]),
            _seq(range(k - 1, -1, -1)),
            str(k),
            _seq([0] + seq[::-1]),
        ]
        why = (
            f"Each call prints `n` and *then* calls `{fname}(n - 1)`, so the numbers appear in the "
            f"order the calls are made: {', '.join(map(str, seq))}. When `n` reaches 0 the base "
            f"case (`{cond}`) returns without printing anything."
        )
    elif shape == "message":
        k = rng.randint(2, 4)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            f'        print("{msg}")',
            "    else:",
            "        print(n)",
            f"        {fname}(n - 1)",
        )
        main = f"{fname}({k})"
        seq = list(range(k, 0, -1))
        expect = _seq(seq + [msg])
        distractors = [
            _seq([msg] + seq),
            _seq(seq),
            _seq(seq[::-1] + [msg]),
            _seq(seq + [0, msg]),
            _seq(seq[:-1] + [msg]),
            msg,
        ]
        why = (
            f"`{fname}({k})` prints {k} and then calls `{fname}({k - 1})`, and so on. Only the last "
            f"call, `{fname}(0)`, takes the base-case branch, so {msg} is printed once, at the end."
        )
    elif shape == "one_line":
        k = rng.randint(3, 6)
        defs = _lines(
            f"def {fname}(n):",
            "    if n <= 0:",
            f'        print("{msg}")',
            "        return",
            '    print(n, end=" ")',
            f"    {fname}(n - 1)",
        )
        main = f"{fname}({k})"
        seq = list(range(k, 0, -1))
        s = _seq(seq, " ")
        expect = f"{s} {msg}"
        distractors = [
            f"{s} 0 {msg}",
            f"{_seq(seq[::-1], ' ')} {msg}",
            f"{msg} {s}",
            s,
            f"{_seq(seq[:-1], ' ')} {msg}",
            _seq(seq + [msg]),
        ]
        why = (
            f"Each call prints its `n` (staying on the same line because of `end=\" \"`) before "
            f"calling `{fname}(n - 1)`. When `n` reaches 0 the base case prints {msg} and stops, "
            f"so 0 itself is never printed."
        )
    elif shape == "step":
        k = rng.randint(5, 10)
        step = rng.choice([2, 2, 3])
        defs = _lines(
            f"def {fname}(n):",
            "    if n <= 0:",
            "        return",
            '    print(n, end=" ")',
            f"    {fname}(n - {step})",
        )
        main = f"{fname}({k})"
        seq = list(range(k, 0, -step))
        expect = _seq(seq, " ")
        distractors = [
            _seq(seq + [seq[-1] - step], " "),
            _seq(range(k, 0, -1), " "),
            _seq(seq[::-1], " "),
            _seq(seq[:-1], " "),
            str(k),
        ]
        why = (
            f"Each call prints `n`, then recurses with `n - {step}`: {', '.join(map(str, seq))}. "
            f"The next value, {seq[-1] - step}, hits the base case `n <= 0`, which returns "
            f"before printing."
        )
    else:
        fname = rng.choice(["count_up", "climb"])
        start = rng.randint(1, 4)
        stop = start + rng.randint(1, 4)
        defs = _lines(
            f"def {fname}(n, stop):",
            "    if n > stop:",
            "        return",
            "    print(n)",
            f"    {fname}(n + 1, stop)",
        )
        main = f"{fname}({start}, {stop})"
        seq = list(range(start, stop + 1))
        expect = _seq(seq)
        distractors = [
            _seq(range(start, stop)),
            _seq(range(start, stop + 2)),
            _seq(seq[::-1]),
            _seq(range(start + 1, stop + 1)),
            str(start),
        ]
        why = (
            f"`n` starts at {start} and goes up by 1 each call, and every call prints before it "
            f"recurses. The base case `n > stop` only stops the call where `n` is {stop + 1}, "
            f"so {stop} is still printed."
        )
    return _output(_prog(defs, main), EASY, distractors, why, rng, expect=expect)


@generator(TOPIC, EASY)
def gen_base_case_value(rng: random.Random) -> Question:
    """The base case must return the 'neutral' value: 0 for sums, 1 for products, "" for strings."""
    shape = rng.choice(["sum_to", "factorial", "list_sum", "product", "reverse", "repeat"])
    if shape == "sum_to":
        fname = rng.choice(["sum_to", "add_up"])
        k = rng.randint(3, 6)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            f"        return {BLANK}",
            f"    return n + {fname}(n - 1)",
        )
        main = f"print({fname}({k}))"
        correct = "0"
        candidates = ["1", "None", "n - 1", f"{fname}(n - 1)", "-1"]
        chain = " + ".join(str(i) for i in range(k, -1, -1))
        why = (
            f"The base case's value is added into the total, so it must be 0, which changes "
            f"nothing: {chain} = {{target}}. Returning 1 would make the result one too big, and "
            f"`None` cannot be added to a number."
        )
    elif shape == "factorial":
        fname = rng.choice(["factorial", "fact"])
        k = rng.randint(3, 5)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            f"        return {BLANK}",
            f"    return n * {fname}(n - 1)",
        )
        main = f"print({fname}({k}))"
        correct = "1"
        candidates = ["0", "n", "None", "n - 1"]
        why = (
            "Every result is multiplied by the base case's value, so it must be 1 (multiplying "
            "by 1 changes nothing). Returning 0, or `n`, which is 0 there, would make the whole "
            "product 0."
        )
    elif shape == "list_sum":
        fname = rng.choice(["total", "add_all", "list_sum"])
        nums = rng.sample(range(1, 10), rng.randint(3, 4))
        defs = _lines(
            f"def {fname}(nums):",
            "    if len(nums) == 0:",
            f"        return {BLANK}",
            f"    return nums[0] + {fname}(nums[1:])",
        )
        main = f"print({fname}({nums}))"
        correct = "0"
        candidates = ["1", "None", "nums[0]", "[]", "nums"]
        why = (
            f"When the list is empty there is nothing left to add, so the base case returns 0 and "
            f"the total is {sum(nums)}. `nums[0]` fails on an empty list, and 1 would make the "
            f"total {sum(nums) + 1}."
        )
    elif shape == "product":
        fname = rng.choice(["product", "multiply_all"])
        nums = [rng.randint(2, 5) for _ in range(3)]
        defs = _lines(
            f"def {fname}(nums):",
            "    if len(nums) == 0:",
            f"        return {BLANK}",
            f"    return nums[0] * {fname}(nums[1:])",
        )
        main = f"print({fname}({nums}))"
        correct = "1"
        candidates = ["0", "None", "nums[0]", "[]"]
        why = (
            "The empty list's result is multiplied into every product, so it must be 1. "
            "Returning 0 would make the final answer 0, and `nums[0]` fails on an empty list."
        )
    elif shape == "reverse":
        fname = rng.choice(["reverse", "backwards"])
        word = rng.choice(_WORDS)
        defs = _lines(
            f"def {fname}(text):",
            '    if text == "":',
            f"        return {BLANK}",
            f"    return {fname}(text[1:]) + text[0]",
        )
        main = f'print({fname}("{word}"))'
        correct = '""'
        candidates = ["None", "0", "text[0]", "[]", '" "']
        why = (
            'The base case\'s result is joined to the letters with `+`, so it must be the empty '
            'string `""`, which adds nothing. `None` or `0` cannot be added to a string, and '
            '`text[0]` fails on an empty string.'
        )
    else:
        fname = rng.choice(["stars", "bar", "line"])
        ch = rng.choice(["*", "#", "=", "~"])
        k = rng.randint(3, 6)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            f"        return {BLANK}",
            f'    return "{ch}" + {fname}(n - 1)',
        )
        main = f"print({fname}({k}))"
        correct = '""'
        candidates = [f'"{ch}"', "None", "0", "n"]
        why = (
            f"`{fname}({k})` adds one {ch} per call, {k} times, and the base case's value goes "
            f'on the end, so it must add nothing: `""`. Returning "{ch}" would give {k + 1} '
            f"characters, and `None` or `0` cannot be added to a string."
        )
    return _blank_question(
        difficulty=EASY,
        template=_prog(defs, main),
        correct=correct,
        candidates=candidates,
        prompt="Which value fills the blank so the code prints `{target}`?",
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_first_return(rng: random.Random) -> Question:
    """Calls pile up until the base case; the deepest call returns first."""
    shape = rng.choice(["factorial", "sum_to", "length", "step"])
    beyond = None
    if shape == "factorial":
        fname = rng.choice(["fact", "factorial"])
        cond, last = rng.choice([("n <= 1", 1), ("n == 1", 1), ("n == 0", 0)])
        k = rng.randint(3, 5)
        defs = _lines(
            f"def {fname}(n):",
            f"    if {cond}:",
            "        return 1",
            f"    return n * {fname}(n - 1)",
        )
        args = (k,)
        beyond = _call(fname, last - 1)
    elif shape == "sum_to":
        fname = rng.choice(["sum_to", "total"])
        k = rng.randint(3, 5)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            "        return 0",
            f"    return n + {fname}(n - 1)",
        )
        args = (k,)
        beyond = _call(fname, -1)
    elif shape == "length":
        fname = rng.choice(["length", "size"])
        word = rng.choice(_SHORT_WORDS)
        defs = _lines(
            f"def {fname}(text):",
            '    if text == "":',
            "        return 0",
            f"    return 1 + {fname}(text[1:])",
        )
        args = (word,)
        beyond = _call(fname, word[0])
    else:
        fname = rng.choice(["skip_sum", "step_sum"])
        k = rng.randint(5, 8)
        defs = _lines(
            f"def {fname}(n):",
            "    if n <= 0:",
            "        return 0",
            f"    return n + {fname}(n - 2)",
        )
        args = (k,)
        beyond = _call(fname, -2 if k % 2 == 0 else 0)
    call = _call(fname, *args)
    calls, returns, _ = _trace(defs, fname, call)
    names = [_call(fname, *a) for a in calls]
    if _call(fname, *returns[0]) != names[-1] or len(names) < 3:
        raise GenerationError("unexpected call order")
    chain = " → ".join(f"`{c}`" for c in names)
    if rng.random() < 0.75:
        prompt = f"When `{call}` runs, which call is the first to finish and return a value?"
        correct = names[-1]
        distractors = [names[0], beyond, names[-2], names[1], names[-3]]
        why = (
            f"The calls pile up: {chain}. Each one is paused, waiting for the call it made, so "
            f"the base case `{names[-1]}` returns first. Then the paused calls finish in reverse "
            f"order, ending with `{names[0]}`."
        )
    else:
        prompt = f"When `{call}` runs, which call is the last to finish and return a value?"
        correct = names[0]
        distractors = [names[-1], names[-2], names[1], beyond]
        why = (
            f"The calls pile up: {chain}. The base case `{names[-1]}` returns first, then each "
            f"paused call finishes in reverse order, so the very first call, `{names[0]}`, is "
            f"the last to finish."
        )
    return _choice(
        difficulty=EASY,
        prompt=prompt,
        code=_prog(defs, f"print({call})"),
        correct=correct,
        distractors=distractors,
        explanation=why,
        rng=rng,
    )


_COUNT_WORDS = [
    "banana", "letter", "pepper", "coconut", "balloon", "papaya", "bubble",
    "cookie", "noodle", "summer", "rabbit", "giraffe", "parrot", "kitten",
]


@generator(TOPIC, EASY)
def gen_sequence_recursion(rng: random.Random) -> Question:
    """Recursion on a string or list: handle the first item, recurse on the rest (``[1:]``)."""
    shape = rng.choice(["length", "count_char", "list_total", "repeat"])
    if shape == "length":
        fname = rng.choice(["length", "size", "count_chars"])
        word = rng.choice(_WORDS)
        defs = _lines(
            f"def {fname}(text):",
            '    if text == "":',
            "        return 0",
            f"    return 1 + {fname}(text[1:])",
        )
        call = f'{fname}("{word}")'
        n = len(word)
        cands = [n - 1, n + 1, 1, 0]
        why = (
            f"Each call counts 1 for the first character and recurses on the rest (`text[1:]`), "
            f'until the empty string returns 0. "{word}" has {n} characters, so the result is '
            f"{' + '.join(['1'] * n)} + 0 = {n}."
        )
        answer = n
    elif shape == "count_char":
        fname = rng.choice(["count", "count_letter"])
        word = rng.choice(_COUNT_WORDS)
        repeated = sorted({c for c in word if word.count(c) >= 2})
        ch = rng.choice(repeated) if rng.random() < 0.8 else rng.choice(sorted(set(word)))
        defs = _lines(
            f"def {fname}(text, ch):",
            '    if text == "":',
            "        return 0",
            "    if text[0] == ch:",
            f"        return 1 + {fname}(text[1:], ch)",
            f"    return {fname}(text[1:], ch)",
        )
        call = f'{fname}("{word}", "{ch}")'
        answer = word.count(ch)
        cands = [len(word), answer + 1, answer - 1, 1, 0]
        why = (
            f'Every call looks at one letter: it adds 1 when that letter is "{ch}" and adds '
            f'nothing otherwise, then recurses on the rest. "{word}" contains "{ch}" {answer} '
            f"time{'s' if answer != 1 else ''}."
        )
    elif shape == "list_total":
        fname = rng.choice(["total", "add_all"])
        nums = rng.sample(range(1, 10), rng.randint(3, 4))
        cond = rng.choice(["not nums", "len(nums) == 0", "nums == []"])
        defs = _lines(
            f"def {fname}(nums):",
            f"    if {cond}:",
            "        return 0",
            f"    return nums[0] + {fname}(nums[1:])",
        )
        call = f"{fname}({nums})"
        answer = sum(nums)
        cands = [answer - nums[0], answer - nums[-1], nums[0], len(nums), nums[-1]]
        why = (
            f"Each call adds the first item to the total of the rest (`nums[1:]`), until the "
            f"empty list returns 0: {' + '.join(map(str, nums))} + 0 = {answer}."
        )
    else:
        fname = rng.choice(["repeat", "echo"])
        word = rng.choice(["ha", "na", "go", "la", "boo", "yo"])
        k = rng.randint(2, 4)
        defs = _lines(
            f"def {fname}(word, times):",
            "    if times == 0:",
            '        return ""',
            f"    return word + {fname}(word, times - 1)",
        )
        call = f'{fname}("{word}", {k})'
        answer = word * k
        cands = [word * (k - 1), word * (k + 1), f"{word}{k}", " ".join([word] * k), word]
        why = (
            f"Each call adds one copy of \"{word}\" and lowers `times` by 1; after {k} copies "
            f'`times` is 0 and the base case adds the empty string. Result: {answer}.'
        )
        return _output(_prog(defs, f"print({call})"), EASY, cands, why, rng, expect=answer)
    return _output(
        _prog(defs, f"print({call})"), EASY, _nums(cands, answer, rng), why, rng, expect=answer
    )


@generator(TOPIC, EASY)
def gen_which_call(rng: random.Random) -> Question:
    """Which call returns a given value? (Work backwards from the result.)"""
    shape = rng.choice(["sum_to", "factorial", "power", "range_sum"])
    if shape == "sum_to":
        fname = rng.choice(["sum_to", "add_up"])
        k = rng.randint(3, 7)
        setup = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            "        return 0",
            f"    return n + {fname}(n - 1)",
        )
        target = k * (k + 1) // 2
        correct = f"{fname}({k})"
        wrong = [f"{fname}({k + 1})", f"{fname}({k - 1})", f"{fname}({k + 2})"]
        if target <= 30:
            wrong.insert(rng.randint(0, 2), f"{fname}({target})")
        why = (
            f"`{fname}({k})` adds {' + '.join(str(i) for i in range(k, 0, -1))} = {target}. "
            f"The argument is where the adding starts, not the answer."
        )
    elif shape == "factorial":
        fname = rng.choice(["factorial", "fact"])
        k = rng.randint(3, 5)
        setup = _lines(
            f"def {fname}(n):",
            "    if n <= 1:",
            "        return 1",
            f"    return n * {fname}(n - 1)",
        )
        target = math.factorial(k)
        correct = f"{fname}({k})"
        wrong = [f"{fname}({k + 1})", f"{fname}({k - 1})", f"{fname}({k * 2})"]
        if target <= 30:
            wrong.insert(rng.randint(0, 2), f"{fname}({target})")
        why = (
            f"`{fname}({k})` multiplies {' * '.join(str(i) for i in range(k, 0, -1))} = {target}. "
            f"Its neighbours are far off: `{fname}({k - 1})` is {math.factorial(k - 1)} and "
            f"`{fname}({k + 1})` is {math.factorial(k + 1)}."
        )
    elif shape == "power":
        b, e = rng.choice([(2, 3), (2, 5), (3, 2), (3, 4), (4, 3), (5, 2), (5, 3), (2, 6), (10, 2)])
        setup = _lines(
            "def power(base, exp):",
            "    if exp == 0:",
            "        return 1",
            "    return base * power(base, exp - 1)",
        )
        target = b ** e
        correct = f"power({b}, {e})"
        wrong = [f"power({e}, {b})", f"power({b}, {e + 1})", f"power({b}, {e - 1})", f"power({b * e}, 1)"]
        why = (
            f"`power({b}, {e})` multiplies `base` {e} times: {' * '.join([str(b)] * e)} = {target}. "
            f"Order matters: the first argument is the number being multiplied, the second is how "
            f"many times."
        )
    else:
        fname = rng.choice(["add_range", "sum_between"])
        lo = rng.randint(1, 5)
        hi = lo + rng.randint(2, 3)
        setup = _lines(
            f"def {fname}(lo, hi):",
            "    if lo > hi:",
            "        return 0",
            f"    return lo + {fname}(lo + 1, hi)",
        )
        target = sum(range(lo, hi + 1))
        correct = f"{fname}({lo}, {hi})"
        wrong = [
            f"{fname}({lo}, {hi + 1})",
            f"{fname}({lo + 1}, {hi})",
            f"{fname}({lo}, {hi - 1})",
            f"{fname}({lo - 1}, {hi})",
        ]
        why = (
            f"The recursion only stops when `lo > hi`, so `hi` itself is included: "
            f"`{correct}` adds {' + '.join(str(i) for i in range(lo, hi + 1))} = {target}."
        )
    return which_expression_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Using the function above, which call returns `{target}`?",
        setup=setup,
        target=target,
        correct_expr=correct,
        wrong_exprs=wrong,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# MEDIUM
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_missing_base_case(rng: random.Random) -> Question:
    """No base case, a step in the wrong direction, or a check that comes too late: RecursionError."""
    shape = rng.choice(["no_base", "wrong_direction", "same_arg", "base_after"])
    broken = rng.random() < 0.6
    if rng.random() < 0.5:
        fname = rng.choice(["total", "sum_to"])
        op, cond, base, k = "+", "n == 0", 0, rng.randint(3, 6)
        answer, smaller = k * (k + 1) // 2, k * (k - 1) // 2
        chain = " + ".join(str(i) for i in range(k, -1, -1))
    else:
        fname = rng.choice(["fact", "factorial"])
        op, cond, base, k = "*", "n == 1", 1, rng.randint(3, 5)
        answer, smaller = math.factorial(k), math.factorial(k - 1)
        chain = " * ".join(str(i) for i in range(k, 0, -1))
    good_step = f"{fname}(n - 1)"
    head = [f"def {fname}(n):"]
    base_lines = [f"    if {cond}:", f"        return {base}"]
    if shape == "no_base":
        body = [f"    return n {op} {good_step}"] if broken else base_lines + [f"    return n {op} {good_step}"]
    elif shape == "wrong_direction":
        step = f"{fname}(n + 1)" if broken else good_step
        body = base_lines + [f"    return n {op} {step}"]
    elif shape == "same_arg":
        step = f"{fname}(n)" if broken else good_step
        body = base_lines + [f"    return n {op} {step}"]
    else:
        if broken:
            body = [f"    rest = {good_step}"] + base_lines + [f"    return n {op} rest"]
        else:
            body = base_lines + [f"    rest = {good_step}", f"    return n {op} rest"]
    code = _prog(_lines(*head, *body), f"print({fname}({k}))")
    if broken:
        distractors = [answer, "None", base, TYPE_ERROR, smaller]
        if shape == "no_base":
            why = (
                f"`{fname}` has no base case, so every call makes another call "
                f"({fname}({k}), {fname}({k - 1}), ... into negative numbers) and none ever "
                f"returns. Python stops it when the call stack gets too deep: `RecursionError`."
            )
        elif shape == "wrong_direction":
            why = (
                f"The base case waits for `{cond}`, but each call passes `n + 1`, so `n` grows "
                f"{k}, {k + 1}, {k + 2}, ... and never reaches it. The calls never stop, so "
                f"Python raises `RecursionError`."
            )
        elif shape == "same_arg":
            why = (
                f"`{fname}(n)` calls itself with the *same* `n`, so the problem never gets "
                f"smaller and `{cond}` never becomes true: `RecursionError`."
            )
        else:
            why = (
                f"The recursive call is the first line, *before* the base case is checked, so "
                f"even `{fname}({base})` goes on to call `{fname}({base - 1})`. The check is never "
                f"reached and Python raises `RecursionError`."
            )
    else:
        distractors = [RECURSION_ERROR, smaller, "None", base]
        why = (
            f"`n` drops by 1 each call, so the base case `{cond}` is reached and the recursion "
            f"stops. The result is {chain} = {answer}."
        )
    return _output(
        code, MEDIUM, _nums(distractors, answer, rng), why, rng,
        prompt=PRINT_OR_ERROR, allow_error=True, expect=RECURSION_ERROR if broken else answer,
    )


@generator(TOPIC, MEDIUM)
def gen_call_count(rng: random.Random) -> Question:
    """How many calls does a linear recursion make? (Don't forget the base-case call.)"""
    shape = rng.choice(["to_zero", "to_one", "step_two", "string", "halving", "list"])
    if shape == "to_zero":
        fname = rng.choice(["total", "sum_to"])
        k = rng.randint(3, 8)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            "        return 0",
            f"    return n + {fname}(n - 1)",
        )
        args = (k,)
    elif shape == "to_one":
        fname = rng.choice(["fact", "factorial"])
        k = rng.randint(3, 7)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 1:",
            "        return 1",
            f"    return n * {fname}(n - 1)",
        )
        args = (k,)
    elif shape == "step_two":
        fname = rng.choice(["skip_sum", "step_sum"])
        k = rng.randint(5, 10)
        defs = _lines(
            f"def {fname}(n):",
            "    if n <= 0:",
            "        return 0",
            f"    return n + {fname}(n - 2)",
        )
        args = (k,)
    elif shape == "string":
        fname = rng.choice(["length", "size"])
        word = rng.choice(_WORDS)
        defs = _lines(
            f"def {fname}(text):",
            '    if text == "":',
            "        return 0",
            f"    return 1 + {fname}(text[1:])",
        )
        args = (word,)
        k = len(word)
    elif shape == "halving":
        fname = rng.choice(["halvings", "count_halves"])
        k = rng.randint(5, 40)
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            "        return 0",
            f"    return 1 + {fname}(n // 2)",
        )
        args = (k,)
    else:
        fname = rng.choice(["total", "add_all"])
        nums = rng.sample(range(1, 10), rng.randint(3, 5))
        defs = _lines(
            f"def {fname}(nums):",
            "    if not nums:",
            "        return 0",
            f"    return nums[0] + {fname}(nums[1:])",
        )
        args = (nums,)
        k = len(nums)
    call = _call(fname, *args)
    calls, _, _ = _trace(defs, fname, call)
    count = len(calls)
    names = [_call(fname, *a) for a in calls]
    chain = ", ".join(f"`{c}`" for c in names) if count <= 7 else (
        ", ".join(f"`{c}`" for c in names[:3]) + ", ..., " + f"`{names[-1]}`"
    )
    why = (
        f"The calls are {chain}: {count} in total. Count both the first call and the "
        f"base-case call `{names[-1]}`, which still runs even though it doesn't recurse."
    )
    cands = [count - 1, count + 1, k, k - 1, k + 1, count - 2, count * 2]
    return _choice(
        difficulty=MEDIUM,
        prompt=f"How many times is `{fname}` called in total, counting the first call `{call}`?",
        code=_prog(defs, f"print({call})"),
        correct=str(count),
        distractors=_nums([c for c in cands if c > 0], count, rng),
        explanation=why,
        rng=rng,
    )


def _doubled(s: str) -> str:
    return "".join(c * 2 for c in s)


@generator(TOPIC, MEDIUM)
def gen_string_transform(rng: random.Random) -> Question:
    """Trace a recursive string function: where the first/last letter goes decides the result."""
    shape = rng.choice(["rev_back", "rev_front", "copy", "double", "skip", "dashes", "mirror"])
    fname = rng.choice(["mystery", "transform", "process", "rebuild"])
    word = rng.choice(_SHORT_WORDS if shape in ("double", "mirror", "dashes") else _WORDS)
    rev = word[::-1]
    base = ['    if text == "":', '        return ""']
    if shape == "rev_back":
        body = base + [f"    return {fname}(text[1:]) + text[0]"]
        distractors = [word, word[1:] + word[0], rev[:-1], word[-1] + word[:-1], word[0]]
        why = (
            f"Each call puts its first letter *after* the processed rest. So \"{word[0]}\" ends "
            f"up last, \"{word[1]}\" second to last, and so on: the word comes out reversed, {rev}."
        )
    elif shape == "rev_front":
        body = base + [f"    return text[-1] + {fname}(text[:-1])"]
        distractors = [word, word[-1] + word[:-1], rev[1:], word[-1] * len(word), word[1:] + word[0]]
        why = (
            f"Each call takes the *last* letter (`text[-1]`) first and recurses on everything "
            f"before it (`text[:-1]`). Taking letters from the back one by one builds {rev}."
        )
    elif shape == "copy":
        body = base + [f"    return text[0] + {fname}(text[1:])"]
        distractors = [rev, word[1:] + word[0], word[0], word[0] * len(word), word[:-1]]
        why = (
            "Each call keeps its first letter in front of the processed rest, so the letters stay "
            f"in their original order and the result is just {word}. Recursion alone doesn't "
            "reverse anything; the order of the `+` does."
        )
    elif shape == "double":
        body = base + [f"    return text[0] * 2 + {fname}(text[1:])"]
        distractors = [word * 2, _doubled(rev), word[0] * 2 + word[1:], _doubled(word)[:-2], word + rev]
        why = (
            f"`text[0] * 2` repeats just the first letter, then the rest is processed the same "
            f"way. Every letter is doubled in place: {_doubled(word)}."
        )
    elif shape == "skip":
        body = base + [f"    return text[0] + {fname}(text[2:])"]
        distractors = [word[1::2], rev[::2], word[0], word[:-1:2] if len(word) % 2 else word[:-2:2] + word[-2], word]
        why = (
            f"`text[2:]` drops two letters at a time, so only every other letter (positions 0, 2, "
            f"4, ...) is kept: {word[::2]}. Slicing past the end just gives \"\", which hits the "
            f"base case."
        )
    elif shape == "dashes":
        base = ["    if len(text) <= 1:", "        return text"]
        body = base + [f'    return text[0] + "-" + {fname}(text[1:])']
        dashed = "-".join(word)
        distractors = [dashed + "-", "-".join(rev), word[0] + "-" + word[1:], "-" + dashed, word]
        why = (
            "Each call adds its first letter and a dash, then the rest. The base case returns a "
            f"single letter on its own, so there is no dash at the end: {dashed}."
        )
    else:
        body = base + [f"    return text[0] + {fname}(text[1:]) + text[0]"]
        distractors = [word * 2, rev + word, word + rev[1:], word, rev * 2]
        why = (
            "Each call wraps the processed rest with its first letter on *both* sides, so the "
            f"letters appear once going in and again (in reverse) coming out: {word + rev}."
        )
    expect = {
        "rev_back": rev, "rev_front": rev, "copy": word, "double": _doubled(word),
        "skip": word[::2], "dashes": "-".join(word), "mirror": word + rev,
    }[shape]
    code = _prog(_lines(f"def {fname}(text):", *body), f'print({fname}("{word}"))')
    return _output(code, MEDIUM, distractors, why, rng, expect=expect)


@generator(TOPIC, MEDIUM)
def gen_digit_recursion(rng: random.Random) -> Question:
    """``n % 10`` peels off the last digit and ``n // 10`` drops it."""
    shape = rng.choice(["digit_sum", "count_digits", "print_reversed", "print_forward"])
    if shape in ("digit_sum", "count_digits"):
        ndig = rng.randint(3, 4) if shape == "digit_sum" else rng.randint(3, 6)
        digits = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(ndig - 1)]
        n = int("".join(map(str, digits)))
        fname = rng.choice(["mystery", "crunch", "process"])
        if shape == "digit_sum":
            defs = _lines(
                f"def {fname}(n):",
                "    if n < 10:",
                "        return n",
                f"    return n % 10 + {fname}(n // 10)",
            )
            answer = sum(digits)
            cands = [n % 10, sum(digits[1:]), sum(digits[:-1]), ndig, n // 10, answer + 1]
            why = (
                f"`n % 10` is the last digit and `n // 10` removes it, so each call adds one digit "
                f"and passes the rest on, until a single digit is left: "
                f"{' + '.join(map(str, digits[::-1]))} = {answer}."
            )
        else:
            cond, base_val = rng.choice([("n < 10", 1), ("n < 10", 0), ("n == 0", 0)])
            defs = _lines(
                f"def {fname}(n):",
                f"    if {cond}:",
                f"        return {base_val}",
                f"    return 1 + {fname}(n // 10)",
            )
            steps = [n // 10 ** i for i in range(ndig + 1)]
            if cond == "n == 0":
                answer = ndig
                why = (
                    f"Each call adds 1 and drops the last digit with `// 10`: "
                    f"{', '.join(map(str, steps))}. Every call except the last one (with 0) adds 1, "
                    f"so the result is {answer}, the number of digits."
                )
            else:
                answer = ndig - 1 + base_val
                steps = steps[:-1]
                why = (
                    f"Each call adds 1 and drops the last digit with `// 10`: "
                    f"{', '.join(map(str, steps))}. That is {ndig - 1} recursive steps, and the "
                    f"base case (a single digit) adds {base_val}, so the result is {answer}."
                )
            cands = [ndig if answer != ndig else ndig - 1, answer + 1, answer - 1, sum(digits), n % 10, n // 10]
        if rng.random() < 0.5:
            code = _prog(defs, f"result = {fname}({n})")
            value = _value_of(code, "result")
            if value != answer:
                raise GenerationError(f"expected {answer}, got {value}")
            return _choice(
                difficulty=MEDIUM,
                prompt=VALUE_OF_RESULT,
                code=code,
                correct=str(value),
                distractors=_nums(cands, value, rng),
                explanation=why,
                rng=rng,
            )
        return _output(
            _prog(defs, f"print({fname}({n}))"), MEDIUM, _nums(cands, answer, rng), why, rng,
            expect=answer,
        )
    ndig = rng.randint(3, 4)
    digits = rng.sample(range(1, 10), ndig)
    n = int("".join(map(str, digits)))
    s, r = str(n), str(n)[::-1]
    if shape == "print_reversed":
        fname = rng.choice(["show", "emit", "display"])
        defs = _lines(
            f"def {fname}(n):",
            "    if n < 10:",
            "        print(n)",
            "        return",
            '    print(n % 10, end="")',
            f"    {fname}(n // 10)",
        )
        distractors = [s, " ".join(r), r[:-1], r[1:], _seq(r)]
        why = (
            f"Each call prints its *last* digit (`n % 10`) before recursing on the rest "
            f"(`n // 10`), so the digits come out from right to left: {r}."
        )
    else:
        fname = rng.choice(["show", "emit", "display"])
        defs = _lines(
            f"def {fname}(n):",
            "    if n >= 10:",
            f"        {fname}(n // 10)",
            '    print(n % 10, end=" ")',
        )
        distractors = [" ".join(r), s, " ".join(s[1:]), " ".join(s[:-1]), s[-1]]
        why = (
            f"Each call first recurses on the number without its last digit, and only prints "
            f"`n % 10` after that call returns. So the leftmost digit is printed first: "
            f"{' '.join(s)}."
        )
    expect = r if shape == "print_reversed" else " ".join(s)
    return _output(_prog(defs, f"{fname}({n})"), MEDIUM, distractors, why, rng, expect=expect)


@generator(TOPIC, MEDIUM)
def gen_binary(rng: random.Random) -> Question:
    """Binary by recursion: the ORDER of 'recurse' and 'add n % 2' decides the bit order."""
    shape = rng.choice(["return_after", "return_before", "print_after", "print_before"])
    n = rng.choice([v for v in range(5, 41) if bin(v)[2:] != bin(v)[:1:-1]])
    bits = bin(n)[2:]
    rev = bits[::-1]
    if shape == "return_after":
        fname = rng.choice(["to_binary", "binary"])
        defs = _lines(
            f"def {fname}(n):",
            "    if n < 2:",
            "        return str(n)",
            f"    return {fname}(n // 2) + str(n % 2)",
        )
        main, answer, other = f"print({fname}({n}))", bits, rev
    elif shape == "return_before":
        fname = rng.choice(["bits", "convert"])
        defs = _lines(
            f"def {fname}(n):",
            "    if n < 2:",
            "        return str(n)",
            f"    return str(n % 2) + {fname}(n // 2)",
        )
        main, answer, other = f"print({fname}({n}))", rev, bits
    elif shape == "print_after":
        fname = rng.choice(["show_bits", "print_binary"])
        defs = _lines(
            f"def {fname}(n):",
            "    if n >= 2:",
            f"        {fname}(n // 2)",
            '    print(n % 2, end="")',
        )
        main, answer, other = f"{fname}({n})", bits, rev
    else:
        fname = rng.choice(["show_bits", "print_bits"])
        defs = _lines(
            f"def {fname}(n):",
            '    print(n % 2, end="")',
            "    if n >= 2:",
            f"        {fname}(n // 2)",
        )
        main, answer, other = f"{fname}({n})", rev, bits
    distractors = [other, answer[1:], answer[:-1], answer + "0", bin(n - 1)[2:], other[1:]]
    remainders = []
    m = n
    while m >= 2:
        remainders.append(f"{m} % 2 = {m % 2}")
        m //= 2
    if answer == bits:
        order = (
            "Each call's remainder goes *after* the deeper call's digits, so the last digit "
            f"found ({m}, from the base case) comes first, giving {bits}, which is {n} in binary."
        )
    else:
        order = (
            "Each call's remainder goes *before* the deeper call's digits, so the digits come "
            f"out in the order they are found: {rev}. That is {n} in binary ({bits}) backwards."
        )
    why = f"The remainders are {', '.join(remainders)}, and the base case gives {m}. {order}"
    return _output(_prog(defs, main), MEDIUM, distractors, why, rng, expect=answer)


def _gcd_pair(rng: random.Random, max_calls: int = 99):
    for _ in range(200):
        g = rng.randint(2, 9)
        p, q = rng.sample(range(2, 10), 2)
        if math.gcd(p, q) != 1 or g * max(p, q) > 80:
            continue
        a, b = g * p, g * q
        calls, x, y = 1, a, b
        while y:
            x, y = y, x % y
            calls += 1
        if calls <= max_calls:
            return a, b, g
    raise GenerationError("no gcd pair")


@generator(TOPIC, MEDIUM)
def gen_gcd(rng: random.Random) -> Question:
    """Euclid's algorithm: gcd(a, b) = gcd(b, a % b) until b is 0."""
    shape = rng.choice(["euclid", "trace", "subtract"])
    a, b, g = _gcd_pair(rng, max_calls=5 if shape == "trace" else 99)
    small_div = max([d for d in range(2, g) if g % d == 0], default=1)
    if shape == "euclid":
        defs = _lines(
            "def gcd(a, b):",
            "    if b == 0:",
            "        return a",
            "    return gcd(b, a % b)",
        )
        pairs = []
        x, y = a, b
        while True:
            pairs.append(f"`gcd({x}, {y})`")
            if y == 0:
                break
            x, y = y, x % y
        cands = [min(a, b), small_div, a % b, b % a, abs(a - b), g * 2, 1]
        why = (
            f"The calls go {' → '.join(pairs)}. When `b` is 0 the base case returns `a`, so "
            f"the answer is {g}."
        )
        return _output(
            _prog(defs, f"print(gcd({a}, {b}))"), MEDIUM, _nums([c for c in cands if c], g, rng),
            why, rng, expect=g,
        )
    if shape == "subtract":
        defs = _lines(
            "def gcd(a, b):",
            "    if a == b:",
            "        return a",
            "    if a > b:",
            "        return gcd(a - b, b)",
            "    return gcd(a, b - a)",
        )
        cands = [min(a, b), abs(a - b), small_div, g * 2, 1, max(a, b) % min(a, b)]
        why = (
            f"Each call subtracts the smaller number from the bigger one; a common divisor of "
            f"{a} and {b} also divides their difference. The numbers shrink until they are "
            f"equal, at {g}, which is returned."
        )
        return _output(
            _prog(defs, f"print(gcd({a}, {b}))"), MEDIUM, _nums([c for c in cands if c], g, rng),
            why, rng, expect=g,
        )
    defs = _lines(
        "def gcd(a, b):",
        "    print(a, b)",
        "    if b == 0:",
        "        return a",
        "    return gcd(b, a % b)",
    )
    pairs = []
    x, y = a, b
    while True:
        pairs.append(f"{x} {y}")
        if y == 0:
            break
        x, y = y, x % y
    distractors = [
        _seq(pairs[:-1] + [g]),
        _seq(pairs[::-1] + [g]),
        _seq([g] + pairs),
        _seq(pairs + ["0"]),
        _seq(pairs),
    ]
    why = (
        "Every call prints its arguments first, including the last call where `b` is 0. That "
        f"call returns `a` ({g}) without recursing, and the outer `print` shows it at the end."
    )
    if a < b:
        why += f" Note the first step just swaps them: {a} % {b} is {a}."
    code = _prog(defs, f"print(gcd({a}, {b}))")
    return _output(code, MEDIUM, distractors, why, rng, expect=_seq(pairs + [g]))


@generator(TOPIC, MEDIUM)
def gen_mutual_recursion(rng: random.Random) -> Question:
    """Two functions that call each other, handing a shrinking ``n`` back and forth."""
    shape = rng.choice(["even_odd", "even_odd", "ping_pong", "take_skip"])
    if shape == "even_odd":
        f1 = _lines(
            "def is_even(n):",
            "    if n == 0:",
            "        return True",
            "    return is_odd(n - 1)",
        )
        f2 = _lines(
            "def is_odd(n):",
            "    if n == 0:",
            "        return False",
            "    return is_even(n - 1)",
        )
        fa, fb = rng.choice([("is_even", "is_odd"), ("is_odd", "is_even"), ("is_even", "is_even"), ("is_odd", "is_odd")])
        a, b = rng.randint(2, 7), rng.randint(2, 7)
        while fa == fb and a == b:
            b = rng.randint(2, 7)

        def val(f, k):
            return (k % 2 == 0) == (f == "is_even")

        va, vb = val(fa, a), val(fb, b)
        distractors = [f"{not va} {vb}", f"{va} {not vb}", f"{not va} {not vb}", RECURSION_ERROR]
        code = _prog(f1, f2, f"print({fa}({a}), {fb}({b}))")
        expect = f"{va} {vb}"

        def land(f, k):
            other = "is_odd" if f == "is_even" else "is_even"
            return f if k % 2 == 0 else other

        why = (
            f"Each call subtracts 1 and switches to the other function. `{fa}({a})` switches {a} "
            f"times and hits 0 inside `{land(fa, a)}`, which returns {val(land(fa, a), 0)}; "
            f"`{fb}({b})` hits 0 inside `{land(fb, b)}`, which returns {val(land(fb, b), 0)}."
        )
        return _output(code, MEDIUM, distractors, why, rng, expect=expect)
    if shape == "ping_pong":
        w1, w2 = rng.choice([("ping", "pong"), ("tick", "tock"), ("left", "right"), ("hip", "hop")])
        k = rng.randint(3, 5)
        start, other = (w1, w2) if rng.random() < 0.7 else (w2, w1)
        f1 = _lines(
            f"def {w1}(n):",
            "    if n > 0:",
            f'        print("{w1}", n)',
            f"        {w2}(n - 1)",
        )
        f2 = _lines(
            f"def {w2}(n):",
            "    if n > 0:",
            f'        print("{w2}", n)',
            f"        {w1}(n - 1)",
        )
        code = _prog(f1, f2, f"{start}({k})")
        names = [start if i % 2 == 0 else other for i in range(k)]
        nums = list(range(k, 0, -1))
        correct = [f"{w} {v}" for w, v in zip(names, nums)]
        distractors = [
            _seq(f"{start} {v}" for v in nums),
            _seq(f"{w} {v}" for w, v in zip([other if w == start else start for w in names], nums)),
            _seq(correct + [f"{start if k % 2 == 0 else other} 0"]),
            _seq(correct[::-1]),
            _seq(correct[:-1]),
        ]
        why = (
            f"`{start}({k})` prints, then hands `n - 1` to the *other* function, which prints and "
            f"hands it back. They alternate until `n` is 0, where `if n > 0` is false and "
            f"nothing more is printed."
        )
        return _output(code, MEDIUM, distractors, why, rng, expect=_seq(correct))
    t, s = rng.choice([("take", "skip"), ("grab", "skip"), ("add", "pass_on")])
    f1 = _lines(
        f"def {t}(n):",
        "    if n <= 0:",
        "        return 0",
        f"    return n + {s}(n - 1)",
    )
    f2 = _lines(
        f"def {s}(n):",
        "    if n <= 0:",
        "        return 0",
        f"    return {t}(n - 1)",
    )
    k = rng.randint(4, 8)
    start = t if rng.random() < 0.6 else s
    kept = list(range(k, 0, -2)) if start == t else list(range(k - 1, 0, -2))
    answer = sum(kept)
    other_sum = k * (k + 1) // 2 - answer
    code = _prog(f1, f2, f"print({start}({k}))")
    cands = [k * (k + 1) // 2, other_sum, answer - kept[-1], k, answer + k]
    why = (
        f"`{t}` adds its `n` and passes `n - 1` to `{s}`, which adds nothing and passes "
        f"`n - 1` back. So only every other number is added: "
        f"{' + '.join(map(str, kept))} = {answer}."
    )
    return _output(code, MEDIUM, _nums(cands, answer, rng), why, rng, expect=answer)


@generator(TOPIC, MEDIUM)
def gen_complete_recursive_case(rng: random.Random) -> Question:
    """Complete the recursive case: combine this step with a call on a SMALLER problem."""
    shape = rng.choice(["sum_to", "factorial", "power", "reverse", "length", "list_total"])
    if shape == "sum_to":
        k = rng.randint(3, 6)
        defs = _lines("def sum_to(n):", "    if n == 0:", "        return 0", f"    return {BLANK}")
        main = f"print(sum_to({k}))"
        correct = "n + sum_to(n - 1)"
        candidates = [
            "n + sum_to(n)", "sum_to(n - 1)", "n * sum_to(n - 1)", "n + (n - 1)",
            "n + sum_to(n + 1)", "sum_to(n - 1) + 1",
        ]
        why = (
            "The sum up to `n` is `n` plus the sum up to `n - 1`, and the call must get "
            "smaller so it reaches the base case. `sum_to(n)` never shrinks (`RecursionError`), "
            "and `sum_to(n - 1)` alone never adds anything but 0."
        )
    elif shape == "factorial":
        k = rng.randint(4, 5)
        defs = _lines("def factorial(n):", "    if n <= 1:", "        return 1", f"    return {BLANK}")
        main = f"print(factorial({k}))"
        correct = "n * factorial(n - 1)"
        candidates = [
            "n * factorial(n)", "factorial(n - 1)", "n + factorial(n - 1)",
            "n * (n - 1)", "n * factorial(n + 1)",
        ]
        why = (
            f"{k}! = {k} * {k - 1}!, so each call multiplies `n` by the factorial of `n - 1`. "
            "`n * (n - 1)` stops after one step, and `factorial(n)` never gets closer to the base "
            "case."
        )
    elif shape == "power":
        b, e = rng.choice([(2, 3), (2, 4), (3, 3), (3, 2), (5, 2), (2, 5), (4, 3)])
        defs = _lines(
            "def power(base, exp):", "    if exp == 0:", "        return 1", f"    return {BLANK}"
        )
        main = f"print(power({b}, {e}))"
        correct = "base * power(base, exp - 1)"
        candidates = [
            "base * power(base, exp)", "power(base, exp - 1)", "exp * power(base, exp - 1)",
            "base * exp", "base + power(base, exp - 1)",
        ]
        why = (
            f"`base ** exp` is `base` times `base ** (exp - 1)`, so each call multiplies by `base` "
            f"once and lowers `exp` until it is 0. For power({b}, {e}) that is "
            f"{' * '.join([str(b)] * e)} = {b ** e}."
        )
    elif shape == "reverse":
        word = rng.choice(_WORDS)
        defs = _lines(
            "def reverse(text):", '    if text == "":', '        return ""', f"    return {BLANK}"
        )
        main = f'print(reverse("{word}"))'
        correct = "reverse(text[1:]) + text[0]"
        candidates = [
            "text[0] + reverse(text[1:])", "reverse(text[1:])", "reverse(text) + text[0]",
            "text[-1] + reverse(text[1:])", "reverse(text[1:]) + text[1]",
        ]
        why = (
            "Reverse the rest of the string, then put the first letter at the *end*. Putting "
            "`text[0]` in front keeps the original order, and `reverse(text)` never gets shorter."
        )
    elif shape == "length":
        word = rng.choice(_WORDS)
        defs = _lines(
            "def length(text):", '    if text == "":', "        return 0", f"    return {BLANK}"
        )
        main = f'print(length("{word}"))'
        correct = "1 + length(text[1:])"
        candidates = [
            "length(text[1:])", "1 + length(text)", "text[0] + length(text[1:])",
            "1 + length(text[2:])", "length(text[1:]) - 1",
        ]
        why = (
            "Count 1 for the first character, plus the length of the rest (`text[1:]`). Without "
            "the `1 +` nothing is ever counted, and `length(text)` never gets shorter."
        )
    else:
        nums = rng.sample(range(1, 10), rng.randint(3, 4))
        defs = _lines(
            "def total(nums):", "    if not nums:", "        return 0", f"    return {BLANK}"
        )
        main = f"print(total({nums}))"
        correct = "nums[0] + total(nums[1:])"
        candidates = [
            "total(nums[1:])", "nums[0] + total(nums)", "nums + total(nums[1:])",
            "nums[1] + total(nums[1:])", "nums[0] + nums[1]",
        ]
        why = (
            "Add the first item to the total of the rest of the list (`nums[1:]`), which is one "
            "item shorter each time until the empty list returns 0."
        )
    return _blank_question(
        difficulty=MEDIUM,
        template=_prog(defs, main),
        correct=correct,
        candidates=candidates,
        prompt="Which expression completes the recursive case so the code prints `{target}`?",
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# HARD
# ==========================================================================


def _order_defs(fname: str, mode: str, one_line: bool) -> str:
    pr = 'print(n, end=" ")' if one_line else "print(n)"
    lines = [f"def {fname}(n):", "    if n == 0:", "        return"]
    if mode in ("before", "both"):
        lines.append("    " + pr)
    lines.append(f"    {fname}(n - 1)")
    if mode in ("after", "both"):
        lines.append("    " + pr)
    return _lines(*lines)


@generator(TOPIC, HARD)
def gen_print_order(rng: random.Random) -> Question:
    """Printing AFTER the recursive call happens on the way back up, in reverse order."""
    shape = rng.choice(["after", "after", "both", "in_out", "spell"])
    if shape in ("after", "both"):
        fname = rng.choice(["show", "display", "echo"])
        one_line = shape == "both" or rng.random() < 0.4
        k = rng.randint(3, 5) if shape == "after" else rng.randint(3, 4)
        sep = " " if one_line else "\n"

        def build(mode):
            return _prog(_order_defs(fname, mode, one_line), f"{fname}({k})")

        code = build(shape)
        desc = list(range(k, 0, -1))
        asc = desc[::-1]
        if shape == "after":
            distractors = [
                _run(build("before")),
                _seq([0] + asc, sep),
                _seq(asc[:-1], sep),
                _seq(desc + [0], sep),
                _run(build("both")),
            ]
            why = (
                f"Each call makes its recursive call *before* printing, so nothing is printed on "
                f"the way down to `{fname}(0)`. The prints happen as the calls return, deepest "
                f"first: `{fname}(1)` prints first and `{fname}({k})` prints last."
            )
        else:
            distractors = [
                _seq(desc + desc, sep),
                _seq([v for v in desc for _ in (0, 1)], sep),
                _seq(asc + desc, sep),
                _seq(desc + [0] + asc, sep),
                _seq(desc, sep),
            ]
            why = (
                f"Each call prints `n` once on the way down (before its recursive call) and again "
                f"on the way back up (after the call returns). The way back up visits the calls "
                f"in reverse, so you get {_seq(desc, ' ')} and then {_seq(asc, ' ')}."
            )
        expect = _seq(asc, sep) if shape == "after" else _seq(desc + asc, sep)
        return _output(code, HARD, distractors, why, rng, expect=expect)
    if shape == "in_out":
        a, b = rng.choice([("in", "out"), ("down", "up"), ("enter", "exit"), ("start", "end"), ("open", "close")])
        fname = rng.choice(["visit", "explore", "dive"])
        k = rng.randint(2, 3)
        base_msg = rng.choice(["base", "bottom"]) if k == 2 and rng.random() < 0.6 else None
        base_lines = [f'        print("{base_msg}")'] if base_msg else []
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            *base_lines,
            "        return",
            f'    print("{a}", n)',
            f"    {fname}(n - 1)",
            f'    print("{b}", n)',
        )
        desc = list(range(k, 0, -1))
        ins = [f"{a} {i}" for i in desc]
        outs = [f"{b} {i}" for i in desc[::-1]]
        mid = [base_msg] if base_msg else []
        distractors = [
            _seq([x for i in desc for x in (f"{a} {i}", f"{b} {i}")] + mid),
            _seq(ins + mid + outs[::-1]),
            _seq(ins + outs + mid),
            _seq(ins[::-1] + mid + outs),
            _seq(mid + ins + outs),
        ]
        why = (
            f"Each call prints \"{a}\" and then waits for its recursive call to finish before it "
            f"prints \"{b}\". So all the \"{a}\" lines come first ({k} down to 1), and the "
            f"\"{b}\" lines appear as the calls return, innermost first (1 up to {k})."
        )
        expect = _seq(ins + mid + outs)
        return _output(_prog(defs, f"{fname}({k})"), HARD, distractors, why, rng, expect=expect)
    fname = rng.choice(["spell", "write", "show_letters"])
    word = rng.choice(_WORDS)
    mode = rng.choice(["after", "after", "both"])

    def spell(m):
        lines = [f"def {fname}(text):", '    if text == "":', "        return"]
        if m in ("before", "both"):
            lines.append('    print(text[0], end="")')
        lines.append(f"    {fname}(text[1:])")
        if m in ("after", "both"):
            lines.append('    print(text[0], end="")')
        return _prog(_lines(*lines), f'{fname}("{word}")')

    code = spell(mode)
    rev = word[::-1]
    if mode == "after":
        distractors = [word, rev[1:], word[1:] + word[0], " ".join(rev), word + rev]
        why = (
            "Each call prints its first letter only *after* the call on the rest of the string "
            f"returns. The deepest call (the last letter) prints first, so the word comes out "
            f"backwards: {rev}."
        )
    else:
        distractors = [word + word, rev + word, word + rev[1:], word, rev]
        why = (
            "Each call prints its first letter on the way down and again on the way back up. "
            f"Going down gives {word}; coming back up visits the calls in reverse, giving {rev}."
        )
    expect = rev if mode == "after" else word + rev
    return _output(code, HARD, distractors, why, rng, expect=expect)


@generator(TOPIC, HARD)
def gen_unwinding_values(rng: random.Random) -> Question:
    """Values printed after the recursive call appear as the stack unwinds, smallest first."""
    shape = rng.choice(["sum", "product", "double"])
    show_n = rng.random() < 0.35
    final = rng.random() < 0.65
    if shape == "sum":
        fname = rng.choice(["total", "sum_to", "add_up"])
        base_cond, base_val, expr = "n == 0", 0, f"n + {fname}(n - 1)"
        lo = 1

        def f(i):
            return i * (i + 1) // 2
    elif shape == "product":
        fname = rng.choice(["fact", "factorial"])
        base_cond, base_val, expr = "n == 1", 1, f"n * {fname}(n - 1)"
        lo = 2
        f = math.factorial
    else:
        fname = rng.choice(["grow", "doubling"])
        base_cond, base_val, expr = "n == 0", 1, f"2 * {fname}(n - 1)"
        lo = 1

        def f(i):
            return 2 ** i
    k = lo + rng.randint(2, 3)
    if not final:
        k = lo + rng.randint(2, 4)
    pr = "print(n, result)" if show_n else "print(result)"
    defs = _lines(
        f"def {fname}(n):",
        f"    if {base_cond}:",
        f"        return {base_val}",
        f"    result = {expr}",
        f"    {pr}",
        "    return result",
    )
    main = f"print({fname}({k}))" if final else f"{fname}({k})"
    code = _prog(defs, main)
    levels = list(range(lo, k + 1))
    printed = [f"{i} {f(i)}" if show_n else str(f(i)) for i in levels]
    tail = [str(f(k))] if final else []
    other_tail = [] if final else [str(f(k))]
    base_line = [f"{lo - 1} {base_val}" if show_n else str(base_val)]
    distractors = [
        _seq(printed[::-1] + tail),
        _seq(base_line + printed + tail),
        _seq(printed + other_tail),
        _seq([str(i) for i in levels] + tail) if not show_n else _seq([f"{i} {i}" for i in levels] + tail),
        _seq(printed[-1:] + tail),
        _seq(printed[::-1] + other_tail),
    ]
    why = (
        f"`print` comes *after* the recursive call, so nothing is printed on the way down. "
        f"`{fname}({lo})` is the first call to get its result back, so it prints first "
        f"({f(lo)}), then each waiting call prints its own result on the way back up, ending "
        f"with `{fname}({k})` ({f(k)})."
    )
    if final:
        why += " The last line is the outer `print` showing the returned value."
    return _output(code, HARD, distractors, why, rng, expect=_seq(printed + tail))


def _flatten(items) -> list:
    out = []
    for x in items:
        if isinstance(x, list):
            out.extend(_flatten(x))
        else:
            out.append(x)
    return out


def _depth(items) -> int:
    return 1 + max([_depth(x) for x in items if isinstance(x, list)], default=0)


def _with_level(items, level: int) -> list:
    """(number, nesting level) pairs in reading order; the outer list is ``level``."""
    out = []
    for x in items:
        if isinstance(x, list):
            out.extend(_with_level(x, level + 1))
        else:
            out.append((x, level))
    return out


def _rand_nested(rng: random.Random, need_deep: bool) -> list:
    def item(depth):
        if depth < 3 and rng.random() < (0.5 if depth == 1 else 0.35):
            return [item(depth + 1) for _ in range(rng.randint(1, 3))]
        return rng.randint(1, 9)

    for _ in range(300):
        top = [item(1) for _ in range(rng.randint(3, 4))]
        flat = _flatten(top)
        if not any(isinstance(x, list) for x in top) or not any(isinstance(x, int) for x in top):
            continue
        if not 4 <= len(flat) <= 8 or len(repr(top)) > 40:
            continue
        if need_deep and _depth(top) < 3:
            continue
        return top
    raise GenerationError("no nested list")


@generator(TOPIC, HARD)
def gen_nested_list(rng: random.Random) -> Question:
    """Recursion handles lists inside lists to any depth."""
    shape = rng.choice(["weighted", "sum_slice", "count_lists", "depth", "flatten"])
    data = _rand_nested(rng, need_deep=shape in ("flatten", "depth") or rng.random() < 0.5)
    flat = _flatten(data)
    top_ints = [x for x in data if isinstance(x, int)]
    shallow = [x for x in data if isinstance(x, int)] + [
        y for x in data if isinstance(x, list) for y in x if isinstance(y, int)
    ]
    n_lists = repr(data).count("[") - 1
    if shape == "weighted":
        fname = rng.choice(["weighted", "depth_sum"])
        defs = _lines(
            f"def {fname}(items, level):",
            "    total = 0",
            "    for item in items:",
            "        if isinstance(item, list):",
            f"            total += {fname}(item, level + 1)",
            "        else:",
            "            total += item * level",
            "    return total",
        )
        pairs = _with_level(data, 1)
        answer = sum(v * d for v, d in pairs)
        one_level = sum(v * min(d, 2) for v, d in pairs)
        from_zero = sum(v * (d - 1) for v, d in pairs)
        cands = [sum(flat), one_level, from_zero, TYPE_ERROR, sum(top_ints), answer + sum(top_ints)]
        why = (
            "Each number is multiplied by the `level` of the list it sits in, and every recursive "
            "call into an inner list passes `level + 1`. So the result is "
            + " + ".join(f"{v}*{d}" for v, d in pairs)
            + f" = {answer}."
        )
    elif shape == "sum_slice":
        fname = rng.choice(["nested_sum", "deep_sum"])
        defs = _lines(
            f"def {fname}(items):",
            "    if not items:",
            "        return 0",
            "    first = items[0]",
            "    if isinstance(first, list):",
            f"        return {fname}(first) + {fname}(items[1:])",
            f"    return first + {fname}(items[1:])",
        )
        answer = sum(flat)
        cands = [sum(top_ints), sum(shallow), TYPE_ERROR, len(flat), sum(flat) - flat[-1]]
        why = (
            "When the first item is a list, the function makes *two* recursive calls: one into "
            "that inner list and one on the rest. Every number at every depth is reached: "
            f"{' + '.join(map(str, flat))} = {answer}."
        )
    elif shape == "count_lists":
        fname = rng.choice(["count_lists", "count_boxes"])
        defs = _lines(
            f"def {fname}(items):",
            "    count = 1",
            "    for item in items:",
            "        if isinstance(item, list):",
            f"            count += {fname}(item)",
            "    return count",
        )
        answer = n_lists + 1
        top_lists = sum(1 for x in data if isinstance(x, list))
        cands = [n_lists, len(flat), len(data), n_lists + 2, top_lists, top_lists + 1]
        why = (
            "Each call counts 1 for the list it was given (`count = 1`) and then adds the counts "
            f"of the lists inside it; numbers add nothing. There are {n_lists} inner lists plus "
            f"the outer list itself, so the result is {answer}."
        )
    elif shape == "depth":
        fname = rng.choice(["depth", "max_depth"])
        defs = _lines(
            f"def {fname}(items):",
            "    deepest = 0",
            "    for item in items:",
            "        if isinstance(item, list):",
            f"            deepest = max(deepest, {fname}(item))",
            "    return deepest + 1",
        )
        answer = _depth(data)
        cands = [answer - 1, answer + 1, len(data), n_lists, n_lists + 1]
        why = (
            "A list with no inner lists has depth 1, and every level of nesting adds 1 to the "
            f"deepest inner list's depth. The deepest number here is inside {answer} pairs of "
            f"brackets, so the result is {answer}."
        )
    else:
        fname = rng.choice(["flatten", "unnest"])
        joiner = rng.choice(["extend", "plus"])
        defs = _lines(
            f"def {fname}(items):",
            "    flat = []",
            "    for item in items:",
            "        if isinstance(item, list):",
            f"            flat.extend({fname}(item))" if joiner == "extend" else f"            flat += {fname}(item)",
            "        else:",
            "            flat.append(item)",
            "    return flat",
        )
        one_level = [y for x in data for y in (x if isinstance(x, list) else [x])]
        answer = flat
        cands = [one_level, data, top_ints, TYPE_ERROR, sorted(flat)]
        why = (
            "Each inner list is flattened by a recursive call *before* its items are added, so "
            f"lists at every depth are opened up, not just the first level: {flat}."
        )
    extra = ", 1" if shape == "weighted" else ""
    code = _prog(defs, f"print({fname}({data}{extra}))")
    distractors = [str(c) for c in cands]
    if isinstance(answer, int):
        distractors = _nums(distractors, answer, rng)
    return _output(
        code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True, expect=answer
    )


@generator(TOPIC, HARD)
def gen_fib_calls(rng: random.Random) -> Question:
    """Naive Fibonacci recomputes the same values again and again: the calls branch like a tree."""
    shape = rng.choice(["counter", "counter", "count_arg"])
    lt2 = rng.random() < 0.6
    base = ["    if n < 2:", "        return n"] if lt2 else ["    if n <= 2:", "        return 1"]
    k = rng.randint(4, 7)

    def calls_for(m):
        if (lt2 and m < 2) or (not lt2 and m <= 2):
            return 1
        return 1 + calls_for(m - 1) + calls_for(m - 2)

    if shape == "counter":
        counter = rng.choice(["calls", "count"])
        defs = _lines(
            "def fib(n):",
            f"    global {counter}",
            f"    {counter} += 1",
            *base,
            "    return fib(n - 1) + fib(n - 2)",
        )
        code = _prog(f"{counter} = 0", defs, f"print(fib({k}), {counter})")
        res = run_code(code)
        v, c = (int(x) for x in res.output.split())
        if c != calls_for(k):
            raise GenerationError(f"call count {c} != {calls_for(k)}")
        fprev = int(_value_of(_prog(defs.replace(f"    global {counter}\n    {counter} += 1\n", ""), f"v = fib({k - 1})"), "v"))
        cprev = calls_for(k - 1)
        distractors = [
            f"{v} {k}", f"{v} {k + 1}", f"{v} {cprev}", f"{v} {2 ** k}", f"{v} {c - 1}",
            f"{fprev} {c}", f"{v} {v}", f"{v} {c + 1}",
        ]
        start = 0 if lt2 else 1
        seq = ", ".join(str(calls_for(m)) for m in range(start, k + 1))
        why = (
            "Every call that isn't a base case makes two more calls, so "
            "calls(n) = 1 + calls(n - 1) + calls(n - 2). For n = "
            f"{start}..{k} that gives {seq}: `fib({k})` returns {v} after {c} calls, far more "
            f"than {k}."
        )
        return _output(code, HARD, distractors, why, rng)
    defs = _lines("def fib(n):", *base, "    return fib(n - 1) + fib(n - 2)")
    lowest = 1 if lt2 else 2
    k = max(k, 5)
    j = rng.randint(lowest, k - 3)
    calls, _, _ = _trace(defs, "fib", f"fib({k})")
    count = sum(1 for a in calls if a == (j,))
    cands = [1, count - 1, count + 1, k - j, 2, count * 2]
    why = (
        f"`fib` doesn't remember results. Every `fib({j + 1})` call makes its own call to "
        f"`fib({j})`, and so does every `fib({j + 2})` call, so the same value is recomputed "
        f"over and over: {count} times during `fib({k})`."
    )
    return _choice(
        difficulty=HARD,
        prompt=f"When this code runs, how many times is `fib({j})` called?",
        code=_prog(defs, f"print(fib({k}))"),
        correct=str(count),
        distractors=_nums(cands, count, rng),
        explanation=why,
        rng=rng,
    )


def _tree_order(n: int, mode: str) -> list:
    """What ``_tree_defs`` prints for ``n`` in pre-order or in-order mode."""
    if n == 0:
        return []
    below = _tree_order(n - 1, mode)
    return [n] + below + below if mode == "pre" else below + [n] + below


def _tree_defs(fname: str, mode: str) -> str:
    pr = '    print(n, end=" ")'
    lines = [f"def {fname}(n):", "    if n == 0:", "        return"]
    if mode == "pre":
        lines += [pr, f"    {fname}(n - 1)", f"    {fname}(n - 1)"]
    elif mode == "in":
        lines += [f"    {fname}(n - 1)", pr, f"    {fname}(n - 1)"]
    elif mode == "post":
        lines += [f"    {fname}(n - 1)", f"    {fname}(n - 1)", pr]
    elif mode == "single_after":
        lines += [f"    {fname}(n - 1)", pr]
    else:
        lines += [pr, f"    {fname}(n - 1)"]
    return _lines(*lines)


@generator(TOPIC, HARD)
def gen_tree_recursion(rng: random.Random) -> Question:
    """Two recursive calls per level: the work (and output) branches like a tree."""
    shape = rng.choice(["in", "pre", "doubling", "stairs", "choices"])
    if shape in ("in", "pre"):
        fname = rng.choice(["pattern", "ruler", "tree"])
        k = 3 if shape == "pre" else rng.choice([3, 3, 4])

        def out(mode):
            return _run(_prog(_tree_defs(fname, mode), f"{fname}({k})"))

        code = _prog(_tree_defs(fname, shape), f"{fname}({k})")
        correct = out(shape)
        others = [m for m in ("in", "pre", "post") if m != shape]
        distractors = [
            out(others[0]),
            out("single_after" if shape == "in" else "single_before"),
            " ".join(correct.split()[: len(correct.split()) // 2 + 1]),
            out(others[1]),
        ]
        if shape == "in":
            why = (
                f"`{fname}(n)` runs the whole `{fname}(n - 1)` pattern, prints `n`, then runs "
                f"`{fname}(n - 1)` again. So `{fname}(1)` prints 1, `{fname}(2)` prints 1 2 1, and "
                f"each level wraps its `n` between two copies of the level below: {correct.strip()}."
            )
        else:
            why = (
                f"`{fname}(n)` prints `n` first, then runs `{fname}(n - 1)` twice in full. "
                f"`{fname}(1)` prints 1, `{fname}(2)` prints 2 1 1, so `{fname}(3)` prints 3, "
                f"then 2 1 1 twice: {correct.strip()}."
            )
        expect = _seq(_tree_order(k, shape), " ")
        return _output(code, HARD, distractors, why, rng, expect=expect)
    if shape == "doubling":
        fname = rng.choice(["count", "branches", "leaves"])
        k = rng.randint(3, 6)
        nodes = rng.random() < 0.4
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            "        return 1",
            f"    return {'1 + ' if nodes else ''}{fname}(n - 1) + {fname}(n - 1)",
        )
        answer = 2 ** (k + 1) - 1 if nodes else 2 ** k
        cands = [2 * k, 2 ** (k - 1), k + 1, 2 ** (k + 1), 2 ** k, 2 ** (k + 1) - 1, k * k]
        if nodes:
            why = (
                f"Each call counts itself (1) plus everything below its two calls, so "
                f"{fname}(n) = 1 + 2 * {fname}(n - 1): 1, 3, 7, 15, ... For n = {k} that is "
                f"2 ** {k + 1} - 1 = {answer}."
            )
        else:
            why = (
                f"Each level adds the results of *two* calls, so the value doubles every level: "
                f"{fname}(0) = 1, {fname}(1) = 2, {fname}(2) = 4, ... {fname}({k}) = 2 ** {k} = "
                f"{answer}."
            )
        return _output(
            _prog(defs, f"print({fname}({k}))"), HARD, _nums(cands, answer, rng), why, rng,
            expect=answer,
        )
    if shape == "stairs":
        fname = rng.choice(["ways", "climb"])
        k = rng.randint(4, 7)
        defs = _lines(
            f"def {fname}(n):",
            "    if n <= 1:",
            "        return 1",
            f"    return {fname}(n - 1) + {fname}(n - 2)",
        )
        vals = [1, 1]
        for _ in range(k):
            vals.append(vals[-1] + vals[-2])
        answer = vals[k]
        cands = [vals[k - 1], vals[k + 1], k, 2 ** (k - 1), answer + 1, 2 * k]
        why = (
            f"Each result is the sum of the two before it, starting from {fname}(0) = {fname}(1) "
            f"= 1: {', '.join(map(str, vals[:k + 1]))}. So `{fname}({k})` returns {answer}."
        )
        return _output(
            _prog(defs, f"print({fname}({k}))"), HARD, _nums(cands, answer, rng), why, rng,
            expect=answer,
        )
    x, y = rng.choice([("a", "b"), ("H", "T"), ("0", "1"), ("x", "o"), ("L", "R")])
    fname = rng.choice(["build", "choices", "paths"])
    k = rng.choice([2, 3])
    pr = "print(prefix)" if k == 2 else 'print(prefix, end=" ")'
    defs = _lines(
        f"def {fname}(prefix, n):",
        "    if n == 0:",
        f"        {pr}",
        "        return",
        f'    {fname}(prefix + "{x}", n - 1)',
        f'    {fname}(prefix + "{y}", n - 1)',
    )
    sep = "\n" if k == 2 else " "
    strs = [""]
    for _ in range(k):
        strs = [s + c for s in strs for c in (x, y)]
    swapped = [s.translate(str.maketrans(x + y, y + x)) for s in strs]
    distractors = [
        _seq([s[::-1] for s in strs], sep),
        _seq(swapped, sep),
        _seq([x * k, y * k], sep),
        _seq(strs[:-1], sep),
        _seq([x, y] + [s for s in strs], sep),
    ]
    why = (
        f"Every call that isn't at the bottom makes two calls: first adding \"{x}\", then "
        f"adding \"{y}\". The first branch is followed all the way down before the second "
        f"starts, so the {2 ** k} strings come out in order: {_seq(strs, ' ')}."
    )
    code = _prog(defs, f'{fname}("", {k})')
    return _output(code, HARD, distractors, why, rng, expect=_seq(strs, sep))


@generator(TOPIC, HARD)
def gen_missing_return(rng: random.Random) -> Question:
    """Forgetting ``return`` on the recursive call: the result is lost (None, or a TypeError)."""
    shape = rng.choice(["sum", "factorial", "find_max", "build_string", "collect"])
    broken = rng.random() < 0.6
    ret = "" if broken else "return "
    if shape in ("sum", "factorial"):
        if shape == "sum":
            fname = rng.choice(["total", "sum_to"])
            op, base_n, base_val = "+", 0, 0
            k = rng.choice([1, 2, 3, 3, 4]) if broken else rng.randint(2, 4)
            answer = k * (k + 1) // 2
        else:
            fname = rng.choice(["fact", "factorial"])
            op, base_n, base_val = "*", 1, 1
            k = rng.choice([2, 3, 3, 4, 5]) if broken else rng.randint(3, 5)
            answer = math.factorial(k)
        if rng.random() < 0.5:
            rec = [f"    {ret}n {op} {fname}(n - 1)"]
        else:
            rec = [f"    result = n {op} {fname}(n - 1)"] + (["    return result"] if not broken else [])
        defs = _lines(f"def {fname}(n):", f"    if n == {base_n}:", f"        return {base_val}", *rec)
        code = _prog(defs, f"print({fname}({k}))")
        lo = base_n + 1
        if broken:
            distractors = [answer, "None", TYPE_ERROR, base_val, RECURSION_ERROR]
            if k == lo:
                why = (
                    f"`{fname}({k})` calls `{fname}({base_n})`, which returns {base_val}, and "
                    f"computes {k} {op} {base_val}, but never returns that value. A function that "
                    f"ends without `return` returns `None`, so `None` is printed."
                )
            else:
                why = (
                    f"Only the base case has a `return`. `{fname}({lo})` computes {lo} {op} "
                    f"{base_val} but never returns it, so it gives back `None`. Then "
                    f"`{fname}({lo + 1})` tries `{lo + 1} {op} None`, which raises `TypeError`."
                )
        else:
            distractors = ["None", TYPE_ERROR, base_val, RECURSION_ERROR]
            why = (
                f"Every level returns its result, so the values flow back up to the first call: "
                f"`{fname}({k})` returns {answer}."
            )
        if not broken:
            expect = answer
        elif k == lo:
            expect = "None"
        else:
            expect = TYPE_ERROR
        return _output(
            code, HARD, _nums(distractors, answer, rng), why, rng,
            prompt=PRINT_OR_ERROR, allow_error=True, expect=expect,
        )
    if shape == "find_max":
        fname = rng.choice(["find_max", "largest"])
        nums = rng.sample(range(1, 10), rng.randint(3, 4))
        defs = _lines(
            f"def {fname}(nums, best):",
            "    if not nums:",
            "        return best",
            "    if nums[0] > best:",
            "        best = nums[0]",
            f"    {ret}{fname}(nums[1:], best)",
        )
        call = f"{fname}({nums}, 0)"
        good = max(nums)
        rec = f"{fname}(nums[1:], best)"
        distractors = [good, "None", "0", TYPE_ERROR, nums[0], nums[-1]]
    elif shape == "build_string":
        fname = rng.choice(["build", "make_line"])
        ch = rng.choice(["*", "#", "ab", "-"])
        k = rng.randint(2, 4)
        defs = _lines(
            f"def {fname}(n, text):",
            "    if n == 0:",
            "        return text",
            f'    {ret}{fname}(n - 1, text + "{ch}")',
        )
        call = f'{fname}({k}, "")'
        good = ch * k
        rec = f'{fname}(n - 1, text + "{ch}")'
        distractors = [good, "None", NOTHING_PRINTED, TYPE_ERROR, ch, ch * (k - 1)]
    else:
        fname = rng.choice(["collect", "gather"])
        k = rng.randint(2, 4)
        defs = _lines(
            f"def {fname}(n, found):",
            "    if n == 0:",
            "        return found",
            "    found.append(n)",
            f"    {ret}{fname}(n - 1, found)",
        )
        call = f"{fname}({k}, [])"
        good = list(range(k, 0, -1))
        rec = f"{fname}(n - 1, found)"
        distractors = [good, "None", "[]", good[::-1], TYPE_ERROR]
    code = _prog(defs, f"print({call})")
    if broken:
        why = (
            f"The line `{rec}` makes the recursive call but throws its result away. The base "
            f"case's value only goes back to the call that asked for it; `{call}` itself reaches "
            f"the end of the function without a `return`, so it returns `None`."
        )
    else:
        why = (
            f"`return {rec}` passes each call's result straight back up, so the base case's "
            f"value ({_lit(good)}) reaches the first call and is printed."
        )
    return _output(
        code, HARD, distractors, why, rng,
        prompt=PRINT_OR_ERROR, allow_error=True, expect="None" if broken else good,
    )


@generator(TOPIC, HARD)
def gen_unreachable_base(rng: random.Random) -> Question:
    """A base case exists, but some inputs skip right past it (or crash before reaching it)."""
    shape = rng.choice(["step_skip", "below_base", "index_vs_recursion", "even_length", "climb"])
    if shape == "step_skip":
        fname = rng.choice(["total", "skip_sum"])
        k = rng.choice([5, 7, 9, 11]) if rng.random() < 0.5 else rng.choice([6, 8, 10])
        defs = _lines(
            f"def {fname}(n):",
            "    if n == 0:",
            "        return 0",
            f"    return n + {fname}(n - 2)",
        )
        terms = list(range(k, 0, -2))
        if k % 2:
            distractors = [sum(terms), sum(terms) - 1, 0, TYPE_ERROR, sum(terms) - k]
            why = (
                f"`n` goes {', '.join(map(str, terms))}, -1, -3, ... It starts odd and drops by 2, "
                f"so it jumps right over 0 and `n == 0` is never true. The calls never stop: "
                f"`RecursionError`. (`n <= 0` would have been a safe base case.)"
            )
        else:
            distractors = [RECURSION_ERROR, k * (k + 1) // 2, sum(terms) - 2, sum(terms) + 1]
            why = (
                f"`n` goes {', '.join(map(str, terms))}, 0. Starting from an even number it lands "
                f"exactly on 0, so the base case is reached: {' + '.join(map(str, terms))} + 0 = "
                f"{sum(terms)}."
            )
        code = _prog(defs, f"print({fname}({k}))")
        expect = RECURSION_ERROR if k % 2 else sum(terms)
        return _output(
            code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True, expect=expect
        )
    if shape == "below_base":
        broken = rng.random() < 0.5
        if rng.random() < 0.5:
            fname = rng.choice(["fact", "factorial"])
            cond = "n == 1" if broken else "n <= 1"
            defs = _lines(
                f"def {fname}(n):",
                f"    if {cond}:",
                "        return 1",
                f"    return n * {fname}(n - 1)",
            )
            call = f"{fname}(0)"
            if broken:
                why = (
                    f"The base case only catches `n == 1`, but `{call}` starts *below* it: it "
                    f"calls `{fname}(-1)`, then `{fname}(-2)`, ... and never reaches 1. Result: "
                    f"`RecursionError`."
                )
            else:
                why = (
                    f"`n <= 1` is true for 0 as well, so `{call}` stops immediately and returns 1 "
                    f"(by definition 0! = 1). With `n == 1` it would have recursed forever."
                )
        else:
            b = rng.randint(2, 9)
            if broken:
                base = ["    if exp == 1:", "        return base"]
            else:
                base = ["    if exp == 0:", "        return 1"]
            defs = _lines(
                "def power(base, exp):", *base, "    return base * power(base, exp - 1)"
            )
            call = f"power({b}, 0)"
            if broken:
                why = (
                    f"The base case is `exp == 1`, but `{call}` starts at 0 and only goes down "
                    f"(-1, -2, ...), so it never reaches 1: `RecursionError`."
                )
            else:
                why = (
                    f"`exp == 0` is the base case, so `{call}` returns 1 straight away: any "
                    f"number to the power 0 is 1."
                )
        code = _prog(defs, f"print({call})")
        if broken:
            distractors = ["1", "0", "None", TYPE_ERROR]
        else:
            distractors = [RECURSION_ERROR, "0", "None", TYPE_ERROR]
        expect = RECURSION_ERROR if broken else 1
        return _output(
            code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True, expect=expect
        )
    if shape == "index_vs_recursion":
        fname = rng.choice(["mystery", "rebuild", "process"])
        word = rng.choice(_SHORT_WORDS)
        variant = rng.choice(["index", "recursion", "fixed"])
        if variant == "index":
            body = [f"    return text[0] + {fname}(text[1:])"]
            distractors = [RECURSION_ERROR, word, word[::-1], TYPE_ERROR]
            why = (
                "There is no base case, but this doesn't recurse forever: when `text` becomes "
                "\"\", Python evaluates the left side of `+` first, and `text[0]` on an empty "
                "string raises `IndexError` before the next call is made."
            )
        elif variant == "recursion":
            body = [f"    return {fname}(text[1:]) + text[0]"]
            distractors = [INDEX_ERROR, word[::-1], word, TYPE_ERROR]
            why = (
                f"There is no base case. The recursive call is evaluated first, and slicing an "
                f"empty string (`\"\"[1:]`) just gives \"\" again, so `{fname}(\"\")` calls itself "
                f"forever: `RecursionError`. `text[0]` is never reached."
            )
        else:
            body = ['    if text == "":', '        return ""', f"    return {fname}(text[1:]) + text[0]"]
            distractors = [RECURSION_ERROR, INDEX_ERROR, word, word[1:] + word[0]]
            why = (
                "The base case stops the recursion at the empty string. Each call puts its first "
                f"letter after the processed rest, so the result is reversed: {word[::-1]}."
            )
        code = _prog(_lines(f"def {fname}(text):", *body), f'print({fname}("{word}"))')
        expect = {"index": INDEX_ERROR, "recursion": RECURSION_ERROR, "fixed": word[::-1]}[variant]
        return _output(
            code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True, expect=expect
        )
    if shape == "even_length":
        fname = rng.choice(["every_other", "skip_letters"])
        word = rng.choice(_WORDS)
        defs = _lines(
            f"def {fname}(text):",
            "    if len(text) == 1:",
            "        return text",
            f"    return text[0] + {fname}(text[2:])",
        )
        parts = [word[i:] for i in range(0, len(word) + 1, 2)]
        if len(word) % 2:
            distractors = [INDEX_ERROR, word[1::2], word[::2][:-1], RECURSION_ERROR]
            why = (
                f'"{word}" has an odd length, so cutting 2 letters each time ('
                + ", ".join(f'"{p}"' for p in parts if p)
                + f") ends on a single letter, the base case. Result: {word[::2]}."
            )
        else:
            distractors = [word[::2], RECURSION_ERROR, word[::2] + word[-1], word[1::2]]
            why = (
                f'"{word}" has an even length, so cutting 2 letters at a time ('
                + ", ".join(f'"{p}"' for p in parts)
                + ") skips the 1-letter case and reaches \"\". `len(\"\") == 1` is false, so "
                "`text[0]` runs on the empty string and raises `IndexError`."
            )
        code = _prog(defs, f'print({fname}("{word}"))')
        expect = word[::2] if len(word) % 2 else INDEX_ERROR
        return _output(
            code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True, expect=expect
        )
    fname = rng.choice(["steps", "hops", "jumps"])
    step = rng.choice([2, 3])
    start = rng.randint(0, 4)
    m = rng.randint(2, 4)
    reachable = rng.random() < 0.5
    goal = start + step * m + (0 if reachable else 1)
    defs = _lines(
        f"def {fname}(n, goal):",
        "    if n == goal:",
        "        return 0",
        f"    return 1 + {fname}(n + {step}, goal)",
    )
    code = _prog(defs, f"print({fname}({start}, {goal}))")
    visits = list(range(start, goal + step + 1, step))[: m + 2]
    if reachable:
        distractors = [RECURSION_ERROR, m + 1, m - 1, goal - start]
        why = (
            f"`n` goes {', '.join(map(str, visits[: m + 1]))}: it lands exactly on {goal}, so the "
            f"base case returns 0 and each of the {m} earlier calls adds 1."
        )
    else:
        distractors = [m, m + 1, 0, TYPE_ERROR]
        why = (
            f"`n` goes {', '.join(map(str, visits))}, ... jumping from {start + step * m} to "
            f"{start + step * (m + 1)}, right over {goal}. `n == goal` is never true, so the "
            f"calls never stop: `RecursionError`. (`n >= goal` would be safer.)"
        )
    expect = m if reachable else RECURSION_ERROR
    return _output(
        code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True, expect=expect
    )
