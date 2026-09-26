"""Translate a scoped native V1Switch program into six independent core blocks.

Standard metadata uses the adapter's reserved flat fields. User fields with
those names are renamed so that their semantics remain distinct. Unsupported
native fields and functions fail explicitly; stages are never fused.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.arch.v1model_profile import FORBIDDEN_FIELDS, READABLE
from p4blo.frontend import il
from p4blo.frontend.blocks import Architecture, BlockCx
from p4blo.frontend.common import (
    ERROR,
    Bits,
    EnumVal,
    Excluded,
    ExternInstB,
    FrontendError,
    Int,
    IntrinsicB,
    NotTranslated,
    ParamIL,
    assign,
    binary,
    bits_type,
    lit_bits,
    lmember,
    lvalue_to_expr,
    member,
    prefixed_name,
    strip_alias,
    typed_parts,
    var,
)
from p4blo.frontend.il import Node
from p4blo.frontend.spectec_il import Translator
from p4blo.v0 import p4blo_pb2 as pb

__all__ = ["V1Model", "bind"]

V1SWITCH = "V1Switch"
STANDARD_METADATA = "standard_metadata_t"
DROP_PORT = 511
CONTRACT: dict[str, pb.Type] = {
    "ingress_port": bits_type(9),
    "parser_error": ERROR,
    "egress_spec": bits_type(9),
    "egress_port": bits_type(9),
}
# Where V1Switch's blocks take M: the parser third, `(packet_in, out H,
# inout M, inout standard_metadata_t)`, and the four controls second.
PARSER_META_INDEX = 2
CONTROL_META_INDEX = 1
# Keep user fields distinct from supported and explicitly unsupported native fields.
CONTRACT_NAMES = frozenset(CONTRACT) | FORBIDDEN_FIELDS
# v1model.p4's extern objects and functions, which the architecture owns.
V1MODEL_OBJECTS = frozenset(
    {
        "counter",
        "direct_counter",
        "meter",
        "direct_meter",
        "register",
        "action_profile",
        "action_selector",
        "Checksum16",
    }
)
HASH_FAMILIES = {
    "csum16": ("checksum16", 16, "csum"),
    "crc16": ("crc16", 16, "hash16"),
    "crc32": ("crc32", 32, "hash32"),
}


@dataclass
class _Roles:
    parser: tuple[Node, list[Node]]
    verify: tuple[Node, list[Node]]
    ingress: tuple[Node, list[Node]]
    egress: tuple[Node, list[Node]]
    compute: tuple[Node, list[Node]]
    deparser: tuple[Node, list[Node]]


@dataclass
class V1Model(Architecture):
    """The v1model binding of one translation."""

    tr: Translator
    contract: set[str] = field(default_factory=set)
    hash_instances: dict[str, str] = field(default_factory=dict)
    # Contract name -> the IR name of the user field of M that had it.
    renamed: dict[str, str] = field(default_factory=dict)

    # -- metadata

    def metadata_read(self, cx: BlockCx, fieldname: str) -> pb.Expr:
        role = "parser" if cx.kind == "parser" else cx.part
        if fieldname not in READABLE.get(role, set()):
            raise Excluded(
                "standard_metadata and other intrinsic metadata parameters",
                "by thesis",
                f"standard_metadata.{fieldname} is unavailable in {role}",
            )
        return self._contract(cx, fieldname)

    def metadata_write(self, cx: BlockCx, fieldname: str, value: pb.Expr) -> list[pb.Stmt]:
        if (
            fieldname != "egress_spec"
            or cx.kind != "control"
            or cx.part not in {"ingress", "egress"}
        ):
            raise Excluded(
                "standard_metadata and other intrinsic metadata parameters",
                "by thesis",
                f"a write to standard_metadata.{fieldname} in {cx.part}",
            )
        return [assign(_as_lvalue(self._contract(cx, "egress_spec")), value)]

    def _contract(self, cx: BlockCx, name: str) -> pb.Expr:
        if cx.meta is None:
            raise Excluded(
                "standard_metadata and other intrinsic metadata parameters",
                "by thesis",
                f"{cx.block.name} has no metadata parameter to carry {name}",
            )
        self.contract.add(name)
        return member(var(cx.meta), name)

    # -- extern functions

    def extern_function(
        self, cx: BlockCx, name: str, targs: list[Node], args: list[Node]
    ) -> list[pb.Stmt]:
        match name:
            case "mark_to_drop" if len(args) == 1:
                self._intrinsic_arg(cx, args[0])
                return self.metadata_write(cx, "egress_spec", lit_bits(9, DROP_PORT))
            case "hash":
                return self._hash(cx, args)
            case "update_checksum":
                return self._update_checksum(cx, args)
            case "verify_checksum":
                raise Excluded(
                    "externFunctionDeclarationIR: an architecture's functions",
                    "by thesis",
                    "verify_checksum requires unsupported checksum_error metadata",
                )
        raise Excluded(
            "externFunctionDeclarationIR: an architecture's functions", "by thesis", name
        )

    def _intrinsic_arg(self, cx: BlockCx, te: Node) -> None:
        e, _, _ = typed_parts(te)
        if e.c == "_BARE %" and isinstance(cx.scope.lookup(e.text(0)), IntrinsicB):
            return
        raise NotTranslated(
            "callStatementIR", "mark_to_drop on something other than standard_metadata"
        )

    def _algorithm(self, cx: BlockCx, te: Node) -> str:
        v = cx.fold(te)
        if not isinstance(v, EnumVal) or v.enum_type != "HashAlgorithm":
            raise NotTranslated("callStatementIR", "a hash algorithm not known at compile time")
        if v.member not in HASH_FAMILIES:
            raise Excluded(
                "externFunctionDeclarationIR: an architecture's functions",
                "by thesis",
                f"HashAlgorithm.{v.member} has no extern family",
            )
        return v.member

    def _data(self, cx: BlockCx, te: Node) -> tuple[pb.Expr, int]:
        """A hash's data: a list is the concatenation of its fields, in order."""
        e, t, _ = typed_parts(te)
        while e.c == "(%) %" and strip_alias(e.node(0)).c in ("TUPLE <%>", "LIST <%>"):
            te = e.node(1)
            e, t, _ = typed_parts(te)
        if e.c in ("SEQ {%}",):
            parts = e.nodes(0)
            if not parts:
                raise NotTranslated("sequenceExpressionIR as an extern argument", "an empty list")
            out = cx.expr(parts[0])
            width = cx.width_of(typed_parts(parts[0])[1])
            for p in parts[1:]:
                out = binary(pb.BINARY_OP_CONCAT, out, cx.expr(p))
                width += cx.width_of(typed_parts(p)[1])
            return out, width
        return cx.expr(te), cx.width_of(t)

    def _family_instance(self, algorithm: str, data_width: int) -> tuple[str, int]:
        family, width, instance = HASH_FAMILIES[algorithm]
        decl = pb.ExternType(
            name=family,
            methods=[
                pb.Method(
                    name="compute",
                    params=[
                        pb.Param(name="data", type=bits_type(data_width), direction=pb.DIRECTION_IN)
                    ],
                    returns=bits_type(width),
                )
            ],
        )
        type_name = self.tr.add_extern_type(decl)
        if type_name not in self.hash_instances:
            self.hash_instances[type_name] = self.tr.add_extern_instance(instance, type_name, [])
        return self.hash_instances[type_name], width

    def _hash(self, cx: BlockCx, args: list[Node]) -> list[pb.Stmt]:
        if len(args) != 5:
            raise NotTranslated("callStatementIR", "hash with other than five arguments")
        result_te, algo_te, base_te, data_te, max_te = args
        algorithm = self._algorithm(cx, algo_te)
        data, data_width = self._data(cx, data_te)
        instance, width = self._family_instance(algorithm, data_width)
        target = cx.lvalue_of_expr(result_te)
        rwidth = cx.width_of(typed_parts(result_te)[1])
        base = cx.fold(base_te)
        maximum = cx.fold(max_te)
        if not isinstance(base, Bits | Int) or not isinstance(maximum, Bits | Int):
            raise NotTranslated(
                "callStatementIR", "hash with a base or max not known at compile time"
            )
        m = maximum.value
        if m == 0 or m & (m - 1):
            raise NotTranslated("callStatementIR", f"hash with max {m}, not a power of two")
        call = pb.CallExtern(instance=instance, method="compute", args=[pb.Arg(expr=data)])
        if rwidth == width:
            # The result goes straight into the target, which is then
            # reduced in place: `data` has been read by then.
            call.result.CopyFrom(target)
            out = [pb.Stmt(call_extern=call)]
            value = lvalue_to_expr(target)
        else:
            family = HASH_FAMILIES[algorithm][0]
            tmp = cx.add_local(f"{family}_result", bits_type(width))
            call.result.CopyFrom(pb.LValue(var=tmp))
            out = [pb.Stmt(call_extern=call)]
            value = var(tmp)
        reduced = value
        if m < (1 << width):
            reduced = binary(pb.BINARY_OP_BIT_AND, reduced, lit_bits(width, m - 1))
        if rwidth != width:
            reduced = pb.Expr(cast=pb.Cast(to=bits_type(rwidth), operand=reduced))
        if base.value % (1 << rwidth):
            reduced = binary(
                pb.BINARY_OP_ADD, reduced, lit_bits(rwidth, base.value % (1 << rwidth))
            )
        if reduced is not value:
            out.append(assign(target, reduced))
        return out

    def _update_checksum(self, cx: BlockCx, args: list[Node]) -> list[pb.Stmt]:
        if len(args) != 4:
            raise NotTranslated("callStatementIR", "update_checksum with other than four arguments")
        cond_te, data_te, checksum_te, algo_te = args
        if self._algorithm(cx, algo_te) != "csum16":
            raise Excluded(
                "externFunctionDeclarationIR: an architecture's functions",
                "by thesis",
                "update_checksum with an algorithm other than csum16",
            )
        data, data_width = self._data(cx, data_te)
        instance, _ = self._family_instance("csum16", data_width)
        target = cx.lvalue_of_expr(checksum_te)
        if cx.width_of(typed_parts(checksum_te)[1]) != 16:
            raise NotTranslated(
                "callStatementIR", "update_checksum into a field that is not bit<16>"
            )
        call = pb.Stmt(
            call_extern=pb.CallExtern(
                instance=instance, method="compute", args=[pb.Arg(expr=data)], result=target
            )
        )
        cond = cx.fold(cond_te)
        if cond is True:
            return [call]
        if cond is False:
            return []
        return [pb.Stmt(conditional=pb.If(condition=cx.expr(cond_te), then=[call]))]

    # -- extern objects

    def extern_object(
        self, cx: BlockCx | None, inst_name: str, t: Node, args: list[Node]
    ) -> ExternInstB:
        family = t.text(0)
        targs = t.nodes(1)
        folder = cx if cx is not None else _GlobalFolder(self.tr)
        if family == "register":
            if not targs or len(targs) > 2:
                raise NotTranslated(
                    "instantiationIR of an extern object", "register without its type"
                )
            value_t = self.tr.type_of(targs[0], inst_name)
            if value_t.WhichOneof("kind") != "bits":
                raise NotTranslated("instantiationIR of an extern object", "a register of non-bits")
            if len(targs) == 2 and strip_alias(targs[1]).c != "BIT <%>":
                raise NotTranslated(
                    "instantiationIR of an extern object", "a register index not bits"
                )
            if len(targs) == 2 and strip_alias(targs[1]).num(0) != 32:
                raise NotTranslated(
                    "instantiationIR of an extern object", "a register index not bit<32>"
                )
            if len(args) != 1:
                raise NotTranslated(
                    "instantiationIR of an extern object", "register with an initial value"
                )
            size = folder.literal(args[0], bits_type(32))
            decl = pb.ExternType(
                name="register",
                constructor_params=[
                    pb.Param(name="size", type=bits_type(32), direction=pb.DIRECTION_IN)
                ],
                methods=[
                    pb.Method(
                        name="read",
                        params=[
                            pb.Param(name="result", type=value_t, direction=pb.DIRECTION_OUT),
                            pb.Param(name="index", type=bits_type(32), direction=pb.DIRECTION_IN),
                        ],
                    ),
                    pb.Method(
                        name="write",
                        params=[
                            pb.Param(name="index", type=bits_type(32), direction=pb.DIRECTION_IN),
                            pb.Param(name="value", type=value_t, direction=pb.DIRECTION_IN),
                        ],
                    ),
                ],
            )
            type_name = self.tr.add_extern_type(decl)
            return ExternInstB(self.tr.add_extern_instance(inst_name, type_name, [size]), type_name)
        if family == "counter":
            if len(args) != 2:
                raise NotTranslated("instantiationIR of an extern object", "counter arguments")
            kind = folder.fold(args[1])
            if not (isinstance(kind, EnumVal) and kind.member == "packets"):
                raise NotTranslated(
                    "instantiationIR of an extern object",
                    "a counter of bytes; the counter family counts packets",
                )
            if targs and (
                strip_alias(targs[0]).c != "BIT <%>" or strip_alias(targs[0]).num(0) != 32
            ):
                raise NotTranslated(
                    "instantiationIR of an extern object", "a counter index not bit<32>"
                )
            size = folder.literal(args[0], bits_type(32))
            decl = pb.ExternType(
                name="counter",
                constructor_params=[
                    pb.Param(name="size", type=bits_type(32), direction=pb.DIRECTION_IN)
                ],
                methods=[
                    pb.Method(
                        name="count",
                        params=[
                            pb.Param(name="index", type=bits_type(32), direction=pb.DIRECTION_IN)
                        ],
                    )
                ],
            )
            type_name = self.tr.add_extern_type(decl)
            return ExternInstB(self.tr.add_extern_instance(inst_name, type_name, [size]), type_name)
        if family in V1MODEL_OBJECTS:
            # The IR has extern types; p4blo's architectures bind no family
            # for this one.
            raise NotTranslated(
                "instantiationIR of an extern object", f"v1model's {family} has no extern family"
            )
        raise NotTranslated(
            "externObjectDeclarationIR", f"{family}: extern objects outside v1model's families"
        )

    def is_intrinsic(self, t: Node) -> bool:
        t = strip_alias(t)
        return t.c == "STRUCT % <%> {%}" and t.text(0) == STANDARD_METADATA


