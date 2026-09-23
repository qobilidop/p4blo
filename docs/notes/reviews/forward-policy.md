# Independent forwarding-policy review

**Final review: clear; chronological investigation follows below.**

Initial read-only structural review in `p4blo-forward-policy`, based on
`ab9d5d5`: **no theorem/contract blocker found**. Final clearance remains
pending native independent mapping cases, audit registration, deliberate
intent faults and restored gates. No candidate build or binary execution
was performed during this inspection.

The sixteen-field Snapshot covers the entire four-root source store:
Ethernet fields/validity, IPv4 fields/validity, metadata, all read-only route
fields and scratch. `observe` and `restore` use explicit Data/Record
constructors, not the authored Ref/Place accessors. Their two inverse laws
prevent loss of a source field or hidden additional store restriction.
The finite types preserve actual widths while permitting arbitrary
representable values, including invalid-header contents.

The policy is independently expressed as route hit and natural TTL greater
than one, direct named record updates and natural predecessor. It does not
reuse the authored nested equality guards, wrapping-add decrement, paths
or command evaluator. Reject cases change only drop; successful rewrite
changes destination/source MAC, TTL, port and drop. Full record equality
preserves checksum/protocol, both validities, metadata sentinel, route inputs
and scratch. There is intentionally no valid-header precondition absent
from the existing authored body.

`authored_policy` proves the complete observation for arbitrary Snapshot
values. Both inverses then lift that result to exact source-store equality
for every Store, not only the fixed conformance initializer. The final
`execute_policy` uses the existing concrete command correspondence theorem
and fixed root well-formedness proof, retaining actual nominal Index,
declaration/mode agreement, frame-value matching and action-free premises.
Its result includes actual reference execution, complete policy-result
frame values, preserved declarations, all non-variable Run state and every
name outside the possible write roots. No circular whole-command correctness
assumption or callback appears in the public statement.

The increased elaborator recursion bound and transparency option are
proof-construction aids; they do not add logical axioms. Final default
audits should independently pin the five theorem roots and distinguish
the two structural inverse laws from the standard-foundation application
and execution proofs.

Requested native mapping coverage must include an asymmetric manually
constructed source Store and independently written expected Snapshot, not
only an observe/restore roundtrip: paired mapping mistakes can preserve
inverse laws. Expected boundary cases should exercise TTL 0, 1, 2 and 255,
route misses, arbitrary nondefault siblings/route values and invalid-header
states. Planned same-width authored destination-to-source alias and removed
TTL-guard mutations should fail this application-intent proof despite the
generic source-to-IR lowering theorem remaining valid.

This is a local already-parsed, route-selected rewrite policy. Parsing,
route selection, checksum maintenance, architecture forwarding/drop fate
and whole-router validity remain outside its claim.

## Final independent checks and adversarial closure

Final candidate at the updated `5e7fd81` base includes the requested manual
asymmetric constructor anchor. Both kernel examples compare it against an
independently written sixteen-field Snapshot, and a native check repeats the
observation. Seven finite cases check independently expected policy values,
actual authored denotation and actual execution over all roots plus an
unrelated root. Distinct MACs, nondefault checksum/protocol/sentinel/scratch,
maximum route port, invalid Ethernet storage, route misses, initial drop
and TTL 0/1/2/255 are present. The tests are now in the ordinary user driver;
all five theorem roots are default-audited.

Independently executed the compiled user test driver: **exit 0**, including
all seven new policy/source/runtime answers and existing suites. Independently
queried the five compiled roots: both inverse laws use no axioms; authored,
source and execution policy use exactly
`[propext, Classical.choice, Quot.sound]`. No candidate rebuild was performed.

Inspected all three mutation outcomes and final source restoration:

- The same-width destination accessor fault compiles the generic source/
  execution witness but rejects the independent policy on an unrestricted
  false `dst = routeDst` requirement.
- Removing TTL-one rejection also compiles the source witness but rejects
  the policy with `False` in that branch. The separate unused-simp failure
  is not the semantic evidence.
- Coordinated view/restore swaps of both MAC pairs preserve all inverse and
  universal policy audits. The independent manual anchors then reject the
  altered labeling at test-module compilation. This is a genuine survivor
  of the universal proofs caught by independently specified meaning; it is
  not represented as a runtime differential failure.

The final note records exact isolated definition edits and separate command
outcomes, clearly distinguishing proof rejection from native execution.
Restored example and policy files independently compare byte-for-byte with
the candidate; restored audit/user logs pass, with exit 0 reported by root.
There is appropriately no DRT bundle for these proof/test-anchor rejections.
Both package gates are reported green, while merged full/required-DRT gates
remain the integrator's checkpoint. No remaining semantic review finding.
