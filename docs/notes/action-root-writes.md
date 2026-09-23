# Variable writes with active action storage

2026-09-23. Small prerequisite from `forwarder-action-next.md`, developed
against `4328f8b`. No runtime, schema, source typing, Fields or Cmd changes.

## Exact laws

`ScalarStatements.writeVar_block_unshadowed` proves actual `writeVar`
updates precisely the block map entry when that entry exists and the actual
action-map lookup is absent. An action map may remain installed. The result
is the complete original Run with only that block entry inserted: action
name, action map, scope, all other block entries and shared Run fields remain
unchanged. The premise is about storage lookup, not an action name or a
declaration permission. Inconsistent-but-operational frames are not excluded.

`readVar_action` and `writeVar_action` prove action-first lookup and exact
action-map-only updates on a genuine hit, regardless of a block decoy or
block absence. The former `writeVar_block` signature is unchanged and now
follows as a corollary. These are operational laws, not a claim that an action
parameter is source-writable or an arbitrary frame is validator-accepted.

The constructive witness uses a genuine active map, a block-only false
value and a shadowed name whose action and block values even have different
types. It discharges the hypotheses by kernel reduction for an arbitrary
surrounding Run; a separate theorem rules out BlockFrame. Four new default
audit roots have exactly `[propext, Classical.choice, Quot.sound]`.

Eight native checks exercise false-value precedence, unshadowed writes,
preserved action bindings/block decoys/scope, action-hit writes, missing-root
failure and an empty installed action map. These are independent selected
storage/error observations, not a complete native Run comparator. Universal
whole-Run success preservation is the exact theorem's conclusion.

Confidence: high for this storage boundary; it does not yet lift field
updates, prove an action body, restore an action on return or establish
Python equivalence. The actual forwarder still needs the selected-action
trace and independent policy theorem described by the accepted plan.

## Compiling model faults

All deliberate edits occurred only in the separate root-owned worktree
`/Users/qobilidop/my/work/p4blo-action-root-faults`, based on `4328f8b` with
the new ScalarStatements source applied. No native consumers ran in that
tree. The main runtime was never edited. Clean SHA-256:

- `ir/P4bloIR/Env.lean`:
  `69b4484e9e669bb0fa37d436d965d4a9e6462fd6fe96083e310c0001168b0624`.
- `ir/P4bloIR/ScalarStatements.lean`:
  `a3dce2c637661b782e8f28b83daa39621c42730f1e5254b58bd9457eeca2e7be`.

For each delta below, start with these clean files, change only Env.lean,
and run the two commands separately with the isolated `ir/` as the scoped
working directory. Replace the absolute root for a fresh reproduction.

```text
nix develop /Users/qobilidop/my/work/p4blo-action-root-faults -c lake build P4bloIR.Env
nix develop /Users/qobilidop/my/work/p4blo-action-root-faults -c lake build P4bloIR.ScalarStatements
```

1. **miss:** In Frame.write?'s `some avs` branch, replace only its fallback
   `some { f with vars := f.vars.insert name value }` with
   `some { f with actionVars := some (avs.insert name value) }`. Actual Env
   compiles, but the unshadowed law fails: wrong block and action maps.
2. **precedence:** Replace Frame.read?'s expression with
   `f.vars[name]? <|> (f.actionVars.bind (·[name]?))`. Actual Env compiles,
   but the action-read law fails with the unjustified goal
   `run.frame.vars[name]?.getD value = value`.
3. **hit:** In Frame.write?'s active-hit branch, replace only
   `some { f with actionVars := some (avs.insert name value) }` with
   `some { f with vars := f.vars.insert name value }`. Actual Env compiles,
   but the action-write law fails at the exact opposite-map update.
4. **layer:** In the original active-miss fallback, retain the block insert
   but add `action := none` to that record update. Actual Env compiles, but
   the unshadowed law rejects the lost action name despite correct values.

Every actual Env build exits 0; every subsequent unchanged proof build exits
1 with the stated semantic equality goal. These are four proof rejections
of compiling model changes, not runtime mismatches, source-intent tests or
new packet artifacts. Logs:
`/tmp/p4blo-action-root-fault-{miss,precedence,hit,layer}-{env,proof}.log`.
Each delta is reversed before applying another. Final Env and proof source
byte-match the clean main sources; restored proof build exits 0 in
`/tmp/p4blo-action-root-fault-restored.log`.

## Checks

Both Lean packages/default audits/native suites pass, including 506 spec
checks. Required real-Lean discovery passes 822 with no skips. All retained
17 execution bundles (24 requests), 24 old codec observations, 25 statement
fault observations (20 distinct inputs) and 59+69+79 old exact codec
transcripts pass. Logs: `/tmp/p4blo-action-root-{lean,drt}.log`.
The ordinary full gate passes **2381 / 5 strict expected discrepancies /
1 explicit unavailable-local-XDP skip**, including formatting, lint, types,
schema/no-drift and workflow checks; exit 0, 377.69 seconds in
`/tmp/p4blo-action-root-check.log`. The required gate is 822 passed /
1565 deselected, exit 0, 83.45 seconds. The proof is committed at `01d8b09`.

Independent [review](reviews/action-root-writes.md) is clear. It freshly
queried the four new roots and old API, executed all 20 focused native checks
and 506 full spec checks, inspected every compiling fault/proof log, and
verified clean source restoration. The reviewer did not rebuild binaries
while the integration gates consumed them.
