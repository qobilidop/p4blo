# Review: A2, SpecTec rule coverage of p4blo's inputs

Commit reviewed: `6724b7f` (HEAD of `main`), covering the merge `35d67cd`
and the follow-ups `a7b2bb3` and `94cd629`. SpecTec pin `2730cfd`.
Date: 2026-09-24. Read-only review; nothing in the repository or the
checkout was modified. Scratch artifacts (a patched probe copy, extra
inputs, reports) are under this review's scratchpad.

## Summary

The measurement holds up. Rule attribution is sound for every in-scope
rule. All 359 in-scope rules that have a leaf have exactly one, so no
region was assigned to the wrong rule. I rebuilt the probe from a
*copy* of the library, instrumented to record the interpreter's real
`Tailcall_rel`, and every tail-credited (leaf, vector) pair (685 of
them, 24 in-scope rules) matched a real tail call. Two probes flipped
exactly the rules predicted and nothing unrelated:

- A `range` select case flipped the range rules.
- A lookahead in `verify` on a short packet flipped the six abort rules.

The cross-check with `cover-sim -instr` fails the run on a mismatch. I
simulated one. `--check` compares the whole rendered report, and two
fresh runs came out byte-identical with no path leakage.
`tests/test_spectec_coverage.py` passes.

The defects are in the hand-written classification and in scope:

- Two function exclusions have the wrong category, and one names a row
  that does not exist.
- A2's own definition says the report covers the corpus *and the
  generated programs*. A1 landed after A2, and the generated programs
  still are not measured. So 26 `reach` texts saying "once its programs
  run on SpecTec (item A1)" are stale. The 58 CI seeds alone hit 3 of
  the 51 "unhit" rules and 9 of the 12 "unhit" functions.
- The ancestor approximation misattributes leaves in 5-typing. That is
  out of scope today but unsound as written.
- The inventory still misses `tbl dec` functions (52 items).

## Confirmed defects

1. **`$shr_arith` is miscategorized.**
   `tests/oracle/spectec-coverage-exclusions.json:21`: it is listed as
   `not-representable`, and its own reason says `int<N>` is out of scope
   for v0. `$shr_arith` is called only from the signed clauses of
   `$bin_shr` (`spec/3-operations/3-operations.watsup:294,305,317`). By
   the fixture's own definitions it is `excluded-construct`, with row
   `fixedIntTypeIR (INT<n>)` (`docs/p4-spec-coverage.md:61`).
   `not-representable` means "the construct is in".

