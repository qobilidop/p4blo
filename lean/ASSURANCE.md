# Scalar construction assurance

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
