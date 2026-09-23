# Proof-visible scalar equality review

Reviewed 2026-09-23: the integrator's working diff against `1d942b5`,
read-only from the independent review worktree. Scope: `Value.equal`, its
two definitional equations, their axiom audit, and scalar regression test.

No blocking finding.

- The previous scalar fallback was derived `BEq Value`. Its matching bits
  constructor delegates to `BEq Bits`, whose existing explicit definition
  compares both width and value; its bool constructor delegates to `BEq
  Bool`. The two new branches use exactly those same comparisons.
- Different-width bit values remain unequal even when numeric values match.
  Bits versus bool, scalar versus aggregate, enum and error comparisons
  still use the unchanged constructor-sensitive fallback. There is no new
  coercion or validity assumption. Width zero remains representable in raw
  runtime `Bits` and is covered without being declared valid IR syntax.
- Header validity, stored fields of invalid headers, struct fields, stack
  elements and ignored stack cursor behavior retain their previous branches.
  Recursive aggregate comparisons naturally reach the new scalar branches;
  since those preserve scalar meaning, this introduces no intended change
  to aggregate equality either.
- Both equations are `rfl` proofs over the actual interpreter helper, not a
  second evaluator or an assumed correspondence. Their expected audit is
  exactly `[propext]`, a standard foundation already admitted by this
  project; no existing audit expectations were weakened. The initial
  no-axioms expectation failed on the real build, correctly revealing this
  transitive dependency through the recursive-definition machinery. An
  `rfl` proof's surface syntax alone does not imply an empty axiom set.
  Exposing these branches makes scalar proofs avoid unfolding the generated
  nested-recursive `BEq Value`, which is an appropriate narrow prerequisite
  for exact eDSL lowering preservation.
- The regression compares all 529 ordered pairs from 23 samples against
  the unchanged derived comparison. It includes widths 0, 1, 2, 8, 32, 64,
  129, zero/one/maximum values, both booleans and cross-kind comparisons.
  Some samples coincide after wrapping (especially width zero), so 529 is
  the number of comparisons, not the number of distinct semantic cases.
  Existing aggregate equality assertions remain unchanged.

This is source/diff review, not an independently rerun build or mutation
campaign. The integrator reports the specification build, exact-axiom audits,
288 Lean checks and 95 required cross-language conformance tests passed.
The corrected audit introduces no custom or unexpected axiom; this reviewer
inspected its exact `[propext]` expectation without independently rerunning
those gates.
No main-worktree changes or commits were made by this reviewer.
