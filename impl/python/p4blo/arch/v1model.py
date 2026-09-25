"""The v1model shim: an IR program printed for v1model.

This is the repository's v1model support, and all of it: not an
implementation of the architecture but the mapping that lets the P4
oracles run a printed program (docs/arch-supports.md, "The v1model shim").
The IR has no architecture; `p4blo.printer` prints its declarations and
blocks, and this module binds them to v1model so that the program compiles
with p4c and runs on BMv2 or P4-SpecTec's simulator:

- the metadata contract mapped onto `standard_metadata`
  (`standard_metadata_binding`), the whole architecture binding;
- `standard_metadata` added to the exported parser and control;
- the extern families in their v1model form (`print_extern_instance` and
  `V1modelStmtPrinter`), which the p4blo block architecture shares;
- the includes, the empty checksum and egress controls, and `main`.

Entry point: `print_program`. A program handed to it is assumed valid;
what the printer or the shim cannot express raises `PrintError`.
"""

from __future__ import annotations

from p4blo import ir
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.printer import MISSING_ROLE_NAMES, BoundProgramPrinter
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.printer import (
    PrintError,
    StmtPrinter,
    print_arg,
    print_literal,
    print_lvalue,
    print_type,
)
from p4blo.v0 import p4blo_pb2 as pb

__all__ = [
    "PrintError",
    "V1modelPrinter",
    "V1modelStmtPrinter",
    "print_extern_instance",
    "print_program",
    "standard_metadata_binding",
]

# Fixed names of the shim's own blocks.
VERIFY_CHECKSUM = "MyVerifyChecksum"
EGRESS = "MyEgress"
COMPUTE_CHECKSUM = "MyComputeChecksum"

# The name of the parameter the shim adds to the exported parser and control.
STANDARD_METADATA = "standard_metadata"


# ---------------------------------------------------------------------------
# The metadata contract
# ---------------------------------------------------------------------------


def standard_metadata_binding(
    index: BoundIndex, meta: str, role: str = "control"
) -> tuple[list[str], list[str]]:
    """The v1model shim: the metadata contract mapped onto `standard_metadata`.

    This is the whole architecture binding. The IR's blocks read and write
    fields of their metadata struct M and perform no effect; v1model
    expresses the same decisions through `standard_metadata`. The mapping is
    by field name, each field optional (docs/design.md, "Metadata contract"):

    | M field        | type     | direction              | v1model                             |
    |----------------|----------|------------------------|-------------------------------------|
    | `ingress_port` | `bit<9>` | provided, parser start | `M.ingress_port = sm.ingress_port;` |
    | `parser_error` | `error`  | provided, control      | `M.parser_error = sm.parser_error;` |
    | `egress_port`  | `bit<9>` | consumed               | `sm.egress_spec = M.egress_port;`   |
    | `drop`         | `bool`   | consumed               | `if (M.drop) { mark_to_drop(sm); }` |

    The architectures write `ingress_port` before the parser runs, so the
    shim copies it in at the top of the parser's start state, and again at
    the start of the ingress control's `apply`, where it still holds the
    same value; `parser_error` is set after the parser, so only the control
    copies it. Consumed fields are acted on at the end of the control's
    `apply`, drop last so that it wins over the egress port. `flood` has no
    v1model mapping and is left to the architectures. Any other field of M
    is plain user metadata.

    Returns the prologue and epilogue statements of the block exported as
    `role`, "parser" or "control", `meta` being that block's name for its M
    parameter; a parser's epilogue is empty. A contract field with the wrong
    type is a `PrintError`, since the architectures would refuse it too.
    """
    if role not in ("parser", "control"):
        raise PrintError(f"no standard_metadata binding for role {role!r}")
    fields = {f.name: f.type for f in index.fields(index.bindings.metadata)}

    def has(name: str, expected: pb.Type) -> bool:
        actual = fields.get(name)
        if actual is None:
            return False
        if actual != expected:
            raise PrintError(
                f"metadata field {name!r} is {print_type(actual)}, "
                f"the contract needs {print_type(expected)}"
            )
        return True

    prologue: list[str] = []
    epilogue: list[str] = []
    sm = STANDARD_METADATA
    control = role == "control"
    if has("ingress_port", pb.Type(bits=9)):
        prologue.append(f"{meta}.ingress_port = {sm}.ingress_port;")
    if has("parser_error", pb.Type(error=pb.ErrorType())) and control:
        prologue.append(f"{meta}.parser_error = {sm}.parser_error;")
    if has("egress_port", pb.Type(bits=9)) and control:
        epilogue.append(f"{sm}.egress_spec = {meta}.egress_port;")
    if has("drop", pb.Type(boolean=pb.BoolType())) and control:
        epilogue.append(f"if ({meta}.drop) {{ mark_to_drop({sm}); }}")
    return prologue, epilogue


