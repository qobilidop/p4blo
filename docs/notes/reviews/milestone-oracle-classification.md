# BMv2 discrepancy classification review

2026-09-23. Independent integrator review: **CLEAR**.

The old strict expected-failure marker accepted any test failure on the
register-bounds vector, including an oracle execution error. The reviewed
change permits only a dedicated exception after matching the exact vector,
semantic-failure status and the two complete documented output mismatches.
All other results retain the ordinary error/divergence paths. A corrected
oracle returns normally and therefore produces strict XPASS, not a hidden
pass. No oracle driver, image, input, implementation or semantic rule changes.

Read the full patch and independently ran all fifteen new classifier/marker
regressions: exit 0, 15 passed / 22 deselected. The four nested pytest checks
exercise the actual marker: the exact discrepancy is expected, changed
mismatch and oracle error fail, and corrected output fails as strict XPASS.
Their subprocess environment removes inherited PYTEST_ADDOPTS and is bounded.
The other controls reject wrong vector/status, missing/additional/reordered
diagnostics and changed output bytes.

Independently ran the actual register-bounds vector on the existing immutable
BMv2 image: exit 0, one precisely classified expected discrepancy, no skips.
Logs: `/tmp/p4blo-milestone-bmv2-independent.log` and
`/tmp/p4blo-milestone-bmv2-independent-live.log`. The owner's separate complete
module run reports 36 passed / one exact expected discrepancy, no skips.
Main owns combined clean-checkout acceptance. This review closes a concrete
false-pass risk; it does not establish every oracle adapter's correctness.
