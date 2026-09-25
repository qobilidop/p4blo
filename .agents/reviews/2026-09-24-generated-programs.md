# Review: A1, generated programs on P4-SpecTec

Commit reviewed: `4a3504a` (merge of `42adb60`, `c0845d7`; recorded in
`78c90cf`), files as at HEAD `6724b7f`. Date: 2026-09-24. Read-only
review; all probes ran under the scratchpad against the pinned simulator
at `2730cfd9`.

## Summary

The generator is deterministic, the shift-limit classifier is narrow, the
strict expected failure for the payload difference is tied to the exact
mismatch, and the sixty-seed test passes (132 passed, 5 xfailed, 175 s).
A wrong expectation on a scalar or table program is reported as `fail`.
One confirmed defect: the `table-mask` classifier accepts a divergence
caused by a Python bug in longest-prefix selection. It checks that the
simulator matches the defect model, but not that the model's rewrite
(lpm to ternary, re-ranked priorities) leaves Python's own result
unchanged when the masks are correct. So the claim "accept exactly the
known table-mask defect and nothing else" does not hold. The two
table-mask seeds from the campaign (467, 1067) still hold up under the
proposed tighter check. Coverage gaps: the CI seed set leaves out 11 of
19 binary operators and every bool scalar. Three of the six families send
four copies of the same computation. The nightly run the plan called for
does not exist.

## Confirmed defects

### D1. `table-mask` classifies a Python lpm bug as a simulator defect

`tests/oracle/generated.py:526-562` (`explained_by_table_mask`) classifies
a failed vector when three things hold: the defect model's outputs differ
from the real ones, the model does not depend on how ties are broken, and
the simulator passes the vector rewritten with the model's expectations.
But the model does more than swap mask for base. It also turns every lpm
key into a ternary key and ranks entries by priority (`table_mask_model`,
lines 485-522). Those steps take Python down a different path: ternary
`key_value_matches` and `beats` by priority. Python's lpm matching and
longest-prefix selection (`impl/python/p4blo/interp/tables.py:232-247`)
never run on the model. If Python is wrong on the lpm path and the mask
defect is not involved, the model still differs from the original, the
simulator (correct here) matches the model, and the vector is labelled
`known table-mask`.

Reproducer: `scratchpad/adv/probe.py`. It patches
`p4blo.interp.tables.beats` in-process so that the shortest prefix wins
on tables without a ternary key, then runs the forwarder with
`lpm_precedence.stf`'s two entries and its first packet through
`generated.run_generated`.

```
cd /Users/qobilidop/my/work/p4blo
nix develop -c uv run python <scratchpad>/adv/probe.py lpm-mutant  <scratchpad>/adv/out-lpm-mutant
nix develop -c uv run python <scratchpad>/adv/probe.py lpm-control <scratchpad>/adv/out-lpm-control
```

Observed with the mutant: `status known`, `known table-mask case-0.stf:
error: [FAIL] Remaining packets to be matched`, so the CLI exits 0.
Expected: `fail`. The /24 entry covers the packet under the real mask and
under the defective one alike, so the mask defect plays no part. Control
without the mutant: `pass`.

Effect: the CI test still fails such a seed, because it is not in `KNOWN`
(`tests/test_oracle_generated.py:225`). The report, though, calls it a
"classified defect" and not a divergence. The CLI and the campaign count
it as `known` and exit 0. The claim in `docs/assurance.md:276-278` and
`tests/oracle/README.md:296-307` is therefore broader than the code.

Fix: also build a control model with the same rewrite and ranking but
each key's real mask (lpm `value/len` as ternary `value &&& prefixmask`,
ternary keys unchanged). Classify only if the control reproduces the
original outputs under both tie orders. The difference is then
attributable to the mask alone. I implemented that check in
`scratchpad/adv/tm_seeds.py` (`control_model`). It rejects the mutant
(`control==original False`). It accepts both campaign table-mask seeds:
seed 467 (`priority`, case-2) and seed 1067 (`acl`, case-2) both give
`control==original: [True, True]`. Add a no-oracle unit test that
patches `beats` and checks that the classifier refuses before it runs the
simulator.

## Classifier analysis

