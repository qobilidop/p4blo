# Next firewall boundary: actual Bloom insertion

2026-09-23. Planning against `fd708e6`, after the actual initialization and
invalid-body proof. This is a bounded application step, not completion of the
firewall milestone. Existing source, runtime, CRC and oracle contracts stay
unchanged. The source module is `P4blo.TutorialFirewall`; the relevant actual
runtime is `Exec.callExtern`, `Externs.call` and `ExternState.call`.

## First checkpoint

Prove the actual `execute TutorialFirewall.insertBloom` completes normally
and updates exactly the two intended externs, in source order. Use the actual
built firewall index, actual declaration/method lookup and actual argument
evaluation. Premises identify action-first `Frame.read?` results for the two
32-bit positions and the two bound one-bit register arrays. Do not replace
these with an assumed evaluator, extern-call callback or whole-body theorem.

Allow arbitrary array lengths and contents, including empty arrays and values
outside the startup profile. The low-level register write stores the supplied
value, with no extra width normalization; the authored literal is precisely
one-bit one. In bounds it sets the selected cell to 1; out of bounds it leaves
the array unchanged. Preserve the order of actual HashMap insertions in the
whole-Run result instead of assuming structural equality of independently
rebuilt maps. Derive pointwise preservation of every other extern, every
unselected cell and array sizes separately. Frame (including scope and action
layers), index, entries/defaults, packet/emitter and visits remain unchanged.

Define independent expected cell observations by index equality and bounds,
not by calling production extern methods. Prove preservation of existing
one-valued membership and establishment of each selected in-bounds cell. A
4096-cell, in-range corollary captures the concrete profile; do not assume the
indices satisfy that bound merely because their width is 32. Hash/mask bounds
and reverse-flow equal-index properties are subsequent obligations.

Use actual finite execution derivations connected by `Finishes.sound`.
Advertised roots must pass the default axiom audit, with constructive kernel
witnesses. No sorry, native proof escape, changed runtime or silent heartbeat
increase. Native queue counts are not advertised as exact-step theorems.

## Independent execution and adversarial acceptance

- Native tests compare complete state and all cells using literal expected
  updates. Include asymmetric arrays/positions, equal positions in distinct
  arrays, zero/last/out-of-range/max-32-bit positions, empty arrays and
  noncanonical preexisting values. Include action-local positions shadowing
  different block positions and unrelated shared-state sentinels.
  Noncanonical natural cells are theorem/native-only witnesses: Python's
  `Bits(1, 3)` constructor rejects them. Never bypass that invariant to claim
  matching cross-language states. Wrong-width injected Python cells, if used,
  are separately labeled and are not those native witnesses.
- Python tests run the actual two statements extracted from the unchanged
  builder, checking their full syntax first. Use detached exact-type complete
  Env snapshots and independent full-array expected results after normal
  execution. Test the valid 4096-cell profile as well as explicitly labeled
  lower-level register boundaries; do not attribute injected malformed state
  to the public loader's accepted startup profile.
- Where matching native/Python states are exported, compare both against the
  independent expectation, not merely against each other. Retain program,
  input and configuration identity for any generic DRT mismatch; internal
  Env-only faults are not packet/state DRT failures if that observer agrees.
- In an isolated worktree, challenge actual first/second target, selected
  position, literal value and write omission. At least one compiling runtime
  fault should reject a whole-state proof; source proof rejections remain
  separately labeled. A benign reversal of independent writes can preserve
  final logical cells, so order evidence must observe intermediate execution
  if order itself is claimed. Require a first-write checkpoint in Lean and
  a delegating call trace in Python that observe array one changed while array
  two is still original; final arrays alone cannot establish ordering.
- Challenge real Python register execution and the completeness of the test
  observer. An unrelated-cell or unrelated-extern mutation must not survive
  by checking only the selected two cells. Verify hook hits, normal completion,
  exact restoration and clean replay. Compilation failures are setup evidence,
  not semantic kills. Reused saved inputs are not new independent inputs.

Both Lean packages/audits/native suites precede binary consumers. Run focused
tests, required real-Lean conformance and the full gate before integration,
with an independent read-only review. Keep original-program oracle profiles
and precise discrepancies unchanged; no Docker rebuild is needed.

## Later composition, deliberately separate

1. Prove actual readback and the two-filter check, including one-sided misses,
   actual drop action effects and preservation of preexisting drop. A successful
   membership check does not undo a previous routing drop.
2. Prove the actual 4095 masks bound both indices, then the direction-dependent
   argument reversal gives equal hash inputs for a reverse flow under explicit
   tuple premises. CRC algorithm equivalence is a different obligation.
3. Compose insertion/check through actual SYN/direction/table-hit branches,
   stating routing, parsing and classification premises explicitly. Do not
   assume the complete filtering computation to prove its consequence.

This cannot imply exact connection tracking: the permanent double-collision
counterexample remains accepted. Expiration, concurrency, arbitrary target
architectures and universal Python equivalence remain out of scope.

## Feasibility evidence, not production coverage

The unregistered `probes/FirewallBloom.lean` proves the actual first
`callExtern`, including declaration lookup, position evaluation, actual extern
dispatch and whole-Run result, for arbitrary arrays and fitting positions.
Three independent pointwise lemmas pin cell values, size and one-valued
membership. The call root uses only the standard three axioms; the cell roots
use only `propext`. No custom axioms, native evaluation or sorry remain.
The probe builds with the existing module-local recursion bound 8192 and
default heartbeat, after both full packages build with 567 spec checks.
It is not imported or registered in the default package, and does not yet
prove execution of both statements or supply native/Python fault evidence.

Reproduce with `nix develop -c lake env lean` on the absolute probe path,
working in the checkout's `lean/` directory. Development attempts needed
explicit named-path/direction reduction and reduction of the final monadic
pair; an array-size lemma needed a bounds case split. These were ordinary
proof development failures, not detected semantic mutants. Production work
must still satisfy all acceptance criteria above.

Confidence: high in the semantic boundary and exact state contract; medium
in the best reusable proof API. Initially keep application-specific helpers
in the user package. Revisit generic register laws only if a second client or
the subsequent readback proof demonstrates genuine reuse. Revisit arbitrary
malformed-array coverage if it obscures the valid profile, never by silently
strengthening premises to make faults disappear.
