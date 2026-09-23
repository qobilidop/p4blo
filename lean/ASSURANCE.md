# Scalar construction assurance

The historical closed-scalar increment below is followed by contextual and
command increments. Their expanded claims supersede older "next" boundaries
without rewriting the earlier experiment records.

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

## Command increment: finite writable scalar bodies

Implemented 2026-09-23 against `46893ff`. This extends the contextual slice
without replacing its Context, Ref, ExprIn or Env APIs. The independent
source command meaning is a total `Env -> Env` transformation using typed
`Env.set`. It never calls IR evaluation, lowering or statement execution.

### Exact boundary and decisions

- `Modes context` is a finite, context-indexed declaration-mode list:
  local or parameter direction. A `Place modes type` contains an existing
  typed reference and proof that its mode is writable. Permission policy
  comes from the spec's `ScalarStatements.writable`: local/out/inout only.
  Input and directionless parameters cannot form writable places.
  `Modes.Agrees` independently requires the actual scope to resolve every
  binding to its exact name/type/direction declaration. The runtime still
  does not enforce declaration permissions. Confidence: high on policy,
  medium on parallel mode metadata ergonomics. Revisit with typed fields,
  not by replacing the already verified expression AST prematurely.
- The authoritative `Typed`/`BodyTyped` statement relations live in the
  spec and reuse `ScalarTyping.TypedIn`. Their executable target check
  `canAssign` rejects malformed entire contexts, missing or mismatched
  names/types/declarations, and read-only targets. This is not a complete
  statement checker or whole-block validity judgment.
- The one command AST is a structured list: empty, write with a tail, and
  conditional with two bodies and a tail. Public assign/ite/seq combinators
  provide ordinary statement composition. `denote_seq` proves sequencing
  means executing the second transformation after the first; `lower_seq`
  proves it lowers to list append. This representation introduces no
  synthetic IR conditionals or alternate executor. Confidence: high on
  semantics, medium on syntax. Revisit when readable packet programs expose
  concrete authoring friction; keep independent expected-output tests.
- `Cmd.steps` constructs a finite prefix of the existing `Execution.step`
  with an arbitrary continuation left untouched. `Steps.execute` invokes
  the existing `Finishes.sound`, not fuel or a second recursive reference
  semantics. Confidence: high. A concrete continuation that raises a parser
  fault if run is a kernel-checked witness/test of the prefix boundary.
- `Cmd.execute_correct` requires context well-formedness, actual declaration
  agreement, exact initial value agreement, and an inactive action layer
  (`action = none`, `actionVars = none`). It proves lowered body typing,
  successful reference execution, exact final source values, typed-frame
  and declaration preservation, `ChangesOnlyVars`, and `PreservesOutside`.
  The former gives an exact Run equality with only frame.vars replaced;
  the latter preserves every runtime lookup outside the possible target
  set, including unrelated names absent from the source context. No stronger
  equality between independently rebuilt hash maps is needed. Confidence:
  high; action/block calls require separately proved layering/copyback.
- `Modes.scope_agrees` and `Modes.frame_matches` are constructive witnesses
  under well-formedness, not arbitrary uninhabited assumptions. The actual
  Index.build/Frame.forBlock path is also tested for locals and in/out/inout
  parameters, including real out/inout writes. These tests are not a general
  proof that the witness constructors build globally valid programs. For
  example, scope/program name collisions and directionless *block* parameter
  validity are outside this fragment. Confidence: high in this distinction;
  prove the full construction bridge before advertising program validity.

Header/metadata paths, aggregate assignments, loops, extern/packet operations,
calls, complete-program lowering, serialization correctness and universal
Python equivalence remain outside the claim. Typed scalar field paths are
next; complete arithmetic coverage is not a prerequisite for useful packets.

### Acceptance evidence

- Twelve specification permission tests include input/directionless
  rejection, out/inout/local acceptance, wrong RHS/declaration width,
  wrong declaration name, missing source/runtime declarations, and invalid
  unused or duplicate contexts. A kernel example rejects an input write
  in the actual syntax-directed statement relation.
- Four negative user elaboration checks reject input and directionless
  places, a boolean RHS for a bits place, and a bits conditional.
