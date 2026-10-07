"""Question generators for the "oop" topic (Classes & OOP).

Covers creating objects and ``__init__``, methods and ``self``, object state
changed by method calls, class vs instance attributes (reading through an
instance, shadowing, instance counters, the shared mutable class attribute
trap), ``__str__`` / ``__repr__`` and other dunder methods (``__len__``,
``__eq__``, ``__add__``, ``__lt__``), inheritance, overriding and ``super()``,
dynamic dispatch through ``self``, multiple inheritance and the MRO,
``isinstance`` / ``issubclass``, ``@property``, ``@classmethod`` /
``@staticmethod``, method chaining, aliasing of objects, and the classic
errors (missing ``self``, missing attributes, wrong argument counts).
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
    error_choice,
    eval_expr,
    generator,
    int_distractors,
    output_question,
    run_code,
    which_expression_question,
)

TOPIC = "oop"
PRINT = "What does this code print?"
PRINT_OR_ERROR = "What is printed, or which error is raised?"
ATTR_ERR = error_choice("AttributeError")
TYPE_ERR = error_choice("TypeError")
NAME_ERR = error_choice("NameError")
VALUE_ERR = error_choice("ValueError")
MAX_SNIPPET_LINES = 14

_PETS = ["Rex", "Fido", "Bella", "Max", "Luna", "Coco", "Milo", "Nala"]
_SURNAMES = ["Lee", "Kim", "Diaz", "Shah", "Ng", "Cruz", "Park", "Rossi"]
_THINGS = ["pen", "cup", "book", "lamp", "mug", "map", "key"]


# --------------------------------------------------------------------------
# Private helpers
# --------------------------------------------------------------------------


def _prog(*blocks: str) -> str:
    """Join top-level blocks (classes, functions, main code) with two blank lines (PEP 8)."""
    code = "\n\n\n".join(b.strip("\n") for b in blocks if b)
    if len(code.split("\n")) > MAX_SNIPPET_LINES:
        raise GenerationError(f"snippet too long:\n{code}")
    return code


def _cls(name: str, *members: str, base: str | None = None) -> str:
    """A class statement; members (attribute groups, methods) are separated by a blank line."""
    head = f"class {name}({base}):" if base else f"class {name}:"
    body = "\n\n".join(m.strip("\n") for m in members if m)
    return f"{head}\n{body or '    pass'}"


def _meth(header: str, *body: str, deco: str | None = None) -> str:
    """A method for a class body, e.g. ``_meth("area(self)", "return self.w * self.h")``."""
    lines = [f"    @{deco}"] if deco else []
    lines.append(f"    def {header}:")
    lines.extend(f"        {line}" for line in body)
    return "\n".join(lines)


def _attrs(*pairs: tuple[str, object]) -> str:
    """Class-attribute lines; each value is Python source text."""
    return "\n".join(f"    {name} = {value}" for name, value in pairs)


def _init(*params: str, extra=()) -> str:
    """``__init__`` storing each parameter as ``self.<param>``, then any ``extra`` lines."""
    sig = ", ".join(("self", *params))
    body = [f"self.{p} = {p}" for p in params] + list(extra)
    return _meth(f"__init__({sig})", *body)


def _q(text: str) -> str:
    """A double-quoted string literal (our words never contain quotes)."""
    return f'"{text}"'


def _norm(text: str) -> str:
    return "\n".join(line.rstrip() for line in str(text).strip("\n").split("\n"))


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
    expect=None,
) -> Question:
    """An output question; ``expect`` (if given) double-checks our own reasoning."""
    if expect is not None:
        got = _run(code)
        if _norm(got) != _norm(str(expect)):
            raise GenerationError(f"expected {expect!r} but the snippet gives {got!r}:\n{code}")
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=_usable(distractors),
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=prompt == PRINT_OR_ERROR,
    )


def _calls(var: str, call: str, k: int, rng: random.Random, max_lines: int) -> tuple[str, str]:
    """``k`` calls of ``var.call``, written out or as a loop; returns (code, description)."""
    if k <= max_lines and rng.random() < 0.5:
        return "\n".join([f"{var}.{call}"] * k), f"is called {k} times"
    return f"for _ in range({k}):\n    {var}.{call}", f"runs once per loop pass, {k} times"


# ==========================================================================
# EASY
# ==========================================================================

# (class, text attribute, text values, number attribute, number range, variable names)
_RECORDS = [
    ("Dog", "name", _PETS, "age", (1, 12), ["pet", "dog", "buddy"]),
    ("Player", "name", NAMES, "score", (5, 60), ["player", "hero"]),
    ("Book", "title", ["Dune", "Emma", "Holes", "Matilda", "Wonder"], "pages", (90, 400), ["book", "novel"]),
    ("Robot", "model", ["R2", "K9", "Bolt", "Zed", "Astro"], "battery", (10, 99), ["bot", "robot"]),
]


def _computed_attribute(rng: random.Random) -> Question:
    """``__init__`` may also compute new attributes from its parameters."""
    kind = rng.choice(["area", "full_name", "total"])
    if kind == "area":
        w, h = rng.sample(range(2, 10), 2)
        v = rng.choice(["r", "rect", "box"])
        klass = _cls("Rectangle", _init("width", "height", extra=["self.area = width * height"]))
        main = f"{v} = Rectangle({w}, {h})\nprint({v}.area)"
        expect = w * h
        distractors = _nums([w + h, 2 * (w + h), f"{w} {h}", "width * height"], expect, rng)
        why = (
            f"`__init__` can compute attributes too: `self.area = width * height` runs when the "
            f"object is created, so `Rectangle({w}, {h})` stores {w} * {h} = {expect}."
        )
    elif kind == "full_name":
        first, last = rng.choice(NAMES), rng.choice(_SURNAMES)
        v = rng.choice(["p", "person", "user"])
        klass = _cls("Person", _init("first", "last", extra=['self.full_name = first + " " + last']))
        main = f"{v} = Person({_q(first)}, {_q(last)})\nprint({v}.full_name)"
        expect = f"{first} {last}"
        distractors = [f"{first}{last}", f"{last} {first}", "first last", first, ATTR_ERR]
        why = (
            f"`__init__` builds `self.full_name` from its two parameters, joining "
            f"{_q(first)}, a space and {_q(last)} into {expect}."
        )
    else:
        item, price, qty = rng.choice(_THINGS), rng.randint(2, 9), rng.randint(2, 6)
        klass = _cls("Order", _init("item", "price", "quantity", extra=["self.total = price * quantity"]))
        main = f"order = Order({_q(item)}, {price}, {qty})\nprint(order.item, order.total)"
        expect = f"{item} {price * qty}"
        distractors = [f"{item} {price + qty}", f"{item} {price}", f"{item} {qty}", f"{item} price * quantity"]
        why = (
            f"Besides storing `item`, `price` and `quantity`, `__init__` computes "
            f"`self.total = price * quantity` = {price} * {qty} = {price * qty}."
        )
    return _output(_prog(klass, main), EASY, distractors, why, rng, expect=expect)


@generator(TOPIC, EASY)
def gen_init_attributes(rng: random.Random) -> Question:
    """``__init__`` stores the constructor's arguments as attributes of the new object."""
    shape = rng.choice(["two_attrs", "two_objects", "two_objects", "keywords", "computed", "computed"])
    if shape == "computed":
        return _computed_attribute(rng)
    cls, sattr, pool, nattr, (lo, hi), var_names = rng.choice(_RECORDS)
    klass = _cls(cls, _init(sattr, nattr))
    prompt = PRINT
    if shape == "two_attrs":
        s, n, v = rng.choice(pool), rng.randint(lo, hi), rng.choice(var_names)
        main = f"{v} = {cls}({_q(s)}, {n})\nprint({v}.{nattr}, {v}.{sattr})"
        expect = f"{n} {s}"
        distractors = [f"{s} {n}", f"{nattr} {sattr}", f"{n} '{s}'", f"{v}.{nattr} {v}.{sattr}"]
        why = (
            f"`{cls}({_q(s)}, {n})` runs `__init__`, which stores the arguments as "
            f"`self.{sattr}` and `self.{nattr}` on the new object. So `{v}.{nattr}` is {n} and "
            f"`{v}.{sattr}` is {s}, printed in that order."
        )
    elif shape == "two_objects":
        s1, s2 = rng.sample(pool, 2)
        n1, n2 = rng.sample(range(lo, hi + 1), 2)
        low = cls.lower()
        a, b = rng.choice([("a", "b"), ("first", "second"), (f"{low}1", f"{low}2")])
        main = (
            f"{a} = {cls}({_q(s1)}, {n1})\n{b} = {cls}({_q(s2)}, {n2})\n"
            f"print({a}.{sattr}, {b}.{nattr})"
        )
        expect = f"{s1} {n2}"
        distractors = [f"{s1} {n1}", f"{s2} {n2}", f"{s2} {n1}", f"{sattr} {nattr}"]
        why = (
            f"Each `{cls}(...)` call creates a separate object with its own attributes. "
            f"`{a}.{sattr}` comes from the first object ({s1}) and `{b}.{nattr}` from the "
            f"second ({n2})."
        )
    else:
        s, n, v = rng.choice(pool), rng.randint(lo, hi), rng.choice(var_names)
        main = f"{v} = {cls}({nattr}={n}, {sattr}={_q(s)})\nprint({v}.{sattr}, {v}.{nattr})"
        expect = f"{s} {n}"
        distractors = [f"{n} {s}", TYPE_ERR, ATTR_ERR, f"{sattr} {nattr}"]
        prompt = PRINT_OR_ERROR
        why = (
            f"Keyword arguments are matched to `__init__`'s parameters by name, not by position, "
            f"so `{sattr}` still receives {_q(s)} and `{nattr}` receives {n}."
        )
    return _output(_prog(klass, main), EASY, distractors, why, rng, prompt=prompt, expect=expect)


@generator(TOPIC, EASY)
def gen_method_uses_self(rng: random.Random) -> Question:
    """Inside a method, ``self`` is the object the method was called on."""
    kind = rng.choice(["rect", "rect", "greet", "cost"])
    prompt = PRINT
    if kind == "rect":
        method = rng.choice(["area", "perimeter"])
        is_area = method == "area"

        def val(w: int, h: int) -> int:
            return w * h if is_area else 2 * (w + h)

        def other(w: int, h: int) -> int:
            return 2 * (w + h) if is_area else w * h

        def formula(w: int, h: int) -> str:
            return f"{w} * {h}" if is_area else f"2 * ({w} + {h})"

        body = "return self.width * self.height" if is_area else "return 2 * (self.width + self.height)"
        klass = _cls("Rectangle", _init("width", "height"), _meth(f"{method}(self)", body))
        w, h = rng.sample(range(2, 10), 2)
        if rng.random() < 0.5:
            v = rng.choice(["r", "rect", "box", "room"])
            main = f"{v} = Rectangle({w}, {h})\nprint({v}.{method}())"
            expect = val(w, h)
            if is_area:
                cands = [other(w, h), w + h, 2 * w * h, w * w]
            else:
                cands = [w + h, w * h, 2 * w + h, w + h + 2]
            distractors = _nums(cands, expect, rng)
            why = (
                f"When `{v}.{method}()` runs, `self` is `{v}`, so `self.width` is {w} and "
                f"`self.height` is {h}. The method returns {formula(w, h)} = {expect}."
            )
        else:
            w2, h2 = rng.sample(range(2, 10), 2)
            while val(w2, h2) == val(w, h):
                w2, h2 = rng.sample(range(2, 10), 2)
            va, vb = val(w, h), val(w2, h2)
            main = (
                f"a = Rectangle({w}, {h})\nb = Rectangle({w2}, {h2})\n"
                f"print(a.{method}(), b.{method}())"
            )
            expect = f"{va} {vb}"
            distractors = [
                f"{va} {va}",
                f"{other(w, h)} {other(w2, h2)}",
                f"{vb} {va}",
                f"{vb} {vb}",
                f"{w + h} {w2 + h2}",
            ]
            why = (
                f"Each call gets its own object as `self`: `a.{method}()` uses {w} and {h} "
                f"({formula(w, h)} = {va}), while `b.{method}()` uses {w2} and {h2} "
                f"({formula(w2, h2)} = {vb})."
            )
    elif kind == "greet":
        me, them = rng.sample(NAMES, 2)
        word = rng.choice(["Hi", "Hello", "Hey"])
        v = rng.choice(["g", "bot", "host"])
        klass = _cls(
            "Greeter",
            _init("name"),
            _meth("greet(self, other)", f'return f"{word} {{other}}, I am {{self.name}}"'),
        )
        main = f"{v} = Greeter({_q(me)})\nprint({v}.greet({_q(them)}))"
        expect = f"{word} {them}, I am {me}"
        distractors = [f"{word} {me}, I am {them}", TYPE_ERR, f"{word} other, I am {me}", f"{word} {them}, I am name"]
        prompt = PRINT_OR_ERROR
        why = (
            f"Python passes `{v}` in as `self` automatically and {_q(them)} fills the `other` "
            f"parameter. So `other` is {them} and `self.name` is the {me} stored by `__init__`."
        )
    else:
        item, price, qty = rng.choice(_THINGS), rng.randint(2, 9), rng.randint(2, 6)
        klass = _cls("Item", _init("name", "price"), _meth("cost(self, quantity)", "return self.price * quantity"))
        main = f"{item} = Item({_q(item)}, {price})\nprint({item}.cost({qty}))"
        expect = price * qty
        distractors = _nums([price + qty, TYPE_ERR, price, qty], expect, rng)
        prompt = PRINT_OR_ERROR
        why = (
            f"`{item}.cost({qty})` passes `{item}` as `self` and {qty} as `quantity`, so the "
            f"method returns `self.price * quantity` = {price} * {qty} = {expect}."
        )
    return _output(_prog(klass, main), EASY, distractors, why, rng, prompt=prompt, expect=expect)


