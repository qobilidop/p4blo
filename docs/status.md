# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order). Updated at every checkpoint.

Last updated: 2026-09-22, after the step 1 checkpoint.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | schema and contract fit in a few pages; no corpus escape hatch | green: ten corpus programs fit with named elaborations only; coverage table published |
| 2. Semantically complete for real programs | four corpus programs match the oracle packet for packet | green: every corpus vector passes on P4-SpecTec (15 files, 10 programs); BMv2 optional second oracle not run |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT with zero unexplained divergences, one theorem | green: Lean interpreter (181 checks); 18,000 random cases over nine programs with zero divergences, 200 per program in CI; theorem `P4blo.extract_emit` proved with core Lean only |

## Steps

| Step | What | Status |
|---|---|---|
| 0 | Skeleton: flake, Python project, schema stub, CI, docs | done |
| 1 | Schema, validator, semantics, forwarder in text format, interpreter, STF runner | done: the forwarder's five vectors pass end to end |
| 2 | Extern registry, stateful program | registry landed; stateful program and the forwarder's checksum wait for the eDSL |
| 3 | eDSL, four corpus programs, two architectures, metadata contract | done: nine programs authored in the eDSL, both architectures, contract check |
| 4 | Printer, v1model shim, P4-SpecTec oracle job, STF replay both sides | printer, oracle build, translation, replay and CI job landed; forwarder passes both sides |
| 5 | Lean interpreter, extern models, DRT, the theorem | done |
| 6 | Coverage table, README claim matrix, write-up | done: coverage table (177 rows, none undecided), README, `docs/writeup.md`; both reviews kept under docs/notes/reviews and their findings fixed |

## Corpus

| Program | Source | Rewritten | Vectors | Oracle |
|---|---|---|---|---|
| forwarder | p4lang tutorial basic | eDSL source rebuilds the golden; checksum16 computes hdrChecksum, verify deferred | 5 hand-derived STF files with correct IPv4 checksums, passing | 5/5 pass on P4-SpecTec, checksum included |
| acl | p4c `ternary2-bmv2` | eDSL, landed | p4c STF, 6 adds, 4 packets, passing | 4/4 pass on P4-SpecTec |
| stacks | p4c `header-stack-ops-bmv2` | eDSL, landed | p4c STF, 15 packets, all passing | 15/15 pass on P4-SpecTec |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | passes on P4-SpecTec |
| stateful | p4c `issue1097-2-bmv2` + own vectors | eDSL, landed; register and counter bound | p4c STF, 2 packets, plus 6 of ours across packets, passing | 8/8 pass on P4-SpecTec |
| csum16 | p4c `issue655-bmv2` | eDSL, landed; checksum16 bound | p4c STF, 6 packets, passing | 6/6 pass on P4-SpecTec |
| parser_error | p4c `parser_error-bmv2` | eDSL, landed | p4c STF, 2 packets, passing | pass on P4-SpecTec |
| verify_error | p4c `issue1824-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | pass on P4-SpecTec |
| priority | p4c `table-entries-priority-bmv2` | eDSL, landed | p4c STF, 3 packets, passing | pass on P4-SpecTec |
| register_bounds | own program from the second review | eDSL, landed | 9 hand-derived packets, passing | pass on P4-SpecTec |

## Blocked

Nothing.
