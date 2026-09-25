"""An independent control with a locally registered extern.

Run ``python examples/custom_extern.py`` after installing the project. The
eDSL declares the ``sequence`` service in a block library that compiles
without architecture or program roles. A host assembles it under its own
``transform`` role, then supplies a Python factory at load. The IR and eDSL
have no special case for this service. A Lean model or P4 printer mapping
would be separate work.
"""

from __future__ import annotations

from collections.abc import Sequence

from p4blo import arch, interp
from p4blo import edsl as p4
from p4blo.arch import entry
from p4blo.arch.contract import Contract
from p4blo.arch.externs import Bindings, Implementation, MethodShape, Registry, Shape
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.interp.values import Bits, Struct, Value, zero
from p4blo.v0 import p4blo_pb2 as pb


class Headers(p4.Struct):
    pass


class Metadata(p4.Struct):
    value: p4.bit8


class SequenceExtern(p4.Extern, name="sequence"):
    """Program-side signature, independent of any Python implementation."""

    def __init__(self, name: str, start: p4.Const[p4.bit8]) -> None:
        super().__init__(name, start)

    def advance(self) -> p4.Bits[p4.L[8]]: ...


sequence = SequenceExtern("numbers", 0)


class Transform(p4.Control[Headers, Metadata]):
    def apply(self) -> None:
        self.assign(self.meta.value, sequence.advance())


def library() -> p4.BlockLibrary:
    """Declare this control and its extern dependency without an architecture."""
    return p4.BlockLibrary(Transform, externs=[sequence])


def build() -> apb.BlockAssembly:
    """Assemble a host program with just the block role it runs."""
    return arch.assemble(
        library(),
        name="custom_extern",
        headers=Headers,
        metadata=Metadata,
        exports={"transform": Transform},
    )


class SequenceBinding:
    """State of one instance in one loaded program."""

    def __init__(self, start: int) -> None:
        self.value = start

    def call(self, method: str, args: list[Value]) -> interp.ExternResult:
        assert method == "advance" and not args
        self.value = (self.value + 1) & 0xFF
        return interp.ExternResult(returns=Bits(8, self.value))


def make_sequence(
    decl: pb.ExternType, bindings: Bindings, args: Sequence[Value]
) -> SequenceBinding:
    """Called separately for each declared instance at each program load."""
    start = args[0]
    assert isinstance(start, Bits)
    return SequenceBinding(start.value)


def registry() -> Registry:
    """Offer exactly the Python extern implementation this host supports."""
    offered = Registry()
    offered.register(
        Implementation(
            "sequence",
            Shape(constructor=(8,), methods={"advance": MethodShape((), returns=8)}),
            make_sequence,
        )
    )
    return offered


def demo() -> tuple[int, int]:
    """Run the named control twice to observe state across invocations."""
    loaded = arch.load(
        build(),
        registry=registry(),
        contract=Contract(()),
        roles={"transform": pb.BLOCK_KIND_CONTROL},
    )
    headers = zero(pb.Type(struct="Headers"), loaded.index)
    metadata = loaded.metadata.zero()
    assert isinstance(headers, Struct)

    def run_once() -> int:
        _, output = entry.run_control(
            loaded.index,
            loaded.block("transform"),
            headers,
            metadata,
            loaded.entries(),
            loaded.externs,
        )
        value = output.fields[0]
        assert isinstance(value, Bits)
        return value.value

    return run_once(), run_once()


if __name__ == "__main__":
    print(demo())