- Nine independent source and actual-executor answers cover
  `(255,7) -> (0,7,true)` and `(3,7) -> (4,11,false)`, a wrapping second
  update, zeros, both input-dependent branches, branch wrap, empty bodies
  and a boolean-only assignment. Every source binding is observed.
- Each runtime case starts with unrelated nonempty packet/cursor, emitter,
  register array, table-default, parser-visit, index and extra local state;
  those observations must remain unchanged. The universal unchanged-field
  and untouched-name theorems are stronger than this finite sample.
- The default `scalarCommands` exporter supplies only source-built syntax
  and inputs. Python independently checks fixture IDs and exact input
  fields/types/values, assembles validated packet wrappers, and exposes all
  final locals plus an unrelated sentinel as four bytes. The raw wrapper
  is explicitly outside the lowering proof. DRT failures are saved before
  the independent answer assertion, so a production fault retains replay.
- All advertised sequencing, permission, witness, update, finite-prefix
  and execute theorems have exact default axiom audits. `Env.get_set` and
  `Cmd.denote_seq` use no axioms; `Cmd.lower_seq` uses propext; the remaining
  audited roots use only propext, Classical.choice and Quot.sound.

### Statement adversarial campaign

All mutants run separately in detached worktree `p4blo-statement-mutants`
at `46893ff` with the candidate applied, never in the implementation tree.
Default baseline builds/audits/tests pass before mutation. The first four
experiments are **proof/build rejections**, not runtime DRT kills:

1. **Reverse source update ordering.** In `Cmd.denote`, replace
   `next.denote (env.set place.ref (denoteIn env value))` with
   `(next.denote env).set place.ref (denoteIn env value)`. The IR compiler
   and its typing proof are untouched. Default build exits 1 in
   `Cmd.denote_seq` and `Cmd.steps`: the source sequencing law and the
   exact final-frame result no longer match the executor.
2. **Write the wrong lowered target.** Change the `.write` lowering target
   from `.var place.ref.name` to `.var (place.ref.name ++ "wrong")`. Default
   build exits 1 in `Cmd.lower_typed` and the write case of `Cmd.steps`.
   The original permission evidence cannot justify that different name;
   the actual machine-step equality also fails.
3. **Omit a write.** Lower `.write _ _ next` as `next.lower`; change its
   typing proof case to `exact ih` and rename the now-unused `hd` premise
   `_hd`. Default build exits 1 specifically in the write case of `Cmd.steps`:
   the claimed assignment transition no longer exists. The adjusted typing
   proof accepts the smaller body, so no stale type derivation or unused
   variable warning is being counted as the detector.
4. **Invert an if.** Lower the conditional with `no.lower` before
   `yes.lower`; swap `hy`/`hn` in its typing derivation too. Default build
   exits 1 in `Cmd.steps`' branch transition equality. Typing still accepts
   both same-context branches, but the actual selected continuation differs.

5. **Wrong same-width source place.** Change `ScalarCommandExamples.x`
   from `⟨.here, rfl⟩` to `⟨.there .here, rfl⟩`. Default build and all proof
   audits pass. `lake test` exits 1 at `statement source known answer
   failed: update-wrap`. Required pytest for `update-dependent` first
   observes DRT agreement, then exits 1 at the independent expected answer:
   actual `031000a5`, expected `040b00a5`. This is a compiled frontend
   semantic kill; mutual interpreter agreement is insufficient here.
6. **Production Python skips writes to x.** In `interp.env.Env.write`'s
   existing-block-binding branch, replace `self.vars[name] = value` with
   `self.vars[name] = self.vars[name] if name == "x" else value`. This affects
   the wrapper's input initialization as well as its body; both are actual
   IR assignments whose execution must agree. Required pytest for
   `update-dependent` exits 1 at DRT before the independent answer assertion,
   automatically saving a complete bundle. Python emits `000701a5`; Lean
   emits `040b00a5`, with no faults, diagnostics or extern-state differences.
   Replaying that bundle while the mutant is live exits 1 (one divergence);
   restoring the single Python line and replaying the **same bundle** exits
   0 (one agreement), without rebuilding Lean.

Reproduce each proof/surface experiment by applying the exact single edit
(plus the specified typing-proof adjustments) in a separate worktree with
this increment, then running its default user build:
`nix develop -c lake +leanprover/lean4:v4.34.0 -d lean build`.
For experiment 5, run `lake test` inside `lean/` and the focused pytest below.
Restore every edit before the next experiment. No mutant is committed.

