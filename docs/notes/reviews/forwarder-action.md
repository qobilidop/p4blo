# Real forwarder selected-action review

Final review: CLEAR. Chronological investigation and resolved observer findings
follow; the concluding section records final evidence and its limits.

2026-09-23. Read-only early pass of the complete logically stable
`lean/P4blo/ForwarderAction.lean` in `p4blo-forwarder-action`, alongside the
accepted action plan, committed initialization proof and actual Exec dispatch.
Owner is developing consumers separately; no candidate binaries consumed or
libraries rebuilt for this pass.

## Independent meaning and actual premises

Snapshot covers all 20 stored components of the real source shapes, including
both validity bits, IPv4 checksum, ingress/egress ports and prior drop.
Direct constructor-based observe/restore avoid authored Ref accessors and
evaluation. The policy sets egress from the action parameter, source MAC from
the old destination, destination from the other parameter and TTL via modular
addition of 255; every omitted field is preserved. Correspondence to actual
IR subtraction is explicit, so TTL zero is not implicitly excluded.

Actual scope action lookup and complete four-assignment body identity are
checked against Forwarder. The public theorem requires the real index/scope,
action-free OUTER block frame and independently matching source store.
Fresh actual action storage contains dstAddr/port only. hdr/meta writes use
the reviewed target-only unshadowed law, never a false BlockFrame premise
inside the installed action. Operational unrelated block bindings and decoys
remain possible; no synthetic checksum local or action typing claim appears.

The constructive populated witness derives scope from the same successful
actual Frame.forBlock initialization already proved for the corpus. It then
installs actual hdr/meta arguments for every source store. This is not a fake
scope/body or a correctness callback.

## Queue and normal-return composition

The entry equation is actual Work.tableAction: scope lookup, real argument
length check and literal-value binding queue the authored statements followed
by actionReturn of the original frame with copy=None. It is not the distinct
direct-action call path with optional argument copyback.

before_return constructs ten explicit real transitions: entry, four pairs of
list/assignment transitions, and empty-list pop. It stops with actionReturn
and arbitrary K still pending. source_steps composes precisely one actual
normal actionReturn step. Its result retains all inner block writes while
restoring original action/actionVars; it does not restore the old entire
frame or use block return. The exact four ordered map updates preserve the
original scope/index/shared components and every other block binding.

run_correct specializes K=[] and uses the existing Finishes.sound theorem
for actual runActionCall. result_matches identifies the final independent
policy source, while ChangesOnlyVars and PreservesOutside state exact
noninterference. No route-selection, parser, checksum, fault-unwind, arbitrary
nested-action validity or whole-forwarding theorem is inferred.

No structural blocker found. The count is evidenced by the explicit proof
chain; Steps itself is not numerically indexed, so native independent 10/11
boundary and pending-K controls must still anchor the count claim. Also
requested an asymmetric direct constructor-to-Snapshot anchor: inverse laws
alone cannot reject consistently paired observation/restoration remapping.

Final review still owes those test observations, strict Python active/final
frame inspection, all parameter/lookup/arity controls, full-body identity,
standard audit roots and actual mutation/live-restored evidence. This draft
must not be treated as checkpoint clearance.

## Stable core/native checkpoint

After owner released frozen binaries, read the complete native test module.
Its literal asymmetric header/metadata answers do not call the source policy;
the additional raw constructor anchor pins restore's field meaning beyond
inverse-law self-consistency. Forty-eight cases cover both validities, prior
drop, TTL 0/1/255 and low/high action data, with operational parameter-name
decoys in the block map and independent complete state comparisons.

The native checks distinguish ten pending transitions from eleven returned
transitions with empty, write and fault continuations; one further step makes
each nonempty continuation observably act. Bad arity rejects before frame
installation. Shared state comparisons use the prior complete index/scope/
installed-state comparator, not index.program alone.

Fresh independent pinned Lean query checked all eleven default audit roots
plus action_lookup: inverse laws have no axioms, the others exactly the
standard three. Direct #eval of 48 answers/144 pending boundaries and the
compiled complete userTests executable both exited 0.
Python observers and adversarial campaigns are still pending, so disposition
remains draft rather than final clearance.

## Python observer pass and two bounded survivors

