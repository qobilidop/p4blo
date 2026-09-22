"""The reference interpreter.

Three entry points, one per block kind, with the calling convention from
docs/design.md:

    parse    : Packet x M            -> H x M x consumed x accepted x error
    control  : H x M x Entries       -> H x M
    deparse  : H                     -> Packet

None of them mutates its arguments; each returns fresh values. Externs are
the only state a block can touch, and they are passed in by the caller.
Everything the interpreter decides is written down in docs/semantics.md.

The package reads as one explanation, bottom up:

    values.py    run-time values and their zero, copy and equality
    api.py       what a caller exchanges with the interpreter
    errors.py    parse errors as an exception
    widths.py    static types and widths of IR expressions
    packet.py    the packet under a parser; the emit buffer of a deparser
    tables.py    installed entries and the match algorithm
    env.py       variable storage for one block activation
    expr.py      expressions and lvalues
    stmt.py      statements, calls, and the parser's state machine
    parser.py, control.py, deparser.py   the three entry points
"""

from __future__ import annotations

from p4blo.interp.api import ExternBinding, ExternResult, Externs, InterpError, ParseOutcome
from p4blo.interp.control import run_control
from p4blo.interp.deparser import run_deparser
from p4blo.interp.parser import run_parser
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits

__all__ = [
    "Bits",
    "ExternBinding",
    "ExternResult",
    "Externs",
    "InstalledEntries",
    "InterpError",
    "ParseOutcome",
    "run_control",
    "run_deparser",
    "run_parser",
]