Experiment 6 uses the tracked test itself to reconstruct, compare and save
the exact program; no temporary reconstruction helper is required. Run from
the isolated worktree with its one-line Python mutation active:

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest \
  'tests/test_lean_edsl_statements.py::test_lean_agrees_on_authored_statement_known_answers[update-dependent]' -q
nix develop -c uv run python -m p4blo.drt.replay \
  /Users/qobilidop/my/work/p4blo-statement-mutants/.artifacts/drt/lean-statements-update-dependent.json \
  --lean /Users/qobilidop/my/work/p4blo-statement-mutants/ir/.lake/build/bin/p4blo-lean
```

Both commands exit 1 under the Python mutation. Remove the mutation and run
the identical replay command again: exit 0, one agreed, zero divergences or
shared errors. The saved request is empty packet, ingress port 0, empty table
entries, with four ports and seed 0. Adjust only the absolute worktree paths
when reproducing. Bundle SHA-256:
`1f806e5de1c788cc573182229b9a6b6a240226e77c49729728d22aedb77cf313`.
The ignored bundle contains concrete program/inputs and is replayable without
the source exporter. This tracked reconstruction recipe removes dependence
on its retention in a temporary worktree.

### Command completed gates

On the unmutated candidate:

- `scripts/check-lean.sh`: exit 0, both packages/default axiom audits, spec
  permission tests, all old expression tests, nine command/state cases,
  four command negative typing checks, real declaration initialization and
  writable-parameter execution, and the faulting-continuation check.
- Required `pytest tests/test_lean_edsl_statements.py -q`: **10 passed**.
- Required `pytest tests -k lean_agrees -q`: **184 passed**, 1011 deselected,
  no skips. The Python/schema full gate also exits 0: **1190 passed,
  5 expected discrepancies**, no skips, plus formatting/lint/type/schema
  and workflow checks.
- The root IR import/export was then added (no semantic body changed).
  Both Lean package gates reran successfully; combined required expression
  and statement pytest suites then passed **32 tests**. Documentation-only
  assurance changes followed. The full integration gate must be rerun on
  merged main, which includes independent parallel work absent from this base.

No proof/build rejection above is represented as an executable semantic
kill. These are selected adversarial experiments, not exhaustive mutation
adequacy or proof of universal Python correctness.

## Field foundation: exact primitive reconstruction

The first field increment is `P4bloIR.FieldLaws`, not yet an aggregate
authoring language. `Declared` requires the actual nominal declaration of
the expected header/struct kind, no opposite-kind declaration at that name,
an exactly ordered field list and nonempty unique names. It does not assert
global index consistency, field-value typing or program validity. Exact
runtime list length is a separate premise. This matters because `setField`
uses `List.set`, which silently leaves a short list unchanged.

`fieldOf_pack` and `setField_pack` expose the actual primitives. The public
`read_declared` and `update_declared` combine declaration agreement with
exact shape to prove successful selection/update, exact reconstructed
container (including nominal name and header validity), selected-value
readback, unchanged length and every other position unchanged. Each
computation leaves the entire arbitrary `Run` unchanged. The setter
**returns a rebuilt container**: these are not yet persistence proofs for
`writeLValue`, nested paths or commands. Invalid headers retain their stored
fields and their false validity bit, as the existing p4blo contract requires;
this is not a portability claim for undefined P4 observations.

The default spec audit checks all six public bridge roots with precisely
`[propext, Classical.choice, Quot.sound]`. Kernel examples construct header
and struct agreement witnesses and an exact invalid-header write. Runtime
tests independently expect unequal-width/unequal-value siblings, both header
validity states, metadata writes, actual `Index.build` declarations, missing
and wrong-kind declarations, cross-kind shadowing, key/name disagreement,
reordered fields, wrong widths, duplicate/empty names and short lists. Raw
short-list reads fail, while raw short-list setters remain no-ops; neither
is disguised as an admissible typed update.

### Primitive adversarial experiments

In an isolated worktree, apply each edit separately to `setField` in
`ir/P4bloIR/Eval.lean` and run, from its `ir/` directory:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.FieldLaws
```

