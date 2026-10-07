"""Question generators for the "functions" topic (Functions).

Covers return values and the implicit ``None`` of a function without
``return``, ``print`` vs ``return``, positional / keyword / default arguments,
calling with the wrong number of arguments, local vs global scope (``global``,
shadowing, ``UnboundLocalError``), ``*args`` / ``**kwargs``, returning several
values as a tuple, early ``return``, functions as values, ``lambda``, call
chains such as ``f(g(x))``, closures with ``nonlocal``, default values being
evaluated only once (including the mutable-default trap), and functions that
mutate their arguments.
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

TOPIC = "functions"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
BLANK = "____"
TYPE_ERROR = error_choice("TypeError")
NAME_ERROR = error_choice("NameError")
UNBOUND = error_choice("UnboundLocalError")
VALUE_ERROR = error_choice("ValueError")
MAX_SNIPPET_LINES = 14


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _prog(*blocks: str) -> str:
    """Join top-level blocks (defs, main code) with two blank lines, as PEP 8 asks."""
    code = "\n\n\n".join(b.strip("\n") for b in blocks)
    if len(code.split("\n")) > MAX_SNIPPET_LINES:
        raise GenerationError(f"snippet too long:\n{code}")
    return code


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


def _nums(cands, correct: int, rng: random.Random) -> list:
    """Misconception-based candidates first, then nearby integers as a fallback."""
    return [*cands, *int_distractors(correct, rng)]


def _sub(src: str, n) -> str:
    """``src`` with its ``{p}`` placeholder replaced by the number ``n``."""
    return src.format(p=str(n) if n >= 0 else f"({n})")


def _calc(src: str, n):
    """Evaluate a tiny arithmetic body such as ``"{p} * 2"`` for ``n``."""
    return eval(src.format(p=f"({n})"), {"__builtins__": {}})  # noqa: S307 - our own strings


def _lines(*parts) -> str:
    return "\n".join(str(p) for p in parts)


_PARAMS = ["n", "x", "num", "value"]

# (name, body with {p} for the parameter, [plausible misreadings of the body])
_ONE_ARG = [
    ("double", "{p} * 2", ["{p} + 2", "{p} ** 2"]),
    ("triple", "{p} * 3", ["{p} + 3", "{p} ** 3"]),
    ("square", "{p} * {p}", ["{p} * 2", "{p} + 2"]),
    ("add_ten", "{p} + 10", ["{p} * 10", "{p} + 1"]),
    ("halve", "{p} // 2", ["{p} / 2", "{p} * 2"]),
    ("minus_three", "{p} - 3", ["3 - {p}", "{p} + 3"]),
]

# Single-parameter helpers used for call chains: (name, body using n).
_STEPS = [
    ("double", "n * 2"),
    ("add_one", "n + 1"),
    ("square", "n * n"),
    ("add_three", "n + 3"),
    ("halve", "n // 2"),
    ("negate", "-n"),
]


def _step_fn(body: str):
    return lambda n: eval(body, {"__builtins__": {}}, {"n": n})  # noqa: S307


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_return_value(rng: random.Random) -> Question:
    """A call is replaced by the value its ``return`` sends back."""
    shape = rng.choice(["direct", "stored", "two_calls", "nested", "order", "divide", "repeat"])
    p = rng.choice(_PARAMS)
    if shape in ("direct", "stored", "two_calls", "nested"):
        name, body, (w1, w2) = rng.choice(_ONE_ARG)
        func = f"def {name}({p}):\n    return {body.format(p=p)}"
        a = rng.randint(2, 5) if shape == "nested" else rng.randint(2, 9)
        fa = _calc(body, a)
        if shape == "direct":
            main = f"print({name}({a}))"
            cands = [_calc(w1, a), a, _calc(w2, a), "None"]
            why = (
                f"Calling `{name}({a})` runs the body with `{p}` = {a}. `return` sends back "
                f"{_sub(body, a)} = {fa}, and `print` shows that value."
            )
        elif shape == "stored":
            k = rng.randint(1, 5)
            main = f"result = {name}({a})\nprint(result + {k})"
            cands = [fa, _calc(w1, a) + k, a + k, _calc(w2, a) + k]
            why = (
                f"`{name}({a})` returns {fa}, so `result` holds {fa} and "
                f"`result + {k}` is {fa + k}."
            )
        elif shape == "two_calls":
            b = rng.choice([v for v in range(2, 10) if v != a])
            fb = _calc(body, b)
            main = f"print({name}({a}) + {name}({b}))"
            cands = [fa, _calc(w1, a) + _calc(w1, b), a + b, fb, f"{fa} {fb}"]
            why = (
                f"Each call is replaced by its return value: `{name}({a})` gives {fa} and "
                f"`{name}({b})` gives {fb}, so the sum is {fa + fb}."
            )
        else:
            ffa = _calc(body, fa)
            main = f"print({name}({name}({a})))"
            cands = [fa, _calc(w1, _calc(w1, a)), _calc(w1, fa), a, fa * 2]
            why = (
                f"The inner call runs first: `{name}({a})` returns {fa}. That value is "
                f"passed to the outer call, and `{name}({fa})` returns {ffa}."
            )
        return _output(_prog(func, main), EASY, _nums(cands, 0, rng), why, rng)

    if shape == "order":
        fname, p1, p2 = rng.choice(
            [("difference", "big", "small"), ("subtract", "a", "b"), ("gap", "first", "second")]
        )
        x, y = rng.sample(range(2, 16), 2)
        code = _prog(f"def {fname}({p1}, {p2}):\n    return {p1} - {p2}", f"print({fname}({x}, {y}))")
        cands = [y - x, x + y, "None", x, y]
        why = (
            f"Arguments are matched to parameters by position: `{p1}` gets {x} and `{p2}` "
            f"gets {y}, so the function returns {x} - {y} = {x - y}."
        )
    elif shape == "divide":
        b = rng.randint(2, 5)
        q = rng.randint(2, 6)
        a = b * q
        fname = rng.choice(["divide", "share", "per_person"])
        code = _prog(f"def {fname}(total, people):\n    return total / people", f"print({fname}({a}, {b}))")
        cands = [q, b / a, a * b, "None"]
        why = (
            f"`{fname}({a}, {b})` returns `{a} / {b}`. The `/` operator always produces a "
            f"float, so the returned value is {a / b}, not {q}."
        )
    else:
        word = rng.choice(["ha", "na", "go", "hey", "ho", "la", "boo"])
        times = rng.randint(2, 4)
        fname = rng.choice(["repeat", "echo"])
        code = _prog(
            f"def {fname}(word, times):\n    return word * times", f'print({fname}("{word}", {times}))'
        )
        cands = [f"{word}{times}", " ".join([word] * times), word * (times + 1), word]
        why = (
            f'`word * times` repeats the string, so `{fname}("{word}", {times})` returns '
            f'"{word}" {times} times in a row: {word * times}.'
        )
    return _output(code, EASY, cands, why, rng)


@generator(TOPIC, EASY)
def gen_implicit_none(rng: random.Random) -> Question:
    """A function without ``return`` gives back ``None``."""
    shape = rng.choice(["print_inside", "print_inside", "no_return", "use_result", "side_effect", "type"])
    prompt, allow_error = PRINT, False
    if shape == "print_inside":
        if rng.random() < 0.5:
            name = rng.choice(NAMES)
            word = rng.choice(["Hello,", "Hi", "Welcome", "Hey"])
            fname = "greet"
            code = _prog(f'def greet(name):\n    print("{word}", name)', f'print(greet("{name}"))')
            shown = f"{word} {name}"
        else:
            n = rng.randint(2, 9)
            fname = rng.choice(["show_double", "print_double"])
            code = _prog(f"def {fname}(n):\n    print(n * 2)", f"print({fname}({n}))")
            shown = str(n * 2)
        distractors = [shown, f"{shown}\n{shown}", "None", f"None\n{shown}"]
        why = (
            f"`{fname}` prints `{shown}` itself, but it has no `return`, so the call evaluates "
            f"to `None` and the outer `print` then shows `None`."
        )
    elif shape == "no_return":
        a, b = rng.randint(2, 9), rng.randint(2, 9)
        var = rng.choice(["total", "result", "answer"])
        fname = rng.choice(["add", "add_numbers", "get_sum"])
        code = _prog(f"def {fname}(a, b):\n    {var} = a + b", f"print({fname}({a}, {b}))")
        prompt = PRINT_OR_ERROR
        distractors = [a + b, NOTHING_PRINTED, NAME_ERROR, "0"]
        why = (
            f"`{fname}` computes {a + b} and stores it in the local variable `{var}`, but never "
            "returns it. A function that ends without `return` returns `None`."
        )
    elif shape == "use_result":
        name, body, _ = rng.choice(_ONE_ARG)
        a = rng.randint(2, 9)
        k = rng.randint(1, 5)
        fa = _calc(body, a)
        code = _prog(
            f"def {name}(n):\n    result = {body.format(p='n')}",
            f"answer = {name}({a})\nprint(answer + {k})",
        )
        prompt, allow_error = PRINT_OR_ERROR, True
        distractors = [fa + k, "None", a + k, NAME_ERROR]
        why = (
            f"`{name}` never returns `result`, so `answer` is `None`. Adding a number to "
            f"`None` (`None + {k}`) raises a `TypeError`."
        )
    elif shape == "side_effect":
        msg = rng.choice(["Hi!", "Go!", "Done!", "Ready?", "Hooray!"])
        fname = rng.choice(["say_hi", "cheer", "announce"])
        var = rng.choice(["result", "value", "out"])
        code = _prog(f'def {fname}():\n    print("{msg}")', f"{var} = {fname}()\nprint({var})")
        distractors = ["None", msg, f"{msg}\n{msg}", f"None\n{msg}"]
        why = (
            f"`{var} = {fname}()` still runs the function, which prints {msg}. "
            f"The function has no `return`, so `{var}` is `None`, which is printed next."
        )
    else:
        n = rng.randint(2, 9)
        fname = rng.choice(["show_double", "print_double"])
        code = _prog(f"def {fname}(n):\n    print(n * 2)", f"result = {fname}({n})\nprint(type(result))")
        distractors = [
            f"{n * 2}\n<class 'int'>",
            "<class 'NoneType'>",
            "<class 'int'>",
            f"{n * 2}\n<class 'function'>",
        ]
        why = (
            f"Calling `{fname}({n})` prints {n * 2}, but the function returns nothing, so "
            "`result` is `None`, whose type is `NoneType`."
        )
    return _output(code, EASY, distractors, why, rng, prompt=prompt, allow_error=allow_error)


@generator(TOPIC, EASY)
def gen_print_vs_return(rng: random.Random) -> Question:
    """A returned value is not printed unless you print it; return ends the function."""
    shape = rng.choice(["discarded", "discarded", "prints_and_returns", "after_return"])
    if shape == "discarded":
        name, body, _ = rng.choice(_ONE_ARG)
        a, b = rng.sample(range(2, 10), 2)
        while _calc(body, a) == _calc(body, b):  # halve(4) == halve(5)
            b = rng.choice([v for v in range(2, 10) if v != a])
        fa, fb = _calc(body, a), _calc(body, b)
        func = f"def {name}(n):\n    return {body.format(p='n')}"
        if rng.random() < 0.5:
            msg = rng.choice(["done", "finished", "bye"])
            code = _prog(func, f'{name}({a})\nprint("{msg}")')
            distractors = [f"{fa}\n{msg}", f"{msg}\n{fa}", fa, NOTHING_PRINTED]
        else:
            code = _prog(func, f"{name}({a})\nprint({name}({b}))")
            distractors = [f"{fa}\n{fb}", fa, f"{fb}\n{fa}", f"{fb}\n{fb}"]
        why = (
            f"The bare call `{name}({a})` returns {fa}, but nothing prints or stores it, so the "
            "value is simply thrown away. `return` gives a value back; only `print` shows it."
        )
    elif shape == "prints_and_returns":
        name, body, _ = rng.choice(_ONE_ARG)
        a = rng.randint(2, 9)
        fa = _calc(body, a)
        var = rng.choice(["result", "answer", "y"])
        code = _prog(
            f"def {name}(n):\n    print(n)\n    return {body.format(p='n')}",
            f"{var} = {name}({a})\nprint({var})",
        )
        distractors = [fa, f"{fa}\n{a}", f"{a}\n{a}", f"{fa}\n{fa}", a]
        why = (
            f"Calling `{name}({a})` first runs `print(n)`, showing {a}, then returns {fa}. "
            f"That returned value is stored in `{var}` and printed on the next line."
        )
    else:
        a, b = rng.randint(2, 9), rng.randint(2, 9)
        msg = rng.choice(["calculated", "Done!", "finished"])
        fname, op = rng.choice([("get_total", "+"), ("get_product", "*"), ("combine", "+")])
        val = a + b if op == "+" else a * b
        code = _prog(
            f'def {fname}(a, b):\n    return a {op} b\n    print("{msg}")', f"print({fname}({a}, {b}))"
        )
        distractors = [f"{msg}\n{val}", f"{val}\n{msg}", msg, "None"]
        why = (
            f"`return` ends the function immediately, so the `print(\"{msg}\")` line after it "
            f"never runs. Only the returned value {val} is printed."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_default_param(rng: random.Random) -> Question:
    """A parameter with a default value can be left out of the call."""
    shape = rng.choice(["power", "greet", "step"])
    if shape == "power":
        default = rng.choice([2, 2, 3])
        a = rng.randint(2, 5) if default == 2 else rng.randint(2, 4)
        b = rng.randint(2, 4)
        e = rng.choice([x for x in (2, 3, 4) if x != default and b ** x <= 100])
        code = _prog(
            f"def power(base, exp={default}):\n    return base ** exp",
            f"print(power({a}), power({b}, {e}))",
        )
        distractors = [
            f"{a ** default} {b ** default}",
            TYPE_ERROR,
            f"{a * default} {b * e}",
            f"{a} {b ** e}",
            f"{a ** default} {e ** b}",
        ]
        why = (
            f"`power({a})` leaves out `exp`, so its default {default} is used: {a} ** {default} = "
            f"{a ** default}. `power({b}, {e})` passes `exp` explicitly, replacing the default: "
            f"{b} ** {e} = {b ** e}."
        )
    elif shape == "greet":
        default = rng.choice(["Hello", "Hi", "Welcome"])
        other = rng.choice([g for g in ["Hey", "Bye", "Good luck", "Howdy"] if g != default])
        n1, n2 = rng.sample(NAMES, 2)
        code = _prog(
            f'def greet(name, greeting="{default}"):\n    return greeting + ", " + name + "!"',
            f'print(greet("{n1}"))\nprint(greet("{n2}", "{other}"))',
        )
        distractors = [
            f"{default}, {n1}!\n{default}, {n2}!",
            TYPE_ERROR,
            f"{default}, {n1}!\n{n2}, {other}!",
            f"{n1}, {default}!\n{n2}, {other}!",
        ]
        why = (
            f'The first call leaves out `greeting`, so it uses the default "{default}". The '
            f'second call passes "{other}", which replaces the default for that call only.'
        )
    else:
        default = rng.choice([1, 1, 2])
        start = rng.randint(3, 12)
        step = rng.choice([s for s in (3, 4, 5, 10) if s != default])
        fname = rng.choice(["count_up", "move", "advance"])
        code = _prog(
            f"def {fname}(start, step={default}):\n    return start + step",
            f"print({fname}({start}), {fname}({start}, {step}))",
        )
        distractors = [
            f"{start + default} {start + default}",
            TYPE_ERROR,
            f"{start} {start + step}",
            f"{start + default} {start + step + default}",
            f"{start + default} {step + default}",
        ]
        why = (
            f"`{fname}({start})` uses the default `step={default}`, giving {start + default}. "
            f"`{fname}({start}, {step})` passes `step` explicitly, so it gives {start + step}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR)


@generator(TOPIC, EASY)
def gen_keyword_args(rng: random.Random) -> Question:
    """Keyword arguments are matched by name, not by position."""
    shape = rng.choice(["subtract", "subtract", "describe", "divide", "mixed"])
    if shape in ("subtract", "mixed"):
        fname, p1, p2 = rng.choice(
            [("subtract", "a", "b"), ("difference", "first", "second"), ("take_away", "start", "amount")]
        )
        x, y = rng.sample(range(2, 20), 2)
        func = f"def {fname}({p1}, {p2}):\n    return {p1} - {p2}"
        if shape == "subtract":
            code = _prog(func, f"print({fname}({p2}={x}, {p1}={y}))")
            distractors = [x - y, TYPE_ERROR, x + y, NAME_ERROR]
            why = (
                f"Keyword arguments are matched by name, not position: `{p1}` is {y} and `{p2}` "
                f"is {x}, so the function returns {y} - {x} = {y - x}."
            )
        else:
            code = _prog(func, f"print({fname}({x}, {p2}={y}))")
            distractors = [y - x, TYPE_ERROR, x + y, NAME_ERROR]
            why = (
                f"The positional argument {x} fills the first parameter `{p1}`, and `{p2}={y}` is "
                f"matched by name, so the function returns {x} - {y} = {x - y}."
            )
    elif shape == "describe":
        name = rng.choice(NAMES)
        age = rng.randint(8, 16)
        thing, p2 = rng.choice([("is", "age"), ("is level", "level"), ("scored", "points")])
        code = _prog(
            f'def describe(name, {p2}):\n    return f"{{name}} {thing} {{{p2}}}"',
            f'print(describe({p2}={age}, name="{name}"))',
        )
        distractors = [f"{age} {thing} {name}", TYPE_ERROR, NAME_ERROR, f"name {thing} {p2}"]
        why = (
            f"`name=\"{name}\"` and `{p2}={age}` are matched to the parameters by name, so the "
            "order you write keyword arguments in does not matter."
        )
    else:
        parts = rng.randint(2, 5)
        total = parts * rng.randint(2, 6)
        fname = rng.choice(["divide", "share"])
        code = _prog(
            f"def {fname}(total, parts):\n    return total // parts",
            f"print({fname}(parts={parts}, total={total}))",
        )
        distractors = [parts // total, TYPE_ERROR, total * parts, NAME_ERROR]
        why = (
            f"Keyword arguments are matched by name: `total` is {total} and `parts` is {parts}, "
            f"so the result is {total} // {parts} = {total // parts}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR)


@generator(TOPIC, EASY)
def gen_wrong_arg_count(rng: random.Random) -> Question:
    """Too many / too few arguments raise TypeError; defaults make arguments optional."""
    shape = rng.choice(["too_many", "too_few", "none_expected", "default_ok", "default_ok", "default_full"])
    a, b, c = rng.sample(range(1, 10), 3)
    fname = rng.choice(["add", "total", "combine"])
    allow_error = shape in ("too_many", "too_few", "none_expected")
    if shape == "too_many":
        code = _prog(f"def {fname}(a, b):\n    return a + b", f"print({fname}({a}, {b}, {c}))")
        distractors = [a + b + c, a + b, NAME_ERROR, "None"]
        why = (
            f"`{fname}` has exactly 2 parameters, but the call passes 3 arguments. Python never "
            "silently ignores extra arguments: it raises a `TypeError`."
        )
    elif shape == "too_few":
        code = _prog(f"def {fname}(a, b):\n    return a + b", f"print({fname}({a}))")
        distractors = [a, "None", NAME_ERROR, a + a]
        why = (
            f"`b` has no default value, so `{fname}({a})` is missing a required argument and "
            "Python raises a `TypeError` before the body runs."
        )
    elif shape == "none_expected":
        msg = rng.choice(["Hi!", "Hello!", "Welcome!"])
        name = rng.choice(NAMES)
        fname = rng.choice(["say_hi", "greeting"])
        code = _prog(f'def {fname}():\n    return "{msg}"', f'print({fname}("{name}"))')
        distractors = [msg, f"{msg} {name}", NAME_ERROR, name]
        why = (
            f"`{fname}` is defined with no parameters, so calling it with one argument "
            f'("{name}") raises a `TypeError`.'
        )
    elif shape == "default_ok":
        k = rng.randint(2, 10)
        code = _prog(f"def {fname}(a, b={k}):\n    return a + b", f"print({fname}({a}))")
        distractors = [TYPE_ERROR, a, "None", a + a]
        why = (
            f"`b` has a default value of {k}, so it may be left out: `{fname}({a})` returns "
            f"{a} + {k} = {a + k}."
        )
    else:
        code = _prog(f"def {fname}(a, b, c=0):\n    return a + b + c", f"print({fname}({a}, {b}, {c}))")
        distractors = [TYPE_ERROR, a + b, NAME_ERROR, a + b + c + 1]
        why = (
            f"`c` has a default, but you are still allowed to pass it. Here `c` is {c}, so the "
            f"result is {a} + {b} + {c} = {a + b + c}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)


@generator(TOPIC, EASY)
def gen_scope_basics(rng: random.Random) -> Question:
    """Locals vanish after the call; functions can read globals; parameters are local."""
    shape = rng.choice(["local_outside", "param_outside", "read_global", "param_shadow", "defined_later"])
    allow_error = shape in ("local_outside", "param_outside")
    if shape == "local_outside":
        var = rng.choice(["total", "secret", "result", "answer"])
        fname = rng.choice(["calculate", "make_total", "compute"])
        a, b = rng.randint(2, 9), rng.randint(2, 9)
        code = _prog(f"def {fname}():\n    {var} = {a} + {b}\n    return {var}", f"{fname}()\nprint({var})")
        distractors = [a + b, "None", UNBOUND, NOTHING_PRINTED]
        why = (
            f"`{var}` is a local variable: it only exists while `{fname}` is running. The "
            f"returned value is thrown away and there is no global `{var}`, so `print({var})` "
            "raises a `NameError`."
        )
    elif shape == "param_outside":
        name, body, _ = rng.choice(_ONE_ARG)
        p = rng.choice(_PARAMS)
        a = rng.randint(2, 9)
        code = _prog(f"def {name}({p}):\n    return {body.format(p=p)}", f"result = {name}({a})\nprint({p})")
        distractors = [a, _calc(body, a), "None", UNBOUND]
        why = (
            f"The parameter `{p}` is local to `{name}`: it gets the value {a} during the call "
            f"and disappears afterwards. Outside the function `{p}` was never defined, so "
            "Python raises a `NameError`."
        )
    elif shape == "read_global":
        var = rng.choice(["bonus", "extra", "tax"])
        k = rng.randint(2, 9)
        s = rng.randint(10, 30)
        fname = f"add_{var}"
        code = _prog(f"{var} = {k}", f"def {fname}(score):\n    return score + {var}", f"print({fname}({s}))")
        distractors = [NAME_ERROR, s, UNBOUND, k]
        why = (
            f"A function can read a global variable it does not assign to. `{var}` is {k}, so "
            f"`{fname}({s})` returns {s} + {k} = {s + k}."
        )
    elif shape == "param_shadow":
        p = rng.choice(_PARAMS)
        g = rng.randint(10, 20)
        a = rng.randint(2, 9)
        code = _prog(f"{p} = {g}", f"def add_one({p}):\n    return {p} + 1", f"print(add_one({a}), {p})")
        distractors = [f"{g + 1} {g}", f"{a + 1} {a + 1}", f"{a + 1} {a}", NAME_ERROR]
        why = (
            f"Inside `add_one`, `{p}` is the parameter (a local variable) holding {a}, so the "
            f"call returns {a + 1}. The global `{p}` is a different variable and stays {g}."
        )
    else:
        word = rng.choice(["hi", "ready", "go team", "hello"])
        var = rng.choice(["message", "text", "note"])
        fname = rng.choice(["show", "display"])
        code = _prog(f"def {fname}():\n    print({var})", f'{var} = "{word}"\n{fname}()')
        distractors = [NAME_ERROR, UNBOUND, var, NOTHING_PRINTED]
        why = (
            "A function looks up global names when it is *called*, not when it is defined. "
            f"By the time `{fname}()` runs, `{var}` already exists, so it prints {word}."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)


@generator(TOPIC, EASY)
def gen_fill_return(rng: random.Random) -> Question:
    """Which line completes the function? (return vs print vs a bare expression)."""
    name, body, (w1, w2) = rng.choice(_ONE_ARG)
    p = rng.choice(_PARAMS)
    a = rng.randint(2, 9)
    k = rng.randint(1, 5)
    expr = body.format(p=p)
    code = _prog(f"def {name}({p}):\n    {BLANK}", f"result = {name}({a}) + {k}\nprint(result)")
    target = str(_calc(body, a) + k)
    correct = f"return {expr}"
    wrong = [
        f"print({expr})",
        expr,
        f"return {w1.format(p=p)}",
        f"{p} = {expr}",
        f"return {w2.format(p=p)}",
        f"return {p}",
    ]

    def prints(line: str) -> str:
        res = run_code(code.replace(BLANK, line))
        return "ERR" if res.error else res.output

    if prints(correct) != target:
        raise GenerationError(f"{correct!r} does not print {target!r}")
    distractors = [w for w in wrong if prints(w) != target]
    why = (
        f"Only `return` hands a value back to the caller, so `{correct}` makes "
        f"`{name}({a})` evaluate to {_calc(body, a)} and `result` becomes {target}. With "
        f"`print(...)` or a bare expression the function returns `None`, and `None + {k}` "
        "raises a `TypeError`."
    )
    return _choice(
        difficulty=EASY,
        prompt=f"Which line fills the blank so the code prints `{target}`?",
        code=code,
        correct=correct,
        distractors=distractors,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# MEDIUM
# ==========================================================================

# (function source, argument source, (first, second) returned, names to unpack into)
def _pair_function(rng: random.Random):
    kind = rng.choice(["min_max", "split_time", "first_last", "divide"])
    if kind == "min_max":
        nums = rng.sample(range(1, 20), 4)
        src = "def min_max(nums):\n    return min(nums), max(nums)"
        return src, f"min_max({nums})", (min(nums), max(nums)), ("low", "high")
    if kind == "split_time":
        minutes = rng.choice([m for m in range(65, 200) if m % 60 > 1 and m % 60 != m // 60])
        src = "def split_time(minutes):\n    return minutes // 60, minutes % 60"
        return src, f"split_time({minutes})", (minutes // 60, minutes % 60), ("hours", "mins")
    if kind == "first_last":
        words = rng.sample(["red", "blue", "green", "gold", "pink", "teal", "gray"], 3)
        src = "def first_last(items):\n    return items[0], items[-1]"
        arg = "[" + ", ".join(f'"{w}"' for w in words) + "]"
        return src, f"first_last({arg})", (words[0], words[-1]), ("first", "last")
    b = rng.randint(3, 6)
    a = b * rng.randint(2, 6) + rng.randint(1, b - 1)
    if a // b == a % b:
        a += 1 if a % b < b - 1 else -1
    src = "def divide(a, b):\n    return a // b, a % b"
    return src, f"divide({a}, {b})", (a // b, a % b), ("whole", "left")


@generator(TOPIC, MEDIUM)
def gen_return_multiple(rng: random.Random) -> Question:
    """``return a, b`` returns ONE tuple, which can be unpacked or indexed."""
    src, call, (x, y), (n1, n2) = _pair_function(rng)
    rx, ry = repr(x), repr(y)
    tup = f"({rx}, {ry})"
    shape = rng.choice(["print", "unpack", "index", "type", "too_many"])
    allow_error = shape == "too_many"
    if shape == "print":
        code = _prog(src, f"print({call})")
        distractors = [f"{x} {y}", f"[{rx}, {ry}]", rx, f"{x}\n{y}"]
        ret = src.split("return ")[1]
        why = (
            f"`return {ret}` sends back both values packed into ONE tuple, so `print` shows "
            f"the tuple {tup} (with parentheses)."
        )
    elif shape == "unpack":
        code = _prog(src, f"{n1}, {n2} = {call}\nprint({n2}, {n1})")
        distractors = [f"{x} {y}", f"({ry}, {rx})", tup, VALUE_ERROR]
        why = (
            f"The function returns the tuple {tup}. Unpacking puts {rx} in `{n1}` and {ry} in "
            f"`{n2}`, and the `print` lists `{n2}` first."
        )
    elif shape == "index":
        code = _prog(src, f"result = {call}\nprint(result[1])")
        distractors = [x, tup, TYPE_ERROR, f"({ry},)"]
        why = f"`result` is the tuple {tup}. Tuples are indexed from 0, so `result[1]` is {ry}."
    elif shape == "type":
        code = _prog(src, f"result = {call}\nprint(type(result))")
        first_type = type(x).__name__
        distractors = ["<class 'list'>", f"<class '{first_type}'>", "<class 'NoneType'>", "<class 'dict'>"]
        why = (
            "Writing two values after `return`, separated by a comma, packs them into a tuple, "
            f"so `result` is {tup} and its type is `tuple`."
        )
    else:
        code = _prog(src, f"a, b, c = {call}\nprint(a)")
        distractors = [rx, tup, TYPE_ERROR, "None"]
        why = (
            "The function returns a tuple of 2 values, but the code tries to unpack it into 3 "
            "names. Unpacking needs exactly as many names as values, so it raises a `ValueError`."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)


@generator(TOPIC, MEDIUM)
def gen_early_return(rng: random.Random) -> Question:
    """``return`` exits immediately — even from inside a loop."""
    shape = rng.choice(["first_match", "first_match", "return_in_loop", "guard"])
    if shape == "first_match":
        kind = rng.choice(["even", "over"])
        found = rng.random() < 0.8
        if kind == "even":
            test, fname, args = "n % 2 == 0", "first_even", ""
            odds = [v for v in range(1, 20) if v % 2]
            evens = [v for v in range(2, 21) if v % 2 == 0]
            if found:
                nums = rng.sample(odds, 3) + rng.sample(evens, 2)
                rng.shuffle(nums)
                if nums[0] % 2 == 0:  # make the first element a non-match
                    i = next(i for i, v in enumerate(nums) if v % 2)
                    nums[0], nums[i] = nums[i], nums[0]
            else:
                nums = rng.sample(odds, 4)
            matches = [v for v in nums if v % 2 == 0]
            head = "def first_even(nums):"
        else:
            limit = rng.randint(8, 14)
            test, fname, args = "n > limit", "first_over", f", {limit}"
            low = list(range(1, limit + 1))
            high = list(range(limit + 1, limit + 15))
            if found:
                nums = rng.sample(low, 3) + rng.sample(high, 2)
                rng.shuffle(nums)
                if nums[0] > limit:
                    i = next(i for i, v in enumerate(nums) if v <= limit)
                    nums[0], nums[i] = nums[i], nums[0]
            else:
                nums = rng.sample(low, 4)
            matches = [v for v in nums if v > limit]
            head = "def first_over(nums, limit):"
        code = _prog(
            f"{head}\n    for n in nums:\n        if {test}:\n            return n\n    return -1",
            f"print({fname}({nums}{args}))",
        )
        if found:
            first = matches[0]
            distractors = [matches[-1], matches, -1, nums.index(first), nums[0]]
            why = (
                f"The loop checks the numbers in order and `return n` exits the function at the "
                f"first match, {first}. The loop never reaches {matches[-1]}."
            )
        else:
            distractors = ["None", nums[-1], nums[0], "[]"]
            why = (
                "No number passes the test, so the `return n` inside the loop never runs. The "
                "loop finishes and the function reaches `return -1`."
            )
        return _output(code, MEDIUM, distractors, why, rng)
    if shape == "return_in_loop":
        fname = rng.choice(["total", "add_up", "sum_all"])
        var = rng.choice(["result", "running", "acc"])
        nums = rng.sample(range(1, 10), rng.randint(3, 4))
        code = _prog(
            f"def {fname}(nums):\n    {var} = 0\n    for n in nums:\n        {var} += n\n"
            f"        return {var}",
            f"print({fname}({nums}))",
        )
        distractors = [sum(nums), nums[-1], sum(nums[:2]), "None", 0]
        why = (
            f"`return {var}` is indented inside the `for` loop, so it runs at the end of the "
            f"FIRST pass: the function returns {nums[0]} before the other numbers are added."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    guard, word, bad, good = rng.choice(
        [
            ("n < 0", "negative", rng.randint(-9, -1), rng.randint(1, 9)),
            ("n == 0", "zero", 0, rng.randint(1, 9)),
            ("n > 100", "too big", rng.randint(101, 150), rng.randint(1, 99)),
        ]
    )
    calls = [bad, good] if rng.random() < 0.5 else [good, bad]
    fname = rng.choice(["check", "check_value"])
    code = _prog(
        f'def {fname}(n):\n    if {guard}:\n        return "{word}"\n    print("checking", n)\n'
        '    return "ok"',
        f"print({fname}({calls[0]}))\nprint({fname}({calls[1]}))",
    )

    def model(mode: str) -> str:
        out = []
        for n in calls:
            if n == bad and mode != "no_stop":
                if mode == "print_anyway":
                    out.append(f"checking {n}")
                out.append(word)
                continue
            if mode != "skip_print":
                out.append(f"checking {n}")
            out.append("ok")
        return "\n".join(out)

    distractors = [model("print_anyway"), model("skip_print"), model("no_stop")]
    why = (
        f"For {bad}, the condition `{guard}` is true, so `return \"{word}\"` ends the call "
        f'right away and the `print("checking", n)` line is skipped. For {good} the function '
        "carries on, prints, then returns \"ok\"."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_global_vs_local(rng: random.Random) -> Question:
    """Assigning inside a function creates a local unless you declare ``global``."""
    var = rng.choice(["score", "lives", "level", "count"])
    shape = rng.choice(["shadow", "global_assign", "global_counter", "param_discard", "param_assign"])
    if shape == "shadow":
        g, local = rng.randint(5, 20), rng.randint(0, 4)
        fname = rng.choice(["reset", "update", "change"])
        code = _prog(
            f"{var} = {g}",
            f'def {fname}():\n    {var} = {local}\n    print("inside:", {var})',
            f'{fname}()\nprint("outside:", {var})',
        )
        distractors = [
            f"inside: {local}\noutside: {local}",
            UNBOUND,
            f"inside: {g}\noutside: {g}",
            f"inside: {g}\noutside: {local}",
        ]
        why = (
            f"Assigning `{var} = {local}` inside `{fname}` creates a new LOCAL variable that "
            f"only exists during the call. The global `{var}` is untouched and is still {g}."
        )
    elif shape == "global_assign":
        g, new = rng.randint(5, 20), rng.randint(0, 4)
        fname = rng.choice(["reset", "update", "change"])
        code = _prog(
            f"{var} = {g}",
            f"def {fname}():\n    global {var}\n    {var} = {new}",
            f"print({var})\n{fname}()\nprint({var})",
        )
        distractors = [f"{g}\n{g}", f"{new}\n{new}", UNBOUND, f"{g}\nNone"]
        why = (
            f"`global {var}` tells Python that `{var}` inside `{fname}` means the global "
            f"variable, so the assignment changes it from {g} to {new}."
        )
    elif shape == "global_counter":
        a, b = rng.sample(range(2, 10), 2)
        start = rng.choice([0, 0, 1, 10])
        fname = rng.choice(["add", "add_points", "deposit"])
        code = _prog(
            f"{var} = {start}",
            f"def {fname}(n):\n    global {var}\n    {var} += n",
            f"{fname}({a})\n{fname}({b})\nprint({var})",
        )
        distractors = [start + b, start, UNBOUND, a + b if start else start + a, start + a]
        why = (
            f"Because of `global {var}`, each call updates the same global variable: "
            f"{start} + {a} + {b} = {start + a + b}."
        )
    else:
        g, k = rng.randint(1, 9), rng.randint(2, 6)
        fname = rng.choice(["bump", "boost", "grow"])
        func = f"def {fname}({var}):\n    {var} += {k}\n    return {var}"
        if shape == "param_discard":
            code = _prog(f"{var} = {g}", func, f"{fname}({var})\nprint({var})")
            distractors = [g + k, UNBOUND, "None", k]
            why = (
                f"The parameter `{var}` is a separate LOCAL variable that starts with the value "
                f"{g}; `+= {k}` changes only that local. The returned {g + k} is never stored, so "
                f"the global `{var}` is still {g}."
            )
        else:
            code = _prog(f"{var} = {g}", func, f"{var} = {fname}({var})\nprint({var})")
            distractors = [g, UNBOUND, "None", g + 2 * k]
            why = (
                f"The function's local `{var}` becomes {g + k} and is returned. Assigning the "
                f"result back with `{var} = {fname}({var})` updates the global to {g + k}."
            )
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR)


def _two_steps(rng: random.Random, x: int):
    """Two different helpers f, g whose order matters for ``x``."""
    for _ in range(50):
        (fn, fb), (gn, gb) = rng.sample(_STEPS, 2)
        f, g = _step_fn(fb), _step_fn(gb)
        if f(g(x)) != g(f(x)):
            return (fn, fb, f), (gn, gb, g)
    raise GenerationError("no non-commuting pair found")


@generator(TOPIC, MEDIUM)
def gen_composition(rng: random.Random) -> Question:
    """Nested calls ``f(g(x))`` run the inner call first; helpers calling helpers."""
    shape = rng.choice(["nested", "nested", "both_orders", "helper"])
    if shape == "helper":
        a, b = rng.sample(range(2, 7), 2)
        op, outer = rng.choice([("+", "sum_of_squares"), ("-", "diff_of_squares")])
        code = _prog(
            "def square(n):\n    return n * n",
            f"def {outer}(a, b):\n    return square(a) {op} square(b)",
            f"print({outer}({a}, {b}))",
        )
        sign = 1 if op == "+" else -1
        ans = a * a + sign * b * b
        distractors = [
            (a + sign * b) ** 2,
            2 * a + sign * 2 * b,
            a + sign * b,
            a * a + sign * b,
        ]
        why = (
            f"`{outer}` calls `square` twice: `square({a})` is {a * a} and `square({b})` is "
            f"{b * b}, so it returns {a * a} {op} {b * b} = {ans}."
        )
        return _output(code, MEDIUM, _nums(distractors, ans, rng), why, rng)
    deep = shape == "nested" and rng.random() < 0.5
    x = rng.randint(2, 4) if deep else rng.randint(2, 6)
    (fn, fb, f), (gn, gb, g) = _two_steps(rng, x)
    while deep and abs(f(g(f(x)))) > 200:  # keep the arithmetic mental-math friendly
        (fn, fb, f), (gn, gb, g) = _two_steps(rng, x)
    defs = [f"def {fn}(n):\n    return {fb}", f"def {gn}(n):\n    return {gb}"]
    if rng.random() < 0.5:
        defs.reverse()
    if shape == "nested":
        if not deep:
            code = _prog(*defs, f"print({fn}({gn}({x})))")
            ans = f(g(x))
            distractors = [g(f(x)), g(x), f(x), f(f(x))]
            why = (
                f"The inner call runs first: `{gn}({x})` returns {g(x)}, and that value is passed "
                f"to `{fn}`, which returns {ans}."
            )
        else:
            code = _prog(*defs, f"print({fn}({gn}({fn}({x}))))")
            ans = f(g(f(x)))
            distractors = [g(f(g(x))), f(g(x)), g(f(x)), f(f(g(x)))]
            why = (
                f"Work from the inside out: `{fn}({x})` is {f(x)}, then `{gn}({f(x)})` is "
                f"{g(f(x))}, and finally `{fn}({g(f(x))})` is {ans}."
            )
        return _output(code, MEDIUM, _nums(distractors, ans, rng), why, rng)
    a, b = f(g(x)), g(f(x))
    code = _prog(*defs, f"print({fn}({gn}({x})), {gn}({fn}({x})))")
    distractors = [f"{b} {a}", f"{a} {a}", f"{b} {b}", f"{f(x)} {g(x)}", f"{g(x)} {f(x)}"]
    why = (
        f"Always start with the innermost call. `{fn}({gn}({x}))` is `{fn}({g(x)})` = {a}, while "
        f"`{gn}({fn}({x}))` is `{gn}({f(x)})` = {b}. The order of nesting matters."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_args_kwargs(rng: random.Random) -> Question:
    """``*args`` collects extra positional arguments in a tuple, ``**kwargs`` in a dict."""
    shape = rng.choice(["count", "show", "first_rest", "kwargs_dict", "kwargs_items"])
    vals = rng.sample(range(1, 10), 3)
    prompt, allow_error = PRINT, False
    if shape == "count":
        fname = rng.choice(["count_args", "how_many"])
        func = f"def {fname}(*args):\n    return len(args)"
        if rng.random() < 0.6:
            code = _prog(func, f"print({fname}({', '.join(map(str, vals))}), {fname}({vals}))")
            distractors = ["3 3", "1 1", "3 0", TYPE_ERROR]
            why = (
                "`*args` collects each positional argument as one item. The first call passes "
                f"3 numbers; the second passes ONE argument (the list {vals}), so `args` has 1 item."
            )
        else:
            code = _prog(func, f"print({fname}({vals[0]}, {vals[1]}), {fname}())")
            distractors = ["2 1", TYPE_ERROR, "2 None", "1 0"]
            why = (
                "`*args` collects all positional arguments into a tuple. With no arguments the "
                "tuple is empty, so `len(args)` is 0 and no error is raised."
            )
        prompt = PRINT_OR_ERROR
    elif shape == "show":
        if rng.random() < 0.5:
            items = vals
            call = ", ".join(map(str, items))
        else:
            items = rng.sample(["a", "b", "c", "x", "y"], rng.randint(2, 3))
            call = ", ".join(f'"{s}"' for s in items)
        fname = rng.choice(["show", "display"])
        code = _prog(f"def {fname}(*items):\n    print(items)", f"{fname}({call})")
        distractors = [str(items), " ".join(map(str, items)), repr(items[0]), f"({tuple(items)},)"]
        why = (
            "`*items` packs all the positional arguments into a TUPLE, so `print(items)` "
            f"shows {tuple(items)}."
        )
    elif shape == "first_rest":
        fname = rng.choice(["split_first", "head_and_rest"])
        code = _prog(
            f"def {fname}(first, *rest):\n    print(first, rest)", f"{fname}({', '.join(map(str, vals))})"
        )
        a, b, c = vals
        distractors = [f"{a} [{b}, {c}]", f"{a} {b} {c}", f"{a} ({a}, {b}, {c})", f"({a}, {b}, {c}) ()"]
        why = (
            f"The first argument fills the normal parameter `first` ({a}); `*rest` collects "
            f"whatever is left into a tuple: ({b}, {c})."
        )
    elif shape == "kwargs_dict":
        (k1, v1), (k2, v2) = rng.sample(
            [("name", f'"{rng.choice(NAMES)}"'), ("age", str(rng.randint(8, 16))),
             ("city", '"Paris"'), ("level", str(rng.randint(2, 9))), ("pet", '"cat"')],
            2,
        )
        fname = rng.choice(["profile", "describe"])
        code = _prog(f"def {fname}(**info):\n    print(info)", f"{fname}({k1}={v1}, {k2}={v2})")
        r1, r2 = repr(eval(v1)), repr(eval(v2))  # noqa: S307 - literals we built
        distractors = [
            f"{{{k1}: {r1}, {k2}: {r2}}}",
            f"['{k1}', '{k2}']",
            f"({r1}, {r2})",
            f"{k1}={r1}, {k2}={r2}",
        ]
        why = (
            "`**info` collects the keyword arguments into a dictionary: the parameter names "
            f"become string keys ('{k1}', '{k2}'), in the order they were passed."
        )
    else:
        pairs = rng.sample([("size", 3), ("color", '"red"'), ("speed", 7), ("shape", '"star"')], 2)
        call = ", ".join(f"{k}={v}" for k, v in pairs)
        code = _prog(
            "def settings(**options):\n    for key, value in options.items():\n        print(key, value)",
            f"settings({call})",
        )
        plain = [(k, str(v).strip('"')) for k, v in pairs]
        distractors = [
            _lines(*(v for _, v in plain)),
            _lines(*(k for k, _ in plain)),
            _lines(*(f"{k} {v}" for k, v in reversed(plain))),
            f"{plain[0][0]} {plain[0][1]}",
        ]
        why = (
            "`**options` is a dictionary of the keyword arguments, so `.items()` gives each "
            "name with its value, in the order they were passed."
        )
    return _output(code, MEDIUM, distractors, why, rng, prompt=prompt, allow_error=allow_error)


@generator(TOPIC, MEDIUM)
def gen_lambda(rng: random.Random) -> Question:
    """Small anonymous functions passed to sorted/max/filter or another function."""
    shape = rng.choice(["sort_key", "max_key", "apply_twice", "ops_dict", "filter"])
    if shape == "sort_key":
        while True:
            digits = rng.sample(range(1, 10), 4)
            tens = rng.sample(range(1, 10), 4)
            nums = [t * 10 + d for t, d in zip(tens, digits)]
            ans = sorted(nums, key=lambda n: n % 10)
            if ans not in (sorted(nums), sorted(nums, reverse=True), nums):
                break
        code = f"nums = {nums}\nprint(sorted(nums, key=lambda n: n % 10))"
        distractors = [sorted(nums), sorted(digits), ans[::-1], sorted(nums, reverse=True), nums]
        why = (
            "The `key` function is applied to each item and the items are ordered by those "
            f"results. `n % 10` is the last digit, so the numbers are sorted by {sorted(digits)}."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    if shape == "max_key":
        names = rng.sample(NAMES, 4)
        scores = rng.sample(range(2, 30), 4)
        pairs = list(zip(names, scores))
        want_max = rng.random() < 0.6
        fn = "max" if want_max else "min"
        var = "best" if want_max else "lowest"
        ranked = sorted(pairs, key=lambda pair: pair[1], reverse=want_max)
        pick, runner_up, other = ranked[0], ranked[1], ranked[-1]
        by_name = (max if want_max else min)(pairs)
        code = (
            "scores = [" + ", ".join(f'("{n}", {s})' for n, s in pairs) + "]\n"
            f"{var} = {fn}(scores, key=lambda pair: pair[1])\n"
            f"print({var}[0])"
        )
        distractors = [other[0], by_name[0], pick[1], pairs[0][0], runner_up[0]]
        why = (
            f"`key=lambda pair: pair[1]` makes `{fn}` compare the numbers, not the names. "
            f"The pair with the {'largest' if want_max else 'smallest'} number is {pick}, and "
            f"`[0]` takes its name."
        )
        return _output(code, MEDIUM, distractors, why, rng)
    if shape == "apply_twice":
        k = rng.randint(2, 5)
        start = rng.randint(1, 6)
        op = rng.choice(["+", "*", "-"])
        f = {"+": lambda n: n + k, "*": lambda n: n * k, "-": lambda n: n - k}[op]
        code = _prog(
            "def apply_twice(func, value):\n    return func(func(value))",
            f"print(apply_twice(lambda n: n {op} {k}, {start}))",
        )
        ans = f(f(start))
        distractors = [f(start), f(f(f(start))), start, f(start) * 2]
        why = (
            f"`func` is the lambda `n {op} {k}`. It is applied to {start} giving {f(start)}, "
            f"then applied again to {f(start)} giving {ans}."
        )
        return _output(code, MEDIUM, _nums(distractors, ans, rng), why, rng)
    if shape == "ops_dict":
        ops = {"add": "+", "sub": "-", "mul": "*"}
        keys = list(ops)
        rng.shuffle(keys)
        a, b = rng.randint(6, 12), rng.randint(2, 5)
        k1, k2 = rng.sample(keys, 2)
        code = (
            "ops = {\n"
            + "".join(f'    "{k}": lambda a, b: a {ops[k]} b,\n' for k in keys)
            + "}\n"
            + f'print(ops["{k1}"]({a}, {b}), ops["{k2}"]({b}, {a}))'
        )

        def calc(k, x, y):
            return eval(f"{x} {ops[k]} {y}")  # noqa: S307 - our own arithmetic

        k3 = next(k for k in keys if k not in (k1, k2))
        r1, r2 = calc(k1, a, b), calc(k2, b, a)
        distractors = [
            f"{r1} {calc(k2, a, b)}",
            f"{calc(k2, a, b)} {calc(k1, b, a)}",
            f"{calc(k1, b, a)} {r2}",
            f"{r2} {r1}",
            TYPE_ERROR,
            f"{calc(k3, a, b)} {calc(k3, b, a)}",
        ]
        why = (
            f'`ops["{k1}"]` looks up a lambda, and `({a}, {b})` calls it, giving {r1}. '
            f'`ops["{k2}"]({b}, {a})` gives {r2} — note the arguments are in a different order.'
        )
        return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR)
    nums = rng.sample(range(1, 20), 5)
    limit = sorted(nums)[2]
    code = f"nums = {nums}\nprint(list(filter(lambda n: n > {limit}, nums)))"
    kept = [n for n in nums if n > limit]
    distractors = [
        [n for n in nums if n <= limit],
        [n for n in nums if n >= limit],
        [n > limit for n in nums],
        sorted(kept),
    ]
    why = (
        f"`filter` keeps the items for which the lambda returns `True`. Only the numbers "
        f"greater than {limit} pass, in their original order: {kept}."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_functions_as_values(rng: random.Random) -> Question:
    """Functions are objects: they can be aliased, stored in lists and passed around."""
    shape = rng.choice(["alias", "called_alias", "pipeline", "pipeline", "pass_func", "pass_result"])
    if shape in ("alias", "called_alias"):
        fname, body, trans = rng.choice(
            [
                ("shout", 'text.upper() + "!"', lambda s: s.upper() + "!"),
                ("whisper", 'text.lower() + "..."', lambda s: s.lower() + "..."),
                ("echo", "text + text", lambda s: s + s),
            ]
        )
        alias = rng.choice(["speak", "say", "talk"])
        w1, w2 = rng.sample(["hi", "Hey", "wow", "Yes", "ok", "Go"], 2)
        func = f"def {fname}(text):\n    return {body}"
        if shape == "alias":
            code = _prog(func, f'{alias} = {fname}\nprint({alias}("{w1}"))')
            distractors = [NAME_ERROR, TYPE_ERROR, w1, f"{fname}"]
            why = (
                f"`{alias} = {fname}` (no parentheses) makes `{alias}` another name for the same "
                f'function, so `{alias}("{w1}")` calls `{fname}` and returns {trans(w1)}.'
            )
            allow_error = False
        else:
            code = _prog(func, f'{alias} = {fname}("{w1}")\nprint({alias}("{w2}"))')
            distractors = [trans(w2), trans(w1), NAME_ERROR, w2]
            why = (
                f'`{fname}("{w1}")` has parentheses, so it CALLS the function: `{alias}` is the '
                f"string {trans(w1)!r}, not a function. Calling a string raises a `TypeError`."
            )
            allow_error = True
        return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)
    if shape == "pipeline":
        x = rng.randint(2, 5)
        (fn, fb, f), (gn, gb, g) = _two_steps(rng, x)
        funcs = {fn: f, gn: g}
        order = rng.choice([[fn, gn], [gn, fn], [fn, gn, fn], [gn, fn, gn], [fn, fn, gn]])
        var = rng.choice(["value", "result", "x"])
        code = _prog(
            f"def {fn}(n):\n    return {fb}",
            f"def {gn}(n):\n    return {gb}",
            f"{var} = {x}\nfor step in [{', '.join(order)}]:\n    {var} = step({var})\nprint({var})",
        )

        def chain(names, start):
            for nm in names:
                start = funcs[nm](start)
            return start

        ans = chain(order, x)
        distractors = [chain(order[::-1], x), funcs[order[-1]](x), funcs[order[0]](x), chain(order[:-1], x)]
        why = (
            f"The list holds the functions themselves. Each pass calls the next one on the "
            f"current value: starting from {x}, applying {', '.join(order)} in order gives {ans}."
        )
        return _output(code, MEDIUM, _nums(distractors, ans, rng), why, rng)
    bonus = rng.randint(2, 9)
    score = rng.randint(10, 30)
    bname = rng.choice(["get_bonus", "daily_bonus"])
    func1 = f"def {bname}():\n    return {bonus}"
    func2 = "def total(score, bonus_func):\n    return score + bonus_func()"
    if shape == "pass_func":
        code = _prog(func1, func2, f"print(total({score}, {bname}))")
        distractors = [TYPE_ERROR, score, NAME_ERROR, f"{score}{bonus}"]
        why = (
            f"`{bname}` is passed WITHOUT parentheses, so `bonus_func` is the function itself. "
            f"`bonus_func()` then calls it and gets {bonus}: {score} + {bonus} = {score + bonus}."
        )
        allow_error = False
    else:
        code = _prog(func1, func2, f"print(total({score}, {bname}()))")
        distractors = [score + bonus, score, NAME_ERROR, "None"]
        why = (
            f"`{bname}()` is called first, so `bonus_func` receives the number {bonus}, not a "
            f"function. `bonus_func()` then tries to call an `int`, which raises a `TypeError`."
        )
        allow_error = True
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)


@generator(TOPIC, MEDIUM)
def gen_mixed_arguments(rng: random.Random) -> Question:
    """Positional + keyword + default arguments in one call (or a clash -> TypeError)."""
    fname, (p1, p2, p3) = rng.choice(
        [("cost", ("price", "qty", "shipping")), ("score", ("points", "times", "bonus"))]
    )
    d2 = rng.choice([1, 2])
    d3 = rng.choice([1, 3, 5])
    a = rng.randint(3, 9)
    b = rng.choice([v for v in range(2, 6) if v != d2])
    c = rng.choice([v for v in range(2, 10) if v not in (d3, b, a)])

    def f(x, y=d2, z=d3):
        return x * y + z

    form = rng.choice(
        ["skip_middle", "skip_middle", "positional", "keywords_swapped", "all_keywords", "clash"]
    )
    allow_error = form == "clash"
    if form == "skip_middle":
        call = f"{fname}({a}, {p3}={c})"
        distractors = [f(a, c), f(a), TYPE_ERROR, a + c]
        why = (
            f"`{a}` fills `{p1}` by position, `{p3}={c}` is matched by name, and `{p2}` keeps "
            f"its default {d2}: {a} * {d2} + {c} = {f(a, z=c)}."
        )
    elif form == "positional":
        call = f"{fname}({a}, {b})"
        distractors = [f(a, z=b), a * b, TYPE_ERROR, f(a)]
        why = (
            f"Positional arguments fill parameters left to right: `{p1}` = {a}, `{p2}` = {b}, and "
            f"`{p3}` uses its default {d3}: {a} * {b} + {d3} = {f(a, b)}."
        )
    elif form == "keywords_swapped":
        call = f"{fname}({a}, {p3}={c}, {p2}={b})"
        distractors = [f(a, c, b), TYPE_ERROR, f(a), f(a, b)]
        why = (
            f"Keyword arguments can come in any order — they are matched by name. So `{p2}` is "
            f"{b} and `{p3}` is {c}: {a} * {b} + {c} = {f(a, b, c)}."
        )
    elif form == "all_keywords":
        call = f"{fname}({p3}={c}, {p1}={a})"
        distractors = [f(c, z=a), TYPE_ERROR, f(a), f(a, c)]
        why = (
            f"Every argument here is matched by name: `{p1}` = {a}, `{p3}` = {c}, and `{p2}` "
            f"uses its default {d2}: {a} * {d2} + {c} = {f(a, z=c)}."
        )
    else:
        call = f"{fname}({a}, {p1}={c})"
        distractors = [f(c), f(a), f(a, c), NAME_ERROR]
        why = (
            f"The positional {a} already fills `{p1}`, and then `{p1}={c}` tries to give it a "
            "second value. Python refuses with a `TypeError` (multiple values for the argument)."
        )
    code = _prog(
        f"def {fname}({p1}, {p2}={d2}, {p3}={d3}):\n    return {p1} * {p2} + {p3}", f"print({call})"
    )
    distractors = _nums(distractors, f(c) if allow_error else int(_run(code)), rng)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)


def _distinct_value_exprs(exprs, setup: str, target) -> list[str]:
    """Keep wrong expressions whose values differ from the target AND from each other.

    Two equivalent wrong calls (e.g. ``power(3, 2)`` and ``power(base=3, exp=2)``) would let a
    player eliminate both without understanding either, so only the first one is kept.
    """
    seen: list = [target]
    out = []
    for e in exprs:
        res = run_code(f"{setup}\n__value = {e}")
        value = ("error", res.error) if res.error else res.namespace["__value"]
        if value in seen:
            continue
        seen.append(value)
        out.append(e)
    return out


@generator(TOPIC, MEDIUM)
def gen_which_call(rng: random.Random) -> Question:
    """Which call returns the target value? (positional order, defaults, keywords)."""
    shape = rng.choice(["power", "scale", "greet"])
    if shape == "power":
        d = 2
        exp = rng.choice([2, 3, 3])
        base = rng.choice([b for b in range(2, 6) if b != exp])
        target = base ** exp
        setup = f"def power(base, exp={d}):\n    return base ** exp"
        if exp == d:
            correct = rng.choice([f"power({base})", f"power(exp={exp}, base={base})"])
        else:
            correct = rng.choice([f"power({base}, {exp})", f"power(exp={exp}, base={base})"])
        wrong = [
            f"power({exp}, {base})",
            f"power(base={exp}, exp={base})",
            f"power({target})",
            f"power({exp})",
            f"power({base}, {exp + 1})",
            f"power({base * exp})",
            f"power({base}, {exp - 1})",
            f"power({base}, {base}, {exp})",
        ]
        why = (
            f"`{correct}` gives `base` = {base} and `exp` = {exp}, so it returns "
            f"{base} ** {exp} = {target}. Swapping the arguments, or leaving out `exp` (default "
            f"{d}), gives a different power."
        )
        shown = str(target)
    elif shape == "scale":
        df = rng.choice([2, 3])
        v, o = rng.sample([n for n in range(2, 8) if n != df], 2)
        fac = rng.choice([x for x in (2, 3, 4, 5) if x not in (df, v, o)])
        use_default = rng.random() < 0.5
        factor = df if use_default else fac
        target = v * factor + o
        setup = f"def scale(value, factor={df}, offset=0):\n    return value * factor + offset"
        if use_default:
            correct = rng.choice([f"scale({v}, offset={o})", f"scale(offset={o}, value={v})"])
        else:
            correct = rng.choice([f"scale({v}, {fac}, {o})", f"scale({v}, offset={o}, factor={fac})"])
        wrong = [
            f"scale({v}, {o})",
            f"scale({o}, offset={v})",
            f"scale({v}, factor={o})",
            f"scale({v}, {o}, {factor})",
            f"scale({factor}, {v}, {o})",
            f"scale({v})",
            f"scale({v}, offset={factor})",
            f"scale(offset={v}, value={o})",
            f"scale({v}, 1, {o})",
        ]
        why = (
            f"`{correct}` sets `value` = {v}, `factor` = {factor} and `offset` = {o}, so it "
            f"returns {v} * {factor} + {o} = {target}. A second positional argument fills "
            "`factor`, not `offset`."
        )
        shown = str(target)
    else:
        dg = rng.choice(["Hello", "Hi"])
        g = rng.choice([w for w in ["Hey", "Welcome", "Good luck", "Bye"] if w != dg])
        name = rng.choice(NAMES)
        target = f"{g}, {name}"
        setup = f'def greet(name, greeting="{dg}"):\n    return greeting + ", " + name'
        correct = rng.choice([f'greet("{name}", "{g}")', f'greet(greeting="{g}", name="{name}")'])
        wrong = [
            f'greet("{g}", "{name}")',
            f'greet("{name}")',
            f'greet(name="{g}", greeting="{name}")',
            f'greet("{g}")',
            f'greet("{name}", greeting="{dg}")',
        ]
        why = (
            f"`{correct}` makes `name` = \"{name}\" and `greeting` = \"{g}\", returning "
            f"\"{target}\". Positional arguments fill `name` first, then `greeting`."
        )
        shown = f'"{target}"'
    wrong = _distinct_value_exprs(wrong, setup, target)
    return which_expression_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which call returns `{shown}`?",
        setup=setup,
        target=target,
        correct_expr=correct,
        wrong_exprs=wrong,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# HARD
# ==========================================================================

_ADD_FUNCS = [
    ("add_item", "item", "items"),
    ("remember", "value", "history"),
    ("collect", "thing", "bag"),
    ("log", "entry", "entries"),
]


@generator(TOPIC, HARD)
def gen_mutable_default(rng: random.Random) -> Question:
    """A list default is created ONCE and shared by every call that uses it."""
    fname, p, lst = rng.choice(_ADD_FUNCS)
    if rng.random() < 0.5:
        x, y, z = rng.sample(range(1, 10), 3)
    else:
        x, y, z = (f'"{w}"' for w in rng.sample(["a", "b", "c", "x", "y", "z"], 3))
    rx, ry, rz = (repr(eval(v)) if isinstance(v, str) else repr(v) for v in (x, y, z))  # noqa: S307
    shape = rng.choice(["sequential", "sequential", "saved", "explicit", "none_fix", "int_default"])
    shared = f"def {fname}({p}, {lst}=[]):\n    {lst}.append({p})\n    return {lst}"
    if shape == "sequential":
        code = _prog(shared, f"print({fname}({x}))\nprint({fname}({y}))")
        distractors = [
            f"[{rx}]\n[{ry}]",
            f"[{rx}, {ry}]\n[{rx}, {ry}]",
            f"[{rx}]\n[{rx}]",
            f"[{ry}]\n[{rx}, {ry}]",
        ]
        why = (
            f"The default list `[]` is created once, when `def` runs, and every call without a "
            f"`{lst}` argument appends to that SAME list. The second call therefore sees {rx} "
            f"already in it."
        )
    elif shape == "saved":
        code = _prog(shared, f"first = {fname}({x})\nsecond = {fname}({y})\nprint(first, second)")
        distractors = [
            f"[{rx}] [{ry}]",
            f"[{rx}] [{rx}, {ry}]",
            f"[{rx}, {ry}] [{ry}]",
            f"[{ry}] [{rx}, {ry}]",
        ]
        why = (
            "Both calls use the one shared default list and return it, so `first` and `second` "
            f"are the same list object. By the time it is printed it holds [{rx}, {ry}]."
        )
    elif shape == "explicit":
        code = _prog(shared, f"print({fname}({x}))\nprint({fname}({y}, []))\nprint({fname}({z}))")
        distractors = [
            f"[{rx}]\n[{ry}]\n[{rz}]",
            f"[{rx}]\n[{rx}, {ry}]\n[{rx}, {ry}, {rz}]",
            f"[{rx}]\n[{ry}]\n[{ry}, {rz}]",
            f"[{rx}]\n[{rx}, {ry}]\n[{rx}, {rz}]",
        ]
        why = (
            f"The middle call passes its own new list, so it does not touch the shared default. "
            f"The third call uses the default again, which still holds {rx} from the first call."
        )
    elif shape == "none_fix":
        code = _prog(
            f"def {fname}({p}, {lst}=None):\n    if {lst} is None:\n        {lst} = []\n"
            f"    {lst}.append({p})\n    return {lst}",
            f"print({fname}({x}))\nprint({fname}({y}))",
        )
        distractors = [f"[{rx}]\n[{rx}, {ry}]", "None\nNone", f"[{rx}, {ry}]\n[{rx}, {ry}]", TYPE_ERROR]
        why = (
            f"Here the default is `None`, and `{lst} = []` runs INSIDE the function, so each call "
            "builds a brand-new list. This is the standard fix for the mutable-default trap."
        )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR)
    else:
        start = rng.choice([0, 0, 10])
        step = rng.randint(1, 5)
        cname, var = rng.choice([("add_point", "points"), ("next_level", "level"), ("bump", "total")])
        code = _prog(
            f"def {cname}({var}={start}):\n    {var} += {step}\n    return {var}",
            f"print({cname}())\nprint({cname}())",
        )
        distractors = [
            f"{start + step}\n{start + 2 * step}",
            f"{start}\n{start + step}",
            f"{start}\n{start}",
            UNBOUND,
        ]
        why = (
            f"The default {start} is an int, and ints cannot be changed in place: `{var} += {step}` "
            f"makes the local `{var}` refer to a NEW int. The default stays {start}, so both calls "
            f"return {start + step}."
        )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR)
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR)


@generator(TOPIC, HARD)
def gen_unbound_local(rng: random.Random) -> Question:
    """Assigning to a name ANYWHERE in a function makes it local everywhere in it."""
    var = rng.choice(["count", "total", "score", "x"])
    g = rng.randint(2, 9)
    k = rng.randint(1, 5)
    shape = rng.choice(["augmented", "read_then_assign", "read_only", "with_global", "branch"])
    allow_error = shape in ("augmented", "read_then_assign", "branch")
    if shape == "augmented":
        fname = rng.choice(["bump", "increase"])
        code = _prog(
            f"{var} = {g}", f"def {fname}():\n    {var} += {k}\n    return {var}", f"print({fname}())"
        )
        distractors = [g + k, NAME_ERROR, g, "None"]
        why = (
            f"`{var} += {k}` assigns to `{var}`, so Python treats `{var}` as LOCAL for the whole "
            "function. Reading it to compute the new value fails because the local has no value "
            "yet: `UnboundLocalError`. Adding `global` would fix it."
        )
    elif shape == "read_then_assign":
        new = g + k
        fname = rng.choice(["show", "report"])
        code = _prog(f"{var} = {g}", f"def {fname}():\n    print({var})\n    {var} = {new}", f"{fname}()")
        distractors = [g, new, NAME_ERROR, f"{g}\n{new}"]
        why = (
            f"Because `{var}` is assigned later in `{fname}`, it is local everywhere in the "
            f"function, even on the line before the assignment. So `print({var})` reads a local "
            "that has no value yet and raises `UnboundLocalError`."
        )
    elif shape == "read_only":
        fname = rng.choice(["show", "report"])
        code = _prog(f"{var} = {g}", f"def {fname}():\n    print({var} + {k})", f"{fname}()\nprint({var})")
        distractors = [UNBOUND, f"{g + k}\n{g + k}", NAME_ERROR, f"{g}\n{g}"]
        why = (
            f"`{fname}` only READS `{var}` and never assigns it, so `{var}` is the global {g}. "
            f"It prints {g + k} and the global is unchanged, so {g} is printed next."
        )
    elif shape == "with_global":
        fname = rng.choice(["bump", "increase"])
        code = _prog(
            f"{var} = {g}",
            f"def {fname}():\n    global {var}\n    {var} += {k}\n    return {var}",
            f"print({fname}(), {var})",
        )
        distractors = [UNBOUND, f"{g + k} {g}", f"{g} {g + k}", NAME_ERROR]
        why = (
            f"`global {var}` makes `{var}` inside `{fname}` refer to the global variable, so "
            f"`+= {k}` updates it to {g + k}. The return value and the global are both {g + k}."
        )
    else:
        flag = rng.random() < 0.4
        fname = rng.choice(["report", "check"])
        code = _prog(
            f"{var} = {g}",
            f"def {fname}(reset):\n    if reset:\n        {var} = 0\n    return {var}",
            f"print({fname}({flag}))",
        )
        if flag:
            distractors = [UNBOUND, g, NAME_ERROR, "None"]
            why = (
                f"`reset` is True, so the local `{var}` is set to 0 and returned. (With "
                f"`False` the same code would crash: the assignment makes `{var}` local "
                "everywhere in the function.)"
            )
            allow_error = False
        else:
            distractors = [g, 0, NAME_ERROR, "None"]
            why = (
                f"Even though `{var} = 0` never runs, its mere presence makes `{var}` local in "
                f"the whole function. With `reset` False, `return {var}` reads a local that was "
                "never assigned: `UnboundLocalError`."
            )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)


@generator(TOPIC, HARD)
def gen_closures(rng: random.Random) -> Question:
    """Inner functions remember their enclosing variables; ``nonlocal`` rebinds them."""
    shape = rng.choice(["counter", "counter", "factory", "nonlocal"])
    if shape == "counter":
        s1, s2 = rng.sample(range(1, 6), 2)
        n1, n2 = rng.choice([("first", "second"), ("a", "b"), ("red", "blue")])
        pattern = rng.choice([(n1, n2, n1), (n2, n1, n1), (n1, n1, n2)])
        code = _prog(
            "def make_counter(step):\n    count = 0\n\n    def tick():\n        nonlocal count\n"
            "        count += step\n        return count\n    return tick",
            f"{n1} = make_counter({s1})\n{n2} = make_counter({s2})\n{n1}()\n"
            f"print({', '.join(f'{c}()' for c in pattern)})",
        )
        steps = {n1: s1, n2: s2}

        def model(mode: str) -> str:
            counts = {n1: 0, n2: 0}
            shared = 0
            out = []
            calls = ([] if mode == "skip_bare" else [n1]) + list(pattern)
            for i, c in enumerate(calls):
                if mode == "shared":
                    shared += steps[c]
                    val = shared
                elif mode == "reset":
                    val = steps[c]
                else:
                    counts[c] += steps[c]
                    val = counts[c]
                if i >= len(calls) - 3:
                    out.append(str(val))
            return " ".join(out)

        distractors = [model("skip_bare"), model("shared"), model("reset")]
        why = (
            f"Each call to `make_counter` creates a NEW `count` that its `tick` remembers, so "
            f"`{n1}` counts by {s1} and `{n2}` counts by {s2} independently. The bare `{n1}()` "
            "call still advances `{n1}`'s count before the print."
        ).replace("{n1}", n1)
        return _output(code, HARD, distractors, why, rng)
    if shape == "factory":
        maker, param, inner, op, names = rng.choice(
            [
                ("make_multiplier", "factor", "multiply", "*", ("double", "triple")),
                ("make_adder", "amount", "add", "+", ("add_two", "add_ten")),
            ]
        )
        vals = (2, 3) if op == "*" else (2, 10)
        n = rng.randint(3, 9)
        order = rng.random() < 0.5
        call = f"{names[0]}({n}), {names[1]}({n})" if order else f"{names[1]}({n}), {names[0]}({n})"
        code = _prog(
            f"def {maker}({param}):\n    def {inner}(n):\n        return n {op} {param}\n    return {inner}",
            f"{names[0]} = {maker}({vals[0]})\n{names[1]} = {maker}({vals[1]})\nprint({call})",
        )

        def ap(v):
            return n * v if op == "*" else n + v

        r0, r1 = ap(vals[0]), ap(vals[1])
        pair = (r0, r1) if order else (r1, r0)
        last = r1  # what everyone would get if the 2nd make_* call "overwrote" the first
        first = r0
        distractors = [f"{last} {last}", f"{first} {first}", f"{n} {n}", f"{pair[1]} {pair[0]}"]
        why = (
            f"Each call to `{maker}` creates a new `{param}`, and the returned `{inner}` "
            f"remembers its own one: `{names[0]}` keeps {vals[0]} and `{names[1]}` keeps "
            f"{vals[1]}. The second call does not overwrite the first."
        )
        return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR)
    start, new = rng.sample(range(1, 20), 2)
    use_nonlocal = rng.random() < 0.5
    var = rng.choice(["total", "level", "status"])
    body = f"        nonlocal {var}\n" if use_nonlocal else ""
    code = _prog(
        f"def outer():\n    {var} = {start}\n\n    def change():\n{body}        {var} = {new}\n"
        f"    change()\n    return {var}",
        "print(outer())",
    )
    if use_nonlocal:
        distractors = [start, UNBOUND, NAME_ERROR, "None"]
        why = (
            f"`nonlocal {var}` makes `{var}` inside `change` refer to `outer`'s variable, so the "
            f"assignment changes it to {new} before `outer` returns it."
        )
    else:
        distractors = [new, UNBOUND, "None", NAME_ERROR]
        why = (
            f"Without `nonlocal`, `{var} = {new}` inside `change` creates a new LOCAL variable "
            f"of `change`. `outer`'s own `{var}` is untouched, so it returns {start}."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR)


@generator(TOPIC, HARD)
def gen_star_args_binding(rng: random.Random) -> Question:
    """How arguments bind to ``*args``, keyword-only parameters and ``**kwargs``."""
    shape = rng.choice(["sep_positional", "sep_keyword", "unpack_call", "kwargs_default", "all_three"])
    allow_error = False
    if shape in ("sep_positional", "sep_keyword"):
        words = rng.sample(["red", "sun", "cat", "map", "box", "owl"], 2)
        sep = rng.choice(["-", "+", "/"])
        args = ", ".join(f'"{w}"' for w in words)
        call = f'join_all({args}, "{sep}")' if shape == "sep_positional" else f'join_all({args}, sep="{sep}")'
        code = _prog('def join_all(*words, sep=" "):\n    return sep.join(words)', f"print({call})")
        spaced = " ".join(words)
        joined = sep.join(words)
        if shape == "sep_positional":
            distractors = [joined, TYPE_ERROR, spaced, f"{spaced}{sep}"]
            why = (
                f'`*words` swallows EVERY positional argument, including "{sep}". A parameter '
                "after `*words` can only be set by keyword, so `sep` keeps its default space."
            )
        else:
            distractors = [f"{spaced} {sep}", TYPE_ERROR, spaced, f"{words[0]}{sep}"]
            why = (
                f'`sep="{sep}"` is passed by keyword, so it sets the parameter `sep` instead of '
                f"being collected into `words`. The two words are joined with {sep!r}."
            )
    elif shape == "unpack_call":
        nums = rng.sample(range(1, 10), rng.randint(2, 4))
        code = _prog(
            "def count(*args):\n    return len(args)",
            f"nums = {nums}\nprint(count(nums), count(*nums))",
        )
        n = len(nums)
        distractors = [f"{n} {n}", "1 1", f"{n} 1", TYPE_ERROR]
        why = (
            f"`count(nums)` passes ONE argument (the list), so `args` is a 1-item tuple. "
            f"`count(*nums)` unpacks the list into {n} separate arguments."
        )
    elif shape == "kwargs_default":
        name = rng.choice(["box", "cup", "kite", "lamp"])
        size = rng.randint(2, 9)
        color = rng.choice(["red", "blue", "green"])
        order = rng.random() < 0.5
        kws = f'color="{color}", size={size}' if order else f'size={size}, color="{color}"'
        code = _prog(
            "def make(name, size=1, **extra):\n    print(name, size, extra)", f'make("{name}", {kws})'
        )
        both = (
            f"{{'color': '{color}', 'size': {size}}}" if order else f"{{'size': {size}, 'color': '{color}'}}"
        )
        distractors = [
            f"{name} 1 {both}",
            f"{name} {size} {both}",
            TYPE_ERROR,
            f"{name} {color} {{'size': {size}}}",
        ]
        why = (
            f"`size={size}` matches the named parameter `size`, so it is NOT put in `extra`. "
            f"Only keywords with no matching parameter end up in `**extra`: {{'color': '{color}'}}."
        )
    else:
        a, b, c = rng.sample(range(1, 10), 3)
        key = rng.choice(["mode", "flag", "tag"])
        val = rng.randint(1, 9)
        code = _prog(
            "def report(first, *rest, **options):\n    print(first, rest, options)",
            f"report({a}, {b}, {c}, {key}={val})",
        )
        distractors = [
            f"{a} [{b}, {c}] {{'{key}': {val}}}",
            f"{a} ({b}, {c}, {val}) {{}}",
            f"({a}, {b}, {c}) {{'{key}': {val}}}",
            f"{a} ({a}, {b}, {c}) {{'{key}': {val}}}",
        ]
        why = (
            f"`first` takes {a}, `*rest` collects the remaining positional arguments into the "
            f"tuple ({b}, {c}), and `**options` collects the keyword argument into a dict."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)


@generator(TOPIC, HARD)
def gen_trace_calls(rng: random.Random) -> Question:
    """Trace the order of prints through nested and chained calls."""
    shape = rng.choice(["nested", "sum", "inner_outer"])
    if shape in ("nested", "sum"):
        x = rng.randint(2, 6)
        (fn, fb, f), (gn, gb, g) = _two_steps(rng, x)
        defs = (
            f'def {fn}(n):\n    print("{fn}", n)\n    return {fb}',
            f'def {gn}(n):\n    print("{gn}", n)\n    return {gb}',
        )
        if shape == "nested":
            code = _prog(*defs, f"print({fn}({gn}({x})))")
            gx = g(x)
            ans = f(gx)
            distractors = [
                _lines(f"{fn} {gx}", f"{gn} {x}", ans),
                _lines(f"{fn} {x}", f"{gn} {f(x)}", g(f(x))),
                _lines(f"{gn} {x}", f"{fn} {gx}"),
                _lines(f"{gn} {x}", f"{fn} {x}", ans),
            ]
            why = (
                f"Arguments are evaluated before a function runs, so `{gn}({x})` runs first "
                f"(printing \"{gn} {x}\" and returning {gx}). Then `{fn}({gx})` prints and returns "
                f"{ans}, which the outer `print` shows last."
            )
        else:
            y = rng.randint(2, 6)
            code = _prog(*defs, f"print({fn}({x}) + {gn}({y}))")
            fx, gy = f(x), g(y)
            distractors = [
                _lines(f"{gn} {y}", f"{fn} {x}", fx + gy),
                _lines(fx + gy),
                _lines(f"{fn} {x}", fx, f"{gn} {y}", gy),
                _lines(f"{fn} {x}", f"{gn} {y}", x + y),
            ]
            why = (
                f"Python evaluates `+` left to right: `{fn}({x})` runs first and prints, then "
                f"`{gn}({y})`. Only after both return ({fx} and {gy}) is the sum {fx + gy} printed."
            )
        return _output(code, HARD, distractors, why, rng)
    x = rng.randint(2, 6)
    k = rng.randint(1, 5)
    m = rng.randint(2, 3)
    before = rng.random() < 0.5
    inner = f'def inner(n):\n    print("inner", n)\n    return n + {k}'
    if before:
        outer = f'def outer(n):\n    print("outer", n)\n    return inner(n * {m}) + 1'
    else:
        outer = (
            f"def outer(n):\n    result = inner(n * {m})\n"
            '    print("outer", result)\n    return result + 1'
        )
    code = _prog(inner, outer, f"print(outer({x}))")
    r = x * m + k
    if before:
        distractors = [
            _lines(f"inner {x * m}", f"outer {x}", r + 1),
            _lines(f"outer {x}", f"inner {x}", x + k + 1),
            _lines(f"outer {x}", f"inner {x * m}", r),
            _lines(f"outer {x}", f"inner {x * m}"),
        ]
        why = (
            f"`outer({x})` prints first, then calls `inner({x * m})`, which prints and returns "
            f"{r}. `outer` adds 1 and returns {r + 1}, which is printed last."
        )
    else:
        distractors = [
            _lines(f"outer {r}", f"inner {x * m}", r + 1),
            _lines(f"inner {x}", f"outer {x + k}", x + k + 1),
            _lines(f"inner {x * m}", f"outer {r}", r),
            _lines(f"inner {x * m}", f"outer {x}", r + 1),
        ]
        why = (
            f"`outer({x})` must finish the call `inner({x * m})` before its own `print` runs, "
            f"so \"inner {x * m}\" appears first. `inner` returns {r}, `outer` prints it and "
            f"returns {r + 1}."
        )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_default_evaluated_once(rng: random.Random) -> Question:
    """Default values are computed when ``def`` runs; globals in the body when called."""
    var, fname, param = rng.choice(
        [("rate", "scale", "factor"), ("bonus", "add_bonus", "extra"), ("base", "make", "start")]
    )
    if var == "rate":  # multiplication: keep the numbers small
        old, new = rng.sample(range(2, 7), 2)
        n = rng.randint(2, 5)
    else:
        old, new = rng.sample(range(2, 10), 2)
        n = rng.randint(2, 9)
    shape = rng.choice(["default", "body", "both"])
    if var == "rate":
        expr_d, expr_b = f"n * {param}", f"n * {var}"

        def calc(v):
            return n * v
    else:
        expr_d, expr_b = f"n + {param}", f"n + {var}"

        def calc(v):
            return n + v

    if shape == "default":
        code = _prog(
            f"{var} = {old}",
            f"def {fname}(n, {param}={var}):\n    return {expr_d}",
            f"{var} = {new}\nprint({fname}({n}))",
        )
        ans = calc(old)
        distractors = [calc(new), n, NAME_ERROR, calc(old + new)]
        why = (
            f"A default value is evaluated ONCE, when `def` runs. At that moment `{var}` was "
            f"{old}, so `{param}` defaults to {old} even after `{var}` changes to {new}."
        )
    elif shape == "body":
        code = _prog(
            f"{var} = {old}", f"def {fname}(n):\n    return {expr_b}", f"{var} = {new}\nprint({fname}({n}))"
        )
        ans = calc(new)
        distractors = [calc(old), n, NAME_ERROR, calc(old + new)]
        why = (
            f"The body looks up the global `{var}` each time the function is CALLED. By the "
            f"time `{fname}({n})` runs, `{var}` is {new}."
        )
    else:
        sym = "*" if var == "rate" else "+"
        code = _prog(
            f"{var} = {old}",
            f"def {fname}(n, {param}={var}):\n    return n {sym} {param} {sym} {var}",
            f"{var} = {new}\nprint({fname}({n}))",
        )
        ans = n * old * new if sym == "*" else n + old + new
        same_old = n * old * old if sym == "*" else n + 2 * old
        same_new = n * new * new if sym == "*" else n + 2 * new
        distractors = [same_new, same_old, NAME_ERROR, calc(new)]
        why = (
            f"`{param}` got its default when `def` ran, so it is {old}. The `{var}` in the body is "
            f"looked up when the function is called, so it is {new}. Result: "
            f"{n} {sym} {old} {sym} {new} = {ans}."
        )
    return _output(code, HARD, _nums(distractors, ans, rng), why, rng, prompt=PRINT_OR_ERROR)


@generator(TOPIC, HARD)
def gen_mutation_and_none(rng: random.Random) -> Question:
    """Mutating a list argument vs rebinding it vs ints — and functions that return None."""
    shape = rng.choice(["both", "reassign", "rebind", "len_of_none", "list_and_int"])
    start = rng.sample(range(1, 10), 2)
    v = rng.randint(1, 9)
    fname = rng.choice(["add_twice", "append_twice"])
    mutator = f"def {fname}(items, value):\n    items.append(value)\n    items.append(value)"
    after = start + [v, v]
    allow_error = False
    if shape == "both":
        code = _prog(mutator, f"nums = {start}\nresult = {fname}(nums, {v})\nprint(nums, result)")
        distractors = [f"{start} {after}", f"{after} {after}", f"{start + [v]} None", f"{start} None"]
        why = (
            f"`items` refers to the same list as `nums`, so the two `append` calls change `nums` "
            f"to {after}. The function has no `return`, so `result` is `None`."
        )
    elif shape == "reassign":
        code = _prog(mutator, f"nums = {start}\nnums = {fname}(nums, {v})\nprint(nums)")
        distractors = [after, start, TYPE_ERROR, start + [v]]
        why = (
            f"The list IS changed inside the function, but `{fname}` returns `None`, and "
            "`nums = ...` then replaces the list with that `None`."
        )
    elif shape == "rebind":
        rname = rng.choice(["with_item", "plus_item"])
        code = _prog(
            f"def {rname}(items, value):\n    items = items + [value]\n    return items",
            f"nums = {start}\nmore = {rname}(nums, {v})\nprint(nums, more)",
        )
        distractors = [
            f"{start + [v]} {start + [v]}",
            f"{start + [v]} None",
            f"{start} None",
            f"{start} {start}",
        ]
        why = (
            "`items + [value]` builds a NEW list and `items = ...` only rebinds the local name, "
            f"so `nums` is untouched ({start}). The new list {start + [v]} is returned into `more`."
        )
    elif shape == "len_of_none":
        code = _prog(mutator, f"nums = {start}\nprint(len({fname}(nums, {v})))")
        distractors = [len(after), len(start), "0", "None"]
        why = (
            f"`{fname}` changes the list but returns `None`, so the code calls `len(None)`. "
            "`None` has no length, so Python raises a `TypeError`."
        )
        allow_error = True
    else:
        uname = rng.choice(["update", "record"])
        n0 = rng.randint(1, 5)
        code = _prog(
            f"def {uname}(log, count):\n    log.append(count)\n    count += 1",
            f"data = []\nn = {n0}\n{uname}(data, n)\n{uname}(data, n)\nprint(data, n)",
        )
        distractors = [
            f"[{n0}, {n0 + 1}] {n0 + 2}",
            f"[{n0}, {n0 + 1}] {n0}",
            f"[] {n0}",
            f"[{n0}, {n0}] {n0 + 2}",
        ]
        why = (
            "`log.append` changes the list object that `data` also refers to, so `data` grows. "
            f"`count += 1` only rebinds the local `count` to a new int, so `n` stays {n0} — and "
            f"both calls append {n0}."
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=allow_error)
