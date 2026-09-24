# Review: agent-state compaction against `agents-archive/2026-09-24`

Independent read-only review of commits e98141a..5d0f51b (4 commits,
257 files, +977/-29302), 2026-09-24. Compared `.agents/{status,decisions,
roadmap}.md` and the trimmed `docs/{verification,examples,milestone-1}.md`
against the tagged originals and checked every path the new files name.
All findings below were fixed in the follow-up commit that adds this file.

## Blocking (1)

**B1. Dropped in-force decision: "eDSL v2 as implemented deviates from the
note in four places" (2026-09-22).** The old log recorded the public eDSL's
static/run-time boundary (`bitN` aliases and typed literals type as places;
`Bool`/`Enum`/`Error` targets have no static place split; extern `in`
parameters accept any `Val` with run-time width check; sub-block call
arguments are run-time checked; failed `assign` reports as
`reportCallIssue`). None of it was in the register, yet
`docs/edsl-v2-design.md:5` (since archived) points at the register for the deviations. The
eDSL is unchanged, so the decision is load-bearing. Fixed: new "Python
eDSL" section in the register.

## Minor

- **M1.** Register said the archived log is at `.agents/decisions.md` in
  the tag; it is `docs/decisions.md`. Fixed.
- **M2.** "P4-SpecTec pinned and translated" lost its known gap: printed
  const lpm entries carry no priorities, still true of
  `python/p4blo/printer.py` and `tests/oracle/run.py`. Restored.
- **M3.** The generated host-policy campaign lost its revisit trigger:
  original BMv2 cannot replace rules mid-sequence. Restored.
- **M4.** Two STF dialect rules were dropped (priority on a non-ternary
  table is an error; lpm key without `/n` is full-width). Restored.
- **M5.** `.agents/notes/parked-proofs.md` cited `forwarder-apply.md` "on
  main" after its deletion. Now names the archive command.
- **M6.** Stale backticked paths in `docs/semantics.md` and
  `docs/milestone-1.md`; deleted reviews named without the archived marker
  in `docs/milestone-1.md`, `docs/website-design.md`, `docs/writeup.md`,
  `docs/evidence/milestone-adversarial.md`; stale link text in
  `docs/design.md`. Fixed. (Paths as they were on 2026-09-24; the later
  documentation consolidation archived several of these files.)
- **M7.** `.agents/reviews/` did not exist. Created by this file.
- **M8.** Status claim 2 read as if the four SpecTec discrepancies were
  corpus vectors; the "separate probes" qualifier is restored.

## Verified as consistent

Revisions `3148a52`, `c94336d`, `38d740e`; counts 4837/1 skip/5 xfail, 17
example tests, ten source faults, six CI run ids; twelve corpus
directories; five non-main worktrees. Register dates spot-checked against
the old log. Roadmap landed/open lists match the old roadmap and open
threads. No strengthened claim found. Superseded entries (two testing
directories, the single extract-emit theorem, `P4bloLean`, eDSL proposal
and acceptance, discussion-only instructions) correctly removed. Every
other named path resolves.

Verdict before fixes: 1 blocking, 8 minor. After fixes: clear.
