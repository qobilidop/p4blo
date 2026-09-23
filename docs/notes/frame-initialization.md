# Actual block frame initialization

2026-09-23. Bounded IR checkpoint following `initialization-bridge-plan.md`
and the separately proved source-zero correspondence. Based on committed
main `c2bb0c8`; implementation and fault experiments use isolated worktree
`work/frame-initialization`.

## Contract

`P4bloIR.Frame.forBlock_initialized` proves that the **existing production**
`Frame.forBlock` succeeds when the requested name resolves to a scope and
actual `Value.zero` succeeds for every declaration in that scope's variable
map. It returns exactly that scope, with `action = none` and
`actionVars = none`. For every string key, its storage lookup is exactly the
scope lookup followed by the successful actual zero result. Consequently,
declared names contain their exact zero values and undeclared names are
absent. The theorem quantifies all actual declarations, including variables
outside a user model. Its premise is per-declaration zero success, never a
whole-frame correctness callback.

`forBlock_correct` exposes the same result for a supplied family of values
with proven actual-zero equations, suitable for later source-zero adapters.
`forBlock_missing` pins the existing unknown-block error. A private induction
over the actual `forIn` operation proves the loop's exact lookup behavior.
It does not define another initializer. HashMap `toList` membership/lookup
facts connect the real scope map to the real loop; map insertion order and
representation equality are not assumed. Repeated keys in the supporting
list lemma are harmless because they are assigned the same proven value.

The scope's stored block need not equal the requested block, and a stored
variable declaration's own name need not equal its map key. Both actual
behaviors remain in the theorem. This is initialization before argument
binding: every direction, including input and directionless parameters,
starts zero here. It proves no global validation, automatic zero-fuel bound,
user `FrameMatches` adapter, call entry, action execution, copyback or parser
unwinding. Those remain separate obligations.

The three public theorems are registered in the default IR audit with exactly
`[propext, Classical.choice, Quot.sound]`. Production initializer source is
unchanged after restoration.

## Constructive and independent acceptance

`Tests/FrameInitialization.lean` supplies an actual six-entry scope with
all four parameter directions, an observer and an unrelated local. It has
8/9/65-bit scalars, Boolean leaves, a nested struct, mixed-width header and
empty header. Expected values are direct constructors with zero scalars and
false header validity, independent of either source or runtime zeroing.

Kernel witnesses discharge **all** actual declaration-zero premises and
instantiate the generic theorem. Another checked witness derives actual
frame reads for the independently expected nested value and the unrelated
Boolean, plus absence under its differing stored declaration name. The
scope intentionally stores a parser block named `stored`, although the
requested block is a control named `requested`: exact scope preservation
does not quietly assume an index validator. A failing extra header
declaration has a kernel proof that the all-declarations premise is false.

Twenty-one compiled native checks observe every expected binding through
both raw storage and action-first `read?`, exact storage size, absent names,
both absent action layers, retained scope block/declarations, the exact
extra-declaration failure, the exact missing-scope error and empty scope.
The same independent values are also checked after actual `Index.build`.
That final built-index check is runtime evidence; it is not promoted into
a theorem about global Index construction.

## Checks and adversarial challenges

Baseline fresh build directories: both packages, default audits and native
tests pass under

```
nix develop -c /Users/qobilidop/my/work/p4blo-frame-initialization/scripts/check-lean.sh
```

Exit 0, 472 specification checks (21 new frame checks), all user-package
checks. No copied caches were used. Full Python/schema, required real-Lean
DRT, Docker/P4-oracle and XDP gates are left to the integrator; this scoped
increment changes only Lean proof/test modules and registration, with no
surviving runtime or protocol edit. Their absence here is not a passing
result.

Each following campaign changes only the actual production `forBlock` in
`ir/P4bloIR/Env.lean`, then runs the production build first:

```
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.Env
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.FrameInitialization
```

Run from the isolated worktree's absolute `ir/` directory. Production builds
must exit 0 before a semantic proof rejection is counted. A rejection here
is a failed exact logical equation, **not** a compiled Python/Lean mismatch.

1. Drop each just-initialized binding:

   ```diff
   -    vars := vars.insert name (← Value.zero decl.type index)
   +    vars := (vars.insert name (← Value.zero decl.type index)).erase name
   ```

   Production compiles, exit 0. The theorem build exits 1 because the actual
   loop containing `erase` cannot satisfy `forBlock_correct`'s exact result.
   A secondary unused-simp warning is not counted as the kill.

2. Initialize declaration names instead of scope map keys:

   ```diff
   -    vars := vars.insert name (← Value.zero decl.type index)
   +    vars := vars.insert (if name == decl.name then name else decl.name) (← Value.zero decl.type index)
   ```

   The conditional retains use of both actual loop variables and always
   selects `decl.name`. The malformed-key witness explains why assuming
   self-naming declarations would conceal this change. Production compiles,
   exit 0; the theorem build exits 1 at the changed-loop exact equation.

3. Add an action overlay to a fresh block frame:

   ```diff
   -  pure { scope, vars }
   +  pure { scope, vars, action := some "ghost", actionVars := some {} }
   ```

   Production compiles, exit 0; the theorem build exits 1 because the actual
   returned frame has `some "ghost"` and `some {}` where its exact result
   requires absent action fields.

All three faults were restored. Original and restored production file SHA256:
`69b4484e9e669bb0fa37d436d965d4a9e6462fd6fe96083e310c0001168b0624`.
`git diff --exit-code -- ir/P4bloIR/Env.lean` exits 0. Supplementary local
logs are `/tmp/p4blo-frame-{drop,name,overlay}-{production,proof}.log`;
the tracked exact patches above and theorem/test modules are the durable
reproduction evidence. No execution replay bundle is invented for a failed
proof build.

After restoring all faults, the same complete two-package command passes
again, exit 0, with all 472 specification checks, default audits, constructive
kernel tests and user-package tests. `git diff --check` also passes.
Independent review is clear: `notes/reviews/frame-initialization.md`. The
reviewer independently rebuilt the theorem/kernel-test/default-audit targets,
ran all 472 specification checks, queried the public roots' exact axiom sets
and verified the restored production hash and empty diff.

Confidence: high in the scoped map/loop result; the proof API cost resolved
without a runtime refactor. The remaining decision is to retain explicit
all-scope declaration success at this boundary. Revisit only when an actual
user source-zero adapter can discharge it for modeled roots **and extras**.
The next bounded step is that adapter and a concrete real-built forwarding
scope, before any call/body-prefix theorem.