@generator(TOPIC, EASY)
def gen_method_changes_state(rng: random.Random) -> Question:
    """A method that assigns to ``self.<attr>`` changes the object permanently."""
    kind = rng.choice(["counter", "amounts", "lamp", "bag"])
    if kind == "counter":
        cls, attr, meth, v = rng.choice(
            [
                ("Counter", "count", "increment", "c"),
                ("Clicker", "clicks", "click", "clicker"),
                ("StepTracker", "steps", "step", "tracker"),
            ]
        )
        k = rng.randint(2, 4)
        klass = _cls(cls, _init(extra=[f"self.{attr} = 0"]), _meth(f"{meth}(self)", f"self.{attr} += 1"))
        calls, how = _calls(v, f"{meth}()", k, rng, max_lines=4)
        main = f"{v} = {cls}()\n{calls}\nprint({v}.{attr})"
        expect = k
        distractors = _nums([0, k - 1, k + 1, 1], k, rng)
        why = (
            f"`__init__` starts `self.{attr}` at 0, and every `{meth}()` call adds 1 to that same "
            f"object's attribute. `{v}.{meth}()` {how}, so the value ends at {k}."
        )
    elif kind == "amounts":
        cls, attr, meth, param, v = rng.choice(
            [
                ("Wallet", "money", "add", "amount", "wallet"),
                ("Game", "score", "add_points", "points", "game"),
                ("Tank", "litres", "fill", "amount", "tank"),
            ]
        )
        amounts = [rng.randint(2, 20) for _ in range(rng.randint(2, 3))]
        klass = _cls(
            cls, _init(extra=[f"self.{attr} = 0"]), _meth(f"{meth}(self, {param})", f"self.{attr} += {param}")
        )
        calls = "\n".join(f"{v}.{meth}({a})" for a in amounts)
        main = f"{v} = {cls}()\n{calls}\nprint({v}.{attr})"
        expect = sum(amounts)
        distractors = _nums(
            [amounts[-1], 0, amounts[0], len(amounts), expect - amounts[-1]], expect, rng
        )
        why = (
            f"Each call adds its argument to `self.{attr}`, and the object keeps that value "
            f"between calls: {' + '.join(map(str, amounts))} = {expect}."
        )
    elif kind == "lamp":
        k = rng.randint(2, 5)
        state = k % 2 == 1
        klass = _cls(
            "Lamp",
            _init(extra=["self.is_on = False", "self.clicks = 0"]),
            _meth("toggle(self)", "self.is_on = not self.is_on", "self.clicks += 1"),
        )
        calls, how = _calls("lamp", "toggle()", k, rng, max_lines=2)
        main = f"lamp = Lamp()\n{calls}\nprint(lamp.is_on, lamp.clicks)"
        expect = f"{state} {k}"
        distractors = [f"{not state} {k}", f"{state} {k - 1}", "False 0", f"{not state} {k + 1}", "True 1"]
        why = (
            f"Each `toggle()` flips `self.is_on` and adds 1 to `self.clicks` on the same lamp. "
            f"It {how}; starting from False, {k} flips leave `is_on` as {state}, and `clicks` is {k}."
        )
    else:
        cls, attr, meth, v, pool = rng.choice(
            [
                ("Bag", "items", "add", "bag", _THINGS),
                ("Playlist", "songs", "add_song", "playlist", ["intro", "remix", "encore", "ballad"]),
                ("Basket", "fruits", "put", "basket", ["apple", "lemon", "mango", "cherry"]),
            ]
        )
        things = rng.sample(pool, rng.randint(2, 3))
        klass = _cls(
            cls, _init(extra=[f"self.{attr} = []"]), _meth(f"{meth}(self, item)", f"self.{attr}.append(item)")
        )
        calls = "\n".join(f"{v}.{meth}({_q(t)})" for t in things)
        main = f"{v} = {cls}()\n{calls}\nprint({v}.{attr})"
        expect = repr(things)
        distractors = ["[]", repr(things[-1:]), repr(things[:1]), " ".join(things), repr(things[::-1])]
        why = (
            f"`__init__` gives the object one empty list, and each `{meth}` call appends to that "
            f"same list, so it keeps every item in order: {things}."
        )
    return _output(_prog(klass, main), EASY, distractors, why, rng, expect=expect)


# (class, class attribute, possible values as source, instance attribute, instance values)
_CLASS_ATTR = [
    ("Player", "max_level", ["10", "20", "50", "99"], "name", NAMES),
    ("Employee", "company", ['"Acme"', '"Zenith"', '"Nova"', '"Orbit"'], "name", NAMES),
    ("Student", "school", ['"Oakwood"', '"Riverside"', '"Hillcrest"'], "name", NAMES),
    ("Car", "wheels", ["4", "6", "3"], "color", ["red", "blue", "green", "black"]),
    ("Cat", "legs", ["4"], "name", _PETS),
]


@generator(TOPIC, EASY)
def gen_class_attribute(rng: random.Random) -> Question:
    """A class attribute is shared: instances look it up on the class."""
    cls, attr, values, iattr, pool = rng.choice(_CLASS_ATTR)
    shape = rng.choice(["read", "read", "change", "change"]) if len(values) > 1 else "read"
    src = rng.choice(values)
    val = src.strip('"')
    klass = _cls(cls, _attrs((attr, src)), _init(iattr))
    low = cls.lower()
    if shape == "read":
        s = rng.choice(pool)
        x = rng.choice(["a", low, f"my_{low}"])
        if rng.random() < 0.5:
            main = f"{x} = {cls}({_q(s)})\nprint({x}.{iattr}, {x}.{attr})"
            expect = f"{s} {val}"
            distractors = [ATTR_ERR, f"{s} None", f"{s} {attr}", f"{val} {s}"]
        else:
            main = f"{x} = {cls}({_q(s)})\nprint({x}.{attr}, {cls}.{attr})"
            expect = f"{val} {val}"
            distractors = [ATTR_ERR, f"None {val}", f"{attr} {val}", TYPE_ERR]
        why = (
            f"`{attr} = {src}` sits in the class body, so it is a class attribute shared by every "
            f"`{cls}`. `{x}` has no `{attr}` of its own, so Python looks it up on the class and "
            f"finds {val}."
        )
    else:
        new_src = rng.choice([v for v in values if v != src])
        new = new_src.strip('"')
        s1, s2 = rng.sample(pool, 2)
        a, b = rng.choice([("a", "b"), (f"{low}1", f"{low}2")])
        lines = [f"{a} = {cls}({_q(s1)})", f"{b} = {cls}({_q(s2)})", f"{cls}.{attr} = {new_src}"]
        if rng.random() < 0.5:
            lines = [lines[0], lines[2], lines[1]]
            distractors = [f"{val} {new}", f"{val} {val}", f"{new} {val}", ATTR_ERR]
        else:
            distractors = [f"{val} {val}", f"{val} {new}", f"{new} {val}", ATTR_ERR]
        main = "\n".join(lines) + f"\nprint({a}.{attr}, {b}.{attr})"
        expect = f"{new} {new}"
        why = (
            f"Objects don't keep a copy of a class attribute; they look it up on the class each "
            f"time. After `{cls}.{attr} = {new_src}`, both `{a}` and `{b}` see {new}, no matter "
            f"when they were created."
        )
    return _output(_prog(klass, main), EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


@generator(TOPIC, EASY)
def gen_str_method(rng: random.Random) -> Question:
    """``print`` and ``str()`` use the object's ``__str__`` method."""
    kind = rng.choice(["point", "pet", "price", "score"])
    if kind == "point":
        x, y = rng.sample(range(1, 10), 2)
        label = "Point:"
        klass = _cls("Point", _init("x", "y"), _meth("__str__(self)", 'return f"({self.x}, {self.y})"'))
        ctor, shown = f"Point({x}, {y})", f"({x}, {y})"
        wrong = [f"Point({x}, {y})", f"{x} {y}", f"({y}, {x})", "(x, y)"]
        var = rng.choice(["p", "point", "spot"])
    elif kind == "pet":
        name, animal = rng.choice(_PETS), rng.choice(["dog", "cat", "parrot", "hamster", "rabbit"])
        label = "Pet:"
        klass = _cls("Pet", _init("name", "kind"), _meth("__str__(self)", 'return f"{self.name} the {self.kind}"'))
        ctor, shown = f"Pet({_q(name)}, {_q(animal)})", f"{name} the {animal}"
        wrong = [f"{animal} the {name}", f"Pet({name}, {animal})", "name the kind", f"{name} {animal}"]
        var = rng.choice(["pet", "buddy", "friend"])
    elif kind == "price":
        amount = rng.randint(2, 99)
        label = "Cost:"
        klass = _cls("Price", _init("amount"), _meth("__str__(self)", 'return f"${self.amount}"'))
        ctor, shown = f"Price({amount})", f"${amount}"
        wrong = [str(amount), f"Price({amount})", "$amount", f"${amount}.00"]
        var = rng.choice(["price", "cost", "tag"])
    else:
        name, points = rng.choice(NAMES), rng.randint(5, 99)
        label = "Top:"
        klass = _cls(
            "Score", _init("name", "points"), _meth("__str__(self)", 'return f"{self.name}: {self.points} pts"')
        )
        ctor, shown = f"Score({_q(name)}, {points})", f"{name}: {points} pts"
        wrong = [f"{name} {points}", f"Score({name}, {points})", f"{points}: {name} pts", "name: points pts"]
        var = rng.choice(["score", "best", "entry"])
    form = rng.choice(["plain", "plain", "label", "str", "concat"])
    if form == "plain":
        main, fmt = f"{var} = {ctor}\nprint({var})", "{}"
        how = f"`print({var})` calls `{var}.__str__()` and prints the string it returns"
    elif form == "label":
        main, fmt = f"{var} = {ctor}\nprint({_q(label)}, {var})", label + " {}"
        how = f"`print` turns each argument into text; for `{var}` that means calling its `__str__`"
    elif form == "str":
        main, fmt = f"{var} = {ctor}\ntext = str({var})\nprint(text)", "{}"
        how = f"`str({var})` calls `{var}.__str__()`, so `text` holds the string it returns"
    else:
        main, fmt = f'{var} = {ctor}\nprint("[" + str({var}) + "]")', "[{}]"
        how = f"`str({var})` calls `{var}.__str__()`, and the result is glued between the brackets"
    expect = fmt.replace("{}", shown)
    distractors = [fmt.replace("{}", w) for w in wrong]
    why = f"{how}: {shown}. Defining `__str__` is how a class controls the way its objects are printed."
    return _output(_prog(klass, main), EASY, distractors, why, rng, expect=expect)


@generator(TOPIC, EASY)
def gen_call_method_expr(rng: random.Random) -> Question:
    """Calling a method needs ``obj.method()``; attributes are read with ``obj.attr``."""
    kind = rng.choice(["rect", "person", "wallet"])
    if kind == "rect":
        w, h = rng.sample(range(2, 10), 2)
        cls, v, m = "Rectangle", rng.choice(["r", "rect", "box"]), "area"
        klass = _cls(cls, _init("width", "height"), _meth("area(self)", "return self.width * self.height"))
        ctor, result = f"Rectangle({w}, {h})", w * h
        manual = f"{v}.width + {v}.height"
        attr, attr_val = rng.choice([("width", w), ("height", h)])
    elif kind == "person":
        first, last = rng.choice(NAMES), rng.choice(_SURNAMES)
        cls, v, m = "Person", rng.choice(["p", "user", "person"]), "full_name"
        klass = _cls(cls, _init("first", "last"), _meth("full_name(self)", 'return self.first + " " + self.last'))
        ctor, result = f"Person({_q(first)}, {_q(last)})", f"{first} {last}"
        manual = f"{v}.first + {v}.last"
        attr, attr_val = rng.choice([("first", first), ("last", last)])
    else:
        coins = rng.sample(range(1, 10), rng.randint(2, 3))
        cls, v, m = "Wallet", rng.choice(["w", "wallet", "purse"]), "total"
        klass = _cls(cls, _init("coins"), _meth("total(self)", "return sum(self.coins)"))
        ctor, result = f"Wallet({coins})", sum(coins)
        manual = f"len({v}.coins)"
        attr, attr_val = "coins", coins
    setup = _prog(klass, f"{v} = {ctor}")
    if rng.random() < 0.65:
        target, correct = result, f"{v}.{m}()"
        core = [f"{v}.{m}", f"{m}({v})", f"{cls}.{m}()", f"{v}.{m}({v})"]
        rng.shuffle(core)
        wrong = core[:2] + [manual] + core[2:]
        why = (
            f"`{v}.{m}()` looks the method up on `{v}`'s class and calls it, passing `{v}` as "
            f"`self` automatically, which gives {target!r}. Without `()`, `{v}.{m}` is just the "
            f"method object, and `{cls}.{m}()` has no object to use as `self`."
        )
    else:
        target, correct = attr_val, f"{v}.{attr}"
        wrong = [f"{v}.{attr}()", f"{cls}.{attr}", f"self.{attr}", f"{v}[{_q(attr)}]", attr]
        rng.shuffle(wrong)
        why = (
            f"`{v}.{attr}` reads the attribute that `__init__` stored on the object `{v}`. It is "
            f"plain data, not a method, so it isn't called with `()`; and `self` only exists "
            f"inside methods, while the class `{cls}` itself has no `{attr}`."
        )
    return which_expression_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Which expression evaluates to `{target!r}`?",
        setup=setup,
        target=target,
        correct_expr=correct,
        wrong_exprs=wrong,
        explanation=why,
        rng=rng,
    )