class _GlobalFolder:
    """Constant folding at program level, for top-level instantiations."""

    def __init__(self, tr: Translator) -> None:
        self.cx = BlockCx(tr, Node("", "", ()), "__global__", "control", tr.global_scope)

    def fold(self, te: Node):  # noqa: ANN201
        return self.cx.fold(te)

    def literal(self, te: Node, t: pb.Type) -> pb.Literal:
        return self.cx.literal(te, t)


def _as_lvalue(e: pb.Expr) -> pb.LValue:
    return lmember(pb.LValue(var=e.member.base.var), e.member.field)


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------


def _package(tr: Translator) -> tuple[Node, list[Node]]:
    for d in tr.decls:
        if d.t == "instantiationIR" and d.text(4) == "main":
            t = strip_alias(d.node(1))
            if t.c != "PACKAGE % <%> {%}":
                raise NotTranslated("instantiationIR", "main is not a package")
            if t.text(0) != V1SWITCH:
                raise Excluded(
                    "instantiationIR of a package (main)",
                    "by thesis",
                    f"{t.text(0)}; only V1Switch is supported",
                )
            return d, d.nodes(3)
    raise FrontendError("the program instantiates no package named main")


def _constructor(tr: Translator, te: Node) -> tuple[Node, list[Node]]:
    e, _, _ = typed_parts(te)
    if e.c != "% (%)":
        raise NotTranslated("instantiationIR", "a package argument that is not a constructor call")
    target = e.node(0)
    if target.list(1):
        raise Excluded(
            "typeArgumentIR, type arguments on STRUCT, HEADER, EXTERN, PARSER, CONTROL",
            "by elaboration",
        )
    name, _ = prefixed_name(target.node(0))
    decl = tr.block_decls.get(name)
    if decl is None:
        raise NotTranslated("instantiationIR", f"{name} is not a parser or control")
    return decl, e.nodes(1)


