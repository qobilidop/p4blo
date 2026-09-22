"""Parse errors, raised to stop a parser run.

A parser stops at the first raised error with the headers and metadata as
they were (docs/semantics.md, "Parsers"). Inside the interpreter that is an
exception; `run_parser` catches it and reports the error in the outcome, so
it never escapes to a caller.
"""

from __future__ import annotations

from p4blo.interp.values import ErrorValue

PACKET_TOO_SHORT = ErrorValue("PacketTooShort")
NO_MATCH = ErrorValue("NoMatch")
STACK_OUT_OF_BOUNDS = ErrorValue("StackOutOfBounds")
PARSER_TIMEOUT = ErrorValue("ParserTimeout")


class ParseError(Exception):
    """Stop the parser, rejecting with `error`.

    Raised with `NoError` for an explicit transition to `reject`.
    """

    def __init__(self, error: ErrorValue) -> None:
        super().__init__(error.name)
        self.error = error