1. Replace the header arm
   `.header t valid fields => pure (t, fields, fun fs => Value.header t valid fs)`
   with `.header t _valid fields => pure (t, fields, fun fs => Value.header t true fs)`.
   Build exits 1 at `setField_pack`, leaving the impossible generic goal
   `valid = true`.
2. Replace `fields.set i value` with `fields.set (i + 1) value`.
   Build exits 1 at both container-kind cases of `setField_pack`, requiring
   equality of the wrong-position and correct-position lists.
3. Replace `fields.set i value` with `List.replicate fields.length value`
   and rename the now-unused binder `i` to `_i` only inside `setField`.
   Build exits 1 at both cases of `setField_pack`, requiring the clobbered
   sibling list to equal the one-cell update. The failure is not an
   unused-variable warning.

All three are **proof/build rejection**, not executable semantic detection.
After each experiment the exact edit was reversed; the final restored module
build exits 0 and the production evaluator has no diff. Runtime Python
field mutations and full aggregate-state replay belong to the later concrete
authoring increment, not this foundation checkpoint.

### Primitive gates and next representation choice

Both Lean packages, default audits and tests pass `scripts/check-lean.sh`.
The required real-Lean `pytest tests -k lean_agrees -q` passes **242 tests**,
1196 deselected, no skips. No Python/schema source changes were made; Docker
builds/oracle runs were not repeated because the shared VM was capacity
constrained. Integration retains its own full gate. Independent review:
`docs/notes/reviews/field-primitives.md` (copied by the integrator).

Next, define independent finite aggregate schemas/values with stored header
validity and typed scalar-leaf paths, then factor only the existing
expression/command read/write seam. Keep one operator AST/denotation and one
command sequencing implementation, with old scalar APIs as specializations.
Confidence is high in the primitive obligations and medium in this planned
API factoring. Revisit if a realistic nested forwarding body requires
pervasive Lean inference annotations; do not replace concrete aggregate
correspondence with an unconstrained callback premise. Parser, tables,
checksum, deparser and whole-forwarder correctness remain separate.

## Aggregate source/store/path checkpoint

`P4blo.Fields` implements finite mutually indexed `Shape`/`Layout` and
`Data`/`Record`: scalar leaves reuse independent Fin/Bool meanings, header
data carries Bool validity, and structs carry Unit instead of a redundant
validity bit. A root `Store` is the same record representation. Positional
`Slot`s select fields/roots and recursive `Path`s terminate only at scalar
leaves. There is no new expression AST, arithmetic evaluator or command
interpreter. Generic integration into the existing Expr/Cmd read/write seam
is deliberately a later checkpoint.

Source `Record.get/set`, `Path.get/set` and `Ref.get/set` are total functions
over source data, independent of IR evaluation and lowering. Readback laws
are proved. `Path.validities_set` and `Ref.validities_set` preserve the list
of **all** stored header validity bits, not only the targeted header. Exact
conversion laws relate record selection/update to the primitive field laws.
`Path.evaluate` and `Path.readLValue` preserve the entire Run. The recursive
`Path.writeLValue` theorem reduces an actual nested write to one actual
root-container write; it does not assume a callback already asserting write
correctness. `Ref.write_matches` establishes successful actual frame update,
exact updated source-store agreement, unchanged non-value Run state, and
every unrelated root unchanged, under no active action layer.

### Independent premises and nonvacuity

- `LocallyWellFormed` checks positive scalar widths, each aggregate's
  nonempty unique fields/name and scalar-only header fields. It does not
  establish coherent reuse of nominal names across a schema tree. Applied
  to a root Layout it checks the root *shapes*, not root-name distinctness
  or nonemptiness.
- `IndexAgrees` recursively requires the real index to match each ordered
  nominal declaration with the correct kind. It does not itself impose
  positive widths or scalar-only headers. Theorems `nominal_fields_unique`
  and `nominal_kind_unique` show that one agreeing index cannot assign
  incompatible layouts or kinds to the same name.
- Exact `FrameMatches` is independent of declarations/permissions.
  `Record.frame_matches` constructs a witness under distinct root names;
  `Ref.write_matches` additionally requires those distinct names and no
  action layer. Nonempty root names, write modes and real variable
  declarations belong to the next authoring boundary, not these operational
  primitive laws. The laws describe exact computation even for source
  shapes outside the locally well-formed fragment.

