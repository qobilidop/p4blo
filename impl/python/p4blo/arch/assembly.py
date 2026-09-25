"""Compose typed block libraries into complete IR for an architecture.

This is the point where H/M roots and export labels are chosen. Compiling
the library separately does not make those choices. The full program is
validated when a loader consumes it.
"""

from __future__ import annotations

from collections.abc import Mapping

from p4blo.edsl._build import Build
from p4blo.edsl.blocks import Block
from p4blo.edsl.errors import EdslError, provenance
from p4blo.edsl.library import BlockLibrary
from p4blo.edsl.views import Struct
from p4blo.v0 import p4blo_pb2 as pb


def assemble(
    library: BlockLibrary,
    *,
    name: str,
    headers: type[Struct],
    metadata: type[Struct],
    exports: Mapping[str, type[Block]],
) -> pb.Program:
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
        build.core.headers = build.core.types.structs[build.struct(headers, "headers")]
        build.core.metadata = build.core.types.structs[build.struct(metadata, "metadata")]
    build.declare_externs(library.externs)
    for block in library.blocks:
        build.block(block)
    for role, block in exports.items():
        with provenance():
            build.core.export(role, build.blocks[block])
    return build.finish()


__all__ = ["assemble"]
