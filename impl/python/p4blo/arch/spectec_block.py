"""The block printer: IR to P4-16 for P4-SpecTec's p4blo block architecture.

The v1model shim (`p4blo.arch.v1model`) binds a program to v1model so that
a whole pipeline runs: the metadata contract is mapped onto
`standard_metadata`, checksum and egress controls are added, and the
simulator's V1Model architecture decides what happens between blocks. The
block architecture (tests/oracle/include/p4blo.p4, and the simulator patch
under tests/oracle/patches/) runs one block per request instead, so this
binding leaves all of that out. Each exported block keeps the signature the
IR gives it, with only the packet added, which is what `p4blo.printer`
prints by itself:

    parser   P(packet_in packet, out H hdr, inout M meta)
    control  C(inout H hdr, inout M meta)
    deparser D(packet_out packet, in H hdr)

and `main` is `P4blo(P(), C(), D())`. The extern families print in their
v1model form, which p4blo.p4 declares with V1Model's signatures. A missing
role gets the same empty block the v1model shim gives it, without
`standard_metadata`.
"""

from __future__ import annotations

from p4blo.arch.bindings import BoundIndex
from p4blo.arch.printer import MISSING_ROLE_NAMES, BoundProgramPrinter
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.arch.v1model import V1modelStmtPrinter, print_extern_instance
from p4blo.printer import PrintError
from p4blo.v0 import p4blo_pb2 as pb

__all__ = ["INCLUDE", "PACKAGE", "BlockPrinter", "PrintError", "print_program"]

# The include that declares the package and the extern families, and the
# package's names, which a program may not use; all must match
# tests/oracle/include/p4blo.p4. The extern families take the names the IR
# gives their types (`register`, `counter`), as under v1model.
INCLUDE = "p4blo.p4"
PACKAGE = "P4blo"
DECLARED = frozenset({PACKAGE, "P4bloParser", "P4bloControl", "P4bloDeparser", "main"})


def print_program(
    program: apb.BlockAssembly,
    *,
    index: BoundIndex | None = None,
    control_role: str | None = None,
) -> str:
    """Print independent blocks, selecting one control stage without merging.

    Packet assemblies select ingress by default; a core block assembly may
    export the literal control role. Other packet stages remain declarations.
    """
    if index is None:
        index = BoundIndex.build(program)
    exports = {e.role: e.block for e in index.bindings.exports}
    selected = control_role or ("ingress" if "ingress" in exports else "control")
    if control_role is not None and selected not in exports:
        raise PrintError(f"no block exported as {selected!r}")
    roles = {role: exports[role] for role in ("parser", "deparser") if role in exports}
    if selected in exports:
        block = index.blocks[exports[selected]]
        if block.kind != pb.BLOCK_KIND_CONTROL:
            raise PrintError(f"selected role {selected!r} is not a control")
        roles["control"] = block.name
    return BlockPrinter(index, roles=roles).render()


class BlockPrinter(BoundProgramPrinter):
    """The printer bound to the block architecture: its include, the
    extern families' v1model forms, and `main`."""

    stmt_printer = V1modelStmtPrinter

    def preamble(self) -> None:
        taken = sorted(DECLARED & set(self.index.program_names))
        if taken:
            raise PrintError(f"the block architecture declares {', '.join(taken)}")
        self.line(
            0, f"// {self.p.name}: printed by p4blo for the p4blo block architecture. Do not edit."
        )
        self.line(0, "#include <core.p4>")
        self.line(0, f"#include <{INCLUDE}>")

    def extern_instance(self, instance: pb.ExternInstance) -> str | None:
        return print_extern_instance(self.index, instance)

    def postamble(self) -> None:
        self.missing_roles()
        self.main()

    def main(self) -> None:
        parts = [self.roles.get(role, name) for role, name in MISSING_ROLE_NAMES.items()]
        self.line(0)
        self.line(0, f"{PACKAGE}({', '.join(f'{p}()' for p in parts)}) main;")
