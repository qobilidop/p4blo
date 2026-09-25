"""The core wire value carries blocks, never architecture selections."""

import pytest
from google.protobuf.descriptor import Descriptor

from p4blo import ir, validator
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl.core import LibraryBuilder, bit
from p4blo.v0 import p4blo_pb2 as pb


def _assert_library_boundary(descriptor: Descriptor) -> None:
    assert {field.name for field in descriptor.fields}.isdisjoint(
        {"headers", "metadata", "exports"}
    )


def test_core_message_has_no_binding_fields() -> None:
    _assert_library_boundary(pb.BlockLibrary.DESCRIPTOR)
    assert "Program" not in pb.DESCRIPTOR.message_types_by_name
    assert "Export" not in pb.DESCRIPTOR.message_types_by_name


def test_boundary_guard_rejects_an_architecture_envelope() -> None:
    with pytest.raises(AssertionError):
        _assert_library_boundary(apb.BlockAssembly.DESCRIPTOR)


def test_library_roundtrips_without_architecture_bindings() -> None:
    builder = LibraryBuilder("scalars")
    builder.control("first", [("x", "inout", bit(8))])
    builder.control("second", [("y", "inout", bit(16))])
    library = builder.build_library()
    assert len(validator.check(library).blocks) == 2
    assert ir.load_text(ir.dump_text(library)) == library
    assert ir.load_binary(ir.dump_binary(library)) == library
    assert ir.load_json(ir.dump_json(library)) == library
