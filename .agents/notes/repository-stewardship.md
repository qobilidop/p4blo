# Repository stewardship

Documentation ownership refactor, 2026-09-26. Retained maintenance evidence:
implementation and independent review are complete; publication must satisfy
exact-main CI. Compact after publication while preserving unresolved obligations.
Archive/base: `de6aa7d9437ffc65c413b0adda7d3f8c558f84f6`.

## Scope and content map

The approved plan adapts p4-spectec-lean's information ownership without changing
runtime behavior or the existing validation/publication requirements.

| Former duplication or location | Owner after refactor |
|---|---|
| README claim tables, long example narratives and layout | short public introduction; existing Design, Assurance and example guides own detail |
| AGENTS architecture histories and duplicate command lists | Design/Assurance and Workflows; AGENTS retains enforceable policy and navigation |
| Workflows agent/PR/checkpoint rules | AGENTS |
| Assurance duplicate oracle explanations | Oracle Discrepancies; Assurance retains implications and exact proof premises |
| Assurance historical release transcript | immutable baseline permalink, with recovery entry; current release-evidence anchor survives |
| Status milestone log and repeated guarantees | durable Validation Evidence; current guarantees remain in public Assurance |
| Status deferred issues | Roadmap, without promoting observations into confirmed defects |
| Decisions detailed rationale | focused topic notes; Decisions retains cross-cutting choices, reasons and routing |
| Parked proof and worktree-cleanup notes | Recovery, including local-only refs, hashes, branch gaps and restoration procedure |
| Four resolved standalone review reports | original text in archive; outcomes/independence limits in Validation Evidence |
| Future reviews | beside their topic, not a separate activity directory |

The two mutation recipe files stay byte-identical at their existing paths.
No recovery backups, parked branches or source/test/fixture files are removed.
The old `.agents/reviews/` CI allowlist remains useful for historical deletion
diffs; it is not a navigation prescription and does not need a code change.

## Validation and independent review

Integrated public-document revision: `f835bdd675f26960e9c53961211c8e01d11b35ac`.
Integrated decision-register revision: `4b4694523fb8292df5dc70690d19f3e31728d3a2`.
Authors used isolated worktrees with disjoint ownership. Root supplied policy,
state, recovery and skill consolidation. No source, spec, test, native input,
pin, recipe or website behavior changed; the relink helper changes only its
module docstring (executable AST compared equal).

Independent read-only AI-agent review by `minimal_arch_review`, not human review,
approved without confirmed defects. It reviewed the archive plus final patch
SHA-256 `2686db76fab3904c0f4b43db2fad1fccaa88a0729511259160fe5a7cc704c075`.
All 68 original top-level decision entries retain choices, reasons, dates,
uncertainty and revisit triggers in their new owners. AGENTS retains Docker
ownership/no-global-prune, disk-limited reviewed-CI fallback, application acceptance
and usability reviews, and published-history agreement requirements. Proof premises,
unresolved observations, original review limits and recovery boundaries survive.

Reviewer checks: 54 Markdown files' links/anchors/public boundary; 40 retained
Git identities; byte-identical recipes; unchanged helper AST; metadata shape for
both skills; whitespace. Dry-run scenarios preserved narrower/read-only scope,
unresolved review obligations and unique parked work. No heavy/runtime/remote
gates were run by the reviewer; final checkpoint evidence is root's responsibility.

Root validation: both skills passed skill-creator `quick_validate.py` using
ephemeral PyYAML (no dependency change). Required-Lean `scripts/check.sh` exited
0: 5,007 tests passed in 95.72 seconds, no skips/expected failures, plus lint,
format/types/schema/generation/workflow checks. Proof inventory and progress
premises compare byte-identical; the earlier validator-catalog reference was
corrected. All removed files matched the archive before removal; the empty
review directory's absence was verified. The local recovery manifest checksum
matches the retained identity. Native oracle and Lean builds were not rerun
locally for prose changes; their full remote workflows apply to the skill edits.
Baseline CI is linked in Status; publishing revision's Actions runs own the new
remote verdict. No baseline/local pass is presented as that verdict.
