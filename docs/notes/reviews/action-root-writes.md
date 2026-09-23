# Independent review: action-aware root writes

2026-09-23. Review worktree `work/action-root-review`, based on committed
`4328f8b`; read-only candidate sources in the integrator's worktree. Scope:
`ir/P4bloIR/ScalarStatements.lean`, `ir/Tests/ScalarStatements.lean`, and
`ir/ProofAudit.lean`. Read the committed `forwarder-action-next.md` plan and
actual `Env.lean` operations. No candidate files or binaries were edited or
rebuilt by the reviewer.

Status: **CLEAR** for this scoped prerequisite. No confirmed defect or
required code change. The integrator's ordinary full gate is a separate
checkpoint gate and was still running at review closure.

## Contract review

`writeVar_block_unshadowed` uses the actual action-map lookup bound to none
and an actual block-map successful lookup. It does not replace those premises
with action-name absence, declared permission, source mode agreement or a
callback asserting correctness. Its none/some action-map cases follow actual
Frame.write? contains branches, using the library lookup/contains relation.
An existing empty action map is allowed, and every other action entry remains
present. The conclusion is equality of the complete successful result and
the whole Run with precisely the block value map updated.

`readVar_action` follows real action-first Frame.read? even with a block decoy.
`writeVar_action` follows the action-hit branch; its lookup premise requires
no block binding. Its exact result preserves the complete block map, scope,
action identity and all non-frame Run fields. Neither law requires runtime
types or semantically valid action declarations. Inconsistent action-name/
action-map metadata is not silently excluded: the operational code actually
uses the map, and the statements correctly retain that behavior.

The old `writeVar_block` statement is unchanged and is derived from the new
law using the existing BlockFrame premise. Existing field/command/action
typing is not broadened. No action body, table selection, call binding,
action return, parser, permission, fault-state preservation or complete
forwarder result follows from this prerequisite alone.

## Nonvacuity and observers

The named constructive witness has a genuinely installed action name and
nonempty action map, with a separate kernel proof that it is not BlockFrame.
It discharges both actual lookups by kernel reduction while quantifying over
every surrounding Run component. The collision root has different block
and action Value constructors (bits17 versus Boolean false), so action-first
lookup cannot accidentally pass using the block decoy or Boolean truthiness.

The additional kernel examples instantiate action reads and writes. The eight
new native controls cover false-valued shadowing, successful unshadowed writes,
complete finite action bindings, block decoy/unrelated roots, action-hit
updates, original store sizes/action identity, missing-root rejection and an
installed empty action map. Exact full-Run preservation on success is supplied
by the universally quantified theorem, not inferred from a partial native
snapshot. The missing-root check asserts its exact failure diagnostic, not a
general theorem of fault-state preservation. No stronger runtime observer is
needed for the scoped advertised success laws.

## Independent checks executed

After the implementer released the stable binary window, ran pinned Lean
`lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true --stdin` in
main's IR package, importing actual compiled ScalarStatements and its tests.
No rebuild was performed. Fresh axiom queries for the three new operational
laws, the constructive witness, and the preserved old API each report exactly
`[propext, Classical.choice, Quot.sound]`. The same query executes the focused
scalar test list: 20 checks, all passing, exit 0.
Log: `/tmp/p4blo-action-root-independent-query.log`.

Executed the existing native `ir/.lake/build/bin/tests` directly, with the IR
package as working directory: 506 checks passed, exit 0.
Log: `/tmp/p4blo-action-root-independent-native.log`.
The implementer reports both-package/default/native gate exit 0 in
`/tmp/p4blo-action-root-lean.log`; the reviewer did not rerun that rebuilding
gate while the integrated full/required suites consumed binaries.

Reviewed candidate SHA-256 values:

- ScalarStatements proof module:
  `a3dce2c637661b782e8f28b83daa39621c42730f1e5254b58bd9457eeca2e7be`.
- ScalarStatements test module:
  `1b6c6e1f2db9616d0200199d843cb00449039c281011c760c2cfdd8ed0a964f2`.
- ProofAudit:
  `e33243fb0a58306e014e0e3c2150c3af67b59a8ae8aaace316bd64a3a57bed87`.

Main Env.lean is unchanged from the review base, verified by matching SHA-256
`69b4484e9e669bb0fa37d436d965d4a9e6462fd6fe96083e310c0001168b0624`.
Diff whitespace check passes. The reviewer has no active binary consumers.

## Adversarial evidence inspected

Read the complete tracked implementation note
`docs/notes/action-root-writes.md` and all eight logs
`/tmp/p4blo-action-root-fault-{miss,precedence,hit,layer}-{env,proof}.log`.
The exact isolated source deltas and reproduction commands in the note
correspond to the failing goals:

| Actual isolated Env fault | Unchanged proof rejection |
|---|---|
| Active miss inserts into action storage | unshadowed law exposes both wrong maps |
| Frame.read? tries block first | action-read law would require arbitrary block decoy to equal action value |
| Active hit inserts into block storage | action-write law exposes opposite-map update |
| Correct fallback block insert clears action name | unshadowed law exposes lost metadata despite correct values |

Every actual Env build succeeds; each subsequent proof build fails at a
genuine semantic equality goal, not a type/termination/lint failure. These
are proof-killed operational mutants. There was no runtime mismatch campaign
for this increment, no new packet input and no claim of runtime replay.

The reviewer inspected the restored build log
`/tmp/p4blo-action-root-fault-restored.log`; the implementer independently
reported its actual exit 0. Separate reviewer `cmp` invocations confirmed
both Env.lean and ScalarStatements.lean in the fault worktree byte-match
the clean candidate, each exit 0. Rechecked all three candidate file hashes
after mutation closure; they match the reviewed hashes above. Main runtime
remained untouched. The additional required/replay gate results in the note
are attributed to the integrator rather than claimed as reviewer executions.
