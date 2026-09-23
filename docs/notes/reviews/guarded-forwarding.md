# Validity-guarded forwarding review

Final review: clear; chronological investigation follows below. Combined
integration gates remain the integrator's responsibility.

2026-09-23. Read-only review of
`/Users/qobilidop/my/work/p4blo-guarded-forwarding`, based on `2713999`.
No reviewer changes or builds in the implementation worktree.

## Contract and independence

This is a separately named guarded command and independent Snapshot policy.
The existing stored-value forwarding body and earlier policy are unchanged.
Actual authored code tests Ethernet then IPv4; the independent policy uses
Boolean conjunction of the two stored validity bits before the previously
verified natural-number hit/TTL policy. The invalid branch changes only drop.

The source theorem quantifies over arbitrary complete Store values through
the existing observation/reconstruction inverse. Invalid states are included,
not eliminated by a precondition. A separate universal source_invalid theorem
pins full-state preservation except drop when either validity bit is false.
The actual execution theorem concretely instantiates the reviewed body law,
retaining real declarations/modes, nominal Index agreement, FrameMatches and
the no-action BlockFrame premise. It proves exact final modeled values and
non-variable Run/outside-target preservation without a whole-command callback.

The nonvacuity witness uses the established agreeing Run for every source
store. It is not an actual caller initialization/call theorem, and the note
says so. Parsing, route lookup, packet fate and checksum correctness are
explicitly outside the claim. Metadata drop is not presented as proved
network dropping behavior.

## Independent answers and observer

The native 64-case profile uses two prior drop values across all validity/hit
combinations and TTL 0/1/2/255. Its asymmetric source values and two-entry
expected forwarding table do not invoke either policy or source denotation.
Every root, stored validity, read-only route and scratch is checked. Closed
kernel anchors pin each single-invalid case and valid TTL-two forwarding.

Python supplies a separate finite answer table and exact 32-case/input
contract. It asserts unique replacement sites for varying initial values,
starts drop false, preserves actual root directions, and observes every field
after the authored body inside the callee. The observer's identity-header mux
distinguishes it from the scoped faulty authored guards without normalizing
production behavior. The permanent actual evaluator fault must produce exact
rewritten fields while both observed stored validity bits remain false;
the saved complete input is replayed live and restored.

## Independently executed stable checks

- New Python suite: 34 passed, exit 0, including real evaluator fault
  retention/live/restored replay regression.
- Compiled userTests: exit 0, including all previous suites and 64 new
  independent policy/source/actual-execution full-state answers.
- Fresh pinned Lean query and GuardedForwardTests.run: exit 0. All four
  advertised policy/source/actual-execution roots report exactly
  `[propext, Classical.choice, Quot.sound]`.
- Independently ran the original fieldCommands exporter and compared its
  17,721 stdout bytes to the pre-increment capture: identical, clean exit and
  stderr, SHA256 `be4beb58c42f1b17e1bcb9e5744ccd3bd5ad945ed64f63a5571574ab0c195280`.
  Original ForwardPolicy and FieldCommandExamples source diffs are empty.

No blocking code finding. Final mutation recipes, restorations and retained
source-edit evidence remain to be checked. Complete candidate/integration
gates are separate from these independent focused checks.

## Final campaign and restoration review

Reviewed the completed five-experiment note and actual failure logs. Missing
and inverted Ethernet guards fail the genuine universal authored-policy
equations. Coordinated omission in both code and independent policy still
fails the retained source_invalid full-state contract. The additional
closed-answer diagnostic temporarily removes that contract only in the
isolated tree; the note explicitly says this lacks the normal contract/audit
and is neither a passing proof mutant nor runtime detection. Its false
single-invalid kernel anchor does fail. No candidate theorem is weakened.

The exporter-only replacement with the old unguarded body genuinely builds
all default proofs/audits, then the selected TTL-two and TTL-255 tests fail
independent expected packets after clean engine agreement. This demonstrates
the distinction between checked application code and selecting the intended
exported body. No differential artifact is claimed for this agreement case.

The actual Python guard-bypass source edit produces one clean live mismatch:
both stored validity bits remain false in the observer, but wrong execution
rewrites the MACs, TTL, port and drop. The recorded restored replay agrees.
The permanent regression's exact independently expected bytes were already
executed successfully during this review.

Independently loaded candidate and isolated retained copies, each 50,175
bytes, SHA256
`3ef594c90fab7df89131d2983c3bab3cfe8004dbc22dfdf0c3017182376d6fe3`.
Both must equal the current exported guard-false-false-true-2 program and
exactly one empty-entry/port-0/deadbeef request, four ports, seed zero. These
source-identity checks pass. Both replay against the restored candidate with
one agreement, no protocol error and no both-error result.

Compared restored policy and exporter source files against the candidate:
both cmp checks pass. Production expr.py has no surviving diff. Independently
ran candidate and restored guardedForward exporters: clean status/stderr and
identical 74,656 output bytes. Whitespace checks pass. Inspected restored
focused log: 34 passed. Complete two-package/default-audit/native restoration
and candidate 597 required DRT are attributed implementer results.

No remaining code or documentation correction. The note preserves exact
fault recipes, a tracked input-reconstruction path, actual mutation versus
proof-rejection distinctions and the no-parser/no-initializer/no-network-drop
boundary. Clear for scoped commits, followed by the parent's combined gates.
