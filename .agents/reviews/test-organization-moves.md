# Mechanical test organization review

Independent read-only AI-agent review by minimal_arch_review on 2026-09-25.
Reviewed staged patch against 614f972, SHA256
238f2a8bddc54eb391b160f19a8b02c8f9b0621fd21a78473bb39cfcdf641fa7,
plus the repaired Lean workflow selector.

Confirmed defect: `pytest tests -k lean_agrees` lost six moved CRC/extern-family
cases. Removing the positional root restores all configured test roots.

Collection retained 5,320 cases and all 2,167 Lean fixture dependencies;
only module paths and two source-path parameter IDs changed. All 89 fixtures
are identical except source-location labels. Assurance's three hashes/six
requests, oracle coverage answers/totals, native P4/STF inputs and patches
are unchanged. spec/ has no diff. Collection and diff whitespace check pass.
No heavy tests run by reviewer; integrator's full required-Lean gate passed
4,798 cases with four expected failures and no skips. Helper extraction,
mixed suite separation and markers are explicitly pending the next step.
