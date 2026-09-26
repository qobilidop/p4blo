"""The supported v1model metadata and six-stage execution profile."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from google.protobuf.message import Message

from p4blo.arch import entry, validator
from p4blo.arch.assembly import assemble as assemble_explicit
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.contract import CONTRACT
from p4blo.arch.externs import supplied_registry
from p4blo.arch.loader import Loaded, LoadError
from p4blo.arch.loader import load as load_explicit
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl.blocks import Control, Deparser, Parser
from p4blo.edsl.library import BlockLibrary
from p4blo.edsl.views import Struct
from p4blo.interp.tables import InstalledEntries
from p4blo.printer.statements import walk
from p4blo.v0 import p4blo_pb2 as pb

ROLE_KINDS = {
    "parser": pb.BLOCK_KIND_PARSER,
    "verify_checksum": pb.BLOCK_KIND_CONTROL,
    "ingress": pb.BLOCK_KIND_CONTROL,
    "egress": pb.BLOCK_KIND_CONTROL,
    "compute_checksum": pb.BLOCK_KIND_CONTROL,
    "deparser": pb.BLOCK_KIND_DEPARSER,
}
REQUIRED_ROLES = ("parser", "ingress", "deparser")
READABLE = {
    "parser": {"ingress_port"},
    "verify_checksum": set(),
    "ingress": {"ingress_port", "parser_error", "egress_spec"},
    "egress": {"ingress_port", "parser_error", "egress_spec", "egress_port"},
    "compute_checksum": {"ingress_port", "parser_error", "egress_spec", "egress_port"},
    "deparser": set(),
}
DROP_PORT = 511
FORBIDDEN_FIELDS = frozenset(
    {
        "drop",
        "flood",
        "packet_length",
        "instance_type",
        "mcast_grp",
        "egress_rid",
        "checksum_error",
        "priority",
        "enq_timestamp",
        "enq_qdepth",
        "deq_timedelta",
        "deq_qdepth",
        "ingress_global_timestamp",
        "egress_global_timestamp",
    }
)


def assemble(
    library: BlockLibrary,
    *,
    name: str,
    headers: type[Struct],
    metadata: type[Struct],
    parser: type[Parser[Any, Any]],
    ingress: type[Control[Any, Any]],
    deparser: type[Deparser[Any]],
    verify_checksum: type[Control[Any, Any]] | None = None,
    egress: type[Control[Any, Any]] | None = None,
    compute_checksum: type[Control[Any, Any]] | None = None,
) -> apb.BlockAssembly:
    """Bind independent blocks to V1Switch; omitted optional stages are empty."""
    selected = {
        "parser": parser,
        "verify_checksum": verify_checksum,
        "ingress": ingress,
        "egress": egress,
        "compute_checksum": compute_checksum,
        "deparser": deparser,
    }
    exports = {role: block for role, block in selected.items() if block is not None}
    result = assemble_explicit(
        library, name=name, headers=headers, metadata=metadata, exports=exports
    )
    check_profile(BoundIndex.build(result))
    return result


def load(program: apb.BlockAssembly) -> Loaded:
    """Load only the supported v1model profile, with fresh supplied extern state."""
    index = validator.check(program)
    check_profile(index)
    return load_explicit(
        program,
        registry=supplied_registry(),
        contract=CONTRACT,
        roles={e.role: ROLE_KINDS[e.role] for e in index.bindings.exports},
    )


def check_profile(index: BoundIndex, *, require_pipeline: bool = True) -> None:
    """Reject unsupported architecture behavior without restricting core validity."""
    fields = {f.name for f in index.fields(index.bindings.metadata)}
    forbidden = fields & FORBIDDEN_FIELDS
    if forbidden:
        raise LoadError(f"unsupported v1model metadata fields: {', '.join(sorted(forbidden))}")
    CONTRACT.check(index)
    roles = {e.role: e.block for e in index.bindings.exports}
    if len(set(roles.values())) != len(roles):
        raise LoadError("each v1model stage must select a distinct block")
    unknown = set(roles) - set(ROLE_KINDS)
    if unknown:
        raise LoadError(f"unsupported v1model roles: {', '.join(sorted(unknown))}")
    if require_pipeline and (missing := set(REQUIRED_ROLES) - set(roles)):
        raise LoadError(f"missing v1model roles: {', '.join(sorted(missing))}")
    protected = fields & {f.name for f in CONTRACT.fields}
    for role, name in roles.items():
        block = index.blocks[name]
        if block.kind != ROLE_KINDS[role]:
            raise LoadError(f"v1model {role} has the wrong block kind")
        aliases: dict[str, tuple[str, ...]] = {}
        if len(block.params) > 1:
            aliases[block.params[1].name] = ()
        _check_block(index, block, role, aliases, protected, set())


def _path(value: pb.LValue | pb.Expr) -> tuple[str, ...] | None:
    kind = value.WhichOneof("kind")
    if kind == "var":
        return (value.var,)
    if kind == "member":
        parent = _path(value.member.base)
        return (*parent, value.member.field) if parent is not None else None
    return None


def _check_block(
    index: BoundIndex,
    block: pb.Block,
    role: str,
    aliases: dict[str, tuple[str, ...]],
    protected: set[str],
    active: set[str],
) -> None:
    if block.name in active:
        raise LoadError("recursive v1model block invocation")
    active = active | {block.name}

    def alias(
        value: pb.LValue | pb.Expr, scope: dict[str, tuple[str, ...]]
    ) -> tuple[str, ...] | None:
        path = _path(value)
        if path is None or path[0] not in scope:
            return None
        return (*scope[path[0]], *path[1:])

    def written(path: tuple[str, ...] | None) -> None:
        if path is None or not protected:
            return
        if not path:
            raise LoadError(f"{role}: whole metadata writes overwrite standard metadata")
        if path[0] in protected and not (
            path == ("egress_spec",) and role in {"ingress", "egress"}
        ):
            raise LoadError(f"{role}: standard metadata {path[0]} is read-only")

    def reads(message: Message, scope: dict[str, tuple[str, ...]]) -> None:
        if isinstance(message, pb.CallBlock | pb.CallAction):
            return
        if isinstance(message, pb.LValue):
            if message.WhichOneof("kind") == "index":
                reads(message.index.index, scope)
                reads(message.index.base, scope)
            elif message.WhichOneof("kind") == "member":
                reads(message.member.base, scope)
            return
        if isinstance(message, pb.Expr):
            path = alias(message, scope)
            if path is not None:
                accessed = protected if not path else ({path[0]} & protected)
                if unavailable := accessed - READABLE[role]:
                    raise LoadError(
                        f"{role}: standard metadata {', '.join(sorted(unavailable))} is unavailable"
                    )
                return
        for descriptor, value in message.ListFields():
            if descriptor.message_type is not None:
                if isinstance(value, Message):
                    reads(value, scope)
                else:
                    for item in value:
                        reads(item, scope)

    def arguments(
        params: Iterable[pb.Param], args: Iterable[pb.Arg], scope: dict[str, tuple[str, ...]]
    ) -> dict[str, tuple[str, ...]]:
        result: dict[str, tuple[str, ...]] = {}
        for param, arg in zip(params, args, strict=True):
            if arg.WhichOneof("kind") == "lvalue":
                path = alias(arg.lvalue, scope)
            else:
                path = alias(arg.expr, scope)
            if path is not None:
                if param.direction == pb.DIRECTION_OUT:
                    written(path)
                result[param.name] = path
            elif arg.WhichOneof("kind") == "expr":
                reads(arg.expr, scope)
        return result

    def statements(
        stmts: Iterable[pb.Stmt], scope: dict[str, tuple[str, ...]], actions: set[str]
    ) -> None:
        for stmt in walk(stmts):
            reads(stmt, scope)
            kind = stmt.WhichOneof("kind")
            if kind == "assign":
                written(alias(stmt.assign.target, scope))
            elif kind == "apply" and stmt.apply.HasField("hit"):
                written(alias(stmt.apply.hit, scope))
            elif kind == "call_block":
                call = stmt.call_block
                if call.block in {export.block for export in index.bindings.exports}:
                    raise LoadError("v1model stage blocks cannot also be called as sub-blocks")
                callee = index.blocks[call.block]
                nested = arguments(callee.params, call.args, scope)
                _check_block(index, callee, role, nested, protected, active)
            elif kind == "call_action":
                call = stmt.call_action
                action = next(a for a in block.actions if a.name == call.action)
                if action.name in actions:
                    raise LoadError("recursive v1model action invocation")
                nested = {
                    k: v for k, v in scope.items() if k not in {p.name for p in action.params}
                }
                nested.update(arguments(action.params, call.args, scope))
                statements(action.body, nested, actions | {action.name})
            elif kind == "call_extern":
                call = stmt.call_extern
                instance = index.extern_instances[call.instance]
                decl = index.extern_types[instance.extern_type]
                method = next(m for m in decl.methods if m.name == call.method)
                mapped = arguments(method.params, call.args, scope)
                for param in method.params:
                    if param.direction in (pb.DIRECTION_OUT, pb.DIRECTION_INOUT):
                        written(mapped.get(param.name))
                if call.HasField("result"):
                    written(alias(call.result, scope))
        # Table actions can be selected by host entries, not just direct calls.

    statements(block.body, aliases, set())
    for state in block.states:
        statements(state.body, aliases, set())
        reads(state.transition, aliases)
    for table in block.tables:
        for key in table.keys:
            reads(key.expr, aliases)
    for action in block.actions:
        nested = {k: v for k, v in aliases.items() if k not in {p.name for p in action.params}}
        statements(action.body, nested, {action.name})


class V1Model:
    """Single-pass unicast v1model, over configured ports 0 through ports-1."""

    def __init__(self, ports: int) -> None:
        if not 1 <= ports <= DROP_PORT:
            raise ValueError("v1model ports must be between 1 and 511")
        self.ports = ports
        self.diagnostics: list[str] = []

    def run(
        self, loaded: Loaded, entries: InstalledEntries, ingress_port: int, packet: bytes
    ) -> list[tuple[int, bytes]]:
        if not 0 <= ingress_port < self.ports:
            raise ValueError(f"ingress_port {ingress_port} is not a configured v1model port")
        index, externs, meta = loaded.index, loaded.externs, loaded.metadata
        m = meta.zero()
        meta.write(m, "ingress_port", ingress_port)
        parsed = entry.run_parser(index, loaded.block("parser"), packet, m, externs)
        if parsed.consumed_bits % 8:
            self.diagnostics.append(
                f"parser consumed {parsed.consumed_bits} bits, not whole bytes; packet dropped"
            )
            return []
        h, m = parsed.headers, parsed.metadata
        meta.write(m, "parser_error", parsed.error)
        for role in ("verify_checksum", "ingress"):
            if role in loaded.blocks:
                h, m = entry.run_control(index, loaded.block(role), h, m, entries, externs)
        selected = meta.number(m, "egress_spec")
        if selected == DROP_PORT:
            return []
        if selected >= self.ports:
            self.diagnostics.append(f"egress_spec {selected} is not a configured v1model port")
            return []
        meta.write(m, "egress_port", selected)
        if "egress" in loaded.blocks:
            h, m = entry.run_control(index, loaded.block("egress"), h, m, entries, externs)
        if meta.number(m, "egress_spec") == DROP_PORT:
            return []
        if "compute_checksum" in loaded.blocks:
            h, m = entry.run_control(
                index, loaded.block("compute_checksum"), h, m, entries, externs
            )
        emitted = entry.run_deparser(index, loaded.block("deparser"), h, externs)
        return [(selected, emitted + packet[parsed.consumed_bits // 8 :])]
