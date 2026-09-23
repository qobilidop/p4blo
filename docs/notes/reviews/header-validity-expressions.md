# Header-validity expression adapter review

Final review: clear; chronological investigation follows below. Combined
post-integration full gates remain the integrator's responsibility.

2026-09-23. Read-only review of
`/Users/qobilidop/my/work/p4blo-validity-expressions`. Deliberate source faults
are confined to the implementer's separate mutant worktree. Reviewer does not
modify or rebuild either implementation tree.

## Structural findings

The scalar/header read sum is an adapter to the existing single ExprWith and
CmdWith ASTs, denotations and lowerers. Read.get observes independent source
data and Read.expr delegates to existing concrete lowering. Read.evaluate
and Read.typed discharge their cases with the already checked scalar and
header root bridges. The resulting generic expression/command theorems are
not weakened to accept an arbitrary whole-command correctness callback.

Root well-formedness/declaration predicates and scalar path typing helpers
move verbatim into Fields to break the import cycle. HeaderFields then depends
only on Fields, and FieldExpressions can import HeaderFields. The spec still
has no dependency on the user package. No IR semantics or Python runtime
changes are part of this candidate.

Scalar Ref/Place types and update operations remain unchanged; HeaderRef has
no writable validity conversion. The new Expr/Cmd specialization uses Read,
with an expected-type scalar Ref coercion. This is intentional surface-source
compatibility, not a claim of definitional identity with the former Expr type.
The existing forwarding policy needs only Read.get added to its proof's
simplification list; its policy meaning and invalid-header behavior are not
changed. The public isValid constructor has direct denotation and lowering
equations rather than an unaudited wrapper convention.

## Observer and fixture inspection

The exporter emits twenty expression cases and four commands, covering all
four sibling validity combinations, direct/empty headers, mixed scalar mux
arithmetic, assignment RHS and branch conditions. Native witnesses discharge
actual declaration, Index and Frame agreement; negatives exclude a writable
validity target and Boolean/bitvector misuse.

The Python wrapper places its complete snapshot after the authored operation
and inside the callee. This placement is essential: input parameters are
copied into read-only callee values, so observing only the caller after return
would hide illicit read-side mutations. The observer includes every stored
source scalar, all header validity bits including the empty header, output
result/flag, answer, unrelated local and nonempty untouched packet suffix.
Hand-written answer tables are independent of exported syntax and denotation.

Differential comparison and complete input retention precede the independent
known-answer assertion. Permanent evaluator faults change either the actual
returned validity or a sibling stored byte while returning the correct Bool.
Each requires an exact single-request saved input, clean live divergence with
specific independently predicted packet bytes, and restored agreement. The
initial observer used the same isValid operand shape as the authored read;
the refinement described below now isolates those two paths explicitly.

Default audit/exporter guards and ordinary native driver registration are
present. No blocking structural finding. This checkpoint does not add named
header paths, validity writes, a validity-guarded forwarding policy, or a proof
of the Python observer/call-initialization scaffolding.

## Independent stable-candidate checks

- New focused Python profile: 27 passed, exit 0, including both actual
  evaluator monkeypatch faults with saved-input live/restored replay checks.
- Four existing authoring profiles: 56 passed, exit 0. An earlier invocation
  used a nonexistent command-suite filename and collected no tests; the
  corrected explicit statement-suite filename is the successful run above.
- Existing compiled userTests: exit 0, including all previous suites and
  twenty unified expression plus four command answers.
- Fresh pinned Lean query and HeaderReadExamples.run: exit 0. Read.typed and
  Read.evaluate have exactly the standard three axioms; the two isValid
  constructor equations depend on no axioms.
- Executed each of scalarExamples, scalarCommands, fieldExpressions and
  fieldCommands with clean stderr and exit 0, independently comparing raw
  stdout bytes to the implementer's pre-refactor captures. All four are
  identical. The captures' provenance is attributed to the implementer;
  this reviewer independently repeated the current-output comparison.

The complete two-package/495 required differential gates are attributed to
the implementer, not independent full-gate reruns. Deliberate source-edit
mutation evidence and final documentation remain to be inspected.

## Observer refinement and recheck

The implementer's adversarial follow-up identified that the initial scoped
fault also matched the observer's identical validity operation. Consequently,
even a weak pre-read snapshot could be corrupted during its own observation
and fail for the wrong reason. This review agreed that the experiment needed
to distinguish the authored read from observer reads.

The observer now applies isValid to an explicit identity header mux, while
the scoped fault matches only the authored member operand. This is local test
instrumentation, not a production normalization or altered adapter meaning.
All twenty-four independent answers pass with this representation.

A deliberately weak control moves the authored read after every snapshot.
Under the same side-effect fault it must have exactly one clean agreement,
an exact independent output packet and a hit counter proving the authored
read actually executed once. This reviewer requested the exact packet/hit
strengthening so mere agreement on dropped output could not qualify.
The strong observer then retains a genuine state-only mismatch: byte 2 loses
the sibling value, while the authored returned Bool remains correct. The
wrong-return fault changes only byte 11, the authored answer, not the
observer's validity byte. Complete input/live/restored assertions remain.

Independently reran the final strengthened focused suite: 27 passed, exit 0.
This closes the observer-order evidence gap. Persisted source-edit campaign
and final note review remain pending.

## Final reproducibility closure

Reviewed the completed `header-validity-expressions.md` note. It accurately
records all four faults, helper relocation and compatibility boundaries, the
observer refinement, expected exact bytes, source-edit/replay commands and
remaining initialization/application obligations. The wrong source leaf is
rejected by concrete exact-value and public constructor proofs. A correctly
typed wrong selected header builds the complete default audit, then fails
the independent answer after both engines agree. Neither result is falsely
described as a runtime Lean/Python discrepancy.

Inspected final actual Python source-edit logs: both tests save a mismatch;
live replay has one divergence and no errors. Wrong-return changes only the
authored answer byte 11; the side effect changes only sibling byte 2 from 57
to 0, with unchanged returned Bool. The actual-source weak-control log has
one agreement. The permanent regression independently validates the stronger
fault-hit and expected-packet conditions as recorded above. Both restored
source-edit replays agree.

Independently loaded all three retained copies (candidate, final-return and
final-side-effect), required exactly the current exported `first-01` program,
one empty-entry request at port 0 with `deadbeef`, port count 4 and seed 0.
All are 25,694 bytes and share SHA256
`5ba522ddbc969b88b33f836a98c52bbb993fa7400fc16997ab1d4fbb821bfed3`.
Each replay against the restored candidate binary exits successfully with
one agreement and no protocol/both-error outcome. These are the same input,
not three distinct witnesses; active source edits determine the two faults.

Compared restored mutant FieldExpressions and HeaderReadExamples directly
with the candidate: both `cmp` checks pass. Actual Python expr.py has no
surviving diff. Independently ran both headerReads exporters: clean exit and
stderr, exactly identical 6,008 output bytes. Restored complete-package and
native gate logs also report success; those builds are attributed evidence.
Candidate whitespace check passes.

No remaining correction requested. The code, permanent observer controls and
final evidence are clear for the scoped core/test commits. The parent will
run combined full gates after integrating current main; this report does not
claim those future results.