2. **`$bitacc_replace` is `unhit` but unreachable, and its reach names a
   non-existent row.** `spectec-coverage-exclusions.json:38`. The reason
   says the printer never emits a slice lvalue. The `reach` says "Not
   reachable ... (coverage row `sliceLvalueIR`); reclassify as
   excluded-construct if that elaboration is kept."
   - The elaboration *is* kept (`.agents/decisions.md:131`, "Elaborations,
     named in the coverage table").
   - No row `sliceLvalueIR` exists. The row is `lvalueIR: typedLvalueIR
     [ e sliceop e ]` (`docs/p4-spec-coverage.md:137`), which entries 34
     and 35 already use.

   It belongs in `excluded-construct`. The test did not catch this for
   two reasons. `test_exclusions_are_well_formed` checks `row` only for
   `excluded-construct`. And an `unhit` entry whose reach says
   "not reachable" passes the non-empty check.

   Fixing 1 and 2 moves the docs table (`docs/p4-spec-coverage.md:355-361`)
   for 3-operations to excluded-construct 24, not-representable 7,
   unhit 11.

3. **The reach texts pointing at item A1 are stale, and A2's input set
   omits the generated programs.** 26 entries say "... once its programs
   run on SpecTec (item A1)". A1 merged at `4a3504a`, 30 minutes after
   A2, and runs 60 seeds on SpecTec in CI (`tests/test_oracle_generated.py`).

   The plan's A2 says "Run it over the corpus and the generated programs"
   (`.agents/notes/ir-semantics-plan.md:66`). The report measures only
   the corpus and examples (`coverage.py:103-105`). `--inputs` exists,
   but the vectors must already be translated, and no path in the repo
   produces such a directory from `tests/oracle/generated.py`.

   Reproducer: `scratchpad/gen.py` writes CI seeds 0..59 (minus the
   `KNOWN` 0 and 25) through `generated.prepare` and `run.translate`.
   Then:

   ```
   nix develop -c uv run python tests/oracle/coverage.py --inputs <scratch>/gen60 --out <scratch>/rep-gen.json
   ```

   This took 68 s, with 73 programs and 223 vectors. In-scope flips to
   hit:

   - Rules: `Expr_eval/cond-true`, `Expr_eval/cond-false`,
     `VarDecl_eval/non-initializer`.
   - Functions: `$bin_bxor`, `$bin_mul`, `$bin_satminus`,
     `$bin_satplus`, `$bxor`, `$cast_bool`, `$un_lnot`, `$un_minus`.
   - Not enforced (8-dynamic functions): `$find_object_qualified_e`,
     `$update_object_qualified_e`.

   Instructions rise from 5646 to 5864 of 14475. None of the
   "parser-condition generator ... lookahead" reaches flipped, so those
   suggestions are unproven for the current generator; the lookahead
   program in item 4 below shows the construct itself does reach them.

   Either feed the CI seed set into the report through a small adapter
   (`--generated SEEDS`), or rewrite the 26 reach texts and record the
   decision.

4. **The ancestor attribution is unsound** (out of scope today).
   `coverage.py:76-79, 617-621`. A rule with neither outputs nor path
   premises gets the relation signature's region, and its leaf is
   credited to the nearest ancestor whose line falls in *any* rule span.
   The ancestor is usually a shared case analysis whose region belongs
   to a sibling rule.

   Reproducer (`scratchpad/anc.py` on the probe dump): in
   `5.03-typing-wellformed.watsup`, the leaves of
   `CallableType_wf/builtinMethodTypeIR` (610) and
   `/tableApplyMethodTypeIR` (681) are both `result@30 <- case@562`. They
   are credited to `CallableType_wf/actionTypeIR` (561, now `leaves:3`),
   while the two real owners show `leaves:0`, which reads as "merged". The
   `Type_wf/*TypeIR` and `Type_alpha/*TypeIR` rows marked `"via":
   "ancestor"` come from the same mechanism.

   No 8-dynamic rule uses this path at this pin, so no in-scope number
   is wrong. After a pin bump it would silently produce hits for the
   wrong rule. Suggestions:
   - Report such leaves as unattributed.
   - Have `test_spectec_coverage.py` fail if any in-scope rule has
     `"via": "ancestor"` or more than one leaf.
   - Allow `leaves: 0` only for rules listed as known merges.

5. **The inventory still skips `tbl dec`.** `scripts/spectec-rules.py:47-50`
   strips only `builtin`/`extern`. 52 table-defined functions are
   missing: 4 in `2-static-runtime` (`$is_defaultable_typeIR`, ...) and
   48 in `5-typing` (`$compat_*`, `$nestable_*`). That contradicts the
   script's docstring ("everything under spec/ except 9-arch").

   They surface in `outside_inventory`. The coverage.py docstring
   (`:90-92`) and the comment (`:726`) still describe that list as
   "9-arch" plus builtin/extern, which is stale since `a7b2bb3`. No
   in-scope effect, since none are in 3-operations or 8-dynamic.

## Attribution analysis

- **Region of a leaf.** `pass/structure/struct.ml:137-148`: a `Result`
  carries `over_region` of the rule's output expressions. Without
  outputs it takes the path premises' region, and failing both the
  relation signature. The probe records `r.left.line`, which for outputs
  is the conclusion's output line, inside the rule span. I checked that
  every in-scope rule except the two known `.apply` aborts has exactly
  one leaf. A cross-attributed region would show up as a 2/0 pair; none
  exists in 8-dynamic.

- **Merged rules.** `Callee_eval/abort` at 255 (parser) and 303 (control)
  have no leaf. The leaf at 352 (table) stands for all three. This is
  documented correctly, in the docstring and in exclusions 236/237. It
  is an inherent ambiguity: if a parser `.apply` abort ever fired, row
  352 would read hit and the test would call its exclusion stale, though
  the table rule never fired. Worth one sentence in the exclusion
  reasons.

- **Tail calls.** The interpreter tail-calls only when the block is
  `[ResultI]`, `tail` holds, `iterinstrs = []` and the outputs are
  syntactically equal (`interp/interp-sl/interp.ml:1857-1874`).

  The probe's flag is looser: `RuleI (_,_,_,_,[ _ ])`, any single-child
  block (`coverage.py:178`). It is used only when the rule instruction
  ran and the `Result` did not. That can also mean the premise failed,
  because the `Unmatch` is caught and becomes `Cont`, which is
  backtracking (`interp.ml:1874`).

  Measured with a probe built from a copied library, with a hook that
  records `Flow.Tailcall_rel` per instruction (`scratchpad/tprobe`,
  `tcheck.py`): 685 tail-credited pairs, **0 without a real tail call**.

  Two fixes:
  - Tighten the flag to `RuleI (_, _, _, [], [ { it = ResultI _; _ } ])`.
  - Correct the docstring at `:73-75`. A failing tail-called relation
    raises `Unmatch` into the *caller's* `RuleI`, which backtracks; it
    does not necessarily "end the run". The remaining over-approximation
    is only that case.

- **Builtins and externs** (`a7b2bb3`). `BuiltinDecD` and `ExternDecD`
  are printed as functions, and `ExternRelD` as a relation.
  `on_func_enter` fires in `invoke_func`'s loop before dispatching to
  `Func.Builtin` (`interp.ml:2098`), and `on_rel_enter` fires before an
  extern relation's dispatch. The report agrees: `$shl` has 588 calls,
  `ExternMethodCall_eval` 504, `$init_archState` 21. Attribution is
  correct.

  Function granularity hides clauses, though. `$bin_shr` "hit" would not
  mean its signed clauses ran. Per-`Return` leaf attribution would be
  the function-side analogue of rule leaves.

- **Hand-checked rules.** 29 rules across expressions, lvalues,
  statements, parser, table, call and copy-out, with hitting programs
  checked against the printed sources:

  - `&&`: `Expr_eval/land-true` (tail-credited) and `land-false` hit in
    exactly the four programs with `&&`. `acl` and `priority` contain
    only `&&&`.
  - `||`: `lor-*` hit in exactly `tutorial_firewall` and
    `examples-firewall`.
  - Mux: `cond-*` are unhit, and no printed program has `?`.
  - Stacks:
    - `Lvalue_write/stack-next`, `Lvalue_eval/stack-next-in-bounds` and
      `Lvalue_read/stack-in-bounds` hit in `acl`, `stacks` and
      `subparser_stack`.
    - The out-of-bounds and `Lvalue_read/stack-next` rows are unhit.
  - Select:
    - `SelectCase_match/no-match` and `SelectCases_match/cons-head-no-match`
      are hit in the same five programs.
    - `ParserSelect_eval/match` is hit; `no-match` is not.
  - Parser transition, tables and statements:
    `ParserTransition_eval/nameIR-accept`,
    `Table_eval/keys-cont-matches-cont-action-cont`, the four
    `Stmt_eval` if-rules, `Copy_out` and `Eval_keyset` are all hit
    where expected.

- **Flip experiments** (`--inputs`, plus a same-program control that
  differs only in the construct):
  - A `16w0x0800 .. 16w0x0900` select case, compared with the same
    program using a literal case, flips exactly:
    - `Eval_keyset_simple/left-cont-right-cont` (136) and group
      `Eval_keyset_simple/range`;
    - `$bin_le`;
    - the two typing `range` rules.
  - `verify(packet.lookahead<bit<16>>() == 16w1, ...)` on a 1-byte packet
    flips exactly:
    - `Expr_eval/non-short-circuit-abort`, `Expr_eval/callee-cont-call-abort`;
    - `Exprs_eval/cons-head-abort`;
    - `Copy_in_arg/abort`@9, `Copy_in/cons-head-abort`;
    - `Call_eval/externFunctionCallee-copyin-abort`.

## Exclusion audit

| # | Item | Category | Verdict |
|---|---|---|---|
| 1 | `$shr_arith` | not-representable | **Wrong**: excluded-construct, row `fixedIntTypeIR (INT<n>)` (defect 1) |
| 3 | `$bitacc_replace` | unhit | **Wrong**: excluded-construct, row `lvalueIR: typedLvalueIR [ e sliceop e ]`; reach names a non-existent row (defect 2) |
| 13 | `$bin_le` | unhit | Right. A range select case also reaches it (verified). |
| 17 | `$cast_bool` | unhit | Right, but the reach is stale: the CI generated seeds hit it. |
| 32 | `$cast_set` | not-representable | Plausible. The range experiment did not reach it; keysets print at key width. |
| 36–41, 234, 259 | `$sizeof*`, `Callee_eval/cont`@192, `Call_eval/builtinSizeMethodCallee` | not-representable | **Doubtful category.** The size methods are not "in"; the reason admits the docs have no row. Add an `excluded, compile-time known` row and reclassify. |
| 45 | `Expr_eval/non-short-circuit-abort` | unhit | Right; verified by the lookahead program. The generator named in reach did not reach it in 58 seeds. |
| 49, 50 | `Expr_eval/cond-true/false` | unhit | Right, but stale: the CI generated seeds hit both. |
| 53 | `Expr_eval/non-default-abort`@210 | unhit | Plausible. The validator allows `call_extern` in parsers. |
| 77, 79–82, 84–85, 193, 195, 197 | keyset and select abort rules | not-representable | Right. Every keyset the printer writes is a literal. |
| 83 | `Eval_keyset_simple/left-cont-right-cont` | unhit | Right; verified with a range case. |
| 91 | `Lvalue_eval/stack-next-out-of-bounds` | unhit | Plausible. No vector overfills a stack. |
| 100 | `Lvalue_read/stack-next` | not-representable | Right. `NEXT_ONLY_EXTRACT` (`validator.py:1336`), and out copy-in uses `$default`, never a read (`8.10.2:84-95`). |
| 127, 128 | `Stmt_eval/non-else-abort`, `else-abort` | excluded-construct, `exitStatementIR` | Right. Control conditions cannot hold a lookahead. |
| 189 | `BlockElementStmt_eval/variableDeclarationIR` | excluded-construct, `blockStatementIR` | Right. The printer declares locals as control/parser locals (`v1model.py:674`). "At block level" is ambiguous with `blockStatementIR`; say "as control or parser local declarations". |
| 191 | `VarDecl_eval/non-initializer` | unhit | Right, but stale: the CI generated seeds hit it. |
| 199 | `ParserTransition_eval/nameIR-reject` | unhit | Right. No printed program has `transition reject`. |
| 202 vs 210/211 | `ParserStmt_eval/parserBlockStatementIR` (unhit) and `ParserBlockElementStmt_eval/variableDeclarationIR-*` (excluded, row `parserBlockStatementIR`) | mixed | **Doubtful row.** The printer *does* produce `parserBlockStatementIR` (braced parser `if` branches, as 202 says), yet 210/211 cite that row as the excluded construct. The real reason is "no declarations inside a block"; cite `parserLocalDeclarationIR` (row 186) or reword the docs row. |
| 228 | `Callee_eval/definedFunctionCallee` | excluded-construct, functions | Right. |
| 236, 237 | `Callee_eval/abort`@255/@303 | not-representable | Right, and the merge note is accurate. |
| 239 | `Callee_eval/parenthesized` | not-representable | Right. `_operand` parenthesizes non-atoms only, and every callee base is an atom (`v1model.py:151,191`). |
| 215 | `TableKey_eval/exit` | excluded-construct, `exitStatementIR` | Right. |

## Scope

- **Enforced in-scope set** (`tests/test_spectec_coverage.py:52-54`):
  rules of 8-dynamic and functions of 3-operations. The report flags
  `in_scope: true` for every 8-dynamic item, including its 35 functions,
  60 relations and 99 rule groups, but only the rules are enforced.
  Seven 8-dynamic functions are unhit and unexplained:
  - `$find_constructorDef_e`
  - `$find_object_qualified_e`, `$update_object_qualified_e` (both hit
    by the generated seeds)
  - `$is_non_fallthrough_switchCaseIR`, `$match_switchLabelIR_general`,
    `$match_switchLabelIR_table`
  - `$values_of_setValue`

  These are run-time helpers (`$match_keyset(s)`, `$select_action` and
  the priority functions decide select and table matching). Put the
  8-dynamic functions in scope; the seven exclusions are easy to write.
- **Other sections.** Of the 2- and 6-section functions called from
  8-dynamic or 3-operations, only `$isValid_header` and
  `$update_headerUnion` are unhit, both header-union. So widening the
  scope to "every function called from 8-dynamic/3-operations" costs two
  exclusions and closes the gap in principle. `4-p4-ir` is accessors,
  and leaving it out is reasonable.
- **Typing-time calls.** "Function hit" includes constant folding during
  typing (documented). Splitting call counts into typing-time and
  simulation-time would make the 3-operations rows a dynamic claim. The
  probe can bump a phase flag around `run_stf_test`'s typing step if
  the API exposes it, or diff against a typing-only run.

## Cleanup requests

- **Separate probe source.** Move `PROBE_ML` into
  `tests/oracle/coverage_probe.ml` and hash the file for the stamp. You
  get OCaml tooling, readable diffs, and a CI cache key on the probe
  alone.
- **CI cache key.** `.github/workflows/oracle.yml:38` keys the whole
  oracle cache, including `~/.opam` and the SpecTec build, on
  `coverage.py`. Any edit to that file, a docstring included, forces a
  full opam and SpecTec rebuild. The probe step runs on every job and
  is stamped and incremental, so drop `coverage.py` from the key, or
  give the probe dir its own cache entry keyed on the probe source.
- **Require flag.** `test_report_matches_a_fresh_measurement` skips when
  the probe is missing. Add a `P4BLO_REQUIRE_SPECTEC_COVERAGE=1` guard,
  set in `oracle.yml`, matching the Lean and XDP gates, so a skip in CI
  fails.
- **Structural invariants.** Add test assertions for in-scope rules:
  `leaves == 1`, except for a named list of known merges, and never
  `"via": "ancestor"`. This catches defect 4 and new merges at a pin
  bump.
- **Silent skip in `walk_def`.** `coverage.py:204-207` ends with
  `| _ -> ()`. A new definition kind with instructions is caught by the
  totals check, but one without instructions (a new extern kind) would
  silently vanish. Make it an explicit list of the ignored constructors.
- **Weak cross-check.** It compares only the headline totals. The
  stock `-instr` file prints `+`/`-` per definition, so comparing
  per-definition hit counts (`per_origin`) costs little and would catch
  compensating drift.
- **`--inputs` paths.** `--inputs` with a directory outside the repo
  writes absolute paths into `inputs[].id/source` and
  `extra_input_dirs`, and `--check` then depends on them. Refuse
  absolute paths when writing the committed report, or document that
  `--inputs` is for ad hoc runs only.
- **Readability.** The module and the docs section read well.
  - The exclusions fixture repeats identical reasons dozens of times
    (36 for-loop entries). A per-row default reason would shrink it.
  - It is pretty-printed with indent 1, while the report is one entry
    per line. Pick one convention.

## Anything else

- Stable reproduction: `--check` passed twice, and a fresh `--out` was
  byte-identical to the tracked report. The report contains no
  absolute paths, and its commit is tied to `build.sh`'s pin by both
  `build_report` and `test_fixtures_name_the_pinned_commit`.
- Isolation: the probe dir holds only a `lib` symlink. The checkout's
  dune files have no `promote` rules, and after all runs
  `git status --ignored` in the checkout shows only `_build/`,
  `p4spectec` and `.p4blo-built`.
- The probe depends on the SL constructors' arities, `instr.note.iid`,
  `Inst.Handler.Default`/`Inst.Hook`, `P4spectec.structure ~final` and
  `build_sim ~cache ~arch`. Arity or signature changes break the build
  loudly. A new instruction kind does too, since dune's dev profile makes
  non-exhaustive matches errors. The silent risks are the tail-call
  condition (above) and `walk_def`'s wildcard.
