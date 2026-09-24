# Shared codec object-helper extraction review

Final review: clear for the separate helper-only commit. No Action/Block
roundtrip theorem is supplied by this checkpoint.

2026-09-23. Read-only review of `p4blo-block-codecs` after baseline `6b9ffd0`.
Inspected new CodecObjectLaws, the complete TableCodecLaws diff and evidence
note; independently tested frozen binaries without rebuilding or editing them.

All nine moved definitions/statements/proofs are byte-identical to the previous
private definitions after excluding their private modifier and namespace
placement. Independently checked each extraction. The internal CodecObject
namespace exposes actual TreeMap last-occurrence lookup and null/omission facts;
it does not introduce a competing decoder or runtime API. Table retains its
optional-action, Boolean/natural facts and all four public predicates/theorem
statements unchanged. Its only extra proof step unfolds the generated local
optional-action matcher after module relocation splits matcher sharing. The
initial rewrite failure is documented as proof plumbing, not a semantic kill.

Independently executed the nine-field actual Block-name lookup probe at pinned
Lean 4.34.0 with warnings as errors, no raised limits or presence-case explosion.
It exits 0 with exactly the standard three axioms. Fresh queries of all four
old Table laws also report exactly `propext`, `Classical.choice`, `Quot.sound`.
This demonstrates useful reuse of the actual encoded object, not a completed
Block codec theorem.

Independent executable/provenance checks:

- **753 Table+Block tests passed**, exit 0, 13.98 seconds.
- **161 native codec anchors passed**, exit 0, empty stderr.
- All **181 historical Table baseline rows** and **56 retained fault
  observations** replay byte-for-byte against the new clean endpoint.
- Historical Table proof identity is checked at `228b76b`; all four public
  statement strings remain unchanged. Old baseline hashes use historical
  `9640523` objects, not later proof-source bytes. Old evidence is not rewritten.
- Current Table proof SHA is
  `323cff1035971abcbf85a40c755857109de2d15765a262a7524821d1604655ab`;
  shared helper SHA is
  `5f3061a319308e42ada1398b2d54a6c5559e90aeb90231059091526d9d768bea`.

The owner reports both full Lean/default suites (595 spec checks) passing;
that broader gate is attributed rather than rerun. No Json, schema, runtime,
observer or fixture changes occur in this increment. Integration replay must
retain the historical proof-hash check and explicitly attest this reviewed
proof-only relocation instead of demanding old/current source equality.

No remaining blocker. The new universal Action/Block laws and their independent
campaigns remain the next separately reviewed change.
