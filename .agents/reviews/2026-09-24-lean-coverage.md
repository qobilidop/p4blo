# Review: Lean rule coverage (B1)

Commit reviewed: `0db270b` (merge of `work/lean-coverage`: `4a0c6c8`, `52526a8`,
`f51d24b`, `5c77102`). Date: 2026-09-24. Reviewer: independent, read-only.
Experiments ran in `/Users/qobilidop/my/work/p4blo-wt/lean-coverage` (at `5c77102`,
whose non-ledger content equals the merge); that worktree was left clean
(`git status --porcelain` and `git diff --stat` both empty, Lean rebuilt from
the restored source, `tests/test_drt_coverage.py` 6 passed).

## Summary

The semantics really is untouched:
`git diff eb0a440 0db270b -- spec/ir/P4bloIR/{Exec,Eval,Env,Tables,Interp}.lean spec/ir/ProofAudit.lean spec/ir/CodecProofAudit.lean impl/lean/UserProofAudit.lean`
is empty. The only other change under `spec/ir/` is the new `P4bloIR/Coverage.lean`
and its import in `P4bloIR.lean`. The observer drives the real `Execution.step`
from the same starting machine for each block, and the reply still comes from
`Switch.run`. The protocol and the Python accounting work.

The claim that coverage is exact for every request does not hold. Six confirmed
defects, all in `classify`'s conditions or the observer's preconditions:

- Copy-back tags are computed against the wrong state: before earlier
  copy-backs, and in the callee action's name layer.
- Two ledger behaviors that SpecTec treats differently or that the ledger lists
  explicitly go unreported: header equality nested in a struct or stack, and an
  action's `out` parameter read at zero.
- An explicitly declared `NoAction` default is tagged as an ordinary default.
- Tags are reported for blocks `Switch.run` refuses to run.

Sensitivity: the adequacy test catches a tag that disappears and a stale
unhit entry. Nothing in either language catches a tag that fires on the
wrong condition.

## Confirmed defects

Reproducers use one template: header `h_t { a: bit<8> }`; struct
`H { h: h_t, g: h_t, s: h_t[2] }`; empty `M`. Parser `P` extracts `hdr.h` and
accepts. Deparser `D` emits `hdr`. Only control `C`'s declarations and body vary.
Each was checked with the Python validator (all valid) and run with
`p4blo-lean run prog.json` on the request
`{"entries":{},"ingress_port":0,"packet":"2a"}`. The output bytes prove what the
real run did.

1. **Copy-back tags ignore earlier copy-backs of the same call**
   (`spec/ir/P4bloIR/Coverage.lean:705-711`, used at 800, 974, 983). The ledger's
   "Copy-back target" entry says each lvalue is resolved when it is written, after
   the earlier `out` arguments were written. `copyBackTags` resolves every lvalue
   against the state before the return step.
   - Program: local `idx: bit<32>`; action
     `b(out bit<32> i, out h_t e) { i = 0; e.setValid(); e.a = 119; }`; body
     `idx = 5; b(idx, hdr.s[idx]);`.
   - Observed: output `2a77`, so the second copy-back landed in range at `s[0]`.
     Yet the tags include `stack.index.writeOutOfRange`.
   - Expected: no `writeOutOfRange` (a false positive). With the roles swapped
     (`idx = 0`, `i = 5`), the tag is missed (a false negative).
   - The same root cause affects `callExtern`'s sequential out/result writes
     (lines 800-805) and `table.hit.written`'s `writeTags` (line 895). The latter
     is computed before the chosen action runs, although `writeHit` runs after it.

2. **An action's copy-back is classified in the callee's name layer**
   (`Coverage.lean:972-975`). `dispatch .actionReturn` (Exec.lean:302-306)
   restores the caller's `action`/`actionVars` *before* `copyBack`. `workTags`
   passes `run` unchanged, so the lvalue names resolve through the callee's
   parameters. Two actions may share parameter names (the proto forbids only
   reuse of block names), so nested calls misclassify.
   - Program: `b(out bit<8> x) { x = 1; }`; `a(inout h_t x) { b(x.a); }`; body
     `a(hdr.g); hdr.g.setValid();`.
   - Observed: output `2a01`, so the field of the still-invalid `hdr.g` was
     written. `header.field.writeInvalid` is absent from the tags.
   - Expected: `header.field.writeInvalid`.
   - Fix: classify with `{ run with frame := { run.frame with action := outer.action, actionVars := outer.actionVars } }`,
     as the `blockReturn` case already does with `caller`.

