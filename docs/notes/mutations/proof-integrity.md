# Proof-integrity gate challenge

2026-09-23, base `feca1ee`, isolated
`verification/mutation-campaign` worktree. This challenges the Lean
proof trust gate, not interpreter semantics. Both deliberate faults
were made one at a time in `lean/P4blo/ScalarTyping.lean` and restored
with anchored patches. No mutation is in this commit.

## Clean baseline

With the tool working directory set to the absolute `lean` directory:

```sh
nix develop /Users/qobilidop/my/work/p4blo-mutation-campaign -c lake build -q
```

The default build exited 0 before the challenges and again after both
were restored. `lakefile.toml` makes `ProofAudit` a default target and
sets `-DwarningAsError=true`.

## Challenge 1: admit the actual theorem

Replaced the complete body of `ScalarTyping.check_sound` (from
`unfold infer at h` through `exact ⟨v, by rw [hv]; rfl, h ▸ ht⟩`)
with `sorry`. The exact baseline command above exited 1 at
`P4blo.ScalarTyping` with:

```text
error: P4blo/ScalarTyping.lean:183:8: declaration uses `sorry`
```

This was a source compilation rejection under warnings-as-errors;
`ProofAudit` did not need to run. It is proof-integrity protection,
not a semantic test kill.

## Challenge 2: depend on a custom axiom

Inserted the following declaration immediately before `check_sound`:

```lean
axiom forged_check_sound {e : Expr} {t : ScalarTy}
    (h : infer e = some t) (run : Run) :
    ∃ v, (evaluate e).run run = (.ok v, run) ∧ HasType v t
```

Replaced the same proof body with `exact forged_check_sound h run`.
There was no `sorry`. The ordinary library target compiled:

```sh
nix develop /Users/qobilidop/my/work/p4blo-mutation-campaign -c lake build P4blo -q
```

It exited 0. The default build command exited 1 specifically at
`ProofAudit`. The observed diagnostic was:

```text
'P4blo.ScalarTyping.check_sound' depends on axioms: [propext,
 Classical.choice,
 Quot.sound,
 P4blo.ScalarTyping.forged_check_sound]
error: ProofAudit.lean:18:0: ❌️ Docstring on `#guard_msgs` does not match generated message
```

The guard expected only `propext`, `Classical.choice` and
`Quot.sound`, so it detected the transitive custom dependency even
though the theorem itself compiled. No warnings or `sorry` caused
this failure.

## Boundary

The audit checks transitive axiom lists for exactly its advertised
roots: `ScalarTyping.Typed.sound`, `ScalarTyping.check_sound`, and
`extract_emit`. This experiment establishes detection for these two
ways of weakening `check_sound`. It does not establish that every
theorem is audited, that theorem statements express the intended P4
behavior, or that Python agrees with Lean.

After restoration, the default pinned Lean build exited 0 and
`git diff` showed no remaining Lean source changes. Only this report
was staged.
