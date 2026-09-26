# Test organization final review

Independent read-only AI-agent review by minimal_arch_review, 2026-09-25.
Reviewed 43fb881 plus staged patch SHA256
7da977a07f4ac77b394155532ce2200460568ece45c059425652aeb1ffbf9b05,
committed as 74a678f with checkpoint prose. Approved; no remaining confirmed defect.

All 5,320 original test/function-parameter identities survive after documented
moves, two source-path parameters and the sharding-test rename. Eleven additions
are six separate printer compilations and five boundary checks. Collection:
5,331 cases; 2,167 Lean, 252 P4-SpecTec, 66 BMv2, six p4c; 2,840 ordinary Python.
All 1,058 package cases have no specialist dependency.

Reconstructed the old validator capture at f6763af and compared the new explicit
scenario catalog: all 310 names and deterministic protobuf hashes match. All
89 validator test functions retain assertion counts. Inspected independent
expectations and assertions survive helper extraction. BMv2 verdict checking
moved intact; its strict-discrepancy regression exercises the extracted helper.
All 89 conformance fixtures are identical except source-location labels;
assurance hashes, six requests and baseline known answers remain unchanged.

Confirmed/fixed selection defect: a guard examining session.items after marker
filtering missed orphan oracle and extra Lean markers. An isolated reproducer
passed while deselecting both bad cases. The collection hook now validates
before deselection. Nineteen shard/import/marker boundary tests independently
pass, including negative regressions. spec/ has no diff; diff whitespace checks
pass. No heavy/native or remote gates were independently run by the reviewer.

Integrator validation on implementation 74a678f (unchanged code from reviewed
patch): full required-Lean Python/schema gate 5,007 passes, no skips/xfails;
Lean package build/audit/tests passed. P4-SpecTec 236 passes/15 exact xfails,
then its stale local coverage probe was rebuilt and the fresh measurement
passed (237 passes total). BMv2/p4c 70 passes/two exact xfails, no skips.
Frozen assurance at 74a678f passed all 28 phases with unchanged three input
hashes/six requests. Remote validation is recorded separately in status.