Kernel examples instantiate an actual mixed nested header/struct/metadata
Index and source store, prove exact frame agreement even with an unrelated
aggregate present, and apply both the complete read theorem and the complete
write-preservation theorem. Repeated use of the same nominal H type at two
roots is accepted. Two different same-kind H declarations are each locally
well formed, but a universal negative example proves that **no index** can
agree with both. Another universally rejects a header/struct H clash.
These are scoped consistency witnesses, not a general validated-program or
`Index.build`/`Frame.forBlock` correctness theorem.

Independent runtime answers include unequal-width/unequal-value siblings,
metadata and nested headers, both validity states, full stored aggregate
values (including invalid headers), an unrelated aggregate root, packet
cursor, emitter and parser bookkeeping. Three kernel shape negatives reject
zero-width leaves, aggregate-valued header fields and duplicate field names;
three failed elaborations reject a wrong-width reference, a scalar value
at aggregate type and a nonexistent/wrong-typed field slot.

### Aggregate-path adversarial checks and gates

Two isolated mutations exercise different boundaries:

1. In `Path.expr`, replace `.member base slot.name` by
   `.member base (slot.name ++ "wrong")`. Building `P4blo.Fields` exits 1
   at `Path.evaluate`: the actual field read with the altered name cannot
   use the exact source selection theorem. This is proof rejection only.
2. In `FieldTests.lean`, replace the definition of the nine-bit `port`
   reference with the also-nine-bit `right` reference. The default user
   build and all audits pass. `lake test` exits 1 at the independently
   expected full source aggregate update: the header field becomes 19
   instead of 511 and metadata remains 3 instead of 19. This is a compiled
   valid-but-unintended source accessor, caught by a runtime known answer,
   not by generic correctness proofs. Restoring the accessor restores the
   default build and all user tests.

The unmutated `scripts/check-lean.sh` passes both packages/audits, all 392
spec checks and all old/new user tests. Required legacy authored-expression
and command conformance suites pass **34 tests**, no skips. There is no new
Python-facing aggregate exporter in this checkpoint and no new claim of
aggregate Python differential coverage; full aggregate-state DRT and actual
Python setter faults with saved live/restored replays remain required for
the field-command integration. No Docker build or oracle rerun was needed.
Independent review: `docs/notes/reviews/aggregate-paths.md` (integrator copy).

Representation confidence is medium: custom finite Layout and positional
Slot keep dependent proofs small and reuse one Record for nested/root
storage. Revisit if ergonomic concrete forwarding bodies require pervasive
type annotations. Do not retain duplicate scalar Expr/Cmd implementations
as an expedient; factor their read/write seam once and retain the current
scalar API as a specialization.

## Field expressions: one shared read/operator implementation

`Scalar.ExprWith Reads` now owns the only operator AST, `denoteWith` and
`lowerWith`. Existing `ExprIn`, closed `Expr`, named constructors, literal
helpers and theorem signatures remain scalar-reference specializations;
the old scalar commands and all old examples are unchanged. `Fields.Expr`
specializes the same implementation to aggregate references. The generic
`evaluate_lower_with` proof requires only a per-leaf read law; the public
field `evaluate_lower` discharges it with actual `Ref.evaluate`, so its
statement has only concrete Index/frame premises and preserves the exact
value and entire Run. Source operators are still independent Fin/Bool
functions, not calls to the IR evaluator.

The spec's `FieldTyping` gives declarative variable/member path and scalar
operator rules. Paths require actual block VarDecl lookup, matching root
name and nominal kind/ordered field declarations. Scalar reads additionally
require a valid positive-width/bool scalar type. The source `lower_typed`
theorem uses `RootWellFormed`, recursive `IndexAgrees` and `RootDeclares`;
each premise has a concrete kernel witness. Six independent spec kernel
negatives reject absent/empty roots, missing declarations, scalar containers,
zero-width literals and overflowing literals. This is **not** a total
aggregate checker, general validity/soundness theorem or action-scope
declaration theorem. Writable field commands remain the next step.

### Full stored-state observation, and a reviewed gap

