# Header validity in the existing expression and command language

2026-09-23. Checkpoint 2 of `header-validity-plan.md`, based on `5d12252`.
Checkpoint 1's read-only HeaderPath/HeaderRef and scalar write restrictions
remain intact. This adds no validity writes, named header resolver, guarded
forwarding application, interpreter behavior, wire syntax or parser proof.

## One read interface; one language

`Fields.Read roots t` has two leaves: an existing scalar `Ref roots t`, or a
read-only `HeaderRef roots` producing Bool validity. Its independent `get` and
IR `expr` dispatch to the previously proved concrete observations; they do
not copy expression operators or evaluate lowered syntax for source meaning.
Concrete `Read.typed` and `Read.evaluate` discharge declaration/index/frame
obligations, including exact returned values and the entire unchanged Run.
Their default-audited axiom sets are the existing aggregate foundations,
`[propext, Classical.choice, Quot.sound]`.

Fields.Expr and Fields.Cmd now specialize the same `ExprWith` and `CmdWith`
to this read sum. Place, Ref, writable root modes, scalar assignments and
all validity-preservation laws are unchanged. Generic expression/command
proofs are reused with the concrete Read law, including arbitrary execution
continuations, unrelated Run state, root permissions and target-name bounds.
There is no arbitrary whole-expression/command correctness callback in the
public concrete results and no second source interpreter.

The one-way scalar Ref-to-Read coercion preserves existing `.read ref` and
`Place.read` call sites. `HeaderRef.isValid` is an ordinary smart constructor.
Two axiom-free audited equations pin its independent source observation and
actual lowered expression to the selected HeaderRef; correctness cannot be
obtained by silently replacing that helper with an unrelated constant.
HeaderRefs/validity leaves cannot become writable scalar Places.

To remove the import cycle, existing root well-formedness/declaration predicates
and scalar path typing lemmas moved unchanged from FieldExpressions to Fields.
HeaderFields now imports Fields; FieldExpressions imports HeaderFields. This
places primitive typing alongside primitive values/paths and leaves the
operator adapter above both. Public primitive names and theorem statements
are preserved. Confidence: high in this boundary, medium in long-term module
size and expected-type coercion ergonomics. Revisit when another aggregate
read or endpoint operation creates substantial duplication; do not introduce
a parallel AST to avoid a local import or inference issue.

The old ForwardPolicy theorem, its independent policy and intentional rewrite
of invalid stored headers remain unchanged. Only `Read.get` was added to its
explicit normalization list. Internal Fields.Expr/Cmd read-parameter types
are generalized, not claimed definitionally identical to `ExprWith (Ref roots)`.

## Legacy compatibility and new examples

A clean pinned build at the committed base preceded every production edit;
no stale `.lake` tree was copied. All four legacy exporter outputs were
captured as raw JSONL and compare byte-for-byte after the refactor. No old
case was removed, renamed or reinterpreted. Captures are under ignored
`.artifacts/validity-baseline/`, reproducible by building `5d12252`:

| Exporter | SHA-256 |
| --- | --- |
| scalarExamples | `2ebec90bffc7fc55b3ad82917907d8c0cf14df7eac655b53d3e5d5759c0c54b4` |
| scalarCommands | `917a2ee192aed09e622eb008995526868f09df8e08d5fba4b5766e8c43e5e8c0` |
| fieldExpressions | `7a6bb52d71df8381ebc3cb4f26456650670f82d0e239e1f0cfb439582850d8c3` |
| fieldCommands | `be4beb58c42f1b17e1bcb9e5744ccd3bd5ad945ed64f63a5571574ab0c195280` |

A separate default `headerReads` exporter emits syntax and checked fixture
inputs only, never computed expected answers. Twenty expression cases cover
all four nested validity pairs, direct and empty headers, and mixed scalar/
validity mux expressions. Four finite commands use validity in both a Boolean
assignment RHS and a conditional, preserving all read-only header data. They
are not a new forwarding-policy implementation. Three negative constructions
check read-only separation, Bool/bitvector mismatch and assignment type.
Constructive Index/declaration/frame witnesses instantiate both concrete
expression and command correctness with nontrivial packet/emitter/visit state.

`test_lean_edsl_header_reads.py` independently pins all 24 case identifiers,
input Bools, result types and output bytes. Packet/direct/empty really are
input-only parameters in the test subcontrol; result/flag are out parameters.
The wrapper evaluates the authored expression/body once and then snapshots
every source field, all four validities, scalar outputs, an unrelated sentinel
and untouched `deadbeef` payload **inside the callee before returning**.
Otherwise copy-in isolation could conceal a mutation to an input parameter.
Caller construction, copy-in/out, result casts, observer and architecture
remain tested scaffolding, not proved initialization or whole-program claims.

The observer applies isValid to an identity header mux, while authored reads
use the actual selected member operand. This is explicit test-only scaffolding
which leaves the stored observation unchanged; it lets the scoped faults below
target the authored read without corrupting the observer a second time. It is
not a production normalization or an adapter repairing interpreter outputs.
An intentionally weaker observer runs the authored read after every snapshot.
Under the same side-effect fault it agrees with the exact expected packet;
a hit counter proves the faulty read actually executed. The correct observer
instead detects the changed sibling byte while the returned Bool is unchanged.

## Gates and review

- Both complete Lean package gates/default audits/user suites: exit 0.
- New focused suite: 27 passed, including two saved/live/restored evaluator
  regression tests and the weak-observer survival control.
