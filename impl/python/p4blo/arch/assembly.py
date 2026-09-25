"""Compose typed block libraries into complete IR for an architecture.

This is the point where H/M roots and export labels are chosen. Compiling
the library separately does not make those choices. The full program is
validated when a loader consumes it.
"""

from __future__ import annotations

from collections.abc import Mapping

from p4blo.arch.bindings import assembly_of
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl._build import Build
from p4blo.edsl.blocks import Block
from p4blo.edsl.errors import EdslError, provenance
from p4blo.edsl.library import BlockLibrary
from p4blo.edsl.views import Struct


def assemble(
    library: BlockLibrary,
    *,
    name: str,
    headers: type[Struct],
    metadata: type[Struct],
    exports: Mapping[str, type[Block]],
) -> apb.BlockAssembly:
    """Build a full IR program from an architecture's selected exports.

    An export must name a root class in `library` by identity. This
    prevents an unrelated class with the same IR name from being silently
    added at assembly. The returned IR is checked by `load` or an explicit
    validator call, preserving the builder's ability to emit invalid IR
    for diagnostic tests.
    """
    roots = set(library.blocks)
    for role, block in exports.items():
        if not role:
            raise EdslError("an export needs a role")
        if block not in roots:
            raise EdslError(f"export {role!r} must name a block in this BlockLibrary")

    build = Build(name)
    build.declare_errors(library.errors)
    with provenance():
        header_name = build.struct(headers, "headers")
        metadata_name = build.struct(metadata, "metadata")
    build.declare_externs(library.externs)
    for block in library.blocks:
        build.block(block)
    bindings = apb.BlockBindings(headers=header_name, metadata=metadata_name)
    for role, block in exports.items():
        bindings.exports.add(role=role, block=build.blocks[block].name)
    return assembly_of(build.finish(), bindings)


__all__ = ["assemble"]
