# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order). Updated at every checkpoint.

Last updated: 2026-09-22, after the step 1 checkpoint.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | schema and contract fit in a few pages; no corpus escape hatch | schema 660 lines with comments; forwarder fits; three more programs pending |
| 2. Semantically complete for real programs | four corpus programs match the oracle packet for packet | forwarder 5/5 on P4-SpecTec; others pending |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | filter 45 lines, switch 50, no P4; forwarder runs under both; three programs pending |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT with zero unexplained divergences, one theorem | not started |

## Steps

| Step | What | Status |
|---|---|---|
| 0 | Skeleton: flake, Python project, schema stub, CI, docs | done |
| 1 | Schema, validator, semantics, forwarder in text format, interpreter, STF runner | done: the forwarder's five vectors pass end to end |
| 2 | Extern registry, stateful program | registry landed; stateful program and the forwarder's checksum wait for the eDSL |
| 3 | eDSL, four corpus programs, two architectures, metadata contract | eDSL, architectures and contract landed; forwarder authored in the eDSL; three programs in flight |
| 4 | Printer, v1model shim, P4-SpecTec oracle job, STF replay both sides | printer, oracle build, translation, replay and CI job landed; forwarder passes both sides |
| 5 | Lean interpreter, extern models, DRT, the theorem | Lean project, IR types, JSON decoder and index landed (Lean 4.34.0); interpreter next |
| 6 | Coverage table, README claim matrix, write-up | not started |

## Corpus

| Program | Source | Rewritten | Vectors | Oracle |
|---|---|---|---|---|
| forwarder | p4lang tutorial basic | eDSL source rebuilds the golden; checksum16 computes hdrChecksum, verify deferred | 5 hand-derived STF files with correct IPv4 checksums, passing | 5/5 pass on P4-SpecTec (before the checksum; rerun pending) |
| acl | p4c `ternary2-bmv2` | in flight | p4c STF, 6 adds, 4 packets | pending |
| stacks | p4c `header-stack-ops-bmv2` | eDSL, landed | p4c STF, 15 packets, all passing | 15/15 pass on P4-SpecTec |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | passes on P4-SpecTec |
| stateful | p4c `issue1097-2-bmv2` + own vectors | eDSL, landed; register and counter bound | p4c STF, 2 packets, plus 6 of ours across packets, passing | pending |
| csum16 | p4c `issue655-bmv2` | eDSL, landed; checksum16 bound | p4c STF, 6 packets, passing | pending |
| companions | `parser_error-bmv2`, `issue1824-bmv2`, `table-entries-priority-bmv2` | in flight | p4c STF | pending |

## Blocked

Nothing.
