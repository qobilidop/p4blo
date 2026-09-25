"""A third-party extern is declared, registered and bound without core changes."""

from __future__ import annotations

import pytest

from examples import custom_extern
from p4blo import arch
from p4blo.arch.contract import Contract
from p4blo.arch.externs import BindError, Implementation, MethodShape, Registry, Shape
from p4blo.v0 import p4blo_pb2 as pb


def load(registry: Registry) -> arch.Loaded:
    return arch.load(
        custom_extern.build(),
        registry=registry,
        contract=Contract(()),
        roles={"transform": pb.BLOCK_KIND_CONTROL},
    )


def test_custom_family_runs_without_a_supplied_architecture() -> None:
    assert custom_extern.demo() == (1, 2)
    first = load(custom_extern.registry())
    second = load(custom_extern.registry())
    assert first.externs["numbers"] is not second.externs["numbers"]
    assert isinstance(first.externs["numbers"], custom_extern.SequenceBinding)
    assert isinstance(second.externs["numbers"], custom_extern.SequenceBinding)
    assert first.externs["numbers"].value == second.externs["numbers"].value == 0


def test_missing_registration_names_the_family() -> None:
    with pytest.raises(BindError, match="no implementation for extern type 'sequence'"):
        load(Registry())


def test_duplicate_registration_is_explicit() -> None:
    offered = custom_extern.registry()
    with pytest.raises(ValueError, match="sequence registered twice"):
        offered.register(offered.implementations["sequence"])


def test_signature_mismatch_is_found_before_running() -> None:
    offered = Registry()
    offered.register(
        Implementation(
            "sequence",
            Shape(constructor=(8,), methods={"advance": MethodShape((), returns=16)}),
            custom_extern.make_sequence,
        )
    )
    with pytest.raises(BindError, match="sequence.advance return: expected bit<16>"):
        load(offered)


def test_registry_does_not_mutate_on_failed_bind() -> None:
    offered = Registry()
    with pytest.raises(BindError):
        load(offered)
    offered.register(
        Implementation(
            "sequence",
            Shape(constructor=(8,), methods={"advance": MethodShape((), returns=8)}),
            custom_extern.make_sequence,
        )
    )
    assert "numbers" in load(offered).externs