Read the complete initial Python observer and independently ran its 74 focused
tests, exit 0 (7.15 seconds). Main active-entry, completed-body and returned
observations use independently constructed complete state with strict detached
freeze; all 48 native exports are checked once with exact profile inventory,
body/parameter identity and strict JSON types. The actual run_action_call
returns normally without a sentinel exception. Packet-fault retention is
separate from the normal action-state observation.

Found two genuine survivors in the extra post-observation action-hit Env.write
probes. A process-local wrapper delegates the real write and, only for active
port:=Bits(9,1), either stores Bits(9,True) or clears the OTHER dstAddr parameter
to zero. In both experiments the fault executes once and observe_action
returns successfully: ordinary Bits equality accepts bool/int equivalence;
the second probe write repairs the other parameter before the final checks.
These are limited to the additional write-branch observation, not a counterexample
to the action theorem or the main normal-call state checks.

Requested strict complete INNER-state comparison after each individual probe
write against an independently updated expected action map, plus the existing
unchanged outer-state check, retaining both mutations as regressions. Final
review awaits this test-only hardening and the actual isolated source campaign.

The post-write hardening is now implemented: independently constructed whole
inner snapshots are frozen before runtime, then compared immediately after
each individual actual write, together with unchanged outer snapshots. Both
reviewer-found faults are retained and each must execute exactly once. Read
the complete change; it closes the value-type and temporarily damaged sibling
gaps without using the runtime result as its expected answer.
Independent revised focused suite: 76 passed, exit 0, 6.95 seconds. Final
campaign evidence remains pending; this does not yet close the checkpoint.

## Final campaign and restoration closure

Read the completed durable note and actual mutation logs. Five actual Lean
edits compile their affected runtime/source module, then fail the unchanged
action proof: restoring the entire old frame loses block writes; omitting
action-layer restoration leaves the installed action name/map; reversed
binding swaps the real values; swapped MAC assignments break the actual body
and transition equations; saturating subtraction leaves a genuinely false
modular arithmetic obligation. The additional unused-simp lint error in the
last log is not the evidence counted. These are proof rejections, not runtime
Lean/Python conformance detections.

The low destination fixture change compiles both packages, audits and native
checks, then fails Python's independent literal-binding contract. This is
correctly classified as a compiled fixture-intent fault: the universal action
theorem remains valid for the changed parameter.

Inspected the actual Python source-edit campaign: omitting only the authored
destination member write compiles, completes the real action, and fails the
strict complete active-state answer. Its separately retained full-program
packet replay diverges cleanly with only the destination MAC wrong, then agrees
after restoration. No setup failure, exception hook or joint error is counted.

Independently compared seven candidate/restored source files, including Exec,
Eval, expr.py, authored Forwarder, action proof, native profiles and Python
observer: all byte-identical; runtime/authored-program git diffs are empty.
Loaded both saved bundle copies and verified exact tracked golden Program,
edge_case(0), installed entries/packet, ports=4 and seed=0. Size 27,697 bytes,
SHA-256 `27376cf7dfe17455b40b849323b35186b471c0b432b01495aa7bd3d9dc0b9c4b`.
Independent restored replay exited 0 with one agreement and zero errors.
This is the prior TTL0 input under a different fault, not a new unique witness;
the internal action Env observation is separately reconstructed from the test.

Executed both restored and candidate exporters independently. Their action
outputs and both retained captures are identical: 8,803,741 bytes, SHA-256
`1b210355f9f2d66b9b764003166e660e7c02be10dd452250fd7c5dfc19ea109e`.
Both old forwarder outputs remain identical: 6,085 bytes, SHA-256
`c1f7c1c16d10c1c11f536cb0a5ff54a42fd11d6a2c30c8a4ac06633d6adc4669`.

Owner-attributed final gates, corroborated by logs: both Lean packages/default
audits/native tests pass; focused 76 pass; required DRT 917 pass with 1,596
deselected and no skips; complete gate 2,507 pass, five existing strict xfails,
one explicitly unavailable optional local XDP-image skip. The final audit
import is core-only for the commit split, with the reviewed eleven root names
and axiom sets unchanged. Independent fresh audits/native and 76 focused
checks are recorded above; this reviewer did not rerun the whole expensive
suite. No unresolved finding remains within the selected-action boundary.
