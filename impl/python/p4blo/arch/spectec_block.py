"""The block printer: IR to P4-16 for P4-SpecTec's p4blo block architecture.

The v1model printer (`p4blo.arch.v1model`) wraps a program in the v1model
shim so that a whole pipeline runs: the metadata contract is mapped onto
`standard_metadata`, checksum and egress controls are added, and the
simulator's V1Model architecture decides what happens between blocks. The
block architecture (tests/oracle/include/p4blo.p4, and the simulator patch
under tests/oracle/patches/) runs one block per request instead, so this
printer leaves all of that out. Each exported block keeps the signature the
IR gives it, with only the packet added:

    parser   P(packet_in packet, out H hdr, inout M meta)
    control  C(inout H hdr, inout M meta)
    deparser D(packet_out packet, in H hdr)

and `main` is `P4blo(P(), C(), D())`. Everything else, statements,
expressions, tables and the extern families, is printed exactly as the
v1model printer prints it, by that printer's own code: this module
subclasses its program printer and overrides only the parts that belong to
the shim. A missing role gets the same empty block the v1model printer
gives it, without `standard_metadata`.
"""

from __future__ import annotations

from p4blo import ir
from p4blo.arch.v1model import (
    MISSING_ROLE_NAMES,
    PACKET,
    PrintError,
    _print_extern_instance,  # pyright: ignore[reportPrivateUsage]
    _print_param,  # pyright: ignore[reportPrivateUsage]
    _ProgramPrinter,  # pyright: ignore[reportPrivateUsage]
)
from p4blo.v0 import p4blo_pb2 as pb

__all__ = ["INCLUDE", "PACKAGE", "PrintError", "print_program"]

# The include that declares the package and the extern families, and the
# package's names, which a program may not use; all must match
# tests/oracle/include/p4blo.p4. The extern families take the names the IR
# gives their types (`register`, `counter`), as under v1model.
INCLUDE = "p4blo.p4"
PACKAGE = "P4blo"
DECLARED = frozenset({PACKAGE, "P4bloParser", "P4bloControl", "P4bloDeparser", "main"})


def print_program(program: pb.Program, *, index: ir.Index | None = None) -> str:
    """The complete P4-16 program for the p4blo block architecture."""
    if index is None:
        index = ir.Index.build(program)
    return _BlockPrinter(index).render()


class _BlockPrinter(_ProgramPrinter):
    def render(self) -> str:
        p = self.p
        taken = sorted(DECLARED & set(self.index.program_names))
        if taken:
            raise PrintError(f"the block architecture declares {', '.join(taken)}")
        self.line(
            0, f"// {p.name}: printed by p4blo for the p4blo block architecture. Do not edit."
        )
        self.line(0, "#include <core.p4>")
        self.line(0, f"#include <{INCLUDE}>")
        self.errors()
        for enum in p.enum_types:
            self.enum(enum)
        for header in p.header_types:
            self.header(header)
        for struct in p.struct_types:
            self.struct(struct)
        if self.top_level_externs:
            self.line(0)
            for name in self.top_level_externs:
                decl = self._extern_decl(name)
                if decl is not None:
                    self.line(0, decl)
        for block in self._block_order():
            self.block(block)
        self.missing_roles()
        self.main()
        return "\n".join(self.out) + "\n"

    def _extern_decl(self, name: str) -> str | None:
        return _print_extern_instance(self.index, self.index.extern_instances[name])

    def _signature(self, block: pb.Block) -> str:
        params = [_print_param(p) for p in block.params]
        match self._role(block):
            case "parser":
                self._expect_params(block, [pb.DIRECTION_OUT, pb.DIRECTION_INOUT])
                params = [f"packet_in {PACKET}", *params]
            case "control":
                self._expect_params(block, [pb.DIRECTION_INOUT, pb.DIRECTION_INOUT])
            case "deparser":
                self._expect_params(block, [pb.DIRECTION_IN])
                params = [f"packet_out {PACKET}", *params]
            case None:
                if block.kind == pb.BLOCK_KIND_PARSER:
                    params = [f"packet_in {PACKET}", *params]
                elif block.kind == pb.BLOCK_KIND_DEPARSER:
                    params = [f"packet_out {PACKET}", *params]
            case role:
                raise PrintError(f"unknown export role {role!r}")
        return ", ".join(params)

    def states(self, block: pb.Block) -> None:
        """The states, with a synthesized `start` when the IR's start state
        has another name, as P4 requires one named `start`."""
        names = {s.name for s in block.states}
        if block.start_state != "start":
            if "start" in names:
                raise PrintError(
                    f"parser {block.name!r} starts at {block.start_state!r} "
                    "but also has a state named 'start'"
                )
            self.line(1, "state start {")
            self.line(2, f"transition {block.start_state};")
            self.line(1, "}")
        for state in block.states:
            self.state(state)

    def apply(self, block: pb.Block) -> None:
        self.line(1, "apply {")
        self.lines(self.stmts.block(block.body, 2))
        self.line(1, "}")

    def missing_roles(self) -> None:
        h, m = self.p.headers, self.p.metadata
        for role, name in MISSING_ROLE_NAMES.items():
            if role in self.roles:
                continue
            if name in self.index.program_names:
                raise PrintError(f"no block exported as {role!r} and the name {name!r} is taken")
            self.line(0)
            match role:
                case "parser":
                    params = f"packet_in {PACKET}, out {h} hdr, inout {m} meta"
                    self.line(0, f"parser {name}({params}) {{")
                    self.line(1, "state start {")
                    self.line(2, "transition accept;")
                    self.line(1, "}")
                case "control":
                    self.line(0, f"control {name}(inout {h} hdr, inout {m} meta) {{")
                    self.line(1, "apply {")
                    self.line(1, "}")
                case _:
                    self.line(0, f"control {name}(packet_out {PACKET}, in {h} hdr) {{")
                    self.line(1, "apply {")
                    self.line(1, "}")
            self.line(0, "}")

    def main(self) -> None:
        parts = [self.roles.get(role, name) for role, name in MISSING_ROLE_NAMES.items()]
        self.line(0)
        self.line(0, f"{PACKAGE}({', '.join(f'{p}()' for p in parts)}) main;")
