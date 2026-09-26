# CI efficiency review

Independent read-only AI-agent review by Codex GPT-6 Astra. This is not
human review. Base: `5de0d9e`; integrated revision:
`c573fb8884df0e7fb193cf6bb0081caca1726876`, followed by the four workflow
scope-result guards and new `tests/structure/test_ci_workflows.py` patch
committed with this report.

## Findings and disposition

One confirmed integration defect, fixed before push: the original guard
trusted `full=false` even when the scope job failed later, such as in a
post-step. A failed scope with a retained false output would skip heavy jobs,
contrary to the documented fail-closed policy. All four callers now require
both successful scope completion and literal false output before skipping.
The structural regression replaces the guard with its former unsafe form
and verifies that the boundary check rejects it. The reviewer independently
approved the fix and ran all five tests successfully. No confirmed finding
remains unresolved.

The initial investigation also confirmed that existing module grouping was
ineffective: xdist consumed markers before the ordinary project hook added
them. A real two-worker experiment showed absent group suffixes and duplicated
fixture execution; prioritizing the hook activated groups but serialized cases
that did not consume those fixtures. Removing that grouping preserves the
observed scheduling rather than activating an unmeasured policy.

## Independently checked evidence

- Classifier `771f9d075a23d34cea6b5b3e92b47e7094ec737b`: 69 tests passed.
  Reviewed real Git raw mode/status records, disabled rename detection,
  NUL-separated paths, commit types, PR merge-base/push endpoints, constant
  output, and uncertainty requesting full CI. Heavy-test Markdown readers
  are excluded; remaining link/ledger readers run in Python CI.
- Shards `bc82cc893eafa82f0d33656bce803b4726da8015`: 14 tests passed.
  An additional real-xdist experiment ran two jobs, each with two workers:
  19 and 21 distinct cases formed the exact 40-case expected union. Stable
  hashing, oracle marking, keyword/marker filtering and deselection hooks
  were checked. Invalid options and empty selections remain failures.
- Integrated `c573fb8`: actionlint and `git diff --check` exited 0;
  classifier/shard/boundary tests passed 96 cases. Reviewed complete-history
  checkout and event handling, PR cancellation versus unique main run groups,
  both Lean builds/audits, shard-1-only main saves, separate failure artifacts,
  unchanged case selections/seeds and oracle isolation.
- Final guard patch: five workflow-boundary tests passed independently and
  `git diff --check` exited 0. All four guards handle missing, failed and
  unknown scope results conservatively, unless the whole run is canceled.

The root integrator separately verified that actual Lean collection partitions
as 1,509 + 1,536 = 3,045 with an exact disjoint union. Oracle author measurements
preserved JUnit identities/statuses across 15 serial/2/4-worker runs; the
reviewer inspected fixture isolation but did not repeat these heavy benchmarks.
The full required-Lean local gate before the guard fix passed 5,284 tests,
with one optional XDP-image skip and four expected failures. The integrator
must rerun the full gate on the final patch and obtain successful applicable
remote CI before merging. No remote performance result is claimed here.
