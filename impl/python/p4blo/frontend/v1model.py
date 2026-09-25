"""The v1model shim in reverse: a V1Switch program bound to p4blo's roles.

`p4blo.arch.v1model` prints an IR program inside a v1model shim: the
metadata contract becomes `standard_metadata`, the checksum and egress
controls are added empty, and the three exported blocks fill V1Switch's
parser, ingress and deparser slots. This module undoes exactly that for a
program P4-SpecTec has typed and instantiated, and states what it does with
everything else V1Switch has:

- **Roles.** The parser is V1Switch's parser, the deparser its deparser,
  and the control is its verify-checksum, ingress, egress and
  compute-checksum controls merged into one, in that order, parameters
  renamed to the ingress control's. Nothing between them is observable
  under the contract except the drop decision, which the merge makes
  explicit: v1model drops after ingress when `egress_spec` is 511, so
  where ingress writes it an egress part is preceded by `M.drop =
  (M.egress_port == 511)`, and it runs only when the packet is not
  dropped. With no egress part the decision
  needs no statement: 511 is no port of p4blo's switch, which drops what
  is sent there.
- **`standard_metadata`.** Each field maps onto a contract field of the
  program's `M` (docs/design.md, "Metadata contract"), added to `M` when
  the source uses it:

  | v1model                           | IR                                          |
  |-----------------------------------|---------------------------------------------|
  | read `ingress_port`               | `M.ingress_port`                            |
  | read `parser_error` in a control  | `M.parser_error`                            |
  | `egress_spec = e` in ingress      | `M.egress_port = e`                         |
  | read `egress_spec` before egress  | `M.egress_port`                             |
  | read `egress_spec` in egress      | `M.drop ? 511 : M.egress_port`              |
  | read `egress_port` in egress      | `M.egress_port`                             |
  | `mark_to_drop(sm)` in ingress     | `M.egress_port = 511`                       |
  | `mark_to_drop(sm)` in egress      | `M.drop = true`                             |

  This is v1model's own rule, so a source that writes a real port after
  `mark_to_drop` forwards, and one that writes 511 drops and skips egress,
  as in v1model. A field of `M` named like a contract field is user
  metadata and is renamed, unless the source copies it to or from
  `standard_metadata` exactly as the printer's shim does (`_Fusion`).
  Any other field of `standard_metadata` is excluded by thesis.
- **Extern functions.** `mark_to_drop` as above. `hash` with `csum16`,
  `crc16` or `crc32` calls a `checksum16`, `crc16` or `crc32` instance
  (`csum`, `hash16`, `hash32`) on the concatenated data, then applies
  v1model's `base + result % max` for a power-of-two `max`.
  `update_checksum` with `csum16` is a conditional `checksum16` call.
  `verify_checksum` is left out: it only sets
  `standard_metadata.checksum_error`, and a program that reads that field
  is refused where it reads it. Every other v1model function is excluded
  by thesis.
- **Extern objects.** `register<T>(size)` is the `register` family with
  `T`'s width and `counter(size, CounterType.packets)` the `counter`
  family; every other v1model object is excluded by thesis.

This inverts the printer's `standard_metadata_binding` and extern
placement: a printed program translates back to the program printed.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass, field

from google.protobuf.message import Message

from p4blo import ir
from p4blo.frontend import il
from p4blo.frontend.blocks import Architecture, BlockCx
from p4blo.frontend.common import (
    BOOL,
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
    lit_bool,
    lmember,
    lvalue_to_expr,
    member,
    prefixed_name,
    rename_block_vars,
    strip_alias,
    typed_parts,
    unary,
    var,
    walk_stmts,
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
    "egress_port": bits_type(9),
    "drop": BOOL,
}
# Every name the architectures read or write in M (p4blo.arch.contract),
# `flood` included although v1model has no counterpart for it.
CONTRACT_NAMES = frozenset({*CONTRACT, "flood"})
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
    # Whether verify or ingress writes egress_spec, so that v1model's drop
    # decision has to be computed at the end of ingress.
    egress_written: bool = False

    # -- metadata

    def metadata_read(self, cx: BlockCx, fieldname: str) -> pb.Expr:
        match fieldname:
            case "ingress_port":
                return self._contract(cx, "ingress_port")
            case "parser_error":
                if cx.kind != "control":
                    raise Excluded(
                        "standard_metadata and other intrinsic metadata parameters",
                        "by thesis",
                        "parser_error read in a parser, before the parser has one",
                    )
                return self._contract(cx, "parser_error")
            case "egress_spec" | "egress_port":
                if fieldname == "egress_port" and cx.part != "egress":
                    raise Excluded(
                        "standard_metadata and other intrinsic metadata parameters",
                        "by thesis",
                        "egress_port read before egress",
                    )
                port = self._contract(cx, "egress_port")
                if fieldname == "egress_spec" and cx.part == "egress":
                    # Egress starts with egress_spec equal to egress_port and
                    # not dropped; only mark_to_drop changes egress_spec
                    # there, to 511, and it is what sets `drop` in egress.
                    drop = self._contract(cx, "drop")
                    return pb.Expr(
                        mux=pb.Mux(condition=drop, then=lit_bits(9, DROP_PORT), otherwise=port)
                    )
                return port
        raise Excluded(
            "standard_metadata and other intrinsic metadata parameters",
            "by thesis",
            f"standard_metadata.{fieldname} has no contract field",
        )

    def metadata_write(self, cx: BlockCx, fieldname: str, value: pb.Expr) -> list[pb.Stmt]:
        if fieldname != "egress_spec" or cx.kind != "control" or cx.part == "egress":
            raise Excluded(
                "standard_metadata and other intrinsic metadata parameters",
                "by thesis",
                f"a write to standard_metadata.{fieldname} in {cx.part}",
            )
        target = self._contract(cx, "egress_port")
        self.egress_written = True
        return [assign(_as_lvalue(target), value)]

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
                if cx.part == "egress":
                    # Egress drops when egress_spec is 511 at its end, and
                    # only mark_to_drop can make it so there.
                    return [assign(_as_lvalue(self._contract(cx, "drop")), lit_bool(True))]
                # v1model's mark_to_drop writes the drop port to egress_spec
                # and nothing else; the drop is decided from egress_spec at
                # the end of ingress (`_merge`), so a later write undoes it.
                self.egress_written = True
                port = self._contract(cx, "egress_port")
                return [assign(_as_lvalue(port), lit_bits(9, DROP_PORT))]
            case "hash":
                return self._hash(cx, args)
            case "update_checksum":
                return self._update_checksum(cx, args)
            case "verify_checksum":
                self.tr.notes.append(
                    f"{cx.block.name}: verify_checksum left out; it only sets "
                    "standard_metadata.checksum_error, which the program does not read"
                )
                return []
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
                    f"{t.text(0)}; only V1Switch has a reverse shim",
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


def bind(tr: Translator) -> pb.Program:
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
    parser = tr.role_block(roles.parser[0], roles.parser[1], "parser", "ingress")
    parts = []
    for part, (decl, cargs) in (
        ("verify", roles.verify),
        ("ingress", roles.ingress),
        ("egress", roles.egress),
        ("compute", roles.compute),
    ):
        parts.append((part, tr.role_block(decl, cargs, "control", part)))
    deparser = tr.role_block(roles.deparser[0], roles.deparser[1], "deparser", "ingress")
    control, tail_only = _merge(tr, arch, parts)

    headers_t = _param_type(roles.parser[0], 1)
    meta_t = _param_type(roles.parser[0], 2)
    headers = tr.type_of(headers_t).struct
    metadata = tr.type_of(meta_t).struct
    _Fusion(tr, arch, metadata, parser, control, tail_only).run()
    _extend_metadata(tr, arch, metadata)
    blocks = tr.ordered_blocks([parser.name, control.name, deparser.name])
    return tr.assemble(
        blocks,
        headers,
        metadata,
        [("parser", parser.name), ("control", control.name), ("deparser", deparser.name)],
    )


def _rename_user_contract_fields(tr: Translator, arch: V1Model, parser: Node) -> None:
    """A field of `M` named like a contract field is user metadata: in
    v1model it is not standard_metadata, and left as it is the architecture
    would read or overwrite it. It is renamed, to a name no field of any
    type has, so that `_Fusion` can find it again by name alone. Only
    `_Fusion` gives a field its contract name back, when the source keeps
    the two exactly synchronized."""
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


def _merge(
    tr: Translator, arch: V1Model, parts: Sequence[tuple[str, pb.Block]]
) -> tuple[pb.Block, bool]:
    """V1Switch's four controls as one block, named and parameterized as
    the ingress control, and whether nothing follows the ingress part.

    v1model drops the packet after ingress when `egress_spec` is 511, which
    the IR's `egress_port` stands for, and then skips egress. When there is
    an egress part and verify or ingress writes `egress_spec`, that decision
    is written out after the ingress part, `drop = (egress_port == 511)`,
    and the egress part runs only when the packet is not dropped. Without
    an egress part the rule would decide nothing: 511 is no port of
    p4blo's switch (`p4blo.arch.switch`), which drops what is sent there."""
    ingress = next(b for p, b in parts if p == "ingress")
    merged = copy.deepcopy(ingress)
    del merged.body[:]
    taken = {v.name for v in [*merged.params, *merged.locals]}
    taken |= {a.name for a in merged.actions} | {t.name for t in merged.tables}
    bodies: dict[str, list[pb.Stmt]] = {}
    for part, block in parts:
        if part == "ingress":
            bodies[part] = list(ingress.body)
            continue
        if not (block.body or block.locals or block.actions or block.tables):
            tr.blocks.pop(block.name, None)
            continue
        block = copy.deepcopy(block)
        mapping = {p.name: merged.params[i].name for i, p in enumerate(block.params)}
        for v in block.locals:
            new = v.name
            i = 0
            while new in taken:
                new = f"{v.name}_{i}"
                i += 1
            if new != v.name:
                mapping[v.name] = new
                tr.notes.append(
                    f"{block.name}: local {v.name} renamed {new} on merging into {merged.name}"
                )
        rename_block_vars(block, mapping)
        for a in block.actions:
            if a.name in taken:
                raise NotTranslated(
                    "controlDeclarationIR", f"{block.name}.{a.name} clashes on merging"
                )
            taken.add(a.name)
        for t in block.tables:
            if t.name in taken:
                raise NotTranslated(
                    "controlDeclarationIR", f"{block.name}.{t.name} clashes on merging"
                )
            taken.add(t.name)
        for v in block.locals:
            taken.add(v.name)
        merged.locals.extend(block.locals)
        merged.actions.extend(block.actions)
        merged.tables.extend(block.tables)
        bodies[part] = list(block.body)
        tr.blocks.pop(block.name, None)
        tr.notes.append(f"{block.name} merged into {merged.name} as its {part} part")
    body: list[pb.Stmt] = []
    body += bodies.get("verify", [])
    body += bodies.get("ingress", [])
    meta = merged.params[1].name if len(merged.params) > 1 else None
    egress = bodies.get("egress", [])
    if egress and arch.egress_written:
        # Only verify and ingress can write egress_spec, so a meta
        # parameter exists here.
        assert meta is not None
        arch.contract.add("drop")
        body.append(_drop_rule(meta))
    if egress:
        if "drop" in arch.contract and meta is not None:
            guard = unary(pb.UNARY_OP_NOT, member(var(meta), "drop"))
            body.append(pb.Stmt(conditional=pb.If(condition=guard, then=egress)))
        else:
            body += egress
    body += bodies.get("compute", [])
    merged.body.extend(body)
    tr.blocks[merged.name] = merged
    return merged, not egress and not bodies.get("compute")


