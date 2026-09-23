# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order), and what is open. Updated at every
checkpoint. To resume the work, read this, then
[decisions.md](decisions.md), then [workflows.md](workflows.md).

Last updated: 2026-09-23, after the eDSL v2 review's findings were
fixed. Every claim is green and every step of the design's build order
is done; what remains is in "Open threads".

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | schema and contract fit in a few pages; no corpus escape hatch | green: ten corpus programs fit with named elaborations only; coverage table published |
| 2. Semantically complete for real programs | four corpus programs match the oracle packet for packet | green: every corpus vector passes on P4-SpecTec and on BMv2 (15 files, 10 programs), with one recorded divergence on an out-of-range register read |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT with zero unexplained divergences, one theorem | green: Lean interpreter (181 checks); 18,000 random cases with zero divergences, 200 per program in CI over all ten; theorem `P4blo.extract_emit` proved with core Lean only |

## Steps

| Step | What | Status |
|---|---|---|
| 0 | Skeleton: flake, Python project, schema stub, CI, docs | done |
| 1 | Schema, validator, semantics, forwarder in text format, interpreter, STF runner | done: the forwarder's five vectors pass end to end |
| 2 | Extern registry, stateful program | done: registry with register, counter and checksum16; the stateful program and the forwarder's checksum |
| 3 | eDSL, four corpus programs, two architectures, metadata contract | done: ten programs in the typed eDSL, both architectures, contract check |
| 4 | Printer, v1model shim, P4-SpecTec oracle job, STF replay both sides | done: every program passes on both oracles, each with its own CI job |
| 5 | Lean interpreter, extern models, DRT, the theorem | done |
| 6 | Coverage table, README claim matrix, write-up | done: coverage table (177 rows, none undecided), README, `docs/writeup.md`; both reviews kept under docs/notes/reviews and their findings fixed |

## Corpus

| Program | Source | Rewritten | Vectors | Oracle |
|---|---|---|---|---|
| forwarder | p4lang tutorial basic | eDSL source rebuilds the golden; checksum16 computes hdrChecksum, verify deferred | 5 hand-derived STF files with correct IPv4 checksums, passing | 5/5 pass on both oracles, checksum included |
| acl | p4c `ternary2-bmv2` | eDSL, landed | p4c STF, 6 adds, 4 packets, passing | 4/4 pass on both oracles |
| stacks | p4c `header-stack-ops-bmv2` | eDSL, landed | p4c STF, 15 packets, all passing | 15/15 pass on both oracles |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | passes on both oracles |
| stateful | p4c `issue1097-2-bmv2` + own vectors | eDSL, landed; register and counter bound | p4c STF, 2 packets, plus 6 of ours across packets, passing | 8/8 pass on both oracles |
| csum16 | p4c `issue655-bmv2` | eDSL, landed; checksum16 bound | p4c STF, 6 packets, passing | 6/6 pass on both oracles |
| parser_error | p4c `parser_error-bmv2` | eDSL, landed | p4c STF, 2 packets, passing | pass on both oracles |
| verify_error | p4c `issue1824-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | pass on both oracles |
| priority | p4c `table-entries-priority-bmv2` | eDSL, landed | p4c STF, 3 packets, passing | pass on both oracles |
| register_bounds | own program from the second review | eDSL, landed | 9 hand-derived packets, passing | passes on P4-SpecTec; two packets diverge on BMv2 by the recorded out-of-range register rule, carried as a strict xfail |

## Open threads

Things a resuming agent should know are in motion or deliberately left.

- **eDSL v2: done** (2026-09-22, reviewed and fixed 2026-09-23). The
  typed surface is `p4blo.edsl`, the v1 builder is `p4blo.edsl.core`;
  all ten corpus programs are authored in v2 with byte-identical
  goldens, type-checked in CI; `tests/test_pyright.py` guards the
  static rules with must-pass and must-fail fixtures. The review is
  `notes/reviews/edsl-v2.md` and every finding is fixed.
- **BMv2 as a second oracle: done** (`oracle/bmv2/`, its own CI job). It
  decides longest prefix, const-entry and ternary priorities without the
  translation P4-SpecTec needs. It cannot see `flood`, which no corpus
  program declares; a program that does would be the way to test it.
- **Playground** (Pyodide/marimo) was removed from the plan on
  2026-09-22; the pure-Python and Python 3.13 constraints keep it
  possible.
- **Unconfirmed review points left open**, from
  `notes/reviews/steps2-5.md`: checksum16 padding for data widths not
  a multiple of 16 has not been judged by the oracle; sub-block
  instance names `<block>_inst` are not checked against the caller's
  scope; a case with both a bad entry and a bad port reports different
  first errors on Python and Lean.
- **Three type checkers** compute expression types: the validator,
  `interp/widths.py`, and the printer's `_Typer`; they must agree, and
  one would do. The typed eDSL is a fourth, at a different level.
- **The next substantial thing** the design names is a p4c backend, so
  that p4c's whole test suite becomes the corpus. It is the community
  version's first job and the experiment that would really test claim 1;
  `docs/writeup.md` section 5 and 4ward are the route.
- **Elaborated-but-unexercised rows** of `coverage.md` (functions,
  newtypes, constructor parameters, named arguments) are rulings, not
  performed rewrites; a p4c backend is the experiment that would test
  them.

## Blocked

Nothing.