The default `fieldExpressions` executable exports seven authored expressions
with case IDs, result widths and initial header validity. Fixed numeric
inputs and expected answers are independently written in Lean tests and
`tests/test_lean_edsl_fields.py`; the exporter emits no computed answer.
The Python wrapper builds an ordinary validated program with a nested header
root and metadata root. Its valid observer header reports every stored
source field, stored header validity, an unrelated sentinel and the result.
Nine-bit fields/results are zero-extended to sixteen bits; bools are cast
through one bit to a byte. It observes invalid-header storage explicitly,
not by trying to emit the invalid header.

Independent review found that the first wrapper took the source snapshots
before evaluating the authored expression, leaving a read-side-effect gap.
The corrected wrapper evaluates the expression **once, first**, then takes
the snapshots; output field declaration order remains unchanged. A required
regression preserves the weak ordering as an adversarial control: a read of
H.right can return the correct 257 while zeroing H.left. The weak gate agrees
with Lean and survives. The corrected gate saves a mismatch, replays it with
the fault active, and agrees after restoration. This observation wrapper is
unverified scaffolding, not a whole-program compiler or application proof.

### Read-seam mutations

All experiments used an isolated worktree, one active fault at a time.

1. In `Scalar.lowerWith`, lower `.add` to `.binary .sub`. Adjust the matching
   `lower_typed_in` addition case to use the equally well-typed `.sub` rule.
   `lake build P4blo.Scalar` exits 1 at `evaluate_lower_with`'s addition
   equality: modular subtraction cannot equal independent modular addition.
   This is a semantic **proof rejection**, not a runtime conformance kill.
2. In `FieldTests.lean`, replace the nine-bit `port` reference definition by
   `right` (also nine-bit). Default build/all audits pass; the field-port
   DRT agrees, then the independent expected answer fails: result 262 instead
   of 8, with the source-state snapshot unchanged. This is a compiled
   valid-but-unintended accessor caught by the independent oracle.
3. Replace the `bits` macro expansion's value by
   `(if $value = 85 then 84 else $value)`. Default build/all audits pass;
   field-add-valid DRT agrees, then the independent expected result fails:
   255 instead of 0. This exercises the refactored generic literal notation,
   which is not verified by the generic lowering theorem.
4. In production Python `field_of`, immediately before its return insert:

   ```python
   if isinstance(container, Header) and container.type_name == "H" and field == "right":
       container.fields[0] = Bits(8, 0)
   ```

   The field-right test fails at DRT and automatically saves its complete
   program/request. Returned right/result bytes remain `0101`; only the
   stored left snapshot changes from `ab` to `00`.
5. In production Python `write_lvalue`, immediately after the existing
   member-field assignment insert:

   ```python
   if isinstance(container, Header) and container.type_name == "H":
       container.valid = True
   ```

   Field-add-invalid fails at DRT: only the stored validity observation
   changes from `00` to `01`; result remains `00`.
6. At the same setter location, instead insert:

   ```python
   if isinstance(container, Header) and container.type_name == "H" and lv.member.field == "right":
       container.fields[0] = Bits(8, 0)
   ```

   Field-no fails at DRT: only the left snapshot changes from `ab` to `00`;
   the selected literal result remains `01ff`. The last two faults affect
   real production writes in the wrapper's initializers. They do not claim
   that a typed field-command lowering theorem already exists.

The three Python faults have no shared errors/diagnostics; their live bundle
replays each exit 1 with one divergence. After restoring each source edit,
the identical saved bundle replays with exit 0 and one agreement, without
rebuilding Lean. The Python evaluator diff is empty. All Lean/source faults
are restored too; default build and user tests pass after restoration.

### Exact replay reconstruction

From the root of an isolated checkout with this checkpoint's Lean binaries
already built, apply one Python edit above, then run:

```sh
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_lean_edsl_fields.py -q -k 'known_answers and field-right'
```

For faults 5 and 6, replace `field-right` with `field-add-invalid` and
`field-no`, respectively. Each command exits 1 and automatically saves
`.artifacts/drt/lean-fields-<case>.json` before the independent-answer check.
Replay while the fault is active, restore only that source edit, then replay
the **same** file again:

```sh
nix develop -c uv run python -m p4blo.drt.replay /absolute/checkout/.artifacts/drt/lean-fields-field-right.json --lean /absolute/checkout/ir/.lake/build/bin/p4blo-lean
```

Use the same case substitution in the bundle filename. Inputs are one empty
packet at ingress port 0, empty table entries, four ports and seed 0. Saved
bundle SHA-256 values, in the order read-side-effect/validity/sibling faults:

