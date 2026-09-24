# Action and Block codec laws review

Final review: CLEAR for the two wire-only laws and their bounded independent
compatibility evidence. Chronological investigation follows.

2026-09-23. Read the new BlockCodecLaws and mixed kernel witnesses in
`p4blo-block-codecs` after separately reviewed baseline `6b9ffd0` and helper
extraction `707fb3f`. No candidate build, source edit or binary consumer run
during this structural pass.

ActionRepresentable requires only its two member-list predicates;
BlockRepresentable requires exactly the six existing member-list predicates.
All strings, three kinds, list lengths/order, arbitrary parameter directions
and semantically invalid kind/field combinations remain unrestricted. The new
predicates inherit only the existing numeric wire bounds rather than smuggling
in validation or successful-decoder assumptions.

Both theorems concern actual Action/Block.decode and toJson for every path.
The earlier reviewed actual-object helper handles omitted groups; ordered
array laws compose actual member decoders. The private enum helper concerns
real emitted fields and the final three constructor cases discharge actual
shared enum mapping. No alternate object decoder, new runtime behavior,
callback, partial-decoder refactor or excessive presence-case split is added.

The forall-kind constructive witness includes all directions, empty and
unresolved names, nested statements, present-empty optional table action,
all nested parser fields and large/maximal boundary values. Twenty negative
witnesses reach inherited bounds through action parameters/body, every Block
member family, both nested table action locations, entry priority/LPM prefix,
parser transitions and standalone body expressions/types/counts. They do not
claim to characterize semantic validity.

The new three default audit registrations and final build behavior remain to
be queried once the owner releases binaries. The independent baseline remains
the source of expected meanings/errors. Paired enum or name/start-state swaps
may preserve roundtrip; the planned direct constructor/full-field controls and
actual fault campaign must still establish meaningful independent detection.
Historical object-helper proof drift stays separately attributed to its already
reviewed extraction, not a changed codec or recaptured baseline.

## Independent stable-candidate checks

After the owner released candidate consumers, the reviewer ran all 518 focused
Action/Block tests successfully, exit 0. The compiled codec endpoint's complete
self-test produced 161 passing native checks, exit 0. A fresh pinned Lean query
confirmed all three added audit roots use exactly propext, Classical.choice
and Quot.sound. An initial reviewer command guessed a nonexistent native
`BlockCodecTests.run` entry point; that query failure was corrected to the
actual registered endpoint and is not mutation evidence.

Independently replayed all 498 historical raw rows against the final candidate
endpoint, requiring exact stdin-source matching, stdout/stderr/status and strict
expected response identity. All passed. The original 3,568,250-byte baseline
hash remains `910a517c0832f9ae2413577c18a774de51290c6e775bf4be07f8398796bef49e`;
all eighteen source hashes match historical baseline commit 6b9ffd0 rather
than incorrectly requiring the newly proof-extended native file to be unchanged.
No candidate rebuild or source edit was performed. Actual campaign evidence
and restored source/artifact comparisons remain the final acceptance step.

## Final campaign/restoration closure

Read the complete final durable note and actual fault/build/test logs. All five
faults successfully built the actual Json module. Reversing Action body encoding
then failed the unchanged ordered-array proof goal. Shared parser/control
mapping, error-order change and absent/null-kind defaulting all built both new
laws, yet independent ordinary focused tests rejected 70, 2 and 2 cases.
The latter two illustrate that success roundtrip says nothing about arbitrary
malformed-input errors or rejected defaults.

The paired name/startState change broke a path-sensitive intermediate rewrite;
the note correctly distinguishes this from a proven universally false
roundtrip and supplies a compiled asymmetric all-kind closed success witness.
Ordinary pytest was blocked by the actual packet preflight, not by executed
codec assertions: 20 pure checks passed and 498 endpoint setups errored. The
separately labeled direct unchanged-body runner then rejected 12 known-answer/
error cases. Its native anchors rejected five. No setup failure or direct
runner is mislabeled packet DRT.

Both paired false-assurance challenges were inspected: corrupting Python's
expected kind or the Lean constructor observer made all 518 Python checks
pass, while independent native literal anchors still rejected four/six cases.
The reviewer independently reconstructed both paired source edits and verified
their recorded SHA-256 identities. The endpoint during fault experiments
retained the reviewed baseline registration layer so a proof rejection did not
block executable observations; final candidate registrations/audits were not
disabled or weakened. Restoration rebuilt the full final layer.

Executed the note's read-only, unique-anchor reconstruction of all five actual
Json patches. All four live-recorded mutant source hashes match; the fifth is
explicitly proof-only. Independently executed the complete dual-endpoint
restoration recipe: 498 historical exact stdout/stderr/status rows, 114 actual
encoded public-protobuf successes, and 86 source-matched live observations
across 78 unique requests all pass. Every deterministic harness-view filename
and all five stored view fields match. Both clean endpoint replies equal the
original raw baseline bytes, not merely each other. Historical baseline/helper
source hashes are checked at their correct commits, not relabeled as current.

The four artifact row counts/bytes/SHA-256 match the durable inventory:

- Kind: 70 rows, 3,002,960 bytes,
  `78d05d6625b519bc4f7062b0c1b852a931824a729ee86ce9476ae0ce7b7cba6b`.
- Names: 12 rows, 4,325,111 bytes,
  `40f0d5d283e4a4a10ff4e69224e42da0ed2fbb3bd3a9cd88a75a2f34dbc77981`.
- Order: 2 rows, 1,970 bytes,
  `9be73ebf8690bca5a5f7561476f9fd10bf6260b29cb6fc7fd820995781b655f9`.
- Default: 2 rows, 2,761 bytes,
  `1efa5687a7a802bb8656642d41de03b9e038a527f9836cb7f88d36a53b9f3ed2`.

All eight restored candidate/fault source pairs compare exactly. Actual Json
retains its original `0d844312...443e` identity; new BlockCodecLaws is
`cdcdfe822bc1885032cea89eef862d1298546d471c6e3c8acf59597014a12736`.
Owner-attributed final gates are both packages/default audits with 595 spec
checks, 1,850 codec tests, 2,304 required Lean comparisons without skips, and
static checks. Reviewer independent runs are the 518/161/three-audit checks
and full provenance/replay work above, not a rerun of the owner's full gates.

No outstanding blocker. Main still owns combined integration. Export/Program,
host entries, validation and general malformed-input/ProtoJSON correctness
remain separate obligations, not consequences of these two roundtrip laws.