def bind(tr: Translator) -> apb.BlockAssembly:
    """Translate a V1Switch program into IR."""
    arch = V1Model(tr)
    tr.arch = arch
    _, args = _package(tr)
    if len(args) != 6:
        raise NotTranslated("instantiationIR", f"V1Switch with {len(args)} arguments")
    roles = _Roles(*[_constructor(tr, a) for a in args])
    # Top-level extern instances, which every block may use.
    for d in tr.decls:
        if d.t == "instantiationIR" and d.text(4) != "main":
            t = strip_alias(d.node(1))
            if t.c == "EXTERN % <%> %":
                if d.opt(5) is not None:
                    raise Excluded(
                        "objectInitializerIR, ABSTRACT in externMethodPrototypeIR", "by scope"
                    )
                tr.global_scope.bind(d.text(4), arch.extern_object(None, d.text(4), t, d.nodes(3)))
            elif t.c in ("PARSER % <%> (%)", "CONTROL % <%> (%)"):
                raise NotTranslated(
                    "instantiationIR", "a parser or control instantiated at top level"
                )

    _rename_user_contract_fields(tr, arch, roles.parser[0])
    parser = tr.role_block(roles.parser[0], roles.parser[1], "parser", "parser", PARSER_META_INDEX)
    parts = []
    for part, (decl, cargs) in (
        ("verify_checksum", roles.verify),
        ("ingress", roles.ingress),
        ("egress", roles.egress),
        ("compute_checksum", roles.compute),
    ):
        parts.append((part, tr.role_block(decl, cargs, "control", part, CONTROL_META_INDEX)))
    deparser = tr.role_block(roles.deparser[0], roles.deparser[1], "deparser", "deparser", None)

    headers_t = _param_type(roles.parser[0], 1)
    meta_t = _param_type(roles.parser[0], 2)
    headers = tr.type_of(headers_t).struct
    metadata = tr.type_of(meta_t).struct
    _extend_metadata(tr, arch, metadata)
    exports = [
        ("parser", parser.name),
        *((role, block.name) for role, block in parts),
        ("deparser", deparser.name),
    ]
    blocks = tr.ordered_blocks([name for _, name in exports])
    return tr.assemble(blocks, headers, metadata, exports)


