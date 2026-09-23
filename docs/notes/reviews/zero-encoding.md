# Decimal-zero encoding review

2026-09-23, independent read-only review of `33d5cf1`. No defect found.

Always emitting decimal strings is correct: `"0"` is meaningful data;
omitting it gives protobuf's empty-string default. Numeric defaults such as
zero LPM prefix length are still omitted correctly. The four Lean
regressions cover every affected `ofDecimal` call site.

Independent Nix build, including ProofAudit, passed. Direct Lean JSON to
Python protobuf conversion passed for zero bit literals, LPM values,
ternary values/masks, exact keys and a nonzero literal, without any adapter
normalization. No tracked edits were made; broader tests were not repeated
by the reviewer.