```text
b023413689d448f2b1d3b299bbfe03d40dc588930a490487ac3039017ecacb73
7d3233bf72af3afa712ea206593126e5f6c9c5c535b4552ff1031c41e264d0d6
e3b174b010a2301b4e9509c7d92b4cddcbd6270463630660de36c5e3742d4f81
```

The required observer regression independently repeats fault 4, checks the
saved program and inputs exactly, verifies the weak-gate survivor and asserts
both concrete full byte sequences plus live/restored outcomes on every run.

### Read-seam gates and decisions

Both Lean package builds/default audits/tests pass, including 392 executable
spec checks plus six new kernel rejection examples, all legacy user tests
and seven new field-expression answers. Four new audit roots (generic
expression correctness and concrete field typing/evaluation) use precisely
`[propext, Classical.choice, Quot.sound]`; prior scalar audits are unchanged.
The corrected focused field suite passes **9 tests**; independent combined
authored suites pass **43 tests**. Required all-suite DRT passes **250 tests**,
1197 deselected, no skips. New Python formatting, lint and pyright pass.
The integrator runs the full merged Python/schema/oracle gate; no Docker
build was performed in this worktree. Review: `docs/notes/reviews/field-expressions.md`.

Confidence is high in the concrete proof premises and medium in the generic
read-family factoring. Existing syntax/examples remain compatible and the
field examples use the same literal/operator syntax. Revisit if writable
packet bodies force pervasive inference annotations. Next factor command
writes once, discharge its generic laws using concrete scalar/field store
operations, add root permissions and integrate full-state command fixtures;
do not maintain two source sequencing interpreters.

## Command write-seam foundation

The next field-command increment begins with two separate reviewed steps.
The spec's `FieldTyping.WritablePath` carries actual root declaration,
nonempty/exact name and `ScalarStatements.writable` permission through
variable/member paths. `StatementTyped`/`BodyTyped` admit only matching
scalar-leaf assignment and scalar-boolean conditionals. No new syntax,
runtime behavior, total field checker or whole-program validity is claimed.
Kernel negatives reject nested writes through input/directionless roots,
missing/empty roots, a wrong nominal kind and a nine-bit RHS for an eight-bit
field. Constructive local/out/inout paths establish nonvacuity. The relation
checkpoint passed both package gates and 43 existing authored tests; review:
`docs/notes/reviews/field-permissions.md`.

`Scalar.CmdWith Reads Places` now owns the single command AST and recursive
source denotation, lowering, possible-root target collection and sequencing.
`Scalar.Cmd modes` is a specialization, retaining its named constructors,
combinators and theorem signatures. The old scalar evaluator/lowerer are
thin adapters, not parallel recursive implementations. Existing scalar
fixtures are unchanged.

`CmdWith.steps_with` composes exact scalar-read and scalar-write leaf laws
at related source/runtime states into finite **actual Execution.step**
prefixes, leaving an arbitrary continuation unexecuted. Each write must
succeed, relate the independently updated source store, preserve every
non-value Run field and preserve names outside its root. The no-action
`BlockFrame` premise remains explicit and is preserved through the real
map-update relation. The generic theorem does not assume correctness of a
whole command. `Scalar.Cmd.steps` discharges these leaf laws using actual
scalar read/write operations; `execute_correct` keeps its original concrete
declaration/permission/value premises and uses `Finishes.sound` as before.

Default audits include both generic sequencing laws and generic prefix
execution. Their exact axiom sets are respectively none, `[propext]`, and
`[propext, Classical.choice, Quot.sound]`; all old scalar audit expectations
are unchanged. Both package builds/audits/tests pass, including all prior
expression/command/path fixtures; all 43 existing authored conformance tests
also pass. Independent review repeats those tests, the user executable and
public API/axiom queries: `docs/notes/reviews/command-seam.md`.
The integrator owns merged full gates.
The next checkpoint must instantiate this seam with concrete aggregate
root modes and path writes before any verified field-command claim.

Confidence is high in the compositional proof and medium in this explicit
parameter API. It introduces no typeclass hierarchy or new dependencies.
Revisit if the route-selected forwarding fixture needs pervasive dependent
casts, if concrete final theorems retain arbitrary correctness callbacks,
or if compatibility pressures create a second sequencing implementation.
The field campaign will distinguish proof-rejected faults from compiled
surface/runtime kills; this factoring alone adds no new mutation-adequacy
claim beyond the earlier retained scalar command experiments.