3. **Header equality inside a struct or stack is not tagged**
   (`Coverage.lean:497-510`). The ledger ("Comparison") says "wherever a header is
   compared, including inside a stack, the next entry applies". That next entry,
   "Header equality", is the one classified *deviates* against SpecTec.
   `equalityBehaviors` tags only headers compared at the top level.
   - Program: local `k: H`; body
     `k = hdr; k.g.a = 9; k.s[0].a = 9; r = (k == hdr); q = (k.s == hdr.s); hdr.h.a = (r && q) ? 1 : 0;`.
   - Observed: output `01`: invalid headers with different stored fields compared
     equal, inside a struct and a stack. The tags have `expr.equality.struct` and
     `expr.equality.stack` only.
   - Expected also: `expr.equality.header.bothValid` (the `h` fields),
     `expr.equality.header.bothInvalid` and
     `expr.equality.header.invalidFieldsDiffer`.
   - Fix: recurse through struct fields and stack elements.

4. **An action's `out` parameter read at zero is not `value.uninitialized`**
   (`Coverage.lean:524-538`). `zeroLocal` returns `false` for any name in the
   action layer. The ledger entry cites `argumentValue` and `Copy_in_arg/out`,
   which cover action `out` parameters, and the docstring says "an `out`
   parameter".
   - Program: local `y: bit<8>`; action `b(out bit<8> x) { y = x; }`; body
     `y = 3; b(hdr.h.a);`.
   - Observed: output `00`. The tags have no `value.uninitialized`.
   - Expected: `value.uninitialized`.