# The extern families the shim knows, by ExternType name. Each matches an
# implementation under impl/python/p4blo/arch/externs/.
REGISTER = "register"
COUNTER = "counter"
CHECKSUM16 = "checksum16"
CRC_WIDTHS = {"crc16": 16, "crc32": 32}


def _crc_width(decl: pb.ExternType) -> int:
    width = CRC_WIDTHS[ir.extern_family(decl.name)]
    if decl.constructor_params or len(decl.methods) != 1:
        raise PrintError(f"{decl.name}: CRC declaration has the wrong shape")
    method = decl.methods[0]
    if (
        method.name != "compute"
        or len(method.params) != 1
        or method.params[0].direction != pb.DIRECTION_IN
        or method.params[0].type.WhichOneof("kind") != "bits"
        or method.returns.WhichOneof("kind") != "bits"
        or method.returns.bits != width
    ):
        raise PrintError(f"{decl.name}: CRC declaration has the wrong shape")
    data_width = method.params[0].type.bits
    if data_width == 0 or data_width % 8:
        raise PrintError(f"{decl.name}: data width must be a positive multiple of 8")
    return width


def _instance_size(instance: pb.ExternInstance) -> str:
    if not instance.args or instance.args[0].WhichOneof("value") != "bits":
        raise PrintError(f"extern instance {instance.name!r} has no size argument")
    return print_literal(instance.args[0])


def print_extern_instance(index: ir.Index, instance: pb.ExternInstance) -> str | None:
    """The v1model instantiation of an extern instance, or None when the
    family has no instance in v1model (checksum16 is a function there)."""
    extern_type = index.extern_types[instance.extern_type]
    family = ir.extern_family(extern_type.name)
    if family == REGISTER:
        # The value width is the width of read's out parameter.
        read = next((m for m in extern_type.methods if m.name == "read"), None)
        if read is None or not read.params:
            raise PrintError(f"extern type {extern_type.name!r} has no read method")
        value_type = print_type(read.params[0].type)
        return f"register<{value_type}>({_instance_size(instance)}) {instance.name};"
    if family == COUNTER:
        return f"counter({_instance_size(instance)}, CounterType.packets) {instance.name};"
    if family == CHECKSUM16:
        return None
    if family in CRC_WIDTHS:
        _crc_width(extern_type)
        if instance.args:
            raise PrintError(f"{family}: constructor takes no arguments")
        return None
    raise PrintError(f"no v1model form for extern type {extern_type.name!r}")


