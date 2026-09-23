# Scalar construction assurance

The historical closed-scalar increment below is followed by the contextual
increment at the end of this file; its expanded claims supersede the older
"Next boundary" section without rewriting the earlier experiment record.

Implementation increment: 2026-09-23. This file records the exact boundary
and experiments for the first user-facing Lean eDSL, independently of the
larger whole-program roadmap.

## Decisions

- Reuse `ScalarTyping.ScalarTy` as the construction-language index, with
  positive width and fitting-value evidence in each literal constructor.
  Composite constructors enforce operand compatibility intrinsically.
  Confidence: high for this closed fragment. Revisit when typed variables
  and aggregate references require a richer source type/context relation.
- Give source terms a separate `Fin (2 ^ width)`/`Bool` denotation. Modular
  addition uses natural arithmetic, equality compares finite values, and
  mux selects the indicated source branch. Only `toValue` relates this to
  the IR's values. Confidence: high; never replace source meaning with
  `evaluate (lower e)`, which would make compiler correctness circular.
- Use ordinary typed constructors and a small scoped notation layer,
  rather than inventing a new statement parser at this stage. `bits[w, n]`
  invokes a checked literal constructor, `+` constructs addition and `===`
  constructs bit equality. Confidence: medium on syntax. Revisit with the
  first packet/stateful examples; ergonomic changes must retain independent
  authored-syntax known answers rather than only testing lower-level ASTs.
- Prove exact computation equality first, then derive arbitrary-Run
  preservation. Reuse reference execution; no second optimized interpreter
  is justified by this increment. Confidence: high. A distinct execution
  representation requires a separately stated refinement theorem.
- Export source-built expressions into Python's existing valid scalar
  packet context. This keeps the tested boundary narrow while exercising
  both implementations and the JSON/protobuf interface. Confidence: high
  for scalar conformance, explicitly insufficient for complete-program
  authoring or verified serialization.

## Claims and exclusions

`lower_typed` proves membership in the specification's closed scalar typing
relation. `evaluate_lower` proves successful evaluation returns exactly the
source value. `evaluate_lower_run` additionally exposes equality of the
entire initial and final `Run`, for every Run, not just well-formed ones.

These theorems cover expressions built by `Scalar.Expr`, including all
literal widths and arbitrarily nested supported operations. They do not
cover whole-program validity, variables/frames, statements, eDSL syntax
elaboration, JSON/protobuf codecs, the Lean compiler/runtime, or Python
equivalence. Known answers and cross-language tests address some of those
boundaries empirically; they are not a replacement theorem.

The default user-package axiom audit guards all three advertised theorems.
Its expected standard foundations are reviewed separately from whether
the theorem statements express the intended behavior.

## Tests

- Six compile-time rejection tests: zero width, overflowing literal,
  addition width mismatch, equality width mismatch, non-boolean mux
  condition, and mux branch width mismatch.
- Dynamic checked-literal acceptance/rejection at positive-width bounds.
- Thirteen independently expected source and lowered known answers:
  zero, maximum, ordinary addition, 8-bit wraparound, 1-bit wraparound,
  65-bit wraparound, equal/unequal values, both bit mux arms, both boolean
  mux arms, and nested addition/equality/selection.
- The Python test independently specifies each width and emitted packet;
  it consumes exported syntax, not exported expected results, validates
  the enclosing program, runs production Python, and compares production
  Python with the reference Lean interpreter. Export count, uniqueness
  and name coverage are checked so missing fixtures cannot silently pass.
- Differential failures retain complete replay bundles under
  `P4BLO_DRT_FAILURE_DIR` (default `.artifacts/drt`).
- A non-Lean-dependent layout test guards the proof audit and example
  exporter's membership in Lake's default targets. Cached outputs must
  not hide accidental removal of either build gate.

## Adversarial experiments

All three experiments ran on 2026-09-23 in the isolated
`p4blo-lean-scalars` worktree, based on committed interface `4b64497`.
All faults were restored with explicit inverse patches before the final
gates. No mutation was committed. These are selected experiments, not an
exhaustive mutation score.

