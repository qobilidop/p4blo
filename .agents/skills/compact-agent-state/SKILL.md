---
name: compact-agent-state
description: Compact the .agents working set at a closed milestone or oversized resume read. Preserve current choices, obligations and evidence, consolidate by topic, archive completed history in Git, and independently review against the recorded archive commit.
---

# Compact agent state

Keep the resume path small and current. AGENTS owns policy and information
ownership; this skill supplies the preservation procedure. Compaction changes
no semantic claim, authorization or parked-work status.

## When

Use at a completed finite scope or when status, decisions, roadmap and live
notes exceed roughly a thousand lines or contain stale plans. Do not compact
in the middle of active engineering, or hide unfinished work to clear space.
A specifically scoped documentation reorganization can consolidate the closed
work it names while recording its own outstanding review and validation.

## Procedure

1. **Record the archive point.** Start from a clean committed tree; record its
   full HEAD in status, recovery notes and the compaction commit's body. Create
   no tag. Resume an unfinished compaction from its recorded branch/archive;
   a same-day date alone does not identify unfinished work.
2. **Map content to owners before moving files.** Inventory hidden notes,
   embedded/separate topic reviews, skills and checked data. Map each current
   choice, open finding, recovery reference and evidence claim to its retained
   destination. Do not merely relocate an accumulated archive.
   - Promote durable artifact contracts/usage to their existing public owner
     or code. Commit substantive promotions separately before removing sources.
   - Consolidate detailed rationale and review evidence with its topic. Keep
     current reason/date, uncertainty, reviewer identity, reviewed revision,
     independence limits and later resolutions distinct.
   - Archive completed plans and resolved reviews only after useful content is
     preserved and every removed version is recoverable at the archive commit.
   - Retain unresolved/paused work, recovery instructions and machine-consumed
     recipes. Inspect consumers; a move needs a navigation benefit.
3. **Rewrite the entry points.** Status holds the current scope, latest checked
   evidence, immediate obligations and next action, not a milestone history or
   duplicate assurance table. Decisions holds cross-cutting rationale and links
   to topic choices; preserve original dates and supersede explicitly. Roadmap
   holds deferred work and entry conditions. Detailed validation belongs beside
   its topic, with a short reference from status. Prefer a few useful notes to
   many fragments; start with one file per topic.
4. **Repair navigation.** Update links and live references in the same change.
   Use `scripts/relink.py` only when mechanical rewriting helps; it cannot find
   slash-free fragments or path computations. Identify historical-review text
   before running it and restore that text afterwards. Label archived
   paths as historical rather than live links. Do not rewrite original verdicts.
   Check public docs stay independent of `.agents/` and all live consumers still
   resolve. Verify removed files and empty directories by listing their targets.
5. **Validate preservation.** Compare against the archive, not recollection:
   every binding decision/reason/date, current proof premise, open thread,
   known discrepancy and recovery boundary must survive. Every evidence hash
   must resolve; old success must not become a claim about a changed tree.
   New structure must explain how to resume without ignored logs or transcripts.
6. **Review and integrate.** Obtain independent read-only comparison against
   the archive. Record findings and their resolutions beside the maintenance
   topic; fix confirmed losses or stronger claims. Follow AGENTS for commits,
   full local gate before push, and exact-main applicable CI before completion.
   Keep compaction distinct from artifact promotion, cite the archive hash in
   its commit body, and remove finished worktrees after integration checks.

## Invariants

- Every still-binding decision survives with reason/date and revisit conditions.
- Evidence retains exact revision, outcome, scope and reviewer limitations.
- Open obligations, parked work and known discrepancies retain their reasoning.
- A removed source is recoverable and all live consumers are repaired.
- No claim grows stronger; reorganization preserves meaning, not every sentence.
