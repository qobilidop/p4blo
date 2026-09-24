# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order), and what is open. Updated at every
checkpoint. To resume the work, read this, then
[decisions.md](decisions.md), then [workflows.md](workflows.md).

Last updated: 2026-09-24. The accepted Python/Lean architecture and bounded
assurance milestone 1 are complete. Broader research remains backlog;
[verification.md](verification.md) is not an open-ended release requirement.
The active new workstream is the three Python application examples in
[examples.md](examples.md); the user authorized autonomous implementation.

## Latest checked checkpoint

**Three-application integration (2026-09-24).** Router, firewall and UDP load
balancer now live under `examples/`, each with source, README and runnable demo.
The load-balancer [review](notes/reviews/example-load-balancer.md) requested a
group-zero backend/service-miss regression; it is added and catches an actual
guard-bypass fault in both interpreters. Its final sequence has 111 independent
requests. All three applications have clean independent reviews and source
fault campaigns with passing restored baselines (three router faults, three
firewall faults, four load-balancer faults). The eDSL and interpreter semantics
needed no changes. Shared discovery, typing, exact vector checks and oracle
inventory guards are the reusable engineering improvements from this work.
An additional reviewed fidelity pass gives the firewall demo valid TCP checksums
and SYN-ACK acknowledgment, with a test of the actual packet fixtures; eight
focused firewall tests pass and the program/STF remain unchanged.
Next: combined full gates and final evidence/cleanup; do not count completion
until the remaining checkbox in [examples.md](examples.md) is satisfied.

**Firewall integration (2026-09-24).** Candidate `f874b6f` adds the public
exact-pinhole TCP filter. Independent [review](notes/reviews/example-firewall.md)
has no confirmed defects. Its 890-request sequence checks packets and all
sixteen cells in both interpreters; both real P4 oracles pass its exact
nine-packet vector. Author focused checks: 12 passed, full Ruff/Pyright pass.
Three isolated program faults each fail both expected-answer tests, with
passing baseline/restoration. Shared source/test interfaces are committed at
`ca6ab6b`. Next: integrate the load balancer and the review-requested group-zero
miss regression, then run collection-wide acceptance and final gates.

**Router implementation (2026-09-24, checked).** The first
public application is in `examples/router/`, with separate verification in
`tests/examples/router/`. Its guarded fixed-header IPv4 contract is documented
in the README. Shared discovery checks goldens, exact vectors, demo output
and generated Lean comparisons; Pyright and both oracle catalogs now include
public examples. Existing upstream corpus contracts are unchanged.

Independent [review](notes/reviews/example-router.md) has no confirmed defects.
Both Lean packages/audits pass (`nix develop -c scripts/check-lean.sh`), as do
all 10 selected router/discovery/oracle tests, including both actual oracles.
Sixty independent packet outcomes run under Python and Lean. Three isolated
source faults each fail both independent-answer tests; baseline/restored
runs pass. Recipe: `notes/mutations/example-programs.py`; local logs:
`.artifacts/examples-mutations/router/`. The full required `scripts/check.sh`
run reported 4817 passed, one optional local XDP-image skip, five existing
precise expected discrepancies and one layout-assertion failure: the old guard
required oracle catalogs to contain only corpus vectors. Updated that guard
to require the exact corpus-plus-examples inventory and nonempty examples.
The corrected layout plus all example tests then pass (12 tests), along with
fresh Ruff format/lint, full Pyright, buf lint/generation drift and actionlint.
Both commands exit as recorded: full initial run 1, focused correction plus
remaining gates 0. No application/runtime source changed after the broad run.
Logs: `.artifacts/examples-router-check.log` and
`.artifacts/examples-router-fix-check.log`. A final combined full run remains
due after integrating the other two applications.

Root owns integration on `main`. Isolated workers own only their respective
`examples/<name>/` and `tests/examples/<name>/` trees on branches
`codex/example-firewall` and `codex/example-load-balancer`, in sibling worktrees
`/Users/qobilidop/my/work/p4blo-example-firewall` and
`/Users/qobilidop/my/work/p4blo-example-load-balancer`. They begin program design
against committed eDSL interfaces; shared router/test interfaces must be
committed and integrated before they depend on them. Next: commit this checked
router baseline, then complete and independently review those applications.