1. **Lower addition as subtraction.** Changed `lower`'s `.add` case from
   `.binary .add` to `.binary .sub`. Also changed that case's typing proof
   to `.binary .sub`, so type preservation still held and could not be
   credited with catching the semantic error. The user-package build
   exited **1** in `evaluate_lower`'s `add` case: the remaining goal equated
   `(x + 2^width - y) % 2^width` with `(x + y) % 2^width` for arbitrary
   operands. This is **proof/build rejection**, not a runtime DRT kill.
2. **Reverse lowered mux arms.** Changed the lowerer to
   `.mux (lower condition) (lower no) (lower yes)` and changed its typing
   derivation to `.mux hc hr hl`. The build exited **1** in
   `evaluate_lower`'s `mux.false` and `mux.true` cases, requiring arbitrary
   source branch values to be equal. Again **proof/build rejection**,
   not a runtime mismatch.
3. **Make authored `+` discard its right operand.** Replaced
   `instance : Add (Expr (.bits width)) := ⟨Expr.add⟩` with
   `⟨fun left _ => left⟩`. The complete user-package default build exited
   **0**, including all three proof audits and the source fixture exporter:
   the typed core compiler still correctly compiled the wrong expression
   chosen by the surface instance. `lake test` then exited **1** with
   `source known answer failed: add`. Independently, required pytest
   `test_lean_agrees_on_authored_scalar_known_answers[add]` exited **1**:
   production Python emitted `13` hex instead of expected `1a` for authored
   `19 + 7`. This is a **compiled semantic known-answer kill**. Agreement
   between two interpreters on the same incorrectly authored IR would not
   have been sufficient; the independent expected result is essential.

The build command for each mutant was `nix develop -c lake
+leanprover/lean4:v4.34.0 -d lean build` from the repository root. The
surface mutant's runtime check was `lake +leanprover/lean4:v4.34.0 test`
inside the user package's Nix environment, followed by
`P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest
'tests/test_lean_edsl.py::test_lean_agrees_on_authored_scalar_known_answers[add]'
-q`. These commands distinguish a compiler/proof failure from tests that
actually execute changed behavior. Apply the exact edits above one at a
time in an isolated worktree to reproduce them.

## Next boundary

Typed references under an explicit frame relation, followed by assignment
and sequence preservation. A scalar `Typed` derivation is not sufficient
to certify a block, and an unverified raw-program wrapper must not be
marketed as a verified whole-program compiler.

## Completed gates

After restoring all mutants on 2026-09-23:

- `scripts/check-lean.sh` exited 0: both packages built, both axiom audits
  passed, 288 specification checks passed, and the new 13 source/lowered
  known answers plus six negative elaboration checks passed alongside the
  existing user-library API smoke checks.
- Required `pytest tests -k lean_agrees -q` exited 0: **108 passed**,
  911 deselected, no skips.
- `scripts/check.sh` exited 0: **1018 passed, one expected BMv2 divergence,
  no skips**, plus formatting, lint, typechecking, protobuf/schema and
  workflow checks. This includes both external oracle suites.
- Independent review requested a final default-target regression guard.
  After adding that test, required `pytest tests/test_lean_edsl.py -q`
  exited 0: **14 passed**, with ruff check/format and pyright passing.
  The full suite above preceded this one-test hardening addition; no
  implementation or fixture changed after that full gate.

No unavailable gate is being counted as passed. The macOS linker emitted
the existing SDK-version warnings; Lean proof/linter warnings remain errors.

## Contextual increment: typed references and exact frames

Implemented 2026-09-23 against `7942768`, before statement authoring. The
specification now has one `TypedIn context` relation and one recursive scalar
checker, with the previous `Typed`, `check`, `infer` interfaces specializing
the empty context. `inferIn` validates the entire finite context (unique,
nonempty names and positive bit widths), including unused declarations.
`checkIn_typed` exposes well-formedness and typing, `checkIn_complete` proves
completeness under well-formedness, and `checkIn_sound` proves successful
same-Run evaluation under the actual runtime `FrameTyped` assumption.
Completeness is only for this scalar relation, not for all valid IR programs.

The user language similarly has one `ExprIn context` AST, with `Expr` as its
closed alias. Positional `Ref` membership and heterogeneous `Env` values
make source variable reads independent of string lookup and IR runtime
values. `lower_typed_in` proves contextual typing under context validity.
`evaluate_lower_in` proves **exact source value and the entire unchanged
Run** under `FrameMatches`; this relation calls the real action-first
`Frame.read?`, not a newly invented lookup. `Env.frame_matches` constructs
a witness for every well-formed context/environment, and
`FrameMatches.typed` supplies the specification's typed-frame premise.