class V1modelStmtPrinter(StmtPrinter):
    """Statements with the extern families' calls in their v1model form;
    without an index every extern call prints as a plain method call."""

    def call_extern(self, call: pb.CallExtern) -> str:
        family = None
        if self.index is not None:
            instance = self.index.extern_instances[call.instance]
            family = ir.extern_family(self.index.extern_types[instance.extern_type].name)
        if family == CHECKSUM16:
            return self._checksum(call)
        if family in CRC_WIDTHS:
            assert self.index is not None
            instance = self.index.extern_instances[call.instance]
            width = _crc_width(self.index.extern_types[instance.extern_type])
            if call.method != "compute" or len(call.args) != 1 or not call.HasField("result"):
                raise PrintError(f"{family} call {call.instance}.{call.method} has the wrong shape")
            return (
                f"hash({print_lvalue(call.result)}, HashAlgorithm.{family}, "
                f"{width}w0, {{ {print_arg(call.args[0])} }}, 64w{1 << width});"
            )
        return super().call_extern(call)

    @staticmethod
    def _checksum(call: pb.CallExtern) -> str:
        # v1model has no checksum extern object; its `hash` with
        # HashAlgorithm.csum16, base 0 and max 2^16 is the one's-complement
        # checksum of the data, which is what checksum16.compute returns.
        # That this agrees with impl/python/p4blo/arch/externs/checksum.py is verified
        # against the oracle in step 4 (docs/design.md, "Build order").
        if call.method != "compute" or len(call.args) != 1 or not call.HasField("result"):
            raise PrintError(f"checksum16 call {call.instance}.{call.method} has the wrong shape")
        result = print_lvalue(call.result)
        data = print_arg(call.args[0])
        return f"hash({result}, HashAlgorithm.csum16, 16w0, {{ {data} }}, 32w65536);"


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------


def print_program(program: apb.BlockAssembly, *, index: BoundIndex | None = None) -> str:
    """The complete P4-16 program for v1model, as text."""
    if index is None:
        index = BoundIndex.build(program)
    return V1modelPrinter(index, roles={e.role: e.block for e in index.bindings.exports}).render()


class V1modelPrinter(BoundProgramPrinter):
    """The printer bound to v1model: its includes, `standard_metadata`,
    the extern families' forms, the shim's own controls and `main`."""

    stmt_printer = V1modelStmtPrinter

    def preamble(self) -> None:
        self.line(0, f"// {self.p.name}: printed by p4blo for v1model. Do not edit.")
        self.line(0, "#include <core.p4>")
        self.line(0, "#include <v1model.p4>")

    def extern_instance(self, instance: pb.ExternInstance) -> str | None:
        return print_extern_instance(self.index, instance)

    def role_params(self, role: str) -> list[str]:
        return [_sm_param()] if role in ("parser", "control") else []

    def binding(self, block: pb.Block) -> tuple[list[str], list[str]]:
        role = self.role(block)
        assert role is not None
        assert isinstance(self.index, BoundIndex)
        return standard_metadata_binding(self.index, block.params[1].name, role)

    def postamble(self) -> None:
        self.missing_roles()
        self.shim_controls()
        self.main()

    def shim_controls(self) -> None:
        assert isinstance(self.index, BoundIndex)
        h, m = self.index.bindings.headers, self.index.bindings.metadata
        checksum_params = f"inout {h} hdr, inout {m} meta"
        egress_params = f"{checksum_params}, {_sm_param()}"
        for name, params in [
            (VERIFY_CHECKSUM, checksum_params),
            (EGRESS, egress_params),
            (COMPUTE_CHECKSUM, checksum_params),
        ]:
            if name in self.index.program_names:
                raise PrintError(f"the shim needs the name {name!r}, which the program uses")
            self.line(0)
            self.line(0, f"control {name}({params}) {{")
            self.line(1, "apply {")
            self.line(1, "}")
            self.line(0, "}")

    def main(self) -> None:
        def block(role: str) -> str:
            return self.roles.get(role, MISSING_ROLE_NAMES[role])

        parts = [
            block("parser"),
            VERIFY_CHECKSUM,
            block("control"),
            EGRESS,
            COMPUTE_CHECKSUM,
            block("deparser"),
        ]
        self.line(0)
        self.line(0, f"V1Switch({', '.join(f'{p}()' for p in parts)}) main;")


def _sm_param() -> str:
    return f"inout standard_metadata_t {STANDARD_METADATA}"
