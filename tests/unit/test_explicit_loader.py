"""The generic loader checks each explicit architecture requirement."""

from __future__ import annotations

import pytest

from p4blo import arch
from p4blo.arch import reference
from p4blo.arch.contract import Contract
from p4blo.arch.externs import Registry
from p4blo.arch.loader import LoadError, load
from p4blo.edsl import BlockLibrary, Control, Struct
from p4blo.v0 import p4blo_pb2 as pb


class Headers(Struct):
    pass


class Metadata(Struct):
    pass


class Policy(Control[Headers, Metadata]):
    pass


def program() -> pb.Program:
    return arch.assemble(
        BlockLibrary(Policy),
        name="control_only",
        headers=Headers,
        metadata=Metadata,
        exports={"policy": Policy},
    )


def test_explicit_loader_accepts_control_only_role() -> None:
    loaded = load(
        program(),
        registry=Registry(),
        contract=Contract(()),
        roles={"policy": pb.BLOCK_KIND_CONTROL},
    )
    assert dict(loaded.blocks) == {"policy": "Policy"}
    assert loaded.block("policy") == "Policy"


def test_explicit_loader_requires_registry_contract_and_roles() -> None:
    with pytest.raises(TypeError, match="registry"):
        load(program())  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="contract"):
        load(program(), registry=Registry())  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="roles"):
        load(program(), registry=Registry(), contract=Contract(()))  # type: ignore[call-arg]


def test_missing_role_is_reported_at_load() -> None:
    with pytest.raises(LoadError, match="exports no 'missing' block"):
        load(
            program(),
            registry=Registry(),
            contract=Contract(()),
            roles={"missing": pb.BLOCK_KIND_CONTROL},
        )


def test_wrong_role_kind_is_reported_at_load() -> None:
    with pytest.raises(
        LoadError, match="export 'policy' must be BLOCK_KIND_PARSER, got BLOCK_KIND_CONTROL"
    ):
        load(
            program(),
            registry=Registry(),
            contract=Contract(()),
            roles={"policy": pb.BLOCK_KIND_PARSER},
        )


def test_reference_loader_requires_its_switch_roles() -> None:
    with pytest.raises(LoadError, match="exports no 'parser' block"):
        reference.load(program())
    with pytest.raises(LoadError, match="reference architecture has no 'policy' role"):
        reference.load(program(), roles=("policy",))
