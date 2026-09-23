# Independent review: command list sequencing

2026-09-23. Read-only review of `/Users/qobilidop/my/work/p4blo-command-blocks`.
Reviewer did not author or edit this candidate and did not build its files.

## Final disposition

Clear for the complete command-list checkpoint. No corrections requested.
Merged full gates and the identified `ForwardPolicy` normalization/audit
remain the integrator's obligations, not completed by this read-only review.

`CmdWith.block` is a single `foldr seq done` over the existing command AST.
It introduces no syntax constructors, evaluator, lowered execution path or
permission policy. Scalar and field APIs are thin aliases with concrete
specializations of the generic list laws.

The generic source theorem states equality to a left-to-right `List.foldl`
that evaluates each component at its predecessor's final source state. It
does not define the expected meaning by calling `block` again. The lowering
theorem independently specifies `flatMap` of the component lowerings in list
order. Their induction steps use the already established `seq` laws. Empty
and singleton lists have exact syntax identities; singleton identity includes
branch continuations through the existing `seq` definition. Existing actual
machine execution and declaration/permission proofs are unchanged and apply
to the resulting ordinary command.

`CommandBlockTests` contains a direct IR syntax anchor, not an expected result
obtained from the combinator. Its assignments set scratch to 10, add 1 or 2
depending on the route hit, then add 3 after either branch. Runtime expected
answers 14/15 therefore check dependency on prior writes, both branches and
the shared tail. Source and actual IR execution are separately observed;
header, metadata, route and unrelated roots are checked unchanged. Existing
whole-Run preservation theorems remain stronger than these finite examples.

No structural correctness or scope issue found. Named-field resolution is
outside this review; this reviewer authored that preceding checkpoint.

## Stable refactor and independent execution

The final inspected `dependent` and forwarding rewrite bodies use readable
block lists. Two kernel `rfl` examples equate the entire new commands to the
exact previous nested `seq` ASTs, including both branch bodies and shared
continuations. Inspection against the actual old-file diff confirms these
anchors reproduce the previous definitions rather than modified expected
programs. This is stronger than agreement on a finite collection of outputs.

Independently ran the candidate's already compiled `userTests` executable:
exit 0. Separately imported `CommandBlockTests`, evaluated its runtime test
and printed all seven default-audited roots using `lake env lean --stdin`:
exit 0. The three denotation roots have no axioms; the generic singleton and
three lowering roots use exactly `[propext]`. No candidate build or code edit
was performed. Logs are `/tmp/p4blo-command-block-review-user-tests.log` and
`/tmp/p4blo-command-block-review-audits.log`.

Root reports byte-identical old/new `fieldCommands` exporter output and 23
focused authored command tests passing; those are author evidence, not
independently rerun checks in this review. The branch predates the independent
`ForwardPolicy` theorem. Root identified its expected normalization update
(unfold the two transparent block aliases); that integration build remains
required even though the authored command ASTs are definitionally unchanged.

## Final campaign and compatibility checks

Inspected the actual reverse and skip fault logs. Reversal fails both the
independent left-fold source equation and concatenated-lowering equation;
skipping the head also fails singleton identity. The bodies remain valid
command constructors, so these are genuine false semantic-law failures, not
syntax or wrong-type failures. Unused-simp diagnostics appear in addition and
are correctly excluded from the claimed evidence. No runtime differential
replay is claimed for rejected builds.

The final tests add explicit fault-sensitivity controls: reversing the test
list yields 10, and omitting its initial assignment yields 23/24 instead of
the independent expected 14/15. Independently reran the final compiled user
tests including these controls: exit 0. Inspected restored build/runtime
logs, and independently compared restored mutant `Commands.lean` with the
candidate byte-for-byte: equal. The 405 required DRT and 23 focused authored
test success logs agree with the author's stated gates.

Compared `PolicyCompatibility.lean` with actual current main's
`P4blo/ForwardPolicy.lean`: the only difference is adding `Cmd.block` and
`Scalar.CmdWith.block` to the explicit `dsimp` list. The policy, theorem
statement and remaining proof are unchanged. Its successful compatibility
probe is appropriate evidence, explicitly not a substitute for integration's
real default audit. Scratch removal and the real main audit remain root-owned.

`docs/notes/command-blocks.md` accurately records the narrow scope, complete
old-AST anchors, distinct proof/runtime evidence and integration obligation.
The exact isolated fault recipes are reproducible. No new source or IR
semantics, parser, global initialization or whole-program claim is introduced.
