# Review: B2, coverage-guided generation

Commit reviewed: `5e4aa8e` (merge `6a9e83d` of `work/guided-generation`, plus
the integrator's follow-ups). Date: 2026-09-24. Read-only; scratch scripts
under the reviewer's scratchpad (`rv/`).

## Summary

The families are honest about validity, and the coverage they buy is real.
I generated 5,200 programs across both families and both profiles, including
choosers that always take the first or last option and the extreme bounds.
The validator rejected none, and neither did `arch.load`. For 32 Python
mutants, each aimed at one previously unhit tag, every mutant makes some
retained family case that carries the tag disagree with Lean. So no tag is
hit only on paper. SpecTec regeneration is deterministic and matches the
committed report. Both remaining unhit SpecTec rules fire on hand-written
inputs.

There are two confirmed defects:

- **D1.** The table-mask control model still lets a Python ternary-matching
  bug be classified as a simulator defect when the bug fires only on real
  masks.
- **D2.** `docs/assurance.md` says the guided driver reaches the last unhit
  rule in fewer programs than uniform choice. Nothing records evidence for
  this, and my measurement contradicts it for the control family. Guidance
  shows no measurable benefit over `--unguided`.

## Confirmed defects

### D1. The table-mask classifier hides a Python ternary bug that fires only when mask differs from value

`tests/oracle/generated.py:476` makes the defect model write every ternary
key as `base &&& base`. A Python bug in `key_value_matches` that only runs
when `mask != value` is therefore inert on the model. The control model
(`real_masks=True`, lines 494-509) keeps the real masks, so it reproduces
the buggy real outputs under both tie orders. The control check passes.
The model differs from the buggy real output, and the simulator matches
the model, because the model equals correct Python there. The CLI then
labels the vector `known table-mask` and exits 0. This is the same kind of
hole as the earlier review's D1, reached from the other side: the model
bypasses the code under test by construction.

Reproducer (`rv/tm_cli.py`). The mutant is applied in-process before
`generated.main`:

```python
old = tables.key_value_matches
def kvm(kv, key):
    if kv.WhichOneof("kind") == "ternary" and int(kv.ternary.mask) != int(kv.ternary.value):
        return key.value == int(kv.ternary.value)
    return old(kv, key)
tables.key_value_matches = kvm
sys.exit(generated.main(["--seeds", "605,845,1205", "--out", OUT]))
```

- Without the mutant, all three seeds (`corpus` family, `tests/corpus/acl`)
  pass: 12 of 12 vectors.
- With the mutant, the result is `known table-mask` on 605 case-2, 845
  case-1, and 1205 case-2 and case-3. The CLI exits 0.
- Expected: `fail`.

An offline search over corpus-family seeds below 4,000 found 31 cases where
this bug changes Python's output. Five of them satisfy every precondition of
the classifier.

CI would still fail these seeds, because they are not in `KNOWN`
(`tests/test_oracle_generated.py:42`). The campaign CLI and its summary
would not.

Suggested fix: add a check that does not go through the interpreter's
matcher. Using a few lines of standalone matching over the case's key
values, confirm that the defect changes which entry wins in some applied
table: the winner under `base &&& base` differs from the winner under the
real masks. If the winner is the same, the mask defect cannot explain the
failure, so it stays a failure. Add a unit test with the mutant above next
to `test_the_table_mask_control_model_reproduces_python`.

### D2. The claim "fewer programs than uniform choice" is unsupported

`docs/assurance.md:311-312` says the guided driver "reaches the last unhit
rule in fewer programs than uniform choice". No commit message, status line
or note records such a measurement.

I ran `guided.guided_campaign` for seeds 1 to 8 with a budget of 200 per
family, guided against `guided=False` (`rv/guided_speed.py`, about 3
minutes). "Last new tag" is the sample number of the last first hit.

| family | guided: mean tags / last new tag / pairs | uniform: mean tags / last new tag / pairs |
|---|---|---|
| control | 72.0 / 79.1 / 7,117 | 72.0 / 52.9 / 7,104 |
| parser | 88.1 / 113.0 / 10,020 | 88.4 / 126.4 / 10,096 |

For the control family, guided reaches its last tag later in 6 of 8 seeds.
For the parser family it is slightly earlier but ends with fewer tags and
fewer pairs. A 150-sample run over three seeds per family
(`rv/guided_eval.py`) gave the same picture: uniform found more pairs in 5
of 6 runs.

The likely cause: every target tag is hit within the first few dozen
samples, which switches the target bonus off. After that, the novelty term
credits every feature of a sample with every new pair, so it rewards
whatever happened to be drawn. Either measure the claim and record the
evidence, or change the sentence to what is true: the driver is
deterministic, and its steering is not yet shown to beat uniform choice.

## Validity

- The families never validate programs themselves (`families.py:15-19`).
  The check happens downstream:
  - `compare_program` calls `arch.load`, which calls `validator.check`
    (`run.py:492`, `arch/loader.py:64`). A `ValidationError` propagates:
    - `check()` in `tests/test_drt_families.py:56-74` does not catch it,
      so the test fails.
    - The Hypothesis test fails and shrinks.
    - `guided_campaign` catches only `ProtocolError`
      (`guided.py:182-186`), so the campaign aborts rather than filtering.
  - `tests/oracle/generated.py:629` (`prepare`) calls `arch.load` and
    reports the seed as an `error`.

  Nothing retries or filters.
- `rv/validity.py` generated 500 seeds for each family and profile with
  `RandomChooser`. It also generated 100 programs each with four adversarial
  choosers: always the first option and lower bounds, always the last option
  and upper bounds, upper bounds only, and random options at the bounds.
  Result: 5,200 programs, 0 validator rejections, 0 generator exceptions.
- `rv/load.py` ran 300 seeds for each family and profile through
  `arch.load`: 0 failures.

## Coverage reality

Method (`rv/cache_lean.py` and `rv/mutate.py`):

1. Run the retained family seeds (0 to 199 for both families, `lean`
   profile, 1,600 requests) once on Lean, and keep each reply's outputs and
   tags.
2. For each tag, monkeypatch the Python behavior the tag names, rerun
   Python on the cached cases, and count the cases that carry the tag and
   now disagree with Lean.

A tag whose behavior did not reach an output would show 0.

In the table, "tagged" is the number of cases that carry the tag, and
"killed" is the number of those that disagree under the mutant. The witness
is family, seed, case. In the output column, rK is result byte `hdr.o.rK`,
and r0 is the parser error.

| tag | mutant | tagged / killed | witness | observable effect (Lean vs mutant) |
|---|---|---|---|---|
| call.action, stmt.callAction | action body skipped | 159 / 96 | control 0, 1 | `hdr.h.a` 0x5a vs 0x00 |
| call.action.nested | nested call skipped | 88 / 70 | control 0, 1 | same byte, the inner `^0x5A` lost |
| call.copyIn.overlap | out zero written at copy-in (aliasing) | 161 / 20 | control 0, 1 | 0x5a vs 0x5d |
| expr.equality.header.bothValid | fields ignored | 165 / 54 | control 2, 0 | result byte 2 vs 1 |
| expr.equality.header.validityDiffers | treated as equal | 225 / 184 | control 0, 0 | 1 vs 2 |
| expr.equality.header.bothInvalid | treated as unequal | 263 / 151 | control 7, 3 | result byte |
| expr.equality.header.invalidFieldsDiffer | fields compared | 98 / 60 | control 7, 3 | result byte |
| expr.equality.struct | first field only | 180 / 15 | control 13, 1 | 2 vs 1 |
| expr.equality.stack | element 0 only | 208 / 71 | control 0, 1 | result byte |
| expr.equality.stack.nextIndexDiffers | nextIndex compared | 25 / 10 | control 41, 1 | 1 vs 2 |
| expr.equality.enum | always equal | 200 / 158 | control 1, 1 | 1 vs 2 |
| parser.timeout | raises NoMatch | 42 / 42 | parser 14, 1 | r0 = 6 (ParserTimeout) vs 3 |
| parser.timeout.subparser | revisit check skipped in SP | 33 / 33 | parser 31, 0 | r0 6 vs 3 |
| select.noMatch | accepts instead | 38 / 38 | parser 0, 0 | r0 3 vs 1 |
| select.range | range exclusive of hi | 32 / 7 | parser 77, 0 | different path and emitted bytes |
| select.multiKey | first key only | 169 / 45 | parser 1, 0 | r0 3 vs 1 |
| select.nonBitsKey | non-bits exact matches all | 261 / 81 | parser 0, 0 | different path |
| parser.verify.failNoError | NoError verify does not raise | 16 / 16 | parser 63, 0 | r0 1 vs 2 |
| parser.target.reject, parser.subparser.reject | reject raises NoMatch | 140 / 140, 25 / 25 | parser 3, 0; parser 5, 0 | r0 |
| stack.index.readOutOfRange | clamps to last element | 89 / 16 | control 18, 0 | emitted stack differs |
| stack.index.writeOutOfRange | clamps to last element | 85 / 35 | control 84, 0 | `hdr.s[last]` written |
| stack.lastIndex.empty | 0 instead of 2^32-1 | 62 / 59 | parser 18, 0 | result byte |
| header.setValid.alreadyValid | zeroes fields | 77 / 38 | control 8, 2 | emitted field |
| header.assign.invalid | keeps target validity | 97 / 30 | control 29, 0 | header emitted vs not |
| table.hit.overwritesAction | hit written before the action | 51 / 33 | control 35, 0 | 2 vs 1 |
| table.miss.noAction | miss runs the second action | 99 / 6 | control 101, 1 | 2 vs 1 |
| stmt.advance, parser.advance.tooShort | no-op / no raise | 45 / 37, 16 / 15 | parser 2, 0 | payload and r0 |

Every tag has at least one observable witness. The thinnest are
`table.miss.noAction` (6 of 99; observable only when `table.hit_value=yes`
and no `hit` lvalue) and `select.range` (7 or 11 of 32, depending on the
mutant). One finding concerns a tag not in the list: see "Anything else".

## Guided driver

- **Weighting.** `Guide.weight` (`guided.py:88-95`) matches the docstring
  in shape: a bonus of 4 for an unhit target, plus novelty from a decayed
  average (`Arm.record`, DECAY 0.8). The novelty term is capped at 4 and
  scaled by 1/4, so its maximum is exactly `NOVELTY_BONUS`. The docstring
  (lines 20-21) does not say so. Weights stay in [1, 7].
- **Reproducibility.** `python -m p4blo.drt guided parser 80 --seed 11
  --show-pairs`, run twice, produced byte-identical output. Each run:
  80 programs, 320 requests, 0 disagreed, 87 of 157 tags, 8,408 pairs.
- **`--unguided`.** It uses `rng.choice`, which is uniform, through the
  same per-sample generator (`guided.py:124-125`).
- **Degenerate loops.** None. Across twelve 150-sample campaigns, at most
  2 of 150 programs repeated, guided or uniform alike.
- **Counting.** Wrapping `compare_program` and recomputing tags and pairs
  from each report's `rule_coverage.hits` (Lean's replies) gives exactly
  `guide.tags` and `guide.pairs` in all 12 runs. The driver's counts come
  from the replies, not from its own bookkeeping.
