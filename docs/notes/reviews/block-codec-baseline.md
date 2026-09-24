# Action and Block codec baseline review

Final baseline review: clear for its separate test-only commit. No new universal
laws or shared-helper extraction are approved by this baseline review.

2026-09-23. Independently read all six changed/new files in `p4blo-block-codecs`
against `ca2f20f` and the reviewed acceptance plan. No candidate source edit or
build was performed; all observations used the released frozen binaries.

## Independent answers and scope

The two new labels are distinct from ActionCall and preserve prior dispatch
fallbacks. Native descriptors directly pattern-match the three BlockKinds and
observe every Action/Block field and ordered nested element through prior
independent member descriptors. They do not reuse the production shared enum
mapping or encoded output as an abstract-value oracle.

Literal native constructor answers and separate kind-descriptor anchors cover
all three kinds, full mixed records regardless of kind, all four directions,
empty/duplicate/unresolved names, malformed/default enum forms, adjacent error
precedence and nested later-index diagnostics. The mixed block distinguishes
name/start_state and ordered members, retains parser bodies and control states,
and tests both absent and present-empty table defaults. No validation or
runtime behavior is silently imposed on representable wire values.

Python covers nineteen canonical records, 384 exact failures and 95 normalized
successes. Large canonical records intentionally compose every prior member
family; reversed/asymmetric records distinguish order. Nested malformed
members retain independently authored earlier diagnostics at a new later
array index rather than generating answers from the Lean decoder. Missing,
null, empty and wrong-type forms are separate. Complete strict JSON comparison
and actual public protobuf Program dump/load preserve message presence with
SetInParent without requiring the transport wrapper to be semantically valid.

## Independent executable/provenance checks

- Focused test file: **518 passed**, exit 0, 10.37 seconds.
- Compiled endpoint self-test: **161 checks**, exit 0, empty stderr.
- Exactly **498 unique ordered requests**, each current request and independent
  expected answer matched to its frozen row, including exact compact-plus-LF
  stdin and actual raw stdout/stderr/exit-status replay.
- All **114 actual successful encoded replies** independently pass the public
  protobuf wrapper and strict canonical-output checks.
- All **eighteen recorded source hashes** match the frozen candidate; actual
  Json bytes equal the original `ca2f20f` git object. No codec/helper/runtime
  source changed.

The retained artifact has 3568250 bytes and SHA-256
`910a517c0832f9ae2413577c18a774de51290c6e775bf4be07f8398796bef49e`,
independently checked. Its documented reconstruction checks original Json and
nonexistence before children, uses strict duplicate-rejecting parsing and checks
sources again afterward. Later witness/helper changes must use historical
baseline source identities rather than rewriting this capture.

Owner-attributed gates are both complete Lean/default suites (595 spec checks),
all 1332 old codec tests and scoped format/lint/type checks. Those broader checks
were not independently rerun here. The modified registrations only append the
new native suite, endpoint labels and CodecKind union.

No blocker found. This captures the unchanged codec's behavior and independent
intent before proof work; it does not prove Action/Block roundtrip, Program
composition, semantic validity, normalization completeness or execution.
