"""The generic loader checks each explicit architecture requirement."""

from __future__ import annotations

import pytest

from p4blo import arch
from p4blo.arch import reference
from p4blo.arch import validator as arch_validator
from p4blo.arch.bindings import bindings_of, library_of
from p4blo.arch.contract import Contract
from p4blo.arch.externs import Registry
from p4blo.arch.loader import LoadError, load
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl import BlockLibrary, Control, Struct
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator import EXPORT_DUPLICATE, EXPORT_SIGNATURE, REF_UNRESOLVED, ValidationError


class Headers(Struct):
    pass


class Metadata(Struct):
    pass


class Policy(Control[Headers, Metadata]):
    pass


def program() -> apb.BlockAssembly:
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


def test_one_library_loads_under_distinct_bindings() -> None:
    assembly = program()
    library = library_of(assembly)
    first = bindings_of(assembly)
    second = apb.BlockBindings(headers=first.headers, metadata=first.metadata)
    second.exports.add(role="alternate", block="Policy")
    loaded_first = load(
        library,
        bindings=first,
        registry=Registry(),
        contract=Contract(()),
        roles={"policy": pb.BLOCK_KIND_CONTROL},
    )
    loaded_second = load(
        library,
        bindings=second,
        registry=Registry(),
        contract=Contract(()),
        roles={"alternate": pb.BLOCK_KIND_CONTROL},
    )
    assert loaded_first.index.program.SerializeToString() == library.SerializeToString()
    assert loaded_second.block("alternate") == loaded_first.block("policy")


def test_library_requires_explicit_bindings() -> None:
    with pytest.raises(TypeError, match="bindings are required"):
        load(
            library_of(program()),
            registry=Registry(),
            contract=Contract(()),
            roles={"policy": pb.BLOCK_KIND_CONTROL},
        )


def test_binding_validation_rejects_bad_roots_roles_and_signatures() -> None:
    assembly = program()
    library = library_of(assembly)
    bindings = bindings_of(assembly)
    bindings.headers = "missing"
    bindings.exports.add(role="policy", block="Policy")
    diagnostics = arch_validator.validate(library, bindings=bindings)
    assert [d.code for d in diagnostics] == [REF_UNRESOLVED, EXPORT_DUPLICATE]

    bindings = bindings_of(assembly)
    bindings.metadata = bindings.headers
    diagnostics = arch_validator.validate(library, bindings=bindings)
    assert [d.code for d in diagnostics] == [EXPORT_SIGNATURE]
    with pytest.raises(ValidationError, match="EXPORT_SIGNATURE"):
        load(
            library,
            bindings=bindings,
            registry=Registry(),
            contract=Contract(()),
            roles={"policy": pb.BLOCK_KIND_CONTROL},
        )


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
