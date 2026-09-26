# Test organization refactor

User-authorized 2026-09-25, base `0e553402cddd1f12e5575c114bbee8e4ca8459d4`.
Branch `work/test-organization`. Preserve every existing test responsibility and
all fixture/program answers; this scope reorganizes rather than pruning tests.
Everything under `spec/` must remain byte-identical, including historical path
comments. No semantic implementation changes or new proof scope.

Target ownership:

- `impl/python/tests/`: Python package component checks, grouped by package.
  Outside the installed p4blo package; pytest importlib mode, no ambiguous tests
  package imports. Runtime unit tests require neither Lean nor P4 oracles.
- `tests/conformance/`: codecs, Python/Lean execution, fixed fixtures, rule
  coverage and finite fault campaigns.
- `tests/oracles/`: real P4 oracle suites, drivers, patches and native inputs.
- `tests/programs/`: corpus and public-example intended behavior/assets,
  organized per program. Public canonical sources remain in examples/.
- `tests/repository/`: meaningful generation, import, docs and CI boundaries.
- `tests/support/`: shared generators/catalogues/expected answers, never imports
  from test modules. Do not consolidate independent implementations or answers.

Integrate in coherent steps: mechanical moves/path updates; extract helpers and
split mixed responsibilities; explicit dependency markers and CI selection;
current docs and policy; full validation, independent review, exact-main CI.
Pytest collection must preserve all 5,320 baseline cases modulo recorded moves
and intentional new boundary checks. Compare complete fixtures and requests,
not just counts. Keep all 710 detailed semantic and all independent fault checks.
Explicit lean/spectec/bmv2 markers replace filename-based dependency inference;
unit marker/selection gates ensure no specialist fixture dependency leaks in.

All subagents work in separate worktrees from a committed base, own disjoint
files, and hand off commits with check results. At most two heavy local jobs;
never rebuild root Lean concurrently with consumers. Review each integrated
step independently. Preserve the three unique parked proof branches.

Initial inventory: 413 tracked test-tree files, 92 test modules, 16 immediate
subdirectories, 5,320 collected cases; 2,167 actual Lean fixture dependencies (the legacy name selector also
selected one Python-only guard). Unit folder includes CRC oracle calls; drt mixes runner
unit checks and actual conformance. There are 73 test-module imports in 29
files. Source collection/logs/maps are convenience data in
`.artifacts/test-organization/`; durable conclusions belong here and in status.

Mechanical move checkpoint: all 5,320 cases preserved after mapped paths and
exactly two source-path parameter renames. All 89 fixtures differ only in
source-location labels; requests, programs and answers are unchanged. Full
required-Lean Python/schema gate: 4,798 passed, four expected failures, no
skips; lint/format/types/generated outputs/workflows passed. Independent
review caught the Lean workflow's explicit old root omitting six moved
cases; it now uses configured roots. Mixed suites and markers remain next.

Integrated ownership/selection checkpoint at 43fb881 plus the following marker
commit: retain every original 5,320 collected case, with moved paths and the
sharding selector test renamed from keyword to marker. Add six separately
collected printer compilation cases and five negative/discovery boundary cases:
5,331 total. Markers: 2,167 Lean, 252 P4-SpecTec, 66 BMv2, six p4c; 324 oracle
union, 2,840 ordinary Python CI cases, 1,058 package cases with no native tools.
The two implementation handoffs are e3387d4 and 43fb881. They retain all test
assertions, and the validator scenario catalog preserves all 310 names and
serialized input hashes. Independent review reproduced that comparison.

The first selection guard ran after marker filtering and could miss an orphan
oracle marker. Independent review reproduced the hole; validation now runs in
the collection hook before filtering, with negative regressions for orphan
oracle, extra Lean and missing Lean markers. No filename inference remains.

Local integrated required-Lean scripts/check.sh: 5,007 passed, no skips or
expected failures; formatting, lint, types, schema, generation and actionlint
passed. scripts/check-lean.sh passed both unchanged specification packages.
Initial P4-SpecTec run: 236 passed/15 expected failures; the fresh coverage
check required rebuilding its stale probe after the path move. That rebuild,
coverage rerun and all BMv2/p4c comparisons are in progress. Frozen assurance,
final independent review, exact-main remote CI and closure remain pending.

Final implementation 74a678f: independent review approved all source/test changes
([report](../reviews/test-organization-final.md)). Local gates complete:
5,007 required-Lean Python/schema passes; unchanged Lean packages passed;
237 P4-SpecTec passes/15 exact expected failures (fresh measurement after probe
rebuild); 70 BMv2/p4c passes/two exact expected failures. No skipped cases.
Frozen assurance at 74a678f passed all 28 phases, including ten Python faults,
Lean CRC and paired codec/observer faults and restored baselines. Three input
hashes and six requests remain exactly the baseline. Local evidence under
.artifacts/test-organization and .artifacts/assurance/test-organization-final
is convenience, not handoff state. Next: integrate and check exact-main CI.

Post-integration follow-up: d095104 Python CI rejected three I001 import blocks.
Ruff's local cache had classified tests.support.catalog before that module
existed; adding tests to known-first-party and a clean no-cache check fixes
classification independently of creation order. Three import orderings change.
CI for Lean/oracles is still running; website deployment passed.

Closure triage found three stale paths in live .agents/notes/mutations scripts
(they had been excluded along with historical notes). Independent review also
found two metadata anchors stale since architecture simplification. Both recipes
now use current paths and egress_spec anchors. In isolated worktree d095104,
all ten application source faults and three VLAN faults fail independent Python
and real-Lean expectations; every baseline/restored run passes. The worktree
is restored clean. No core/spec/fixture answers change. Full gate and exact-main
remote CI will cover this follow-up; full assurance need not be repeated for
import ordering and optional recipe edits.