- **Effectiveness.** See D2.

## Classifier

- **The earlier attack.** I ran `tables.beats` patched so that the shortest
  prefix wins, through the CLI (`rv/tm_cli.py shortest 5,3077`):
  - Seed 3077 (tutorial_firewall, the only corpus seed below 4,000 whose
    output the mutant changes) is `fail`. The CLI exits 1.
  - Seed 5 (acl, the `KNOWN` table-mask seed) stays `known`, correctly:
    the mutant does not change its outputs.
- **My own attack.** It succeeds. See D1.

## SpecTec coverage

- **Check.** `nix develop -c uv run python tests/oracle/coverage.py
  --check` exits 0 and reports a match at `2730cfd`. It took 34.3 s wall
  time with the gate running.
- **The 18 seeds.** Two processes with different `PYTHONHASHSEED`
  materialize them to the same hash, `2e88302a14f3a2db`. The report lists
  them in `generated_seeds`, and each appears in `inputs` as
  `generated-NNNNN-<family>` with source `tests/oracle/generated.py seed N`.
- **Spot check of three newly hit rules.** I used ad hoc reports with
  `--inputs` and `--out`: `ParserSelect_eval/no-match` (line 118),
  `ParserTransition_eval/nameIR-reject` (line 168) and
  `Lvalue_read/stack-out-of-bounds` (line 321).
  - A negative program adds a vector to none of the three: select with a
    default, an in-range `hdr.s[1].a = 5`, accept only. Their counts stay
    1, 6 and 3.
  - A positive program adds exactly one vector to each: select without a
    default on a mismatching key, `transition reject`, and
    `hdr.s[3].a = 5` on a size-2 stack. The counts become 2, 7 and 4.
  - Neither input newly hits any other rule.