def _drop_rule(meta: str) -> pb.Stmt:
    """`meta.drop = (meta.egress_port == 511)`: v1model's drop decision."""
    port = member(var(meta), "egress_port")
    is_drop_port = binary(pb.BINARY_OP_EQ, port, lit_bits(9, DROP_PORT))
    return assign(_as_lvalue(member(var(meta), "drop")), is_drop_port)


class _Fusion:
    """Give renamed user fields of M their contract names back where the
    source keeps them synchronized with standard_metadata exactly as the
    printer's shim does (`p4blo.arch.v1model.standard_metadata_binding`),
    so that a printed program reads back as printed. Each step is taken only
    when the whole translated program shows that no execution can tell the
    two apart; otherwise the field stays renamed and the copies stay.

    - `ingress_port`, `parser_error`, which the architecture provides: the
      user field is written only by copies `M.f_ = M.f` from the contract
      field, nothing writes M whole or as an `out` argument, and a copy runs
      before anything reads the user field: the first statement of the
      parser's start state for `ingress_port`; one of the copies that open
      the merged control for `parser_error`, which no parser then reads. The
      user field always equals the contract field then, which nothing
      writes.
    - `egress_port`, which the architecture consumes: nothing follows the
      ingress part, whose end is `M.egress_port = M.egress_port_`, perhaps
      followed by the translated drop epilogue, and nothing else in the
      program mentions the contract field. The user field holds at the end
      what the copy would have put there.
    - `drop`: nothing follows the ingress part, which ends in `if (M.drop_)
      { M.egress_port = 511; }`, and nothing mentions a contract `drop`. The
      statement sends the packet to 511 when the flag is set; it is removed
      and the flag becomes the contract's `drop`, which drops the packet
      instead. The two agree because 511 is no port of p4blo's switch
      (`p4blo.arch.switch`), which drops what is sent there; the printer's
      epilogue relies on the same.
    """

    def __init__(
        self,
        tr: Translator,
        arch: V1Model,
        metadata: str,
        parser: pb.Block,
        control: pb.Block,
        tail_only: bool,
    ) -> None:
        self.tr = tr
        self.arch = arch
        self.metadata = metadata
        self.parser = parser
        self.control = control
        self.tail_only = tail_only
        self.blocks = list(tr.blocks.values())

    def run(self) -> None:
        if not self.arch.renamed or self.metadata not in self.tr.struct_types:
            return
        self._provided("ingress_port")
        self._provided("parser_error")
        if self.tail_only:
            self._consumed()

    # -- the steps

    def _provided(self, name: str) -> None:
        user = self._user(name)
        if user is None:
            return
        copies = [s for s in self._statements() if self._is_copy(s, user, name)]
        if not copies or self._refs(user)[1] != len(copies) or self._refs(name)[1]:
            return
        if self._m_written_whole():
            return
        if name == "ingress_port":
            start = next((s for s in self.parser.states if s.name == self.parser.start_state), None)
            if start is None or not start.body or not self._is_copy(start.body[0], user, name):
                return
        else:
            opening: list[pb.Stmt] = []
            for s in self.control.body:
                # A copy of a field already given its name back is `X.f = X.f`.
                if not any(self._is_copy(s, self.arch.renamed.get(f, f), f) for f in CONTRACT):
                    break
                opening.append(s)
            if not any(self._is_copy(s, user, name) for s in opening):
                return
            parsers = [b for b in self.blocks if b.kind == pb.BLOCK_KIND_PARSER]
            if self._refs(user, parsers)[0]:
                return
        self._fuse(user, name)

    def _consumed(self) -> None:
        body = self.control.body
        if len(self.control.params) < 2 or self.control.params[1].type.struct != self.metadata:
            return
        meta = self.control.params[1].name
        end = len(body)
        drop_user = self._user("drop")
        epilogue = drop_user is not None and end >= 1 and body[-1] == _epilogue(meta, drop_user)
        if epilogue:
            end -= 1
        egress_user = self._user("egress_port")
        port = member(var(meta), "egress_port")
        if (
            egress_user is not None
            and end >= 1
            and body[end - 1] == assign(_as_lvalue(port), member(var(meta), egress_user))
            and self._refs("egress_port") == (0, 1 + epilogue)
        ):
            del body[end - 1]
            self._fuse(egress_user, "egress_port")
        if epilogue and drop_user is not None and self._refs("drop") == (0, 0):
            del body[-1]
            self._fuse(drop_user, "drop")
            self.arch.contract.add("drop")
            if self._refs("egress_port") == (0, 0):
                self.arch.contract.discard("egress_port")

    # -- what the program does

    def _user(self, name: str) -> str | None:
        """The renamed user field that had the contract name, when its type
        is the contract's."""
        user = self.arch.renamed.get(name)
        if user is None:
            return None
        fields = {f.name: f.type for f in self.tr.struct_types[self.metadata].fields}
        return user if fields.get(user) == CONTRACT[name] else None

    def _statements(self) -> list[pb.Stmt]:
        out: list[pb.Stmt] = []
        for b in self.blocks:
            out += walk_stmts(b.body)
            for st in b.states:
                out += walk_stmts(st.body)
            for a in b.actions:
                out += walk_stmts(a.body)
        return out

    @staticmethod
    def _is_copy(s: pb.Stmt, target: str, source: str) -> bool:
        """`X.target = X.source` for one variable X."""
        if s.WhichOneof("kind") != "assign":
            return False
        t, v = s.assign.target, s.assign.value
        return (
            t.WhichOneof("kind") == "member"
            and t.member.field == target
            and t.member.base.WhichOneof("kind") == "var"
            and v.WhichOneof("kind") == "member"
            and v.member.field == source
            and v.member.base.WhichOneof("kind") == "var"
            and v.member.base.var == t.member.base.var
        )

    def _refs(self, name: str, blocks: Sequence[pb.Block] | None = None) -> tuple[int, int]:
        """How many field reads and field writes (lvalues, `out` arguments
        included) name `name`, whatever the type they are on."""
        reads = writes = 0
        for m in _messages(self.blocks if blocks is None else blocks):
            if isinstance(m, pb.Member) and m.field == name:
                reads += 1
            elif isinstance(m, pb.LMember) and m.field == name:
                writes += 1
        return reads, writes

    def _m_written_whole(self) -> bool:
        """Whether some statement assigns a variable of type M as a whole,
        or some block or action has an `out` parameter of type M."""
        m = pb.Type(struct=self.metadata)
        for b in self.blocks:
            params = [*b.params, *(p for a in b.actions for p in a.params)]
            if any(p.type == m and p.direction == pb.DIRECTION_OUT for p in params):
                return True
            whole = {v.name for v in [*b.params, *b.locals] if v.type == m}
            whole |= {p.name for a in b.actions for p in a.params if p.type == m}
            for s in self._statements_of(b):
                if s.WhichOneof("kind") == "assign" and s.assign.target.var in whole:
                    return True
        return False

    @staticmethod
    def _statements_of(b: pb.Block) -> list[pb.Stmt]:
        out = list(walk_stmts(b.body))
        for st in b.states:
            out += walk_stmts(st.body)
        for a in b.actions:
            out += walk_stmts(a.body)
        return out

    # -- the change

    def _fuse(self, user: str, name: str) -> None:
        """Rename the user field `name` again, in M and wherever it is read
        or written; its renamed name is unique to it (the renaming saw every
        field of every type)."""
        for m in _messages(self.blocks):
            if isinstance(m, pb.Member | pb.LMember) and m.field == user:
                m.field = name
        for f in self.tr.struct_types[self.metadata].fields:
            if f.name == user:
                f.name = name
        for b in self.blocks:
            for t in b.tables:
                for k in t.keys:
                    if k.name and k.name == ir.dotted_path(k.expr):
                        k.name = ""
        del self.arch.renamed[name]
        self.tr.field_renames = {k: v for k, v in self.tr.field_renames.items() if v != user}
        struct = self.metadata
        self.tr.notes.remove(
            f"{struct}.{name} renamed {user}: user metadata, not the contract field"
        )
        self.tr.notes.append(
            f"{struct}.{name} is the contract field: the source copies it to or from "
            "standard_metadata exactly as the printer's shim does"
        )


def _epilogue(meta: str, drop_user: str) -> pb.Stmt:
    """`if (meta.drop_) { meta.egress_port = 511; }`: the printer's `if
    (M.drop) { mark_to_drop(sm); }` translated with M.drop renamed."""
    port = assign(_as_lvalue(member(var(meta), "egress_port")), lit_bits(9, DROP_PORT))
    return pb.Stmt(conditional=pb.If(condition=member(var(meta), drop_user), then=[port]))


def _messages(blocks: Sequence[pb.Block]) -> list[Message]:
    """Every message inside `blocks`, pre-order."""
    out: list[Message] = []

    def visit(m: Message) -> None:
        out.append(m)
        for fd, value in m.ListFields():
            if fd.message_type is None:
                continue
            if isinstance(value, Message):
                visit(value)
            else:
                for x in value:
                    visit(x)

    for b in blocks:
        visit(b)
    return out


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
