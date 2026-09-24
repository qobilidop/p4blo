# Independent source-zero review

Final review: clear for the bounded source-zero checkpoint.

2026-09-23. Reviewed the stable, restored candidate in
`/Users/qobilidop/my/work/p4blo-source-zero`, based on `6ff0449`.
No candidate edits or rebuilds were performed by this reviewer.

## Findings

The source initializer is genuinely independent: Fin zero, Bool false,
header invalidity and recursive Record construction do not invoke IR zero,
conversion or evaluation. Its proof compares conversion afterward with the
actual production `Value.zeroWith`, not a replacement proof-only initializer.

The explicit maximum-depth budget matches the real recursion: a scalar
consumes one unit, each aggregate consumes one before initializing all of its
children at the same remaining fuel, and an empty aggregate consumes one.
The layout maximum is appropriate; summing sibling depths would be an
unnecessarily stronger premise. The public production-zero corollary keeps
its actual HashMap-size-derived fuel bound explicit. No nominal acyclicity,
global validation or automatic budget sufficiency is smuggled in.

IndexAgrees supplies exact kind, stored declaration name and fields, plus
recursive agreement. The test that malformed stored nominal names are
returned unchanged by runtime zero correctly protects a behavior outside
that theorem premise. Width zero is correctly allowed by this raw source
representation; positive-width authoring validity is a distinct obligation.

The mixed nested fixture and existing forwarding roots constructively
discharge the actual budget with checked HashMap lemmas. Independent expected
IR constructors pin stored fields and false validity, rather than comparing
two calls to the same initializer. Tests cover empty aggregates, Boolean and
0/1/8/9/65-bit scalars, several sufficient budgets and every insufficient
budget below the fixture's depth, missing names and malformed nominal names.

The root export, ordinary user test driver and three default axiom guards
are registered. README and note correctly stop before frame construction,
parameter binding, action-layer exclusion, copyback and global validation.
No blocking defect found.

## Independently executed checks

- Existing compiled userTests: exit 0, including source-zero native answers
  and all earlier user suites.
- Pinned Lean stdin import of SourceZeroTests and fresh native `#eval`:
  exit 0. Queried Shape.zeroWith_correct, Layout.zeroWith_correct and
  Shape.zero_correct: all exactly `[propext, Classical.choice, Quot.sound]`.
  The concrete actualZero and forwardZero witnesses have the same foundation.
- Restored SourceZero.lean and actual Value.lean SHA256 hashes exactly match
  both hashes recorded in the note. Value.lean git diff is empty.
- Candidate diff whitespace check passes.

An initial standalone import query placed the IR build directory first and
failed because that directory still contains stale pre-rename `P4blo/`
artifacts. Placing the user package first resolves the correct namespace and
the query passes. This is a local cache/search-path observation, not a source
failure. This review does not claim an uncached package build; the complete
two-package gates are the implementer's separately attributed results.

## Adversarial evidence

Inspected actual logs for all three faults. Source-only invalid-to-valid
headers and production-only invalid-to-valid headers both fail the universal
correspondence at the genuine false/true equality. The extra termination
warning is not the semantic detection evidence.

Changing both source and production initializer consistently builds the
universal correspondence and all user audits, but the independent constructor
answer, validity list and actual-zero expected-value theorem fail. This is a
useful demonstrated shared-model survivor killed by independent kernel
answers, not a runtime Python differential mismatch. The note preserves exact
edits and correctly avoids inventing a replay bundle for proof rejection.

Next frame work must still cover every actual scope variable, including
unmodeled observer extras, exact lookups, and the absence of an action layer.
The present theorem is a sound ingredient, not that larger conclusion.