## Remaining unhit rules

I wrote both inputs by hand (`rv/hand/unhit/`) and ran them through the
probe with `--inputs`. Both fire, so the exclusions' `reach` texts are
right:

- **`Expr_eval/non-default-abort`** (`8.03.1`, line 210) fires with a
  parser that runs `hash(sum, HashAlgorithm.csum16, 16w0,
  { packet.lookahead<bit<8>>() }, 32w65536);` after extracting the only
  byte of a 1-byte packet: hit, 1 vector.
- **`Copy_in_arg/abort`** (inout, `8.10.2`, line 42) fires with a
  sub-parser `SP(packet_in, inout h_t x)`, applied as
  `sp.apply(packet, hdr.s[packet.lookahead<bit<32>>()])` on a packet
  that is too short: hit, 1 vector.

## Sensitivity

I ran `tests/test_drt_families.py` with a pytest plugin that monkeypatches
the Python interpreter (`rv/plug/rvmut.py`):

| mutant | result | caught by |
|---|---|---|
| `push_front` shifts nothing, only moves nextIndex | 2 failed | `test_lean_agrees_on_family_seeds[control]` (eq_stack) and `test_lean_agrees_on_shrinking_family_programs` |
| miss with no default runs the table's parameterless action (the `NoAction` default) | 2 failed | the same two tests (table programs) |
| `push_front` without the nextIndex clamp | 17 passed | nothing; see "Anything else" |