- Required all-suite Lean/Python DRT: 495 passed, 1385 deselected, no skips.
- New Python formatting, lint and type checks: exit 0; diff whitespace clean.
- Independent read-only review: clear. Separate execution/audit checks passed;
  the reviewer matched all three final bundle copies to tracked source inputs,
  replayed restored agreement and verified source/export restoration. Report:
  `reviews/header-validity-expressions.md`.

Merged full-repository gates remain the integrator's responsibility. Existing
independent policy and legacy conformance claims are retained; these tests do
not prove universal Python equivalence or application intent.

## Four isolated faults

The detached tree `/Users/qobilidop/my/work/p4blo-validity-expression-mutants`
is based on `5d12252` with candidate sources. It was built clean, without copied
caches. The normal candidate was never intentionally mutated. Apply each edit
alone and restore it before the next; commands below run in that tree's pinned
Nix environment (Lake commands from its `lean/`, Python commands from its root).

1. **Wrong unified source leaf.** Change Read.get's
   `| .headerValid ref, store => ref.get store` to return `!ref.get store`.
   Building `P4blo.FieldExpressions` exits 1 at the actual concrete evaluate
   equality and the smart-constructor denotation equation. This is a genuine
   false Boolean result, not a constructor-shape error or runtime DRT kill.
2. **Valid wrong source header.** Change HeaderReadExamples.first from
   `.mk .here (.field .here .here)` to
   `.mk .here (.field (.there .here) .here)`. Default build and proof audits
   pass. The `first-01` conformance test exits 1 at the independent expected
   packet assertion **after the engines agree**; answer byte 11 becomes 1
   instead of 0. Generic correspondence proves faithful execution, not the
   caller's intended header. The independent source runtime answer also fails.
3. **Actual Python wrong return.** Replace the production `case "is_valid"`
   equation in `python/p4blo/interp/expr.py` with:

   ```python
   header = expect_header(evaluate(expr.is_valid.header, env))
   if env.block.name == "HeaderReadBody" and expr.is_valid.header == pb.Expr(
       member=pb.Member(base=pb.Expr(var="packet"), field="first")
   ):
       return not header.valid
   return header.valid
   ```

   The scoped fault changes only the authored read; the observer's identity
   mux does not match that operand. Selected test exits 1, saves the complete
   program/request before any independent-answer assertion, and live replay
   exits 1 with one divergence and no errors. Only answer byte 11 differs.
4. **Actual Python read-side effect.** Use the same guard, replacing its
   `return not header.valid` with:

   ```python
   sibling = expect_header(evaluate(pb.Expr(
       member=pb.Member(base=pb.Expr(var="packet"), field="second")
   ), env))
   sibling.fields[0] = Bits(8, 0)
   ```

   Keep the final `return header.valid`. The weak pre-read observer survives
   (one agreement, exact original packet) although the read runs. The normal
   test saves a mismatch; live replay exits 1 and changes only sibling byte 2,
   from 57 to 0. The selected Bool/answer stays false/0. Source fields still
   exist when invalid, so this is not masked by header emission behavior.

Run either actual Python fault with:

```sh
P4BLO_REQUIRE_LEAN=1 P4BLO_DRT_FAILURE_DIR=.artifacts/drt/final-fault nix develop -c uv run pytest 'tests/test_lean_edsl_header_reads.py::test_lean_agrees_on_authored_header_reads[first-01]'
nix develop -c uv run python -m p4blo.drt.replay .artifacts/drt/final-fault/lean-header-reads-first-01.json --lean ir/.lake/build/bin/p4blo-lean
```

The exported input is validated by the tracked `exported_programs` helper.
Both faults have the same complete input bundle: first-01, empty entries,
ingress port 0, payload deadbeef, port count 4 and seed 0. Retained final copies
are under mutant `.artifacts/drt/final-return/` and `final-side-effect/`, plus
candidate `.artifacts/drt/lean-header-reads-first-01.json`. All have SHA-256
`5ba522ddbc969b88b33f836a98c52bbb993fa7400fc16997ab1d4fbb821bfed3`.
The observer-refinement investigation's earlier bundles are superseded, not
additional distinct final witnesses.

Expected restored bytes: `ab0039011234cc0101000000a5deadbeef`.
Wrong-return bytes: `ab0039011234cc0101000001a5deadbeef`.
Side-effect bytes: `ab0000011234cc0101000000a5deadbeef`.

The weaker-control recipe reuses tracked helpers: load `first-01` with
`exported_programs(Path("lean/.lake/build/bin/headerReads"))`, transform it
with `pre_read_observer`, and compare the same single Case/port count against
the real Lean binary while the side-effect fault is active. The permanent
regression additionally checks one actual fault hit and the exact expected
weak packet, then saves/replays the strong mismatch and restores the evaluator.

Restore actual expr.py and both Lean edits exactly. Both saved final bundles
then replay with one agreement/no divergence/errors (exit 0). Rebuild both
Lean packages and user tests before declaring the isolated tree restored;
compare its FieldExpressions/HeaderReadExamples and headerReads output against
the candidate. Those restored builds/tests and byte comparisons all passed;
the restored isolated focused suite also passed all 27 cases. Session logs use `/tmp/p4blo-validity-mutant-` with
`read-leaf.log`, `final-alias-{build,test}.log`,
`final-{return,side-effect}-{test,live,restored}.log`,
`final-weak-control.log`, and `final-restored-build.log`.
Exact source recipes and outcomes here are the durable evidence.
