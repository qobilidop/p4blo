# Generic command write-seam review

**Clear** for the interface-only factoring checkpoint in
`p4blo-field-commands`, after the separate field-permission relation.
Reviewed `Commands.lean`, the scalar specialization, default audit additions
and README/ASSURANCE updates read-only. Concrete field command permissions
and execution discharge remain a following checkpoint, not a current claim.

`CmdWith Reads Places` owns the sole command AST and recursive denotation,
lowering, sequencing and possible-target collection. Its source denotation
uses only supplied source read/write functions and the independent scalar
expression semantics; it does not invoke the IR evaluator. Assignment
evaluates against the current store, updates that store before the tail,
and conditionals run the chosen branch before the common tail. Lowering
preserves the same structure. Scalar `Cmd` is an abbreviation with thin
adapters and retained named constructors/combinators, not a second recursive
command evaluator.

The generic prefix theorem assumes exact successful read/write leaf laws
at related states, not correctness of a whole command. The write law must
relate the independently updated source value and preserve all non-variable
Run state and every name outside the target root. `BlockFrame` is explicit
and propagated by `ChangesOnlyVars`. The proof constructs transitions of
the actual execution machine and leaves arbitrary continuation work at the
endpoint; branch and tail traces compose in the correct order. The generic
`Matches` predicate can be abstract, as appropriate for this composition
lemma; it is not substituted for a concrete user-facing correctness proof.

The scalar specialization concretely discharges reads with actual frame
lookup and writes with actual `writeVar_block` plus constructive source
`Env.set`/frame matching. It retains its existing explicit context,
declaration/permission, frame-value and no-action premises. Public
`execute_correct` still establishes authoritative typing, actual successful
execution, exact final source environment, final frame typing/declaration
agreement, full non-variable Run preservation and unrelated-name preservation.
No generic correctness callbacks leak into that theorem statement.

After stable-binary confirmation, independently ran all three existing
authored Python test files: **43 passed**, exit 0. Existing fixtures were
unchanged. Independently ran the compiled user test executable: expression,
scalar command, aggregate/read-path and API checks pass, exit 0. Queried the
retained named constructors and scalar correctness theorem through Lean
stdin, and independently checked new compiled audit roots:

- `denoteWith_seq`: no axioms;
- `lowerWith_seq`: `[propext]`;
- `steps_with`: `[propext, Classical.choice, Quot.sound]`.

The implementer reports both complete Lean package/default-audit gates
passed; no reviewer rebuild or image operation was performed. Documentation
correctly treats the factoring as a foundation and makes no new mutation
adequacy claim. The next concrete field instance must still discharge actual
root declarations/permissions, index agreement, source field get/set and
full sibling/validity preservation rather than assume them as arbitrary laws.
