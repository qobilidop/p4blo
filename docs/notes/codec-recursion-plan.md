# Make the actual recursive decoders proof-visible

Date: 2026-09-23. Baseline: `ba274f3`. Feasibility plan, not an implemented
recursive-codec theorem. Production `Json.lean` is unchanged. Read with
`codec-proof-plan.md`, `codec-proof.md`, and `keyvalue-codec.md`.

## Recommendation and confidence

Replace the actual `partial def Expr.decode` with well-founded recursion on
`sizeOf j`, carrying child bounds through its existing helper structure. Do
Expr first, LValue second, and Stmt's arrays third. Keep the public signatures,
accepted finite JSON values, default handling, field visitation order, and
diagnostic strings unchanged. Do not introduce a second decoder or fuel.

Confidence is high that finite-tree descent is available: the attached probe
kernel-checks the hard lookup/default bounds against the actual pinned Json
representation. Confidence is medium in the size of the helper refactor:
oneof erasure and general array traversal erasure remain implementation work.
No whole-decoder refactor or recursive roundtrip theorem has been checked yet.
This is a concrete next increment, not a claim that the barrier is closed.

## Actual dependencies, not mutual recursion

`Expr.decode` recurses only into Expr. `LValue.decode` recurses into LValue
and calls Expr. `Arg.decode` calls those two without recursion. `Stmt.decode`
recurses only through conditional branch lists and calls Expr/LValue/Arg.

```
Expr  →  LValue  →  Arg  →  Stmt
  └───────────────────────┘
```

The arrows indicate availability order, not that Expr calls LValue. No mutual
termination construction is required. Expr contains no recursive arrays, so
it can land without first solving the general array helper equivalence.

## Checked descent facts

`CodecRecursionProbe.lean` is an isolated non-production module, not a package
target or an alternative codec. Its seven named audited theorems establish:

1. A successful `Std.DTreeMap.Internal.Impl.Const.get?` returns a value with
   strictly smaller structural `sizeOf` than the tree containing it.
2. Lifting through the two Raw wrappers and `Json.obj` preserves strictness.
3. Each indexed Json-array element is strictly smaller than `Json.arr xs`.
4. `sizeOf (Json.mkObj []) = 4`; this is no larger than any `Json.obj fields`.
5. A successful `Decode.get? path j key = .ok (some v)` implies `v < j` in
   structural size, accounting for actual null-as-absent behavior.
6. On successful get, its message target including the `{}` default is
   **no larger** than the containing object.
7. The candidate bound-carrying `boundedMsgField`, with proofs erased from
   its callback, equals the **actual** `Decode.msgField` for every callback,
   input, key, path, and valid enclosing bound. Errors are included.

All seven audit outputs contain only `[propext, Classical.choice,
Quot.sound]` or a subset, never `sorryAx` or a native decision axiom.
The probe's attached-array callback type also compiles; two definitional
examples check left-to-right indexed results and the first-error path.
Those examples are not its still-missing universal erasure theorem.

The tree proof does not require `TreeMap.Raw.WF`, sortedness, balancedness,
or truthful cached node counts. It follows physical lookup branches using
the generated structural `sizeOf`, **not** the cached `Impl.size`. Thus it
does not accidentally restrict which in-memory Json objects are accepted.

### The default-value subtlety

The existing module comment says every recursive call uses a proper sub-value.
Literally this is false for missing/null message fields: `msgField` synthesizes
`{}`. It must be corrected when the production refactor lands.

For Expr, the oneof payload `v` is strictly smaller than the enclosing `j`.
Successful message-field access establishes
`sizeOf target ≤ sizeOf v < sizeOf j`, including a synthesized empty object.
Trying to prove `target < v` fails for an empty payload and would encourage
an unnecessary semantics-changing missing-field special case. Keep the
original default decoder call and its exact nested `no kind set` diagnostic.
For non-object payloads, `get?` fails before invoking the callback.

## Smallest production patches

### A. Expr visibility, with helper erasure

- Add the structural lookup/default lemmas in a focused helper module or
  the existing Decode namespace; production Json must import them. Isolate
  dependence on pinned TreeMap internals behind the lookup lemma.
- Add proof-carrying lookup/oneof selection preserving the old case-list
  traversal. Either refactor `oneof` into a selector plus callback dispatch,
  proving its erasure against the current helper before replacement, or
  supply a dependent counterpart with an erasure theorem. Do not replace
  recognized-case scanning with object iteration: error order differs.
- The selected callback receives `sizeOf payload < sizeOf outer`. Use the
  checked bounded message helper for recursive Expr arguments; keep normal
  helpers for leaf/enum/scalar arguments.
- Replace **the existing** `Expr.decode` definition with `def ... termination_by
  sizeOf j`, keeping constructor/argument order byte-for-byte in intent.
  Recursive arguments use the supplied strict bound. There must be only one
  production Expr decoder and ordinary callers must continue using it.
- Prove actual unfolding and one nontrivial nested representable roundtrip
  before calling the proof-visibility seam usable. Add universal Expr
  representability/roundtrip only if it remains a reviewable increment; it
  must constrain embedded Literal/Ty and uint32 slice indices, not semantic
  validity. An unfolding theorem alone is not the universal codec result.

### B. LValue, then Stmt

Reuse Expr's helper contract for LValue; its index calls the already-total
Expr decoder. Arg needs no recursion refactor. Stmt requires an attached
array traversal: each element carries actual membership and therefore a
strict size bound. Compose `element < array < conditional payload < outer`.
Empty/missing/null branches must remain `[]`.

