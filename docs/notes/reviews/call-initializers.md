# Actual local-initializer prefix review

Final review: clear; chronological investigation follows below.

2026-09-23. Read-only review of root-owned
`/Users/qobilidop/my/work/p4blo-call-initializers` against `ac69759`.

The proof executes the actual statement dispatcher, literal evaluator and
writeVar_block lemma. It composes four real machine transitions: unpack and
execute each assignment. The endpoint retains exactly statements suffix and
the entire arbitrary continuation, without an extra administrative pop or
assumed successful suffix. Machine fault is absent at the stated endpoints;
this is not a theorem about entering an already-faulted machine.

The result is an exact Run/frame map replacement with scratch19 then
unrelated165. ChangesOnlyVars preserves every other Run and frame component;
the outside theorem quantifies all other map names, including absent names.
Independent constructor-based bodyStore retains arbitrary aggregate source
data/validities and changes only the modeled scratch leaf. Operational
existence of both bindings and absent action layers are explicit. Actual
declaration/type/permission requirements are supplied separately by
body_typed, not incorrectly inferred from map membership.

The concrete source witness derives its preconditions from actual empty-body
call entry, then starts at a statement-list boundary. It does not silently
claim body-bearing lookup, runBlock expansion or whole-call composition.
When integrating with the independently reviewed body family, establish the
definitional equality of CallBodyEntry.initializers and CallInitializers.body;
the two modules currently record the same syntax in separate worktrees.

Native expectations use literal four-step counts and 19/165 values, not
finalRun/bodyStore as their answer oracle. Sixteen cases cross both validity
bits, zero/nonzero prior unrelated and empty/nonempty suffix. Pending work
has an observable write and a real fault; separately executing it shows the
boundary was meaningful. Four missing-unrelated controls exercise the actual
error including block name and retained first write, without claiming atomic
rollback. Non-frame native sentinels and caller metadata are selected checks,
not full native equality of every index/scope map; the note correctly reserves
that stronger preservation for the exact universal theorem.

Public export, ordinary test-driver and five default audit registrations
are present. No runtime, AST or lowering changes. No structural blocking
finding at this stage; final independent runs and evidence follow below.

## Independent stable-binary checks

With the owner's explicit exclusive-execution window, ran fresh pinned Lean
queries against the candidate: all five advertised audit roots use exactly
`[propext, Classical.choice, Quot.sound]`. Fresh native evaluation passes all
sixteen prefix boundaries and four missing-extra controls. Full compiled
userTests also exits 0, including earlier suites. Existing field-command and
call-entry Python tests pass **36 cases**, exit 0 (5.59 s). No candidate
rebuild/source modification was performed; execution access was released
before the owner started the required differential suite.

## Final campaign and retained replay

Inspected the final evidence note and actual isolated logs. A one-sided
scratch19-to-20 body change leaves a genuine false machine-transition goal
as well as an incompatible typing witness; unused-simp diagnostics do not
constitute the sole failure. The paired seven-token update changes source,
body and operational answers consistently: its default build and all audits
pass, but the unchanged native literal-19 anchor fails at execution. This
correctly separates proof preservation from intended policy/constant choice.

The actual Python assignment-source fault evaluates normally and changes only
the RewriteBody scratch8/19 value to 20. The existing full authored-program
gate saves a clean single-output mismatch before failing, live CLI replay
diverges, and restored replay plus the original test pass. The new permanent
test applies the same value fault through the real assignment write hook,
counts exactly one initial and one replay invocation, checks the full saved
program/request/ports/seed and compares the exact independent one-byte
output difference. It restores the hook and requires agreement on the same
bundle. It is discovered by the required real-Lean selector.

Requested one final assertion hardening: protocol_error=None and
both_errored=0 alone do not exclude one-sided faults or parser diagnostics
alongside outputs. The implementer added both outcomes' error=None,
diagnostic=None and exact empty state assertions. Independently reran the
final retained regression after this addition: **1 passed**, exit 0. No
production-source or Lean change was necessary.

Independently loaded the retained actual-source-fault bundle, verified its
43963 bytes and SHA256
`af03fad4149a65fddbe3345cb546e08e1e9d6820b34a82ac47a9a514abfeb79b`,
and checked exact equality with the current fieldCommands fixture for
forward-hit, the one empty-entry ingress-0 deadbeef request, four ports and
seed zero. Restored replay gives one agreement, no divergence/errors and
exit success. Candidate and actual mutant-worktree bundle bytes are equal.
The restored CallInitializers.lean and stmt.py each match the candidate and
the recorded SHA256; actual production runtime changes do not remain.

The owner reports both Lean/default/native gates and 603 required cases
passing before the final three assertion-only additions; its rerun after
those assertions and the combined integration gate remain attributed owner
checks. No blocking finding. Clear for this exact local-prefix checkpoint;
body-bearing call/initializers syntax equality and actual runBlock-to-prefix
composition are still the next explicit obligations, not implied here.
