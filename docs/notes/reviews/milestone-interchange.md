# Milestone interchange review

2026-09-23. Independent read-only review of the `frame_initialization` agent's
`work/milestone-interchange` candidate, performed from the usability agent's
separate worktree. No candidate edits, builds or production changes by the
reviewer. Acceptance is the finite `milestone-1.md` checklist and current
profile, not a new codec or application proof ladder.

## Codec baseline: CLEAR

The inspected baseline consists of new `Tests.ProgramCodec` and
`Tests.EntriesCodec`, their endpoint/native registration, the two Python test
modules, shared label additions and `notes/milestone-interchange.md`. Production
syntax, codecs and interpreters are unchanged. This clearance permits a
separate coherent test-baseline commit; it does **not** close host rejection
or fault-sensitivity acceptance.

Compared the descriptors and independent fixture inventory against all eleven
Program schema/Lean fields and all four TableEntries fields. Export role/block,
headers/metadata and block/table have asymmetric anchors. Ordered, duplicated,
empty and unresolved names remain deliberately invalid-but-representable data.
Whole-program success does not establish validator acceptance. Native literal
JSON is compared to separately written constructors, while the endpoint's
value observer reads actual decoded fields without calling the encoder.

Python canonical successes use public `ir.load_json`/`ir.dump_json` and actual
protobuf Entries conversion, not a private substitute adapter. Expected wire
and decoded-value fixtures do not call production encoders/decoders. Existing
component fixtures are reused explicitly rather than miscounted as newly
independent evidence. Strict JSON rendering preserves bool/int distinctions.
Optional defaults distinguish none/null from present empty ActionCall; list
order, inherited uint32 boundaries, nested paths and competing-error order
are exercised. Numeric enums/camelCase/unknown-field acceptance differences
are labeled outside the shared canonical contract, not normalized as parity.

Independent execution against owner-released stable binaries:

- `nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest
  tests/test_codec_program.py tests/test_codec_entries.py -q`: **203 passed**,
  exit 0 (`/tmp/p4blo-interchange-review-focused.log`).
- `ir/.lake/build/bin/codec-leaves --self-test`: exit 0, including both new
  constructor/presence suites (`/tmp/p4blo-interchange-review-native.log`).
- Source-pinned capture independently checked: 22 current source SHA-256s;
  all 165 exact request/expected/stdin/stdout pairs, empty stderr and zero
  statuses; all 73 successful encodings passed the actual public protobuf
  conversions. Capture size **813788** bytes and SHA-256
  `ac4bf8faed73c025be23086bcb20acbf958c20a07c7430e4048da3063aee496e` match.

Owner-attributed both-package/old-codec/static gates are recorded in the
implementation note; they were not rerun by this reviewer. No theorem or
runtime fault-detection claim is added by these baseline checks.

## Remaining scoped review

Host decode/validation/installation rejection, complete strict detached state,
no-packet-entry observers and continuation after rejection still need their
own implementation and review. Pure Lean Except failure alone cannot reveal
discarded intermediate execution; the planned native parser trap addresses
the explicit first-error boundary. The paired codec fault and actual host
side-effect fault also remain pending. Final milestone closure must not treat
this baseline clearance as clearance of those later obligations.

## Host slice: structural and executable checks clear

The host candidate adds 14 decode/install rejection profiles with a valid /
rejected / valid sequence, independent complete two-counter answers, actual
packet-entry call counts, startup decode/validation negatives, and actual
Lean missing-parser trap controls. Native traps are correctly described as
operational error precedence, not a theorem that no discarded work can occur.

Root's first concrete observer finding is fixed in the inspected draft:
logical counter serialization turns both `1` and `True` into `"0x1"`; raw
strict `freeze(loaded.externs)` now rejects that mutation, with a retained
single-hit survivor/strong-observer regression.

