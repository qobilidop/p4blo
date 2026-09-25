# pyright: strict
"""The Python eDSL for p4blo programs: type-safe by construction.

Headers and structs are classes with annotated fields; parsers, controls
and deparsers are classes whose states and actions are methods; widths are
type parameters, `Bits[L[8]]`, spelled through the aliases `bit8`,
`bit48`, ...; every reference is a Python object that pyright resolves.
The design and what pyright checks are in `docs/design.md`, "Python eDSL"; each
module's docstring states the static rules it provides:

- `values`: `Bits`, `Var`, `Bool`, `Enum`, `Error`, the aliases, `concat`, `mux`.
- `views`: `Header`, `Struct`, `Stack`.
- `blocks`: `Parser`, `Control`, `Deparser`, `state`, `action`, `Table`.
- `externs`: `Extern` and the families `Register`, `Counter`, `Checksum16`.
- `program`: `Program`, whose `build()` returns the `pb.Program`.
- `errors`: `EdslError`, with `(defined at file:line)`.

The two clocks
--------------

A program written here runs on two clocks, and it helps to keep them apart.

**Build time** is when Python runs: a class body declares a header, a
`@state` method runs *once*, with a recording `self`, when `Program.build()`
assembles the block, and each `self.assign(...)`, `self.extract(...)` or
`with self.if_(...)` appends a statement to the IR. Python's own control
flow at build time is ordinary metaprogramming: a `for` loop emitting five
`if_` blocks emits five, and an `if` on a Python value decides what to
emit. Values of the eDSL have no truth value at build time, because their
value is unknown until run time: `if hdr.ttl == 1:` raises and names the
cause.

**Run time** is when a packet goes through the IR, in an interpreter or a
target. `with self.if_(cond)` is a run-time branch; `mux(cond, a, b)` a
run-time choice; a `select` a run-time dispatch. Nothing written here
reads Python source: the IR is exactly what the build-time calls recorded.

The dynamic API of the same builder, `p4blo.edsl.core`, is documented for
generated programs: plain constructors, strings for names, `bit(n)` for
widths. This package is a typed front over it, and the core's run-time
checks remain authoritative.

What pyright checks, and what it cannot
---------------------------------------

The design note's contract, kept here because no single module carries the
whole of it: `values` has the value rules, `views` the field rules,
`blocks` the block rules. A row marked (*) is one of the four deviations
from the note that the type checker forced; each is accepted and recorded
in `.agents/decisions.md`, and each holds its run-time side.

Checked statically:

- field, state, action, table, extern and block names, every reference
  being an attribute pyright resolves rather than a string;
- equal widths in arithmetic, in comparison and in assignment, and the
  width of a cast target;
- action argument count, names and widths, in a direct call, in a table's
  `default=` and in its const entries -- the entries only when `keys` is a
  tuple of one to four keys, which is what types them;
- extern method names, argument directions, and the width of an `out`
  argument;
- that a place is required where the IR requires one: an rvalue assigned
  to, or passed as an extern's `out` argument, is refused;
- that an enum value goes to a place of its own enum type, in an
  assignment as well as in a comparison.

Run time only:

- the width of a `concat`, a slice or a `lookahead`: `Bits[Any]` until
  `x.as_(bit16)` asserts it;
- that an `int` literal fits its width, and that a `select` keyset fits
  its key's type;
- a table's key match-kind rules, and everything the validator owns;
- (*) that a `bitN(...)` literal is not a place: the aliases name places
  (`bitN = Var[L[N]]`) so that annotated fields are assignable and an
  action parameter accepts `bit9(1)`, so a literal written as a target is
  caught by the core;
- (*) that a `Bool`, `Enum` or `Error` target is a place: those three have
  no static place split, so assigning to a member literal is caught by the
  core rather than by the checker;
- (*) the width of an extern's `in` arguments, typed `Val[T]`, since
  binding `T` to a place type would reject a cast rvalue;
- (*) a sub-block call's arguments, `self.call(Sub, ...)`, since a
  callable protocol cannot be expressed from the annotations. This is why
  `tests/unit/test_pyright.py` builds and validates every must_pass fixture
  instead of only type-checking it.

Two notes on what a diagnostic looks like. `assign` is overloaded over the
kinds of target, so pyright reports a failed assignment as
`reportCallIssue`, "No overloads match", rather than as an argument type;
four must_fail headers say so. And action data is written `bit9(1)`, never
a bare int: that is the one place the literal rule is denied statically
although the build accepts it, for the reason `blocks` gives.
"""

