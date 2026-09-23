# Aggregate-copy conformance profile

2026-09-23. This checks a concrete implementation risk: Python stores mutable
headers/structs, while Lean rebuilds immutable values. Correct field updates
do not by themselves establish that a prior whole-aggregate assignment made
an independent deep copy. No production semantics or public API changes.

## Scope and independent observations

`tests/test_drt_aggregate_copy.py` builds validator-checked programs with three
local records. Each contains a two-field header and an eight-bit tag. Copy
either the source header into the target header or the entire source record
into the target record. Then change a source field, source tag and source
validity, and change the other target field. The unrelated record is a
sentinel. Observe every stored field, tag and validity bit **after** all
operations, including invalid-header contents, through a separate valid
result header. Nothing is inferred from whether the invalid header emitted.

Expected bytes come from explicit value tuples and integer byte conversion,
not Python execution, Lean evaluation, field-copy helpers or source lowering.
The output pads each scalar observation to a byte boundary explicitly.
Sixteen systematic cases cross header/struct copies, both validity states
and widths 8/9/16/65. Forty deterministic shrinking generated examples vary
the four field values across those shapes. There is no rejection filtering:
a generator producing invalid IR fails the ordinary validator.

The wrapper is test scaffolding, not a verified frontend or complete program
proof. Stacks, arbitrary nesting, calls/copyback, malformed declarations and
concurrent behavior are not covered by this profile. No original P4 oracle
claim is made for observing stored fields of invalid headers.

## Real implementation fault injection and retained replay

Two permanent tests replace the actual interpreter `expr.copy` dependency
with an identity function for Header or Struct values, leaving other copies
alone. Both faults run through the production Python architecture and IR
interpreter against the compiled production Lean executable. Each creates
one observable mismatch with no matching-error shortcut; comparison saves
the concrete program and complete request before the independent byte answer.
The saved replay fails with the fault active and passes after restoration.
The expected-byte check also passes after restoration. These are executable
fault kills, not build failures; no injected fault is merged into production.

The test is its own tracked reconstruction recipe:

```
P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_drt_aggregate_copy.py -q
```

Concrete ignored bundles were additionally retained under `.artifacts/drt/`
in the implementation worktree, using the same permanent tests with explicit
output folders. Each contains one empty-input request and the full program:

| Copy | File | Bytes | SHA-256 |
|---|---|---|---|
| Header | `copy-header/aggregate-copy-a11c5b4716fff9ab5f0d1dd7.json` | 26254 | `79d0ceacb9590d067b81b52d77fa175b78ed5c9ae7ec9532d8739ef7d12c0cc6` |
| Struct | `copy-struct/aggregate-copy-5ab5bcc15014358200d144ec.json` | 25984 | `06d4685c99bcbae43974fcca8f6447abc986729b957cacbd9a882e9339121101` |

Their immutable input is `copy_program(kind, 9, False, 257, 19, 3, 7)`;
regenerate and run the real fault with
`test_lean_agrees_copy_observer_kills_aliasing`, passing the actual built
Lean path, the kind, an empty output directory and `pytest.MonkeyPatch()`.
Use the ordinary `python -m p4blo.drt.replay FILE` for restored comparison.
Ignored artifacts are convenient retained evidence, not the only handoff.

## Checks and next obligation

Implementation worktree based on `7a58ef2`: both Lean package gates/audits
pass; the focused Python gate passes **19 tests**, including the shrinking
campaign and both live/restored mutations. Formatting, lint and type checks
pass. The full Python/schema/oracle gate passes **1526 tests / five precise
expected discrepancies / one explicit unavailable-XDP-image skip**, exit 0;
the final tighter replay assertions were also rerun in the focused gate.
Independent review: `reviews/aggregate-copy.md`. This is additional bounded runtime evidence alongside
the ongoing Lean field-expression proofs, not a proof of Python equivalence
or aggregate assignment correctness for every program.

Confidence is high for the selected aliasing risks, medium for generated
shape diversity. Revisit this profile when stacks or block/action copyback
become the next verified authoring feature; add independent copy-out ordering
answers rather than assuming these local assignment tests establish them.
