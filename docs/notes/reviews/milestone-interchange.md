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