from p4blo.edsl.blocks import (
    Accept,
    Action,
    ActionCall,
    Block,
    Control,
    Deparser,
    Entry,
    Key,
    Parser,
    Reject,
    State,
    StateRef,
    Table,
    Transition,
    action,
    dont_care,
    entry,
    exact,
    lpm,
    masked,
    prefix,
    range_,
    state,
    ternary,
)
from p4blo.edsl.errors import EdslError
from p4blo.edsl.externs import CRC16, CRC32, Extern
from p4blo.edsl.program import Program
from p4blo.edsl.values import (
    Bits,
    Bool,
    Const,
    CoreErrors,
    Enum,
    Error,
    Errors,
    In,
    InOut,
    L,
    Out,
    Val,
    Value,
    Var,
    bit,
    bit1,
    bit2,
    bit3,
    bit4,
    bit5,
    bit6,
    bit7,
    bit8,
    bit9,
    bit10,
    bit11,
    bit12,
    bit13,
    bit14,
    bit15,
    bit16,
    bit17,
    bit18,
    bit19,
    bit20,
    bit21,
    bit22,
    bit23,
    bit24,
    bit25,
    bit26,
    bit27,
    bit28,
    bit29,
    bit30,
    bit31,
    bit32,
    bit33,
    bit34,
    bit35,
    bit36,
    bit37,
    bit38,
    bit39,
    bit40,
    bit41,
    bit42,
    bit43,
    bit44,
    bit45,
    bit46,
    bit47,
    bit48,
    bit49,
    bit50,
    bit51,
    bit52,
    bit53,
    bit54,
    bit55,
    bit56,
    bit57,
    bit58,
    bit59,
    bit60,
    bit61,
    bit62,
    bit63,
    bit64,
    concat,
    mux,
)
from p4blo.edsl.views import Header, Stack, Struct, View

__all__ = [
    "CRC16",
    "CRC32",
    "Accept",
    "Action",
    "ActionCall",
    "Bits",
    "Block",
    "Bool",
    "Const",
    "Control",
    "CoreErrors",
    "Deparser",
    "EdslError",
    "Entry",
    "Enum",
    "Error",
    "Errors",
    "Extern",
    "Header",
    "In",
    "InOut",
    "Key",
    "L",
    "Out",
    "Parser",
    "Program",
    "Reject",
    "Stack",
    "State",
    "StateRef",
    "Struct",
    "Table",
    "Transition",
    "Val",
    "Value",
    "Var",
    "View",
    "action",
    "bit",
    "bit1",
    "bit2",
    "bit3",
    "bit4",
    "bit5",
    "bit6",
    "bit7",
    "bit8",
    "bit9",
    "bit10",
    "bit11",
    "bit12",
    "bit13",
    "bit14",
    "bit15",
    "bit16",
    "bit17",
    "bit18",
    "bit19",
    "bit20",
    "bit21",
    "bit22",
    "bit23",
    "bit24",
    "bit25",
    "bit26",
    "bit27",
    "bit28",
    "bit29",
    "bit30",
    "bit31",
    "bit32",
    "bit33",
    "bit34",
    "bit35",
    "bit36",
    "bit37",
    "bit38",
    "bit39",
    "bit40",
    "bit41",
    "bit42",
    "bit43",
    "bit44",
    "bit45",
    "bit46",
    "bit47",
    "bit48",
    "bit49",
    "bit50",
    "bit51",
    "bit52",
    "bit53",
    "bit54",
    "bit55",
    "bit56",
    "bit57",
    "bit58",
    "bit59",
    "bit60",
    "bit61",
    "bit62",
    "bit63",
    "bit64",
    "concat",
    "dont_care",
    "entry",
    "exact",
    "lpm",
    "masked",
    "mux",
    "prefix",
    "range_",
    "state",
    "ternary",
]
