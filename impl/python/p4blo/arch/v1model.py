"""The supported v1model pipeline, its loader and P4 printer.

Core blocks remain independent. This module binds six V1Switch stages,
with explicit standard metadata and single-pass unicast/drop behavior.
"""

from __future__ import annotations

from p4blo import ir
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.contract import ContractError
from p4blo.arch.loader import LoadError
from p4blo.arch.printer import BoundProgramPrinter
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.arch.v1model_profile import (
    DROP_PORT,
    ROLE_KINDS,
    V1Model,
    assemble,
    check_profile,
    load,
)
from p4blo.printer import (
    PrintError,
    StmtPrinter,
    print_arg,
    print_literal,
    print_lvalue,
    print_param,
    print_type,
)
from p4blo.v0 import p4blo_pb2 as pb

__all__ = [
    "PrintError",
    "V1Model",
    "assemble",
    "load",
    "ROLE_KINDS",
    "DROP_PORT",
    "V1modelPrinter",
    "V1modelStmtPrinter",
    "print_extern_instance",
    "print_program",
    "standard_metadata_binding",
]

# Names used for omitted, empty stages.
VERIFY_CHECKSUM = "MyVerifyChecksum"
EGRESS = "MyEgress"
COMPUTE_CHECKSUM = "MyComputeChecksum"

# Native standard metadata parameter on parser, ingress and egress.
STANDARD_METADATA = "standard_metadata"
ROLE_NAMES = {
    "parser": "MyParser",
    "verify_checksum": VERIFY_CHECKSUM,
    "ingress": "MyIngress",
    "egress": EGRESS,
    "compute_checksum": COMPUTE_CHECKSUM,
    "deparser": "MyDeparser",
}


# ---------------------------------------------------------------------------
# The metadata contract
# ---------------------------------------------------------------------------


def standard_metadata_binding(
    index: BoundIndex, meta: str, role: str = "ingress"
) -> tuple[list[str], list[str]]:
    """Mirror the supported standard fields at their native stage boundary."""
    from p4blo.arch.contract import CONTRACT

    CONTRACT.check(index)
    fields = {f.name for f in index.fields(index.bindings.metadata)}
    inputs = {
        "parser": ("ingress_port",),
        "ingress": ("ingress_port", "parser_error", "egress_spec"),
        "egress": ("ingress_port", "parser_error", "egress_spec", "egress_port"),
        "verify_checksum": (),
        "compute_checksum": (),
        "deparser": (),
    }
    if role not in inputs:
        raise PrintError(f"no standard_metadata binding for role {role!r}")
    prologue = [
        f"{meta}.{name} = {STANDARD_METADATA}.{name};" for name in inputs[role] if name in fields
    ]
    epilogue = []
    if role == "ingress" and "egress_spec" in fields:
        epilogue.append(f"{STANDARD_METADATA}.egress_spec = {meta}.egress_spec;")
    if role == "egress":
        # Egress has a fresh drop request, not a new routing decision. Keep
        # its local value visible to ComputeChecksum, but lower its final
        # native value to drop or the already selected destination. This
        # also avoids the pinned P4-SpecTec runner's post-egress redirection.
        prologue = [
            f"{meta}.egress_spec = 0;"
            if line == f"{meta}.egress_spec = {STANDARD_METADATA}.egress_spec;"
            else line
            for line in prologue
        ]
        destination = f"{STANDARD_METADATA}.egress_port"
        if "egress_spec" in fields:
            destination = f"({meta}.egress_spec == 9w511 ? 9w511 : {destination})"
        epilogue.append(f"{STANDARD_METADATA}.egress_spec = {destination};")
    return prologue, epilogue


# Supported extern families, by ExternType name. Each matches an
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
    try:
        check_profile(index, require_pipeline=False)
    except (LoadError, ContractError) as exc:
        raise PrintError(str(exc)) from exc
    return V1modelPrinter(index, roles={e.role: e.block for e in index.bindings.exports}).render()


class V1modelPrinter(BoundProgramPrinter):
    """The printer bound to v1model: its includes, `standard_metadata`,
    the extern families' forms, empty stages and `main`."""

    stmt_printer = V1modelStmtPrinter

    def preamble(self) -> None:
        self.line(0, f"// {self.p.name}: printed by p4blo for v1model. Do not edit.")
        self.line(0, "#include <core.p4>")
        self.line(0, "#include <v1model.p4>")

    def extern_instance(self, instance: pb.ExternInstance) -> str | None:
        return print_extern_instance(self.index, instance)

    def role_params(self, role: str) -> list[str]:
        return [_sm_param()] if role in ("parser", "ingress", "egress") else []

    def _signature(self, block: pb.Block) -> str:
        role = self.role(block)
        if role in {"verify_checksum", "ingress", "egress", "compute_checksum"}:
            self._expect_params(block, [pb.DIRECTION_INOUT, pb.DIRECTION_INOUT])
            return ", ".join([*(print_param(p) for p in block.params), *self.role_params(role)])
        return super()._signature(block)

    def binding(self, block: pb.Block) -> tuple[list[str], list[str]]:
        role = self.role(block)
        assert role is not None
        assert isinstance(self.index, BoundIndex)
        return standard_metadata_binding(self.index, block.params[1].name, role)

    def apply(self, block: pb.Block) -> None:
        prologue, epilogue = (
            self.binding(block)
            if self.role(block) in {"verify_checksum", "ingress", "egress", "compute_checksum"}
            else ([], [])
        )
        self.line(1, "apply {")
        for line in prologue:
            self.line(2, line)
        self.lines(self.stmts.block(block.body, 2))
        for line in epilogue:
            self.line(2, line)
        self.line(1, "}")

    def postamble(self) -> None:
        self.missing_roles()
        self.main()

    def missing_roles(self) -> None:
        assert isinstance(self.index, BoundIndex)
        h, m = self.index.bindings.headers, self.index.bindings.metadata
        for role, name in ROLE_NAMES.items():
            if role in self.roles:
                continue
            if name in self.index.program_names:
                raise PrintError(f"the v1model adapter needs the name {name!r}")
            self.line(0)
            if role == "parser":
                self.line(
                    0,
                    f"parser {name}(packet_in packet, out {h} hdr, "
                    f"inout {m} meta, {_sm_param()}) {{",
                )
                self.line(1, "state start {")
                prologue, _ = standard_metadata_binding(self.index, "meta", role)
                for line in prologue:
                    self.line(2, line)
                self.line(2, "transition accept;")
                self.line(1, "}")
            else:
                if role == "deparser":
                    params = ["packet_out packet", f"in {h} hdr"]
                else:
                    params = [f"inout {h} hdr", f"inout {m} meta", *self.role_params(role)]
                self.line(0, f"control {name}({', '.join(params)}) {{")
                self.line(1, "apply {")
                prologue, epilogue = standard_metadata_binding(self.index, "meta", role)
                for line in [*prologue, *epilogue]:
                    self.line(2, line)
                self.line(1, "}")
            self.line(0, "}")

    def main(self) -> None:
        parts = [self.roles.get(role, name) for role, name in ROLE_NAMES.items()]
        self.line(0)
        self.line(0, f"V1Switch({', '.join(f'{p}()' for p in parts)}) main;")


def _sm_param() -> str:
    return f"inout standard_metadata_t {STANDARD_METADATA}"
