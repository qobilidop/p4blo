# Checked named scalar paths

2026-09-23. First checkpoint from `authoring-ergonomics-plan.md`. This adds
ordinary smart constructors only; command lists, macros and example rewrites
remain separate work. The source representations, semantics and lowering in
`Fields`, `FieldExpressions` and `FieldCommands` are unchanged.

## Contract and decisions

```lean
def ttl : Fields.Place modes (.bits 8) :=
  Fields.Place.named ["hdr", "ipv4", "ttl"]
def nextDst : Fields.Ref roots (.bits 48) :=
  Fields.Ref.named ["route", "dst"]
```

The expected type supplies roots, modes and exact scalar type. `Ref.resolve`
and `Place.resolve` are total fallible functions returning existing typed
references/places, with explicit `ResolutionError` values. Every visited
segment must be nonempty and match exactly one name in that layout, regardless
of the other matches' types. Intermediate values must be aggregates and the
endpoint must be a positive-width bitvector or Boolean of exactly the
requested type. Places additionally check the existing root mode's writable
flag; input and directionless parameters remain read-only.

Lookup returns an actual `Slot` carrying a proof of its spelling and selected
name count. Recursive resolution produces existing `Path` and `Ref` values,
not a second AST, fallback offset or echoed request. The six public audited
roots (`Ref.resolve_sound`, `Ref.named_sound`, `Ref.named_expr`,
`Place.resolve_sound`, `Place.named_sound`, `Place.named_lvalue`) depend on
exactly `[propext]`. They certify structural spelling, nonempty unique
visited names and a valid scalar endpoint; the expression/lvalue corollaries
relate actual lowering to the direct requested root/member chain.

The successful constructor proof defaults to `by decide +kernel`. Plain
`decide` gets stuck reducing the proof-carrying lookup/equality transport on
successful paths in this pinned Lean version. Kernel reduction discharges
the same proposition without `native_decide`, unchecked casts, new axioms or
an external evaluator. Dynamic callers use the fallible resolver for precise
diagnostics. Invalid concrete smart constructors fail elaboration.

High confidence: retain existing representations, root permission policy,
exact spelling certificates and separate semantic premises. Medium confidence:
explicit segment lists and default kernel decision are the best ergonomic
surface. Revisit if realistic schemas make reduction slow, errors obscure the
bad segment, or callers need repeated type transports. Prefer a minimal
checked elaborator only after those issues arise; do not weaken resolution.

This is deliberately not global schema or nominal-index validation. Unvisited
duplicate/empty names and malformed shapes are not certified. Cross-root
nominal consistency, declaration agreement, frame agreement and permission
agreement with real runtime declarations remain the existing execution
theorems' separate premises. Names do not specify aggregate nominal kinds;
the existing layout fixes those kinds. No general resolver completeness or
reference-identity uniqueness theorem is claimed beyond the proved unique
selected-name counts and deterministic resolver. Whole-program correctness,
packet parsing and intended application policy are unchanged obligations.

## Checks

`NamedFieldsTests` is imported and run by the default user test executable.
It includes 17 exact kernel diagnostic answers, 11 rejected smart-constructor
elaboration attempts, local/out/inout writes, input reads, exact lowered
names, distinct same-width siblings, and independent source-store values.
Two schemas reorder `other : bits 8` and `wanted : bits 8`; both named paths
lower to `root.wanted` and return independently initialized value 7 rather
than sibling value 3. Duplicate matches are tested at the head, after an
unrelated head, with differing scalar types and scalar/aggregate kinds.
One positive case explicitly demonstrates the unvisited-schema boundary.

Candidate gates (working tree based on `ae9ca87`):

- `nix develop -c scripts/check-lean.sh`: exit 0, both packages, default
  audits, all existing runtime suites and named tests.
- `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees`:
  exit 0, 405 passed, 1338 deselected, no skips.
- Independent read-only review: clear; compiled user tests, separate module
  evaluation and all six exact audit roots independently checked, along with
  mutation logs and byte-identical restoration. Integration retains the report
  at `docs/notes/reviews/named-paths.md`.

## Adversarial campaign and reconstruction

Use an isolated worktree with these candidate files; never mutate the working
implementation. For each edit below, build from that worktree's `lean/`
directory with `nix develop -c lake +leanprover/lean4:v4.34.0 build TARGET`.
Restore the exact edit before the next case. No Python or IR semantics are
changed in this authoring-only checkpoint, so no new differential mismatch
bundle is claimed; the existing required conformance suite is a regression
gate. The previous field-command production fault bundles remain unchanged.

1. **Wrong sibling, naming-proof rejection.** In `resolveSlot`'s nonmatching
   head branch replace
   `pure ⟨selected.shape, .there selected.slot, selected.spelling, empty,`
   with `pure ⟨shape, .here, by simp_all [Slot.name], empty,`.
   Keep the existing name-count proof. This is a shape-correct existential
   selection of the wrong head; for `other8/wanted8` it selects the same-width
   sibling. Building `P4blo.NamedFields` exits 1 at the spelling proof with
   `name ≠ query` and unsolved goal `False`. It is not runtime detection and
   is not merely a dependent shape mismatch.
2. **Wrong diagnostic, kernel known-answer rejection.** Replace only
   `| .nil => .error (.missing query)` with
   `| .nil => .error (.ambiguous query)` in `resolveSlot`.
   Building `P4blo.NamedFields` exits 0: successful-resolution soundness says
   nothing about exact error labels. Building `P4blo.NamedFieldsTests` exits 1
   on expected missing-name diagnostics, including a proposition proved
   false for the missing root. This is kernel regression-test rejection,
   not a runtime interpreter mismatch.
3. **Valid wrong authored name, compiled runtime detection.** In `run` only,
   change the local `selectedDst` constructor's path from
   `["hdr", "ethernet", "dst"]` to `["hdr", "ethernet", "src"]`.
   Building `P4blo.NamedFieldsTests` exits 0; both named-lowering audits still
   report `[propext]`. The following command exits 1 with
   `authored destination name must select the independent destination value`:

   ```sh
   nix develop -c lake +leanprover/lean4:v4.34.0 env lean --stdin <<'LEAN'
   import P4blo.NamedFieldsTests
   #print axioms P4blo.Fields.Ref.named_expr
   #print axioms P4blo.Fields.Place.named_lvalue
   #eval P4blo.NamedFieldsTests.run
   LEAN
   ```

After restoration, the same module build and evaluation exit 0. Both new
files compare byte-for-byte with the candidate. Session evidence is retained
in `/tmp/p4blo-named-mutant-{wrong-slot,diagnostic-build,diagnostic-tests,alias-build,alias-runtime,restored-build,restored-runtime}.log`;
the exact recipes and outcomes above are the repository's durable evidence.
The isolated tree is `/Users/qobilidop/my/work/p4blo-named-path-mutants`.
