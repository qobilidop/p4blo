# Independent source-zero correspondence

2026-09-23. First bounded step of `initialization-bridge-plan.md`, based on
committed main `6ff0449`. No production IR initializer or runtime semantics
changes survive this increment.

## Contract and limits

`Fields.Shape.zero` and `Layout.zero` construct independent source values:
zero Fin scalars, false Bool leaves, invalid headers with recursively zero
stored fields, and Unit-validity structs. They do not invoke IR conversion,
the reference initializer or the evaluator. `zeroFuel` measures the maximum
aggregate nesting plus one unit for each leaf; an empty aggregate still
consumes one unit. Siblings share fuel, so the layout measure uses maximum,
not sum.

Mutually checked Shape/Layout theorems connect these values to the **actual**
`Value.zeroWith`, assuming exact existing nominal `IndexAgrees` and a
sufficient explicit fuel bound. The production `Value.zero` corollary uses
its unchanged `headerTypes.size + structTypes.size + 2` budget. All three
roots are default-audited with exactly
`[propext, Classical.choice, Quot.sound]`.

This does not prove a global nominal-depth bound, declaration validation,
frame construction, parameter binding or copyback. A concrete mixed fixture
and the existing forwarding roots discharge the real runtime-budget premise
using checked HashMap size lemmas. Native computation is not used as a
logical witness. Width zero remains representable here; positive-width
authoring validity is separate. There is no competing runtime initializer.

## Independent acceptance

`SourceZeroTests` constructs expected IR values directly, without either
zero implementation. It covers mixed 8/65-bit and Boolean header fields,
a nested struct with a 9-bit sibling, an empty header, all stored validity
bits, and independent scalar widths 0/1/8/9/65. Kernel answers pin exact
source conversion, depth, validity and actual production zero. The forwarding
root theorem establishes a nonvacuous existing-application instantiation.

Native checks include sufficient fuel 3/4/9, insufficient fuel 0/1/2,
the actual production budget, unknown declarations and an inconsistent
stored nominal name. The latter deliberately preserves actual behavior:
runtime zero uses the stored declaration name, while `IndexAgrees` would
reject that malformed declaration. It must not be silently normalized away.

Both package/default-audit/test gates pass before and after the campaign:
451 specification checks plus all user checks, exit 0. Required real-Lean
DRT passes 469 tests with no skips (59.64 seconds). The complete Python/schema
gate passes 1847 tests, with five documented strict oracle discrepancies and
one explicit unavailable-local-XDP-image skip (349.43 seconds), exit 0;
formatting, lint, types, schema generation/no drift and workflow checks pass.
Independent review is clear: `notes/reviews/source-zero.md`.

The reviewer noticed stale pre-rename `P4blo/` artifacts in the copied IR
build cache when making a standalone import query. After every running test
finished, both worktree build directories were moved out to a recoverable
temporary directory and their absence checked. A fresh two-package build,
both default audits and all native tests pass, exit 0; the rebuilt IR cache
contains `P4bloIR/` and no stale `P4blo/` directory. A second required DRT run
against these freshly built binaries passes all 469 checks with no skips
(53.58 seconds), exit 0.

## Actual adversarial campaign

Run the following only in an isolated worktree, with the normal packages
built first. Each replacement targets the unique exact line shown. Commands
below use the pinned environment from the worktree's `lean/` directory.

1. Change only `Shape.zero`'s header case in `P4blo/SourceZero.lean`:

   ```diff
   -  | .aggregate .header _ fields => .aggregate false fields.zero
   +  | .aggregate .header _ fields => .aggregate true fields.zero
   ```

   `nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.SourceZero`
   exits **1**. The actual correspondence equation requires false to equal
   true. The accompanying termination warning is not counted as the kill.

2. Keep that source fault and also change the production header initializer
   in `ir/P4bloIR/Value.lean`:

   ```diff
   -      pure (.header decl.name false fields)
   +      pure (.header decl.name true fields)
   ```

   `nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.SourceZero UserProofAudit`
   exits **0**, including the universal correspondence and every default
   user audit. The source and reference now agree on the same wrong meaning.
   `nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.SourceZeroTests`
   exits **1**: the independently constructed expected value, false validity
   list and actual-zero expected-value theorem all reject it. These are
   independent kernel-answer kills, not a Python/Lean runtime mismatch.

3. Restore the source line, leaving only the actual initializer fault.
   Building `P4blo.SourceZero` again exits **1** at true versus false in the
   actual correspondence equation. Restore the initializer exactly.

Both files' SHA256 hashes match the pre-campaign originals after restoration:

```text
68d0223fb41a0f2e2f4d108dc4382305d7deececefb9410c89677c0f01972835  lean/P4blo/SourceZero.lean
d1debfa211cca72554d3a873389cfe203e2e1d98a29f7baa12e0c38bb5d0999f  ir/P4bloIR/Value.lean
```

`git diff --exit-code -- ir/P4bloIR/Value.lean` exits 0. Supplementary local
logs are `/tmp/p4blo-source-zero-mutant-{source,paired-build,paired-kill,runtime}.log`.
The exact source recipes and tracked expected answers are the durable
evidence; no execution replay bundle is invented for a failed proof build.

Confidence is high in the scoped correspondence, medium in the next generic
frame-fold proof cost. The next increment must account for every actual scope
variable, including observer extras, and prove exact lookups/no action layer.
This source-zero result alone does not discharge those body-theorem premises.
