# Independent initial stores reach actual frames

2026-09-23. User-package adapter following the independently reviewed source
zero and actual IR frame theorems. Based on main `db99dc2`; implementation,
proof checks and faults run in isolated `work/initial-source-frames`.

## Scope and choices

`Fields.Layout.initialize` connects independent `Layout.zero` to actual
`P4bloIR.Frame.forBlock` and existing `FrameMatches`. Its premises are actual
scope lookup, `RootDeclares`, nominal `IndexAgrees`, an explicit source-depth
bound within the unchanged production fuel budget, and successful actual
zeroing of **unmodeled** scope entries. Modeled entries' zero equations are
discharged by the source-zero theorem, rather than assumed again. The
conclusion retains the whole looked-up scope, both absent action fields and
the IR theorem's exact lookup description for every string, including extras.
There is no new executable initializer or whole-frame correctness callback.

`Layout.Covers` separately states that every actual declaration belongs to a
modeled root. `Modes.scope_covers` proves this for the existing generated
scope; `Modes.initialize` composes it with checked declaration agreement to
discharge all entries without an extras premise. `Covers.absent` justifies
absence for unmodeled names only under this genuine complete coverage
condition. `RootDeclares` or `Modes.Agrees` alone cannot imply absence of
extras. The generic adapter itself does not require syntactic well-formedness
beyond its explicit semantic premises; the fully modeled Modes corollary uses
the existing `RootWellFormed` premise to obtain declaration agreement.

Confidence: high in this narrow premise-discharge boundary. Retain the
explicit fuel bound and extras obligation until a later application can
prove them; do not silently replace them with global validity. Revisit the
quantified extras API when a concrete call-entry proof needs reusable scope
extension facts. No changes to shared field expression/permission/command
modules were necessary, and no separate source language was introduced.

## Actual Index.build witness

`InitialFrameTests.actualIndex` is computed by **actual** `Index.build` on
the existing `FieldCommandExamples.program`. Its `getD` projection is backed
by `actualIndex_built`, a kernel-checked equation proving the build returned
that exact index successfully. The finite witness uses Lean's proof-producing
`cbv` tactic; it uses neither `native_decide` nor a native result as an axiom.
Straight definitional `rfl` did not reduce the HashMap computations, but `cbv`
with the pinned library's checked evaluation lemmas discharged the successful
build and concrete lookup facts cheaply. No production Index refactor was
needed.

Checked scope lookup, exact mode declarations, nominal map equations and
actual HashMap size facts discharge the remaining initialization premises.
Scope coverage is proved from actual variable lookups. In particular, the
real builder inserts variables in a different order from `Modes.scope`, so
the proof never assumes equality of those maps' representations.

`forward_initialized` proves real `Frame.forBlock` on that built index
produces a block frame matching the independent source zero store.
`forward_expected` then derives exact independently constructed headers,
metadata, route data and scratch values from that correspondence. Both
headers start invalid; all stored siblings are zero, including 48/16/8/9-bit
fields and Booleans. This is the existing forwarding **declaration program**,
not the Python packet/call wrapper and not argument binding or body execution.

The successful-extras fixture explicitly extends that built scope with an
observer `inout bit<65>` parameter and an unrelated Boolean local. Its named
kernel theorem proves matching modeled roots and exact successful extras.
This extension is hand-built and is described as such; the `Index.build`
witness above does not claim to construct it. It is not the wrapper's actual
observer layout. A failing extra references an absent header type. Checked
negative witnesses show the extras premise and full-coverage premise are
false where appropriate. All four parameter directions and a local mode have
a constructive initialized-frame theorem through `Modes.initialize`.

## Trust, independent answers and checks

Default `UserProofAudit` checks the generic adapter, exact scope-coverage
lemma, Modes corollary, concrete actual-build equation, concrete forwarding
initialization/expected-answer theorems and successful-extras theorem. Every
advertised root has exactly `[propext, Classical.choice, Quot.sound]`.
Concrete witnesses are audited even though they live alongside tests; no
test-only native escape is hidden behind the application claim.

