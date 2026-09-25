# Review: compaction of `.agents/` after the IR semantics scope

Commit reviewed: `c88a9a6adf90f7019c4433f2fc75278e32368e0a` ("Compact the agent state after the IR semantics scope"), with the promotion commit `97f5df1`. Archive commit: `26c93485861bc5442076a1060fcc8d1743952702`.
Date: 2026-09-25. Reviewer: independent, read-only.

## Summary

The structure is right. The three scopes, the claims table, the open threads, parked proofs, unconfirmed review points and the joint milestone all survive. Every hash cited in `status.md` resolves, and `tests/structure/test_docs_links.py` passes (2 passed). The CI links at `dd491cf` point at that commit and all four report success.

The decisions register fails invariant 1 in several places:

- Two whole entries still in force were dropped.
- One rule that four source files cite by name lost its content.
- One rule that `buf.yaml` cites was dropped.
- The eDSL deviation list now names the wrong fourth deviation.
- One known printer and oracle gap was dropped.
- Many merged entries lost their reasons and revisit triggers.

`status.md` has three problems:

- One wrong evidence claim: the `check-assurance.py` revision.
- One evidence hash is not on any ref.
- Two claims are stronger than the evidence.

The promoted design text contradicts itself: it says "four things" and then gives a table of five rows.

## Dropped decisions

Old line numbers refer to `git show 26c9348:.agents/decisions.md`.

**Still in force and dropped entirely:**

1. *"Existing public APIs may change for demonstrated usability gains."* (old l.95–98, 2026-09-23). It is not in the new register and not in `docs/`. **Restore.**
2. *"Mutation survivors drive generated-program coverage"* (old l.446–454, 2026-09-23). It carries three rules found nowhere else in `docs/` (`git grep` for "mid-sequence", "within one sequence" and "cannot replace" finds nothing):
   - shrinking preserves types;
   - failed programs are retained under `.artifacts/drt/`;
   - host changes within one sequence are Python/Lean-only evidence, because the original BMv2 protocol cannot replace rules mid-sequence, with the trigger "revisit before claiming original-oracle coverage of host changes".

   **Restore**, at least the host-change limitation and its trigger.
3. **Port rules: the ingress half.** Old l.237–240 said "an out-of-range `ingress_port` is the caller's error before anything runs; the filter has no port count". The new merged entry (new l.170–173) keeps only the egress half. Four files cite `.agents/decisions.md, "Port rules"` for exactly the dropped half:
   - `impl/python/p4blo/arch/filter.py:10-12`
   - `impl/python/p4blo/arch/switch.py:9-11`
   - `spec/arch/P4bloArch/Switch.lean:22-23`
   - `spec/arch/P4bloArchTest/Forwarder.lean:118-121`

   **Restore** those two clauses. The same entry also dropped "`parser_error` is written ... before the control" and "the filter forwards the original bytes, so its tests rewrite expectations". `docs/workflows.md:253` sends architecture authors to these rules.
4. **buf's version-suffix lint exception.** Old l.102–103 said it "is excepted rather than renaming to `v1alpha1`". The new l.89 keeps only "pre-1.0 by design". `buf.yaml:8-9` says "see .agents/decisions.md" for this exception. **Restore** the half-sentence.
5. **eDSL deviations.** The old entry (l.175–188) listed four:
   - width aliases and typed literals are places;
   - `Bool`/`Enum`/`Error` have no place split;
   - extern `in` values are checked at run time;
   - **sub-block call arguments are checked at run time.**

   Beside them it noted that `assign` failures surface as `reportCallIssue`. The new l.129–135 drops the sub-block call deviation and counts `reportCallIssue` as the fourth. `impl/python/p4blo/edsl/__init__.py:47-50,84` marks the sub-block call row (*) as one of "the four deviations ... recorded in `.agents/decisions.md`". **Fix the list.**
6. **Known gap: printed const lpm entries carry no priorities** (old l.376–378), so overlapping const lpm entries fail on SpecTec. It still holds: `impl/python/p4blo/printer/program.py:402-420` gives explicit priorities to ternary tables only. It appears nowhere in the new register or in status. **Restore** it in the register, or add it to status as an open thread.

**Kept, but the reason or revisit trigger was lost:**

