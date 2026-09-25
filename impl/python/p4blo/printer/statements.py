"""The printer's statements: one IR statement to lines of P4-16.

Each dedicated node reverses to its P4 syntax (`packet.extract(...)`,
`h.setValid()`, `s.push_front(n)` and so on). An extern call prints as a
plain method call; an architecture whose extern families have another
form overrides `StmtPrinter.call_extern`.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from p4blo import ir
from p4blo.printer.terms import (
    PACKET,
    PrintError,
    print_args,
    print_expr,
    print_lvalue,
)
from p4blo.v0 import p4blo_pb2 as pb

INDENT = "    "


def print_stmt(stmt: pb.Stmt, *, index: ir.Index | None = None, depth: int = 0) -> str:
    """A statement, possibly several lines, indented `depth` levels.

    With an index a call to a parser or deparser passes the packet on;
    without one every callee is taken to be a control.
    """
    return "\n".join(StmtPrinter(index).lines(stmt, depth))


@dataclass
class StmtPrinter:
    index: ir.Index | None

    def block(self, stmts: Iterable[pb.Stmt], depth: int) -> list[str]:
        return [line for s in stmts for line in self.lines(s, depth)]

    def lines(self, stmt: pb.Stmt, depth: int) -> list[str]:
        pad = INDENT * depth
        match stmt.WhichOneof("kind"):
            case "assign":
                a = stmt.assign
                return [f"{pad}{print_lvalue(a.target)} = {print_expr(a.value)};"]
            case "conditional":
                return self._conditional(stmt.conditional, depth)
            case "apply":
                a = stmt.apply
                call = f"{a.table}.apply()"
                if a.HasField("hit"):
                    return [f"{pad}{print_lvalue(a.hit)} = {call}.hit;"]
                return [f"{pad}{call};"]
            case "call_action":
                c = stmt.call_action
                return [f"{pad}{c.action}({print_args(c.args)});"]
            case "call_block":
                c = stmt.call_block
                args = print_args(c.args)
                if self._callee_takes_packet(c.block):
                    args = f"{PACKET}, {args}" if args else PACKET
                return [f"{pad}{instance_name(c.block)}.apply({args});"]
            case "call_extern":
                return [f"{pad}{self.call_extern(stmt.call_extern)}"]
            case "set_valid":
                return [f"{pad}{print_lvalue(stmt.set_valid.header)}.setValid();"]
            case "set_invalid":
                return [f"{pad}{print_lvalue(stmt.set_invalid.header)}.setInvalid();"]
            case "push":
                p = stmt.push
                return [f"{pad}{print_lvalue(p.stack)}.push_front({p.count});"]
            case "pop":
                p = stmt.pop
                return [f"{pad}{print_lvalue(p.stack)}.pop_front({p.count});"]
            case "extract":
                return [f"{pad}{PACKET}.extract({print_lvalue(stmt.extract.target)});"]
            case "advance":
                return [f"{pad}{PACKET}.advance({print_expr(stmt.advance.bits)});"]
            case "verify":
                v = stmt.verify
                return [f"{pad}verify({print_expr(v.condition)}, error.{v.error});"]
            case "emit":
                return [f"{pad}{PACKET}.emit({print_expr(stmt.emit.value)});"]
            case _:
                raise PrintError("statement has no kind")

    def _conditional(self, c: pb.If, depth: int) -> list[str]:
        pad = INDENT * depth
        lines = [f"{pad}if ({print_expr(c.condition)}) {{"]
        lines += self.block(c.then, depth + 1)
        if c.otherwise:
            lines.append(f"{pad}}} else {{")
            lines += self.block(c.otherwise, depth + 1)
        lines.append(f"{pad}}}")
        return lines

    def _callee_takes_packet(self, block: str) -> bool:
        if self.index is None:
            return False
        return self.index.blocks[block].kind != pb.BLOCK_KIND_CONTROL

    def call_extern(self, call: pb.CallExtern) -> str:
        """An extern call as a method call on the instance, the result
        assigned when there is one."""
        method = f"{call.instance}.{call.method}({print_args(call.args)})"
        if call.HasField("result"):
            return f"{print_lvalue(call.result)} = {method};"
        return f"{method};"


def instance_name(block: str) -> str:
    """The name of a sub-block's instantiation in its caller."""
    return f"{block}_inst"


def walk(stmts: Iterable[pb.Stmt]) -> Iterator[pb.Stmt]:
    """Every statement in `stmts`, recursively through conditionals."""
    for s in stmts:
        yield s
        if s.WhichOneof("kind") == "conditional":
            yield from walk(s.conditional.then)
            yield from walk(s.conditional.otherwise)


def block_stmts(block: pb.Block) -> Iterator[pb.Stmt]:
    """Every statement of a block: its body, its states and its actions."""
    yield from walk(block.body)
    for state in block.states:
        yield from walk(state.body)
    for action in block.actions:
        yield from walk(action.body)