Declaration agreement is a separate `Declares` predicate. Neither the
constructed witness nor exact value agreement certifies a valid block,
action, declaration scope, writable parameter, or whole program. No separate
optimized interpreter or verified serialization is claimed. Assignments,
statement sequencing, aggregate references and statement validity remain
future increments.

### Decisions and revisit triggers

- Finite lists with decidable whole-context validity, not an unchecked
  function environment. Confidence: high for this fragment; revisit when
  aggregate bindings and nested source scopes require richer contexts.
- One AST with a closed specialization avoids duplicated semantics.
  Typed named accessors currently bind positional references once; literal
  notation infers its context from the surrounding expected type. The
  explicit `bits` helper remains closed. Confidence: medium on ergonomics;
  revisit with the first useful statement program and preserve known-answer
  tests around any new binding/notation elaborator.
- Value agreement and declaration agreement remain separate. Confidence:
  high. The next statement increment must add declaration/writability
  obligations and must not treat `Env.frame` as a validated program frame.
- The original `lower_typed` audit now uses `[propext, Quot.sound]` rather
  than `[propext]`, because it specializes the generalized context proof
  through list uniqueness/membership. All other new audit roots use only
  the recorded standard foundations; exact axiom lists remain default gates.
  Confidence: high; theorem statement review is still required in addition
  to checking absence of untrusted axioms.

### Additional coverage

- Nine contextual checker tests: valid read/composition; missing binding;
  width/kind mismatch; and invalid unused empty-name, zero-width, duplicate
  same-type and duplicate different-type contexts.
- Nine negative elaboration tests in total, now with explicit expected
  types so an uninferred context cannot masquerade as a width/type rejection.
  The three additions reject a wrong-width reference, a reference into an
  empty context, and a nonboolean variable used as a mux condition.
- Kernel-checked frame witness, rejected missing/wrong-width frames, and
  action shadowing: the block environment no longer matches a frame whose
  action layer overrides its value, while the corresponding action value
  does match. Runtime tests independently expect the shadowed value 42.
- Eight independently expected variable examples (21 total): both reads,
  addition, wrapping addition, both mux arms, equal and unequal references.
  Python checks exact exported ID/width/input-binding coverage and values,
  assembles ordinary validated scalar packet programs, then checks expected
  bytes and cross-language agreement. The exporter supplies syntax and
  input values only, never source-computed expected outputs.

### Contextual adversarial experiments

Experiments run in detached worktree `p4blo-frame-mutants` at `7942768`
with the candidate patch applied. This is separate from the implementation
worktree. Each fault is applied alone and restored with an inverse patch.

1. **Wrong lowered variable name.** Replace `lower`'s `.read ref` case
   `.var ref.name` with `.var (ref.name ++ "wrong")`. The default user build
   exits 1 in both `lower_typed_in` and `evaluate_lower_in`: lookup/typing
   cannot establish the new name, and exact evaluation cannot use the
   original frame agreement. This is proof/build rejection, not a runtime
   inconsistency detected by differential testing.
2. **Same-width wrong source accessor.** Change `ScalarExamples.x` from
   `.read .here` to `.read (.there .here)`. Default build, proof audits and
   exporter all succeed. `lake test` exits 1 with `open source known answer
   failed: read-x`; independently the required Python test for `read-x`
   exits 1 with output `07` instead of `13`. This is a compiled semantic
   known-answer kill even though the core lowering theorem still holds.

3. **Swap input bindings without changing the source expression.** Change
   `ScalarExamples.values a b c` to construct `.cons b (.cons a ...)`.
   Default user build and proof audits succeed. Required pytest for
   `read-add` exits 1 in the shared fixture with `unexpected initial
   bindings: read-x`: the exporter supplies x=7/y=19 where the independent
   input contract specifies x=19/y=7. This is a compiled fixture-contract
   kill, before interpreter execution, not a DRT result or a proof failure.
   In particular, commutative addition alone cannot detect swapped inputs.