- **Revisit triggers lost:**
  - devcontainer: Codespaces;
  - register read: "revisit only if a corpus program depends on it";
  - tutorial firewall barrier: "valid for the single-ingress FIFO implementation; revisit before recirculation or asynchronous externs";
  - coverage scope: "revisit when a pin bump changes that cost";
  - block runner: "offer the patch upstream when it stabilizes". The promoted plan's "the two simulator patches are candidates to move to that project" also dropped, so no forward intent for the patches survives anywhere;
  - block runner: the reason entries are refused rather than rewritten ("no corpus program yet needs" the name map);
  - XDP: "a failed upstream snapshot download is not evidence either way";
  - `ExternState`: "confidence high in the boundary", plus the reasons both alternatives were rejected. For the closure, the state-threading conversion is not total. For the type parameter, it is invasive for no gain.
- **Reasons lost:**
  - Python 3.13 / pure Python: "free now and reopening it later is not";
  - p4lang-builds: "the official p4c image is amd64 only and crashed under emulation on ARM". `tests/oracle/bmv2/README.md:74-76` cites decisions.md for this reason;
  - p4c optional: "building p4c is out of proportion";
  - pins: "anyone must be able to reproduce the build";
  - the merged wire-syntax line (new l.90–97) lost every per-item reason: Block tripling the machinery, the golden reading like the program, about twenty fixed operators, annotations doubling the goldens, the printer reversing the dedicated nodes, never needing `getattr`, dotted-path sugar rejected;
  - `int<N>`: no corpus need, doubles the arithmetic rules;
  - decimal strings: protobuf defaults to empty, and Lean's decoder had hidden the defect;
  - parser loop bound: fuel makes meaning depend on an unspecified number, and the rule matches BMv2;
  - "never normative": the earlier wording claimed an authority the evidence does not give;
  - CRC: the known answers and BMv2 confirmation;
  - proof-trust gate: catches imported axioms and native shortcuts, and "checks dependencies, not whether a theorem states the intended property; that is review's job" (a scope limitation);
  - applications: a paired relabeling preserves proofs, hence the asymmetric anchor;
  - p4c backend: "the community version's first job";
  - freezing the architectures: "the project's value is the IR".
- **Coverage-rulings reference is now circular.** The Elaborations entry dropped its enumerated elaborations and its "out by scope" list with their rationale. `docs/p4-spec-coverage.md:311-313` says the rulings on the sixteen formerly open rows "and their reasons are in `.agents/decisions.md`". The register now says they are "named in the coverage table". The coverage table does carry each row's status, but the reasons that lived only in decisions.md are now only in git.
- **Other in-force rules merged away:**
  - "a new external-oracle test must be selected by the job that builds that oracle". This is covered by `docs/workflows.md:58`, so it is acceptable.
  - Observer rules: compare JSON type-sensitively since Python equates false with zero; check copy isolation by branch; demonstrated survivors stay as permanent regressions. These are not in `docs/`.
  - Certificates: bound at the decoded AST; exhaustion is a checker verdict; process-group cleanup fails closed. Partly in `docs/assurance.md` §Execution certificates.
  - Representability includes invalid syntax, and only uint32 fields are bounded.
  - "old raw transcripts are retained before a refactor".
  - "no whole-program validity follows from a body theorem".
  - "selection hit is not a forwarding default".
  - `.agents/`-split enforcement by `tests/structure/test_docs_links.py`.
- **Dates:**
  - The eDSL re-zeroing entry (new l.136–138) is dated 2026-09-25. The rule dates from 2026-09-24 (old l.212–223, "the eDSL must do the same"), and `b89ca45` merged on 2026-09-24 22:59.
  - The website entry lost 2026-09-23.
  - The validity entry adds 2026-09-25, but its follow-ups `789ef4e` merged on 2026-09-24 23:18.
- **A trigger that fired was not answered.** The deviation-theorems entry's trigger ("revisit when a single-block SpecTec runner makes installation observable", old l.559–560) fired when A4 landed. The new entry (l.333–336) dropped the trigger without recording what the revisit decided.
- **The theorem gate changed without a new reason.** "No new application or typed-source-language theorems until the SpecTec IL bridge exists" (old l.429–434) became "unless a scope asks for it" (new l.337–341), under the old dates. The gating condition changed: the bridge exists now. That needs a new date and reason rather than a silent rewrite.

Rightly removed or superseded:

- STF "first oracle / second" ranking;
- the active-scope entry, replaced by the three-frozen-scopes entry;
- the `notes/ir-semantics-plan.md` pointer;
- the first compaction's tag note.

New entries not in the old register are sourced from old status rows D, B2 and gate speed, and are consistent with the code I checked:

