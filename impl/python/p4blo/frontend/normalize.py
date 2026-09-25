"""A canonical form of an IR program, for comparing two authorings of it.

A golden written in the eDSL and a translation from P4 source may differ in
choices that carry no meaning: the order of declarations, the names of a
block's parameters and locals, and assignments of a variable to itself.
`normalize` removes exactly those differences and no others:

- header, struct, enum and extern types, extern instances and blocks are
  sorted by name, and so are a block's locals once renamed;
- a block's parameters are renamed `p0`, `p1`, ... by position and its
  locals `v0`, `v1`, ... in the order of their first use, reading states
  in order, then the body, then actions in order, skipping any name an
  action parameter of the block has, which would capture the variable
  inside that action; an action parameter keeps its name, since table
  entries name action data by it;
- an instance of a stateless extern family (`checksum16`, `crc16`,
  `crc32`; docs/arch-supports.md, "Extern families") is renamed after its
  type, `checksum16#0`, in the order of first use: it has no state to
  observe, and the v1model shim prints it as a function call, so its name
  does not survive a round trip through the printer;
- `x = x` is removed.

Everything a host or the architecture sees keeps its name: blocks, tables,
actions, keys, stateful extern instances, errors and the fields of every
type. Two programs with equal normal forms are the same program up to
those renamings, which no execution can observe.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable

from google.protobuf.message import Message

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb

__all__ = ["drop_self_assignments", "normalize"]


def normalize(program: apb.BlockAssembly) -> apb.BlockAssembly:
    p = copy.deepcopy(program)
    for field_name in ("header_types", "struct_types", "enum_types", "extern_types"):
        items = sorted(getattr(p, field_name), key=lambda d: d.name)
        del getattr(p, field_name)[:]
        getattr(p, field_name).extend(items)
    _rename_stateless_instances(p)
    instances = sorted(p.extern_instances, key=lambda d: d.name)
    del p.extern_instances[:]
    p.extern_instances.extend(instances)
    for block in p.blocks:
        _normalize_block(block)
    blocks = sorted(p.blocks, key=lambda b: b.name)
    del p.blocks[:]
    p.blocks.extend(blocks)
    return p


STATELESS_FAMILIES = frozenset({"checksum16", "crc16", "crc32"})


def _rename_stateless_instances(p: apb.BlockAssembly) -> None:
    stateless = {
        i.name: i.extern_type
        for i in p.extern_instances
        if i.extern_type.split(".", 1)[0] in STATELESS_FAMILIES
    }
    order: list[str] = []

    def note(m: Message) -> None:
        if isinstance(m, pb.CallExtern) and m.instance in stateless and m.instance not in order:
            order.append(m.instance)
        for _, value in m.ListFields():
            if isinstance(value, Message):
                note(value)
            elif not isinstance(value, str | bytes | int | float | bool):
                for x in value:
                    if isinstance(x, Message):
                        note(x)

    for block in p.blocks:
        note(block)
    order += sorted(set(stateless) - set(order))
    counts: dict[str, int] = {}
    mapping: dict[str, str] = {}
    for name in order:
        t = stateless[name]
        mapping[name] = f"{t}#{counts.get(t, 0)}"
        counts[t] = counts.get(t, 0) + 1
    for i in p.extern_instances:
        i.name = mapping.get(i.name, i.name)

    def rename(m: Message) -> None:
        if isinstance(m, pb.CallExtern) and m.instance in mapping:
            m.instance = mapping[m.instance]
        for _, value in m.ListFields():
            if isinstance(value, Message):
                rename(value)
            elif not isinstance(value, str | bytes | int | float | bool):
                for x in value:
                    if isinstance(x, Message):
                        rename(x)

    for block in p.blocks:
        rename(block)


def _normalize_block(block: pb.Block) -> None:
    order: list[str] = []
    local_names = {v.name for v in block.locals}

    def note(m: Message) -> None:
        if isinstance(m, pb.Expr | pb.LValue) and m.WhichOneof("kind") == "var":
            if m.var in local_names and m.var not in order:
                order.append(m.var)
            return
        for _, value in m.ListFields():
            if isinstance(value, Message):
                note(value)
            elif not isinstance(value, str | bytes | int | float | bool):
                for x in value:
                    if isinstance(x, Message):
                        note(x)

    for s in block.states:
        note(s)
    for st in block.body:
        note(st)
    for t in block.tables:
        note(t)
    for a in block.actions:
        note(a)
    unused = sorted(local_names - set(order))
    reserved = {p.name for a in block.actions for p in a.params}
    params = _numbered("p", len(block.params), reserved)
    mapping = {p.name: params[i] for i, p in enumerate(block.params)}
    locals_named = [*order, *unused]
    mapping |= dict(zip(locals_named, _numbered("v", len(locals_named), reserved), strict=True))
    by_name = {v.name: v for v in block.locals}
    locals_ = [by_name[n] for n in [*order, *unused]]
    del block.locals[:]
    block.locals.extend(locals_)
    for v in [*block.params, *block.locals]:
        v.name = mapping[v.name]
    _rename_all(block.body, mapping)
    for s in block.states:
        _rename_all(s.body, mapping)
        _rename_all([s.transition], mapping)
        drop_self_assignments(s.body)
    for t in block.tables:
        _rename_all(t.keys, mapping)
    for a in block.actions:
        shadow = {p.name for p in a.params}
        _rename_all(a.body, {k: v for k, v in mapping.items() if k not in shadow})
        drop_self_assignments(a.body)
    drop_self_assignments(block.body)


def _numbered(prefix: str, count: int, reserved: set[str]) -> list[str]:
    """`count` names `prefix0`, `prefix1`, ..., skipping reserved ones."""
    out: list[str] = []
    i = 0
    while len(out) < count:
        name = f"{prefix}{i}"
        i += 1
        if name not in reserved:
            out.append(name)
    return out


def _rename_all(messages: Iterable[Message], mapping: dict[str, str]) -> None:
    for m in messages:
        _rename(m, mapping)


def _rename(m: Message, mapping: dict[str, str]) -> None:
    if isinstance(m, pb.Expr | pb.LValue) and m.WhichOneof("kind") == "var":
        if m.var in mapping:
            m.var = mapping[m.var]
        return
    for _, value in m.ListFields():
        if isinstance(value, Message):
            _rename(value, mapping)
        elif not isinstance(value, str | bytes | int | float | bool):
            for x in value:
                if isinstance(x, Message):
                    _rename(x, mapping)


def _same(target: pb.LValue, value: pb.Expr) -> bool:
    match target.WhichOneof("kind"), value.WhichOneof("kind"):
        case "var", "var":
            return target.var == value.var
        case "member", "member":
            return target.member.field == value.member.field and _same(
                target.member.base, value.member.base
            )
        case "index", "index":
            return target.index.index == value.index.index and _same(
                target.index.base, value.index.base
            )
        case _:
            return False


def drop_self_assignments(stmts: Iterable[pb.Stmt]) -> None:
    """Remove `x = x`, which does nothing, in place and in nested branches."""
    kept: list[pb.Stmt] = []
    items = list(stmts)
    for s in items:
        if s.WhichOneof("kind") == "assign" and _same(s.assign.target, s.assign.value):
            continue
        if s.WhichOneof("kind") == "conditional":
            drop_self_assignments(s.conditional.then)
            drop_self_assignments(s.conditional.otherwise)
        kept.append(s)
    if len(kept) != len(items) and hasattr(stmts, "__delitem__"):
        del stmts[:]  # type: ignore[attr-defined]
        stmts.extend(kept)  # type: ignore[attr-defined]
