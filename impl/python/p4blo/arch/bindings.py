"""Project and check architectural bindings of a core block library."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dc_field

from p4blo import ir
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    EXPORT_DUPLICATE,
    EXPORT_SIGNATURE,
    REF_KIND,
    REF_UNRESOLVED,
    Diagnostic,
    ValidationError,
)
from p4blo.validator.names import DIRECTION_NAMES, KIND_NAMES
from p4blo.validator.types import describe, same_type

# An exported block follows the reference architecture's H/M calling convention.
EXPORT_SIGNATURES: dict[int, tuple[tuple[int, str], ...]] = {
    pb.BLOCK_KIND_PARSER: ((pb.DIRECTION_OUT, "H"), (pb.DIRECTION_INOUT, "M")),
    pb.BLOCK_KIND_CONTROL: ((pb.DIRECTION_INOUT, "H"), (pb.DIRECTION_INOUT, "M")),
    pb.BLOCK_KIND_DEPARSER: ((pb.DIRECTION_IN, "H"),),
}


def library_of(assembly: apb.BlockAssembly) -> pb.BlockLibrary:
    """Extract the architecture-independent declarations without reordering."""
    library = pb.BlockLibrary(name=assembly.name, errors=assembly.errors)
    for field in (
        "header_types",
        "struct_types",
        "enum_types",
        "extern_types",
        "extern_instances",
        "blocks",
    ):
        getattr(library, field).extend(getattr(assembly, field))
    return library


def bindings_of(assembly: apb.BlockAssembly) -> apb.BlockBindings:
    """Extract H/M roots and export labels from the flat transport envelope."""
    bindings = apb.BlockBindings(headers=assembly.headers, metadata=assembly.metadata)
    bindings.exports.extend(assembly.exports)
    return bindings


def assembly_of(library: pb.BlockLibrary, bindings: apb.BlockBindings) -> apb.BlockAssembly:
    """Create the stable flat architecture transport from independent inputs."""
    assembly = apb.BlockAssembly(name=library.name, errors=library.errors)
    for field in (
        "header_types",
        "struct_types",
        "enum_types",
        "extern_types",
        "extern_instances",
        "blocks",
    ):
        getattr(assembly, field).extend(getattr(library, field))
    assembly.headers = bindings.headers
    assembly.metadata = bindings.metadata
    assembly.exports.extend(bindings.exports)
    return assembly


def exported(index: ir.Index, bindings: apb.BlockBindings, role: str) -> pb.Block:
    """Return the block selected for `role` after binding validation."""
    for export in bindings.exports:
        if export.role == role:
            return index.blocks[export.block]
    raise KeyError(role)


@dataclass
class BoundIndex(ir.Index):
    """A core name index paired with one explicit architectural role choice."""

    bindings: apb.BlockBindings = dc_field(default_factory=apb.BlockBindings)

    @classmethod
    def build(
        cls,
        program: apb.BlockAssembly | pb.BlockLibrary,
        *,
        bindings: apb.BlockBindings | None = None,
    ) -> BoundIndex:
        if isinstance(program, apb.BlockAssembly):
            if bindings is not None:
                raise TypeError("bindings must be omitted for a BlockAssembly")
            library, selected = library_of(program), bindings_of(program)
        elif isinstance(program, pb.BlockLibrary):
            if bindings is None:
                raise TypeError("bindings are required for a BlockLibrary")
            library, selected = program, bindings
        else:
            raise TypeError(f"expected BlockAssembly or BlockLibrary, got {type(program).__name__}")
        index = ir.Index.build(library)
        return cls(**vars(index), bindings=selected)

    def exported(self, role: str) -> pb.Block:
        return exported(self, self.bindings, role)


def validate_bindings(
    library: pb.BlockLibrary, index: ir.Index, bindings: apb.BlockBindings
) -> list[Diagnostic]:
    """Check H/M references, duplicate roles and exact export signatures."""
    diagnostics: list[Diagnostic] = []

    def resolve(name: str, table: Mapping[str, object], what: str, path: str) -> object | None:
        decl = table.get(name)
        if decl is not None:
            return decl
        if name in index.program_names:
            diagnostics.append(Diagnostic(REF_KIND, f"{name!r} is not a {what}", path))
        elif name:
            diagnostics.append(Diagnostic(REF_UNRESOLVED, f"no {what} named {name!r}", path))
        else:
            diagnostics.append(Diagnostic(REF_UNRESOLVED, f"{what} reference is unset", path))
        return None

    headers = resolve(bindings.headers, index.struct_types, "struct type", "headers")
    metadata = resolve(bindings.metadata, index.struct_types, "struct type", "metadata")
    header_type = pb.Type(struct=bindings.headers) if headers is not None else None
    metadata_type = pb.Type(struct=bindings.metadata) if metadata is not None else None
    roles: set[str] = set()
    for i, export in enumerate(bindings.exports):
        path = f"exports[{i}]"
        if export.role in roles:
            diagnostics.append(
                Diagnostic(EXPORT_DUPLICATE, f"role {export.role!r} exported twice", path)
            )
        roles.add(export.role)
        block = resolve(export.block, index.blocks, "block", f"{path}.block")
        if not isinstance(block, pb.Block) or block.kind not in EXPORT_SIGNATURES:
            continue
        if header_type is None or metadata_type is None:
            continue
        expected = [
            (direction, header_type if which == "H" else metadata_type)
            for direction, which in EXPORT_SIGNATURES[block.kind]
        ]
        actual = [(p.direction, p.type) for p in block.params]
        if len(actual) != len(expected) or any(
            d != ed or not same_type(t, et)
            for (d, t), (ed, et) in zip(actual, expected, strict=True)
        ):
            want = ", ".join(f"{DIRECTION_NAMES[d]} {describe(t)}" for d, t in expected)
            got = ", ".join(f"{DIRECTION_NAMES[d]} {describe(t)}" for d, t in actual)
            diagnostics.append(
                Diagnostic(
                    EXPORT_SIGNATURE,
                    f"{KIND_NAMES[block.kind]} {block.name!r} must have params ({want}); "
                    f"got ({got})",
                    path,
                )
            )
    return diagnostics


def check_bindings(library: pb.BlockLibrary, index: ir.Index, bindings: apb.BlockBindings) -> None:
    diagnostics = validate_bindings(library, index, bindings)
    if diagnostics:
        raise ValidationError(diagnostics)
