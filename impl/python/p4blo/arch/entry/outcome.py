"""Result of the optional H/M parser calling convention."""

from dataclasses import dataclass

from p4blo.interp.values import NO_ERROR, ErrorValue, Struct


@dataclass(slots=True)
class ParseOutcome:
    """What a parser run produced (docs/ir-semantics.md, "Parsers").

    Rejection and error are separate: `accept` gives `accepted` with
    `NoError`; an explicit `reject` gives not accepted with `NoError`; a
    raised error gives not accepted with that error.
    """

    headers: Struct
    metadata: Struct
    consumed_bits: int
    accepted: bool = True
    # A name from Program.errors.
    error: ErrorValue = NO_ERROR