4. **Wrong production Python read.** Insert `name = "y" if name == "x"
   else name` at the start of `interp.env.Env.read`. No Lean source or
   exported input changes. The required `read-x` known-answer test exits 1
   (`07` versus `13`). Calling `compare_program` directly on that same
   exported program, empty packet and four ports independently reports
   **one divergence, zero agreed, zero shared errors**: Python outputs `07`,
   Lean outputs `13`, with no error or state differences. This is an actual
   production Lean–Python differential kill, not just a build or oracle
   fixture failure.

To reproduce, apply one exact edit above to this increment in an isolated
worktree. Build both packages with `scripts/check-lean.sh` before mutation;
for Lean mutations run `lake +leanprover/lean4:v4.34.0 -d lean build` from
the root in Nix. Then run `lake test` in `lean/` for the source known answers
or required `pytest 'tests/test_lean_edsl.py::test_lean_agrees_on_authored_scalar_known_answers[read-x]' -q`
(substitute `read-add` for experiment 3). The direct differential check in
experiment 4 uses the fixture's validated `read-x` program,
`Case(pb.Entries(), 0, b"")`, four ports and `ir/.lake/build/bin/p4blo-lean`;
it bypasses the preceding independent expected-output assertion solely to
demonstrate differential detection. Restore each edit before the next.

The exact reconstruction/save command for experiment 4 is below. Run from
the isolated worktree with the Python read mutation active (adjust the
absolute worktree path when reproducing). The tracked pytest fixture is
called through `__wrapped__` solely to reuse its independent input checks
and packet-program assembly, without invoking its expected-output assertion.

```sh
mkdir -p /Users/qobilidop/my/work/p4blo-frame-mutants/.artifacts/drt
nix develop -c uv run python - <<'PY'
import runpy
from pathlib import Path
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import compare_program
from p4blo.v0 import p4blo_pb2 as pb

root = Path('/Users/qobilidop/my/work/p4blo-frame-mutants')
binary = root / 'ir/.lake/build/bin/p4blo-lean'
fixture = runpy.run_path(str(root / 'tests/test_lean_edsl.py'))['authored_expressions']
program = fixture.__wrapped__(binary)['read-x']
report = compare_program(program, [Case(pb.Entries(), 0, b'')], 4, [binary])
path = root / '.artifacts/drt/typed-frame-read-x.json'
save(report, path)
print(report.summary())
assert not report.passed and len(report.divergences) == 1
PY
nix develop -c uv run python -m p4blo.drt.replay \
  /Users/qobilidop/my/work/p4blo-frame-mutants/.artifacts/drt/typed-frame-read-x.json \
  --lean /Users/qobilidop/my/work/p4blo-frame-mutants/ir/.lake/build/bin/p4blo-lean
```

Observed reconstruction exits 0 (the assertion expects a mismatch). Replay
with the mutant active exits **1**: one divergence, Python port 0 `07`, Lean
port 0 `13`. Remove the one-line mutation and rerun the **same saved bundle**
without rebuilding either Lean executable: replay exits **0**, one agreed,
zero diverged, zero shared errors. The bundle includes the concrete program,
ports, seed and request, so replay does not invoke the exporter or fixture.
Its SHA-256 is
`38451c94a44d22dabafb456feb3b2cc7967ec5d0107106f58caa05a04e2a1615`.
The bundle is an ignored experiment artifact; the complete reconstruction
above is tracked here so later sessions do not depend on a temporary file.

### Contextual completed gates

On the unmutated candidate, 2026-09-23:

- `scripts/check-lean.sh`: exit 0; both packages, exact axiom audits,
  specification tests, 21 source/lowered known answers, nine negative
  elaboration tests, frame-premise kernel tests and API smoke tests pass.
- Required `pytest tests/test_lean_edsl.py -q`: **22 passed**.
- Required `pytest tests -k lean_agrees -q`: **122 passed**, 959 deselected,
  no skips. Binaries were built before these tests, not concurrently.
- `scripts/check.sh`: exit 0; **1078 passed, 3 expected divergences**,
  no skips, plus formatting/lint/type/schema/workflow checks.
- Independent read-only reviewer reexecuted the 22 focused tests, reviewed
  theorem statements and actual axiom roots, and confirmed the added
  `Quot.sound` dependency traces through `Ref.lookup`/`List.mem_map`.

These counts are for this branch's base and increment; the integrator must
rerun merged-main gates because other reviewed work is progressing in parallel.
