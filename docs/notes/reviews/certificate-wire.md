# Certificate wire review

2026-09-23, independent read-only review of `b065681` at `9d2747e`, in an
isolated worktree. No confirmed defect found.

The decoded AST is compared with the fixed example before construction of
the initial machine. Both initial values, budget, completion tag/message,
register width/cells, counter cells and local width/value are bound. All
other initial machine fields come from the fixed constructor.

Validation through Nix: clean build including ProofAudit, 283 Lean checks,
and 58 independent CLI probes passed. Probes covered missing fields,
malformed/noncanonical hex, invalid budgets, altered seeds and observations,
changed arithmetic and extern constructor arguments, and a valid 16,385-bit
counter. Correct claims were accepted; wrong observations mismatched;
insufficient budgets exhausted; malformed envelopes and changed programs
were rejected. The tracked worktree stayed clean.

The documentation correctly limits this to a fixed standalone fragment
and specified observation. Program equality is decoded-AST equality, not
JSON-byte or unrecognized-metadata equality. Decoding, AST comparison,
construction, observation mapping and compiled execution remain outside the
generic checker's proof boundary. The Python producer was not yet reviewed.

Recommendation: retain more of the probe matrix in automated regressions,
especially missing claim fields, malformed budgets, semantic AST changes
and local/counter observation changes. The Python binding suite is the next
place to exercise these cases through the executable boundary.
