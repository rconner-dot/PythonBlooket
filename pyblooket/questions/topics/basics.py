"""Question generators for the "basics" topic (Variables & Math).

Covers assignment and reassignment, augmented assignment, the arithmetic
operators (``/ // % **``), operator precedence, int/float/str/bool types and
conversions, ``round()``, and the classic gotchas: floor division and modulo
with negative numbers, float precision, ``-x ** 2`` and simultaneous (tuple)
assignment.
"""

from __future__ import annotations

import random

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    NOTHING_PRINTED,
    GenerationError,
    Question,
    build_question,
    error_choice,
    eval_expr,
    generator,
    output_question,
    run_code,
    which_expression_question,
)

TOPIC = "basics"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
TYPE_ERROR = error_choice("TypeError")
VALUE_ERROR = error_choice("ValueError")


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _run(code: str) -> str:
    """The choice text for what ``code`` prints, or the error it raises."""
    res = run_code(code)
    if res.error:
        return error_choice(res.error)
    return res.output if res.output else NOTHING_PRINTED


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
        distractors=distractors,
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _trunc_divmod(a: int, b: int) -> tuple[int, int]:
    """Division that truncates toward zero (what C/Java do) — a misconception source."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q, a - b * q


def _nearby(correct: int, rng: random.Random) -> list[str]:
    """Nearby integers as a fallback; never negative when the answer isn't."""
    cands = [correct + d for d in (1, -1, 2, -2, 10)] + [correct * 2]
    if correct >= 0:
        cands = [c for c in cands if c >= 0]
    rng.shuffle(cands)
    return [str(c) for c in cands if c != correct]


def _short_float(value: float, max_len: int = 7) -> str | None:
    """repr of a float if it is short enough to be a believable distractor."""
    text = repr(value)
    return text if len(text) <= max_len else None


# Decimal additions whose float result is NOT exactly the decimal answer
# (0.1 + 0.2 -> 0.30000000000000004).  Computed once, deterministically.
_INEXACT_SUMS = [
    (p, q, r)
    for w1 in range(3)
    for w2 in range(2)
    for d1 in range(1, 9)
    for d2 in range(1, 9)
    if d1 + d2 <= 9
    for p, q, r in [(f"{w1}.{d1}", f"{w2}.{d2}", f"{w1 + w2}.{d1 + d2}")]
    if float(p) + float(q) != float(r)
]
_INEXACT_PRODUCTS = [
    (f"0.{d}", k, f"0.{d * k}")
    for d in range(1, 5)
    for k in range(2, 5)
    if d * k <= 9 and float(f"0.{d}") * k != float(f"0.{d * k}")
]


# ==========================================================================
# EASY
# ==========================================================================


