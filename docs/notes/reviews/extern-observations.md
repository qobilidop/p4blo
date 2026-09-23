# Extern observation review

2026-09-23. Independent read-only review of `86b3878` in a separate
worktree. 65 non-Lean harness/state checks passed; 12 were deselected.

One confirmed medium-severity finding: decimal encoding and decoding
raise ValueError beyond Python's default 4,300-digit conversion limit.
Widening the register_bounds header fields, register element parameters,
and control local to bit<16384> passed the validator. A packet of 2048 zero
bytes, `80` followed by 2047 zero bytes, and 2048 zero bytes ran successfully,
emitted 6144 bytes and stored a 16384-bit value. Encoding its state failed.

Resolution: canonical hexadecimal values on both sides, without globally
disabling Python's conversion limit. The roundtrip regression now includes
a 16384-bit value; a full wide-register pipe regression covers fake and
Lean peers.

Other probes confirmed missing state is rejected, unsupported adapters and
inconsistent register cell widths fail explicitly, counter-only corruption
diverges without packet changes, and matching errors still compare state.
Reviewer did not rerun Lean or broad oracle gates; integration owns those.
