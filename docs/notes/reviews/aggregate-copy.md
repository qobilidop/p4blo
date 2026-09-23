# Aggregate-copy conformance review

Independent read-only review on 2026-09-23 of
`p4blo-aggregate-copy/tests/test_drt_aggregate_copy.py` and its scoped note.
**Disposition: clear, retaining the ordinary full integration gate.** No
production changes, candidate builds or image operations by the reviewer.

## What the profile establishes

The programs exercise actual whole-header assignment and whole-record
assignment, followed by independent mutations on both source and target.
Header copies retain the target record's tag; record copies replace it.
Changing the source tag, source validity, source left field and target right
field after copying exposes shared mutable containers in either direction.
An unrelated record supplies separate data/validity/tag sentinels.

All source/target/unrelated snapshots occur **after** the tested operations.
Stored fields of invalid headers are read into a separate valid result
header, rather than inferred from an invalid header's omitted emission.
Explicit byte-aligned casts make nine-bit and 65-bit observations readable
without losing high bits. Expected bytes use independently specified final
value tuples and integer byte conversion, not interpreter results or the
copy implementation. Both architecture loaders perform normal validation;
no invalid-program filtering or special bypass was introduced.

Sixteen systematic cases cover both copy kinds, both header validities and
widths 8/9/16/65 with deliberately unequal boundary/sentinel values. The
bounded Hypothesis profile varies four field values and retains shrinking.
It does not claim arbitrary nesting, stack copies, calls/copyback ordering,
concurrency, original P4 oracle agreement or a universal assignment proof.
The accompanying note keeps those exclusions explicit.

## Fault detection and replay

The permanent mutation tests patch the actual interpreter `expr.copy`
dependency, returning an existing Header or Struct object instead of its
deep copy and preserving ordinary handling of other values. The mutation
therefore reaches actual mutable runtime assignments; this is not merely
altering expected data or faking Lean output.

The failing comparison saves the complete program/request before the
independent known-answer assertion. Final tightened tests assert exact
saved program, one empty request at ingress 0, ports 4 and seed 0. Live
replay has a genuine output difference, with neither side reporting an error
or diagnostic. After scoped restoration, the saved program agrees and the
independent byte answer passes. Both live/restored mutation tests were run
independently as part of the focused suite.

## Independently executed evidence

Ran the complete focused file against the stable built Lean executable
with `P4BLO_REQUIRE_LEAN=1`, reviewer environment and isolated temporary
artifact/Hypothesis directories. Both the initial and final tightened suite
pass **19 tests**, exit 0. The final statistics show **40 passing generated
examples**, zero failing examples, and four internal invalid generation
attempts; the source contains no `assume`/filter-based acceptance shortcut.

Independently loaded the two additionally retained artifacts, reconstructed
their programs with `copy_program(kind, 9, False, 257, 19, 3, 7)`, checked
exact program/inputs/ports/seed and replayed each through the stable Lean
endpoint: **one agreement each**. Hashes/lengths match the implementation
note:

- Header: `aggregate-copy-a11c5b4716fff9ab5f0d1dd7.json`, 26254 bytes,
  `79d0ceacb9590d067b81b52d77fa175b78ed5c9ae7ec9532d8739ef7d12c0cc6`;
- Struct: `aggregate-copy-5ab5bcc15014358200d144ec.json`, 25984 bytes,
  `06d4685c99bcbae43974fcca8f6447abc986729b957cacbd9a882e9339121101`.

Candidate `git diff --check` passes. Both Lean builds/audits and static
checks are integrator-reported, not additional reviewer builds. Full suite
completion remains an integration gate rather than an inferred pass from
these focused tests. No further correctness issue found.