- Python organized by concern;
- tests grouped by question;
- `lake build --no-build` stale-binary check (`impl/python/p4blo/conformance.py:547-559`);
- the pair term measured and removed.

## Dropped threads or evidence

Against `git show 26c9348:.agents/status.md` and `roadmap.md`:

- **`check-assurance.py` evidence is inconsistent** (new status l.98–99). It reads "at `b126923`, the `--wfail` change being the last to touch its inputs". But `b126923` is an *ancestor* of the `--wfail` commit `dd491cf`. `dd491cf` changed `tests/assurance/runner.py` (the assurance runner) and the lakefiles, and `git show b126923:scripts/check-assurance.py` has no `wfail`. The run therefore predates the `--wfail` change, and later commits (`3a654b5`, `23bb9c8`) also touched Lean sources under `spec/`. Either cite the revision actually run or say that no `check-assurance.py` run exists after `dd491cf`.
- **Evidence hash not on any ref.** `8f4458d` (new status l.101–102, oracle suites 360 passed / 6 xfailed) resolves locally, but `git branch -a --contains 8f4458d` is empty. It is reflog-only and will not resolve on a fresh clone. `git diff --stat 8f4458d 3a654b5` differs in 13 files, so "whose content `3a654b5` merged" is not exact either.
- **The Lean CI link was omitted.** "CI at `dd491cf`" lists CI, Oracle, BMv2 and XDP. The required Lean workflow run at that commit exists and succeeded (`36109471240`) but is not linked. The runs at `26c9348` have since partly completed: CI, BMv2, XDP and Website succeeded, while Lean `36110812032` and Oracle `36110811991` were still in progress when checked.
- **Evidence for the application collection.** The old status's CI links and local-check evidence at `c94336d` are gone. The table row now cites only `examples/README.md`. That is acceptable only if the milestone evidence is considered recorded elsewhere, and for this scope it is not in `docs/assurance.md`.
- **Threads dropped without landing:**
  - **Status → Verification open items:** "general assignment preservation" appears nowhere now.
  - **Status → XDP:** "an FD-only strict adapter and capability-scoped execution preflight; flowlet time/randomness and Katran profile audits".
  - **Status → claim 2 row:** the "four exact pinned SpecTec discrepancies" from the original-source CRC/mask probes (still in `docs/assurance.md`, but dropped from the claims row; see Stronger claims).
  - **Status → C4:** "not proved: that a non-consuming loop always reaches the revisit check". `docs/assurance.md` still lists it under "Does not establish", and roadmap C2 covers termination, so this one is only lightly lost.
  - **Status → C1 review:** `noAlias` and `writable` are needed only for Python correspondence, not for progress.
  - **Status → printer declaration order:** "the generated control family declares callees first meanwhile".
  - **Roadmap:** "Generated action and sub-block calls ... Open: parser-error copyback and table-invoked actions" (old roadmap l.50–53). It did not land; `docs/assurance.md` covers bounded in/out and aggregate profiles only.
  - **Roadmap disclaimers:** "no exact connection-tracking claim" (firewall), "capability and licensing handling" (xdp-filter), "no whole-Katran or general eBPF-translator claim".
  - **Roadmap → Lean surface:** "Open: notation, if a real application still needs it" (partly kept in decisions).

Surviving correctly:

- the joint milestone;
- C2 and C3;
- printer declaration order;
- the two unhit SpecTec rules (the exclusions file does give the reaching input for each);
- module headers;
- parked proofs and worktree cleanup;
- the three unconfirmed review points;
- interchange items;
- BMv2 `flood`;
- the p4c backend.

## Stronger claims

- **The claim 2 row** (new status l.27) says "every corpus and example vector passes both P4 oracles at the pipeline level except the strict BMv2 register and priority divergences". `docs/assurance.md` §Known disagreements says otherwise. The table-mask defect is observed by "two strict tests ... on the unchanged original firewall and on the printed IR". The printed IR is the `tutorial_firewall` corpus program on SpecTec, and the corpus table says its "CRC and mask defects are classified". So SpecTec also has classified pipeline exceptions. The old row said so, via the "four exact pinned SpecTec discrepancies". Separately, the priority divergence is on p4c's own source, not a corpus vector; the printed golden passes both oracles.
- **"Each item was built by a sub-agent in its own worktree, reviewed independently, and its review's defects fixed on `main`"** (new status l.33–35). The archived reviews cover only ten items: ledger, lean-coverage, spectec-coverage, generated-programs, guided-generation, deviation-theorems, conformance, single-block, il-bridge, validity. No review exists for the D items (Lean layout, Python consolidation, test regrouping), the const-entry priority ruling, the eDSL re-zeroing, copy-back resolution or the gate speed-up.
- **"Every theorem audited on the three standard axioms"** (new status l.68–69). `docs/assurance.md` says the audits check the transitive axioms of *advertised* theorems. Say "every advertised theorem".
- **"BMv2 is the tie-breaker where SpecTec is known wrong (... the shift limit)"** (new decisions l.189–192). `docs/assurance.md` calls the shift limit "a limit of the simulator, not a rule disagreement", handled by keeping amounts in range or classifying the error. Neither there nor in the old entry is BMv2 its tie-breaker. Drop "the shift limit" from that list.

