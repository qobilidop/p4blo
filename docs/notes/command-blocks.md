# Readable command lists with unchanged meaning

2026-09-23. Implements the list-sequencing increment from
`authoring-ergonomics-plan.md`, separately from typed named paths.

`Scalar.CmdWith.block` is one right fold of the existing `seq`, ending with
`done`. Scalar and field `Cmd.block` are thin adapters. There is no new AST,
interpreter, monad, custom parser or implicit runtime-local binding behavior.
The source effects execute in list order; a branch finishes before the next
list element. Empty and singleton behavior is checked explicitly.

Universal `denoteWith_block` equates source meaning with an independent
**left** fold of individual denotations, threading updated state. Universal
`lowerWith_block` equates lowering with concatenated per-command lowerings.
Concrete scalar/field laws expose those same equalities at the public API.
Seven roots are default-audited: generic/concrete denotation uses no axioms;
singleton and the three lowering roots use only propext. Existing command
typing, exact execution, root permissions and noninterference are unchanged.

The dependent-write and route-selected forwarding examples now use ordinary
command lists. Both **entire previous ASTs** are retained as kernel `rfl`
equations in `CommandBlockTests`; this is stronger than equality on selected
inputs. Actual main/candidate field-command exporter output also compares
byte-for-byte. Independent Python expected snapshots are unchanged.

## Checks and faults

The registered user tests contain a directly written IR sequence with a
branch and shared tail, independent of block lowering. Native checks give
scratch 14/15 for the two branches and preserve every other root. Negative
controls reverse those same commands (result 10) or omit the first assignment
(23/24), confirming the chosen examples distinguish order/omission faults.

Both complete Lean package gates/default audits pass. The scalar/field
authored-command focused suite passes 23 checks; required all-suite DRT
passes 405 without skips on base `5e7fd81`. Current merged full-gate counts
belong in `docs/status.md`; no new Python conformance count is implied by
adding Lean-local tests. Independent review: `docs/notes/reviews/command-blocks.md`.

In detached `p4blo-command-block-mutants` at `5e7fd81`, copy the candidate
modules/registrations and first run default build/user tests successfully.
Then change only the body of `Scalar.CmdWith.block` in `Commands.lean`:

1. Replace `commands.foldr seq .done` with
   `commands.reverse.foldr seq .done`. Default audit build exits 1 at both
   universal composition equations: the remaining fold cannot establish the
   claimed left-to-right meaning or concatenated lowering.
2. Restore, then replace that body with `commands.tail.foldr seq .done`.
   Default audit build exits 1 at singleton identity and both composition
   equations. A singleton has become `done`, not its supplied command.

These are genuine changed list semantics and proof rejections, not runtime
Python/Lean divergences. Extra unused-simp failures are not counted as the
semantic evidence. The native negative controls above independently exhibit
different results for both faulty list transformations. No execution replay
bundle is invented for a compile-time rejection.

Restore the exact one-line body, compare `Commands.lean` byte-for-byte with
the candidate, then rerun default build and user tests in the pinned Nix
environment. Both final restored commands exited 0, including the native
fault-sensitivity controls, before integration.

## Integration and confidence

The separately integrated `ForwardPolicy` theorem used an explicit reduction
list for the old source spelling. The equivalent new spelling requires adding
`Cmd.block` and `Scalar.CmdWith.block` to that `dsimp` list, without changing
its statement, policy or subsequent argument. Typechecking a copy of the
actual theorem against the candidate example with exactly those additions
passes. The integrator must apply this proof-normalization update and rerun
the actual default audit; a standalone compatibility probe is not that gate.

Confidence is high in order/meaning and byte compatibility, medium in whether
ordinary list syntax is sufficiently ergonomic for larger programs. Revisit
only after a real application still exposes repetitive construction friction;
do not add `do` syntax that suggests runtime bindings the language lacks.