def _rename_user_contract_fields(tr: Translator, arch: V1Model, parser: Node) -> None:
    """Keep ordinary user metadata distinct from reserved adapter fields."""
    meta_t = strip_alias(_param_type(parser, 2))
    if meta_t.c != "STRUCT % <%> {%}":
        return
    every_field = {
        f.text(2)
        for d in tr.decls
        for n in il.walk(d)
        if n.c in ("HEADER % <%> {%}", "STRUCT % <%> {%}")
        for f in n.nodes(2)
    }
    names = [f.text(2) for f in meta_t.nodes(2)]
    for name in names:
        if name not in CONTRACT_NAMES:
            continue
        new, i = f"{name}_", 0
        while new in every_field:
            new = f"{name}_{i}"
            i += 1
        every_field.add(new)
        tr.field_renames[(meta_t.text(0), name)] = new
        arch.renamed[name] = new
        tr.notes.append(
            f"{meta_t.text(0)}.{name} renamed {new}: user metadata, not the contract field"
        )


def _param_type(decl: Node, i: int) -> Node:
    return ParamIL.of(decl.nodes(4)[i]).type


def _extend_metadata(tr: Translator, arch: V1Model, metadata: str) -> None:
    struct = tr.struct_types[metadata]
    have = {f.name: f.type for f in struct.fields}
    for name in CONTRACT:
        if name not in arch.contract:
            continue
        if name in have:
            if have[name] != CONTRACT[name]:
                raise FrontendError(
                    f"{metadata}.{name} has the wrong type for the metadata contract"
                )
            continue
        struct.fields.append(pb.Field(name=name, type=CONTRACT[name]))