@generator(TOPIC, EASY)
def gen_reassignment(rng: random.Random) -> Question:
    """x = x + 3, copies made before a reassignment, derived values."""
    x, y = rng.sample(["x", "y", "score", "total", "age", "level", "speed", "points"], 2)
    shape = rng.choice(["update", "copy", "derived"])
    if shape == "update":
        op = rng.choice(["+", "-", "*"])
        b = rng.randint(2, 9)
        a = rng.randint(b + 2, 15) if op == "-" else rng.randint(3, 12)
        result = {"+": a + b, "-": a - b, "*": a * b}[op]
        alt = {"+": a * b, "-": a + b, "*": a + b}[op]
        code = f"{x} = {a}\n{x} = {x} {op} {b}\nprint({x})"
        distractors = [str(a), str(alt), str(b), *_nearby(result, rng)]
        why = (
            f"Python evaluates the right side first using the current value of `{x}` "
            f"({a} {op} {b} = {result}), then stores that result back in `{x}`."
        )
    elif shape == "copy":
        a, b = rng.sample(range(2, 20), 2)
        code = f"{x} = {a}\n{y} = {x}\n{x} = {b}\nprint({x}, {y})"
        distractors = [f"{b} {b}", f"{a} {a}", f"{a} {b}"]
        why = (
            f"`{y} = {x}` copies the value {a} into `{y}` at that moment. Giving `{x}` "
            f"a new value afterwards does not change `{y}`."
        )
    else:
        a = rng.randint(2, 9)
        b = rng.randint(2, 9)
        k = rng.randint(2, 3)
        f = rng.choice(["*", "+"])
        ya = a * k if f == "*" else a + k
        yb = (a + b) * k if f == "*" else a + b + k
        code = f"{x} = {a}\n{y} = {x} {f} {k}\n{x} = {x} + {b}\nprint({x}, {y})"
        distractors = [
            f"{a + b} {yb}", f"{a} {ya}", f"{ya} {a + b}", f"{a + b} {ya + b}",
            f"{a + b} {a}", f"{b} {ya}",
        ]
        why = (
            f"`{y}` was computed when `{x}` was {a}, so it is {ya}. Changing `{x}` to "
            f"{a + b} afterwards does not go back and recompute `{y}`."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_augmented_assignment(rng: random.Random) -> Question:
    """+=, -=, *= — one or two in a row."""
    name = rng.choice(["score", "coins", "points", "lives", "total", "count"])
    fns = {"+=": lambda v, k: v + k, "-=": lambda v, k: v - k, "*=": lambda v, k: v * k}
    a = rng.randint(4, 15)

    def operand(op: str) -> int:
        return rng.randint(2, 5) if op == "*=" else rng.randint(2, 9)

    if rng.random() < 0.5:
        op = rng.choice(list(fns))
        b = operand(op)
        result = fns[op](a, b)
        code = f"{name} = {a}\n{name} {op} {b}\nprint({name})"
        if op == "+=":
            distractors = [str(b), str(a), str(a * b)]
        elif op == "-=":
            distractors = [str(b - a), str(b), str(a)]
        else:
            distractors = [str(a + b), str(b), str(a)]
        distractors += _nearby(result, rng)
        why = (
            f"`{name} {op} {b}` is shorthand for `{name} = {name} {op[0]} {b}`, "
            f"so `{name}` becomes {a} {op[0]} {b} = {result}."
        )
    else:
        op1, op2 = rng.sample(list(fns), 2)
        b, c = operand(op1), operand(op2)
        mid = fns[op1](a, b)
        result = fns[op2](mid, c)
        code = f"{name} = {a}\n{name} {op1} {b}\n{name} {op2} {c}\nprint({name})"
        distractors = [
            str(fns[op1](fns[op2](a, c), b)),  # ran the lines in the wrong order
            str(fns[op2](a, c)),  # only the last line counts
            str(mid),  # forgot the last line
            *_nearby(result, rng),
        ]
        why = (
            f"Each line updates `{name}` using its current value: {a} {op1[0]} {b} = {mid}, "
            f"then {mid} {op2[0]} {c} = {result}."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_division_operators(rng: random.Random) -> Question:
    """/ vs // vs % vs ** on small positive ints."""
    op = rng.choice(["/", "//", "%", "**"])
    if op == "**":
        a, b = rng.randint(2, 5), rng.randint(2, 3)
        if (a, b) == (2, 2):
            a = rng.randint(3, 5)
    else:
        b = rng.randint(3, 7) if op == "%" else rng.randint(2, 6)
        if op == "/" and rng.random() < 0.4:
            a = b * rng.randint(2, 6)  # divides evenly: still a float!
        else:
            a = rng.randint(2 * b + 1, 30)
            if a % b == 0:
                a += 1
    q, r = divmod(a, b)
    t = a / b
    if op == "/":
        distractors = [str(q), f"{q}.{r}", str(r), str(round(t)), str(q + 1), str(float(q + 1))]
        why = f"`/` is true division and always gives a float, even when it divides evenly: {a} / {b} = {t}."
    elif op == "//":
        distractors = [str(t), str(r), str(float(q)), str(q + 1)]
        why = (
            f"`//` is floor division: it divides and keeps only the whole-number part. "
            f"{a} / {b} is {t}, so {a} // {b} is {q}."
        )
    elif op == "%":
        distractors = [str(q), str(t), str(round(t - q, 2)), str(b - r), str(a - b)]
        why = f"`%` gives the remainder: {b} goes into {a} {q} times ({q * b}) with {r} left over."
    else:
        distractors = [str(a * b), str(b**a), str(a + b), str(a ** (b + 1))]
        why = f"`**` is exponentiation: {a} ** {b} means {a} multiplied by itself {b} times = {a**b}."
    distractors += _nearby(q, rng)
    if rng.random() < 0.5:
        code = f"print({a} {op} {b})"
    else:
        x, y = rng.choice([("a", "b"), ("x", "y"), ("m", "n"), ("total", "size")])
        code = f"{x} = {a}\n{y} = {b}\nprint({x} {op} {y})"
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_type_of_value(rng: random.Random) -> Question:
    """type() of literals and simple expressions (7 / 7 is a float!)."""
    a = rng.randint(2, 9)
    b = rng.randint(2, 5)
    d = rng.randint(1, 9)
    var = rng.choice(["x", "value", "result", "item", "data"])
    options = {
        "int": [
            (f"{a * b}", f"`{a * b}` is a whole-number literal with no decimal point, so it is an `int`."),
            (f"{a * b} // {b}", f"`//` on two ints gives an int: {a * b} // {b} is {a}."),
            (f'int("{a}")', f'`int("{a}")` converts the string "{a}" into the integer {a}.'),
            (f"int({a}.{d})", f"`int()` drops the decimal part and returns the integer {a}."),
            (f"{a} * {b}", f"Multiplying two ints gives an int ({a * b})."),
        ],
        "float": [
            (
                f"{a * b} / {b}",
                f"`/` always returns a float, even when it divides evenly: {a * b} / {b} is {float(a)}.",
            ),
            (f"{a}.{d}", f"A number written with a decimal point, like {a}.{d}, is a `float`."),
            (f"{a} + {b}.0", f"Mixing an int and a float gives a float: {a} + {b}.0 is {a + b}.0."),
            (f"float({a})", f"`float({a})` converts the int to the float {float(a)}."),
        ],
        "str": [
            (f'"{a}"', f'The quotes make `"{a}"` a string, even though it looks like a number.'),
            (f"str({a * b})", f'`str({a * b})` converts the number into the string "{a * b}".'),
            (f'"{a}" + "{b}"', f'Adding two strings joins them into "{a}{b}", which is still a `str`.'),
            (f'"{a}.{d}"', f'The quotes make `"{a}.{d}"` a string, not a float.'),
            ('"True"', 'With quotes, `"True"` is just a 4-letter string, not a bool.'),
        ],
        "bool": [
            (f"({a * b} > {b})", "A comparison like `>` produces True or False, which are `bool` values."),
            ("True", "`True` (no quotes) is one of the two `bool` values."),
            (f"({a} == {a}.0)", f"`==` produces a bool. ({a} == {a}.0 is True, because the values are equal.)"),
            (f"({a} != {b})", "`!=` is a comparison, so its result is a `bool`."),
        ],
    }
    kind = rng.choice(list(options))
    expr, why = rng.choice(options[kind])
    order = {
        "int": ["float", "str", "bool"],
        "float": ["int", "str", "bool"],
        "str": ["int", "float", "bool"],
        "bool": ["str", "int", "float"],
    }[kind]
    code = f"{var} = {expr}\nprint(type({var}))"
    return _output(code, EASY, [f"<class '{t}'>" for t in order], why, rng)


@generator(TOPIC, EASY)
def gen_simple_precedence(rng: random.Random) -> Question:
    """* before +, ** before *, parentheses first, left-to-right for + and -."""
    a, b, c = rng.sample(range(2, 10), 3)
    d = rng.choice([v for v in range(2, 6) if v != c])
    big = rng.randint(20, 40)
    templates = [
        (f"{a} + {b} * {c}", [f"({a} + {b}) * {c}", f"{a} + {b} + {c}"],
         f"`*` happens before `+`, so this is {a} + ({b} * {c}) = {a} + {b * c}."),
        (f"({a} + {b}) * {c}", [f"{a} + {b} * {c}", f"{a} + {b} + {c}"],
         f"Parentheses are evaluated first: {a} + {b} = {a + b}, then {a + b} * {c}."),
        (f"{big} - {b} * {c}", [f"({big} - {b}) * {c}", f"{big} - {b} - {c}"],
         f"`*` happens before `-`, so this is {big} - ({b} * {c}) = {big} - {b * c}."),
        (f"{a} + {b} ** 2", [f"({a} + {b}) ** 2", f"{a} + {b} * 2"],
         f"`**` happens before `+`, so this is {a} + ({b} ** 2) = {a} + {b * b}."),
        (f"{a} * {d} ** 2", [f"({a} * {d}) ** 2", f"{a} * {d} * 2"],
         f"`**` happens before `*`, so this is {a} * ({d} ** 2) = {a} * {d * d}."),
        (f"{big} - {b} + {c}", [f"{big} - ({b} + {c})", f"{big} - {b} - {c}"],
         f"`+` and `-` have equal precedence and run left to right: ({big} - {b}) + {c}."),
        (f"{a} * {b} - {c} * {d}", [f"({a} * {b} - {c}) * {d}", f"{a} * ({b} - {c}) * {d}"],
         f"Both multiplications happen first: {a * b} - {c * d}."),
    ]
    expr, alts, why = rng.choice(templates)
    result = eval_expr(expr)
    distractors = [str(eval_expr(alt)) for alt in alts] + _nearby(result, rng)
    if rng.random() < 0.5:
        code = f"print({expr})"
    else:
        name = rng.choice(["result", "answer", "total", "x"])
        code = f"{name} = {expr}\nprint({name})"
    return _output(code, EASY, distractors, f"{why} The result is {result}.", rng)


@generator(TOPIC, EASY)
def gen_multiple_assignment(rng: random.Random) -> Question:
    """Tuple swap, chained assignment x = y = 5, unpacking then updating."""
    x, y = rng.choice([("a", "b"), ("x", "y"), ("left", "right"), ("p", "q"), ("first", "second")])
    a, b = rng.sample(range(1, 15), 2)
    shape = rng.choice(["swap", "chained", "unpack"])
    if shape == "swap":
        code = f"{x}, {y} = {a}, {b}\n{x}, {y} = {y}, {x}\nprint({x}, {y})"
        distractors = [f"{a} {b}", f"{b} {b}", f"{a} {a}"]
        why = (
            f"The right side `{y}, {x}` is evaluated first (giving {b}, {a}) and then both "
            f"names are assigned at once, so the values are swapped."
        )
    elif shape == "chained":
        k = rng.randint(2, 9)
        code = f"{x} = {y} = {a}\n{x} = {x} + {k}\nprint({x}, {y})"
        distractors = [f"{a + k} {a + k}", f"{a} {a}", f"{a} {a + k}"]
        why = (
            f"`{x} = {y} = {a}` gives both names the value {a}. Reassigning `{x}` to {a + k} "
            f"later does not affect `{y}`."
        )
    else:
        code = f"{x}, {y} = {a}, {b}\n{x} = {x} + {y}\nprint({x}, {y})"
        distractors = [f"{a + b} {a + b}", f"{a} {b}", f"{a + b} {a}", f"{b} {a + b}"]
        why = (
            f"Unpacking sets `{x}` to {a} and `{y}` to {b}. Only `{x}` is reassigned "
            f"({a} + {b} = {a + b}); `{y}` keeps {b}."
        )
    return _output(code, EASY, distractors, why, rng)


@generator(TOPIC, EASY)
def gen_basic_conversions(rng: random.Random) -> Question:
    """int(), float(), str() conversions and the str + int TypeError."""
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    k = rng.randint(2, 3)
    d = rng.randint(5, 9)
    shape = rng.choice(["int_add", "str_join", "int_float", "float_add", "str_repeat", "str_plus_int"])
    if shape == "int_add":
        code = f'print(int("{a}") + {b})'
        distractors = [f"{a}{b}", TYPE_ERROR, f"{a + b}.0"]
        why = f'`int("{a}")` turns the string into the number {a}, so this is ordinary addition: {a} + {b} = {a + b}.'
    elif shape == "str_join":
        code = f"print(str({a}) + str({b}))"
        distractors = [str(a + b), TYPE_ERROR, f"{a} {b}"]
        why = f'Both numbers become strings, and `+` on strings joins them: "{a}" + "{b}" is "{a}{b}".'
    elif shape == "int_float":
        code = f"print(int({a}.{d}))"
        distractors = [str(a + 1), f"{a}.0", f"{a}.{d}", VALUE_ERROR]
        why = f"`int()` does not round: it simply drops everything after the decimal point, so {a}.{d} becomes {a}."
    elif shape == "float_add":
        code = f'print(float("{a}") + {b})'
        distractors = [str(a + b), f"{a}{b}", TYPE_ERROR]
        why = f'`float("{a}")` is the number {float(a)}; adding the int {b} gives the float {float(a + b)}.'
    elif shape == "str_repeat":
        code = f"print(str({a}) * {k})"
        distractors = [str(a * k), TYPE_ERROR, " ".join([str(a)] * k)]
        why = f'`str({a})` is the string "{a}", and multiplying a string by {k} repeats it: "{str(a) * k}".'
    else:
        code = f'print("{a}" + {b})'
        distractors = [str(a + b), f"{a}{b}", VALUE_ERROR]
        why = (
            f'`"{a}"` is a string and {b} is an int. Python will not add a `str` and an `int`, '
            f"so it raises a TypeError. Convert one side first."
        )
    return _output(code, EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, EASY)
def gen_missing_operator(rng: random.Random) -> Question:
    """Which operator (// % / **) turns `a ? b` into the given value?"""
    op = rng.choice(["//", "%", "/", "**", "//", "%"])
    if op == "**":
        a, b = rng.randint(3, 5), rng.randint(2, 3)
    else:
        b = rng.randint(2, 5)
        a = rng.randint(2 * b + 1, 25)
        if a % b == 0:
            a += 1
    target = eval_expr(f"{a} {op} {b}")
    order = {
        "//": ["/", "%", "-", "*", "+"],
        "%": ["//", "/", "-", "*", "+"],
        "/": ["//", "%", "*", "-", "+"],
        "**": ["*", "+", "//", "%", "-"],
    }[op]
    # 6 == 6.0 in Python, so drop anything numerically equal to the target.
    wrong = [o for o in order if eval_expr(f"{a} {o} {b}") != target]
    meaning = {
        "//": "`//` divides and keeps only the whole-number part.",
        "%": "`%` gives the remainder after dividing.",
        "/": "`/` is true division, which gives a float.",
        "**": "`**` raises to a power.",
    }[op]
    other = wrong[0]
    why = (
        f"`{a} {op} {b}` is {target!r}: {meaning} "
        f"(For comparison, `{a} {other} {b}` would be {eval_expr(f'{a} {other} {b}')!r}.)"
    )
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Which operator should replace `?` so that `{a} ? {b}` evaluates to `{target!r}`?",
        correct=op,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# MEDIUM
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_str_num_mixing(rng: random.Random) -> Question:
    """Mixing "4" and 4: + raises, * repeats, int()/str() fix it."""
    s, n = rng.choice(
        [("text", "num"), ("digit", "times"), ("a", "b"), ("x", "y"), ("label", "count"), ("s", "n")]
    )
    a, b = rng.randint(2, 9), rng.randint(2, 4)
    sa = str(a)
    head = f'{s} = "{a}"\n{n} = {b}\n'
    shape = rng.choice(["add", "radd", "mul", "int_add", "str_add", "two_step_str", "two_step_int"])
    if shape in ("add", "radd"):
        expr = f"{s} + {n}" if shape == "add" else f"{n} + {s}"
        body = f"print({expr})"
        distractors = [f"{a}{b}" if shape == "add" else f"{b}{a}", str(a + b), VALUE_ERROR, sa * b]
        why = (
            f'`{s}` holds the string "{a}" (it has quotes). Python will not use `+` between a '
            f"`str` and an `int`, so it raises a TypeError. Convert first with `int({s})` or `str({n})`."
        )
    elif shape == "mul":
        body = f"print({s} * {n})"
        distractors = [str(a * b), TYPE_ERROR, " ".join([sa] * b), VALUE_ERROR]
        why = f'Multiplying a string by an int repeats it: "{a}" * {b} is "{sa * b}". No arithmetic happens.'
    elif shape == "int_add":
        body = f"print(int({s}) + {n})"
        distractors = [f"{a}{b}", TYPE_ERROR, f"{a + b}.0", VALUE_ERROR]
        why = f'`int({s})` turns "{a}" into the number {a}, so this is ordinary addition: {a} + {b} = {a + b}.'
    elif shape == "str_add":
        body = f"print({s} + str({n}))"
        distractors = [str(a + b), TYPE_ERROR, f"{a} {b}", VALUE_ERROR]
        why = f'`str({n})` turns {b} into "{b}", and `+` on two strings joins them: "{a}" + "{b}" is "{a}{b}".'
    elif shape == "two_step_str":
        body = f"result = int({s}) * {n}\nprint(str(result) + {s})"
        distractors = [str(a * b + a), TYPE_ERROR, sa * b + sa, VALUE_ERROR]
        why = (
            f'`int({s}) * {n}` is {a} * {b} = {a * b}. `str(result)` makes it "{a * b}", and adding '
            f'the string "{a}" joins them into "{a * b}{a}".'
        )
    else:
        body = f"{s} = {s} * {n}\nprint(int({s}) + 1)"
        rep = sa * b
        distractors = [str(a * b + 1), f"{rep}1", TYPE_ERROR, VALUE_ERROR]
        why = (
            f'`{s} * {n}` repeats the string, giving "{rep}". `int()` then reads that as the number '
            f"{rep}, and adding 1 gives {int(rep) + 1}."
        )
    return _output(head + body, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, MEDIUM)
def gen_augmented_trace(rng: random.Random) -> Question:
    """Trace 3-4 augmented assignments including //= and %=."""
    name = rng.choice(["n", "score", "total", "value", "x", "points"])
    for _ in range(60):
        start = rng.randint(6, 30)
        kinds = [rng.choice(["//=", "%="])]
        kinds += [rng.choice(["+=", "-=", "*=", "//=", "%=", "**="]) for _ in range(rng.randint(2, 3))]
        rng.shuffle(kinds)
        v = start
        ops: list[tuple[str, int]] = []
        trace = [start]
        for kind in kinds:
            if kind == "+=":
                k = rng.randint(2, 9)
                v += k
            elif kind == "-=":
                if v < 3:
                    break
                k = rng.randint(1, min(9, v - 1))
                v -= k
            elif kind == "*=":
                if v > 40:
                    break
                k = rng.randint(2, 4)
                v *= k
            elif kind == "//=":
                ks = [k for k in range(2, 6) if v % k and v // k >= 2]
                if not ks:
                    break
                k = rng.choice(ks)
                v //= k
            elif kind == "%=":
                ks = [k for k in range(3, 10) if v % k >= 2 and k < v]
                if not ks:
                    break
                k = rng.choice(ks)
                v %= k
            else:
                if not 2 <= v <= 9:
                    break
                k = 2
                v **= k
            ops.append((kind, k))
            trace.append(v)
        else:
            if 2 <= v <= 400 and len(set(trace)) == len(trace):
                break
    else:
        raise GenerationError("could not build an augmented-assignment trace")

    lines = [f"{name} {kind} {k}" for kind, k in ops]

    def program(body: list[str]) -> str:
        return "\n".join([f"{name} = {start}", *body, f"print({name})"])

    def swap_div_mod(line: str) -> str:
        if "//=" in line:
            return line.replace("//=", "%=")
        return line.replace("%=", "//=")

    candidates = [
        _run(program([swap_div_mod(ln) for ln in lines])),  # mixed up // and %
        _run(program([ln.replace("//=", "/=") for ln in lines])),  # / instead of //
        _run(program(lines[:-1])),  # forgot the last line
        _run(program(lines[1:])),  # skipped the first line
    ]
    distractors = [
        c for c in candidates if not c.startswith("Error") and len(c) <= 8
    ] + _nearby(v, rng)
    steps = " → ".join(str(t) for t in trace)
    rules = []
    if "//=" in kinds:
        rules.append("`//=` keeps only the whole-number part of the division")
    if "%=" in kinds:
        rules.append("`%=` keeps only the remainder")
    why = (
        f"Each augmented assignment updates `{name}` using its current value: {steps}. "
        f"Remember: {' and '.join(rules)}."
    )
    return _output(program(lines), MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_swap_bug(rng: random.Random) -> Question:
    """Swapping two variables: naive (buggy), with temp, temp bug, arithmetic."""
    x, y = rng.choice(
        [("a", "b"), ("x", "y"), ("left", "right"), ("first", "second"), ("p", "q"), ("top", "bottom")]
    )
    a, b = rng.sample(range(1, 20), 2)
    shape = rng.choice(["naive_xy", "naive_yx", "temp_ok", "temp_bug", "arith"])
    if shape == "naive_xy":
        body = f"{x} = {y}\n{y} = {x}"
        why = (
            f"`{x} = {y}` overwrites {x}'s old value ({a}) before it is saved anywhere, so "
            f"`{y} = {x}` just copies {b} back. Both end up {b}."
        )
    elif shape == "naive_yx":
        body = f"{y} = {x}\n{x} = {y}"
        why = (
            f"`{y} = {x}` overwrites {y}'s old value ({b}) before it is saved anywhere, so "
            f"`{x} = {y}` just copies {a} back. Both end up {a}."
        )
    elif shape == "temp_ok":
        body = f"temp = {x}\n{x} = {y}\n{y} = temp"
        why = f"`temp` saves the original {a} before `{x}` is overwritten, so `{y}` can get it back: a real swap."
    elif shape == "temp_bug":
        body = f"temp = {x}\n{x} = {y}\n{y} = {x}"
        why = (
            f"The last line copies the NEW value of `{x}` ({b}), not `temp`, so the saved {a} "
            f"is never used and both end up {b}."
        )
    else:
        body = f"{x} = {x} + {y}\n{y} = {x} - {y}\n{x} = {x} - {y}"
        why = (
            f"`{x}` becomes {a + b}; then `{y}` = {a + b} - {b} = {a}; then `{x}` = {a + b} - {a} = {b}. "
            f"The values are swapped."
        )
    code = f"{x} = {a}\n{y} = {b}\n{body}\nprint({x}, {y})"
    distractors = [f"{b} {a}", f"{b} {b}", f"{a} {a}", f"{a} {b}"]
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_precedence_mixed(rng: random.Random) -> Question:
    """Precedence with // % ** mixed in; distractors are wrong groupings."""
    a = rng.randint(10, 30)
    c, d = rng.sample(range(2, 6), 2)
    b = rng.choice([v for v in range(2, 10) if v not in (c, d)])
    templates = [
        (f"{a} + {b} // {c} * {d}", f"{a} + (({b} // {c}) * {d})",
         [f"({a} + {b}) // {c} * {d}", f"{a} + {b} // ({c} * {d})", f"({a} + {b}) // ({c} * {d})"]),
        (f"{a} * {b} % {c} + {d}", f"(({a} * {b}) % {c}) + {d}",
         [f"{a} * ({b} % {c}) + {d}", f"{a} * {b} % ({c} + {d})", f"{a} * ({b} % ({c} + {d}))"]),
        (f"{a} + {b} ** 2 // {c}", f"{a} + (({b} ** 2) // {c})",
         [f"({a} + {b}) ** 2 // {c}", f"({a} + {b} ** 2) // {c}", f"{a} + {b} * 2 // {c}"]),
        (f"{c} + {d} * {b} ** 2", f"{c} + ({d} * ({b} ** 2))",
         [f"({c} + {d}) * {b} ** 2", f"{c} + ({d} * {b}) ** 2", f"{c} + {d} * {b} * 2"]),
        (f"{a} * {d} - {b} // {c}", f"({a} * {d}) - ({b} // {c})",
         [f"({a} * {d} - {b}) // {c}", f"{a} * ({d} - {b}) // {c}", f"{a} * ({d} - {b} // {c})"]),
        (f"{a} - {b} + {c} * {d}", f"({a} - {b}) + ({c} * {d})",
         [f"({a} - {b} + {c}) * {d}", f"{a} - ({b} + {c}) * {d}", f"{a} - ({b} + {c} * {d})"]),
        (f"{a} // {c} * {d}", f"({a} // {c}) * {d}",
         [f"{a} // ({c} * {d})", f"{a} / {c} * {d}", f"({a} // {c}) * {d} + 1"]),
        (f"{a} % {b} * {c}", f"({a} % {b}) * {c}",
         [f"{a} % ({b} * {c})", f"{a} // {b} * {c}", f"({a} % {b}) + {c}"]),
    ]
    expr, grouped, alts = rng.choice(templates)
    result = eval_expr(expr)
    distractors = [str(eval_expr(alt)) for alt in alts] + _nearby(result, rng)
    if rng.random() < 0.5:
        code = f"print({expr})"
    else:
        name = rng.choice(["result", "answer", "x", "value"])
        code = f"{name} = {expr}\nprint({name})"
    why = (
        f"`**` binds tightest, then `*`, `//` and `%` (equal, left to right), then `+` and `-`. "
        f"So Python reads it as `{grouped}`, which is {result}."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_round_vs_int(rng: random.Random) -> Question:
    """int() truncates, round() goes to the nearest value (incl. decimal places)."""
    var = rng.choice(["x", "price", "temp", "height", "score", "speed"])
    w = rng.randint(2, 19)
    shape = rng.choice(["pair", "pair", "negative", "places", "sum"])
    if shape == "pair":
        f = rng.choice([1, 2, 3, 4, 6, 7, 8, 9])
        r = w + 1 if f > 5 else w
        code = f"{var} = {w}.{f}\nprint(int({var}), round({var}))"
        distractors = [f"{r} {r}", f"{w} {w}", f"{w} {w + 1}", f"{w + 1} {w + 1}", f"{w} {r}.0"]
        why = (
            f"`int()` simply drops the decimal part, giving {w}. `round()` goes to the nearest "
            f"whole number, giving {r}."
        )
    elif shape == "negative":
        f = rng.randint(6, 9)
        code = f"{var} = -{w}.{f}\nprint(int({var}), round({var}))"
        distractors = [f"-{w + 1} -{w + 1}", f"-{w} -{w}", f"-{w + 1} -{w}"]
        why = (
            f"`int()` truncates toward zero, so int(-{w}.{f}) is -{w}, not -{w + 1}. "
            f"`round()` goes to the nearest whole number, which is -{w + 1}."
        )
    elif shape == "places":
        k = rng.randint(1, 2)
        digits = [rng.randint(0, 9) for _ in range(rng.randint(k + 1, 4))]
        digits[k - 1] = rng.randint(1, 8)  # rounding never carries past this digit
        digits[k] = rng.choice([0, 1, 2, 3, 4, 6, 7, 8, 9])  # never a round-half case
        digits[-1] = digits[-1] or rng.randint(1, 9)
        text = f"{w}." + "".join(map(str, digits))
        value = float(text)
        code = f"{var} = {text}\nprint(round({var}, {k}))"
        trunc = repr(float(f"{w}." + "".join(map(str, digits[:k]))))
        distractors = [
            trunc,
            repr(round(value, 3 - k)),
            str(round(value)),
            repr(float(f"{w}." + "".join(map(str, digits[: k + 1])))),
            f"{round(value, k) + 10 ** -k:.{k}f}",
            f"{round(value, k) - 10 ** -k:.{k}f}",
            f"{value:.{k + 1}f}",
        ]
        direction = "up" if digits[k] > 5 else "down"
        why = (
            f"`round({var}, {k})` keeps {k} decimal place{'s' if k > 1 else ''}. The next digit is "
            f"{digits[k]}, so it rounds {direction} to {round(value, k)}."
        )
    else:
        v1, v2 = rng.choice([("a", "b"), ("x", "y"), ("price", "tax"), ("width", "height")])
        w2 = rng.randint(1, 9)
        f1, f2 = rng.randint(6, 9), rng.randint(6, 9)
        code = f"{v1} = {w}.{f1}\n{v2} = {w2}.{f2}\nprint(round({v1}) + int({v2}))"
        result = w + 1 + w2
        distractors = [str(result + 1), str(w + w2), *_nearby(result, rng)]
        why = (
            f"`round({w}.{f1})` is {w + 1} (nearest whole number), but `int({w2}.{f2})` is {w2} "
            f"because `int()` just drops the decimals. {w + 1} + {w2} = {result}."
        )
    return _output(code, MEDIUM, distractors, why, rng)


_SPLITS = [
    ("total_minutes", "hours", "minutes", 60, 61, 300, "hour"),
    ("total_seconds", "minutes", "seconds", 60, 61, 400, "minute"),
    ("total_inches", "feet", "inches", 12, 13, 99, "foot"),
    ("total_cents", "dollars", "cents", 100, 101, 999, "dollar"),
    ("total_days", "weeks", "days", 7, 8, 60, "week"),
    ("eggs", "cartons", "extra", 12, 13, 99, "carton"),
]


@generator(TOPIC, MEDIUM)
def gen_unit_split(rng: random.Random) -> Question:
    """Splitting a quantity with // and % (135 minutes -> 2 hours 15 minutes)."""
    total, big, small, size, lo, hi, unit = rng.choice(_SPLITS)
    n = rng.randint(lo, hi)
    if n % size == 0:
        n += rng.randint(1, size - 1)
    q, r = divmod(n, size)
    if rng.random() < 0.7:
        second = f"{small} = {total} % {size}"
    else:
        second = f"{small} = {total} - {big} * {size}"
    code = f"{total} = {n}\n{big} = {total} // {size}\n{second}\nprint({big}, {small})"
    frac = round(n / size - q, 2)
    distractors = [f"{r} {q}"]  # mixed up // and %
    as_float = _short_float(n / size)
    if as_float:
        distractors.append(f"{as_float} {r}")  # used / instead of //
    if 2 * r >= size:
        distractors.append(f"{q + 1} {r}")  # rounded instead of floored
    distractors += [f"{q} {size - r}", f"{q} {frac}", f"{q + 1} {r}", f"{q} {n - q}"]
    why = (
        f"`{n} // {size}` counts the whole {unit}s ({q}) and the remainder is what is left over "
        f"({r}), since {q} * {size} + {r} = {n}."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_int_float_result(rng: random.Random) -> Question:
    """Which results are ints and which are floats (12 / 3 -> 4.0, 12 // 3 -> 4)."""
    x, y = rng.choice([("a", "b"), ("m", "n"), ("total", "parts"), ("big", "small")])
    outs = rng.choice([["c", "d"], ["p", "q"], ["r", "s", "t"], ["c", "d", "e"]])
    if x in outs or y in outs:
        raise GenerationError("name clash")  # cannot happen with the lists above
    b = rng.randint(2, 5)
    a = b * rng.randint(2, 6)
    int_exprs = [f"{x} // {y}", f"{x} + {y}", f"{x} * {y}", f"{x} - {y}", f"int({x} / {y})", f"{y} ** 2"]
    float_reasons = {
        f"{x} / {y}": "`/` always returns a float, even when it divides evenly",
        f"{x} * 1.0": "multiplying by the float `1.0` makes the result a float",
        f"float({y})": "`float()` converts the int to a float",
        f"{x} / {y} * {y}": "`/` gives a float first, and float * int stays a float",
        f"{y} * 2.0": "an int times a float is a float",
        f"{x} / {y} + 1": "`/` gives a float first, and float + int stays a float",
    }
    float_exprs = list(float_reasons)
    kinds = [rng.choice(["int", "float"]) for _ in outs]
    if len(set(kinds)) == 1:
        kinds[rng.randrange(len(kinds))] = "int" if kinds[0] == "float" else "float"
    exprs = []
    pool = {"int": rng.sample(int_exprs, len(outs)), "float": rng.sample(float_exprs, len(outs))}
    for i, kind in enumerate(kinds):
        exprs.append(pool[kind][i])
    lines = [f"{x} = {a}", f"{y} = {b}"] + [f"{o} = {e}" for o, e in zip(outs, exprs)]
    code = "\n".join(lines) + f"\nprint({', '.join(outs)})"
    values = [eval_expr(e, f"{x} = {a}\n{y} = {b}") for e in exprs]
    as_int = [str(int(v)) for v in values]
    as_float = [str(float(v)) for v in values]
    correct = [str(v) for v in values]

    def flipped(idx: set[int]) -> str:
        return " ".join(
            (as_int[i] if correct[i] == as_float[i] else as_float[i]) if i in idx else correct[i]
            for i in range(len(values))
        )

    singles = [flipped({i}) for i in range(len(values))]
    rng.shuffle(singles)
    doubles = [flipped({i, j}) for i in range(len(values)) for j in range(i + 1, len(values))]
    distractors = singles + doubles + [" ".join(as_int), " ".join(as_float)]
    fi = kinds.index("float")
    ii = kinds.index("int")
    int_reason = (
        "`int()` converts the float back to an int"
        if exprs[ii].startswith("int(")
        else f"`{exprs[ii]}` uses only ints (and no `/`), so the result stays an int"
    )
    why = (
        f"`{outs[fi]}` is {correct[fi]} because {float_reasons[exprs[fi]]}. "
        f"`{outs[ii]}` is {correct[ii]} because {int_reason}."
    )
    return _output(code, MEDIUM, distractors, why, rng)


@generator(TOPIC, MEDIUM)
def gen_digit_expressions(rng: random.Random) -> Question:
    """Which expression extracts a digit / part of a number using // and %?"""
    digits = rng.sample(range(1, 10), 4)
    n = int("".join(map(str, digits)))
    v = rng.choice(["n", "num", "number", "code", "pin"])
    tasks = [
        ("the last digit of", f"{v} % 10",
         [f"{v} // 10", f"{v} / 10", f"{v} % 100", f"10 % {v}", f"{v} - 10"],
         "`% 10` keeps the remainder after dividing by 10, which is the last digit."),
        ("without its last digit:", f"{v} // 10",
         [f"{v} / 10", f"{v} % 10", f"{v} - {v} % 10", f"{v} // 100", f"{v} % 1000"],
         "`// 10` divides by 10 and throws away the remainder, which chops off the last digit."),
        ("the tens digit of", f"{v} // 10 % 10",
         [f"{v} % 10 // 10", f"{v} % 100", f"{v} // 100 % 10", f"{v} // 10", f"{v} % 10"],
         "`// 10` drops the last digit, then `% 10` keeps the new last digit, which was the tens digit."),
        ("the last two digits of", f"{v} % 100",
         [f"{v} // 100", f"{v} % 10", f"{v} / 100", f"{v} - 100", f"{v} // 10"],
         "`% 100` keeps the remainder after dividing by 100, which is the last two digits."),
        ("the first digit of", f"{v} // 1000",
         [f"{v} / 1000", f"{v} % 1000", f"{v} // 100", f"{v} % 10", f"{v} % 1000 // 100"],
         "`// 1000` throws away the last three digits of a 4-digit number, leaving the first digit."),
        ("the hundreds digit of", f"{v} // 100 % 10",
         [f"{v} % 100 // 10", f"{v} // 100", f"{v} % 1000", f"{v} // 10 % 10", f"{v} % 100"],
         "`// 100` drops the last two digits, then `% 10` keeps the last remaining digit."),
    ]
    desc, correct, wrong, rule = rng.choice(tasks)
    setup = f"{v} = {n}"
    target = eval_expr(correct, setup)
    if desc.endswith(":"):
        prompt = f"Which expression evaluates to `{target}`, which is `{v}` {desc[:-1]}?"
    else:
        prompt = f"Which expression evaluates to `{target}`, {desc} `{v}`?"
    wrong = list(wrong)
    rng.shuffle(wrong)
    return which_expression_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        setup=setup,
        target=target,
        correct_expr=correct,
        wrong_exprs=wrong,
        explanation=f"{rule} For {n} that gives {target}.",
        rng=rng,
    )


# ==========================================================================
# HARD
# ==========================================================================


@generator(TOPIC, HARD)
def gen_negative_floor_mod(rng: random.Random) -> Question:
    """// and % with negative numbers: Python floors (-7 // 2 == -4, -7 % 3 == 2)."""
    b = rng.randint(2, 6)
    a = rng.randint(b + 1, 30)
    if a % b == 0:
        a += 1
    shape = rng.choice(["neg_num", "neg_div", "identity", "true_vs_floor", "wrap"])
    if shape == "neg_num":
        x = -a
        code = f"x = {x}\nprint(x // {b}, x % {b})"
        q, r = divmod(x, b)
        tq, tr = _trunc_divmod(x, b)
        distractors = [f"{tq} {tr}", f"{q} {tr}", f"{tq} {r}", f"{tq} {-tr}"]
        why = (
            f"`//` rounds DOWN (toward negative infinity): {x} / {b} is about {x / b:.2f}, which "
            f"floors to {q}, not {tq}. Then `%` makes `q * {b} + r == {x}` true, so r = {r} "
            f"(the remainder takes the sign of the divisor)."
        )
    elif shape == "neg_div":
        code = f"x = {a}\ny = {-b}\nprint(x // y, x % y)"
        q, r = divmod(a, -b)
        tq, tr = _trunc_divmod(a, -b)
        distractors = [f"{tq} {tr}", f"{q} {tr}", f"{tq} {r}", f"{-q} {-r}"]
        why = (
            f"{a} / {-b} is about {a / -b:.2f}; `//` floors it to {q} (not {tq}). The remainder "
            f"must satisfy {q} * {-b} + r == {a}, so r = {r}: it takes the sign of the divisor."
        )
    elif shape == "identity":
        x = -a
        name = rng.choice(["x", "n", "value"])
        code = (
            f"{name} = {x}\nq = {name} // {b}\nr = {name} % {b}\n"
            f"print(q, r)\nprint(q * {b} + r)"
        )
        q, r = divmod(x, b)
        tq, tr = _trunc_divmod(x, b)
        distractors = [
            f"{tq} {tr}\n{x}",
            f"{tq} {r}\n{tq * b + r}",
            f"{q} {tr}\n{q * b + tr}",
            f"{q} {-r}\n{q * b - r}",
        ]
        why = (
            f"`//` floors: {x} / {b} is about {x / b:.2f}, so q = {q} (not {tq}). Python "
            f"guarantees q * {b} + r == {name}, so r = {r} and the second line prints {x}."
        )
    elif shape == "true_vs_floor":
        x = -a
        code = f"print({x} / {b}, {x} // {b})"
        t = x / b
        if len(repr(t)) > 8:
            b = 2 if a % 2 else 4
            if a % b == 0:
                a += 1
            x = -a
            code = f"print({x} / {b}, {x} // {b})"
            t = x / b
        q = x // b
        tq, _ = _trunc_divmod(x, b)
        distractors = [f"{t} {tq}", f"{t} {float(tq)}", f"{t} {float(q)}", f"{tq} {q}"]
        why = (
            f"`/` gives the exact float {t}. `//` rounds that DOWN to the next lower whole number, "
            f"which for a negative value is {q}, not {tq}."
        )
    else:
        name, size = rng.choice([("hour", 12), ("day", 7), ("minute", 60)])
        start = rng.randint(1, size // 2)
        back = rng.randint(start + 1, size - 1)
        code = f"{name} = {start}\n{name} = ({name} - {back}) % {size}\nprint({name})"
        result = (start - back) % size
        diff = start - back
        distractors = [str(diff), str(-diff), str((start + back) % size), str(size + back - start)]
        distractors += _nearby(result, rng)
        why = (
            f"{start} - {back} is {diff}. With a positive divisor, Python's `%` always returns a "
            f"value from 0 to {size - 1}, so {diff} % {size} wraps around to {result}."
        )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_float_precision(rng: random.Random) -> Question:
    """0.1 + 0.2 == 0.3 is False; round()/tolerance comparisons; 8 / 4 == 2 but is a float."""
    if rng.random() < 0.75:
        p, q, lit = rng.choice(_INEXACT_SUMS)
        x_expr = f"{p} + {q}"
    else:
        p, k, lit = rng.choice(_INEXACT_PRODUCTS)
        x_expr = f"{p} * {k}"
    x_val = eval_expr(x_expr)
    c = rng.randint(2, 5)
    d = rng.randint(2, 4)
    checks = [
        ("x", f"x == {lit}", True),
        ("x", f"round(x, 2) == {lit}", True),
        ("x", f"abs(x - {lit}) < 1e-9", True),
        ("y", f"y == {c}", True),
        ("y", f"isinstance(y, int)", True),
    ]
    chosen = [checks[0]] + rng.sample(checks[1:], 2)
    rng.shuffle(chosen)
    lines = [f"x = {x_expr}"]
    if any(var == "y" for var, _, _ in chosen):
        lines.append(f"y = {c * d} / {d}")
    lines += [f"print({expr})" for _, expr, _ in chosen]
    code = "\n".join(lines)
    res = run_code(code)
    if res.error:
        raise GenerationError(res.error)
    actual = [line == "True" for line in res.output.split("\n")]

    def show(bools: list[bool]) -> str:
        return "\n".join(str(v) for v in bools)

    naive = [n for _, _, n in chosen]  # what you'd expect if floats were exact
    distractors = [show(naive)]
    distractors += [show([not v if i == j else v for j, v in enumerate(actual)]) for i in range(3)]
    distractors += [show([not v for v in actual]), show([False] * 3), show([True] * 3)]
    why = (
        f"0.1-style decimals can't be stored exactly in binary, so `{x_expr}` is really "
        f"{x_val!r} and `x == {lit}` is False. Compare floats with `round()` or a small tolerance instead."
    )
    if any(var == "y" for var, _, _ in chosen):
        why += f" `{c * d} / {d}` is the float {float(c)}: it equals {c}, but it is not an `int`."
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_power_unary_minus(rng: random.Random) -> Question:
    """-3 ** 2 == -9, (-3) ** 2 == 9, and ** is right-associative."""
    a = rng.randint(2, 9)
    sq = a * a
    shape = rng.choice(["literal", "variable", "both", "trace", "right_assoc"])
    if shape == "literal":
        code = f"print(-{a} ** 2)"
        distractors = [str(sq), str(-2 * a), str(2 * a), *_nearby(-sq, rng)]
        why = f"`**` binds more tightly than the unary minus, so `-{a} ** 2` means `-({a} ** 2)` = -{sq}."
    elif shape == "variable":
        name = rng.choice(["x", "n", "temp", "delta"])
        code = f"{name} = -{a}\nprint({name} ** 2)"
        distractors = [str(-sq), str(-2 * a), str(2 * a), *_nearby(sq, rng)]
        why = (
            f"`{name}` already holds the negative number -{a}, so `{name} ** 2` squares -{a} "
            f"and gives {sq}. (Only a literal like `-{a} ** 2` is read as `-({a} ** 2)`.)"
        )
    elif shape == "both":
        code = f"print(-{a} ** 2, (-{a}) ** 2)"
        distractors = [f"{sq} {sq}", f"-{sq} -{sq}", f"{sq} -{sq}"]
        why = (
            f"`**` binds more tightly than unary minus: `-{a} ** 2` is `-({a} ** 2)` = -{sq}, "
            f"while the parentheses in `(-{a}) ** 2` square -{a} to get {sq}."
        )
    elif shape == "trace":
        name = rng.choice(["x", "n", "k"])
        code = f"{name} = {a}\ny = -{name} ** 2\nz = (-{name}) ** 2\nprint(y, z, y + z)"
        distractors = [f"{sq} {sq} {2 * sq}", f"-{sq} -{sq} -{2 * sq}", f"{sq} -{sq} 0", f"-{sq} {sq} {2 * sq}"]
        why = (
            f"`-{name} ** 2` means `-({name} ** 2)` = -{sq} because `**` binds tighter than unary "
            f"minus; `(-{name}) ** 2` squares -{a} to get {sq}. Their sum is 0."
        )
    else:
        base, e1, e2 = rng.choice([(2, 3, 2), (2, 2, 3), (3, 2, 3), (2, 4, 2), (10, 2, 3), (3, 3, 2)])
        code = f"print({base} ** {e1} ** {e2})"
        left = (base**e1) ** e2
        result = base ** (e1**e2)
        distractors = [str(left), str(base * e1 * e2), str((base**e1) * e2), str(base ** (e1 + e2))]
        why = (
            f"`**` groups from right to left: `{base} ** {e1} ** {e2}` is `{base} ** ({e1} ** {e2})` "
            f"= {base} ** {e1**e2} = {result}, not ({base} ** {e1}) ** {e2} = {left}."
        )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_simultaneous_assignment(rng: random.Random) -> Question:
    """a, b = b, a + b uses the OLD values — vs. doing it one line at a time."""
    if rng.random() < 0.45:
        x, y = rng.choice([("a", "b"), ("x", "y"), ("prev", "curr"), ("lo", "hi")])
        rules = [
            ([x, y], [y, f"{x} + {y}"]),
            ([x, y], [f"{x} + {y}", x]),
            ([x, y], [y, f"{x} * 2"]),
            ([x, y], [f"{y} + 1", f"{x} + {y}"]),
        ]
        targets, exprs = rng.choice(rules)
        s0, s1 = rng.randint(0 if "*" not in exprs[1] else 1, 2), rng.randint(1, 3)
        k = rng.randint(3, 5)

        def loop(n: int, sequential: bool) -> str:
            if sequential:
                body = "\n".join(f"    {t} = {e}" for t, e in zip(targets, exprs))
            else:
                body = f"    {', '.join(targets)} = {', '.join(exprs)}"
            return f"{x}, {y} = {s0}, {s1}\nfor _ in range({n}):\n{body}\nprint({x}, {y})"

        code = loop(k, False)
        distractors = [_run(loop(k, True)), _run(loop(k + 1, False)), _run(loop(k - 1, False)), _run(loop(k + 1, True))]
        why = (
            f"In `{', '.join(targets)} = {', '.join(exprs)}` the whole right side is evaluated "
            f"FIRST using the old values, then both names are updated at once. Tracing all "
            f"{k} iterations that way gives {_run(code)}."
        )
        return _output(code, HARD, distractors, why, rng)

    names = rng.choice([("x", "y", "z"), ("a", "b", "c"), ("p", "q", "r"), ("m", "n", "k")])
    p, q, r = names
    for _ in range(40):
        a, b = rng.sample(range(1, 10), 2)
        r_expr = rng.choice([f"{p} + {q}", f"{q} - {p}", f"{p} * 2", f"{q} + 1"])
        tuples = [
            ([p, q], [q, f"{p} + {r}"]),
            ([p, r], [r, f"{p} + {q}"]),
            ([q, r], [r, f"{q} * 2"]),
            ([p, q], [q, p]),
            ([q, p], [f"{p} + {q}", q]),
            ([r, p], [p, f"{r} - {q}"]),
        ]
        aug = rng.choice([f"{r} -= {p}", f"{p} += {r}", f"{q} *= 2", f"{r} += {q}"])
        steps = [rng.choice(tuples), aug]
        if rng.random() < 0.5:
            steps.append(rng.choice(tuples))
        if steps[-1] is aug and rng.random() < 0.5:
            steps.reverse()

        def render(seq_mode: str, drop: str | None = None) -> str:
            out = [f"{p} = {a}", f"{q} = {b}", f"{r} = {r_expr}"]
            for idx, step in enumerate(steps):
                if drop == "aug" and step is aug:
                    continue
                if drop == "last" and idx == len(steps) - 1:
                    continue
                if isinstance(step, str):
                    out.append(step)
                    continue
                targets, exprs = step
                if seq_mode == "tuple" or (seq_mode == "first" and idx > 0):
                    out.append(f"{', '.join(targets)} = {', '.join(exprs)}")
                elif seq_mode == "reverse":
                    out += [f"{t} = {e}" for t, e in reversed(list(zip(targets, exprs)))]
                else:
                    out += [f"{t} = {e}" for t, e in zip(targets, exprs)]
            out.append(f"print({p}, {q}, {r})")
            return "\n".join(out)

        code = render("tuple")
        correct = _run(code)
        seq = _run(render("seq"))
        if seq != correct and not correct.startswith("Error") and "-" not in correct:
            break
    else:
        raise GenerationError("tuple assignment did not matter")
    distractors = [
        seq,
        _run(render("reverse")),
        _run(render("first")),
        _run(render("tuple", drop="last")),
        _run(render("tuple", drop="aug")),
    ]
    vals = correct.split()
    distractors.append(" ".join([vals[0], vals[1], str(int(vals[2]) + 1)]))
    distractors.append(" ".join([str(int(vals[0]) + 1), vals[1], vals[2]]))
    distractors.append(" ".join([vals[0], str(int(vals[1]) + 1), vals[2]]))
    first_targets, first_exprs = next(step for step in steps if not isinstance(step, str))
    tuple_line = f"{', '.join(first_targets)} = {', '.join(first_exprs)}"
    why = (
        f"In a line like `{tuple_line}`, Python evaluates the entire right side using the "
        f"current values BEFORE assigning any name. Treating it as separate lines would give {seq}."
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_augmented_rhs_grouping(rng: random.Random) -> Question:
    """x *= step + 1 means x = x * (step + 1), not x * step + 1."""
    name = rng.choice(["total", "score", "x", "value", "amount"])
    other = rng.choice(["step", "bonus", "k", "rate"])
    menu = [
        ("*=", "+", "*"),
        ("*=", "-", "*"),
        ("-=", "-", "-"),
        ("-=", "+", "-"),
        ("//=", "+", "//"),
    ]
    for _ in range(40):
        start = rng.randint(10, 30)
        s = rng.randint(3, 6)
        picks = rng.sample(menu, 2)
        ks = [rng.randint(1, 2) for _ in picks]
        middle = f"{name} += {other}" if rng.random() < 0.3 else None
        lines = []
        misread = []
        for (aug, inner, base), k in zip(picks, ks):
            lines.append(f"{name} {aug} {other} {inner} {k}")
            misread.append(f"{name} = {name} {base} {other} {inner} {k}")
        if middle:
            lines.insert(1, middle)
            misread.insert(1, middle)

        def prog(body: list[str]) -> str:
            return "\n".join([f"{name} = {start}", f"{other} = {s}", *body, f"print({name})"])

        code = prog(lines)
        correct = _run(code)
        both = _run(prog(misread))
        first_only = list(lines)
        first_only[0] = misread[0]
        second_only = list(lines)
        second_only[-1] = misread[-1]
        first = _run(prog(first_only))
        second = _run(prog(second_only))
        outs = [correct, both, first, second]
        if len(set(outs)) == 4 and not any(o.startswith("Error") or o.startswith("-") for o in outs):
            break
    else:
        raise GenerationError("misreadings coincide")
    distractors = [both, first, second, *_nearby(int(correct), rng)]
    aug0, inner0, base0 = picks[0]
    why = (
        f"An augmented assignment evaluates its WHOLE right side first: `{lines[0]}` means "
        f"`{name} = {name} {base0} ({other} {inner0} {ks[0]})`, not `{misread[0].split(' = ', 1)[1]}`. "
        f"Applying that rule to every line gives {correct}."
    )
    return _output(code, HARD, distractors, why, rng)


@generator(TOPIC, HARD)
def gen_conversion_pipeline(rng: random.Random) -> Question:
    """int("4.5") raises ValueError; int(float(...)) truncates; str/num round trips."""
    shape = rng.choice(["price", "price", "chain", "divide"])
    if shape == "price":
        w = rng.randint(2, 9)
        frac = rng.choice(["5", "25", "75"])
        price = f"{w}.{frac}"
        qty = rng.randint(2, 3)
        pname, qname = rng.choice([("price", "qty"), ("weight", "count"), ("cost", "n"), ("size", "times")])
        variant = rng.choice(["int", "int_float", "float", "repeat", "plus"])
        expr = {
            "int": f"int({pname}) * {qname}",
            "int_float": f"int(float({pname})) * {qname}",
            "float": f"float({pname}) * {qname}",
            "repeat": f"{pname} * {qname}",
            "plus": f"{pname} + {qname}",
        }[variant]
        code = f'{pname} = "{price}"\n{qname} = {qty}\ntotal = {expr}\nprint(total)'
        fval = float(price) * qty
        pool = {
            "int": str(w * qty),
            "float": repr(fval),
            "value": VALUE_ERROR,
            "type": TYPE_ERROR,
            "repeat": price * qty,
        }
        order = {
            "int": ["int", "float", "type", "repeat"],
            "int_float": ["float", "value", "int", "type"],
            "float": ["int", "type", "value", "repeat"],
            "repeat": ["float", "type", "int", "value"],
            "plus": ["value", "float", "repeat", "int"],
        }[variant]
        distractors = [pool[key] for key in order] + [repr(float(w * qty))]
        why = {
            "int": f'`int()` only accepts strings that look like a whole number, so `int("{price}")` '
                   f"raises a ValueError. Use `int(float(...))` or `float(...)` instead.",
            "int_float": f'`float("{price}")` gives {float(price)}, then `int()` drops the decimals to '
                         f"get {w}, so total is {w} * {qty} = {w * qty}.",
            "float": f'`float("{price}")` is {float(price)}, and {float(price)} * {qty} = {fval}.',
            "repeat": f'`{pname}` is still a string, and string * int repeats it {qty} times: '
                      f'"{price * qty}". No arithmetic happens.',
            "plus": f"`{pname}` is a string and `{qname}` is an int; `+` can't combine a `str` and an "
                    f"`int`, so it raises a TypeError.",
        }[variant]
    elif shape == "chain":
        a = rng.randint(2, 8)
        b = a + 1
        last = rng.choice(["repeat", "int", "plus"])
        tail = {"repeat": "print(c * 2)", "int": "print(int(c) * 2)", "plus": "print(c + 2)"}[last]
        code = f'a = "{a}"\nb = int(a) + 1\nc = str(b) + a\n{tail}'
        joined = f"{b}{a}"
        pool = {
            "repeat": joined * 2,
            "int": str(int(joined) * 2),
            "sum_repeat": str(b + a) * 2,
            "sum_int": str((b + a) * 2),
            "type": TYPE_ERROR,
            "plus_join": f"{joined}2",
        }
        order = {
            "repeat": ["int", "sum_repeat", "type", "sum_int"],
            "int": ["repeat", "sum_int", "type", "sum_repeat"],
            "plus": ["plus_join", "int", "sum_int", "repeat"],
        }[last]
        distractors = [pool[key] for key in order]
        why = (
            f'`b` is the int {b}, but `str(b) + a` joins two strings, so `c` is the string "{joined}". '
            + {
                "repeat": f'A string times 2 repeats it: "{joined * 2}".',
                "int": f"`int(c)` converts it back to the number {joined}, and {joined} * 2 = {int(joined) * 2}.",
                "plus": "Adding the int 2 to a string raises a TypeError.",
            }[last]
        )
    else:
        d = rng.randint(2, 5)
        k = rng.randint(2, 9)
        a = d * k
        op = rng.choice(["/", "//"])
        name = rng.choice(["n", "share", "each", "result"])
        mark = rng.choice(["!", "?", " items", " pts"])
        code = f'{name} = int("{a}") {op} {d}\nprint(str({name}) + "{mark}")'
        float_text = f"{float(k)}{mark}"
        int_text = f"{k}{mark}"
        distractors = [int_text if op == "/" else float_text, TYPE_ERROR, f"{a} {op} {d}{mark}", VALUE_ERROR]
        why = (
            f'`int("{a}")` is {a}. ' + (
                f"`/` always produces a float, so `{name}` is {float(k)} and `str()` keeps the `.0`."
                if op == "/" else
                f"`//` on two ints gives the int {k}, so `str({name})` is \"{k}\" with no `.0`."
            ) + f' Joining it with "{mark}" gives the output shown.'
        )
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, allow_error=True)


@generator(TOPIC, HARD)
def gen_digit_loop(rng: random.Random) -> Question:
    """Loops driven by % 10 and //= 10 (digit sum, reversing, repeated division)."""
    shape = rng.choice(["digit_sum", "reverse", "divide"])
    if shape == "digit_sum":
        digits = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(rng.randint(2, 3))]
        n = int("".join(map(str, digits)))
        acc = rng.choice(["total", "digit_sum", "s"])
        code = (
            f"n = {n}\n{acc} = 0\nwhile n > 0:\n    {acc} += n % 10\n    n //= 10\nprint({acc}, n)"
        )
        s = sum(digits)
        first = digits[0]
        distractors = [f"{s} {n}", f"{s - first} {first}", f"{s - first} 0", f"{s} {first}", f"{digits[-1]} 0"]
        why = (
            f"Each pass adds the last digit (`n % 10`) and then chops it off (`n //= 10`), so the "
            f"loop adds {' + '.join(map(str, reversed(digits)))} = {s}. It stops only when `n` reaches 0."
        )
    elif shape == "reverse":
        digits = rng.sample(range(1, 10), rng.randint(3, 4))  # distinct, so never a palindrome
        n = int("".join(map(str, digits)))
        rev = int("".join(map(str, reversed(digits))))
        acc = rng.choice(["rev", "flipped", "result"])
        code = (
            f"n = {n}\n{acc} = 0\nwhile n > 0:\n    {acc} = {acc} * 10 + n % 10\n    n //= 10\nprint({acc})"
        )
        distractors = [str(n), str(rev // 10), str(sum(digits)), str(rev * 10), str(rev % (10 ** (len(digits) - 1)))]
        why = (
            f"Each pass shifts `{acc}` left one place (`* 10`) and appends the last digit of `n` "
            f"(`n % 10`), then drops that digit from `n`. The digits of {n} come out last-first: {rev}."
        )
    else:
        d = rng.randint(2, 4)
        n0 = rng.randint(20, 150)
        code = f"n = {n0}\nsteps = 0\nwhile n > 1:\n    n //= {d}\n    steps += 1\nprint(n, steps)"
        n, steps, trace = n0, 0, [n0]
        while n > 1:
            n //= d
            steps += 1
            trace.append(n)
        to_zero = _run(f"n = {n0}\nsteps = 0\nwhile n > 0:\n    n //= {d}\n    steps += 1\nprint(n, steps)")
        distractors = [to_zero, f"{n} {steps - 1}", f"{n} {steps + 1}", f"{1 - n} {steps}", f"{n0} 0"]
        why = (
            f"`n` goes {' → '.join(map(str, trace))}, one `//= {d}` per pass, so the loop runs "
            f"{steps} times and stops as soon as `n > 1` is False (n = {n})."
        )
    return _output(code, HARD, distractors, why, rng)