## Cleanup requests

1. **Failure reports say "seed 0".** `tests/test_drt_families.py:59`
   calls `compare_program` without the family seed, so every failure
   message and replay bundle says `seed 0` whatever the seed was. I
   observed this in all 36 bundles from the sensitivity runs. Pass the
   seed, or print it in `pytest.fail`.
2. **Shared decision-point names.** The docstring (`families.py:24-28`)
   says points are named by the enclosing construct, but several points
   are shared across constructs: `validity` and `eq.op` (all four equality
   features), `keyset` and `select.key` (parser and sub-parser),
   `verify.error`, `set_enum.member`. The one-feature-sensitive pairs
   therefore cannot tell `eq_header` from `eq_struct` for `validity=...`.
   Either prefix these points or correct the docstring.
3. **Methods shadow helpers.** `_Control` methods `set_valid`, `call` and
   `table` share names with module helpers, and `_Control.set_valid`'s body
   calls the module's `set_valid` (`families.py:600-611`). The code is
   correct but misleading. Name them `feature_*`, or dispatch through a
   table, rather than `getattr` (line 456).
4. **Novelty docstring.** State the cap and scaling of the novelty term in
   `guided.py`'s docstring (lines 20-21).
5. **Redundant assertion.** `tests/test_drt_coverage.py:256`,
   `assert len(known) <= 0`, is implied by the regression and stale checks
   above it. Assert `known == {}` or drop it.
6. **No SpecTec ceiling.** `tests/test_spectec_coverage.py` puts no ceiling
   on the `unhit` category, while the Lean side has one. Pin it at 2, so
   that new unhit rules cannot be absorbed by adding exclusions.

## Anything else

- **`stack.push.clamp` is hit but not observable.** It is hit, by the
  stacks corpus, but only in controls, where nextIndex is never observable
  afterwards: equality ignores it, `lastIndex` and `extract(hs.next)` are
  parser-only, and nextIndex is not emitted. The no-clamp mutant also
  passes `tests/test_drt.py` (67 passed), `tests/test_corpus.py` and
  `tests/test_conformance.py` (243 passed). `stack.pop.clamp` very likely
  has the same property. This tag, and probably the other clamp and
  oversize tags, is covered only on paper. The families never push or pop
  in a parser, although the IR allows it (`p4blo.proto:390-392`). A parser
  `push`/`pop` followed by `extract(hs.next)` or `lastIndex` would make the
  clamps observable.
- **Duplicate defaults in printed selects.** The parser family prints
  selects with a don't-care case and an explicit default, both as
  `default:`. The simulator accepts this. Note that `select.default=no`
  still allows an all-don't-care case, so it is a weaker path to
  `select.noMatch` than its name suggests.