5. **An explicit `NoAction` default is tagged `table.miss.defaultAction`, not
   `table.miss.noAction`** (`Coverage.lean:926-929`). The ledger ("Table miss")
   makes a declared `NoAction`, which must be empty, the same as none declared.
   The docstring says "the default on a miss is `NoAction`, nothing".
   - Program: `actions { name: "NoAction" }`; table `t` with an exact key on
     `hdr.h.a`, `actions: "NoAction"`, `default_action { action: "NoAction" }`;
     body `t.apply()`.
   - Observed: `table.miss`, `table.miss.defaultAction`.
   - Expected: `table.miss.noAction`.
   - `tests/corpus/tutorial_firewall` declares exactly this default, so the unhit
     reason for `table.miss.noAction` ("every generated table declares a default
     action") needs re-examining after the fix.

6. **Tags for blocks `Switch.run` refuses to run** (`spec/arch/P4bloArch/Coverage.lean:58-96`).
   `traceParser`/`traceControl`/`traceDeparser` skip the kind and arity check that
   `runParser`/`runControl`/`runDeparser` make through `blockOf` (Interp.lean:39-43).
   `p4blo-lean run` does not run the validator.
   - Program: add `params { name: "extra" type { bits: 8 } direction: DIRECTION_IN }`
     to parser `P` (the validator rejects this with `EXPORT_SIGNATURE`; the Lean
     endpoint loads it).
   - Observed: `{"error":"block 'P' is not a parser of (out H, inout M)", "coverage":["lvalue.member","parser.extract.header","parser.target.accept","parser.transition.direct","stmt.extract"]}`.
   - Expected: `[]`; nothing ran.
   - This input is outside the validated domain, so severity is low. It still
     contradicts "up to the failure" in `Main.lean`'s usage text.

## Doubtful conditions

- `parser.subparser.reject` (`Coverage.lean:986`) fires on any `NoError` fault
  reaching a block return. `verify(false, NoError)` in a sub-parser fires it with
  no `reject` anywhere; checked, the tags were `parser.verify.failNoError`,
  `call.block.faultCopyBack` and `parser.subparser.reject`. The docstring says
  "an explicit `reject`". Either narrow the condition or reword the docstring.
- `table.miss.hostDefault` (line 929) compares the installed default with the
  declared one. A host that sets the same default as declared is not counted as
  replacing it. That is defensible, but it is not what "a default the host
  replaced" says.
- Tags are emitted before the step and are not withdrawn if the step faults. For
  example, `call.extern.out`/`call.extern.result` fire even if the extern raises,
  and `table.hit.written` fires even if the action faults. Validated controls have
  no run-time fault today, so this is latent. The parser statements that can
  fault do classify their fault conditions correctly.
- `castBehaviors` tags `bool` to any `bit<N>` as `expr.cast.boolToBits`
  (line 514). This is harmless while the validator allows only `bit<1>`.

Checked against the ledger and `Exec.lean`/`Eval.lean`, with no issue found
(by probe where marked *):
- Values: `expr.add/sub/mul.wrap`, `addSat/subSat.clamp`, `shl/shr.overflow`,
  `shl.truncate`, `shift.otherWidth`, the five `expr.cast.*`,
  `expr.equality.stack.nextIndexDiffers`.
- Headers: `header.field.readInvalid`, `header.assign.invalid`*,
  `header.setValid.alreadyValid`, `header.setInvalid.alreadyInvalid`*.
- Stacks: `stack.lastIndex.empty`*, `stack.push.clamp/oversize`,
  `stack.pop.clamp/oversize`*, `stack.index.readOutOfRange`.
- Parsers: `parser.extract.next`*, `.next.full`*, `.next.fullAndShort`*,
  `.tooShort`*, `.zeroWidth`, `.indexOutOfRange`, `parser.advance.tooShort`,
  `parser.verify.*`*, `parser.target.*`, `parser.revisit`/`timeout`/`timeout.subparser`.
- Select: all eight `select.*`.
- Tables: `table.hit`, `table.miss`, `table.lpm.longest`,
  `table.ternary.priority`/`priorityZero`, `table.constEntry`.
- Calls: `call.copyOut.order`, `call.action.nested`*, `call.block.faultCopyBack`*.
- Emit: `emit.header.valid/invalid`*, `emit.struct`*, `emit.stack`*, `emit.padding`.

## Mutation results

Each mutation was reverted byte for byte, then Lean was rebuilt and the tests
were rerun green.

- **(a) Wrong condition.** `Coverage.lean:485`: `x.value < y.value` changed to
  `x.value ≤ y.value`, so `expr.sub.wrap` fires when `x == y`.
  - `lake build` and `lake test` in `spec/arch`: all tests passed.
  - `pytest tests/test_drt_coverage.py tests/test_drt_protocol.py`: 27 passed.
  - A probe of `3 - 3` on `bit<8>` reported `expr.sub.wrap`.
  - **Survived; nothing catches it.** The Lean checks assert only that some tags
    are included, apart from one `!contains`. The Python test compares only the
    unhit set. A table of exact expected tag sets for small programs, including
    negative cases at each boundary, would kill this class.
- **(b) Removed emission.** `Coverage.lean:922`: `if m.hit then [.«table.hit»]`
  changed to `if m.hit then []`.
  - Lean `archTests`: passed (not caught).
  - **Caught** by `tests/test_drt_coverage.py::test_lean_agrees_and_hits_every_rule_tag`:
    "1 rule tags stopped being hit ... table.hit".
- **(c) Stale unhit entry.** Added `"table.hit"` to `tests/drt-unhit-tags.json`.
  - **Caught** by the same test's stale assertion: "tags listed in
    tests/drt-unhit-tags.json are now hit; remove them: table.hit". It fires
    before the `len(known) <= 34` ceiling.

## Protocol

- **Error and malformed replies carry `coverage`.** The following replies to
  `p4blo-lean run` on the forwarder all carried `"coverage":[]` with
  `error` and `state`, and exit 0:
  - a non-JSON line;
  - ingress port 9;
  - odd-length hex.

  A truncated packet reported partial tags, including `parser.extract.tooShort`.
- **`RuleCoverage`** counts `None` as `unreported` and an empty list as
  `reported` (`coverage.py:45-51`). `test_an_older_peer_without_coverage_is_counted_not_refused`
  covers this.
- **The fake is honest in behavior:** empty inventory, `coverage: []`, and
  `--fake --coverage` prints "0 of 0 tags hit over 5 requests". But the comment
  at `impl/python/p4blo/drt/coverage.py:42` says unreported replies come from
  "an older peer, or the fake". The fake sends `[]` and is counted as reported,
  which `test_the_fake_reports_no_rule_tags` asserts. Fix the comment.
- **The CLI works.** `python -m p4blo.drt tests/corpus/forwarder 20 --coverage --lean spec/arch/.lake/build/bin/p4blo-lean`
  exits 0 and prints "rule coverage: 36 of 157 tags hit over 20 requests",
  36 hit lines and 121 unhit lines.

## Cleanup requests

Tag docstrings in `spec/ir/P4bloIR/Coverage.lean` whose citations no longer
match `docs/ir-semantics.md` at `0db270b`. The current sections are: Values and
operations, Expressions, Lvalues and assignment, Statements and calls, Parsers,
Tables, Deparsers, Externs.

- Module header, line 18 ("the value rules of "Values"") and the comment at 137:
  the section is now "Values and operations".
- Lines 138-146: `Values, "Arithmetic"` should be `Values and operations,
  "Arithmetic on `bit<N>`"`.
- Lines 148-157, 158-165, 175-191, 204: the section `Values` should be
  `Values and operations` (the entries "Shifts", "Comparison", "Casts" and
  "Uninitialized variables" still exist).
- Lines 166-174: `Headers, "Header equality"` should be `Values and operations,
  "Header equality"`.
- Lines 196-203: `Parsers, "lookahead"` should be `Parsers, "`lookahead<T>`"`.
- Line 209: `Headers, "Reading a field of an invalid header"` should be
  `Expressions`.
- Lines 211 and 213: `Headers, "Writing a field ..."` and `"Assigning a header"`
  should be `Lvalues and assignment`.
- Lines 216 and 218: `Headers, "`setValid` ..."` / `"`setInvalid` ..."` should be
  `Statements and calls`.
- Lines 221, 224 and 227: `Header stacks, "Index out of range"` and
  `"`hs.lastIndex`"` should be `Expressions`.
- Lines 229-236: `Header stacks, "`push_front`"` / `"`pop_front`"` should be
  `Statements and calls, "`push_front(n)`"` / `"`pop_front(n)`"`.
- Lines 280 and 288-294: `Header stacks, "`hs.next`"` should be
  `Lvalues and assignment, "`hs.next`"`.
- Lines 298-303: `Parsers, "`verify`"` should be `Parsers, "`verify(cond, err)`"`.
- Lines 380-402: `Controls, "Block calls"` / `"Action calls"` should be
  `Statements and calls`.
- Line 403: `Controls, "Recursion"` should be `Statements and calls, "Recursion"`.
- Lines 325-329 and 405-407 (`Parsers: ...` sub-parser and fault copy-back) could
  cite `Parsers, "A raised error stops the parser"`.
- Line 384 (`Tables: a table runs an action ...`) could cite
  `Statements and calls, "Action calls"`.
- Line 371 (`Tables: a program's const entry matches`) has no entry; it is the
  Tables intro paragraph.
- The section comments `-- Headers.` (208) and `-- Header stacks.` (220) follow
  the old layout.

## Anything else

- **B1's gate is not met as written.** The plan (`.agents/notes/ir-semantics-plan.md`
  B1) asks for "every closed behavior" to have a tag and for "every ledger entry
  to be hit". There is no mapping from ledger entries to tags, so no test can
  check that.
  - The run-time closed behavior without a tag is **"Copy-back target"**, a
    *deviates* entry. The tag that marks header equality as a deviation misses
    the nested case (defect 3).
  - The other untagged entries are installation-time or validator rules, such as
    "Priority outside ternary tables", "Key expressions", "Entries name their
    action", "Keys are bits", "Errors", "Binding", "Sub-blocks" and "Method call
    order". They need an explicit "not a run-time rule" exclusion if the gate is
    to be literal.
- **`tracesAgree` in `spec/arch/ArchTests/Coverage.lean`** starts the parser from
  zero metadata without `ingress_port`, and the control without `parser_error`.
  It therefore checks the trace functions but not `Coverage.run`'s own
  reconstruction of `Switch.run`'s inputs, lines 110-126. I read that
  reconstruction and it matches `Switch.run` today.
- **Cost.** The observer re-executes every block, so each Lean request runs the
  program twice. This is acceptable for DRT but worth stating, since `Coverage.run`
  is computed even when the caller ignores it.
