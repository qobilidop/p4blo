# Stateful program generation review

2026-09-23, independent read-only review of `b6d437b`. No confirmed defect.

Generation preserves widths, extern signatures, packet fields and statement
ordering. Composite strategies rebuild dependent bounds while shrinking.
Both runtimes start fresh and compare every extern cell after each request;
failure artifacts retain the whole sequence and distinguish program/prefix
changes in their filenames.

Clean Lean build and 28 tests passed, including 100 Hypothesis examples and
247 deterministic experiments. Independent fault injection reset a register
before each read: request 1 agreed, request 2 diverged. The saved JSON
reproduced the fault and passed after restoration. Hypothesis shrank it to
an 8-bit, one-cell ADD program with requests `[(0, 1), (0, 0)]`, preserving
validation and the necessary stateful prefix. Protobuf reuse did not alias
the unconditional/conditional count statements or separate programs.

Tracked files remained unchanged; whitespace checks passed. Broad oracle
gates were not repeated. The generator remains bounded to one register and
counter, byte-aligned complete packets, a fixed control structure and empty
host tables. Nested calls, changing tables, parser faults and other extern
families are not covered by this generator.
