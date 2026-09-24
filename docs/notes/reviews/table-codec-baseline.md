# Table declaration codec baseline review

Final review: clear for the test-only baseline checkpoint. No universal
Table codec or table-execution proof is approved by this baseline review.

2026-09-23. Read-only candidate `p4blo-table-codec`, base `58bb072`.
Read all six changed/new files, including the complete native/Python fixtures,
endpoint registrations and provenance recipe. Candidate was frozen; no edits
or builds performed.

The four new endpoint labels preserve old `key` meaning KeyValue, while
`table_key` observes Key. All fields of Key/ActionCall/Entry/Table are observed
independently of encoded JSON; MatchKind has direct constructor cases and
separate literal native anchors. Existing expression/literal/key-value
descriptors are reused without replacing their meanings or request sets.

Fixtures include arbitrary invalid-but-wire-representable declarations, all
match/embedded syntax families, asymmetric arrays/strings/arguments, optional
defaults and both const flags, zero/max and propagated overflow boundaries.
The important distinction is explicit: Entry absent/null/empty action succeeds
and re-encodes as action:{}, while Table absent/null default is none and {}
is some empty call. Public protobuf wrappers preserve empty-message presence
using SetInParent and do not apply semantic validation or Index construction.
Competing-error cases follow actual field order and exact nested indices.

Independent executed checks:

- Focused new table suite: 235 passed, exit 0, 3.76 seconds.
- Native actual codec self-test: 106 checks, exit 0, including 20 new checks.
- Loaded the artifact strictly; verified 181 unique ordered source-matched
  requests, exact compact-plus-LF stdin, independent expected answers and
  integer-zero status/empty stderr. Replayed all raw responses byte-for-byte.
- All 82 actual successful responses pass public protobuf wrapper checks;
  the other 99 match exact independent errors.
- Verified all eleven source hashes, and production Json bytes against
  `git show 58bb072:ir/P4bloIR/Json.lean`, unchanged SHA
  `0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.
- Artifact size 320705 bytes; SHA-256
  `d801a79376f9bf2f786a176b3173535f851b391aeac947a48951d0e7148cc40c`.

Owner's both-package/default/native 540-check gate, all-codec 1049 focused
checks and static gates remain separately attributed. The capture recipe
guards production bytes before children, refuses existing output, asserts
exact nonempty unique inventory, uses strict parsing and rechecks all source
hashes afterward. Later witness additions must be compared to historical
baseline hashes, not silently recaptured over this evidence.

No blocker found. Commit this baseline separately, then review the four
wire-only universal laws, constructive witnesses, default audits and planned
actual enum/bool/ordering/optional-default mutation campaigns. Successful
codec observations do not imply semantic validity, matching behavior,
whole-Program coverage or universal Python equivalence.
