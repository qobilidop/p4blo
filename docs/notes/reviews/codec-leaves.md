# Actual leaf codec proof review

Read-only review on 2026-09-23 of `p4blo-codec-proof`.
**Disposition: clear subject to mandatory root-owned integration
registration and the resulting merged gates.**
The test-oracle type-equality false acceptance confirmed below is now fixed
and independently tested. Restored native checks, mutation evidence and the
final persisted evidence note pass review. No candidate builds by this reviewer.

## Substantive proof boundary

Theorems mention the actual `Decode.decimal`, `Decode.uint32`,
`Literal.decode`/`Literal.toJson` and `Ty.decode`/`Ty.toJson`. They reduce
the real helpers and prove actual decimal folding; no alternate codec,
decoder-equivalence assumption, circular representability definition or
vacuous validity premise was introduced. The roundtrip theorem conclusions
recover the original abstract value, not an arbitrary canonicalized witness.

`UInt32` is precisely `n < 2^32`. Literal representability constrains width
only; type representability constrains bit width or stack size only. Empty
names, zero widths/sizes and decimal values larger than their width remain
in the wire domain. Kernel examples instantiate these deliberately invalid
but representable leaves. A complementary theorem rejects every overflowing
numeric uint32 with the actual diagnostic. No runtime bitvector allocation
is performed for the huge-width codec witnesses.

Omitted ordinary width/name/size fields are handled explicitly; false/empty
oneof cases stay present. Decimal zero is the explicit nonempty string
`"0"`. Five advertised audit roots guard standard foundations only. This
is a JSON-value left inverse, not arbitrary JSON text identity, complete
ProtoJSON acceptance, binary protobuf verification or Python correctness.
The documented partial-recursive decoder barrier and independent semantic
validity/version/unknown-field obligations remain appropriately separate.

## Independent data and confirmed test-oracle flaw

The test endpoint returns a semantic descriptor by inspecting the decoded
abstract constructor independently of production encoding. Python fixtures
specify expected tags, values and exact default/presence payloads; the public
protobuf JSON path is exercised by embedding raw leaves in an intentionally
unvalidated Program. Malformed leaf probes are expressly Lean-profile tests,
not a claim of rejection-language parity with protobuf.

**Confirmed finding:** `assert_leaf` compares ordinary Python dictionaries.
JSON Boolean false therefore compares equal to numeric zero, and true to
one; integer/float types can similarly collapse. I called the actual helper
with a scoped fake subprocess response containing numeric 0 in both the
semantic Boolean value and encoded Boolean field. It passed when both
expected values were false. No candidate binary ran and no artifact/source
was changed in that reproduction. This can hide precisely a wrong typed
encoding that an independent expected JSON payload should reject.

Requested type-sensitive recursive JSON comparison or explicit response
validation, plus a permanent false-to-zero response regression. Also
recommended parsing the **actual Lean encoded payload** through protobuf:
initial code separately parses only the independently supplied original
wire. These observations were sent to implementer and integrator.

**Resolution:** comparisons now use sorted JSON rendering, preserving the
Boolean/integer/float distinctions for parsed JSON values. Four fake-response
tests check rejection and retained raw artifact contents; three nested
controls establish the previously collapsing type pairs. The actual Lean
encoded payload is now passed through the public protobuf adapter path.
Independently ran the pure suite during the isolated-binary restoration:
**46 passed, 48 Lean probes deselected**, exit 0, with bytecode/cache writes
disabled and artifacts scoped to a reviewer temporary directory.

## Integration obligations

Root-owned export, default audit/executable and ordinary native test-driver
registration must land with integration. A test-only executable entry point
separate from the reusable `CodecLawTests` module avoids duplicate global
`main` definitions. Shared `lean_binary` fixture and `test_lean_agrees`
prefix retain required-gate discovery. Missing endpoint with a present
production Lean executable must fail, not skip.

The final evidence note records exact fault edits and tracked-fixture
reconstruction. Its replay script now requires exactly the three retained
artifact names, so a missing/empty artifact directory cannot report a false
success; calls are bounded and reject unexpected stderr.

## Independently executed restored checks

After stable-binary confirmation, all focused leaf tests pass:
**94 passed**, exit 0, with required Lean enabled. Executed the actual
`codec-leaves --self-test`: all **36 native checks pass**, exit 0. Queried
the five compiled theorem roots independently; each has exactly
`[propext, Classical.choice, Quot.sound]`. Confirmed production `Json.lean`
has no diff after restoration.

Inspected mutation logs: base-11 decimal folding, omitted decimal zero and
relaxed uint32 upper bound each compile the production codec but fail the
actual codec proof module. These are proof/build rejection, not runtime
semantic detections. The paired literal key rename `error` to `fault`
builds the codec, proof module and audit successfully, yet exactly three
independent canonical literal cases fail (36 passing controls). Retained
live-replay logs show all three malformed decoded outcomes and restored
replays return the intended values. This demonstrates why a left-inverse
alone does not establish conformance to the independent wire mapping.

Independently inspected all three retained artifacts: their requests and
expected observations match unique tracked test fixtures, their retained
mutant responses disagree, and actual restored endpoint replay agrees for
each. File byte lengths and SHA256:

- `leaf-20ed59fac41b5ec549d280dc.json`: 350 bytes,
  `5aaad7b02a93bb14f816a7d312e5b60d902da3c61e72d23bc2a529fe9b05f4b7`;
- `leaf-4258345fb66680b79d8b2c8c.json`: 401 bytes,
  `d14b92774c9ad1249290d37fcde38b971f34b3fc2449d9261e3f9b03e6e662be`;
- `leaf-aaacaa5bb2d071c2a03340df.json`: 329 bytes,
  `7dcfb245f49e52263fc909416ac0ca1059c075339cf4a4bf06b450989126d7a1`.

These are exact raw-leaf artifacts, not execution DRT bundles. Mutations
were not repeated by this reviewer. Full integration gates remain attributed
to the implementer/integrator and must not be confused with these independently
executed focused checks.

Final implementer full gate completed: inspected `/tmp/p4blo-codec-full.log`
ending in **1594 passed, 1 optional XDP-image skip, 5 existing strict xfails**
and `all checks passed`; implementer reports exit 0. The required Lean gate
has 294 passes. This closes the candidate full-gate qualification without
claiming the pending root registration/merged gate was already exercised.

## Integrated ordinary-gate registration

Independently inspected integration commit `1f69a58` and the resulting
`d8e2341` tree. Registration obligations are now satisfied: `CodecLaws`
is exported from `P4bloIR`; `CodecProofAudit` is a library and a default
build target; `codec-leaves` is a default executable rooted at the separate
`Tests.CodecLeaves` module; and `CodecLawTests.tests` runs inside the ordinary
spec test driver's failure-accounting computation. The five explicit axiom
guards remain present. The two-package script builds default targets and
runs both test drivers with the pinned toolchain and appropriate package
working directories.

The package-layout regression checks the audit's library/default-target
registration and the leaf executable's root/default-target registration.
Independently executed that file against the integrated tree: **4 passed**,
exit 0, without rebuilding either package. Root reports the merged Lean
gate passed with **428 spec checks** and all user checks, and the required
DRT gate passed **321 tests**; those merged gate results are attributed,
not repeated here. Root's combined full gate was still running at review.

**Registration review: clear.** No remaining codec registration blocker;
ordinary merged full-gate completion remains the integrator's checkpoint.
