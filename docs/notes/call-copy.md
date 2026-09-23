# Bounded aggregate call copy-in/out profile

2026-09-23. `tests/test_drt_call_copy.py` extends runtime evidence beyond
local aggregate assignment, without claiming a call/copyback proof.

## Contract and independently expected state

Run the same small header-transforming body as a direct action and a
sub-control. Its read-only input snapshots a caller header also passed as
inout. A distinct out header starts with nonzero caller fields and is valid
before calling. In the callee, update the inout left field, read the original
left through the input snapshot into the inout right, copy the original
right into the out left, and increment the out right from its required zero.
The out header must remain invalid regardless of its caller's initial value.

Observe every field and validity bit of the inout header, out header and an
unrelated header **after** the complete call, using a separate valid result
header. Preserve an unrelated scalar sentinel and a nonempty `dead` packet
tail. Expected bytes come from explicit final tuples and integer conversion,
not either interpreter, argument helpers or a Lean-generated expected value.

Twelve boundary cases cross action/sub-control, initial header validity and
widths 8/9/65. Forty deterministic shrinking examples vary the three data
values across that profile. All programs go through ordinary validation;
there is no generator rejection filter or unchecked execution shortcut.

An initial proposed name-shadowing case failed validation with
`NAME_DUPLICATE`: action parameters may not collide with enclosing block
declarations. It was corrected to disjoint names, not bypassed or treated
as a valid language case. Likewise two overlapping writable out/inout
arguments are prohibited by the existing validator. Only the permitted
overlap of an input snapshot with one writable argument is generated here.
Do not claim these tests demonstrate behavior of rejected aliases or the
effect of copyback order between overlapping writable parameters.

## Faults and complete replays

Six permanent regression cases inject three real interpreter dependencies
for each call kind, one at a time:

1. `stmt.copy` returns the same Header instead of copying argument values.
   Later inout writes then corrupt the supposedly independent input snapshot.
2. `stmt.argument_value` initializes the out argument from its caller storage
   instead of zero; the output's field values and validity reveal the fault.
3. `stmt.copy_back` skips all copyback, losing the callee's updates.

Each actual Python execution disagrees with the compiled Lean endpoint in
its output, with neither side reporting an error or diagnostic. The harness
saves the complete program/request before testing the independent expected
answer. Tests check exact program, one request at ingress 0 with empty table
entries and payload `dead`, four ports and seed zero. The saved replay still
fails live, then agrees after scoped restoration, and the independent byte
answer passes. No intentional production fault is committed.

Regenerate all faults and replay checks from the tracked test alone:

```
P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_drt_call_copy.py -q
```

Additional ignored artifacts were retained by calling
`test_lean_agrees_call_copy_mutation_replays` with the real built Lean path,
kind, fault, an empty output directory and `pytest.MonkeyPatch()`.
There are six experiments but only **two distinct input bundles**: replay
stores the input, not the active mutation. All three faults for a given kind
therefore produce identical bytes. Exact input construction is
`call_program(kind, 9, False, 257, 19, 3)`.

| Kind | Filename | Bytes | SHA-256 |
|---|---|---|---|
| action | `call-copy-664b837a2dd1ba1906357b0b.json` | 21048 | `cffb414c8101cd0076c0309421eab80c172016d7af45dcbfe5e35de7c097b8fd` |
| block | `call-copy-01ccf986bf9a536f534ada66.json` | 20568 | `5624b281526f1be85bc021ad4b049578983b50dc90cbbef403b21b5a444e372b` |

Use the ordinary `python -m p4blo.drt.replay FILE` against the restored
implementation. Fault definitions and matching live/restored expectations
are permanent tests, so temporary artifacts are not the only handoff.

## Gates and scope limits

Implementation worktree starts from `480eef4`. Both Lean packages/default
audits pass. The focused suite passes **19 tests**, including forty generated
examples and six live/restored faults. Formatting, lint, pyright and diff
checks pass. The full Python/schema/oracle gate with required Lean passes
**1648 tests / five precise expected discrepancies / one explicit local
XDP-image skip**, exit 0. Independent review is clear, including nineteen
focused tests and exact checks of both distinct retained inputs:
`reviews/call-copy.md`.

Confidence is high for the selected snapshot, initialization and copyback
faults; medium for call-shape diversity. No original P4 oracle, arbitrary
nesting, action table invocation, parser-error copyback, calls with extern
effects, recursive-call behavior or general Python equivalence claim follows.
Expand to a named parser-fault/call profile when its observation contract and
independent expected state are established; do not infer it from normal
successful control calls.
