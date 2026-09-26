---
name: compact-agent-state
description: Compact the .agents/ working set at a milestone boundary. Records the archive commit, rewrites status and the decisions register to current truth, promotes artifact-describing notes into docs/, archives finished notes and reviews, and checks the invariants that make compaction safe. Use when a milestone closes or the resume read exceeds its budget.
---

# Compact agent state

`.agents/` is a working set, not an archive: git already keeps every
byte. Compaction rewrites the working set so a fresh agent reads only
what is true now. It never changes a claim.

## When

- A finite scope (milestone, collection) has just been recorded complete
  in `.agents/status.md`.
- The resume read (`status.md`, `decisions.md`, `roadmap.md`, live notes)
  exceeds roughly a thousand lines, or stale plans sit beside live ones.

Do not compact in the middle of active work, and do not compact to make
room for a new scope before the old one is recorded as closed.

## Procedure

1. **Record the archive point.** On a clean working tree, note the full
   hash of the committed pre-compaction `HEAD`; it goes into `status.md`
   as the archive commit and into the compaction commit's body. Follow
   `AGENTS.md` for feature branches, direct commits or a required PR. No tag is
   created: the repository does not tag commits (user's instruction,
   2026-09-24). If status records an unfinished compaction, resume its
   branch and archive point; a same-day archive date alone does not mean
   compaction is still in progress.
2. **Triage every file under `.agents/notes/` and `.agents/reviews/`**
   with one question: does it describe the artifact or the work?
   - A contract, design, survey or release-evidence document that tests,
     source or `docs/` cite is documentation of the artifact. Promote it
     into `docs/` with `git mv` and let links follow. Commit this move on
     its own, before any deletion.
   - A completed plan, step note, review whose findings are fixed, probe,
     or campaign report is history. Delete it.
   - A note that an open thread or a surviving note cites stays.
3. **Rewrite `status.md`** to current state only: one table per finite
   scope with result, revision and evidence; the claims with their status;
   the last checked evidence with commit hashes and CI run links; open
   threads that are parked or backlog; blocked. Target about 150 lines.
4. **Rewrite `decisions.md`** as a topical register of decisions in
   force. Keep each entry's original date. Merge entries that state one
   rule in several increments; remove entries whose subject no longer
   exists or that only sequenced work now landed. Target about 300 lines.
5. **Trim `roadmap.md`** to landed/open per item; move landed detail to
   `docs/assurance.md` if it is not already there.
6. **Fix references.** Links into deleted files become plain mentions
   marked archived; links into promoted files follow them. Path strings in
   tests, docstrings and the website follow too. `scripts/relink.py` in
   this skill does the mechanical part from a moves map and a deleted
   list; it leaves link labels alone and does not see path fragments
   without a slash, so grep for those and fix labels by hand, and restore
   `.agents/reviews/` afterwards so review records keep the paths they
   were written with. `docs/` must not link into `.agents/`;
   `tests/structure/test_docs_links.py` checks both rules.
7. **Commit** the compaction separately from the promotion and cite the
   archive commit's hash in the body. Then run `scripts/check.sh`; Lean and oracle gates are
   unaffected by documentation moves unless a path string in them changed.
8. **Review.** An independent read-only agent compares the new `status.md`
   and `decisions.md` against `git show <archive commit>:...`, claim
   by claim, and reports anything dropped that is still in force or
   reworded into something stronger. Fix findings before pushing. Keep the
   review under `.agents/reviews/` until the next compaction.
9. **Integrate following `AGENTS.md`.** Obtain independent review and run
   the full local gate before pushing. Feature branches are optional;
   integrate completed work into `main` and verify successful applicable
   remote CI on that exact revision before completion.
   Use a PR only when requested or required by repository protections;
   its final revision must pass review and applicable CI before merge.

## Invariants

Compaction is correct only if all of these hold afterwards:

1. Every decision still in force survives with its reason and date.
2. Every claim of current evidence carries a commit hash that resolves.
3. Open threads, parked work and known discrepancies with their reasoning
   survive.
4. Anything a test, source file or `docs/` file references still exists,
   or the reference was updated in the same commit.
5. No claim is stronger than before. Removing and reorganizing is allowed;
   summarizing status into something the evidence does not say is not.