# (class, text attr, values, number attr, range, method, body, result format,
#  attribute that is never set, (its source, shown), method that doesn't exist, variable)
_ERR_THEMES = [
    ("Dog", "name", _PETS, "age", (1, 12), "speak", 'return self.name + " says woof"', "{} says woof",
     "color", ('"brown"', "brown"), "bark", "dog"),
    ("Robot", "model", ["R2", "K9", "Bolt", "Zed"], "battery", (10, 99), "beep", 'return self.model + " beeps"',
     "{} beeps", "speed", ("5", "5"), "talk", "bot"),
    ("Player", "name", NAMES, "level", (1, 20), "greet", 'return "I am " + self.name', "I am {}",
     "team", ('"red"', "red"), "hello", "player"),
]


@generator(TOPIC, EASY)
def gen_object_errors(rng: random.Random) -> Question:
    """Missing attributes, wrong argument counts and instance-vs-class access."""
    (cls, sattr, pool, nattr, (lo, hi), meth, body, res_fmt, missing, (msrc, mshown), wrong_meth, x) = rng.choice(
        _ERR_THEMES
    )
    s, n = rng.choice(pool), rng.randint(lo, hi)
    klass = _cls(cls, _init(sattr, nattr), _meth(f"{meth}(self)", body))
    result = res_fmt.format(s)
    create = f"{x} = {cls}({_q(s)}, {n})"
    shape = rng.choice(
        ["missing_attr", "missing_attr", "wrong_args", "wrong_args", "class_access", "wrong_method",
         "add_attr", "add_attr", "method_ok"]
    )
    if shape == "missing_attr":
        main = f"{create}\nprint({x}.{missing})"
        expect, distractors = ATTR_ERR, ["None", NAME_ERR, TYPE_ERR, NOTHING_PRINTED]
        why = (
            f"`__init__` only creates `{sattr}` and `{nattr}`. `{x}` has no attribute called "
            f"`{missing}`, so reading it raises `AttributeError` (Python does not hand back `None`)."
        )
    elif shape == "wrong_args":
        main = f"{x} = {cls}({_q(s)})\nprint({x}.{sattr})"
        expect, distractors = TYPE_ERR, [s, ATTR_ERR, "None", NAME_ERR]
        why = (
            f"`__init__(self, {sattr}, {nattr})` needs two arguments besides `self`, but "
            f"`{cls}({_q(s)})` passes only one, so creating the object raises `TypeError` before "
            f"anything is printed."
        )
    elif shape == "class_access":
        main = f"{create}\nprint({cls}.{sattr})"
        expect, distractors = ATTR_ERR, [s, sattr, NAME_ERR, TYPE_ERR]
        why = (
            f"`self.{sattr} = {sattr}` stores the value on each object, not on the class. "
            f"`{x}.{sattr}` would work, but the class `{cls}` itself has no `{sattr}`, so "
            f"`AttributeError` is raised."
        )
    elif shape == "wrong_method":
        main = f"{create}\nprint({x}.{wrong_meth}())"
        expect, distractors = ATTR_ERR, [result, NAME_ERR, "None", TYPE_ERR]
        why = (
            f"The class defines `{meth}`, not `{wrong_meth}`. Looking up a method that doesn't "
            f"exist fails exactly like a missing attribute: `AttributeError`."
        )
    elif shape == "add_attr":
        main = f"{create}\n{x}.{missing} = {msrc}\nprint({x}.{missing}, {x}.{nattr})"
        expect = f"{mshown} {n}"
        distractors = [ATTR_ERR, f"None {n}", TYPE_ERR, f"{missing} {n}"]
        why = (
            f"Attributes don't have to be created in `__init__`: assigning `{x}.{missing} = {msrc}` "
            f"simply adds a new attribute to that object, so it prints {mshown} and then `{nattr}` = {n}."
        )
    else:
        main = f"{create}\nprint({x}.{meth}(), {x}.{nattr})"
        expect = f"{result} {n}"
        distractors = [TYPE_ERR, ATTR_ERR, f"None {n}", NAME_ERR]
        why = (
            f"`{x}.{meth}()` passes the object as `self`, so `self.{sattr}` is {s} and the method "
            f"returns {result!r}; `{x}.{nattr}` is {n}."
        )
    return _output(_prog(klass, main), EASY, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


# ==========================================================================
# MEDIUM
# ==========================================================================

# parent, child, (inherited method, value), (overridden method, parent value, child value),
# (method only the child has, value)
_OVERRIDE = [
    ("Animal", "Bird", ("eat", "eats"), ("move", "walks", "flies"), ("sing", "tweets")),
    ("Vehicle", "Boat", ("honk", "beep"), ("travel", "drives", "sails"), ("anchor", "anchored")),
    ("Employee", "Manager", ("greet", "hello"), ("role", "staff", "boss"), ("approve", "approved")),
    ("Phone", "Tablet", ("charge", "charging"), ("size", "small", "large"), ("draw", "drawing")),
]


@generator(TOPIC, MEDIUM)
def gen_inheritance_override(rng: random.Random) -> Question:
    """A child inherits methods it doesn't define and overrides the ones it does."""
    parent, child, (inh, iv), (ov, pv, cv), (co, cov) = rng.choice(_OVERRIDE)
    pclass = _cls(parent, _meth(f"{inh}(self)", f"return {_q(iv)}"), _meth(f"{ov}(self)", f"return {_q(pv)}"))
    shape = rng.choice(["child_both", "child_both", "both_objects", "child_only_err", "child_only_ok"])
    if shape in ("child_both", "both_objects"):
        cclass = _cls(child, _meth(f"{ov}(self)", f"return {_q(cv)}"), base=parent)
        if shape == "child_both":
            main = f"print({child}().{inh}(), {child}().{ov}())"
            expect = f"{iv} {cv}"
            distractors = [f"{iv} {pv}", ATTR_ERR, f"{pv} {cv}", f"None {cv}", f"{cv} {cv}"]
            why = (
                f"`{child}` inherits `{inh}` from `{parent}` unchanged, so it returns {iv}. But "
                f"`{child}` defines its own `{ov}`, which overrides the parent's: Python looks in "
                f"the child class first and finds {cv}."
            )
        else:
            main = f"print({parent}().{ov}(), {child}().{ov}())"
            expect = f"{pv} {cv}"
            distractors = [f"{cv} {cv}", f"{pv} {pv}", f"{cv} {pv}", ATTR_ERR]
            why = (
                f"Overriding only affects the child class. A `{parent}` object still uses "
                f"`{parent}.{ov}` ({pv}), while a `{child}` object finds its own `{ov}` first ({cv})."
            )
    else:
        cclass = _cls(child, _meth(f"{co}(self)", f"return {_q(cov)}"), base=parent)
        if shape == "child_only_err":
            main = f"print({parent}().{co}())"
            expect = ATTR_ERR
            distractors = [cov, "None", TYPE_ERR, NAME_ERR]
            why = (
                f"Inheritance only flows downward: `{child}` gets everything `{parent}` has, but "
                f"`{parent}` knows nothing about methods added in `{child}`. A `{parent}` object "
                f"has no `{co}`, so `AttributeError` is raised."
            )
        else:
            main = f"print({child}().{co}(), {child}().{ov}())"
            expect = f"{cov} {pv}"
            distractors = [ATTR_ERR, f"{cov} None", TYPE_ERR, f"None {pv}"]
            why = (
                f"`{child}` has its own `{co}` ({cov}) and inherits `{ov}` from `{parent}` "
                f"because it doesn't define one, so `{ov}` returns the parent's {pv}."
            )
    code = _prog(pclass, cclass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


# parent, child, text attr, values, number attr, range, child's extra attr, range, variable
_SUPER = [
    ("Employee", "Manager", "name", NAMES, "pay", (30, 90), "bonus", (5, 20), "boss"),
    ("Character", "Wizard", "name", NAMES, "health", (50, 90), "shield", (5, 30), "hero"),
    ("Account", "Savings", "owner", NAMES, "balance", (100, 500), "interest", (10, 50), "acct"),
]


@generator(TOPIC, MEDIUM)
def gen_super_calls(rng: random.Random) -> Question:
    """``super()`` reuses the parent's ``__init__`` or method from inside the child."""
    shape = rng.choice(["init_then_modify", "init_then_modify", "forgot_super", "extend_greet", "extend_cost"])
    if shape in ("init_then_modify", "forgot_super"):
        parent, child, sattr, pool, nattr, (lo, hi), extra, (elo, ehi), v = rng.choice(_SUPER)
        s, n, e = rng.choice(pool), rng.randint(lo, hi), rng.randint(elo, ehi)
        pclass = _cls(parent, _init(sattr, nattr))
        header = f"__init__(self, {sattr}, {nattr}, {extra})"
        create = f"{v} = {child}({_q(s)}, {n}, {e})"
        if shape == "init_then_modify":
            cclass = _cls(
                child,
                _meth(header, f"super().__init__({sattr}, {nattr})", f"self.{nattr} += {extra}"),
                base=parent,
            )
            main = f"{create}\nprint({v}.{sattr}, {v}.{nattr})"
            expect = f"{s} {n + e}"
            distractors = [f"{s} {n}", ATTR_ERR, f"{s} {e}", f"None {n + e}", f"{s} {n}{e}"]
            why = (
                f"`super().__init__({sattr}, {nattr})` runs `{parent}.__init__` on the new object, "
                f"setting `{sattr}` = {s} and `{nattr}` = {n}. The child then adds `{extra}`: "
                f"{n} + {e} = {n + e}."
            )
        else:
            cclass = _cls(child, _meth(header, f"self.{extra} = {extra}"), base=parent)
            main = f"{create}\nprint({v}.{extra}, {v}.{sattr})"
            expect = ATTR_ERR
            distractors = [f"{e} {s}", f"{e} None", TYPE_ERR, NAME_ERR]
            why = (
                f"`{child}` defines its own `__init__`, which replaces the parent's, and it never "
                f"calls `super().__init__(...)`. So only `{extra}` is set; `{sattr}` doesn't "
                f"exist and reading it raises `AttributeError`."
            )
        code = _prog(pclass, cclass, main)
    elif shape == "extend_greet":
        word, name = rng.choice(["Hello", "Hi", "Welcome"]), rng.choice(NAMES)
        child = rng.choice(["LoudGreeter", "Shouter"])
        pclass = _cls("Greeter", _meth("greet(self, name)", f"return {_q(word + ', ')} + name"))
        cclass = _cls(child, _meth("greet(self, name)", 'return super().greet(name).upper() + "!"'), base="Greeter")
        main = f"print({child}().greet({_q(name)}))"
        base = f"{word}, {name}"
        expect = base.upper() + "!"
        distractors = [f"{base}!", f"{word.upper()}, {name}!", base.upper(), base, f"{word}, {name.upper()}!"]
        why = (
            f"`super().greet(name)` runs the parent's version, which returns {_q(base)}. The child "
            f"then upper-cases that result and adds \"!\", giving {expect}."
        )
        code = _prog(pclass, cclass, main)
    else:
        m, extra, w = rng.randint(2, 5), rng.randrange(5, 20, 5), rng.randint(2, 9)
        child = rng.choice(["Express", "Overnight"])
        pclass = _cls("Shipping", _meth("cost(self, weight)", f"return weight * {m}"))
        cclass = _cls(child, _meth("cost(self, weight)", f"return super().cost(weight) + {extra}"), base="Shipping")
        main = f"print({child}().cost({w}), Shipping().cost({w}))"
        expect = f"{w * m + extra} {w * m}"
        distractors = [
            f"{w * m + extra} {w * m + extra}",
            f"{w + extra} {w * m}",
            f"{(w + extra) * m} {w * m}",
            f"{w * m} {w * m}",
            f"{extra} {w * m}",
        ]
        why = (
            f"`{child}().cost({w})` calls `super().cost({w})`, which runs the parent's version: "
            f"{w} * {m} = {w * m}, then adds {extra} to get {w * m + extra}. The plain `Shipping` "
            f"object is unaffected by the child and returns {w * m}."
        )
        code = _prog(pclass, cclass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


_SHADOW = [("Player", "lives"), ("Spaceship", "shields"), ("Robot", "speed"), ("Hero", "potions")]


@generator(TOPIC, MEDIUM)
def gen_class_attr_shadowing(rng: random.Random) -> Question:
    """Assigning through an instance creates an instance attribute that hides the class one."""
    cls, attr = rng.choice(_SHADOW)
    v, x, y = rng.sample(range(1, 10), 3)
    with_init = rng.random() < 0.4
    members = [_attrs((attr, v))]
    if with_init:
        members.append(_init("name"))
        na, nb = rng.sample(NAMES, 2)
        make = f'a = {cls}("{na}")\nb = {cls}("{nb}")'
    else:
        make = f"a = {cls}()\nb = {cls}()"
    klass = _cls(cls, *members)
    shape = rng.choice(["set_instance", "set_instance", "instance_then_class", "augmented", "class_then_instance"])
    if shape == "set_instance":
        main = f"{make}\na.{attr} = {x}\nprint(a.{attr}, b.{attr}, {cls}.{attr})"
        expect = f"{x} {v} {v}"
        distractors = [f"{x} {x} {x}", f"{x} {x} {v}", f"{x} {v} {x}", f"{v} {v} {v}"]
        why = (
            f"`a.{attr} = {x}` creates a NEW attribute on `a` only, which hides the class "
            f"attribute for `a`. `b` has no own `{attr}`, so it (and the class) still show {v}."
        )
    elif shape == "instance_then_class":
        main = f"{make}\na.{attr} = {x}\n{cls}.{attr} = {y}\nprint(a.{attr}, b.{attr})"
        expect = f"{x} {y}"
        distractors = [f"{y} {y}", f"{x} {v}", f"{x} {x}", f"{v} {y}"]
        why = (
            f"`a.{attr} = {x}` gives `a` its own attribute. Changing `{cls}.{attr}` to {y} affects "
            f"every object that still reads the class attribute (`b`), but `a`'s own {x} hides it."
        )
    elif shape == "augmented":
        main = f"{make}\na.{attr} -= 1\nprint(a.{attr}, b.{attr}, {cls}.{attr})"
        expect = f"{v - 1} {v} {v}"
        distractors = [f"{v - 1} {v - 1} {v - 1}", f"{v - 1} {v} {v - 1}", f"{v - 1} {v - 1} {v}", ATTR_ERR]
        why = (
            f"`a.{attr} -= 1` means `a.{attr} = a.{attr} - 1`: it reads the class value {v}, then "
            f"ASSIGNS {v - 1} to a new attribute on `a`. The class attribute, and therefore "
            f"`b`, still hold {v}."
        )
    else:
        main = f"{make}\n{cls}.{attr} = {y}\na.{attr} = {x}\nprint(a.{attr}, b.{attr}, {cls}.{attr})"
        expect = f"{x} {y} {y}"
        distractors = [f"{x} {x} {x}", f"{y} {y} {y}", f"{x} {v} {y}", f"{x} {y} {x}"]
        why = (
            f"`{cls}.{attr} = {y}` changes the shared class attribute, seen by `b`. Then "
            f"`a.{attr} = {x}` creates an attribute on `a` alone, leaving the class at {y}."
        )
    code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


# class, counter attribute, names for the objects
_COUNTERS = [
    ("Robot", "count", ["Astro", "Bolt", "Chip", "Dot"]),
    ("Student", "total", NAMES),
    ("Ticket", "sold", ["A1", "B2", "C3", "D4"]),
    ("Order", "created", ["tea", "cake", "soup", "toast"]),
]


@generator(TOPIC, MEDIUM)
def gen_instance_counter(rng: random.Random) -> Question:
    """A class attribute updated in ``__init__`` counts the objects created."""
    cls, cnt, pool = rng.choice(_COUNTERS)
    shape = rng.choice(["direct", "loop", "self_bug", "numbering"])
    if shape == "direct":
        k = rng.randint(2, 3)
        names = rng.sample(pool, k)
        varnames = ["a", "b", "c"][:k]
        klass = _cls(cls, _attrs((cnt, 0)), _init("name", extra=[f"{cls}.{cnt} += 1"]))
        made = "\n".join(f"{vn} = {cls}({_q(nm)})" for vn, nm in zip(varnames, names))
        main = f"{made}\nprint({cls}.{cnt}, a.{cnt})"
        expect = f"{k} {k}"
        distractors = [f"{k} 1", "1 1", f"{k} 0", "0 0", f"{k - 1} {k - 1}"]
        why = (
            f"Each `__init__` runs `{cls}.{cnt} += 1`, updating the ONE counter stored on the class, "
            f"so after {k} objects it is {k}. `a.{cnt}` isn't a snapshot: `a` has no own `{cnt}`, "
            f"so it reads the class's current value, {k}."
        )
    elif shape == "loop":
        k = rng.randint(3, 4)
        names = rng.sample(pool, k)
        klass = _cls(cls, _attrs((cnt, 0)), _init("name", extra=[f"{cls}.{cnt} += 1"]))
        main = f"for name in {names}:\n    item = {cls}(name)\nprint({cls}.{cnt}, item.name)"
        expect = f"{k} {names[-1]}"
        distractors = [f"1 {names[-1]}", f"{k} {names[0]}", f"{k - 1} {names[-1]}", f"0 {names[-1]}"]
        why = (
            f"The loop creates {k} objects; `item` only keeps the last one ({names[-1]}), but every "
            f"`__init__` call bumped the shared `{cls}.{cnt}`, so it is {k}."
        )
    elif shape == "self_bug":
        names = rng.sample(pool, 2)
        klass = _cls(cls, _attrs((cnt, 0)), _init("name", extra=[f"self.{cnt} += 1"]))
        main = f"a = {cls}({_q(names[0])})\nb = {cls}({_q(names[1])})\nprint({cls}.{cnt}, a.{cnt}, b.{cnt})"
        expect = "0 1 1"
        distractors = ["2 1 2", "2 2 2", "0 1 2", "1 1 1", "0 0 0"]
        why = (
            f"`self.{cnt} += 1` reads the class's 0 and then ASSIGNS 1 to a new attribute on that "
            f"object. Each object gets its own `{cnt}` of 1, and `{cls}.{cnt}` is never changed: "
            f"to share a counter you must write `{cls}.{cnt} += 1`."
        )
    else:
        names = rng.sample(pool, 3)
        klass = _cls(
            cls, _attrs((cnt, 0)), _init("name", extra=[f"self.number = {cls}.{cnt}", f"{cls}.{cnt} += 1"])
        )
        made = "\n".join(f"{vn} = {cls}({_q(nm)})" for vn, nm in zip("abc", names))
        main = f"{made}\nprint(a.number, c.number, {cls}.{cnt})"
        expect = "0 2 3"
        distractors = ["1 3 3", "0 2 2", "3 3 3", "0 0 3", "1 2 3"]
        why = (
            f"Each object copies the counter's current value into `self.number` BEFORE adding 1: "
            f"`a` gets 0, `b` gets 1, `c` gets 2. After three objects `{cls}.{cnt}` is 3."
        )
    code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, expect=expect)


@generator(TOPIC, MEDIUM)
def gen_dunder_methods(rng: random.Random) -> Question:
    """``len()``, ``==`` and ``+`` call ``__len__``, ``__eq__`` and ``__add__``."""
    shape = rng.choice(["len", "eq", "eq", "no_eq", "add", "no_add"])
    if shape == "len":
        songs = rng.sample(WORDS, rng.randint(2, 4))
        extra = rng.choice([w for w in WORDS if w not in songs])
        cls, attr, v = rng.choice([("Playlist", "songs", "mix"), ("Team", "members", "team"), ("Deck", "cards", "deck")])
        klass = _cls(cls, _init(attr), _meth("__len__(self)", f"return len(self.{attr})"))
        n = len(songs)
        if rng.random() < 0.5:
            main = f"{v} = {cls}({songs})\n{v}.{attr}.append({_q(extra)})\nprint(len({v}))"
            expect = n + 1
            distractors = _nums([n, TYPE_ERR, 1, n + 2], expect, rng)
            note = f"; after the append the list holds {n + 1} items"
        else:
            main = f"{v} = {cls}({songs})\nprint(len({v}))"
            expect = n
            distractors = _nums([TYPE_ERR, 1, n + 1, n - 1], expect, rng)
            note = f", which is {n}"
        why = f"`len({v})` calls `{v}.__len__()`, which returns `len(self.{attr})`{note}."
    elif shape in ("eq", "no_eq"):
        cls, attr = rng.choice([("Coin", "value"), ("Card", "rank"), ("Badge", "level")])
        p, q = rng.sample(range(1, 20), 2)
        if shape == "eq":
            klass = _cls(cls, _init(attr), _meth("__eq__(self, other)", f"return self.{attr} == other.{attr}"))
            main = f"print({cls}({p}) == {cls}({p}), {cls}({p}) == {cls}({q}))"
            expect = "True False"
            distractors = ["False False", "True True", TYPE_ERR, "False True"]
            why = (
                f"`==` calls `__eq__`, which compares the `{attr}` attributes: {p} == {p} is True "
                f"and {p} == {q} is False, even though all four are different objects."
            )
        else:
            klass = _cls(cls, _init(attr))
            main = f"a = {cls}({p})\nb = {cls}({p})\nc = a\nprint(a == b, a == c)"
            expect = "False True"
            distractors = ["True True", "False False", "True False", TYPE_ERR]
            why = (
                f"Without an `__eq__` method, `==` falls back to checking whether both sides are "
                f"the SAME object. `a` and `b` are two separate objects (same `{attr}`, but that "
                f"isn't compared), while `c` is just another name for `a`."
            )
    else:
        cls, attr = rng.choice([("Money", "amount"), ("Distance", "km"), ("Points", "value")])
        vals = rng.sample(range(2, 30), rng.choice([2, 2, 3]))
        args = " + ".join(f"{cls}({x})" for x in vals)
        main = f"total = {args}\nprint(total.{attr})"
        if shape == "add":
            klass = _cls(
                cls, _init(attr), _meth("__add__(self, other)", f"return {cls}(self.{attr} + other.{attr})")
            )
            expect = sum(vals)
            distractors = _nums([TYPE_ERR, ATTR_ERR, vals[0], "".join(map(str, vals))], expect, rng)
            why = (
                f"`+` calls `__add__`, which returns a NEW `{cls}` holding the sum of the "
                f"`{attr}` values, so `total.{attr}` is {' + '.join(map(str, vals))} = {expect}."
            )
        else:
            klass = _cls(cls, _init(attr))
            expect = TYPE_ERR
            distractors = [sum(vals), ATTR_ERR, "".join(map(str, vals)), NAME_ERR]
            why = (
                f"Python only knows how to `+` two `{cls}` objects if the class defines "
                f"`__add__`. This one doesn't, so the addition raises `TypeError`."
            )
    code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


_SIBLINGS = [("Vehicle", "Car", "Bike", "ride"), ("Animal", "Dog", "Cat", "pet"),
             ("Shape", "Circle", "Square", "shape"), ("Account", "Savings", "Checking", "acct")]
_CHAINS = [("Animal", "Dog", "Puppy", "pup"), ("Vehicle", "Car", "Taxi", "cab"),
           ("Shape", "Polygon", "Square", "tile"), ("Employee", "Manager", "Director", "boss")]


@generator(TOPIC, MEDIUM)
def gen_isinstance_issubclass(rng: random.Random) -> Question:
    """``isinstance`` respects inheritance, ``type(...) ==`` does not; subclassing is one-way."""
    if rng.random() < 0.5:
        base, own, sib, o = rng.choice(_SIBLINGS)
        setup = _prog(_cls(base), _cls(own, base=base), _cls(sib, base=base), f"{o} = {own}()")
        pool = [
            (f"isinstance({o}, {base})", 3,
             f"`{o}` is a `{own}`, and `{own}` inherits from `{base}`, so `{o}` also counts as a `{base}`."),
            (f"issubclass({own}, {base})", 3, f"`class {own}({base})` makes `{own}` a subclass of `{base}`."),
            (f"type({o}) == {own}", 1, f"`type()` gives the exact class `{o}` was created from: `{own}`."),
            (f"isinstance({o}, {sib})", 2,
             f"`{sib}` is a sibling of `{own}` (both inherit from `{base}`), but `{o}` is not a `{sib}`."),
            (f"issubclass({base}, {own})", 3,
             f"Inheritance is one-way: `{own}` is a subclass of `{base}`, not the other way round."),
            (f"type({o}) == {base}", 3,
             f"`type({o})` is exactly `{own}`; unlike `isinstance`, comparing types ignores inheritance."),
            (f"isinstance({own}, {base})", 2,
             f"`{own}` is a class, not an object made from `{base}`; comparing classes needs `issubclass`."),
        ]
    else:
        base, mid, leaf, o = rng.choice(_CHAINS)
        setup = _prog(_cls(base), _cls(mid, base=base), _cls(leaf, base=mid), f"{o} = {leaf}()")
        pool = [
            (f"isinstance({o}, {base})", 3,
             f"`{leaf}` inherits from `{mid}`, which inherits from `{base}`, so a `{leaf}` object is "
             f"an instance of every ancestor, including `{base}`."),
            (f"issubclass({leaf}, {base})", 3,
             f"`issubclass` follows the whole chain: `{leaf}` → `{mid}` → `{base}`."),
            (f"isinstance({o}, {mid})", 1, f"`{o}` is a `{leaf}`, and every `{leaf}` is also a `{mid}`."),
            (f"issubclass({mid}, {leaf})", 3,
             f"Inheritance is one-way: `{mid}` is the PARENT of `{leaf}`, not a subclass of it."),
            (f"type({o}) == {mid}", 3,
             f"`type({o})` is exactly `{leaf}`; comparing types with `==` ignores inheritance."),
            (f"isinstance({mid}(), {leaf})", 2,
             f"A `{mid}` object is not a `{leaf}`: a parent's objects don't get the child's type."),
            (f"issubclass({base}, {mid})", 1, f"`{base}` is an ancestor of `{mid}`, not a subclass of it."),
        ]
    graded = []
    for expr, weight, note in pool:
        graded.append((expr, weight, note, bool(eval_expr(expr, setup))))
    target = rng.random() < 0.5
    rights = [g for g in graded if g[3] is target]
    wrongs = [g for g in graded if g[3] is not target]
    correct = rng.choices(rights, weights=[g[1] for g in rights])[0]
    rng.shuffle(wrongs)
    wrongs.sort(key=lambda g: -g[1])
    wrong_exprs = [g[0] for g in wrongs]
    if target:
        wrong_exprs.append(f"issubclass({o}, {setup.split()[1].rstrip(':')})")
    why = f"{correct[2]} So `{correct[0]}` is {target}. By contrast, {wrongs[0][2][0].lower()}{wrongs[0][2][1:]}"
    return which_expression_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which expression evaluates to `{target}`?",
        setup=setup,
        target=target,
        correct_expr=correct[0],
        wrong_exprs=wrong_exprs,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_property(rng: random.Random) -> Question:
    """``@property`` is read like an attribute but recomputed on every access."""
    kind = rng.choice(["square", "person", "wallet"])
    if kind == "square":
        old, new = rng.sample(range(2, 10), 2)
        v, prop = rng.choice(["sq", "tile", "board"]), "area"
        klass = _cls("Square", _init("side"), _meth("area(self)", "return self.side * self.side", deco="property"))
        make, change = f"{v} = Square({old})", f"{v}.side = {new}"
        before, after, assigned = old * old, new * new, rng.choice([20, 50, 100])
        extra = [new * 2, old * new]
        detail = f"{new} * {new} = {after}"
        ptype = "int"
    elif kind == "person":
        first, last = rng.choice(NAMES), rng.choice(_SURNAMES)
        new_last = rng.choice([s for s in _SURNAMES if s != last])
        v, prop = rng.choice(["p", "user", "member"]), "full_name"
        klass = _cls(
            "Person",
            _init("first", "last"),
            _meth("full_name(self)", 'return self.first + " " + self.last', deco="property"),
        )
        make, change = f"{v} = Person({_q(first)}, {_q(last)})", f"{v}.last = {_q(new_last)}"
        before, after, assigned = f"{first} {last}", f"{first} {new_last}", _q(f"{first} {new_last}")
        extra = [f"{first}{new_last}", f"{first} {last} {new_last}"]
        detail = f"{_q(first)} + \" \" + {_q(new_last)}"
        ptype = "str"
    else:
        coins = rng.sample(range(1, 10), 2)
        add = rng.choice([c for c in range(1, 10) if c not in coins])
        v, prop = rng.choice(["w", "wallet", "purse"]), "total"
        klass = _cls("Wallet", _init("coins"), _meth("total(self)", "return sum(self.coins)", deco="property"))
        make, change = f"{v} = Wallet({coins})", f"{v}.coins.append({add})"
        before, after, assigned = sum(coins), sum(coins) + add, rng.choice([0, 50, 100])
        extra = [add, sum(coins) + 2 * add]
        detail = f"sum({coins + [add]}) = {after}"
        ptype = "int"
    shape = rng.choice(["recompute", "recompute", "call_it", "assign"])
    if shape == "recompute":
        main = f"{make}\n{change}\nprint({v}.{prop})"
        expect = after
        distractors = [before, TYPE_ERR, ATTR_ERR, *extra]
        why = (
            f"`@property` makes `{prop}` look like an attribute, but its method runs every time "
            f"it is read, so it sees the current data: {detail}. It was not frozen when the "
            f"object was created."
        )
    elif shape == "call_it":
        main = f"{make}\nprint({v}.{prop}())"
        expect = TYPE_ERR
        distractors = [before, ATTR_ERR, "None", NAME_ERR]
        why = (
            f"With `@property`, `{v}.{prop}` (no parentheses) already runs the method and gives the "
            f"{ptype} {before!r}. Adding `()` then tries to call that {ptype}, which raises `TypeError`."
        )
    else:
        main = f"{make}\n{v}.{prop} = {assigned}\nprint({v}.{prop})"
        expect = ATTR_ERR
        distractors = [str(assigned).strip('"'), before, TYPE_ERR, "None"]
        why = (
            f"A property defined with only `@property` (no setter) is read-only: assigning "
            f"`{v}.{prop} = ...` raises `AttributeError`. Change the underlying data instead."
        )
    code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


@generator(TOPIC, MEDIUM)
def gen_object_aliasing(rng: random.Random) -> Question:
    """Variables and parameters refer to objects; changing the object is seen everywhere."""
    cls, attr = rng.choice([("Player", "score"), ("Hero", "gold"), ("Plant", "height")])
    klass = _cls(cls, _init("name", attr))
    n1, n2 = rng.sample(NAMES, 2)
    s1, s2 = rng.randint(2, 20), rng.randint(2, 20)
    d = rng.randint(2, 9)
    shape = rng.choice(["alias", "alias", "copy", "function", "loop"])
    if shape == "alias":
        main = f"a = {cls}({_q(n1)}, {s1})\nb = a\nb.{attr} += {d}\nprint(a.{attr}, b.{attr})"
        expect = f"{s1 + d} {s1 + d}"
        distractors = [f"{s1} {s1 + d}", f"{s1 + d} {s1}", f"{s1} {s1}", f"{s1 + d} {s1 + 2 * d}"]
        why = (
            f"`b = a` does not copy the object; it makes `b` a second name for the SAME "
            f"`{cls}`. Changing `b.{attr}` changes that one object, so both names show {s1 + d}."
        )
        code = _prog(klass, main)
    elif shape == "copy":
        main = (
            f"a = {cls}({_q(n1)}, {s1})\nb = {cls}(a.name, a.{attr})\n"
            f"b.{attr} += {d}\nprint(a.{attr}, b.{attr})"
        )
        expect = f"{s1} {s1 + d}"
        distractors = [f"{s1 + d} {s1 + d}", f"{s1 + d} {s1}", f"{s1} {s1}", f"{s1 + d} {s1 + 2 * d}"]
        why = (
            f"`{cls}(a.name, a.{attr})` builds a brand-new object with the same values. `b` is a "
            f"separate object, so adding {d} to `b.{attr}` leaves `a.{attr}` at {s1}."
        )
        code = _prog(klass, main)
    elif shape == "function":
        fname = rng.choice(["add_bonus", "reward", "boost"])
        func = f"def {fname}(p, amount):\n    p.{attr} += amount"
        main = f"x = {cls}({_q(n1)}, {s1})\n{fname}(x, {d})\nprint(x.{attr})"
        expect = s1 + d
        distractors = _nums([s1, d, "None", s1 + 2 * d], expect, rng)
        why = (
            f"Passing `x` to `{fname}` passes the object itself, not a copy: the parameter `p` "
            f"refers to the same `{cls}`. So `p.{attr} += {d}` changes `x.{attr}` to {s1 + d}."
        )
        code = _prog(klass, func, main)
    else:
        factor = rng.choice([2, 3])
        main = (
            f"team = [{cls}({_q(n1)}, {s1}), {cls}({_q(n2)}, {s2})]\nfor member in team:\n"
            f"    member.{attr} *= {factor}\nprint(team[0].{attr}, team[1].{attr})"
        )
        expect = f"{s1 * factor} {s2 * factor}"
        distractors = [f"{s1} {s2}", f"{s1} {s2 * factor}", f"{s1 * factor} {s2}", f"{s1 * factor} {s1 * factor}"]
        why = (
            f"The loop variable `member` refers to each object in the list in turn, so "
            f"`member.{attr} *= {factor}` changes the objects themselves: {s1} → {s1 * factor} and "
            f"{s2} → {s2 * factor}."
        )
        code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, expect=expect)


@generator(TOPIC, MEDIUM)
def gen_forgot_self(rng: random.Random) -> Question:
    """Classic slips: no ``self`` parameter, no ``self.`` prefix, attribute set too late."""
    bug = rng.choice(["no_self_param", "bare_name", "late_attr", "bare_method"])
    buggy = rng.random() < 0.7
    if bug == "no_self_param":
        cls, attr, val, meth, sound = rng.choice(
            [("Robot", "name", "R2", "beep", "Beep!"), ("Dog", "name", "Rex", "bark", "Woof!"),
             ("Bell", "size", "big", "ring", "Ding!")]
        )
        header = f"{meth}()" if buggy else f"{meth}(self)"
        klass = _cls(cls, _init(attr), _meth(header, f"return {_q(sound)}"))
        v = cls.lower()
        main = f"{v} = {cls}({_q(val)})\nprint({v}.{meth}())"
        if buggy:
            expect, distractors = TYPE_ERR, [sound, NAME_ERR, ATTR_ERR, "None"]
            why = (
                f"`{v}.{meth}()` automatically passes `{v}` as the first argument, but `{meth}()` "
                f"was defined with no parameters to receive it, so Python raises `TypeError`. "
                f"Instance methods need `self` as their first parameter."
            )
        else:
            expect, distractors = sound, [TYPE_ERR, NAME_ERR, "None", ATTR_ERR]
            why = (
                f"`{meth}(self)` receives `{v}` as `self` (unused here) and returns {_q(sound)}, "
                f"which is printed."
            )
    elif bug == "bare_name":
        cls, attr, pool, fmt = rng.choice(
            [("Player", "name", NAMES, "I am "), ("Pet", "name", _PETS, "My name is "),
             ("Planet", "title", ["Mars", "Venus", "Pluto"], "Welcome to ")]
        )
        val = rng.choice(pool)
        ref = attr if buggy else f"self.{attr}"
        meth = rng.choice(["intro", "describe"])
        klass = _cls(cls, _init(attr), _meth(f"{meth}(self)", f"return {_q(fmt)} + {ref}"))
        v = rng.choice(["p", "obj", "item"])
        main = f"{v} = {cls}({_q(val)})\nprint({v}.{meth}())"
        if buggy:
            expect, distractors = NAME_ERR, [f"{fmt}{val}", ATTR_ERR, TYPE_ERR, f"{fmt}{attr}"]
            why = (
                f"Inside `{meth}`, the bare name `{attr}` is a local/global variable, and none "
                f"exists, so Python raises `NameError`. The object's data must be reached through "
                f"`self.{attr}`; `__init__`'s parameter `{attr}` vanished when `__init__` finished."
            )
        else:
            expect, distractors = f"{fmt}{val}", [NAME_ERR, ATTR_ERR, f"{fmt}{attr}", TYPE_ERR]
            why = f"`self.{attr}` reads the value `__init__` stored on `{v}`, so the method returns {_q(fmt + val)}."
    elif bug == "late_attr":
        cls, flag, start, counter = rng.choice(
            [("Timer", "running", "start", "ticks"), ("Game", "active", "begin", "score"),
             ("Engine", "on", "ignite", "rpm")]
        )
        klass = _cls(
            cls,
            _init(extra=[f"self.{flag} = False"]),
            _meth(f"{start}(self)", f"self.{flag} = True", f"self.{counter} = 0"),
        )
        v = cls.lower()
        if buggy:
            main = f"{v} = {cls}()\nprint({v}.{flag}, {v}.{counter})"
            expect, distractors = ATTR_ERR, ["False 0", "False None", "True 0", TYPE_ERR]
            why = (
                f"`self.{counter}` is only created when `{start}()` runs, and it was never called. "
                f"So `{v}` has `{flag}` but no `{counter}` attribute yet: `AttributeError`."
            )
        else:
            main = f"{v} = {cls}()\n{v}.{start}()\nprint({v}.{flag}, {v}.{counter})"
            expect, distractors = "True 0", [ATTR_ERR, "False 0", "True None", "False None"]
            why = (
                f"Calling `{v}.{start}()` sets `{flag}` to True and creates `{counter}` = 0 on the "
                f"object, so both attributes exist when they are printed."
            )
    else:
        x = rng.randint(2, 9)
        cls, helper, outer = rng.choice([("Calculator", "double", "quadruple"), ("Number", "twice", "four_times")])
        call = f"{helper}()" if buggy else f"self.{helper}()"
        klass = _cls(
            cls,
            _init("x"),
            _meth(f"{helper}(self)", "return self.x * 2"),
            _meth(f"{outer}(self)", f"return {call} * 2"),
        )
        main = f"c = {cls}({x})\nprint(c.{outer}())"
        if buggy:
            expect, distractors = NAME_ERR, [x * 4, ATTR_ERR, TYPE_ERR, x * 2]
            why = (
                f"Methods are not plain functions in scope: inside `{outer}`, the bare name "
                f"`{helper}` doesn't exist, so `NameError`. Another method of the same object must "
                f"be called as `self.{helper}()`."
            )
        else:
            expect, distractors = x * 4, [NAME_ERR, x * 2, ATTR_ERR, x * 8]
            why = (
                f"`self.{helper}()` calls the other method on the same object, returning "
                f"{x} * 2 = {x * 2}; `{outer}` doubles that to {x * 4}."
            )
    code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


@generator(TOPIC, MEDIUM)
def gen_class_and_static_methods(rng: random.Random) -> Question:
    """``@staticmethod`` gets no ``self``; ``@classmethod`` gets the class as ``cls``."""
    shape = rng.choice(["static", "from_text", "class_state", "class_state"])
    if shape == "static":
        limit = rng.choice([25, 30, 35])
        cur, test = rng.randint(10, limit - 1), rng.randint(limit + 1, 45)
        cls, meth, attr, v = rng.choice(
            [("Weather", "is_hot", "temp", "today"), ("Oven", "is_hot", "degrees", "oven")]
        )
        klass = _cls(cls, _init(attr), _meth("is_hot(degrees)", f"return degrees > {limit}", deco="staticmethod"))
        if rng.random() < 0.5:
            main = f"{v} = {cls}({cur})\nprint({cls}.{meth}({test}), {v}.{meth}({v}.{attr}))"
            expect = "True False"
            distractors = [TYPE_ERR, "True True", "False False", "False True"]
        else:
            main = f"{v} = {cls}({cur})\nprint({v}.{meth}({v}.{attr}), {cls}.{meth}({test}))"
            expect = "False True"
            distractors = [TYPE_ERR, "True True", "False False", "True False"]
        why = (
            f"A `@staticmethod` receives no `self`, so it works the same whether called on the "
            f"class or on an object: {test} > {limit} is True and {cur} > {limit} is False."
        )
    elif shape == "from_text":
        x, y = rng.sample(range(1, 10), 2)
        sep = rng.choice([",", "-", "x"])
        klass = _cls(
            "Point",
            _init("x", "y"),
            _meth("from_text(cls, text)", f"x, y = text.split({_q(sep)})", "return cls(int(x), int(y))",
                  deco="classmethod"),
        )
        op = rng.choice(["+", "*"])
        main = f"p = Point.from_text({_q(f'{x}{sep}{y}')})\nprint(p.x {op} p.y)"
        expect = x + y if op == "+" else x * y
        other = x * y if op == "+" else x + y
        distractors = _nums([f"{x}{y}", TYPE_ERR, other, f"{x}{sep}{y}"], expect, rng)
        why = (
            f"A `@classmethod` receives the class itself as `cls`, so `Point.from_text(...)` works "
            f"without an object. It splits the text and returns `cls({x}, {y})`, a new `Point`, so "
            f"`p.x {op} p.y` is {expect}."
        )
    else:
        cls, attr, meth = rng.choice(
            [("Game", "level", "next_level"), ("Shop", "discount", "raise_discount"), ("Club", "fee", "raise_fee")]
        )
        start, step = rng.randint(1, 5), rng.randint(1, 3)
        klass = _cls(
            cls, _attrs((attr, start)), _meth(f"{meth}(cls)", f"cls.{attr} += {step}", deco="classmethod")
        )
        new = start + step
        main = f"a = {cls}()\nb = {cls}()\na.{meth}()\nprint(a.{attr}, b.{attr}, {cls}.{attr})"
        expect = f"{new} {new} {new}"
        distractors = [f"{new} {start} {start}", f"{new} {start} {new}", f"{start} {start} {new}", TYPE_ERR]
        why = (
            f"Even when called through `a`, a `@classmethod` receives the CLASS as `cls`, so "
            f"`cls.{attr} += {step}` changes the shared class attribute to {new}, which every "
            f"object sees."
        )
    code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


_CHAIN_OPS = [("add", "+=", "+"), ("times", "*=", "*"), ("minus", "-=", "-")]


@generator(TOPIC, MEDIUM)
def gen_method_chaining(rng: random.Random) -> Question:
    """Methods that ``return self`` can be chained; one that returns ``None`` breaks the chain."""
    ops = rng.sample(_CHAIN_OPS, 2)
    cls = rng.choice(["Calc", "Number", "Tally"])
    broken = rng.random() < 0.35
    broken_idx = rng.randrange(2)
    methods = []
    for i, (name, aug, _) in enumerate(ops):
        body = [f"self.value {aug} n"]
        if not (broken and i == broken_idx):
            body.append("return self")
        methods.append(_meth(f"{name}(self, n)", *body))
    klass = _cls(cls, _init("value"), *methods)
    start = rng.randint(2, 6)
    seq = [rng.choice(ops) for _ in range(2)]
    if seq[0] == seq[1]:
        seq = [ops[0], ops[1]] if rng.random() < 0.5 else [ops[1], ops[0]]
    seq.insert(rng.randrange(3), rng.choice(ops))
    nums = [rng.randint(2, 5) for _ in seq]
    chain = "".join(f".{name}({n})" for (name, _, _), n in zip(seq, nums))
    main = f"print({cls}({start}){chain}.value)"
    value, steps = start, []
    for (name, _, op), n in zip(seq, nums):
        steps.append(f"{op} {n}")
        value = eval(f"{value} {op} {n}")  # noqa: S307 - our own arithmetic
    rev = start
    for (name, _, op), n in reversed(list(zip(seq, nums))):
        rev = eval(f"{rev} {op} {n}")  # noqa: S307
    no_last = start
    for (name, _, op), n in list(zip(seq, nums))[:-1]:
        no_last = eval(f"{no_last} {op} {n}")  # noqa: S307
    bad_name = ops[broken_idx][0]
    breaks = broken and any(name == bad_name for (name, _, _) in seq)
    if breaks:
        expect = ATTR_ERR
        distractors = [value, TYPE_ERR, start, "None"]
        why = (
            f"`{bad_name}` changes `self.value` but has no `return self`, so it returns `None`. "
            f"The next step in the chain is then looked up on `None`, which raises `AttributeError`."
        )
    else:
        expect = value
        distractors = _nums([rev, ATTR_ERR, no_last, start], value, rng)
        why = (
            f"Each method updates `self.value` and returns `self`, so the next call in the chain "
            f"acts on the same object, left to right: {start} " + " then ".join(steps) + f" gives {value}."
        )
    code = _prog(klass, main)
    return _output(code, MEDIUM, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


# ==========================================================================
# HARD
# ==========================================================================

# class, list attribute, method, items, (object names)
_SHARED = [
    ("Dog", "tricks", "learn", ["sit", "roll", "beg", "spin"], ("rex", "fido")),
    ("Student", "courses", "enroll", ["math", "art", "music", "chess"], ("ava", "ben")),
    ("Hero", "items", "pick_up", ["sword", "map", "key", "rope"], ("knight", "rogue")),
    ("Robot", "logs", "record", ["start", "move", "scan", "stop"], ("r1", "r2")),
]


@generator(TOPIC, HARD)
def gen_shared_mutable_class_attr(rng: random.Random) -> Question:
    """A list stored as a class attribute is ONE list shared by every instance."""
    cls, attr, meth, pool, (o1, o2) = rng.choice(_SHARED)
    t1, t2, t3 = rng.sample(pool, 3)
    method = _meth(f"{meth}(self, item)", f"self.{attr}.append(item)")
    make = f"{o1} = {cls}()\n{o2} = {cls}()"
    shape = rng.choice(["shared", "shared", "fixed", "rebind", "int_vs_list"])
    if shape in ("shared", "fixed"):
        if shape == "shared":
            klass = _cls(cls, _attrs((attr, "[]")), method)
        else:
            klass = _cls(cls, _init(extra=[f"self.{attr} = []"]), method)
        who = rng.choice([o1, o2])
        main = f"{make}\n{o1}.{meth}({_q(t1)})\n{o2}.{meth}({_q(t2)})\nprint({who}.{attr})"
        mine = [t1] if who == o1 else [t2]
        both = [t1, t2]
        if shape == "shared":
            expect = repr(both)
            distractors = [repr(mine), repr([t2] if who == o1 else [t1]), "[]", f"{[t1]} {[t2]}", repr([t2, t1])]
            why = (
                f"`{attr} = []` in the class body creates ONE list stored on the class. Neither "
                f"object has its own `{attr}`, so `self.{attr}.append(...)` mutates that shared "
                f"list for both: {both}."
            )
        else:
            expect = repr(mine)
            distractors = [repr(both), "[]", repr([t2] if who == o1 else [t1]), repr([t2, t1])]
            why = (
                f"`self.{attr} = []` runs inside `__init__`, so every object gets its own new "
                f"list. `{who}` only ever appended to its own list: {mine}."
            )
    elif shape == "rebind":
        klass = _cls(cls, _attrs((attr, "[]")), method)
        main = (
            f"{make}\n{o2}.{attr} = [{_q(t1)}]\n{o1}.{meth}({_q(t2)})\n{o2}.{meth}({_q(t3)})\n"
            f"print({o1}.{attr}, {o2}.{attr})"
        )
        expect = f"{[t2]} {[t1, t3]}"
        distractors = [
            f"{[t1, t2, t3]} {[t1, t2, t3]}",
            f"{[t2, t3]} {[t1]}",
            f"{[t2, t3]} {[t1, t3]}",
            f"{[t2]} {[t3]}",
        ]
        why = (
            f"`{o2}.{attr} = [...]` is an ASSIGNMENT, so it creates a separate list on `{o2}` "
            f"alone. After that, `{o2}` appends to its own list, while `{o1}` still appends to the "
            f"shared class list."
        )
    else:
        klass = _cls(
            cls,
            _attrs(("count", 0), (attr, "[]")),
            _meth(f"{meth}(self, item)", "self.count += 1", f"self.{attr}.append(item)"),
        )
        main = f"{make}\n{o1}.{meth}({_q(t1)})\n{o2}.{meth}({_q(t2)})\nprint({o1}.count, {o1}.{attr})"
        expect = f"1 {[t1, t2]}"
        distractors = [f"2 {[t1, t2]}", f"1 {[t1]}", f"2 {[t1]}", f"0 {[t1, t2]}"]
        why = (
            f"`self.count += 1` reads the class's 0 and then ASSIGNS 1 to a new attribute on each "
            f"object, so each count is separate. `self.{attr}.append(...)` never assigns; it "
            f"mutates the one list stored on the class, so both items land in it."
        )
    code = _prog(klass, main)
    return _output(code, HARD, distractors, why, rng, expect=expect)


# (first parent, shared attr value, ...) themes for class-attribute MRO lookups
_MRO_ATTR = [
    (("Cat", "meow", "legs", 4), ("Bird", "tweet", "wings", 2), "Griffin", "sound"),
    (("Horse", "neigh", "legs", 4), ("Eagle", "screech", "wings", 2), "Pegasus", "sound"),
    (("Fish", "sea", "fins", 2), ("Human", "land", "arms", 2), "Mermaid", "home"),
    (("Boat", "sail", "masts", 2), ("Plane", "fly", "engines", 4), "Seaplane", "move"),
]

_MRO_SELF = [
    ("Swimmer", "Flyer", "Duck", "speed", (2, 9), (10, 30), "race", "self.speed * 2"),
    ("Walker", "Runner", "Athlete", "pace", (2, 6), (8, 15), "lap", "self.pace + 10"),
    ("Saver", "Spender", "Wallet", "rate", (1, 5), (6, 12), "yearly", "self.rate * 12"),
]


@generator(TOPIC, HARD)
def gen_multiple_inheritance(rng: random.Random) -> Question:
    """With several parents, Python searches them left to right (the MRO)."""
    if rng.random() < 0.55:
        (p1, s1, u1, n1), (p2, s2, u2, n2), child, shared = rng.choice(_MRO_ATTR)
        # The first-listed parent only has the shared attribute; the other also has its own one.
        if rng.random() < 0.5:
            (p1, s1, u1, n1), (p2, s2, u2, n2) = (p2, s2, u2, n2), (p1, s1, u1, n1)
        firstc = _cls(p1, _attrs((shared, _q(s1))))
        secondc = _cls(p2, _attrs((shared, _q(s2)), (u2, n2)))
        order = [p1, p2] if rng.random() < 0.5 else [p2, p1]
        winner = s1 if order[0] == p1 else s2
        loser = s2 if winner == s1 else s1
        childc = _cls(child, base=", ".join(order))
        main = f"print({child}.{shared}, {child}.{u2})"
        expect = f"{winner} {n2}"
        distractors = [f"{loser} {n2}", ATTR_ERR, f"{winner} None", f"{winner}{loser} {n2}"]
        why = (
            f"Python searches `{child}`, then its parents in the order listed: `{order[0]}`, then "
            f"`{order[1]}`. `{shared}` is found first in `{order[0]}` ({winner}); `{u2}` exists "
            f"only in `{p2}`, so the search continues there and finds {n2}."
        )
        code = _prog(firstc, secondc, childc, main)
    else:
        p1, p2, child, attr, r1, r2, meth, body = rng.choice(_MRO_SELF)
        a1, a2 = rng.randint(*r1), rng.randint(*r2)
        order = [p1, p2] if rng.random() < 0.5 else [p2, p1]
        vals = {p1: a1, p2: a2}
        win, lose = vals[order[0]], vals[order[1]]

        def calc(n: int) -> int:
            return eval(body.replace(f"self.{attr}", str(n)))  # noqa: S307 - our own arithmetic

        firstc = _cls(p1, _attrs((attr, a1)))
        secondc = _cls(p2, _attrs((attr, a2)))
        childc = _cls(child, _meth(f"{meth}(self)", f"return {body}"), base=", ".join(order))
        main = f"print({child}().{meth}())"
        expect = calc(win)
        distractors = _nums([calc(lose), ATTR_ERR, calc(win + lose), TYPE_ERR], expect, rng)
        why = (
            f"`self.{attr}` is looked up along the MRO: `{child}` → `{order[0]}` → `{order[1]}`. "
            f"Parents are tried left to right as written in `class {child}({', '.join(order)})`, "
            f"so `{order[0]}`'s value {win} is used: `{body}` = {expect}."
        )
        code = _prog(firstc, secondc, childc, main)
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


# parent, child, hook method, parent hook value, child hook value, public method, prefix
_DISPATCH = [
    ("Animal", "Cow", "sound", "...", "moo", "speak", "It says "),
    ("Shape", "Square", "name", "shape", "square", "describe", "I am a "),
    ("Employee", "Intern", "title", "staff", "intern", "badge", "Badge: "),
    ("Greeter", "Pirate", "hello", "hello", "ahoy", "greet", "Captain says "),
]


@generator(TOPIC, HARD)
def gen_self_dispatch(rng: random.Random) -> Question:
    """A parent method calling ``self.method()`` runs the CHILD's override."""
    shape = rng.choice(["template", "template", "class_attr", "super_hook", "init_hook"])
    if shape == "template":
        parent, child, hook, pv, cv, pub, prefix = rng.choice(_DISPATCH)
        pclass = _cls(
            parent, _meth(f"{hook}(self)", f"return {_q(pv)}"), _meth(f"{pub}(self)", f"return {_q(prefix)} + self.{hook}()")
        )
        cclass = _cls(child, _meth(f"{hook}(self)", f"return {_q(cv)}"), base=parent)
        main = f"print({child}().{pub}())"
        expect = prefix + cv
        distractors = [prefix + pv, cv, ATTR_ERR, prefix + pv + cv]
        why = (
            f"`{pub}` is inherited from `{parent}`, but inside it `self` is the `{child}` object. "
            f"So `self.{hook}()` finds `{child}`'s override first and returns {_q(cv)}, giving {expect}."
        )
        code = _prog(pclass, cclass, main)
    elif shape == "class_attr":
        parent, child, attr, pval, cval = rng.choice(
            [("Shape", "Square", "sides", 0, 4), ("Vehicle", "Bike", "wheels", 4, 2), ("Animal", "Spider", "legs", 4, 8)]
        )
        via_self = rng.random() < 0.6
        ref = f"self.{attr}" if via_self else f"{parent}.{attr}"
        pclass = _cls(parent, _attrs((attr, pval)), _meth("describe(self)", f'return f"{{{ref}}} {attr}"'))
        cclass = _cls(child, _attrs((attr, cval)), base=parent)
        main = f"for thing in [{parent}(), {child}()]:\n    print(thing.describe())"
        right_self = f"{pval} {attr}\n{cval} {attr}"
        right_cls = f"{pval} {attr}\n{pval} {attr}"
        if via_self:
            expect = right_self
            distractors = [right_cls, f"{cval} {attr}\n{cval} {attr}", ATTR_ERR, f"{cval} {attr}\n{pval} {attr}"]
            why = (
                f"`self.{attr}` is looked up on the actual object: for the `{child}` it finds the "
                f"child's own class attribute {cval} before the parent's {pval}."
            )
        else:
            expect = right_cls
            distractors = [right_self, f"{cval} {attr}\n{cval} {attr}", ATTR_ERR, f"{cval} {attr}\n{pval} {attr}"]
            why = (
                f"The method reads `{parent}.{attr}`, naming the parent class explicitly, so it "
                f"always gets {pval}, even for a `{child}`. Only `self.{attr}` would find the "
                f"child's {cval}."
            )
        code = _prog(pclass, cclass, main)
    elif shape == "super_hook":
        parent, child, hook, base, suffix, pub, prefix = rng.choice(
            [("Coffee", "Latte", "recipe", "coffee", " + milk", "order", "Order: "),
             ("Pizza", "Deluxe", "toppings", "cheese", " + olives", "describe", "Pizza with "),
             ("Plan", "ProPlan", "features", "chat", " + video", "summary", "Includes ")]
        )
        pclass = _cls(
            parent, _meth(f"{hook}(self)", f"return {_q(base)}"), _meth(f"{pub}(self)", f"return {_q(prefix)} + self.{hook}()")
        )
        cclass = _cls(child, _meth(f"{hook}(self)", f"return super().{hook}() + {_q(suffix)}"), base=parent)
        main = f"print({child}().{pub}())"
        expect = prefix + base + suffix
        bare = suffix.replace(" + ", "")
        distractors = [prefix + base, base + suffix, prefix + bare, ATTR_ERR]
        why = (
            f"`{pub}` comes from `{parent}`, but `self.{hook}()` dispatches to `{child}.{hook}` "
            f"because `self` is a `{child}`. That override calls `super().{hook}()` ({_q(base)}) "
            f"and appends {_q(suffix)}."
        )
        code = _prog(pclass, cclass, main)
    else:
        parent, child, attr, hook, pval, cval = rng.choice(
            [("Widget", "BigWidget", "size", "default_size", 1, 10),
             ("Account", "Premium", "limit", "default_limit", 100, 500),
             ("Player", "Boss", "health", "start_health", 10, 50)]
        )
        pval, cval = pval * rng.randint(1, 3), cval * rng.randint(1, 3)
        pclass = _cls(
            parent, _meth("__init__(self)", f"self.{attr} = self.{hook}()"), _meth(f"{hook}(self)", f"return {pval}")
        )
        cclass = _cls(child, _meth(f"{hook}(self)", f"return {cval}"), base=parent)
        main = f"print({parent}().{attr}, {child}().{attr})"
        expect = f"{pval} {cval}"
        distractors = [f"{pval} {pval}", ATTR_ERR, f"{cval} {cval}", TYPE_ERR]
        why = (
            f"`{child}` has no `__init__`, so it inherits `{parent}`'s. That `__init__` calls "
            f"`self.{hook}()`, and since `self` is a `{child}`, the child's override runs, "
            f"returning {cval}."
        )
        code = _prog(pclass, cclass, main)
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


@generator(TOPIC, HARD)
def gen_super_order(rng: random.Random) -> Question:
    """WHERE ``super()`` is called decides which values win and in what order things happen."""
    shape = rng.choice(["init_overwrite", "init_overwrite", "transform", "print_order"])
    if shape == "init_overwrite":
        parent, child, a1, a2, (p1, p2), c1 = rng.choice(
            [("Vehicle", "Bike", "speed", "wheels", (10, 4), 25),
             ("Character", "Knight", "health", "armor", (50, 1), 80),
             ("Phone", "Tablet", "screen", "cameras", (6, 2), 11)]
        )
        child_first = rng.random() < 0.6
        own = f"self.{a1} = {c1}"
        body = [own, "super().__init__()"] if child_first else ["super().__init__()", own]
        pclass = _cls(parent, _init(extra=[f"self.{a1} = {p1}", f"self.{a2} = {p2}"]))
        cclass = _cls(child, _meth("__init__(self)", *body), base=parent)
        v = child.lower()
        main = f"{v} = {child}()\nprint({v}.{a1}, {v}.{a2})"
        if child_first:
            expect = f"{p1} {p2}"
            distractors = [f"{c1} {p2}", ATTR_ERR, f"{c1} None", f"{p1} None"]
            why = (
                f"`{child}.__init__` sets `{a1}` to {c1} FIRST, then `super().__init__()` runs the "
                f"parent's `__init__`, which overwrites `{a1}` with {p1} and sets `{a2}` to {p2}."
            )
        else:
            expect = f"{c1} {p2}"
            distractors = [f"{p1} {p2}", ATTR_ERR, f"{c1} None", f"{p1} None"]
            why = (
                f"`super().__init__()` runs first, setting `{a1}` = {p1} and `{a2}` = {p2}; then "
                f"the child replaces `{a1}` with {c1}. The last assignment wins."
            )
        code = _prog(pclass, cclass, main)
    elif shape == "transform":
        m, add, k, n = rng.randint(2, 4), rng.randint(1, 3), rng.randint(2, 9), rng.randint(2, 6)
        parent, child, meth = rng.choice([("Base", "Child", "scale"), ("Pricer", "Discount", "price"),
                                          ("Scorer", "Bonus", "score")])
        pclass = _cls(parent, _meth(f"{meth}(self, n)", f"return n * {m}"))
        cclass = _cls(child, _meth(f"{meth}(self, n)", f"return super().{meth}(n + {add}) + {k}"), base=parent)
        main = f"print({child}().{meth}({n}), {parent}().{meth}({n}))"
        right = (n + add) * m + k
        expect = f"{right} {n * m}"
        distractors = [
            f"{n * m + add + k} {n * m}",
            f"{(n + add + k) * m} {n * m}",
            f"{n + add + k} {n * m}",
            f"{right} {right}",
            f"{n * m + k} {n * m}",
        ]
        why = (
            f"`super().{meth}(n + {add})` passes {n} + {add} = {n + add} to the parent, which "
            f"returns {n + add} * {m} = {(n + add) * m}; the child then adds {k} to get {right}. "
            f"The `{parent}` object just returns {n} * {m} = {n * m}."
        )
        code = _prog(pclass, cclass, main)
    else:
        parent, child = rng.choice([("Base", "Child"), ("Vehicle", "Car"), ("Device", "Phone")])
        before = rng.random() < 0.5
        lines = [f'print("{child} start")', "super().__init__()", f'print("{child} end")']
        if not before:
            lines = [f'print("{child} start")', f'print("{child} end")', "super().__init__()"]
        pclass = _cls(parent, _meth("__init__(self)", f'print("{parent} init")'))
        cclass = _cls(child, _meth("__init__(self)", *lines), base=parent)
        main = f"obj = {child}()"
        s, e, p = f"{child} start", f"{child} end", f"{parent} init"
        options = [f"{s}\n{p}\n{e}", f"{p}\n{s}\n{e}", f"{s}\n{e}\n{p}", f"{s}\n{e}", f"{p}\n{s}\n{e}\n{p}"]
        expect = options[0] if before else options[2]
        distractors = options
        why = (
            f"Creating a `{child}` runs only `{child}.__init__`; the parent's `__init__` runs exactly "
            f"when `super().__init__()` is reached, so its line is printed at that point."
        )
        code = _prog(pclass, cclass, main)
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


@generator(TOPIC, HARD)
def gen_repr_in_containers(rng: random.Random) -> Question:
    """``print(obj)`` uses ``__str__`` but a printed list shows each item's ``__repr__``."""
    kind = rng.choice(["point", "money", "temp"])
    if kind == "point":
        cls = "Point"
        init = _init("x", "y")
        s_body, r_body = 'return f"({self.x}, {self.y})"', 'return f"Point({self.x}, {self.y})"'
        objs = [tuple(rng.sample(range(1, 10), 2)) for _ in range(2)]
        ctor = [f"Point({a}, {b})" for a, b in objs]
        strs = [f"({a}, {b})" for a, b in objs]
        reprs = ctor
    elif kind == "money":
        cls = "Money"
        init = _init("amount")
        s_body, r_body = 'return f"${self.amount}"', 'return f"Money({self.amount})"'
        objs = rng.sample(range(2, 50), 2)
        ctor = [f"Money({a})" for a in objs]
        strs = [f"${a}" for a in objs]
        reprs = ctor
    else:
        cls = "Temp"
        init = _init("degrees")
        s_body, r_body = 'return f"{self.degrees} degrees"', 'return f"Temp({self.degrees})"'
        objs = rng.sample(range(-5, 35), 2)
        ctor = [f"Temp({a})" for a in objs]
        strs = [f"{a} degrees" for a in objs]
        reprs = ctor
    str_m, repr_m = _meth("__str__(self)", s_body), _meth("__repr__(self)", r_body)
    shape = rng.choice(["list", "single_and_list", "single_and_list", "dict", "repr_only"])
    if shape == "repr_only":
        klass = _cls(cls, init, repr_m)
        main = f"x = {ctor[0]}\nprint(x, [x])"
        expect = f"{reprs[0]} [{reprs[0]}]"
        distractors = [f"{strs[0]} [{reprs[0]}]", f"{strs[0]} [{strs[0]}]", f"{reprs[0]} [x]", f"x [{reprs[0]}]"]
        why = (
            f"This class defines only `__repr__`. When there is no `__str__`, `print` falls back to "
            f"`__repr__`, so both the object and the list show {reprs[0]}."
        )
    else:
        klass = _cls(cls, init, str_m, repr_m)
        if shape == "list":
            main = f"items = [{ctor[0]}, {ctor[1]}]\nprint(items)"
            expect = f"[{reprs[0]}, {reprs[1]}]"
            distractors = [f"[{strs[0]}, {strs[1]}]", f"{strs[0]} {strs[1]}", f"[{strs[0]}, {reprs[1]}]",
                           f"{reprs[0]} {reprs[1]}"]
            why = (
                "Printing a list shows the list's own text, which is built from each element's "
                f"`__repr__`, not `__str__`. So the items appear as {reprs[0]} and {reprs[1]}."
            )
        elif shape == "single_and_list":
            main = f"items = [{ctor[0]}, {ctor[1]}]\nprint(items[0], items)"
            expect = f"{strs[0]} [{reprs[0]}, {reprs[1]}]"
            distractors = [
                f"{strs[0]} [{strs[0]}, {strs[1]}]",
                f"{reprs[0]} [{reprs[0]}, {reprs[1]}]",
                f"{reprs[0]} [{strs[0]}, {strs[1]}]",
                f"{strs[0]} {strs[0]} {strs[1]}",
            ]
            why = (
                f"`print(items[0])` prints the object itself, so it uses `__str__`: {strs[0]}. "
                f"`print(items)` prints a list, and a list shows its elements with `__repr__`."
            )
        else:
            key = rng.choice(["best", "first", "home", "goal"])
            main = f"data = {{{_q(key)}: {ctor[0]}}}\nprint(data)"
            expect = f"{{'{key}': {reprs[0]}}}"
            distractors = [f"{{'{key}': {strs[0]}}}", f"{{{key}: {strs[0]}}}", f"{{{key}: {reprs[0]}}}", f"{key}: {strs[0]}"]
            why = (
                "A dict, like a list, shows its contents with `repr()`: the key appears with its "
                f"quotes and the value via `__repr__`, giving {reprs[0]} rather than {strs[0]}."
            )
    code = _prog(klass, main)
    return _output(code, HARD, distractors, why, rng, expect=expect)


@generator(TOPIC, HARD)
def gen_dunder_semantics(rng: random.Random) -> Question:
    """Subtle dunder behaviour: ``__add__`` that mutates, ``in`` uses ``__eq__``, sorting uses ``__lt__``."""
    shape = rng.choice(["add_mutates", "add_mutates", "contains", "contains", "sorted"])
    if shape == "add_mutates":
        cls = rng.choice(["Counter", "Total", "Stack"])
        a, b = rng.sample(range(2, 15), 2)
        mutating = rng.random() < 0.7
        if mutating:
            add = _meth("__add__(self, other)", "self.value += other.value", "return self")
        else:
            add = _meth("__add__(self, other)", f"return {cls}(self.value + other.value)")
        klass = _cls(cls, _init("value"), add)
        main = f"a = {cls}({a})\nb = {cls}({b})\nc = a + b\nprint(a.value, c.value)"
        if mutating:
            expect = f"{a + b} {a + b}"
            distractors = [f"{a} {a + b}", f"{a + b} {a}", f"{a} {a}", TYPE_ERR]
            why = (
                f"This `__add__` changes `self` (that is, `a`) and returns `self`, so `c = a + b` "
                f"makes `c` the very same object as `a`. Both show {a} + {b} = {a + b}."
            )
        else:
            expect = f"{a} {a + b}"
            distractors = [f"{a + b} {a + b}", f"{a + b} {a}", f"{a} {a}", TYPE_ERR]
            why = (
                f"This `__add__` builds and returns a NEW `{cls}`, leaving `a` untouched at {a}; "
                f"`c` is the new object holding {a + b}."
            )
    elif shape == "contains":
        cls, attr = rng.choice([("Card", "rank"), ("Coin", "value"), ("Tile", "number")])
        x, y = rng.sample(range(2, 10), 2)
        has_eq = rng.random() < 0.6
        members = [_init(attr)]
        if has_eq:
            members.append(_meth("__eq__(self, other)", f"return self.{attr} == other.{attr}"))
        klass = _cls(cls, *members)
        use_index = rng.random() < 0.35
        hand = f"hand = [{cls}({x}), {cls}({y}), {cls}({x})]"
        if use_index:
            main = f"{hand}\nprint({cls}({y}) in hand, hand.index({cls}({y})))"
            if has_eq:
                expect = "True 1"
                distractors = ["False 1", "True 2", VALUE_ERR, "False -1"]
            else:
                expect = VALUE_ERR
                distractors = ["True 1", "False 1", "False -1", TYPE_ERR]
        else:
            main = f"{hand}\nprint({cls}({y}) in hand, hand.count({cls}({x})))"
            if has_eq:
                expect = "True 2"
                distractors = ["False 0", "True 1", "False 2", TYPE_ERR]
            else:
                expect = "False 0"
                distractors = ["True 2", "True 0", "False 2", TYPE_ERR]
        if has_eq:
            why = (
                f"`in`, `count` and `index` compare items with `==`, which calls `__eq__`. Since "
                f"`__eq__` compares `{attr}`, a new `{cls}({y})` matches the one already in the list."
            )
        else:
            why = (
                f"`in`, `count` and `index` compare with `==`. Without `__eq__`, `==` is only True "
                f"for the SAME object, and `{cls}({y})` creates a new one, so nothing matches"
                + (" and `index` raises `ValueError`." if use_index else ".")
            )
    else:
        names = rng.sample(NAMES, 3)
        scores = rng.sample(range(1, 30), 3)
        cls = rng.choice(["Player", "Runner", "Racer"])
        klass = _cls(cls, _init("name", "score"), _meth("__lt__(self, other)", "return self.score < other.score"))
        team = ", ".join(f"{cls}({_q(n)}, {s})" for n, s in zip(names, scores))
        by_score = [n for _, n in sorted(zip(scores, names))]
        if rng.random() < 0.6:
            main = f"team = [{team}]\nprint([p.name for p in sorted(team)])"
            expect = repr(by_score)
            distractors = [repr(sorted(names)), repr(names), repr(by_score[::-1]), TYPE_ERR, repr(sorted(names)[::-1])]
            why = (
                f"`sorted` orders items using `<`, which calls `__lt__`, and this `__lt__` compares "
                f"`score`. So the players come out from lowest to highest score: {by_score}."
            )
        else:
            main = f"team = [{team}]\nprint(min(team).name, max(team).name)"
            expect = f"{by_score[0]} {by_score[-1]}"
            distractors = [f"{by_score[-1]} {by_score[0]}", f"{sorted(names)[0]} {sorted(names)[-1]}",
                           f"{names[0]} {names[-1]}", TYPE_ERR, f"{by_score[0]} {by_score[1]}",
                           f"{by_score[1]} {by_score[-1]}"]
            why = (
                f"`min` and `max` compare the objects with `<`/`>`, which use `__lt__`, so they "
                f"pick the lowest and highest `score`: {by_score[0]} and {by_score[-1]}."
            )
    code = _prog(klass, main)
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


@generator(TOPIC, HARD)
def gen_identity_traps(rng: random.Random) -> Question:
    """Names, list slots and parameters hold REFERENCES to objects, not copies."""
    shape = rng.choice(["multiply_list", "multiply_list", "rebind_param", "rebind_name", "stored_list"])
    if shape == "multiply_list":
        cls, attr = rng.choice([("Box", "items"), ("Jar", "coins"), ("Cup", "sugar")])
        klass = _cls(cls, _init(extra=[f"self.{attr} = 0"]))
        a, b = rng.randint(1, 5), rng.randint(1, 5)
        i, j = rng.sample(range(3), 2)
        shared = rng.random() < 0.65
        make = f"[{cls}()] * 3" if shared else f"[{cls}() for _ in range(3)]"
        main = (
            f"boxes = {make}\nboxes[{i}].{attr} += {a}\nboxes[{j}].{attr} += {b}\n"
            f"print([box.{attr} for box in boxes])"
        )
        separate = [0, 0, 0]
        separate[i] += a
        separate[j] += b
        together = [a + b] * 3
        if shared:
            expect = repr(together)
            distractors = [repr(separate), repr([a] * 3), repr([b] * 3), TYPE_ERR]
            why = (
                f"`[{cls}()] * 3` creates ONE object and a list holding three references to it. "
                f"Every slot is the same `{cls}`, so both changes add up: {a} + {b} = {a + b} everywhere."
            )
        else:
            expect = repr(separate)
            distractors = [repr(together), repr([a] * 3), repr([b] * 3), TYPE_ERR]
            why = (
                "The comprehension calls `" + cls + "()` three times, so the list holds three "
                "separate objects and each change affects only its own slot."
            )
        code = _prog(klass, main)
    elif shape == "rebind_param":
        cls, attr = rng.choice([("Player", "score"), ("Account", "balance"), ("Plant", "height")])
        start, add, add2 = rng.randint(2, 9), rng.randint(5, 20), rng.randint(1, 4)
        klass = _cls(cls, _init(attr))
        fname = rng.choice(["update", "refresh", "tweak"])
        func = f"def {fname}(obj):\n    obj.{attr} += {add}\n    obj = {cls}(0)\n    obj.{attr} += {add2}"
        main = f"x = {cls}({start})\n{fname}(x)\nprint(x.{attr})"
        expect = start + add
        distractors = _nums([add2, start + add + add2, start, 0], expect, rng)
        why = (
            f"`obj.{attr} += {add}` changes the object `x` refers to, giving {start + add}. Then "
            f"`obj = {cls}(0)` only makes the local name `obj` point to a NEW object; `x` is "
            f"untouched by the later change."
        )
        code = _prog(klass, func, main)
    elif shape == "rebind_name":
        cls, attr = rng.choice([("Player", "score"), ("Robot", "power"), ("Plant", "height")])
        klass = _cls(cls, _init(attr))
        s1, s2, d = rng.randint(2, 9), rng.randint(10, 20), rng.randint(1, 4)
        main = (
            f"a = {cls}({s1})\nb = a\nb.{attr} += {d}\na = {cls}({s2})\na.{attr} += {d}\n"
            f"print(a.{attr}, b.{attr})"
        )
        expect = f"{s2 + d} {s1 + d}"
        distractors = [f"{s2 + d} {s2 + d}", f"{s2 + d} {s1}", f"{s2 + 2 * d} {s1 + d}", f"{s1 + d} {s1 + d}"]
        why = (
            f"`b = a` makes both names refer to the first object, which `b.{attr} += {d}` changes to "
            f"{s1 + d}. Then `a = {cls}({s2})` just points `a` at a NEW object; `b` still refers to "
            f"the first one."
        )
        code = _prog(klass, main)
    else:
        cls, attr, meth = rng.choice([("Stack", "items", "pop"), ("Queue", "items", "pop")])
        nums = rng.sample(range(1, 10), 3)
        klass = _cls(cls, _init(attr), _meth(f"remove(self)", f"return self.{attr}.{meth}()"))
        var = rng.choice(["nums", "values", "data"])
        main = f"{var} = {nums}\ns = {cls}({var})\ns.remove()\nprint(len({var}), s.remove())"
        expect = f"2 {nums[1]}"
        distractors = [f"3 {nums[1]}", f"3 {nums[2]}", f"2 {nums[2]}", f"3 {nums[0]}"]
        why = (
            f"`self.{attr} = {attr}` stores a reference to the SAME list as `{var}`, not a copy. "
            f"The first `remove()` pops {nums[2]} from that shared list, so `len({var})` is 2, and "
            f"the next pop returns {nums[1]}."
        )
        code = _prog(klass, main)
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR, expect=expect)


@generator(TOPIC, HARD)
def gen_trace_object_state(rng: random.Random) -> Question:
    """Trace an object's state through a loop of method calls with a guard or links."""
    shape = rng.choice(["account", "account", "thermostat", "nodes"])
    if shape == "account":
        while True:
            start = rng.randrange(30, 80, 10)
            amounts = [rng.randrange(10, 50, 5) for _ in range(rng.randint(3, 4))]
            bal, ok = start, []
            for a in amounts:
                ok.append(a <= bal)
                if a <= bal:
                    bal -= a
            first_fail = ok.index(False) if False in ok else -1
            if 0 < first_fail < len(amounts) - 1 and any(ok[first_fail + 1:]):
                break
        klass = _cls(
            "Account",
            _init("balance"),
            _meth("withdraw(self, amount)", "if amount <= self.balance:", "    self.balance -= amount"),
        )
        main = f"acct = Account({start})\nfor amount in {amounts}:\n    acct.withdraw(amount)\nprint(acct.balance)"
        expect = bal
        no_guard = start - sum(amounts)
        stop_early = start - sum(amounts[:first_fail])
        distractors = _nums([no_guard, stop_early, 0, bal + amounts[first_fail]], bal, rng)
        trace = []
        b = start
        for a, good in zip(amounts, ok):
            if good:
                trace.append(f"{b} - {a} = {b - a}")
                b -= a
            else:
                trace.append(f"{a} is skipped")
        why = (
            "Each withdrawal only happens if there is enough money; a refused one is skipped and "
            "the loop carries on: " + "; ".join(trace) + "."
        )
    elif shape == "thermostat":
        low, high = rng.choice([(15, 25), (16, 24), (18, 26)])
        start = rng.randint(low + 2, high - 2)
        while True:
            changes = [rng.choice([-1, 1]) * rng.randint(2, 7) for _ in range(4)]
            t, clamped, raw = start, False, start
            for c in changes:
                raw += c
                nt = max(low, min(high, t + c))
                if nt != t + c:
                    clamped = True
                t = nt
            if clamped and raw != t:
                break
        klass = _cls(
            "Thermostat",
            _init("temp"),
            _meth("adjust(self, change)", f"self.temp = max({low}, min({high}, self.temp + change))"),
        )
        main = f"t = Thermostat({start})\nfor change in {changes}:\n    t.adjust(change)\nprint(t.temp)"
        expect = t
        distractors = _nums([raw, high, low, max(low, min(high, raw))], t, rng)
        trace, cur = [], start
        for c in changes:
            cur = max(low, min(high, cur + c))
            trace.append(str(cur))
        why = (
            f"Every call clamps the new temperature into {low}..{high} BEFORE the next change is "
            f"applied, so the steps go {start} → " + " → ".join(trace) + f". Adding all the changes "
            f"first ({raw}) and clamping once would be wrong."
        )
    else:
        a, b, c, new = rng.sample(range(1, 10), 4)
        klass = _cls("Node", _meth("__init__(self, value, next_node=None)", "self.value = value", "self.next = next_node"))
        which = rng.choice(["mid", "tail"])
        target = "second" if which == "mid" else "third"
        main = (
            f"third = Node({c})\nsecond = Node({b}, third)\nfirst = Node({a}, second)\n"
            f"{target}.value = {new}\nprint(first.next.value + first.next.next.value)"
        )
        bb, cc = (new, c) if which == "mid" else (b, new)
        expect = bb + cc
        distractors = _nums([b + c, a + bb, a + b, ATTR_ERR], expect, rng)
        why = (
            f"`first.next` IS the object named `second`, and `first.next.next` IS `third` — they are "
            f"references, not copies. Changing `{target}.value` to {new} is therefore visible "
            f"through `first`: {bb} + {cc} = {expect}."
        )
    code = _prog(klass, main)
    return _output(code, HARD, distractors, why, rng, prompt=PRINT_OR_ERROR if shape == "nodes" else PRINT,
                   expect=expect)