Direct expected-value constructors are separate from both zero functions.
Kernel witnesses and native checks observe every modeled root, false stored
header validities, exact extra values, action absence and storage sizes.
Negative checks distinguish missing declarations/nominal agreement, a
source-depth bound of two instead of the required three, absent root
declarations, non-covering extras and an actual failing extra initializer.
The native low-fuel check pins the exact production nesting error.

Baseline fresh two-package gate:

```
nix develop -c /Users/qobilidop/my/work/p4blo-initial-source-frames/scripts/check-lean.sh
```

Exit 0, both packages/default audits/native test drivers, 481 specification
checks and all user checks including the new frame observations. There were
no copied build caches.

## Actual challenges and restoration

This adapter has no new executable runtime path. The following are logical
adapter/fixture faults, distinguished from compiled interpreter mismatches.
Run the commands from the isolated worktree's absolute `lean/` directory.

1. Misidentify the block selected by the generic adapter. In
   `P4blo/InitialFrames.lean`, change only the generic conclusion:

   ```diff
   -    ∃ frame, P4bloIR.Frame.forBlock index block = .ok frame ∧ frame.scope = scope ∧
   +    ∃ frame, P4bloIR.Frame.forBlock index scope.block = .ok frame ∧ frame.scope = scope ∧
   ```

   `nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.InitialFrames`
   exits 1: the proven actual result for `block` cannot establish that result
   for `scope.block`. The Modes corollary independently exposes the same
   unjustified substitution. The exact requested-name scope premise matters;
   this is a rejected false adapter claim, not a production execution fault.

2. After restoring the adapter, change the actual extra declaration in
   `P4blo/InitialFrameTests.lean` from `bit<65>` to `bit<64>`:

   ```diff
   -    vars := (actualScope.vars.insert "observer" (.param ⟨"observer", .bits 65, .inout⟩)).insert
   +    vars := (actualScope.vars.insert "observer" (.param ⟨"observer", .bits 64, .inout⟩)).insert
   ```

   Building `P4blo.InitialFrames` exits 0: the generic correspondence still
   holds, and every modeled forwarding root is unaffected by this extra.
   Building `P4blo.InitialFrameTests` exits 1 specifically at the independent
   `extras_initialized` expected-value equation: actual zero has width 64,
   while the required observer has width 65. This is an independent kernel
   answer rejection. No runtime mismatch or replay bundle is claimed.

Both files were restored and their SHA256 hashes match the pre-fault values:

```
a15946e7afac1f5c29186ed38021b1f3919a1e1a1be866451066f3077e351017  lean/P4blo/InitialFrames.lean
bc43cd5e798da0df8d89c1885517978ea622b7e512b409b5d6bf0344d48df38e  lean/P4blo/InitialFrameTests.lean
```

Supplementary local logs are `/tmp/p4blo-initial-frame-adapter-fault.log`,
`/tmp/p4blo-initial-frame-extra-generic.log` and
`/tmp/p4blo-initial-frame-extra-answer.log`. The tracked patches and audited
proofs/independent answers above are the durable reproduction evidence.

Restored `scripts/check-lean.sh` passes again, exit 0: both packages, all
default audits, 481 specification checks and all user tests including the
new low-fuel/initial-frame checks. The focused new kernel/native suite is
part of these default gates. Required real-Lean conformance also passes:

```
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees
```

538 passed, 1423 deselected, no skips, 61.34 seconds, exit 0. No binary was
rebuilt during this run. `git diff --check` passes. Python/schema, external
P4-oracle and XDP gates were not rerun in this isolated proof/test increment;
the integrator owns combined full gates. No Docker build or external system
change was performed.

Independent review is clear: `notes/reviews/initial-source-frames.md`. The
reviewer rebuilt generic/concrete targets and the default audit, ran the
user-package and focused native checks, queried all seven advertised axiom
sets afresh, and inspected the exact fault diagnostics and restored hashes.

This does not establish global `Index.build` validity, general nominal fuel
adequacy, action-overlay compatibility, parameter copy-in, block dispatch,
packet state, call/body-prefix execution, copyback or parser unwinding. The
next bounded obligation remains actual sub-control entry and a body prefix,
with the real wrapper's declarations and extras discharged separately.
