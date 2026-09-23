# Generated-program review

2026-09-23. Independent read-only review of `14b7a80`, `25acc5c`,
and `6e8f1cc`, against a freshly rebuilt Lean executable.

47 protocol/replay/state/generated-program tests passed. Generated
contexts make the result header valid, assign the expression and emit it;
empty input avoids payload ambiguity and parser-alignment drops. Shrinking
preserves types and invalid generated programs fail rather than disappear.
An independent in-memory wrapping-add mutation shrank to bit<8>(1) +sat
bit<8>(255). Its saved bundle diverged with the fault and passed after
restoration. Wide-state and prior protocol regressions passed.

One medium-severity finding: CI printed replay paths but did not upload
the bundles. Resolved by a pinned failure-only artifact upload that
includes hidden files and retains them for 14 days.

Limits: pure closed expressions cannot reveal eager evaluation of skipped
branches. Variables, packet reads, aggregates and stateful statement
generation are not covered by this generator. Casts, slices, muxes and
logical negation rely on generated examples in addition to Lean unit tests.
The reviewer did not inspect the concurrent final-process-exit fix or
rerun external oracles. No tracked review files were changed.
