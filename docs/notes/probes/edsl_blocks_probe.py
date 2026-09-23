"""Blocks as classes: typed params, actions as methods, tables holding methods."""
from __future__ import annotations
from typing import Any, Callable, Generic, Literal, ParamSpec, TypeVar, Concatenate

W = TypeVar("W", bound=int)
P = ParamSpec("P")

class Bits(Generic[W]):
    def __sub__(self, other: Bits[W] | int) -> Bits[W]: ...
class Bool: ...
class Header:
    def is_valid(self) -> Bool: ...
class ipv4_t(Header):
    ttl: Bits[Literal[8]]
    dstAddr: Bits[Literal[32]]
class headers:
    ipv4: ipv4_t
class metadata:
    egress_port: Bits[Literal[9]]
    drop: Bool

class ActionCall: ...
class Action(Generic[P]):
    """What @action makes of a method: callable for direct calls and for
    entries/defaults, both checked against the declared parameters."""
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ActionCall: ...

def action(f: Callable[Concatenate[Any, P], None]) -> Action[P]: ...

class Table:
    def __init__(self, keys: list[Any], actions: list[Action[...]], default: ActionCall | None = None, size: int = 0) -> None: ...

class Control:
    hdr: headers
    meta: metadata
    def assign(self, target: Bits[W] | Bool, value: Bits[W] | Bool | int) -> None: ...
    def apply(self, t: Table) -> None: ...

def lpm(x: Bits[Any]) -> Any: ...

class MyIngress(Control):
    @action
    def drop(self) -> None:
        self.assign(self.meta.drop, True)

    @action
    def ipv4_forward(self, dstAddr: Bits[Literal[48]], port: Bits[Literal[9]]) -> None:
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl - 1)

    ipv4_lpm = Table(keys=[lpm(headers.ipv4.dstAddr)], actions=[ipv4_forward, drop], default=drop(), size=1024)
    bad_table = Table(keys=[], actions=[ipv4_forward], default=ipv4_forward(port=2))   # ERROR: missing dstAddr
    bad_table2 = Table(keys=[], actions=[ipv4_forward], default=ipv4_forward(1, 2, 3))  # ERROR: too many

    def body(self) -> None:
        self.apply(self.ipv4_lpm)
        self.drop()                       # a direct call, typed
        self.ipv4_forward(port=2)         # ERROR: missing dstAddr
        self.apply(self.ipv4_lpn)         # ERROR: typo
