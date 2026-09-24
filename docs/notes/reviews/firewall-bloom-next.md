# Firewall Bloom insertion plan review

Final review: clear for the proposed first checkpoint; no implementation or
execution proof is supplied by this planning review.

2026-09-23. Independently read the complete planning document in
`p4blo-firewall-bloom-next` against the committed `TutorialFirewall.insertBloom`,
`Exec.callExtern`, `Externs.call`, `ExternState.call`, and Python register/value
implementations. No candidate files were changed and no builds were run.

## Semantic boundary

The proposed premises are sufficient for a useful actual-machine theorem:
the real built index fixes instance/type/method lookup and the two in-only
arguments; actual action-first position reads and the two register-state
lookups then determine the two calls. Both authored result destinations are
absent. This permits a genuine whole-Run result preserving the complete frame,
including any active action layer, rather than assuming a block-only frame or
an evaluator-correctness callback.

The operational register write sets the chosen cell to the supplied natural
value when in bounds, otherwise preserves the array. It does not normalize
preexisting values. Exact ordered extern-map insertions are the appropriate
whole-state conclusion; pointwise unchanged-other-key and unchanged-other-cell
corollaries should be derived separately. The two distinct register names do
not imply disjoint numerical positions, and the plan correctly covers equal
positions as well as empty and out-of-range arrays.

Preservation of existing **one-valued membership** is sound even with arbitrary
natural cells. Numeric monotonicity would not be: overwriting a cell containing
3 with 1 decreases its natural value. The explicit 4096/in-range corollary is
also necessary; a 32-bit position alone supplies no 4096-cell bound.

## Clarifications applied before clearance

The final plan now explicitly keeps noncanonical natural cells as Lean theorem
and native witnesses. Python rejects `Bits(1, 3)`; bypassing that invariant
would not establish a corresponding accepted Python state. Cross-language
observations must use representable cells, with any separately injected
wrong-width state labeled honestly.

The final plan also requires a Lean first-write checkpoint and a delegating
Python trace observing array one updated while array two remains original.
The final logical arrays alone cannot distinguish reversal of these independent
writes. This closes the possible overclaim about execution order.

## Acceptance and limits

The independent full-array/full-Env expectations, action-shadowing cases,
unrelated-state faults, actual compiling runtime fault, and separate proof
versus runtime detection labels are appropriate. Normal completion, hook-hit
counts and restoration remain required; a packet/extern observer survivor must
not be relabeled as a detected internal-state divergence. Reused replay inputs
remain reused evidence.

Readback/drop composition, hash masking and reverse-flow inputs, actual SYN
and table-hit control flow, and the permanent Bloom-collision counterexample
are correctly deferred. Neither this insertion theorem nor the plan proves
exact connection tracking, complete firewall behavior, concurrency safety, or
universal Python equivalence.

Confidence is high in the first semantic boundary. The proposed medium
confidence in a reusable API is reasonable: start application-specific and
extract generic register laws only after a concrete second use.

## Subsequent feasibility probe

Independently read and executed the later unregistered
`docs/notes/probes/FirewallBloom.lean` with pinned Lean 4.34.0,
`-DwarningAsError=true`, and the frozen candidate's user/spec library paths.
The command exited 0. `first_call` uses exactly the actual `callExtern`, actual
method/instance lookups, action-first position read and register operation; its
conclusion gives the complete resulting Run through the one intended map
insert. The only assumptions are the actual index, actual position binding
and actual first register state. There is no assumed evaluator/call result.

The first-call theorem reports exactly `propext`, `Classical.choice`, and
`Quot.sound`; the exact cell observation, size preservation and existing-one
membership laws each report only `propext`. The natural-valued array helper
describes the actual update, while its observation law supplies the independent
index-equality/bounds characterization needed later.

This closes feasibility for one call and these cell laws only. The probe does
not yet establish actual two-statement dispatch/completion, the second call's
preserved premises, complete first-write checkpoint evidence, or a registered
application theorem. Its explicit recursion setting is local to this probe;
no runtime or production registration changed. Clear to retain the plan and
probe together with these limits.
