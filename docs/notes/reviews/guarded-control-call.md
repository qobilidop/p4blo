# Observer-free whole-control-call review

Final review: clear; chronological investigation follows below.

2026-09-23. Read-only structural review of
`/Users/qobilidop/my/work/p4blo-guarded-control-call` at `b115c32`, limited to
the new GuardedControlCall module and the committed guarded-call plan.
Unfinished consumers were not inspected or executed and no candidate source
edits/builds were performed.

## Core theorem and composition

The selected body is exactly the two local assignments plus guarded command
lowering, with no observer statements. Its program/index use the actual
body-bearing declaration family, and successful Index.build/block lookup are
derived from that family rather than assumed. body_prefix connects it to
GuardedCallPrefix.body []; it is not an empty-body index substitution.

resultStore uses the independent Snapshot observation/policy/restoration and
literal top-level Record slots for hdr/meta. It does not reuse authored field
accessors, command denotation or interpreter output as a policy oracle.
The fourth observer argument remains arbitrary operational Value and passes
through unchanged; observer-free does not mean the parameter was removed.

source_steps first applies the committed actual guarded prefix with empty
suffix. It then takes the required real administrative step that pops
statements [], and composes the reviewed normal return. FrameMatches yields
the actual callee hdr/meta reads; the separate prefix preservation equation
supplies observer. Return writes use the original caller's three existence
witnesses and BlockFrame, not a later callee frame. Definitional record
reduction identifies the exact final Run with the independent result.

The theorem retains arbitrary caller Run/source data/K with actual index and
four caller lookup premises. K stays pending, and both endpoints have no
fault. call_correct specializes K=[] and uses actual Steps.finishes,
Finishes.done and soundness to obtain semantic callBlock completion. There
is no assumed whole-call correctness callback or second executor.

The result preserves all original non-frame state and original caller scope /
action metadata. Therefore ChangesOnlyVars relative to the original caller
Run is now appropriate, unlike the earlier callee-entry prefix. Explicit
lookup/preservation laws retain source_route, caller scratch/unrelated and
all other outside names, including absence. Callee scratch19/unrelated165 do
not escape. Caller hdr receives the unchanged observer value; its redundant
same-value insert need not be simplified into internal HashMap equality.

The result-only preservation lemmas do not themselves assert execution
without premises; execution comes from source_steps/call_correct. No global
validity, caller construction, parser/route/checksum/packet fate, observer
encoding, arbitrary call/action/lvalue or fault-unwind guarantee is implied.

No blocking structural finding. This is not final checkpoint clearance:
actual-built nonvacuity, independent complete-return observations, literal
step boundaries, copy-isolation/order controls and final mutation/restoration
evidence still require review when the owner freezes them.

## Completed fixture and execution review

The owner subsequently froze candidate sources/binaries while running only
read-only required comparisons; mutations run in a separate worktree. This
reviewer inspected the complete native module, exporter, Python test and
registrations, without rebuilding the candidate.

The Python fixture independently constructs the exact two literal assignments
(scratch19, unrelated165) and one already-reviewed guarded conditional. It
compares the complete selected block, declarations and arguments, rather than
slicing the candidate's body. The guard syntax comes from its separate
exporter; the independently specified policy/source outcomes remain separate
anchors for intended behavior. There are exactly three selected statements
and no observer suffix.

All 64 exported profiles are checked once against independent detached whole
Run/callee JSON, with strict scalar types, exact case coverage and no duplicate
case keys. This includes index maps, both caller and installed-entry indexes,
scope maps, old caller locals, retained callee locals, nonempty installed
entries/default, register cells, packet data/cursor, emitter and visits.
Native checks reuse the reviewed order-independent full-map/shared-state
comparators and their corruption controls. They check 192 combinations of
profile and continuation, including actual semantic callBlock completion.

Literal total counts 13/16/19/22/25/33 add the real empty-statements pop and
normal-return transitions. One step short still has the original caller's
blockReturn pending; the completed trace leaves arbitrary representative K
untouched. Running the retained block continuation fails with its independent
unknown-block error. Running the retained statement continuation first writes
the restored caller's scratch200, then produces the named parser fault.
Neither behavior is silently consumed by the claimed call prefix.

The Python path invokes real call_block to normal completion. Its delegating
run_block hook checks incoming mutable aggregate isolation before executing
the real body, then captures a detached full callee state. There is no early
exception or substituted copyback. A delegating write spy checks all three
ordered copyback destinations, since final values alone would not distinguish
commuting writes. Both caller and retained callee are compared afterward.

All four incoming roots (including readonly route) must be disjoint from
original mutable objects/field lists. After return, all copied-out roots and
the original caller route are disjoint from the retained callee's aggregates.
Real member writes separately exercise Ethernet, IPv4, Metadata, Result and
Route; each checks the complete updated caller and unchanged callee. Original
input trees also remain unchanged. As before, this covers this finite
Struct/Header tree profile, not arbitrary cyclic/Stack/extern object graphs.