## Broken references

These are all introduced or exposed by the compaction:

- **Four source files cite "Port rules" in `.agents/decisions.md` for a clause that is gone:** `impl/python/p4blo/arch/filter.py:12`, `impl/python/p4blo/arch/switch.py:9`, `spec/arch/P4bloArch/Switch.lean:22`, `spec/arch/P4bloArchTest/Forwarder.lean:118`.
- `buf.yaml:9` cites decisions.md for the lint exception, which was dropped.
- `impl/python/p4blo/edsl/__init__.py:47-50` names "the four deviations ... recorded in `.agents/decisions.md`"; one of them is missing.
- `tests/oracle/bmv2/README.md:74-76` cites decisions.md for the amd64/emulation reason, which was dropped. Its entry title, "p4c and BMv2 from Bili's multi-arch builds", was already stale before this compaction.
- `docs/assurance.md:355-356`: "An independent review of the observer and its fixes are filed under the agent reviews". That review (`2026-09-24-lean-coverage.md`) was deleted, and `.agents/reviews/` no longer exists. It is a plain mention, not a link, so the docs-link test does not see it. Reword it to say that it was reviewed.
- `tests/drt-unhit-tags.json:2` cites "plan item B2". The plan was deleted; name the work instead.
- `AGENTS.md:40-42`: the example `git show <archive commit>:docs/notes/<name>.md` is wrong for the new archive commit. At `26c9348` the notes are under `.agents/notes/`, e.g. `.agents/notes/ir-semantics-plan.md`.
- `.agents/decisions.md:6-8`: "The chronological log up to the last compaction is in git at the archive commit `26c9348`". At that commit decisions.md was already a register; the chronological log is `docs/decisions.md` at `9e8f7d47`. `status.md` l.5–7 gets this right.

Pre-existing, not introduced here: `impl/lean/ASSURANCE.md:595,692,849,871,897,1103` cite `docs/notes/reviews/*.md` paths that have not existed since the first compaction.

## Promotion

`docs/design.md` "Relation to p4-spectec-lean" (from `97f5df1`) matches the archived plan's table row for row: five interfaces, the same formats and the two pending alignments. It has one error. The archived note's "owns exactly four things" meant four ownership areas: the IR and meaning, the elaboration, the block contract and the validation suite. The promoted text says "p4blo owns four things that project consumes" and then gives a **five-row** table. Say "five", or restore the four ownership areas.

Not carried anywhere:

- "the two simulator patches are candidates to move to that project";
- the explicit not-built list's "any decoder of program IL into Lean types";
- the pin dates and branch detail. Status keeps the `8c8e0c6f` / `2730cfd9` pins, which is acceptable.

Nothing in the tree cites the deleted plan or the deleted reviews by file name: `git grep` for `ir-semantics-plan`, `reviews/2026-09-24`, `compaction-2026-09-24`, `docs-consolidation-2026` and `spec-split-2026` finds nothing outside `.agents/status.md`. The two phrase-level references are listed under Broken references (`docs/assurance.md:356`, `tests/drt-unhit-tags.json`). `docs/` does not link into `.agents/`: `tests/structure/test_docs_links.py` passes.

## Anything else

- **AGENTS.md** (item 5): the file table names status, decisions, roadmap, `notes/`, `reviews/` and `skills/`. Every one exists except `.agents/reviews/`, which the compaction removed. It comes back when this report is filed, so this is fine once filed.
  - "`notes/`: ... plans they cite": no plan remains.
  - `.agents/notes/firewall-readback-next.md` is cited only through `parked-proofs.md`, by its old path at `9e8f7d47` (pre-existing).
- **The decisions header** points at `26c9348` for the old log, but the second-previous archive `9e8f7d47` is reachable only through that commit's header. That works, but `status.md` is the only place that names both archives directly.
