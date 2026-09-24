# Foundational declaration codec laws review

Final review: clear; chronological investigation follows below. Root's full
combined integration gate remains a separately recorded obligation.

2026-09-23. Read-only candidate `p4blo-declaration-codec`, following the
separately reviewed and committed test-only baseline `21b0fec`. No candidate
edits or rebuilds; executable checks use owner-confirmed frozen binaries.

## Universal laws

Read all nine representability predicates, actual-codec proofs, constructive
witnesses, negative bounds and public/default-audit registrations. Predicates
are exactly embedded wire bounds: TypeRepresentable for fields/variables/
parameters, recursive finite member coverage for the record lists, optional
return coverage and LiteralRepresentable for extern arguments. EnumType is
unconditionally representable and its theorem appropriately has no premise.
No semantic name, direction, header-field, resolution or arity restriction is
smuggled into successful roundtrip premises.

The proofs expose the actual declaration decoder/encoder records, handle
omitted empty names/lists and present optional types, then reuse existing
actual Ty/Literal and array laws at every member path. There is no alternate
decoder, new runtime implementation, fuel bound or callback assuming whole
declaration correctness. String names and finite list lengths are arbitrary;
all four Direction constructors are handled, including directionless NONE.

The mixed kernel witness covers every selected declaration, all embedded
Ty/Literal families and all directions, deliberately retaining semantically
invalid declarations. Explicit negative examples cover overflowing leaves,
optional returns and both extern-type lists. All nine laws plus this combined
witness are registered in the existing default audit. Production Json is
intended to remain byte-identical throughout this proof increment.

## Independent checks so far

- Fresh pinned Lean queries of all ten audit roots: exit 0, each exactly
  `[propext, Classical.choice, Quot.sound]`.
- New focused declaration suite against frozen actual binaries: 319 passed,
  exit 0, 5.77 seconds.
- Actual codec native executable: exit 0, 86 checks including the 14 new
  independent declaration anchors.
- All 247 original raw transcripts replay byte-for-byte against the proof
  candidate; their requests/expected answers match current tracked fixtures.
  Every old source hash is validated against committed baseline `21b0fec`,
  not incorrectly against the now-extended witness source. The retained
  baseline SHA remains
  `a38bc43a8feb08db437ff371925ba1d23d446182aa5906e1cadd462f15d4e2b1`.

## Campaign boundaries under review

The note correctly distinguishes a real shared Direction table fault from
ordinary packet-runner preflight failure. A failed checksum signature before
test bodies run cannot count as five semantic codec observations. Invoking
the existing 319 strict test bodies directly against the actual codec endpoint
is an appropriate separately labeled codec campaign, not required packet DRT.
The paired expected-fixture and descriptor corruptions must be reported as
survivors of those direct Python checks, with independently authored native
anchors providing the remaining detection. Exact final logs, provenance,
source restoration and raw live/restored bundles remain to be checked before
final clearance.

## Final campaign and restoration closure

The pending statements above are historical. Inspected the final complete
note and actual logs. The one-sided HeaderType field reversal compiles actual
Json, then fails the unchanged universal proof at the nonempty-list equality;
this is not a syntax/lint failure or a runtime mismatch. Shared Direction
swapping, paired instance labels and changed Param error order all compile
the actual endpoint and unchanged default audits. Direct strict codec checks
reject respectively five value observations, one value plus one precedence
observation, and 17 exact diagnostics. Native literal anchors reject each.

The ordinary faulty Direction pytest runs stop 247 endpoint cases in fixture
setup (72 pure Python checks pass); they do not count as the five independent
codec detections. Inspected the separately documented direct 319-body runner
and logs establishing those detections. Pairing the actual Direction fault
with corrupt Python expectations makes all 319 direct bodies pass while two
native anchors fail. Pairing it instead with the Lean constructor observer
also makes all 319 pass while four native anchors fail. These are honestly
recorded survivors demonstrating the need for independent literal anchors,
not inflated proof or differential guarantees.

Independently reconstructed each actual Direction/name/order production
patch in memory from the clean source and matched its recorded mutant Json
SHA. Unchanged law/descriptor/fixture hashes in all bundles also match the
clean candidate. Verified 24 distinct source-matched requests and genuine
clean-exit mismatches, with 24 equivalent harness views—not 48 inputs. Checked
all request-derived harness filenames. Primary bundle sizes and hashes:

- Direction: 5 rows, 33706 bytes,
  `fe10de274ff7e5c9f6a3dd121f6cf978e754b519b735ba4bfbccc1bec1d2c880`.
- Instance labels: 2 rows, 16233 bytes,
  `a18f896fa322110a5aba9457015c1af9524b3d8790c157699f778f32c15bfe11`.
- Param order: 17 rows, 10915 bytes,
  `6bbfe29af92580ec1420b26d255630c631241531fc2204588405c3dc19db8a74`.

Independently replayed every retained request against BOTH restored endpoints:
all agree with tracked independent expected answers, with clean status/stderr.
Byte-compared candidate and restored fault-tree Json, declaration laws,
declaration tests and Python fixtures; all four match exactly. Inspected
restored default build, ordinary shared-fixture 319-test success and 86 native
checks. The owner required gate reports 1069 passed / 1637 deselected, no skips,
exit 0; its wider 814 focused and both-package gates are owner-attributed.

The final note provides exact patches, live/direct/capture/replay recipes,
strict source provenance and explicit proof/runtime/preflight distinctions.
No remaining blocker found. Actual codec behavior is unchanged; the new
production content consists of proofs and exports. None of these laws proves
semantic declaration validity, full Program codec coverage, textual/binary
encoding, malformed-language equivalence, or general Python correctness.
