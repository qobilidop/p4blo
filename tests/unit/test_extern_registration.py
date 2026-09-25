"""A third-party extern is declared, registered and bound without core changes."""

from __future__ import annotations

import pytest

from examples import custom_extern
from p4blo import arch
from p4blo.arch.contract import Contract
from p4blo.arch.externs import BindError, Implementation, MethodShape, Registry, Shape
from p4blo.v0 import p4blo_pb2 as pb


def load(registry: Registry, program: pb.Program | None = None) -> arch.Loaded:
    return arch.load(
        program if program is not None else custom_extern.build(),
        registry=registry,
        contract=Contract(()),
        roles={"transform": pb.BLOCK_KIND_CONTROL},
    )


def test_custom_family_runs_without_a_supplied_architecture() -> None:
    assert custom_extern.demo() == (1, 2)


def test_one_registry_creates_fresh_state_per_instance_and_load() -> None:
    program = custom_extern.build()
    other = program.extern_instances.add()
    other.CopyFrom(program.extern_instances[0])
    other.name = "other"
    other.args[0].bits.value = "7"

    offered = custom_extern.registry()
    first = load(offered, program)
    second = load(offered, program)
    numbers = first.externs["numbers"]
    other_numbers = first.externs["other"]
    second_numbers = second.externs["numbers"]
    assert isinstance(numbers, custom_extern.SequenceBinding)
    assert isinstance(other_numbers, custom_extern.SequenceBinding)
    assert isinstance(second_numbers, custom_extern.SequenceBinding)
    assert (numbers.value, other_numbers.value, second_numbers.value) == (0, 7, 0)

    numbers.call("advance", [])
    assert (numbers.value, other_numbers.value, second_numbers.value) == (1, 7, 0)
    other_numbers.call("advance", [])
    assert (numbers.value, other_numbers.value, second_numbers.value) == (1, 8, 0)


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
