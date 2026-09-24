# Foundational declaration codec baseline review

Final review: clear for the test-only baseline checkpoint. Universal laws and
the planned actual-code fault campaigns remain separate obligations.

2026-09-23. Candidate `/Users/qobilidop/my/work/p4blo-declaration-codec`, base
`c146126`. Independently read all six changed/new files and the actual nine
production decoder definitions. Candidate source and binaries were frozen;
no candidate edits or rebuilds were performed.

## Observation and scope

The dedicated Lean observer describes every field of all nine declarations.
Direction is observed by direct constructor matching, independent of the
shared production enum table; separately written native literal-wire anchors
cover all four constructors. Existing Ty/Literal constructor descriptors are
reused, not the encoded JSON. The endpoint delegates old kinds unchanged and
both native entrypoints register the additional checks.

The independent Python fixtures cover wire-representable but semantically
invalid declarations: empty/duplicate/unresolved names, aggregate header
fields, empty enums, all parameter directions including non-input constructor
parameters, zero/max widths and sizes, and unbounded literal values. Distinct
ordered fields/parameters/arguments and asymmetric extern names/methods make
permutation or slot-swap errors observable. Optional absent/null returns are
distinct from a present empty type. Public protobuf parsing/dump/load uses
minimal wrappers without a validator or Index.build filtering these cases.

Inspected the malformed/default matrix against actual decode order: names
before type/direction; Method params before returns; ExternType constructor
params before methods; instance name before extern_type before arguments.
Nested first-error paths, later indices, unspecified/numeric direction and
normalization controls are anchored independently. Strict harness equality
and duplicate-rejecting JSON parsing prevent Boolean/integer observational
collapse. This is not an assertion of identical ProtoJSON acceptance languages.

## Independent executed checks

- New focused declaration file: 319 passed, exit 0, 5.03 seconds.
- Actual compiled `codec-leaves --self-test`: exit 0, including all 14 new
  native direction/order/default/error observations and prior codec checks.
- Loaded the retained artifact with strict JSON; checked format/base, exact
  size 189142 bytes and SHA-256
  `a38bc43a8feb08db437ff371925ba1d23d446182aa5906e1cadd462f15d4e2b1`.
- Checked every recorded source hash against the frozen files; actual Json
  bytes also equal `git show c146126:ir/P4bloIR/Json.lean`, SHA-256
  `0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.
- Source-matched all 247 ordered requests and independent expected answers,
  requiring unique compact-plus-LF inputs, integer exit status 0 and empty
  stderr. Re-executed every raw input: stdout/stderr/status match exactly.
  All 102 successful actual outputs passed the public protobuf wrapper;
  the remaining 145 replies match exact independent diagnostics.
- Production IR/Json/JsonBounds tracked diff is empty; working changes are
  confined to the six declared test/registration/note files.

The owner's complete two-package gate, 520 spec checks, 814 all-codec focused
checks and static checks are attributed to its logs; they are not substituted
for the independent executions above. Required/full integration gates were
not claimed for this preliminary checkpoint.

## Provenance and disposition

The durable capture recipe checks actual production bytes against the old
commit before launching the endpoint, rejects an existing destination,
asserts the exact nonzero unique request inventory, uses strict JSON and
independent answers, and rechecks source hashes after capture. Later proof
work must validate old hashes against this committed baseline, not falsely
compare changed test/witness files to old bytes or overwrite the artifact.

No blocker found. Land this baseline separately before the universal laws.
Final proof review must still inspect wire-only predicates, default audits,
constructive witnesses, paired Direction/name observer challenges, actual
compiling error/default faults, and exact live/restored replay provenance.