Permanent negative controls exercise selective output aliases and shared
field lists, reversed/skipped copyback, copying an input parameter, leaked
locals, cursor int-to-float and visit int-to-Bool changes, cleared entries,
callee-local corruption, all four incoming aliases, malformed strict snapshots
and paired wrong initializer/source expectations. A subsequent tests-only
strengthening explicitly disables only the order assertion for reversed and
skipped observer copyback: the complete value/isolation checks survive both
faults, and restoring the order assertion rejects each with exactly one hook
hit. This demonstrates why the ordered trace observation is necessary when
distinct writes commute or the copied-back value is unchanged.

Independently executed against the stable candidate:

- Focused Python suite: **91 passed**, exit 0, 3.74 seconds.
- Compiled userTests: exit 0, including **192** new whole-call profiles and all
  existing user checks.
- Fresh pinned-Lean axiom queries for all nine new roots: body_prefix uses
  `[propext]`; the other eight use exactly
  `[propext, Classical.choice, Quot.sound]`.

The permanent actual-Python skipped-observer regression also passed: it
separately observes copyback order at the observer-free call boundary and a
saved/replayed packet mismatch in the existing observer-bearing packet
wrapper. That is a different wrapper, not packet encoding proved by this
whole-control theorem. Its expected faulty packet was corrected during fixture
development to 42 zero Result-header bytes plus payload because that wrapper's
initial Result is valid. This calibration is not a production fix or an
independent successful mutation experiment by itself.

No current blocking finding. Final clearance still requires the owner's
isolated compiled proof/runtime fault logs, exact saved input/source identity,
and restoration evidence; those are not yet claimed here.

## Final campaign and restoration closure

The final note and actual retained logs were independently inspected. The
three experiments have accurately distinct outcomes:

1. Omitting `pop` in the actual proof fails on the real queue mismatch between
   statements[] followed by return and return alone. This is genuine theorem
   rejection, not a runtime semantic kill or a syntax/unused-variable failure.
2. Changing the invalid-Ethernet literal observation count13 to12 compiles the
   default package/audits and rebuilt native executable. Native checks then
   reject the missing two-transition boundary; the Python full snapshot
   fixture rejects the incomplete result/count/queue. The actual call theorem
   remains unchanged: this is an observation-fixture fault, not an interpreter
   mutation or a weakened proof.
3. An actual production `copy_back` observer-skip edit fails the normal-call
   order check, and independently produces the recorded clean packet mismatch
   in the existing observer-bearing wrapper. The live complete-input replay
   reports one divergence; restored replay reports one agreement. The log
   shows Python's 42 zero bytes plus payload versus Lean's independently
   expected observed bytes plus payload, with no error/diagnostic/state fault.

The selected fault logs show87 deselections and stop at their first failure;
this does not imply88 total tests. The recorded substring selector also
matches TTL255 and both prior-drop values, selecting four of91 tests; `-x`
leaves three selected cases unrun. The owner checked collection explicitly
and is tightening durable commands to exact node IDs. The subsequent
tests-only weak-order controls did not add cases; they were inspected and
executed: **12 passed**, 79 deselected, exit 0. The complete value/isolation
observer survives the reversed/skipped write faults when only its order check
is disabled, and the strong ordered observer rejects them. An unchanged
observer value alone cannot expose skipped same-value copyback.

Independent final source/artifact checks completed successfully:

- Candidate and restored isolated core, native test, Python test and unchanged
  production stmt.py are byte-identical; all four SHA-256 values equal those
  in the note. The isolated production stmt.py and Exec.lean diffs are empty.
- Both candidate and restored exporters were freshly executed with successful
  exits and empty stderr. The whole-call output is byte-identical:
  **1,964,786 bytes**, SHA-256
  `4f599e9bdddff4af05ec6f9fba75f522c1c46c161fc1015b308627b126b2137d`.
- Old prefix and return exporters also match across both trees and their
  recorded baseline hashes: prefix866173 bytes, SHA `eb3f2ef539102c316ec8b3c63903d998d06c0fb7e26c45bff008b81140229327`;
  return56754 bytes, SHA `425a401a96e4323a03f4299bdc8ba2a6a420df71af23e9c20e0af5cf0d080fc7`.
- Both retained replay bundles are byte-identical: **50175 bytes**, SHA-256
  `3ef594c90fab7df89131d2983c3bab3cfe8004dbc22dfdf0c3017182376d6fe3`.
  The entire program matches the current tracked guarded exporter/wrapper,
  and the request is exactly empty entries, ingress0, `deadbeef`, ports4,
  seed0. Independently replaying the restored candidate gives **one agreement,
  zero divergences, zero both-errors, no protocol error**, exit 0.

This is the same input previously retained for guard/local-write faults, now
challenged by a distinct return fault; it is not counted as a new unique
witness. Direct call-state observation is not described as packet DRT.

The final focused suite was independently rerun after the weak-order additions
and restoration checks: **91 passed**, exit 0, 3.44 seconds. Owner logs
additionally show restored default build,
native suite and91 focused tests succeeding; the final required suite reports
**743 passed, 1537 deselected**, with scoped formatting/lint/types clean.
Those broad required/static gates are owner-attributed. Full merged
Python/schema/oracle gates remain the integrator's responsibility. No remaining
blocking finding, and no extension of the exact bounded theorem claim.
