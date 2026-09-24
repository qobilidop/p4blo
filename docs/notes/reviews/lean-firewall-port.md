# Lean tutorial firewall source/execution review

Final review: CLEAR for source authoring and bounded persistent execution.
The subsequent initialization/invalid-body proof phase is not part of this review.

2026-09-23. Read-only review of `p4blo-lean-firewall` source/execution phase.
The planned invalid-IPv4 body and seven-local initialization proofs are a
separate subsequent phase and are not supplied by these files.

## Source and execution boundary

Read complete TutorialFirewall source and main, Python corpus source, new
test module, reused state observer and boundary/profile helpers, public export
and default executable registration. The Lean Program is genuinely authored
from constructors/named paths, not loaded from the golden or Python. Shared
Forwarder protocol layouts/checksum expression are reused as data only; the
new three-header/seven-local roots do not import its two-header frame proof.

Visible source preserves parser extraction/select order, all five actions,
both tables/defaults, seven locals and both 4096-bit registers. Hash input is
the left-associated 104-bit tuple with direction-dependent address AND port
reversal; masking/cast widths match the Python source. Routing precedes TCP
classification; filtering requires an actual hit; outbound SYN-bit insertion,
inbound two-bit Bloom check, drop port 511, wrapping TTL and checksum-after-drop
are retained. No behavior is hidden in a new extern or architecture shortcut.

The fixed runner prepares this authored Program once, accepts only host entries,
ingress and packet, and threads returned extern state between requests. It
reports complete registered extern observations after each request. Error
responses preserve the current runner state; the present focused acceptance
profiles cover successful requests rather than a general error-recovery claim.

## Independent observation

Program identity compares both independent Python authoring and frozen golden,
then validates. Both known STF filenames and nonempty requests are guarded.
Known sequence and generated profiles compare independent packet answers and
all 8192 register cells after every packet, preserving history in both loaded
Python state and one fixed Lean process. Missing/wrong externs, cell widths,
array lengths, cell values and envelope shape are checked. Existing strict
state decoding rejects extra per-extern fields and noncanonical cell values.

After the owner released stable binaries, independently ran identity, six known
sequences, default-target and four malformed-state controls: 12 passed,
115 deselected, exit 0 (1.38 seconds). This was not a full suite or proof gate.

## Follow-up requested before final review

The current automatic replay retention runs generic Lean-from-JSON comparison
before the fixed runner. A fault confined to the new runner's persistence can
therefore pass that comparison and fail the later fixed observation without a
saved fixed-runner transcript/complete sequence. Requested explicit retention
or a durable exact reconstruction regression, with an actual state-reset fault
that persistence cases kill. Such evidence must not be mislabeled as a generic
interpreter inconsistency or a new unique corpus input.

The current known-sequence diagnostic comparison uses truthiness. These
profiles independently expect no diagnostic, so requested explicit absence
on both sides rather than only agreement on presence. No exact parser-cursor,
internal frame, arbitrary extern, original-oracle rerun or complete firewall
correctness claim follows from the present packet/state tests.

## Fixed-runner retention hardening

Read the revised helper: completed-process nonzero/stderr/protocol/output/state
failures save a separate fixed-runner record with full reference Program,
ports, exact request stream and raw stdout/stderr/exit status. The helper now
requires diagnostic absence explicitly. It neither pretends the record is a
generic DRT bundle nor silently accepts a reset between packets. Launch and
timeout errors are outside this completed-process retention claim.

The permanent regression actually runs the native executable in a fresh process
for each of four requests, rather than fabricating replies. It requires four
actual invocations, generic interpreter agreement, saved complete input, a
lost-state/drop witness, and restored independent output/state agreement.
Independent complete revised suite: 128 passed, exit 0 (19.98 seconds), including
the generated forty-example profile and this retention regression.

Inspected the actual isolated compiled runner fault logs: changing runSwitch's
state input to initial compiles successfully; generic execution still agrees
on all four requests, while fixed execution loses Bloom state and drops the
third established-flow response. Independently loaded that raw record, verified
the exact golden/builder Program and tracked connection() request sequence,
clean status/stderr, full replies and concrete lost-state observation. Replayed
the saved exact stdin against the unmodified candidate: all four independent
packet answers and full 8192-cell snapshots pass with no diagnostics/errors.
Artifact: 331,679 bytes, SHA-256
`6dd40faa8dbd00129dd11f6831bc42e3c5b35046beba3bf8324b5fd2a1d6f161`.
The requested test gaps are closed. Final source-intent campaign/restoration,
durable note and owner acceptance gates are still pending.

## Final source campaign and execution-phase disposition

Read the final durable note and actual logs. A compiled literal-true hit-guard
fault fails independent whole-Program identity; both engines nevertheless
agree on that same wrong Program, while the independent missing-direction-SYN
model rejects unintended Bloom insertion. This is appropriately a source-intent
failure, not a proof rejection or engine inconsistency.

The actual Python Register.call write omission compiles and yields three clean
state divergences plus one agreement over connection()'s four inputs. Live
replay reproduces them, restored replay agrees. Independently verified the
complete retained Program/request/entries/ports=4/seed=0 against the golden and
tracked helpers, then replayed it against the clean candidate: four agreements,
zero errors. Bundle is 76,260 bytes, SHA-256
`c547f2999038dae030dfd93402e7e26a73782f0424384fda9633a5ee7e886103`;
independently byte-compared to main's prior firewall-crc32 bundle. Same inputs
under a new fault are not counted as new unique witnesses. The fixed reset
transcript likewise adds distinct protocol evidence for those same inputs.

Independently compared all four restored source files (TutorialFirewall, main,
Python observer and Register) across candidate/fault tree, and verified empty
Register runtime diffs. Fresh exports from both restored executables match:
13,588 bytes, SHA-256
`5342abef71eb652082d9bf2cf09ba6059b66d3f135ee7742c23fb58380722ecd`.
The integrator retained reset transcript was also independently hash/size checked;
owner subsequently copied it to the same documented candidate-relative path.

Owner-attributed final gates, corroborated by logs: both package/default/native
gates pass (540 spec checks), required 1,418 pass/1,701 deselected/no skips,
full Python/schema/static/workflow gate 3,113 pass with five existing strict
expected discrepancies and one explicit unavailable local XDP-image skip.
Independent 128-test execution and replay checks are recorded above; this
reviewer did not repeat the expensive full oracle suite.

No unresolved finding remains for this source/execution checkpoint. A newly
unregistered TutorialFirewallProof file begun afterward is explicitly excluded
from clearance and the two source/execution commits. Actual nine-root/seven-local
initialization and whole-Run invalid-IPv4 body identity remain the next separately
reviewed obligations; neither they nor a complete firewall milestone are claimed
by this approval.