Reviewer found a second concrete type-confusion survivor in the remaining
ordinary metadata equality. In an isolated Python process, a wrapper delegates
actual `Loaded.entries`, catches `InstallError`, then changes
`loaded.metadata.contract.fields[0].provided` from `True` to integer `1`
using `object.__setattr__`. The full `observe_rejected_host(target)` completed
successfully, with exactly one hook hit. The frozen dataclass/dictionary
comparison accepted equal numeric contents of different types. Owner and
root received the exact recipe; strict detached config snapshots and a
retained negative are requested before final clearance. No candidate source
or runtime was edited by the reviewer. An earlier attempted slot-zero probe
had zero hits because this small fixture has no metadata slots, and is
explicitly excluded as evidence.

Finding resolved: the owner replaced index, metadata, roles and installed
configuration comparisons with strict detached `freeze` snapshots, retaining
the extern check. The added metadata regression restores the shared contract
in `finally`, including on assertion failure. Reviewer independently retried
the original delegating one-hit fault: it now rejects with the exact
`rejected host changed metadata configuration` assertion.

Against the released final source/binaries, reviewer independently ran the
two codec test modules: **239 passed**, exit 0
(`/tmp/p4blo-interchange-review-host-focused.log`). The endpoint self-test
also exits 0 with **193** anchors, including the three actual host/parser-trap
controls (`/tmp/p4blo-interchange-review-host-native.log`). No additional
source finding; final sensitivity/restoration note inspection remains pending.

## Final host and sensitivity disposition: CLEAR

The later sections supersede the chronological pending statuses above. Final
source, recorded campaigns and restored execution have now been inspected;
no remaining correction is requested. Ordinary required/combined integration
gates remain the owner's/root's responsibility, not implied by this review.

The paired real Program decoder/encoder swap compiled successfully. Inspected
ordinary test logs show five failures / 122 passes and two native anchor
failures, with genuine wrong decoded nominal slots and first-error order.
The minimal retained object has unchanged encoded JSON but the wrong decoded
headers/metadata slots; this demonstrates independent observation beyond a
roundtrip. This is a compiled codec fault, not a theorem rejection or setup
failure. Mutating the actual Python `Loaded.entries` rejection branch to
increment unused ticks[1] also compiled; 12 installation profiles fail while
two decode-only controls pass. The strict-source repeat is the same fault
and request, not another input/campaign.

Reviewer independently ran the note's complete read-only restoration recipe
after inspecting it. Exit 0 (`/tmp/p4blo-interchange-review-final-replay.log`):

- all 22 historical baseline source hashes resolve at `e03cd7a`, preserving
  the pre-formatting baseline instead of silently repinning it;
- current fixture request/answer identities match all 165 historical rows;
  both restored endpoints produce byte-exact historical replies;
- both source mutations reconstruct in memory to their recorded mutant
  hashes without editing production files;
- representative field and host artifacts match tracked fixtures, complete
  Program/config/packet inputs, raw replies/state and expected errors;
- restored field decoding gives the independent answer on both endpoints;
  restored host rejection preserves state and the subsequent valid packet
  advances exactly to the second independent full-array answer;
- all six candidate/fault-tree source pairs are byte-identical, and production
  Json/loader files have no candidate diff.

Independently checked final artifact hashes/sizes:

- paired field: 1366 bytes,
  `f5b5cf7ce22e6be04f4805a49a57caef85041bf44273429aa659ec3d8deadcef`;
- strict host: 10573 bytes,
  `ca3cf93868c5936598b286463c0b3a512fce0b31c4e495d72081300e6742e682`.

The superseded pre-strict host capture is explicitly not extra evidence.
Host evidence is accurately labeled a direct rejected-request state witness,
not fabricated as a packet DRT divergence. The finite fixture does not claim
global validator equivalence, rollback after execution faults, hardened JSON
acceptance or universal Python correctness. No optional proof work is needed
for this closeout slice. Reviewer has no active candidate consumers.

Final owner gate addendum: inspected the completed post-review required-gate
log, **2882 passed / 1875 deselected**, exit 0 (190.33 seconds), at
`/tmp/p4blo-milestone-required-final.log`. The implementation note now records
that result and final static/restored checks; no pending owner-result line
remains. Root still owns the final combined main/release gate.
