# Typed named-path review

**Final review: clear; chronological investigation follows below.**

Initial structural review of `NamedFields.lean` and its independent tests in
`p4blo-named-paths`: **no blocker found**. Final registered gates, mutation
restoration and documentation are pending; no binary execution was performed
during this first inspection.

The resolver constructs existing Slot/Path/Ref/Place objects, not a second
source AST. Proof-carrying lookup checks the actual selected Slot name,
nonempty query and uniqueness across the whole visited layout before leaf
type matching. Thus duplicates with different types/kinds are rejected, not
silently disambiguated by the requested scalar type. Nested resolution
decreases the segment list and requires aggregate intermediates, an exact
scalar endpoint and positive bit width. Selected-path success intentionally
does not certify unvisited schema/index validity.

`Ref.segments` is computed structurally from real root/member slots. Public
soundness and expression/lvalue spelling results connect the resolver output
to the requested segments and actual lowered member chain. They do not
merely echo the input string. Place resolution uses the same selected Ref
and checks its real source root mode; input/directionless paths stay readable
but not writable. Concrete execution still requires independent actual
declaration/index/frame premises.

The checked constructors extract only a proven successful result. Their
default `decide +kernel` proof uses kernel reduction, not `native_decide`,
an axiom or unchecked cast. Dynamic callers receive explicit errors instead.
No macro/elaborator or implicit packet-state behavior is introduced.

Tests independently inspect lowered names and selected values for same-width
siblings; reordering unrelated schema slots preserves requested spelling and
value. Exact diagnostics cover empty/missing/ambiguous names, mixed-kind and
tail duplicates, scalar traversal, aggregate endpoints, type/width/zero-width
errors and read-only modes. Explicitly typed negative elaboration examples
avoid accidental rejection merely from missing type-context inference.
Positive local/out/inout paths and input reads are included, as is a deliberate
success through an otherwise invalid unvisited schema to pin the limited
scope. Final review will check registered audits and actual fault outcomes.

## Final registration, checks and mutation evidence

The root package exports NamedFields, the ordinary user driver imports/runs
its tests, and all six public soundness/spelling results are default-audited.
Independently ran the compiled user driver: exit 0 with all previous suites
and named tests passing. Independently imported the compiled test module,
executed its runtime checks and queried each of the six roots: exit 0 and
exactly `[propext]` for every result. The 17 diagnostic answers and 11
rejected constructors are kernel-checked tests; selected-value/reordering/
spelling checks also run natively. No reviewer rebuild was performed.

Inspected three actual isolated mutation outcomes:

- Selecting an existentially shape-correct wrong head instead of the named
  tail fails the naming certificate with `False` under `name ≠ query`.
  This is proof rejection, not a dependent-type accident or runtime kill.
- Changing missing-name diagnostics to ambiguity builds the resolver but
  fails independent exact-error kernel examples; successful-resolution
  soundness alone does not specify errors.
- A valid authored dst-to-src request change builds the tests and retains
  soundness audits but fails the compiled independent destination-value
  check. Correctly resolving the wrong requested intent is not prevented
  by naming soundness and is accurately reported as a known-answer kill.

Independently confirmed both restored source files are byte-identical to
the candidate; restored module/evaluation logs pass. The final note records
exact edits and reproducible commands without implying a Python/Lean runtime
divergence or inventing a DRT replay bundle for these experiments.

The implementer reports both complete Lean package/default-audit gates
passed, and the required DRT log has **405 passed, 1338 deselected**, no skips.
Those gates are attributed rather than rerun. This is a checked authoring
constructor improvement, not a whole-schema checker or resolver completeness
theorem. No remaining review finding; merged full gates remain root-owned.
