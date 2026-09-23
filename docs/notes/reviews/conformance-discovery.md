# Required conformance discovery review

2026-09-23, independent read-only review of `36a077a`.

Found one existing omission: `test_lean_states_the_same_reason_as_python`
did not match `-k lean_agrees`. Python CI does not build Lean, so this
malformed-LPM and invalid-ingress comparison skipped there as well.
Collection selected 26 tests without it; explicit execution passed.

Fix: rename it to `test_lean_agrees_on_error_reasons`. The required gate
now discovers it with the other conformance tests. No other exclusion or
skip issue was found in the broader discovery change. The shared fixture
still fails missing/broken executables, and build-before-test is retained.