## Concrete scalar-field commands

The concrete `Fields.Cmd modes` instance adds no source operator/command
AST, recursive sequencing evaluator or alternative IR executor.
`FieldPlaces` reuses `Scalar.Mode` and its authoritative local/out/inout
policy through a general `Mode.declarationIR` helper; the scalar declaration
API and prior proof audits remain unchanged. Aggregate Modes are indexed
by the existing Layout, and `Modes.Agrees` checks the actual root's name,
nominal type and direction. `Modes.scope_agrees`/`frame_matches` construct
declaration and value witnesses. `Place.typed` carries writable-root
evidence down existing variable/member paths to `FieldTyping.WritablePath`.

The public `Fields.Cmd.steps` and `execute_correct` have only concrete
premises: `RootWellFormed roots`, `roots.IndexAgrees initial.index`,
`modes.Agrees initial.frame.scope`, exact `FrameMatches source initial.frame`
and both halves of `BlockFrame`. They derive authoritative body typing and
actual finite-prefix/execution success. The full final source store is
related exactly, actual declaration agreement is preserved, all non-value
Run fields are unchanged, and names outside the possible root-target set
retain their values. `Cmd.validities` additionally proves that every stored
header-validity bit is unchanged. An arbitrary continuation remains
unexecuted in the prefix theorem; `Steps.execute`/`Finishes.sound` connects
the empty-continuation case to the existing production executor.

Read laws are discharged by actual `Ref.evaluate`; writes by actual
`Ref.write_matches`, which reconstructs each nested parent and writes its
complete root. The invariant also carries actual index agreement across
every update. No public field theorem asks a caller to assume correctness
of a callback or of an entire lowered command. Mutable storage alone does
not establish permission: a kernel witness has exactly matching values but
an actual input declaration where Modes says inout, and its declaration
agreement is provably false.

The mixed constructive fixture contains Ethernet and IPv4 headers, metadata,
a read-only route record and a scalar local. Its exact source/index/frame
witness instantiates final execution, with an extra unmodeled runtime root,
nonempty packet and nonzero cursor/emitter/visits/extern state/table defaults.
Ten independent Lean full-root answers exercise dependent writes to the same
header, updated-state branch conditions, both branches and shared tail,
wraparound, all combinations of the two initial header validity bits, and
a route-selected forwarding rewrite. Source answers are explicit IR values,
not results obtained by evaluating the lowered body. Additional kernel
checks reject input/directionless Places, wrong assignment/condition types,
forged root direction/type, missing nominal index and a hidden action-value
layer. A supplied continuation is both left untouched by a kernel proof
and shown to genuinely fault when run separately. Actual `Index.build` and
`Frame.forBlock` construct local/out/inout aggregate roots; a scalar write
then retains zero siblings and invalid header bits in all three cases.

Seven new default audits cover the constructive scope/frame, writable-path
bridge, validity preservation, concrete prefix and execution, and the mixed
fixture's final correspondence witness. The validity lemma uses precisely
`[propext, Quot.sound]`; the other six use precisely
`[propext, Classical.choice, Quot.sound]`. Both complete Lean package gates,
all default audits and the old/new user tests pass. There is no new trusted
axiom or native-evaluation escape.

These are already-initialized, action-free scalar-field body theorems, not
general initialization, aggregate assignment/copyback, whole-program
validity, universal Python equivalence or a verified packet-processing
application. The forwarding body consumes provided route-hit and next-hop
values. It guards TTL 0/1, then uses existing wrapping addition by 255 to
decrement the eight-bit TTL. Parser extraction, header-validity tests, table
lookup, checksum recomputation, architecture fate and deparsing are excluded.

Confidence is high in the concrete correspondence boundary and medium in
positional paths/mode ergonomics. References and Places are declared once;
the forwarding body itself uses ordinary assign/if/sequence and `place.read`
without casts or proof terms. Revisit when parsing or application predicates
force repeated path transports, or when a named-field surface can improve
readability without obscuring the single underlying typed AST. Do not add
an independent forwarding evaluator to make the example easier to prove.