- **Wrong expectations are reported.** With `generated.expectation`
  patched to corrupt the last expected byte and `self_check` disabled:
  seed 1 (parser_condition) gives `fail` on all four vectors, and the
  forwarder table program gives `fail` with `MODELLED {}`. The table-mask
  path recomputes outputs from Python and does not read the vector's
  expect lines, so a corrupted expectation on a table program cannot be
  explained away (`probe.py wrong-scalar`, `wrong-table`).
- **`shift-limit`** (`generated.py:421-443`) is narrow. It requires status
  `error`, exactly one `error:` line from `V1Model_ingress` or
  `V1Model_parser`, a `function bin_shl|bin_shr failed` frame, and a last
  line of exactly `shift amount too large`. The message comes only from
  `$shl`, `$shr` and `$shr_arith` in `numerics.ml:51,68,88`, each guarded
  by `offset > max_bit_width`. A mismatch earlier in the same vector adds
  a second `error:` line and is rejected, and the unit test covers that
  (`test_oracle_generated.py:152-159`). I could not make a wrong
  expectation slip through except in the way the design intends: the
  shifted case is not judged at all. That is the documented meaning of
  `known`.
  - Minor: `any(line in lines …)` checks that the `bin_shl` frame is
    present, not that it is the direct parent of the builtin. A `$shl`
    reached from a nested helper under `bin_shl` would also qualify. At
    this pin that path does not exist.
- **`table-mask` against the documented defect.** The rewrite in
  `table_mask_model` (value = mask = the base; for lpm the base is the
  value under the prefix mask; ternary base is `value & mask`) matches
  `9.1-table-interface.watsup:157-275`, where every ternary and lpm branch
  builds `typedExpressionIR_mask_cast` from `typedExpressionIR_base`. Exact
  keys are untouched, as in the exact branch. The model runs only on
  `fail` verdicts of non-sequence vectors (`generated.py:671-676`), is
  rejected when its outputs equal the real ones (line 553), and requires
  the simulator to pass a vector with the unchanged `add` lines and packet
  and the model's expectations (lines 556-562). All three steps match the
  README. The gap is D1. Two smaller notes: the model is not self-checked
  against its own rewritten vector, which is harmless because Python
  produced it; and there is no unit test for the rejection branches
  (tie-dependent model, model equal to original).
- **Strict expected failure for the payload** (`test_oracle_generated.py:262-278`).
  It raises `KnownDeviation` only on `fail` with `brief(detail)` equal to
  the exact string `expected (0) 2CABCD but got (0) 2D579A`, which I
  rederived: 0010110 followed by abcd at the bit level is 2D 57 9A. If the
  simulator padded to a byte, the vector would pass,
  `assert result.status == "pass"` would hold, and strict xfail would
  report XPASS. An error or a different mismatch raises `AssertionError`,
  which `raises=KnownDeviation` turns into a failure. Correct.
- **`KNOWN` handling** (`test_oracle_generated.py:215-227`). A listed seed
  raises the expected exception only when every non-pass has exactly the
  listed defect. A new failure on a listed seed, or a classified defect on
  an unlisted seed, fails. Correct.

## Family coverage gaps

Measured with `scratchpad/adv/cover.py` over seeds 0-1099 and 0-59:

- **CI seed set (0-59).** Scalar and parser expressions together never
  produce ADD, SUB_SAT, BIT_AND, BIT_OR, BIT_XOR, SHR, EQ, NE, LE, GE or
  AND, which is 11 of 19 binary operators. SHR runs only in the two probe
  tests. No bool `scalar` seed appears (10 bit-typed seeds, 2 of them
  xfail on shift-limit). The `corpus` family reaches 7 of 15 programs.
  "Every binary and unary operator" holds only for the local campaign,
  not for CI.
- **Over 1,100 seeds.** Every operator appears, but EQ never appears in
  the `scalar` family (0 of 184 seeds). It shows up only in parser
  conditions (7). Bool scalars are 19 of 184.
- **Leaves.** Scalar and parser expressions use only literals and (in
  parser conditions) `lookahead`. They never contain `var`, `member`,
  `index`, `last_index` or `is_valid`. No cast goes from bool to bits
  inside an expression (only the top-level wrapper for bool results), and
  no cast goes from bits to bool except from `bit<1>`.
- **Lookahead.** 63 of 184 parser_condition seeds (34%) contain no
  `lookahead` leaf at all.
