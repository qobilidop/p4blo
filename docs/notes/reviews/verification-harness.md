# Verification harness review

2026-09-23. Independent read-only agent in its own worktree, reviewing
`9dfce5c`, `06513b2`, `f7cb4af` against `725dc8b`.

## Confirmed findings

1. **High: timeout cleanup could hang on descendant-held pipes.** A peer
   running `import os,time; os.fork(); time.sleep(3)` with timeout 0.1
   returned only after 3.02 seconds. The runner killed the parent but
   `stdout.close()` waited for the worker's stream lock while the child
   retained stdout. A persistent child could hang indefinitely.
2. **Medium: protocol failures bypassed replay saving.** A peer replying
   successfully to request 0 then `not json` to request 1 caused CLI exit
   2 with no files despite `--save`. The report and any earlier divergence
   were discarded before the CLI could save the concrete inputs.

## Resolution

The runner owns a POSIX session and kills its process group on cleanup.
Stream closure never waits on a still-blocked worker. A forked, sleeping
descendant is now a regression test; the worker terminates before return.
Protocol exceptions retain the report and immutable request snapshots;
the CLI saves it before returning failure. Regressions cover a failure
after a prefix, an earlier divergence, mutable protobuf input aliasing,
and startup failure. Saved experiments replay successfully against the
uncorrupted fake comparator.

## Review evidence and limits

Reviewer: 13 new protocol/replay tests passed; 37 existing non-Lean DRT
tests passed; required-Lean missing-binary injection failed rather than
skipping. `git diff --check` passed and tracked review files were unchanged.
The reviewer did not run Lean or oracle gates in this harness-only review.
Root ran the expanded regression tests after implementing the fixes.

## Follow-up adversarial checks

Root found and fixed a further false-green boundary: a peer could return
its last valid reply then exit nonzero, print unsolicited output or hang
at EOF. Normal context exit now requires bounded clean shutdown and
checks all three cases. Concrete-program comparisons, replay and generated
tests share this path, retaining the completed report on shutdown failure.
The initial executable probe uses the same process-group cleanup, rather
than a separate subprocess timeout vulnerable to inherited pipes.