`Array.mapFinIdxM` is not sufficient by itself: its callback gives an index
bound and a separate element, but **no equality** relating that element to
`xs[i]`. `xs.attach.mapIdxM` supplies real membership without inventing that
equality. Prove its proof-erased traversal equals existing `xs.mapIdxM`
including first-error behavior before changing production Stmt. Pinned core
has attach/list/array mapping lemmas, but this investigation did not find a
ready `mapIdxM_attach` theorem. A local traversal induction is an explicit
remaining obligation, not assumed finished.

No general Program codec theorem, parser-raw-text theorem, semantic validator
proof, or Expr/Stmt execution theorem follows from these patches.

## Concrete comparison with `partial_fixpoint`

The actual interpreter runner uses `partial_fixpoint`; it is a reasonable
alternative to check, but not a drop-in replacement here. The pinned core has
`MonadTail (Except ε)` with a flat-order bottom, not `MonoBind (Except ε)`.
`CodecFixpointProbe.lean` checks a tail-recursive Except control successfully
and prints the standard-axiom unfolding theorem, then deliberately fails on
a recursive call whose result is bound and mapped through a constructor-like
operation. The compiler reports:

```
Could not prove ... to be monotone in its recursive calls
Tried to apply 'Lean.Order.monotone_bind', but failed.
Possible cause: A missing 'Lean.Order.MonoBind' instance.
```

This is the non-tail result dependency present in Expr member/index/binary,
not evidence that every possible fixed-point encoding is impossible. A CPS
refactor, lifted result domain, or different order might work, but changes
more machinery and leaves finite-input termination to a separate theorem.
Given the compiled subtree/default bounds, prefer well-founded recursion.
Neither alternative warrants a hidden fuel cutoff. Logical termination also
does not promise unlimited runtime stack/memory; bounded resource tests and
fail-closed process handling remain necessary.

## Acceptance and adversarial tests before integration

- Save actual pre-refactor native results for independently authored Expr
  inputs: every constructor, unequal binary/mux operands, nested member/index,
  decimal/uint32 limits, representable but semantically invalid nodes.
  Compare post-refactor abstract descriptors, canonical encoded wire, and
  **exact** failure strings, not merely success/failure.
- Explicit malformed vectors: nonobject top-level and payload, missing/null
  message, unknown-only object, zero/multiple recognized kinds, null kind plus
  live kind, several errors in different fields, malformed nested operands.
  Keep case-list error ordering and path punctuation unchanged. Stmt adds
  invalid element 0 versus later elements and both branch-list diagnostics.
- Extend real Python/Lean codec probes with type-sensitive JSON comparison,
  and feed actual Lean-encoded outputs into Python's public protobuf path.
  Preserve semantically invalid but representable syntax; do not run a
  validator as a substitute for parsing. Do not assert general ProtoJSON
  parity: unknown fields, aliases, duplicate raw keys and other policy gaps
  remain separately bounded.
- Any generated recursive campaign must save raw request plus expected
  descriptor/wire **before** losing exceptions. Current leaf `assert_leaf`
  saves nonzero/malformed replies but `subprocess.TimeoutExpired` escapes
  before save. Fix the observer in the next implementation's scope and test
  fake timeout, crash, malformed output, missing output, and type confusion;
  captured timeout output can be bytes and must be normalized safely.
  The artifact must identify profile, seed/minimal sequence, command and
  observed failure, and replay must fail on empty selection or wrong counts.
- Build both packages before cross-language tests; run ordinary native
  tests, audit actual theorem roots, required `test_lean_agrees` cases, and
  ordinary full gate. Add endpoint/default-target registration and its guard
  through the integrator, not an unregistered proof file.
- Deliberately swap unequal recursive operands in only one direction: prove
  the actual source compiles, then show theorem rejection/runtime detection
  as separate evidence. Swap both encoder/decoder consistently: roundtrip may
  survive, but independent descriptor/wire known answers must fail and save
  a replay. Deliberately perturb a default or first-error ordering and show
  exact negative tests detect it. Restore every fault and replay artifacts
  successfully. A termination elaboration failure is not a semantic mutant
  detected by a runtime test.

## Reproduce these feasibility checks

Run from a checkout using the pinned Nix environment; substitute the absolute
checkout path for the two probe paths below. These modules are not imported
by production or default targets.

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build P4bloIR.Json
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir env lean /Users/qobilidop/my/work/p4blo-codec-recursion/docs/notes/CodecRecursionProbe.lean
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir env lean /Users/qobilidop/my/work/p4blo-codec-recursion/docs/notes/CodecFixpointProbe.lean
```

Observed exits: baseline **0**, descent/helper probe **0**, fixed-point
negative control **1**, specifically the non-tail Except monotonicity error
after its successful tail control. No production file changed; no Docker or
full Python run is claimed for this planning-only increment. Scratch theorem
development initially encountered ordinary branch-order/simplification/type
inference failures; only the final zero-exit descent probe is positive evidence.

Pinned sources inspected: `Lean/Data/Json/Basic.lean`,
`Std/Data/TreeMap/Raw/Basic.lean`, `Std/Data/DTreeMap/Raw/Basic.lean`,
`Std/Data/DTreeMap/Internal/{Def,Queries}.lean`, `Init/Data/Array/{Basic,Mem,Attach}.lean`,
and `Init/Internal/Order/MonadTail.lean`, under Lean v4.34.0. Concrete next step:
independent review of this plan, then the Expr-only production slice with
pre-change diagnostics and helper-erasure checks. Arrays can follow separately.
