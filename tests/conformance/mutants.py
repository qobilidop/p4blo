"""Deliberate faults in the Python interpreter that the corpus must catch.

    python -m tests.conformance.mutants [NAME ...]

Each mutant replaces one function of the reference interpreter in this
process only, then runs `check-python` over the tracked fixtures and
prints the fixtures that caught it. A mutant no fixture catches is a gap
in the corpus. `tests/test_conformance.py` requires every mutant here to be
caught; the README records which fixtures catch each one, and the Lean
mutant, which needs a rebuilt endpoint and is run by hand.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from p4blo import conformance
from p4blo.arch import switch
from p4blo.arch.externs import counter
from p4blo.interp import expr, tables
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb


@dataclass(frozen=True)
class Mutant:
    description: str
    owner: object
    attribute: str
    # The replacement, given the original.
    make: Callable[[Any], Callable[..., Any]]


def _sub_off_by_one(original: Callable[..., Value]) -> Callable[..., Value]:
    def bits_binary(op: int, x: Bits, y: Bits) -> Value:
        if op == pb.BINARY_OP_SUB:
            return Bits.wrap(x.width, x.value - y.value - 1)
        return original(op, x, y)

    return bits_binary


def _count_twice(original: Callable[..., object]) -> Callable[..., object]:
    def call(self: counter.Counter, method: str, args: list[Value]) -> object:
        original(self, method, args)
        return original(self, method, args)

    return call


def _flood_to_ingress(
    original: Callable[..., list[tuple[int, bytes]]],
) -> Callable[..., list[tuple[int, bytes]]]:
    def run(
        self: switch.Switch, loaded: object, entries: object, ingress: int, packet: bytes
    ) -> list[tuple[int, bytes]]:
        outputs = original(self, loaded, entries, ingress, packet)
        # Only a flood sends to every port but one.
        if len(outputs) == self.ports - 1 > 1 and ingress not in [p for p, _ in outputs]:
            outputs = sorted([*outputs, (ingress, outputs[0][1])])
        return outputs

    return run


def _lpm_unchecked(original: Callable[..., None]) -> Callable[..., None]:
    def check_key_value(key: pb.Key, kv: pb.KeyValue, width: int) -> None:
        if kv.WhichOneof("kind") != "lpm":
            original(key, kv, width)

    return check_key_value


MUTANTS: dict[str, Mutant] = {
    "sub-off-by-one": Mutant(
        "bit<N> subtraction subtracts one more", expr, "bits_binary", _sub_off_by_one
    ),
    "count-twice": Mutant("a counter's count adds two", counter.Counter, "call", _count_twice),
    "flood-to-ingress": Mutant(
        "a flood also leaves on the ingress port", switch.Switch, "run", _flood_to_ingress
    ),
    "lpm-unchecked": Mutant(
        "an LPM key value is installed without checking its prefix",
        tables,
        "check_key_value",
        _lpm_unchecked,
    ),
}


@contextmanager
def applied(name: str) -> Iterator[None]:
    mutant = MUTANTS[name]
    original = getattr(mutant.owner, mutant.attribute)
    setattr(mutant.owner, mutant.attribute, mutant.make(original))
    try:
        yield
    finally:
        setattr(mutant.owner, mutant.attribute, original)


def killers(name: str) -> list[str]:
    """The fixtures whose check fails under the mutant."""
    with applied(name):
        return [
            path.stem
            for path in conformance.fixture_paths(conformance.DEFAULT_DIR)
            if conformance.check_python_fixture(path)
        ]


def main(argv: list[str]) -> int:
    names = argv or list(MUTANTS)
    survivors = 0
    for name in names:
        caught = killers(name)
        survivors += not caught
        print(f"{name}: {MUTANTS[name].description}; caught by {len(caught)}: {' '.join(caught)}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