**Application collection planning (2026-09-24).** Accepted three familiar
applications: IPv4 router, stateful firewall and flow-affine load balancer.
Canonical source/demo/docs will live under `examples/`, verification under
`tests/examples/`; upstream corpus fixtures retain their existing contracts.
The finite plan is [examples.md](examples.md), with the iterative engineering
loop in [workflows.md](workflows.md#application-development) and navigation in
`AGENTS.md`. Implementation has not started. Next: specify the router profile
and independent expected outcomes, then build its complete runnable scenario.
This checkpoint changes documentation only; no new runtime evidence is claimed.
Independent [planning review](notes/reviews/examples-plan.md) found no blocking
issues; both navigation/review-wording suggestions are resolved. `git diff
--check` and a one-off check of headings and 39 local link targets pass.
Runtime gates were not rerun for this documentation-only change.

**Python gateway walkthrough (2026-09-24, published).** At the user's
request, replace the website's short Python/Lean excerpts with a complete
Python eDSL example and Veil-style scrolling explanation. The new
`tests/corpus/vlan_gateway/` program parses one VLAN tag, applies exact
ingress/VLAN/destination policy, removes admitted tags and counts admissions.
It fits the existing eDSL and interpreter contracts without API or semantic
changes. Its README defines the single-tag/trusted-host boundary and runnable
three-packet demo. `scripts/render-website-example.py` generates nine
contiguous highlighted regions and the downloadable source; pytest and the
Pages workflow check source drift. Design rationale is in
[website-design.md](notes/website-design.md).

The focused seven example/corpus tests and both pinned P4 oracle replays
pass. Independent expected bytes, diagnostics and every one of the 512
counter cells are checked over a 53-request persistent sequence in Python
and Lean. Two source/website drift tests pass. Commands completed with exit 0:

- `nix develop -c scripts/check-lean.sh`: both packages, default proof audits,
  spec checks and native/API tests pass, with no Lean source changes.
- `P4BLO_REQUIRE_LEAN=1 nix develop -c scripts/check.sh`: **4808 passed**,
  five existing precise oracle expected discrepancies and one optional local
  XDP-image skip; Ruff format/lint, Pyright, schema generation drift and
  actionlint pass. Collection confirms all **2888** `lean_agrees` tests are
  included in this full required run; the selector was not redundantly rerun.
- Focused new-vector replays on P4-SpecTec and BMv2: **2 passed**, no skips.
  The existing shared Docker images were reused, not rebuilt.
- `nix develop -c node --check website/main.js` and `actionlint` pass for
  the final JavaScript and deployment workflow. Both website source checks
  pass, including actual rendered text equality and generator `--check`.

Chrome checks cover 1920-pixel desktop and 390-pixel mobile visuals, document
overflow at 320/390/768/1024, step buttons/arrow navigation, manual scrolling,
mobile-card exit, copy success feedback and a script-free fallback exposing
all nine notes. Browser warning/error logs are empty. Reduced-motion behavior
was source-reviewed, not browser-emulated; no screen-reader certification is
claimed. The bounded [source-fault recipe](notes/mutations/vlan-gateway.py)
then exercised three program faults in an isolated worktree, running each
through both unchanged interpreters. Independent expectations reject omitted
initial drop (case 5), omitted tag invalidation (case 0), and the wrong counter
index (case 0, unchanged output packet), even though Python and Lean agree
with each other. Baseline and restored runs each pass all three gateway tests.
The first attempt exposed a missing artifact-directory creation in the new
failure handler; that I/O error is not counted as Lean semantic detection.
The one-line fix is followed by the successful campaign and **5 passing**
gateway/website tests. The broader gate above preceded that failure-handler
fix; no interpreter or application source changed afterward. Retained local
evidence: `.artifacts/vlan-gateway/2026-09-24-checked/`, including mutant
sources, replay bundles, logs and hashes. The independent
[review](notes/reviews/vlan-gateway.md) has no remaining confirmed defects;
it distinguishes its own checks from the integrator's campaign and browser
checks. Published from `38d740e998a0c482983df8704af1bc81429b5f9c` at
<https://qobilidop.github.io/p4blo/#examples>; Pages run
[35972463500](https://github.com/qobilidop/p4blo/actions/runs/35972463500)
succeeded. Public HTML, CSS, JavaScript and downloadable Python source match
the committed files byte for byte. Chrome verifies the live step transition
with no browser warnings/errors. Both temporary review/mutation worktrees
were removed after preserving the review and fault artifacts; their paths
were verified absent and the original six registrations remain. The requested
example and visual are complete; the next step is user feedback on the live
walkthrough. No additional semantic or proof work is implied.
No whole-gateway proof or Lean-authored counterpart is claimed. The frozen
milestone 1 evidence below retains its original eleven-program counts.

**Local worktree cleanup (2026-09-24).** Removed 86 obsolete worktrees from
the initial 92 after preserving and independently checking 86 recovery
archives (971 file entries, about 271 MiB). Six trees remain: main, the two
documented parked drafts, and three trees with unique history/review content.
All removed directories were verified absent, final registrations recounted,
and retained non-main HEAD/status checked unchanged. Branches were preserved;
review found and protected one reflog-only commit with a local recovery ref.
Exact scope, local archive location and recovery instructions are in
[worktree-cleanup.md](notes/worktree-cleanup.md), with the
[independent review](notes/reviews/worktree-cleanup.md). No implementation
changed; runtime gates were not rerun. Cleanup is complete; retain the five
non-main trees pending separate review or a new scope for the parked work.

**Project website (2026-09-23).** The user requested a website inspired by
Veil, then explicitly requested GitHub Pages publication. The responsive
static design is in `website/`, with rationale in
[website-design.md](notes/website-design.md) and a CLEAR independent
[review](notes/reviews/website-design.md). The `Website` workflow publishes
only that directory on relevant `main` pushes or manual dispatch. Published
at <https://qobilidop.github.io/p4blo/> from `c44ee92`; Pages deployment
[35964437831](https://github.com/qobilidop/p4blo/actions/runs/35964437831)
completed successfully. The public page renders correctly in Chrome, its
language switcher works and its error/warning log is empty. Pages uses
workflow publishing with HTTPS enforced. This completes the requested
website task; the next step is user feedback on the live design.

Checks: `nix develop -c node --check website/main.js` passes; a one-off Nix
Python HTML/source check passes for 17 unique IDs, all 26 link destinations,
three local assets and both exact action excerpts. Chrome visual checks
cover desktop and 390-pixel mobile layouts; document widths at 320, 390,
768 and 1024 pixels have no horizontal overflow. Mouse/arrow-key language
switching (including Home/End) and clipboard success were exercised; browser
error/warning log is empty. `nix develop -c actionlint` passes for all six
workflows; the Pages workflow also received independent review. No
screen-reader certification is claimed. Python/schema, Lean,
DRT, mutation and oracle gates were not rerun for these isolated presentation
files; the frozen implementation evidence below is unchanged.

**Assurance milestone 1 is complete.** The frozen code-gate revision is
`3148a52f2212238da00fe76ebe8eab81d86b6023`, pushed to `main`. Exact commands,
provenance, exceptions and CI links are in the
[completion report](notes/milestone-1-completion.md); the
[independent release review](notes/reviews/milestone-release.md) is CLEAR.
Subsequent completion bookkeeping is documentation-only, not a new tested
code revision. No mandatory implementation work remains for this milestone.

Fresh-checkout acceptance passed:

- Locked environment and both Lean package builds, default proof audits,
  627 spec checks and user-package native/API tests.
- Full Python/schema/workflow gate: **4793 passed**, five precisely classified
  expected oracle discrepancies and one explicit optional local XDP-image skip.
  All required P4 oracle and printer checks ran; no availability skip is hidden.
- Required Lean/Python conformance: **2886 passed**, no skips or errors.
- Finite `scripts/check-assurance.py` campaign: ten selected sensitivity
  regressions, actual compiled Lean runtime/codec faults, the paired-observer
  challenge, exact independent detections and restored saved-input replays.
  An independent reviewer rechecked provenance and replayed restored inputs.
- All five remote workflows passed at the same revision: CI `35960620942`,
  Lean `35960620935`, P4-SpecTec `35960620865`, BMv2 `35960620846` and XDP
  `35960620983`. The earlier XDP snapshot outage below is historical.

Closeout integrates whole-program/host interchange (`dcddcad`, `a6697f3`),
the finite catalogue (`dd5f135`), precise oracle classification (`01484ae`)
and the tested two-language quickstart (`eb66820`). Review closed two real
bool/int state-observer survivors and a broad BMv2 expected-failure marker.
The [profile](profile.md) and [evidence map](evidence.md) distinguish syntax,
validity, tested execution and scoped proofs. This is not universal Python
equivalence, full P4 support or a fully proved application pipeline.

Stop here. The threads below are future/parked work, not an instruction to
resume them automatically. Their unfinished proof drafts remain preserved in
[parked-proofs.md](notes/parked-proofs.md); a new milestone needs new direction.

## Historical checkpoints

Combined local code integration at `7bfdcca`, including reviewed Action/Block
laws and the oracle selector at `529475f`, total Expr/LValue/Stmt codec proofs,
Arg wire laws, unified read-only header expressions, independent source zero,
actual/source frame-initialization proofs, readable command lists and forwarding
policy proofs, the separately named validity-guarded policy and exact flat-body
prefixes and actual body-bearing plain-root call entry: both Lean package gates and default audits pass, with
**595 spec checks**, all existing scalar/context/
command/path answers and negative checks, seven field-expression answers and
six additional field-expression kernel rejection examples, plus ten field-
command full-state answers and declaration/permission/continuation checks.
Named paths add 17 exact diagnostics and 11 rejected constructions; the
arbitrary-store policy adds seven independent policy/source/runtime answers.
Command lists retain exact previous ASTs/exports and independent order checks;
codec tests retain independent constructor observations and malformed errors.
Header primitives add opposite-validity/direct/empty-header answers; source
zero pins independent values, exact fuel limits and nominal boundaries.
Unified reads add 20 expressions and four commands with full post-read
observations; frame tests cover all entries, map keys and action absence.
The source-frame adapter adds kernel-checked actual-built forwarding
initialization, independent expected values and explicit extra declarations.
Flat-prefix proofs add four audited roots and 16 actual queue-boundary cases,
without changing runtime semantics or the former whole-body theorem APIs.
Guarded forwarding adds 64 independent Lean state answers and 32 exported
Python/Lean cases, including invalid headers and boundary TTLs.
Call entry adds seven spec checks, twelve default-audited roots and 23
focused Python checks, including independent full-state and strict JSON
observer regressions. Body-parametric entry adds six audited roots, twelve
native entry boundaries and eighteen Python checks comparing complete selected
block syntax and strictly typed snapshots. The old entry exporter remains
byte-identical; the new exporter matches the reviewed candidate exactly.
The actual local-initializer prefix adds five audited roots, sixteen native
boundaries and four missing-extra controls. An actual Python initializer fault
is caught, saved, replayed live and checked again after restoration.
Normal return adds six spec checks, nine audited roots and 41 focused Python
checks. Complete-state, ordered-write and recursive mutable-isolation observers
reject the independently reproduced selective-alias faults. The guarded call
prefix adds five audited roots, 192 native boundaries and 78 Python checks;
complete native Index/scope/shared comparisons and strict frozen Python state
reject independent observer faults. Its exporter is byte-identical to the
reviewed candidate. The independently reviewed statement-codec baseline adds
four spec checks and 107 Python checks, without changing the production
decoder. All 79 captured old statements replay with exact byte transcripts
and independent source-matched answers. The actual total statement decoder,
all-input ordinary-helper recurrence and universal representable statement
roundtrip are now integrated, with eight new audited roots and constructive
all-constructor witnesses. Two compiling faults are proof-rejected; four
other faults retain roundtrip proofs but fail independent wire/error answers.
All 25 saved campaign observations (20 distinct requests) replay restored.
The separately named observer-free whole control call adds nine audited roots, 192 native
profiles and 91 Python checks, including actual normal completion, full state,
all incoming/outgoing mutable copies and independent ordered-write controls.
Its exporter is byte-identical to the reviewed candidate.
The action-root prerequisite adds exact unshadowed block writes and action-hit
read/write laws, preserving the old block API. Four new audits, a genuine
active-frame kernel witness and eight native storage/error checks pass. Four
isolated compiling Env faults are proof-rejected; the runtime is unchanged.
The complete Lean-authored corpus forwarder now exactly matches the Python
builder and golden. Seven audited roots include actual initialization and
the invalid-IPv4 body's whole-Run identity; 24 native state profiles, two
post-drop checksum checks, four in-memory packet answers and 50 Python tests
cover the explicitly bounded port. Review found a state-only Python fault
surviving packet checks; strict complete-state checks now reject it. A new
actual TTL-underflow fault is retained and replayed live/restored.
The declaration baseline adds 14 native checks and 319 Python tests, without
changing production codecs. All 247 raw transcripts match source-pinned
expectations and exact bytes; 102 successful outputs pass public protobuf
wrappers. The action-layer field adapter adds four audited roots and a mixed
shadowed/unshadowed witness, preserving the old block-only APIs. A rejected
false theorem conclusion is not counted as a compiling runtime fault.
Nine declaration roundtrip laws now add ten default-audited roots with
constructive witnesses and overflow controls. All old bytes remain unchanged.
One actual encoder fault is proof-rejected; paired mapping/error-order faults
that preserve proofs produce 24 source-matched raw mismatches. Paired Python
fixture/Lean-observer corruption survives direct Python checks but fails
independent native anchors. All restored replays pass with reconstructed mutant
source hashes. The standalone next-table probe also passes independently;
it is unregistered and is not claimed as production Table coverage.
The independent table baseline adds 20 native and 235 Python checks, with
181 exact raw transcripts (82 protobuf successes / 99 errors). Production
codec bytes and all old inventories remain unchanged. Four actual table codec
laws now add five default audits with constructive wire-only witnesses and
overflow controls. Five compiling faults distinguish proof rejection from
roundtrip-preserving wire/error mistakes; 56 raw observations over 52 distinct
requests and all paired-observer challenges replay restored.
The actual selected forwarder action adds eleven audited roots, 48 independent
native outcomes / 144 queue boundaries and 76 Python checks. It proves real
literal binding, the complete field policy and exact normal layer restoration,
not table selection or the surrounding pipeline. Review-discovered temporary
sibling corruption and bool/int-equality gaps in auxiliary write probes are
closed. Five compiling model faults fail the proofs; the actual Python
destination-write fault reuses the existing TTL0 bundle. All source restoration
and byte identities pass. The Lean-authored tutorial firewall now matches its
independent Python builder and frozen IR exactly. Its fixed in-memory server
retains state; 128 focused checks cover complete Bloom arrays, byte cuts,
collisions and changing policies. Compiling source/server/Python faults are
caught; review closed fixed-server retention and diagnostic-observer gaps.
The separate 331679-byte reset transcript replays to all four restored answers;
both it and the register-write challenge reuse existing four-packet input.
The firewall initialization and invalid-body proofs are now integrated:
thirteen default-audited roots, nine independently observed initialized roots,
48 native whole-state profiles and 58 Python checks. Both actual guard faults
are proof-rejected; a real Python local-write fault survives packet/extern DRT
but fails the complete Env observer after normal completion. This adds no
new divergent packet bundle. The parser-codec baseline adds 27 native anchors
and 283 Python checks, preserving all actual codec bytes. Its 231 frozen raw
rows, 76 actual public-protobuf outputs and thirteen historical source hashes
all replay exactly. Five universal parser-codec laws now add six default
audits, mixed constructive witnesses and overflow controls. Five compiling
codec faults distinguish false roundtrips from paired mapping/error-order
mistakes; 40 retained observations over 34 distinct requests replay restored.
The forwarder's actual bounded table installation/selection adds nine audited
roots, 270 native cases and 50 Python checks. Its independent numeric policy
covers every IPv4 query and fitting payload for five installation shapes.
A compiling shortest-prefix fault is rejected; the actual Python fault also
produces a retained, live/restored packet mismatch on a new two-route input.
Actual table application now adds twelve audited roots, 270 native applications,
810 queue boundaries and 24 hit/error controls, plus 320 Python checks.
It composes actual key evaluation, installed selection, action completion and
normal restoration while retaining arbitrary continuation and explicit hit
timing. The new default-skip fault reuses TTL0 packet bytes under a distinct
no-route configuration; complete source-matched replay agrees after restoration.
Both overlapping-route orders and three default profiles pass immutable BMv2.
Dedicated oracle CI now explicitly selects that exact test without Lean
fixtures. The surrounding guarded ingress/checksum remains separate work.
Exact Bloom insertion now adds thirteen default audits, 84 native profiles
and 79 Python checks, including the repaired runtime-read-coupling observer.
Seven actual compiling Lean source/runtime faults fail proofs; a real Python
other-cell fault reuses the old four-packet input with three state-only
mismatches. Independent review and final combined restoration checks pass.
The Action/Block baseline adds 28 native anchors and 518 Python checks; all
498 exact raw rows and 114 public protobuf outputs replay against eighteen
historical source identities. The separate shared-helper extraction preserves
all four Table statements and old bytes. Two actual Action/Block roundtrip
laws now add three default audits, an all-kind mixed kernel witness and twenty
overflow exclusions. Five compiling codec faults distinguish proof rejection
from roundtrip-preserving mapping/default/error-order mistakes. Paired faulty
observers can fool direct comparisons but not the independent native anchors.
All 86 retained raw observations (78 distinct requests) replay restored.
The owned printer lifecycle fix adds fifteen deterministic regressions;
all actual printer goldens pass without skips and independent review is clear.
Required real-Lean DRT: **2700 passed**, no skips. Full gate:
**4512 passed / 5 precise expected discrepancies / 1 explicit skip**, plus
formatting, lint, types, schema generation/no drift and workflow checks;
all commands exited 0. The sole skip is the unavailable local XDP image;
required native XDP CI passes at `c550a6f`, including lifecycle regressions.
Latest reviews under `notes/reviews/`: `field-permissions.md`,
`command-seam.md`, `field-commands.md`, `keyvalue-codec.md` and `call-copy.md`.
Latest reviews also include `named-paths.md`, `forward-policy.md`,
`command-blocks.md`, `expr-codec.md`, `header-validity-primitives.md`,
`source-zero.md`, `lvalue-codec.md`, `frame-initialization.md` and
`header-validity-expressions.md`, `initial-source-frames.md` and
`guarded-forwarding.md`, `command-prefix.md`, `certificate-cleanup.md` and
`plain-call-entry.md`, `body-parametric-entry.md`, `call-initializers.md` and
`plain-call-return.md`, `guarded-call-prefix.md`, `stmt-codec-baseline.md` and
`guarded-control-call.md`, `stmt-codec.md`, `action-root-writes.md` and
`lean-forwarder.md`, `declaration-codec-baseline.md`, `field-action-writes.md`,
`declaration-codec.md`, `table-codec-next.md`, `table-codec-baseline.md` and
`lean-firewall-next.md` and `forwarder-action.md`, `table-codec.md`,
`lean-firewall-port.md`, `forwarder-table-next.md`, `program-codec-completion.md`,
`lean-firewall-proof.md`, `parser-codec-baseline.md`, `firewall-bloom-next.md`,
`forwarder-tables.md`, `parser-codec.md`, `firewall-bloom.md`,
`block-codec-next.md`, `block-codec-baseline.md`, `codec-object-helpers.md`
and `printer-lifecycle.md`, `forwarder-apply.md`, `forwarder-apply-ci.md`
and `firewall-readback-next.md`, `block-codec.md`, `milestone-1-scope.md`.

All five remote workflows pass for `425fbc9`. At pushed `ff47066`, CI, Oracle
and BMv2 plus Lean pass. XDP run `35949452182` failed before compilation:
Ubuntu's pinned snapshot returned HTTP 503 for noble-security/InRelease.
Attempt 2 also failed before compilation with HTTP 503 on all three pinned
InRelease indexes, in both build/runtime stages. No further immediate retry
or infrastructure change is made; pins/checks remain unchanged. At `54e3c65`,
CI (`35950597919`), Lean (`35950597842`), Oracle (`35950597925`) and BMv2
(`35950597905`) pass. XDP (`35950597787`) again fails before compilation,
this time with HTTP 502 on all three pinned Ubuntu InRelease indexes.
This is not a completed XDP gate or a code fix; the experimental XDP profile
is reported separately from milestone 1's P4 acceptance.
This closes the earlier macOS CI run `35922311964` failure at
`2bd65b8`: a redundant final process-group kill raised PermissionError after
timeout cleanup, masking its diagnostic. Reviewed fix `8438cbd`, integrated
at `5871da8`, attempts cleanup once, retains bounded reaping and fails closed
on cleanup denial. Six deterministic regressions and both live descendant
tests pass. The complete integrated certificate module passes all 61 cases
against the real Lean checker, without skips. Fresh remote CI run
`35924868471` passes; the closure is not merely a retry of the original commit.
Evidence: `notes/certificate-cleanup.md` and its independent review.
Twenty retained execution-fault bundles and 255 raw codec
artifacts have tracked reconstruction recipes and byte-checked ignored
copies under `.artifacts/drt` and `.artifacts/codec` respectively.
All twenty execution bundles replay successfully on this integration
(twenty-seven requests), as do all 255 raw codec observations. The real
forwarder's new TTL0 bundle matches its current authored Program, tracked
edge input and fixed configuration. The new
statement campaigns contribute 25 observations of 20 distinct requests;
these counts are not independent-input counts. Declaration campaigns add 24
observations of 24 distinct requests; harness views are not additional inputs.
Table campaigns add 56 observations of 52 distinct requests, with 56 matching
harness views. Parser campaigns add 40 observations of 34 distinct requests,
with 40 matching harness views. Action/Block campaigns add 86 observations
over 78 distinct requests and 86 matching harness views. Historical Table and
Parser registration layers remain pinned at `661c8d8` and `e4c8402`; current
Action/Block registration additions are checked separately at `b0c31425`,
without rewriting old artifacts.
The later reviewed Table helper relocation is checked independently at
`707fb3f`, retaining the original proof identity at `228b76b`.
The fixed-firewall reset transcript lives separately under
`.artifacts/fixed-firewall/state-reset.json`; it is not a generic DRT bundle
or an additional distinct packet sequence.
Header-read,
guarded and initializer bundles match their current exporter/wrapper and exact request. All fifteen
Expr/LValue/Arg fault inputs uniquely match tracked fixtures; all 59 Expr and
69 LValue/Arg and 79 Stmt source-matched pre-refactor transcripts retain byte-identical
stdout/stderr and exit status. Artifact
command metadata is never executed. Reconstruction recipes survive losing
local ignored artifacts and temporary logs. The 247 declaration baseline
transcripts additionally retain exact bytes, independent source-matched answers
and historical hashes at `21b0fec`; the 181 table baseline transcripts have
historical hashes at `9640523`. The parser baseline's 231 rows have historical
hashes at `9d68d7d`; the 498 Action/Block baseline rows use `6b9ffd0`.
None of these baselines is counted as fault evidence.
Earlier exact counts and experiments remain in named review/assurance
reports and git history, not competing current instructions below.

During the full gate a task-owned p4c version container logged success but
remained daemon-marked running with no processes or mounts. Removing that
exact verified container released the probe; absence was verified and all
printer golden checks subsequently passed. No daemon restart, prune, image
build or unrelated cleanup occurred. The reviewed bounded owned-container
lifecycle fix is now integrated at `25064ab`; the underlying daemon cause
is not established. Scope and failure handling: `notes/printer-lifecycle.md`.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | existing constructs and explicit extern contracts; no application escape hatch | green: twelve corpus programs fit; firewall adds no core construct; coverage table published |
| 2. Supports the tested real programs | corpus packets and original firewall packet/state prefixes | 18 vector files, 12 programs; one strict BMv2 register divergence; separate CRC/mask probes expose four precise pinned SpecTec discrepancies |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT and named checked properties | green: 595 spec checks plus user-package tests; corpus and typed generated-program DRT with extern-state comparison; contextual scalar checking, exact scalar/field expression and command lowering, header-read/source-zero correspondence, actual frame initialization and plain-root entry/normal return, representable leaf/Expr/LValue/Arg/Stmt, declaration/table/parser codecs and finite-trace execution proofs; no universal Python equivalence claim |

## Steps

| Step | What | Status |
|---|---|---|
| 0 | Skeleton: flake, Python project, schema stub, CI, docs | done |
| 1 | Schema, validator, semantics, forwarder in text format, interpreter, STF runner | done: the forwarder's five vectors pass end to end |
| 2 | Extern registry, stateful program | done: registry with register, counter and checksum16; the stateful program and the forwarder's checksum |
| 3 | eDSL, four corpus programs, two architectures, metadata contract | done: twelve programs in the typed eDSL, both architectures, contract check |
| 4 | Printer, v1model shim, P4-SpecTec oracle job, STF replay both sides | done: corpus gates run on both oracles in separate CI jobs; precise expected discrepancies are recorded above |
| 5 | Lean interpreter, extern models, DRT, the theorem | done |
| 6 | Coverage table, README claim matrix, write-up | done: coverage table (177 rows, none undecided), README, `docs/writeup.md`; both reviews kept under docs/notes/reviews and their findings fixed |

## Corpus

| Program | Source | Rewritten | Vectors | Oracle |
|---|---|---|---|---|
| forwarder | p4lang tutorial basic | Python and Lean sources equal the unchanged golden; direct Lean execution and invalid-control theorem; checksum16 computes hdrChecksum, verify deferred | 5 hand-derived STF files plus TTL0/1 and full invalid-control state checks, passing | 5/5 pass on both oracles, checksum included |
| acl | p4c `ternary2-bmv2` | eDSL, landed | p4c STF, 6 adds, 4 packets, passing | 4/4 pass on both oracles |
| stacks | p4c `header-stack-ops-bmv2` | eDSL, landed | p4c STF, 15 packets, all passing | 15/15 pass on both oracles |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | passes on both oracles |
| stateful | p4c `issue1097-2-bmv2` + own vectors | eDSL, landed; register and counter bound | p4c STF, 2 packets, plus 6 of ours across packets, passing | 8/8 pass on both oracles |
| csum16 | p4c `issue655-bmv2` | eDSL, landed; checksum16 bound | p4c STF, 6 packets, passing | 6/6 pass on both oracles |
| parser_error | p4c `parser_error-bmv2` | eDSL, landed | p4c STF, 2 packets, passing | pass on both oracles |
| verify_error | p4c `issue1824-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | pass on both oracles |
| priority | p4c `table-entries-priority-bmv2` | eDSL, landed | p4c STF, 3 packets, passing | pass on both oracles |
| register_bounds | own program from the second review | eDSL, landed | 9 hand-derived packets, passing | passes on P4-SpecTec; two packets diverge on BMv2 by the recorded out-of-range register rule, carried as a strict xfail |
| tutorial_firewall | pinned p4lang tutorial solution | Python and Lean sources equal unchanged golden; persistent direct Lean execution | connection/Bloom false positives, byte cuts and generated host-policy sequences | original BMv2 packets/all 8192 register cells at 30 prefix boundaries; SpecTec controls pass but exact CRC/mask probes disagree; scoped Lean application proofs next |
| vlan_gateway | original p4blo homepage example | complete Python eDSL; generated IR and website source; no new core construct | one STF file with 11 packets; independent 53-request packet/diagnostic/full-counter sequence in Python and Lean | packet vectors pass both pinned P4 oracles; counters checked by Python/Lean expectations |

## Open threads

The application collection is active. Milestone 1 is complete; the other
older plans below are deliberately parked, not automatic continuation tasks.

- **Python application collection:** autonomous implementation is authorized;
  follow [examples.md](examples.md). Current iteration: all three implemented,
  reviewed and challenged with known-answer program mutations; review findings
  resolved. Next: full combined gates, final evidence and removal of task-owned
  worktrees. Existing six preserved worktrees are outside this cleanup scope.
  Keep the finite checklist and review findings current as each advances.

- **Project website:** the requested Python gateway walkthrough is published,
  checked and independently reviewed at
  <https://qobilidop.github.io/p4blo/#examples>. It is complete; future visual
  feedback does not reopen the parked semantics/proof work.

- **Local worktrees:** cleanup is complete; five non-main trees remain
  intentionally. See [the inventory and recovery guide](notes/worktree-cleanup.md)
  before treating any remaining tree or local archive as disposable.

- **Architecture implementation: milestone 1 complete.**
  Future extensions follow [implementation.md](implementation.md) and the agreed design in
  [notes/ir-spec-boundary.md](notes/ir-spec-boundary.md). Python and Lean only;
  full architecture-independent P4 remains a north star. Small commits and
  pushes are authorized. Record uncertain choices and revisit triggers.

  Package boundaries and shared verification layout are complete:
  `ir/` owns `p4blo-ir` / `P4bloIR`, abstract meaning and the wire schema;
  `lean/` owns user-facing `p4blo` / `P4blo` and imports the spec one-way;
  `python/p4blo/` provides Python authoring and interpretation. Shared corpus
  and oracles live under `tests/`. Wire identities and generated bytes are
  preserved. Both Lean packages and their default proof audits are explicit
  gates. Independent reviews include clean builds without caches or an
  active default toolchain: `notes/reviews/package-boundary.md`,
  `shared-verification-layout.md` and `lean-public-names.md`.

- **Verified Lean authoring: scalar and field commands integrated.**
  Closed bits/bools/addition/equality/mux and context-indexed variable reads
  share one AST and independent Fin/Bool source semantics. Exact lowering
  preserves the source value and the entire Run under actual action-first
  frame agreement. A constructive frame witness rules out vacuous premises.
  The scoped IR checker validates unique nonempty names/positive widths and
  has soundness and completeness for its scalar relation.
  Assignment/sequence/if use independent source-state updates and lower to
  finite prefixes of actual execution. Exact source values, unrelated Run
  fields and names outside the target set are preserved. Constructive
  permission/declaration/frame witnesses rule out vacuous premises.
  No validated global initialization, complete program or verified codec
  claim follows; action layers remain excluded from writable bodies.

  Twenty-one independently expected authored expressions include eight
  variable cases; malformed contexts/references, missing/wrong-width frames
  and action shadowing are tested. Mutation evidence distinguishes proof
  rejection, compiled-but-wrong surface accessors, corrupted input fixtures
  and a replayed actual Python-read mismatch. Exact obligations, axioms,
  decisions, commands and exclusions: `lean/ASSURANCE.md`; independent
  review: `notes/reviews/typed-frames.md`.
  Commands add nine independent whole-state answers and four negative typing
  cases, real out/inout writes and a faulting-continuation witness. Six
  adversarial changes separate proof rejection, compiled wrong source intent
  and an actual Python-write mismatch saved/replayed live and restored.
  Review: `notes/reviews/typed-statements.md`; exact scope in `lean/ASSURANCE.md`.
  The next increment was typed packet/metadata fields rather than every
  remaining scalar operator; those results are recorded below.
  `notes/typed-fields-plan.md` requires actual Index agreement and full
  sibling/validity preservation. Primitive field bridges are integrated
  from `ddb9f0e`: exact nominal declaration/shape premises, stored invalid-
  header fields, validity and siblings, with three actual setter proof faults
  rejected. Review: `notes/reviews/field-primitives.md`. The next aggregate
  checkpoint `7a2ad91` is integrated at `d2a1921`: independent finite source
  shapes/stores and scalar paths now correspond to actual nested reads and
  persistent writes, preserving validity, siblings, unrelated roots and
  non-value Run fields. Local shape checks do not imply nominal coherence;
  positive witnesses and impossible conflicting-layout examples expose that
  boundary. Root permission and integrated expression/command proofs were
  separate follow-up obligations, now implemented below. Review:
  `notes/reviews/aggregate-paths.md`.
  `a271370`/`a3f3537` are integrated at `d8e2341`: one shared `ExprWith`
  operator AST now serves scalar references and aggregate paths. Concrete
  field typing uses actual declarations/Index, and evaluation returns the
  exact independent source value with the entire Run unchanged. Seven
  authored field expressions and six kernel rejection examples complement
  old scalar fixtures. Review `notes/reviews/field-expressions.md` found and
  fixed pre-expression snapshots: a real read-side effect survived the old
  observer but fails after evaluation is observed first. Three actual Python
  read/setter faults have retained live/restored replay evidence; proof and
  compiled surface faults are separately recorded in `lean/ASSURANCE.md`.
  Command write factoring and actual root permissions followed in
  isolated `work/field-commands`, based on committed `d8e2341`, following
  `notes/field-commands-plan.md` (committed `480eef4`).
  First specification increment `8b39c06` is integrated: writable member
  paths inherit actual root declaration permission, and scalar assignment/
  conditional/body relations reuse the field-expression typing boundary.
  Constructive local/out/inout witnesses and six kernel rejection examples
  cover readonly/missing/empty roots, wrong nominal kind and width mismatch.
  Both Lean gates/default audits pass after integration. This adds no runtime
  behavior or total checker. Review: `notes/reviews/field-permissions.md`.
  Generic command factoring `cd34e83` is integrated: `CmdWith` now owns the
  sole command AST, independent denotation, lowering and exact-prefix proof.
  The scalar API/theorems are preserved through concrete adapters, with all
  prior authored fixtures unchanged. Both Lean gates and 62 authored/call
  focused checks pass. Review: `notes/reviews/command-seam.md`.
  Concrete field modes/places and command proofs `9755077`/`7a4a05b` are
  integrated at `3f1efb6`: actual root permission, exact full source values,
  all validity bits, preserved declarations, unrelated runtime state and
  arbitrary continuations. Ten authored cases include a route-selected
  forwarding rewrite; real subcontrol directions and complete post-body
  snapshots constrain the unverified wrapper. Three generic proof faults
  fail; a compiled same-width wrong accessor passes generic proofs/DRT but
  fails independent expected bytes. Two actual authored-write validity/
  sibling faults save and replay live/restored. Review:
  `notes/reviews/field-commands.md`; recipes and scope: `lean/ASSURANCE.md`.
  The body theorem does not prove a router, initializer or call copying.
  Named paths `d47f8bc` and independent policy `d31f8bc` are integrated at
  `0dc7b08`. Names resolve unambiguously into existing typed references;
  spelling/permission soundness does not imply global schema validity.
  All six naming roots are default-audited; wrong slot, error diagnostic and
  valid-but-wrong requested intent faults are distinguished in
  `notes/named-paths.md` and its review.
  The forwarding theorem covers arbitrary source stores and actual reference
  execution against an independent complete-state hit/TTL policy. Five
  default-audited roots include lossless observation laws. Wrong destination
  and missing TTL guard faults fail the application proof; paired state
  relabeling still passes those proofs but fails independent mapping anchors.
  This does not establish parsing, checksum maintenance or architecture fate.
  Scope/review: `notes/forward-policy.md`, `notes/reviews/forward-policy.md`.
  Readable list sequencing `cf78144` is integrated at `5d0b74f`, preserving
  exact previous ASTs and exported bytes. Independent review is clear;
  both integrated Lean gates (including actual policy normalization/audit)
  and 23 focused authored-command checks pass. The combined full/required
  gates also pass at the latest checkpoint above.
  Scope: `notes/command-blocks.md`, `notes/reviews/command-blocks.md`.
  The reviewed header-validity plan/probe is committed at `cdb7a3c`:
  `notes/header-validity-plan.md`, `notes/reviews/header-validity-plan.md`.
  Primitive checkpoint 1 (`3cf11ee`/`c3ca9e6`) is integrated at `5d12252`:
  constrained header-only paths, concrete exact evaluation and authoritative
  scoped typing. Independent review is clear; both integrated Lean gates pass.
  Source constant/inversion faults fail the proof; a well-typed wrong sibling
  passes generic correctness but fails independent opposite-validity answers.
  Scope: `notes/header-validity-primitives.md` and its matching review.
  Checkpoint 2 (`edc12bd`/`078a9de`) is integrated at `2713999`: one shared
  read-family adapter preserves scalar writes and all four legacy exporter
  byte streams. Twenty expressions and four commands have independent full
  post-read observations. A weak pre-read snapshot misses a demonstrated
  correct-return side effect; the strengthened observer catches it. Actual
  Python wrong-return/side-effect faults save and replay the same complete
  witness, with restored agreement. Independent review is clear; scope and
  recipes: `notes/header-validity-expressions.md` and its matching review.
  Checkpoint 3 (`74ef437`/`fe17a77`) is integrated at `cffad0d`: a separately
  named both-valid-header policy, arbitrary-store proof, exact invalid-drop-only
  contract and concrete execution lift. Independent review is clear and combined
  gates pass above. Missing/inverted/paired guards fail the independent contract;
  exporting the old body passes generic proofs and engine agreement but fails
  independent answers. An actual Python bypass saves/live-replays divergence
  and agrees restored. Scope: `notes/guarded-forwarding.md` and its review.
  The old body's invalid-header contract and byte exports remain unchanged;
  parsing, route lookup, checksum and actual network drop remain unproved.
  An independent initialization review recommends the next premise-discharge
  bridge in `notes/initialization-bridge-plan.md` (committed `6ff0449`).
  Independent structural source zero and actual fuel-bounded Value.zero
  correspondence (`bcc4d27`/`f9d22ac`) are integrated at `c2bb0c8`. Exact
  nominal agreement and sufficient actual runtime budget remain explicit;
  mixed fixtures and existing forwarding roots discharge them constructively.
  Source-only/reference-only validity faults fail correspondence; a paired
  wrong model passes the proofs but fails independent kernel expected values.
  Review is clear, both integrated Lean gates pass; isolated full and required
  gates pass, including a fresh two-package build and 469 fresh-binary DRT
  checks after removing stale caches from the build search path. Scope:
  `notes/source-zero.md`, `notes/reviews/source-zero.md`.
  The actual Frame.forBlock theorem (`f00ca87`/`f1737b7`) is integrated at
  `db99dc2`. It accounts for every scope declaration, exact lookups/absence,
  the actual selected scope and no action overlay, without assuming scope
  block or stored declaration names match their lookup keys. Three compiling
  drop/name/overlay faults fail the exact theorem. Independent review is clear;
  both integrated Lean gates pass with 481 spec checks. Combined Python/DRT
  gates pass at the latest checkpoint above. Scope: `notes/frame-initialization.md`
  and its matching review.
  Source-zero/FrameMatches adapter `139e478`/`6c99835` is integrated at
  `c269994`: modeled zero values are discharged from independent source zero;
  unmodeled declarations retain explicit success obligations. A separate
  coverage condition justifies absent extras. Kernel-checked actual Index.build
  and forwarding-frame witnesses have only the standard three axioms, including
  independent expected values. Successful/failing extras are explicit local
  scope extensions, not the packet wrapper's actual observer layout. Independent
  review is clear; isolated fresh-cache Lean and 538 required DRT checks pass.
  Combined integration gates pass at the latest checkpoint above.
  Scope: `notes/initial-source-frames.md`
  and its matching review. Actual plain-root sub-control entry
  (`258ec14`/`0559c70`/`f8a0f61`) is integrated at `901c994`: actual four-root
  binding, complete Run frame replacement and exact captured caller/queue.
  The source bridge derives actual initialization for a kernel-built selected
  declaration program, including the real H/Result observer layout and extras.
  Its empty body and manually supplied caller remain explicit boundaries.
  Independent review is clear; twelve audit roots have only standard axioms,
  seven new spec checks and 23 focused Python checks pass. Five compiling
  actual-Exec faults are rejected by proofs; paired declaration corruption
  fails an independent syntax anchor. Actual Python cursor corruption fails
  entry-state answers. Eight state-survivor controls and eight JSON/type/case
  controls permanently reject demonstrated observer gaps. These internal
  snapshots are not packet-program replay bundles. Scope/review:
  `notes/plain-call-entry.md`, `notes/reviews/plain-call-entry.md`.
  Body-parametric entry (`db6b861`/`381e627`) is integrated at `dbfa37c`:
  one actual-built body family supplies lookup/scope and initialization while
  preserving the old empty API. The source proof is generalized once, not
  duplicated. Full selected guarded-block syntax matches the tracked Python
  wrapper, including both local assignments and the complete observer. Six
  audited roots, twelve native boundaries and 41 combined entry tests pass.
  A wrong empty index fails the proof; two wrong-but-compiling selected bodies
  fail independent syntax identity. No body execution is inferred from entry.
  Scope/review: `notes/body-parametric-entry.md` and its matching review.
  The next composition connected real local assignments and guarded
  forwarding to the exact pending observer suffix and return, as recorded below.
  Staged contract: `notes/call-body-prefix-plan.md`. Do not substitute the
  empty declaration witness, reshape the wrapper or claim copyback/global
  validity from a successful finite prefix.
  The disjoint local-assignment prerequisite (`70f5775`/`0d983ab`) is
  integrated at `21410b6`: the exact scratch19/unrelated165 prefix preserves
  full source agreement, outside names and arbitrary pending work. It does
  not itself assume or establish entry to an actual body-bearing call.
  Independent review and adversarial evidence: `notes/call-initializers.md`
  and its matching review. Composition (`dcbdf9c`/`101d2d7`) is independently
  reviewed and integrated at `b115c32`, including explicit initializer and
  selected-body syntax identity. It starts at actual call entry and proves
  full source-policy agreement plus exact non-frame preservation, while the
  arbitrary suffix and captured caller return remain pending. Five audit
  roots, 192 native profiles and 78 focused Python checks pass. Review exposed
  an int/float shared-state comparison survivor; recursive exact-type checks
  and complete native Index/scope/shared observations now reject it, with
  permanent corruption controls. A new actual local-write fault reuses the
  existing guarded packet input, so artifact counts do not increase. Scope:
  `notes/guarded-call-prefix.md`, `notes/reviews/guarded-call-prefix.md`.
  Normal return (`d019f64`/`16626b5`/`884a168`) is independently reviewed and
  integrated at `5061126`; contract:
  `notes/plain-call-return-plan.md`. It preserves the current post-callee Run
  outside the restored caller frame, not a historical entry Run. Review found three selective-alias
  observer gaps; recursive mutable-container detachment checks and four real
  branch writes now reject them, with permanent negative controls.
  All integrated gates and retained replays pass; exact scope and evidence:
  `notes/plain-call-return.md` and its matching review. With the guarded prefix
  landed, follow committed `notes/guarded-call-plan.md` for a separately named
  observer-free whole control call. That result (`1a0bf48`/`e8a584c`) is now
  independently reviewed and integrated at `9e53f4b`: actual empty-list pop
  and normal return complete `callBlock`, with exact independent source-policy
  results and original caller/shared-state preservation. Nine audits, 192
  native cases and 91 Python checks pass. Complete values alone cannot detect
  commuting writes or skipped same-value observer copyback; explicit weak/
  strong ordered-write controls demonstrate that gap. A separate observed
  packet wrapper exposes a genuine live/restored copyback mismatch on the
  same retained guarded input. Evidence/review: `notes/guarded-control-call.md`
  and its matching review. It keeps the observer parameter as
  pass-through but does not execute the seventeen observation assignments or
  claim parsing, lookup, checksum, architecture fate or full packet execution.
  Actual forwarder authoring (`0b157ff`/`2f92dad`) is independently reviewed
  and integrated at `f1493d8`, following `notes/lean-forwarder-next.md`.
  Complete Program equality preserves TTL wrap, old-destination MAC ordering,
  default drop, post-drop checksum and non-IPv4 pass-through. Both decoded
  DRT and direct public in-memory execution pass existing vectors and literal
  edge answers. Actual initialization and whole-Run invalid-control identity
  have seven default-audited roots. Review found a metadata-write survivor
  under packet-only tests; 24 strict Python complete-state profiles and
  permanent corruption controls now expose it. Four compiled wrong-intent
  source changes fail identity, and actual saturating Python subtraction
  has a new saved live/restored corpus mismatch. Evidence/review:
  `notes/lean-forwarder.md` and its matching report. Ordinary parser/action/
  table/extern assembly remains explicitly unverified; no full-pipeline
  theorem is implied. The target-only unshadowed field adapter is now
  integrated from `0da36db` at `77b9890`, preserving other modeled
  action-shadowed roots and the old APIs. Its four audited roots, mixed-layer
  witness and narrow false-conclusion challenge are independently reviewed:
  `notes/field-action-writes.md` and its matching report.
  Actual selected table-action execution is integrated from `539fe00` and
  `105e234` at `783cbba`: independent complete field policy, literal binding,
  ten transitions with normal return pending and the eleventh restoring only
  action layers. The relation is unindexed; exact counts are anchored by the
  explicit derivation and 144 native queue boundaries. Eleven audited roots
  and 76 focused Python checks pass; review fixed two auxiliary write-observer
  survivors with strict complete-state checks after each write. Five compiling
  model faults fail proofs; a real Python destination-write fault reuses the
  existing TTL0 bundle, not a new distinct witness. Scope and CLEAR review:
  `notes/forwarder-action.md` and its matching report. Actual bounded table
  installation/selection is integrated at `b3635a0`: universal IPv4 query and
  fitting payloads for five shapes, nine audits, 270 native cases and 50
  Python checks. Independent numeric expected selection and a new two-route
  mismatch supplement the actual lookup proofs. Scope/review:
  `notes/forwarder-tables.md`. Actual application is integrated at `9a12253`,
  with twelve audits, 270 native cases, 810 queue boundaries, 24 hit/error
  controls and 320 Python checks. Scope/review: `notes/forwarder-apply.md`.
  Further ingress/checksum proof work is parked for milestone 1. The exact
  unfinished tree and checks are recorded in `notes/parked-proofs.md`; none
  of its uncommitted results is a landed guarantee or acceptance blocker.
  The small operational root prerequisite is independently reviewed and
  committed at `01d8b09`: actual active-map absence permits a block write
  without dropping action storage; action-hit reads/writes prefer and change
  only that layer. The old BlockFrame API remains a corollary. A constructive
  active witness, four new default audits and eight native controls accompany
  four compiling actual-frame faults rejected by the proofs. This does not
  broaden source permissions or prove an action body/return. Scope/review:
  `notes/action-root-writes.md` and its matching independent report.
  Its proof-only flat-suffix prerequisite (`ea87e2f`/`5d706de`) is integrated
  at `45fe743`: the same command induction now retains the exact pending
  suffix/continuation and full source/noninterference facts. Old whole-body
  signatures are derived unchanged; no AST, runtime or wrapper changes.
  Independent review is clear, four audit roots have only standard axioms,
  16 native boundaries and isolated 564 required checks pass. False consumed-
  suffix/admin-step proofs are rejected; an actual compiled executor fault
  also produces a clean live/restored mismatch on the existing dependent-next
  bundle (not an extra distinct witness). Combined local gates pass above;
  the separately corrected certificate-cleanup failure is recorded above. Scope:
  `notes/command-prefix.md`, `notes/reviews/command-prefix.md`.

- **Tutorial firewall: bounded Python port and original-state oracle done.**
  The typed port adds no core IR construct. Independent packet and complete
  8192-cell expectations retain Bloom false positives. Original pinned BMv2
  matches 30 bounded prefix observations. CRC16/CRC32 services have explicit
  positive byte-aligned contracts, no hidden padding or range reduction.
  Exact strict probes expose pinned SpecTec's odd-byte CRC32 and table-mask
  defects; passing controls remain separate. Oracle CI discovers both sets.
  Scope, pins, observer barrier, exclusions and authoring costs:
  `notes/firewall-port.md`, `notes/crc-contract.md`.
  Reviews: `notes/reviews/firewall-port.md`, `crc-externs.md`.
  The next Lean application plan and independent review are now committed:
  `notes/lean-firewall-next.md` and its matching report. Exact-golden authoring,
  persistent complete-array execution and a first invalid-IPv4 body identity
  are scoped separately from later Bloom properties. Source/execution commits
  `be2c4b3`/`11d9380` are integrated at `236d404`, independently reviewed CLEAR.
  Exact source identity, persistent fixed execution and 128 focused checks
  pass, including three actual compiling fault campaigns and restored replay.
  A native-server reset survives generic IR DRT but fails the strengthened
  dedicated transcript observer. The Python register-write fault reuses the
  existing `firewall-crc32.json`, not a new distinct input. Scope and review:
  `notes/lean-firewall-port.md`. Initialization/invalid-body proof commits
  `a8480fb`/`50bd31c` are integrated at `a74f691`, independently reviewed CLEAR.
  All nine initialized roots are proved; the body theorem needs only the
  actual index and action-first invalid-IPv4 read, preserving arbitrary unused
  state and overlays. Thirteen audits, 48 native profiles and 58 Python checks
  pass, with two compiling source proof rejections and a packet-invisible
  actual Python local-write fault. Scope: `notes/lean-firewall-proof.md`.
  Exact actual Bloom insertion is integrated at `3372d45`: thirteen audited
  roots, 84 native profiles and 79 Python checks, complete two-write execution
  and explicit first-write boundary. Review found and closed a runtime-read
  coupling in expected positions. Six compiling authored-body faults and one
  actual Lean register fault are proof-rejected; a real Python other-cell
  fault produces three state-only mismatches on the existing four-packet input.
  Scope, reconstruction and CLEAR review: `notes/firewall-bloom.md`.
  Future backlog: actual two-read prefix before the decision, then drop/no-op
  composition, hash bounds and control composition. These are not milestone 1
  blockers. No exact-connection-tracking claim.
  Reviewed plan `b3defb4` is integrated at `279ed03`:
  `notes/firewall-readback-next.md`. The implementation is parked, not active;
  `notes/parked-proofs.md` records its tree, successful standalone checks and
  unfinished Python draft. It is not publicly registered or integrated.

  Four validator-accepted wrong ports fail both engines. Subsequent actual
  Python/Lean CRC XOR-one mutations pass packet-only gates but produce three
  state-only divergences in four requests. Strong known-answer/full-state
  gates kill both compiled mutants; all faults are restored. Proof audits
  do not certify CRC's intended external algorithm. Reproduction and review:
  `notes/mutations/firewall-hash-state.md`,
  `notes/reviews/firewall-hash-state.md`.
  Byte-truncation coverage is integrated from `d547a61`: all 55 cuts of one
  TCP frame, 54 valid-malformed-valid persistence sequences and 41 additional
  unchanged-original BMv2 prefix observations. Atomic-extract errors, validity
  and retained payload have independent expectations; the instrumented parser
  observer is explicitly distinct from the original oracle. An actual Python
  cursor fault creates two payload-only mismatches, automatically saves its
  five-request bundle and agrees after restoration. Review and full recipes:
  `notes/reviews/firewall-boundaries.md`, `notes/firewall-boundaries.md`.
  Generated `tcp-flow-policy-v1` is integrated from `b7f59a1`: forty shrinking
  examples per engine, full-cell independent GF(2)/zlib expectations,
  mid-sequence host policy replacement and targeted Bloom correlations.
  Three unchanged-original BMv2 scenarios add eleven prefix observations;
  host changes within one sequence remain Python/Lean-only evidence.
  An actual table-hit fault shrinks to one absent-rule SYN: packets match
  but two wrong cells expose it. The complete saved replay fails live and
  passes restored; inputs are promoted into a tracked named regression.
  See `notes/firewall-generated.md` and `notes/reviews/firewall-generated.md`.
  The external job selects this suite. Lean authoring/application proofs
  and broader profiles remain open.

- **Verification infrastructure is established; broader proofs remain open.**
  [verification.md](verification.md) records exact claims. Required real-Lean
  CI, complete-sequence failure replays, abstract extern-state comparison,
  timeout/process cleanup, typed generated scalar/stateful programs and
  shrinking are in place. Finite-trace execution soundness, scalar value
  laws and a bounded reexecution checker connect to actual production
  execution. The Python certificate producer is documented in
  [certificates.md](certificates.md); it is not universal equivalence or a
  standalone proof term. Reviews and fixes cover stale binding observations,
  malformed cells, duplicate responses and descendant process leakage.

  Earlier adversarial campaigns found and killed eager branches and
  state-only out-of-bounds/persistence faults; exact patches/replays are in
  `notes/mutations/2026-09-23.md`. Compiler/surface faults are additionally
  recorded in `lean/ASSURANCE.md`. A proof-integrity gate rejects `sorry`,
  forged axioms and unexpected transitive axioms; theorem statements still
  require review. Matching tests never prove universal Python equivalence.
  Still open: whole-program validity/soundness and termination, aggregates,
  general assignment preservation, tables/nested calls/parser-fault generation,
  further extern contracts and application properties.

  Local aggregate-copy profile `30a23b0` is integrated: sixteen header/struct,
  validity and width boundaries plus forty shrinking examples observe all
  source/target/unrelated stored fields after writes. Actual Python copy
  alias faults fail and replay live, then pass restored; independently
  expected bytes remain a separate gate. It does not establish stack or call
  copyback correctness. Scope, recipes and review: `notes/aggregate-copy.md`,
  `notes/reviews/aggregate-copy.md`.
  Bounded action/sub-control copy-in/out profile `2aa8864` is integrated:
  twelve boundaries and forty shrinking examples expose permitted overlapping
  input/inout snapshots, out-zero initialization and complete post-call values,
  validity, unrelated storage and untouched payload. Six real Python faults
  exercise argument aliasing, bad out defaults and skipped copyback, save the
  exact inputs and replay divergent/live then agreeing/restored. They yield
  two distinct retained input bundles. Overlapping writable arguments and
  action/local name collisions remain validator errors, not generated valid
  cases; no call proof follows. Scope and review: `notes/call-copy.md`,
  `notes/reviews/call-copy.md`.

- **Interchange has scoped leaf/Expr proofs, not a verified program codec.**
  Real encoder/decoder defects were fixed without adapter normalization:
  zero literals now emit decimal `"0"`; missing/null decimal string fields
  no longer become numeric zero. Forty-two wire cases include persistent
  valid/malformed/valid requests with counters exactly 1/1/2. Reviews:
  `notes/reviews/zero-encoding.md`, `decimal-wire-defaults.md`.
  Versioned representability, codec proofs, resource limits, duplicate input
  keys and unknown-field policy remain open.
  Harness hardening `44beaba` is integrated at `4ce3798`: duplicate keys and
  nonstandard constants are rejected recursively; replay envelope/version
  types and error diagnostics are checked without rejecting semantically
  invalid IR inputs. Actual lossy peers previously erased packets/state and
  falsely agreed; regressions now retain protocol-failure replays. All five
  prior concrete mutation bundles still replay through the stricter loader.
  Evidence/review: `notes/wire-harness.md`, `notes/reviews/wire-harness.md`.
  This is not general codec equivalence, semantic alias/unknown-field policy
  or a resource budget. `3fca173` plus default registration `1f69a58` prove
  actual decimal/uint32 and all Literal/Ty round trips over JSON values under
  v0 representability; semantic validity is deliberately not a premise.
  Thirty-six native checks and 94 focused checks include 48 required native
  interoperability probes. A paired wrong wire key still passes universal
  round trips but fails three independent protobuf answers. Review also fixed
  a false/zero observer ambiguity with type-sensitive JSON comparisons.
  Three raw leaf artifacts and tracked recipes preserve this boundary:
  `notes/codec-proof.md`, `notes/reviews/codec-leaves.md`.
  KeyValue increment `b2e5ef2` is integrated at `ba274f3`: every actual key
  constructor has a JSON-value round-trip law, bounding only uint32 prefix
  lengths. Arbitrary values/masks and semantically invalid keys remain in
  scope. Six paired value/mask remappings preserve round trips and encoded
  payloads but fail independent decoded-value answers; exact raw artifacts
  all replay restored. The focused codec suite now has 170 checks and native
  codec driver 52. Review: `notes/reviews/keyvalue-codec.md`; exact source
  recipes and proof boundary: `notes/keyvalue-codec.md`.
  Expr implementation `cb68f91`/`2226ebe`/`858f82a` is integrated at `e2f2849`.
  The actual decoder uses well-founded recursion over finite JSON, with
  arbitrary-input helper erasure/unfolding laws and a universal representable
  Expr roundtrip. No parallel proof-only decoder or fuel cutoff is involved;
  wire representability deliberately includes semantically invalid syntax.
  Fifty-nine pre-refactor transcripts preserve exact output/errors/status.
  Paired index remapping and an actual shared NOT/NEGATE name-table fault
  pass roundtrip proofs, but independent decoded-constructor answers reject
  them. The shared operator fault initially survived all tests, prompting
  an observer fix and native anchor. Five full raw mismatches replay restored;
  subprocess failures retain inputs before failing. Review is clear:
  `notes/reviews/expr-codec.md`; recipes/scope: `notes/expr-codec.md`.
  LValue/Arg increment `58051cc`/`8f3fa77` is integrated at `b868100`:
  actual LValue decoding is total with the old-body unfolding law, and every
  representable LValue/Arg roundtrip uses the production codecs. Arg needed
  no implementation change. All 69 original transcripts preserve exact bytes,
  errors and status. Paired operand/argument-label faults preserve roundtrip
  proofs and encoded wires but fail independent constructor/error answers;
  ten raw faults replay restored. Review is clear, isolated full/required
  gates pass; combined integration is checked separately above. Scope:
  `notes/lvalue-codec.md`, `notes/reviews/lvalue-codec.md`.
  Statement arrays are now integrated from `work/stmt-codec`,
  based on committed `1d1168c`. There is no mutual decoder recursion: only
  conditional branch lists recurse into Stmt. An independently checked
  unregistered probe proves attached-array traversal erasure, field bounds,
  repeated-field erasure and generic array roundtrip. Plan and review:
  `notes/stmt-codec-plan.md`, `notes/reviews/stmt-codec-plan.md`; probe:
  `ir/StmtCodecProbe.lean`. The production decoder now uses those bounded
  helpers, with erasure preserving the old ordinary-helper recurrence.
  Independently reviewed baseline `5cbbc85` is integrated at `8f62b31`:
  direct constructor observations, 28 canonical, 42 malformed/order and nine
  normalization requests, with four native anchors. All 79 source-matched
  raw transcripts are retained/replayed; old source hashes are pinned to
  `5cbbc85`, not expected to equal future refactored files. Reproduction
  refuses a changed old decoder or overwriting retained evidence. Scope:
  `notes/stmt-codec.md`, `notes/reviews/stmt-codec-baseline.md`.
  Totality, original-body unfolding and universal statement roundtrip
  (`dcbcf96`/`4564b66`/`70ef3e8`) are independently reviewed and integrated
  at `dcbf392`. Eight new audited roots, constructive all-constructor witnesses
  and overflow controls accompany the proof. All 79 old transcripts remain
  byte-identical; six compiling challenges distinguish proof kills from
  paired mapping/default/diagnostic faults that retain roundtrip proofs.
  All 25 retained live observations (20 distinct inputs) match tracked
  fixtures and replay restored. Evidence: `notes/stmt-codec.md`; final review:
  `notes/reviews/stmt-codec.md`. The next declaration slice has an accepted,
  independently checked plan/probe: `notes/program-codec-next.md` and its
  matching review, with `ir/DeclarationCodecProbe.lean` left unregistered.
  The separately reviewed baseline `21b0fec` is integrated: 247 exact raw
  transcripts, 102 public protobuf successes, 145 errors and 14 native anchors.
  Nine universal laws and ten audit roots are integrated at `20ce06f`, with
  production codec bytes unchanged. A one-sided encoder reversal is rejected
  by its law; three paired/order faults preserve all roundtrip proofs but
  fail 24 independent raw observations. Deliberately corrupting either Python
  expectations or the Lean observer hides the Direction fault from Python
  checks, while independent native anchors still reject it. Faulty packet
  preflight is explicitly not counted as direct codec detection. Scope and
  final review: `notes/declaration-codec.md` and its matching report.
  Baseline `9640523` is independently reviewed and integrated
  at `a5ba464`: 181 exact raw transcripts, 82 public protobuf successes,
  99 errors, direct MatchKind observation and 20 native anchors. All old
  request labels/bytes remain unchanged. Four production laws and five audits
  (`228b76b`/`7beb6af`/`661c8d8`) are integrated at `634a21a`, with unchanged
  actual codecs and 56 source-matched raw fault observations / 52 distinct
  requests. Paired fixture/observer corruption demonstrates false assurance
  that independent native anchors reject. Scope and final review:
  `notes/table-codec.md` and its matching report. Preserve the frozen baseline.
  The reviewed `notes/program-codec-completion.md` stages parser syntax,
  Action/Block and Export/Program, with host entries separate. Its six-root
  parser probe is unregistered feasibility only. The reviewed parser baseline
  `9d68d7d` is now integrated at `fd708e6`: 27 native anchors, 283 focused
  checks and 231 source-pinned raw rows (76 successes / 155 errors).
  Five universal laws and six audited roots are integrated at `ca2f20f`;
  40 fault observations over 34 distinct inputs preserve historical provenance.
  Action/Block baseline `6b9ffd0` adds 498 exact transcripts, 114 protobuf
  successes and 28 native anchors. Reviewed helper-only `707fb3f` shares nine
  unchanged actual-object facts while preserving all four Table statements.
  Both are integrated; the two universal laws and campaign also landed as
  milestone 1 closeout. The obsolete `work/block-codecs` checkout was removed
  in the 2026-09-24 cleanup; its branch and recovery archive remain available.
  Preserve historical baseline/proof hashes; current Program/Export/Entries
  test evidence is mapped in `evidence.md`.
  Text parsing, semantic-version policy, whole-program codecs and general
  runtime resource limits remain separate obligations.

- **XDP and later examples: compile-only profile integrated.**
  `notes/xdp-preflight.md` pins the authentic Ethernet-allow xdp-filter
  build and libbpf, complete per-CPU observations and an FD-only non-attaching
  oracle design. `980c642` integrates the pinned original feature build,
  offline ELF/BTF/map inspection, syscall tracing and negative fixtures.
  Required clean-runner CI `35900039992` at `63ec6d1` passes all ten checks
  without skips. Independent review verified the downloaded repeated object,
  source archive hashes and compiler provenance. Exact evidence and limits:
  `tests/oracle/xdp/README.md`, `notes/reviews/xdp-build.md`.
  No kernel load/run or p4blo behavioral equivalence is established.
  Capability-bearing execution and port redistribution licensing still need
  explicit handling.
  Do not treat Docker availability or skipped kernel tests as an oracle pass.
  Flowlet time/randomness and the bounded Katran profile still require audit.
  The runtime remains non-root, capability-free, network-free and read-only;
  no security restriction was relaxed to obtain a pass. Native CI is now a
  fifth required workflow, retaining objects/provenance/corresponding sources
  for 14 days. The local final image is unavailable because of Docker VM
  capacity: its one skip is not native evidence. Only exact own rebuildable
  cache/image data was removed, with a verified host recovery export. The
  capacity incident, failed fixture/permission checks and recovery are in
  `notes/xdp-build-progress.md`; unrelated Docker data is not a cleanup target.
  Next: an FD-only strict adapter and explicit capability-scoped execution
  preflight, independently of the ongoing Lean authoring work.
  Observer-lifecycle fix `1fecd97` is integrated: Docker client timeout had
  left a daemon-owned container alive. The helper uses a unique owned name,
  bounded cleanup and successful exact-name absence verification. Seven pure
  failure-path regressions and live normal/timeout probes pass. Review:
  `notes/reviews/xdp-cleanup.md`. Daemon outages, forced interpreter death
  and late creation races remain outside the scoped cleanup guarantee.
  No kernel or semantic claim follows.

- **eDSL v2: done** (2026-09-22, reviewed and fixed 2026-09-23). The
  typed surface is `p4blo.edsl`, the v1 builder is `p4blo.edsl.core`;
  all eleven corpus programs are authored in v2 with byte-identical
  goldens, type-checked in CI; `tests/test_pyright.py` guards the
  static rules with must-pass and must-fail fixtures. The review is
  `notes/reviews/edsl-v2.md` and every finding is fixed.
- **BMv2 as a second oracle: done** (`tests/oracle/bmv2/`, its own CI job). It
  decides longest prefix, const-entry and ternary priorities without the
  translation P4-SpecTec needs. It cannot see `flood`, which no corpus
  program declares; a program that does would be the way to test it.
- **Playground** (Pyodide/marimo) was removed from the plan on
  2026-09-22; the pure-Python and Python 3.13 constraints keep it
  possible.
- **Unconfirmed review points left open**, from
  `notes/reviews/steps2-5.md`: checksum16 padding for data widths not
  a multiple of 16 has not been judged by the oracle; sub-block
  instance names `<block>_inst` are not checked against the caller's
  scope; a case with both a bad entry and a bad port reports different
  first errors on Python and Lean.
- **Three type checkers** compute expression types: the validator,
  `interp/widths.py`, and the printer's `_Typer`; they must agree, and
  one would do. The typed eDSL is a fourth, at a different level.
- **The p4c backend is deferred behind verification.** The design names it so
  that p4c's whole test suite becomes the corpus. It is the community
  version's first job and the experiment that would really test claim 1;
  `docs/writeup.md` section 5 and 4ward are the route.
- **Elaborated-but-unexercised rows** of `coverage.md` (functions,
  newtypes, constructor parameters, named arguments) are rulings, not
  performed rewrites; a p4c backend is the experiment that would test
  them.

## Blocked

Nothing.
