# Bounded call-copy DRT review

**Clear** for integration subject to the ordinary full gate. Reviewed
`tests/test_drt_call_copy.py` and `docs/notes/call-copy.md` read-only in
`p4blo-call-copy`, base `480eef4`. No production code change is involved.

The generated programs use permitted input-snapshot overlap with a single
inout argument; the out argument uses distinct storage. This follows the
existing control-call contract and does not bypass the validator or claim
semantics for forbidden overlapping writable arguments. The abandoned
shadowing case is accurately recorded as rejected, not implemented support.
The common body is exercised both as a direct action and as a sub-control.

The independent final tuples distinguish snapshot copying from mutation,
out zero-initialization from caller state, and successful copyback. Every
stored field and validity bit of both affected headers and an unrelated
header is observed after the complete call, even when a header is invalid.
An unrelated scalar and nonempty unconsumed packet tail are checked too.
Byte-padding for widths 8, 9 and 65 does not drop high bits. Expected bytes
do not depend on either interpreter's value/copy implementation.

Independently executed the whole candidate file with required Lean enabled:
**19 passed**, exit 0. This includes twelve boundary cases, the forty-example
generated profile, and all six scoped live/restored fault checks. The faults
replace actual argument-copy, out-initialization and copyback dependencies;
each produces a genuine output divergence without error/diagnostic. They
are not failures of program construction or validation. Input retention
precedes the independent known-answer assertion, and live replay plus
restored agreement are asserted by each permanent test.

Independently inspected all six artifacts created by that execution. Each
contains exactly the tracked `call_program(kind, 9, False, 257, 19, 3)`, one
empty-entry request at ingress zero with payload `dead`, four ports and seed
zero. As documented, there are two distinct input bundles, not six distinct
programs; mutations are intentionally not stored as part of replay input.
The independently reproduced byte lengths and SHA256 match the note:

- Action: 21048 bytes,
  `cffb414c8101cd0076c0309421eab80c172016d7af45dcbfe5e35de7c097b8fd`.
- Sub-control: 20568 bytes,
  `5624b281526f1be85bc021ad4b049578983b50dc90cbbef403b21b5a444e372b`.

No candidate build or shared-image operation was performed. The implementer
reports both Lean gates and static checks passed; full-gate completion is
the integrator's remaining checkpoint. The evidence is bounded runtime
conformance, not a universal call theorem or evidence about parser-fault
copyback, table action invocation, extern effects or arbitrary nesting.