- **Repeated cases.** In `scalar`, `aggregate_copy` and `call_copy`, all
  four cases of every program (50 of 50 checked each, seeds 0-299)
  produce the same emitted prefix. Only the appended payload differs,
  because the result depends on constants and not on the packet. About
  1,650 of the campaign's 3,851 vectors therefore repeat one computation
  per program. The vector count overstates independent checks. Use one
  case for these families, or say so next to the count.
- **Shift limit.** WIDTHS reaches 127-bit shift amounts drawn uniformly,
  so 47 of 368 scalar and parser programs (13%) are unjudged. Biasing
  shift-amount leaves toward values ≤ 2048 (edges plus small values)
  would recover most of them without hiding the defect, which the two
  boundary probes already pin.
- **Stateful, aggregate_copy, call_copy, corpus.** The samplers reach
  every documented option: all five update operators, three conditions,
  three write orders, both flags, 2-16 requests; header and struct at
  every width with both validity states; action and block at 8, 9 and 65
  bits; all 15 corpus and example programs. Entries appear in 332 of 732
  corpus cases.

## Cleanup requests

- `generated.py:143-217` re-implements the Hypothesis `scalar` strategy
  of `tests/test_drt_programs.py:48-110`. `WIDTHS`, `ARITHMETIC` and
  `COMPARISONS` are copied (lines 97-117), tied only by a comment. The two
  will drift. Share the constants from one module and state in the
  docstring that `Scalars` also adds `lookahead` leaves.
- `docs/assurance.md:274-278` says the classifier checks "that the
  simulator agrees with the corrected model". The model reproduces the
  defect; it is not a corrected model. Suggested wording: "…agrees with a
  model of the defect".
- `docs/assurance.md:267-279` does not say that the generated comparison
  is Python against SpecTec, and that Lean is not consulted
  (`generated.py` calls only `python_outcome`; I confirmed that no Lean
  call exists). The README says it ("the simulator matched Python"), but
  a reader of the assurance page could assume SpecTec judges Lean. Add
  one sentence: expectations come from the Python interpreter, and
  Python-versus-Lean agreement is the differential tests' job.
- `generated.py:526-531`: `explained_by_table_mask` annotates with
  `Prepared`, which is defined 100 lines later (line 629). This works
  only because of `from __future__ import annotations`. Move `Prepared`
  above the defect section. `__all__` lists `prepare` but not `Prepared`.
- `generated.py:421-431`: `known_defect` documents only `shift-limit`,
  while `table-mask` is attached through `Result.modelled`. One sentence
  saying where the second classifier lives would help.
- `generated.py:5-6`: "the differential tests against Lean change the
  program itself" is unclear. Presumably it means that they vary the
  program and not only the packets.
- Plan A1's gate asked for "a new job in the oracle workflow with a fixed
  seed set and a nightly larger run". The build added a step to the
  existing job (`.github/workflows/oracle.yml:223-224`) and no schedule,
  and `.agents/decisions.md` records no decision replacing the nightly
  run. Either add a scheduled workflow for, say, `--seeds 0:1100`, or
  record the decision.

## Anything else

- Determinism: 300 seeds prepared in two processes with
  `PYTHONHASHSEED=1` and `987` are byte-identical (`diff -r`, 1,050
  vectors). Two CLI runs of `--seeds 0:20` gave identical inputs and
  verdicts (paths aside), exit 0 both times: 19 pass, 1 known (seed 0,
  shift-limit), 55 s.
- CI shape: `tests/test_oracle_generated.py` took 175 s for 132 passed
  and 5 xfailed. Another oracle process was sometimes running at the same
  time, so this is an upper bound; the docstring's "about three minutes"
  holds. Test ids name the seed and family (`[53-corpus]`), and a failure
  message carries the seed, family, description, the per-vector brief and
  the inputs directory. That directory is `tmp_path` and CI does not
  upload it, but `--seeds N` reproduces it locally and deterministically.
- As in `tests/test_oracle.py`, a missing simulator makes the oracle tests
  skip, not fail. In CI the build step fails first, so this matters only
  if the build succeeds with an incomplete checkout.
- Scratch artifacts: `<scratchpad>/adv/` (probe.py, cover.py, prep.py,
  tm_seeds.py, cover.txt), `<scratchpad>/tm.log`,
  `<scratchpad>/pytest-gen.log`, and `<scratchpad>` =
  `/private/tmp/claude-501/-Users-qobilidop-my-work-p4blo/e93494d7-08c2-4eba-aaee-42e2dc9e2062/scratchpad`.
