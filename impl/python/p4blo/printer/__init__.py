"""The P4 printer: IR to P4-16 text, with no architecture.

The IR has no architecture, and neither has this printer: it turns types,
expressions, statements, declarations and blocks into P4-16, a faithful
reversal of the IR's dedicated nodes back into P4 syntax
(`packet.extract(...)`, `h.isValid()`, `s.push_front(n)` and so on; see
.agents/decisions.md). An architecture binds a printed program to its
package by subclassing `ProgramPrinter`: `p4blo.arch.v1model` for v1model,
`p4blo.arch.spectec_block` for P4-SpecTec's block architecture.

  terms       types, literals, expressions, lvalues, pieces of declarations
  statements  statements, and `StmtPrinter`
  program     block libraries, and `ProgramPrinter` with its hooks

Entry points: `print_program` for a block library without an architecture,
and `print_type`, `print_expr`, `print_lvalue` and `print_stmt` for pieces.
A library is assumed valid; what the printer cannot express raises
`PrintError`.
"""

from p4blo.printer.program import ProgramPrinter, print_program
from p4blo.printer.statements import (
    INDENT,
    StmtPrinter,
    block_stmts,
    instance_name,
    print_stmt,
    walk,
)
from p4blo.printer.terms import (
    PACKET,
    PrintError,
    print_action_call,
    print_arg,
    print_args,
    print_bits,
    print_expr,
    print_key,
    print_key_sets,
    print_key_value,
    print_literal,
    print_lvalue,
    print_param,
    print_target,
    print_type,
)

__all__ = [
    "INDENT",
    "PACKET",
    "PrintError",
    "ProgramPrinter",
    "StmtPrinter",
    "block_stmts",
    "instance_name",
    "print_action_call",
    "print_arg",
    "print_args",
    "print_bits",
    "print_expr",
    "print_key",
    "print_key_sets",
    "print_key_value",
    "print_literal",
    "print_lvalue",
    "print_param",
    "print_program",
    "print_stmt",
    "print_target",
    "print_type",
    "walk",
]
