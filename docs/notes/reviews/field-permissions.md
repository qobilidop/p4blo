# Field command permission relation review

Disposition: **clear** for the small authoritative relation checkpoint,
reviewed read-only in `p4blo-field-commands` against `d8e2341`. Only
`ir/P4bloIR/FieldTyping.lean` and `ir/Tests/FieldTyping.lean` implement this
increment. The generic command refactor and concrete execution theorem
remain later work, not claims of this checkpoint.

`WritablePath.var` requires the actual block lookup, nonempty reference
name, agreement with the declaration's own name, and the existing
`ScalarStatements.writable` permission. Member descent retains this root
premise; runtime storage or successful reads cannot manufacture permission.
Locals, out and inout are accepted; input and directionless parameters are
not. Each member uses the existing nominal `FieldsOf` relation, including
exact kind/declaration and unambiguous field names. Assignment requires
the target's exact scalar IR type and reuses the existing scalar expression
typing relation. Conditionals require a Boolean condition and both bodies;
body formation introduces no new execution semantics.

The relation deliberately does not establish runtime frame agreement,
absence of action overlays, global index validity or termination. The
forthcoming lowering/evaluation theorem must retain explicit concrete
frame and declaration premises; this increment does not replace them.
Aggregate whole-value assignment, stacks and packet operations remain
outside the statement fragment.

Kernel examples provide constructive nested local/out/inout witnesses and
reject input/directionless nested writes, absent and empty roots, wrong
nominal kind, and nine-bit assignment to an eight-bit field. These are
proofs about the specification relation, not merely API elaboration failures.
`Tests.Main` already imports this test module, so these examples are checked
by the ordinary spec test build. Independently imported the compiled test
module and queried all new constructor interfaces through Lean stdin:
exit 0. No candidate rebuild was performed.

Inspected the completed two-package log; implementer reports exit 0 with
392 runtime spec checks, all user tests/default audits, and a separate
43-test authored Python gate. No new operational theorem or axiom-audit
root is claimed for these inductive definitions. Requested only a module
overview update from read-only wording to include the new statement rules;
this is a documentation correction, not a semantic blocker.
