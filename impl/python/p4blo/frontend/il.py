"""P4-SpecTec's IL as Python values, read from the `il-export` JSON.

The `il-export` command (tests/oracles/patches/0002-il-export.patch) prints
the values P4-SpecTec's own typing and instantiation relations produce,
structurally: every variant value names its syntax type and its
constructor. This module turns that JSON into small immutable Python
values so that the translator (`p4blo.frontend.spectec_il`) can match on
them without knowing the spec's grammar beyond the productions it
translates.

    JSON                                  Python
    true / false                          bool
    n (a natural number)                  int
    {"int": i}                            int
    {"text": s}                           str
    {"t": T, "c": C, "a": [...]}          Node(T, C, (...))
    {"t": T, "s": [[atom, v], ...]}       Record(T, (("ATOM", v), ...))
    {"tuple": [...]}                      tuple
    {"opt": v | null}                     Opt(v | None)
    [...]                                 list
    {"func": f}, {"extern": j}            Func(f), Extern(j)

`Node.t` is the value's syntax type (`typedExpressionIR`, `typeIR`, ...)
and `Node.c` its constructor with `%` for each argument, spaces as the
spec writes them: `BinE % % %` style mixfix notation, so `"% # %"` is a
typed expression and `"BIT <%>"` a `bit<N>` type. Nothing is normalized:
a value is exactly what the spec computed.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

__all__ = [
    "Export",
    "Extern",
    "Func",
    "ILError",
    "Node",
    "Opt",
    "Record",
    "Value",
    "loads",
    "render",
    "walk",
]


class ILError(Exception):
    """The export is not shaped as the translator expects."""


@dataclass(frozen=True, slots=True)
class Node:
    """A variant value: syntax type `t`, constructor `c`, arguments `a`."""

    t: str
    c: str
    a: tuple[Value, ...]

    def arg(self, i: int) -> Value:
        return self.a[i]

    def node(self, i: int) -> Node:
        v = self.a[i]
        if not isinstance(v, Node):
            raise ILError(f"{self.t} {self.c!r}: argument {i} is not a variant: {v!r}")
        return v

    def text(self, i: int) -> str:
        v = self.a[i]
        if not isinstance(v, str):
            raise ILError(f"{self.t} {self.c!r}: argument {i} is not text: {v!r}")
        return v

    def num(self, i: int) -> int:
        v = self.a[i]
        if not isinstance(v, int) or isinstance(v, bool):
            raise ILError(f"{self.t} {self.c!r}: argument {i} is not a number: {v!r}")
        return v

    def list(self, i: int) -> list[Value]:
        v = self.a[i]
        if not isinstance(v, list):
            raise ILError(f"{self.t} {self.c!r}: argument {i} is not a list: {v!r}")
        return v

    def nodes(self, i: int) -> list[Node]:
        out: list[Node] = []
        for v in self.list(i):
            if not isinstance(v, Node):
                raise ILError(f"{self.t} {self.c!r}: argument {i} holds a non-variant: {v!r}")
            out.append(v)
        return out

    def opt(self, i: int) -> Value | None:
        v = self.a[i]
        if not isinstance(v, Opt):
            raise ILError(f"{self.t} {self.c!r}: argument {i} is not an option: {v!r}")
        return v.value

    def is_(self, c: str) -> bool:
        return self.c == c

    def short(self) -> str:
        """A one-line rendering for error messages, truncated."""
        text = render(self)
        return text if len(text) <= 160 else text[:157] + "..."


@dataclass(frozen=True, slots=True)
class Record:
    """A struct value of the spec's own syntax (contexts, layers)."""

    t: str
    fields: tuple[tuple[str, Value], ...]

    def get(self, atom: str) -> Value:
        for name, value in self.fields:
            if name == atom:
                return value
        raise ILError(f"{self.t} has no field {atom}")


@dataclass(frozen=True, slots=True)
class Opt:
    value: Value | None


@dataclass(frozen=True, slots=True)
class Func:
    name: str


@dataclass(frozen=True, slots=True)
class Extern:
    json: Any


type Value = (
    bool | int | str | Node | Record | Opt | Func | Extern | tuple[Value, ...] | list[Value]
)


def _value(j: Any) -> Value:
    if isinstance(j, bool | int):
        return j
    if isinstance(j, list):
        return [_value(x) for x in j]
    if isinstance(j, dict):
        if "c" in j:
            return Node(j["t"], j["c"], tuple(_value(x) for x in j["a"]))
        if "s" in j:
            return Record(j["t"], tuple((k, _value(v)) for k, v in j["s"]))
        if "text" in j:
            return j["text"]
        if "int" in j:
            return int(j["int"])
        if "opt" in j:
            return Opt(None if j["opt"] is None else _value(j["opt"]))
        if "tuple" in j:
            return tuple(_value(x) for x in j["tuple"])
        if "func" in j:
            return Func(j["func"])
        if "extern" in j:
            return Extern(j["extern"])
    raise ILError(f"unrecognized IL JSON value: {str(j)[:120]}")


@dataclass(frozen=True)
class Export:
    """One `il-export` result: the typed program and the instantiation.

    `program` is the output of `Program_ok`, a `p4programIR` whose one
    argument lists every declaration in source order, the included
    `core.p4` and architecture files first. `global_layer` and `store` are
    the outputs of `Program_inst`: the global instantiation layer and the
    store of instantiated objects, keyed by object path.
    """

    program: Node
    global_layer: Record
    store: Node

    @property
    def declarations(self) -> list[Node]:
        return self.program.nodes(0)

    def objects(self) -> Iterator[tuple[tuple[str, ...], Node]]:
        """The store's objects with their paths, in the spec's order."""
        for pair in self.store.nodes(0):
            path = pair.list(0)
            yield tuple(str(p) for p in path), pair.node(1)


def loads(text: str) -> Export:
    """Parse the JSON `il-export` prints."""
    j = json.loads(text)
    if not isinstance(j, dict) or j.get("format") != "p4spectec-il-export/1":
        raise ILError("not an il-export document (format p4spectec-il-export/1)")
    program = _value(j["program"])
    global_layer = _value(j["global"])
    store = _value(j["store"])
    if not isinstance(program, Node) or not isinstance(store, Node):
        raise ILError("il-export: program and store must be variants")
    if not isinstance(global_layer, Record):
        raise ILError("il-export: the global layer must be a record")
    return Export(program, global_layer, store)


def walk(v: object) -> Iterator[Node]:
    """Every variant inside `v`, pre-order."""
    if isinstance(v, Node):
        yield v
        for x in v.a:
            yield from walk(x)
    elif isinstance(v, list | tuple):
        for x in v:
            yield from walk(x)
    elif isinstance(v, Opt) and v.value is not None:
        yield from walk(v.value)
    elif isinstance(v, Record):
        for _, x in v.fields:
            yield from walk(x)


def render(v: Value) -> str:
    """The spec's own notation for `v`, roughly: constructor with arguments."""
    if isinstance(v, Node):
        parts = v.c.split("%")
        out = parts[0]
        for i, rest in enumerate(parts[1:]):
            out += render(v.a[i]) if i < len(v.a) else "?"
            out += rest
        return out.strip() or v.t
    if isinstance(v, list | tuple):
        return "[" + ", ".join(render(x) for x in v) + "]"
    if isinstance(v, Opt):
        return "" if v.value is None else render(v.value)
    if isinstance(v, str):
        return v
    if isinstance(v, Record):
        return "{" + "; ".join(f"{k} {render(x)}" for k, x in v.fields) + "}"
    return str(v)
