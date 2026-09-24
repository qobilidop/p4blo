# Actual forwarder ingress prefix review

Draft structural review: initial premise discrepancy resolved; core clear on
inspection, not final checkpoint clearance. No candidate execution or build
performed in this pass.

Read the complete first compiled ForwarderIngress module at 9a12253. The
literal first conditional, full independent checksum concatenation/destination
anchor, actual-body identity, valid application composition and exact pending
statement/K boundary are sound on inspection. `Ready` contains only actual
scope, BlockFrame and installed-state identities; it is required precisely
when the source bit tied to actual guard evaluation is true. The invalid
branch does not accidentally execute or require table readiness. The explicit
selected-list pop is present, and unindexed Steps is not mislabeled numeric.

The result policy is complete table policy on valid IPv4 and identity otherwise;
it adds no Ethernet/TTL/prior-drop guard. Whole Run, outside roots and real
populated-frame instance reuse existing concrete laws without replacing actual
execution by callbacks. Checksum dispatch itself remains unexecuted.

## Premise discrepancy to resolve

The current `invalid_steps` requires `FrameMatches store run.frame` for both
source roots, hdr and meta. That is stronger than its comment "Only the actual
header read is needed" and the accepted header-only invalid boundary. It
excludes arbitrary/missing metadata and arbitrary unused malformed header
contents which the already committed `ForwarderProof.invalid_guard` supports.

Recommended small fix: expose a raw header-only invalid-prefix theorem with
actual index plus `frame.read? "hdr" = some (invalidHeaders ethernet values)`.
Compose the same three actual steps using the existing invalid_guard fact,
then derive the typed-store invalid theorem as a convenience corollary. Keep
normal typed profiles and operational malformed/absent-state controls labeled
separately. This is a scope/premise issue, not an unsound proof.

After the fix, independent native/audit/Python tests and actual mutation,
source restoration and retained replay evidence remain to be reviewed.

## Resolution

Re-read the added `invalid_steps_header`: it uses only actual index and the
action-first read of hdr as invalidHeaders with arbitrary Ethernet value and
IPv4 field list. It composes the committed actual invalid_guard through the
three real steps. The typed-store invalid_steps now derives that concrete
header witness and invokes the raw theorem, rather than duplicating a stronger
premise as the only public boundary. This resolves the reported scope gap.
Planned absent/malformed metadata, poison unused state and shadowed-header
native/Python controls remain important nonvacuity checks, not yet run here.
