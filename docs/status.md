# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order). Updated at every checkpoint.

Last updated: 2026-09-22.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | schema and contract fit in a few pages; no corpus escape hatch | not started |
| 2. Semantically complete for real programs | four corpus programs match the oracle packet for packet | not started |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | not started |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT with zero unexplained divergences, one theorem | not started |

## Steps

| Step | What | Status |
|---|---|---|
| 0 | Skeleton: flake, Python project, schema stub, CI, docs | done |
| 1 | Schema, validator, semantics, forwarder in text format, interpreter, STF runner | not started |
| 2 | Extern registry, stateful program | not started |
| 3 | eDSL, four corpus programs, two architectures, metadata contract | not started |
| 4 | Printer, v1model shim, P4-SpecTec oracle job, STF replay both sides | not started |
| 5 | Lean interpreter, extern models, DRT, the theorem | not started |
| 6 | Coverage table, README claim matrix, write-up | not started |

## Corpus

| Program | Source | Rewritten | Vectors | Oracle |
|---|---|---|---|---|
| forwarder | p4lang tutorial basic | no | hand-written, pending | pending |
| acl | to be picked from p4c testdata | no | | |
| stacks (MPLS or VLAN) | to be picked from p4c testdata | no | | |
| stateful (register) | to be picked from p4c testdata | no | | |

## Blocked

Nothing.
