# Actual frame initialization review

2026-09-23. Final disposition: clear for the scoped IR checkpoint.
The integrator independently reviewed the stable/restored candidate in
`p4blo-frame-initialization` at base `c2bb0c8`; no implementation or test
source was edited by this reviewer.

The private list lemma proves the actual `forIn` operation, not a competing
initializer. Repeated list keys assign the same proven value, so its exact
lookup result does not assume a HashMap insertion order or representation.
The public theorem connects this loop to the unchanged `Frame.forBlock`
definition, using actual `toList` membership and map lookup facts.

Per-declaration actual zero equations, or merely successful actual zeroing
in the derived theorem, cover every scope entry. No whole-frame correctness
callback, globally valid index, source-model completeness or implicit fuel
adequacy is assumed. The conclusion pins all lookups, including absent
names, the exact selected scope and both absent action fields. Scope/block
and map-key/declaration-name consistency are deliberately not prerequisites.

Independent constructor values and kernel witnesses make the premises
nonvacuous. The mixed fixture covers every parameter direction, observer and
unrelated locals, nested and empty invalid headers, widths 8/9/65 and Bool.
It deliberately gives the selected scope a different block/kind and one
variable a different stored declaration name. The failing extra declaration
has a checked impossibility witness for the all-entries premise. Actual
Index.build is additionally tested without being claimed as a universal
index-construction theorem.

Independently executed after restoration:

- Pinned build of FrameInitialization, its kernel tests and ProofAudit:
  exit 0. Default root/test/audit registrations were inspected.
- Pinned `lake test`: exit 0, all 472 spec checks, including the 21 new frame
  observations through both raw storage and action-first reads.
- Fresh Lean query of all three public axiom sets: each exactly
  `[propext, Classical.choice, Quot.sound]`.
- Production Env.lean SHA256 matches the recorded restored/original value:
  `69b4484e9e669bb0fa37d436d965d4a9e6462fd6fe96083e310c0001168b0624`.
  Its git diff is empty; candidate whitespace checks pass.

Inspected the actual drop-binding, wrong-name and action-overlay failure
logs. Each changes the production initializer and reaches a genuine wrong
loop/result equation in forBlock_correct; secondary unused-simp warnings
are not counted. The implementer separately checked production compilation
before each proof rejection and both complete Lean package gates before and
after restoration. This review did not repeat the live mutations. Exact
edits and distinctions are recorded in `notes/frame-initialization.md`.

No remaining finding. Full Python/schema and required DRT are separate
integration gates, not inferred from these scoped checks. A source-zero to
FrameMatches adapter must still discharge all scope entries, including extras;
parameter binding, call entry/return, action execution, parser unwinding and
global validation remain outside this result.
