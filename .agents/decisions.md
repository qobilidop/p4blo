# Decisions

Decisions in force, with reasons and original dates. Supersede entries in place. The latest
archive is `d2f9dbd6fefacc80da40d4f6fba294c819cd4d28`. Its topical register
preserves the current minimal architecture and oracle judgments. Earlier registers are at
`34ce204e4a8be7633133a715e10c9ac6a8b891b1`,
`9fc6c19febf839fa56873be10788b515c4e29ae9` and `26c93485861bc5442076a1060fcc8d1743952702`;
the chronological log is `docs/decisions.md` at `9e8f7d47e582de3d9813d4d91c152efdb2b6`.
Design and semantics pages hold contracts; this register keeps choices and boundaries.

## Environment and tooling

- **Ordinary commands by default; pinned tools optional.** `uv sync --locked` and
  `.python-version` select Python 3.13. `flake.nix`/`flake.lock` pin the same tools for `nix
  develop`, direnv and CI; docs do not require them. Lean comes from elan because nixpkgs
  lags; oracle-only OCaml lives in `devShells.oracle`. Preserve historical command
  transcripts. (2026-09-24)
- **No devcontainer:** uv serves contributors avoiding Nix; a non-flake container would
  drift. Revisit for Windows without WSL2. **Python 3.13, pure Python:** no native code in
  the package; imposing this now is free, reopening it later is not. (2026-09-22)
- **p4c/BMv2 from `github.com/qobilidop/p4lang-builds`:** native amd64/arm64 p4c
  1.2.5.15/BMv2 1.15.4 images with immutable tags; the official amd64-only p4c image crashed
  under ARM emulation. Pin p4c by index digest. Docker golden typechecking is optional
  locally, skipped without Docker, because building p4c is disproportionate. (2026-09-22)
- **Pin every external input for reproducibility.** `docs/workflows.md` lists image digests,
  Actions commits, opam repository commit and source SHA-256s. (2026-09-22)
- **Fresh Lean caches after package moves; build before testing.** Copied caches shadow
  renamed modules in standalone queries. Rebuild from empty build directories after moves;
  never rebuild while tests consume that worktree's executable. (2026-09-23)
- **CI restores main's compiled Lean `lib`/`ir`, never `bin`; only main saves.** Caching
  avoids costly cold builds; `lake build` rejects deleted source imports despite stale
  `.olean`s. Revisit if gates query outside `lake build`/`lake test`. **Parallel
  differential CI:** two deterministic node-ID hash shards, each using `-n auto --dist
  load`, cover every selected case exactly once. Each builds/audits before testing; only
  shard 1 saves main's cache. Module grouping would serialize unrelated tests. Confidence
  high on coverage preservation; observed timings are not guarantees. Revisit shard count if
  runner overhead dominates. (2026-09-25)
- **Proven prose-only changes skip specialist CI; Python/schema always run.** The user
  delegated this policy choice. A narrow regular-Markdown allowlist excludes parsed/executed
  docs; unknown paths, unavailable history, type/mode changes and classifier failure request
  full CI. PR scope covers the whole branch diff, not just its latest commit. Superseded PR
  runs cancel, main runs do not. This saves repeated oracle/Lean work without reducing cases
  for executable changes. Revisit the allowlist when a heavy gate gains a documentation
  input. (2026-09-25)
- **Docker disk pressure authorizes only own-artifact cleanup**, never unrelated images.
  (2026-09-23)

## Layout and ownership

- **Lean owns abstract syntax, validity and meaning; protobuf owns wire syntax.** Conversion
  has separate proof obligations. `spec/ir/` is `P4bloIR`/`p4blo-ir`, schema beside it,
  nothing architectural; `spec/arch/` is `P4bloArch`/`p4blo-arch`, depending on IR and
  supplying tested v1model/extern adapters and `p4blo-lean`, without architecture-proof
  guarantees. Python in `impl/python/` is the authoring surface. Retire the separate
  `impl/lean/` typed-source/application package to focus limited resources on the core IR.
  (ownership 2026-09-23; simplification 2026-09-25)
- **Lean follows Mathlib/Batteries layout:** client imports under `<Root>/`, gate-only
  tests/audits/probes in one singular `<Root>Test` library, avoiding global `Tests`
  collisions. Roots contain Lake's required files, README and at most one Main, with schemas
  under `spec/ir/proto/` and `spec/arch/proto/`. `p4blo-lean` serves runtime/validation
  checks; acronyms stay capitalized. `test_package_layout.py` prevents unregistered probes
  and executable-root sprawl. (2026-09-24; schema exception 2026-09-25)
- **Extern state is first-order data; its model is a function.** `ExternState` carries kind,
  optional width, cells and private configuration; the architecture supplies `ExternModel`
  at load. This keeps `Run` unparameterized and cells inspectable: closure threading lacked
  a total Lean definition; type parameters through all theorems were invasive without
  expressive gain. Confidence medium; revisit if cells cannot carry a family's structured
  state. (2026-09-24)
- **Commit generated protobuf code** in `impl/python/p4blo/v0/` and
  `impl/python/p4blo/arch/v0/`; CI regenerates and rejects drift. (2026-09-22; architecture
  path 2026-09-25)
- **Python is organized by concern.** `validator` groups rule categories behind one
  `validate`; `validator.typer` alone supplies expression types to interpreter, printer and
  STF (a top-level typer would cycle through diagnostic codes). The architecture-free
  printer has five binding hooks; `frontend` bridges P4-SpecTec IL. (2026-09-25)
- **Tests group by question** in `tests/`: unit, codec, programs, drt, lean, external and
  structure, with READMEs and pinned layout; data/drivers separate. Module stem or `bmv2` in
  the name assigns the `oracle` marker. Shared verification belongs in `tests/`; public
  applications in `examples/`, their checks in `tests/examples/`. (assets 2026-09-23;
  examples 2026-09-24; test grouping 2026-09-25)
- **Public APIs may change for demonstrated usability gains.** Preserve semantic
  contracts/readability, separate authoring from meaning changes, and migrate callers with
  diagnostic and golden tests. (2026-09-23)

## IR and wire syntax

- **`p4blo.v0` is deliberately pre-1.0:** except buf's version-suffix lint in `buf.yaml`,
  rather than rename to `v1alpha1`. (2026-09-22)
- **One kind-tagged Block** avoids tripling shared machinery; **scoped-name references**
  make goldens read like programs; **typed oneofs** describe about twenty fixed operators;
  **no expression annotations**, since typed leaves, value widths and one validator
  inference suffice and annotations double goldens. **Dedicated packet/header nodes**
  reverse directly in the printer, leaving externs to mean declared externs. **Separate
  expressions and lvalues:** dotted-path sugar is a second syntax unable to express indices.
  **Annotation fields start at 100** to separate metadata; **rename Python-keyword fields**
  to avoid `getattr`; **table size is informative** for printer roundtrips. (2026-09-22)
- **`int<N>` is outside v0:** no corpus need, twice the arithmetic rules; additive when
  wanted. **Elaborations:** slice lvalues become whole-field read-modify-write;
  `switch(action_run)` becomes an action-assigned local and if-chain; `type` like `typedef`;
  inline functions; instantiate a block per constructor arguments. Out by scope, additive:
  `string`, non-header arrays, `packet_in.length()`, static extern methods, mutable initial
  entries/per-entry `const`, object initializers, abstract methods. Out by thesis: `range`,
  `optional`, `..` in entries, since core.p4 declares only exact/ternary/lpm. The bridge
  performs coverage-table rewrites and refuses excluded rows by name. (2026-09-22; bridge
  2026-09-24)
- **Larger entry priority wins; const numbering follows the specification.** Default
  `largest_priority_wins` preserves explicit `priority = n`; implicit entries decrement the
  preceding priority by `priority_delta`, beginning at `(k - 1) * delta + 1`. P4 ignores
  p4c's non-language `@priority`; p4c's BMv2 counter and smaller-wins ranking invert
  specification order. The `priority` corpus follows the specification and classifies the
  source's BMv2 disagreement strictly. Printed explicit priorities with
  `largest_priority_wins = true` pass both oracles. Reason: P4's mechanization, not a
  compiler backend, defines the reference meaning. (2026-09-24)
- **Emit decimal strings including zero; reject missing strings.** Protobuf defaults to
  empty and Lean's absent-as-zero decoder hid the defect. **Canonical interchange only:**
  unknown fields, enum numbers and camelCase differ between parsers. Reject ambiguous JSON
  before information is lost, without validating away invalid IR needed for experiments.
  (2026-09-23)

## Python eDSL

- **Blocks are the authoring unit; optional BlockLibrary is not a program.** It bundles
  blocks/shared types, errors and extern declarations, without H/M, roles, ports or fate.
  Python/protobuf/Lean core libraries validate independently; architecture BlockBindings
  selects H/M/exports. Core validity/progress stays separate from tested binding/entry
  behavior. Reason: `p4.Program` conflated authoring and composition; arbitrary export names
  alone left the wire H/M convention intact. (2026-09-25)
- **Assembly recompiles in one shared context, without a fragment linker.** This preserves
  declaration order and type/sub-block/extern identity. Core libraries exclude bindings;
  architecture's flat BlockAssembly adapter keeps old payload fields/bytes, intentionally
  changing descriptors/generated APIs. It preserves corpus transports without making
  assembly a complete program or returning binding choices to core. (2026-09-25)
- **Concrete externs belong to architecture support; registration is local and explicit.**
  Generic `edsl.Extern`; typed families/dynamic helpers in `arch.externs.declarations`;
  Registry binds independent Shapes through per-instance factories. Generic loading requires
  registry, contract and role kinds; `arch.v1model` chooses the supplied environment.
  Python registration supplies neither Lean meaning nor printer support. Reason: core
  language must not imply a built-in switch or fixed services. (2026-09-25)
- **Readability before syntax.** Router/firewall/load-balancer examples use domain aliases,
  symbolic predicates and build-time helpers, with explicit assignments/runtime branches.
  Unchanged goldens and independent packet/state tests anchor acceptance. Keep examples
  self-contained; share only for demonstrated authoring gains. (2026-09-25)
- **Four pyright-forced deviations from static type safety:** width aliases and typed
  literals type as places (literal targets fail at runtime); Bool/Enum/Error have no static
  place split; extern `in` accepts values with runtime width checks; sub-block arguments are
  runtime-checked. Overloaded `assign` failures are `reportCallIssue`; must-fail fixtures
  and `tests/unit/test_pyright.py` pin static rules. (2026-09-22)

## Semantics rulings

- **`docs/ir-semantics.md` is the deviation ledger** for equivalence up to elaboration/known
  deviation; architecture choices go in `docs/arch-supports.md`. Each entry has P4 section,
  pinned P4-SpecTec rule, Lean definitions/theorems, Python function and tests, classified
  same, refines undefined, deviates or not representable. `tests/ledger-classes.json` pins
  classes; `docs/ledger-xref.md` is generated. Unlisted differences are bugs, not rulings
  invented during fixes: the deviation list must be checkable. **Lean is executable and
  proved, checked against P4-SpecTec, never normative**: that would claim authority the
  evidence does not give this independent P4-inspired project; the reference is P4-SpecTec's
  elaborated IL. (2026-09-24)
- **Re-zero uninitialized parser-state/action/inlined-function locals on every entry.**
  P4-SpecTec enters fresh scopes; IR block locals retain values. Bridge review exposed
  validated disagreements, requiring elaboration resets. (2026-09-24; eDSL followed
  2026-09-25)
- **Parser bound is no-consumption revisit, not fuel:** fuel makes meaning depend on an
  unspecified number; revisit agrees with BMv2. (2026-09-22)
- **Minimal architecture support is core blocks plus scoped v1model.** Parser,
  Control and Deparser remain kinds of one core Block; P4bloParser/P4bloControl/
  P4bloDeparser name the oracle interface. Retire Filter/custom Switch/flood.
  Six independent pipeline roles preserve drop/state boundaries; unsupported
  native services reject explicitly. Only core IR is formally verified.
  Reason: focus limited resources on useful behavior with independent oracles.
  Profile details live in docs/arch-supports.md. (2026-09-25)
- **Judge discrepancies against the applicable contract, not an oracle vote.**
  docs/oracle-discrepancies.md owns paired minimal cases, pins and dispositions.
  BMv2's selected destination and pre-egress zero request define our target
  profile; P4-SpecTec's different native outputs are exact regressions. Where
  the language leaves behavior unspecified, label our deterministic policy.
  Reason: independent implementations can share defects or implement different
  extensions; agreement alone cannot define correctness. (2026-09-25)
- **Out-of-range register reads yield zero**, unlike BMv2's unchanged target; P4 leaves this
  implementation-defined. Keep the exact vector's strict xfail; revisit only if a corpus
  program depends on it. (2026-09-22)
- **CRC16/CRC32 are stateless, exact byte-aligned widths, full results, no padding/range
  reduction.** Independent answers exposed P4-SpecTec's odd-byte defect; BMv2 confirms
  standard behavior. Contract: `docs/assurance.md`. (2026-09-23)
- **Statements use an explicit continuation machine:** total single-operation steps and a
  proof-visible fixpoint connect finite traces to results; termination for validated
  programs remains separate. (2026-09-23)

## Oracles and corpus

- **P4-SpecTec is primary for IR meaning; BMv2 breaks known defects** (odd-byte CRC32
  padding, masks) and judges simulator limits (real lpm, const/runtime ternary priorities,
  shifts above its builtin limit of 2048). Reason: P4-SpecTec mechanizes P4. Compare printed
  P4 through v1model, blocks through patched simulation, and IL through the bridge.
  (2026-09-24)
- **Block simulation uses the minimal `p4blo` architecture** in `tests/oracle/p4blo.watsup`
  and OCaml patch `0001`, on given headers, metadata, entries and extern state. Build
  stamp/cache key include patch digest. Families use v1model implementations; refuse entries
  needing its STF name maps (no corpus need yet). Accept differences only via checked models
  of the exact defect, never tags. Reason: pipeline observations hid register cells. Offer
  upstream when stable; both patches may move to `p4-spectec-lean`, which already forks
  P4-SpecTec. (2026-09-24)
- **The IL bridge is the P4 frontend, not verified.** Patch0002 exports
  instantiated P4 program IR. Preserve all six v1model roles without merging;
  rename colliding user fields instead of equating them to intrinsic fields.
  Reject native verify_checksum until checksum_error is supported. Original
  source comparisons account for explicit authored schedule choices; round
  trips check stage structure and packet/extern state rather than byte identity.
  Reason: fused controls hid architecture boundaries. (2026-09-25)
- **P4-SpecTec's Lean rendering belongs to `p4-spectec-lean`.** p4blo owns IR, meaning,
  elaboration and validation; no duplicate rendering/interpreter, trace-localized N+1
  testing, new simulator patches beyond the two, or bridge census beyond corpus. Freeze
  oracle machinery as the rendering's test bed and keep bridge small for the eventual
  theorem. `docs/design.md` gives consumed interfaces. Reason: duplicate rendering wastes
  effort and splits trust. (2026-09-24)
- **Conformance corpus is fixed Lean answers in `tests/conformance/`.** Canonical one-line
  answer diffs; `refresh` reanswers tracked inputs, never generates; `export` adds inputs.
  Record semantics/binary digests and reject stale binaries via `lake build --no-build`,
  time comparison fallback. Format 2 has only nonzero cells; two contract fixtures cover
  rejected installs/unicast/drop/invalid ports and egress redirection attempts. State changed semantics before refreshing.
  (2026-09-24)
- **P4-SpecTec coverage:** 8-dynamic rules/functions and 3-operations functions, builtins
  included; corpus, examples and fixed greedy seeds. Outside calls report `called_in_scope`
  without enforcement, avoiding eight exclusions for unions, compound assignment and
  overload helpers. Regenerate the inventory `tests/oracle/spectec-rules.json` at each pin
  bump. (2026-09-24)
- **STF vectors** use the dialect in `impl/python/p4blo/stf.py`. The simulator lacks
  longest-prefix selection, so `tests/oracle/run.py` supplies prefix priorities; BMv2 judges
  real lpm/const/runtime ternary priority. Printed ternary entries are non-const because p4c
  1.2.5 refuses const priorities. Known gap: printed const lpm entries lack priorities;
  overlaps fail on P4-SpecTec until the printer adds them. (2026-09-22)
- **Corpus uses STF-bearing p4c tests plus own programs.** The unchanged tutorial firewall
  is independent input; a scoped BMv2 barrier reads all 8192 cells. Valid only for pinned
  single-ingress FIFO; revisit before recirculation/asynchronous externs. (2026-09-22,
  2026-09-23)
- **Challenge original-program oracles; do not copy them.** Strict pinned discrepancy tests
  have passing controls; never adapt inputs for agreement. Strict XPASS rejects stale
  exceptions; BMv2 xfails name exact vector/status/mismatch. Discover Lean
  `test_lean_agrees` tests across the tree. (2026-09-23)
- **Own and verify every Docker check container; never prune globally.** (2026-09-23)
- **Remove the premature XDP compile-only experiment.** User-requested: compiling an
  upstream program neither executed it nor validated a p4blo application, so the
  workflow/toolchain/inspector/tests cost maintenance without supporting P4 claims. Revisit
  only for a concrete application and independent execution oracle. Preserve historical
  evidence; recover files at `b7860a5`. Confidence high: no interpreter/schema dependency.
  (2026-09-25)

## Verification and proof boundaries

Current claims and premises are in `docs/assurance.md` and the core audit files. Retired
authoring/architecture proof history is recoverable from
`5ee52d90f19d5d5a81bf972a115298ae167e691b`; it is not current assurance.

- **Follow Cedar:** executable formal model, property proofs, typed generators, component
  differential testing; implementations share only wire syntax, with no universal
  Python/Lean equivalence claim. (2026-09-23)
- **Adequacy means rule coverage, not counts.** Lean witness pairs pin rule conditions;
  retained `tests/drt-coverage-parts/` union covers inventory except shrinking-only
  `tests/drt-unhit-tags.json`. Every unhit in-scope P4-SpecTec rule needs a reason. Keep
  guidance only when measured useful; the pair-reward term was measured and removed.
  (2026-09-24, 2026-09-25)
- **Replay complete experiments:** versioned program/request sequences from fresh state;
  observe logical extern state after every request as hex strings. Missing state fails.
  **Mutate both sides** in isolated worktrees; survivors become tests, build failures are
  not semantic kills. `scripts/check-assurance.py` replays a finite reviewed catalogue, not
  a mutation-score guarantee. (2026-09-23)
- **Survivors drive generation:** scalar boundaries, recursively typed expressions, stateful
  programs with independent register/counter bounds, host changes; type-preserving
  shrinking, invalid programs fail rather than filter, failures saved in `.artifacts/drt/`.
  Host changes within sequences are Python/Lean-only: original BMv2 cannot replace rules
  mid-sequence. Revisit before claiming original-oracle host-change coverage. (2026-09-23)
- **Proof trust is gated** by `lake build --wfail`: warnings fail without changing the
  severities `#guard_msgs` observes (adopted from `p4-spectec-lean`, 2026-09-25).
  `<Root>Test` audits advertised theorems' transitive axioms to catch imported axioms/
  native shortcuts; intended meaning still needs review. (2026-09-23)
- **Retire the fixed execution-certificate experiment.** It packaged bounded reexecution of
  one example and added no general Python correctness claim. Keep ordinary differential
  testing and core semantic proofs instead. Revisit only for a concrete consumer needing
  checked execution claims. (2026-09-25)
- **Review observers adversarially; anchor every roundtrip independently.** Paired faults
  preserve laws. Independent known answers and constructor observations reject them.
  (2026-09-23)
- **Total decoders recurse well-foundedly over finite JSON**, no proof-only duplicate.
  **Fixed-application evidence is separate from generic replay:** exact state/numeric
  contracts accompany packets; exhaust named malformed profiles before random traffic.
  (2026-09-23)
- **Core library validity is over the index:** `Valid p idx`, checked in Python validator
  order/codes by `Validity.check`, proved by `Validity.check_sound`; no completeness claim.
  Progress needs the generic `ExternContract` and a Run fitting block kind; `InstalledOk`
  follows real `Installed.build`. Architecture bindings and concrete externs keep runtime
  checks/tests but no soundness/discharge or non-vacuity proof claims. Wire-shape errors are
  Lean `DECODE`. Termination/completeness remain open. (2026-09-24; library split and
  assurance simplification 2026-09-25)
- **Deviation theorems cover runtime closed behavior only.** Installation, binding and
  architecture entries have no theorem because their meaning is outside the IR evaluator.
  (2026-09-24)
- **Keep application behavior tests with independent expected answers.** Retire
  Lean-authored applications and their proofs, preserving Python examples, state/packet
  anchors, useful fault tests and oracle coverage. Unique historical readback/ingress drafts
  stay recoverable on parked branches; they are retired research, not a continuation queue.
  (2026-09-25)
- **Formal assurance targets architecture-free core IR only.** The user explicitly
  prioritized limited resources: retain existing core validity/progress/semantic/codec
  proofs and independent conformance tests; remove Lean authoring, application/architecture
  proofs and exclusive support machinery. No new proof family, architecture or importer
  expansion is part of simplification. Python authoring and the P4 importer remain tested
  tools. Confidence: high for this phase; revisit for a concrete user need that justifies
  the proof cost. (2026-09-25)

## Scope and process

- **Full architecture-independent P4 is a north star, not a deliverable.** (2026-09-23)
  **Frozen scopes:** assurance milestone 1 at `3148a52` (2026-09-23), Python application
  collection at `c94336d` (2026-09-24), architecture-free semantics at `26c9348`
  (2026-09-25). Keep architecture/applications/claim 3 green without expansion; value is IR
  and meaning. Playground out; p4c backend deferred behind verification as the community
  version's first job. (2026-09-22 to 2026-09-25)
- **Website is static/dependency-free**, GitHub Pages from `website/`, with walkthrough
  generated from tested VLAN gateway. (2026-09-24)
- **Review independently after each step.** Record revision/patch, reproducers,
  checks/limits in `.agents/reviews/`; fix findings before integration so reports identify
  the work integrated. (2026-09-25)
- **PRs are optional during the personal-project phase.** To reduce overhead, the user
  authorizes autonomous commits, pushes and integration, including substantive work. Use
  feature branches/worktrees when useful, including WIP, or commit directly to main. Keep
  coherent commits, independent final-patch review, full local gate before push and
  applicable remote CI on the exact integrated main revision before completion. Fix failures
  with follow-up commits; never bypass protections. Use a PR when requested or required,
  with final-head review and remote CI before merge. Confidence high for this phase; revisit
  when collaboration/release needs justify PRs. (2026-09-25)
- **When used, PRs explain problem, result, tradeoffs, validation/limits without chat
  context.** Re-read final diff; one AI-disclosure sentence names the verified session
  agent/model; agent review is not human review. Adopt Git/Google/GitHub and
  p4-spectec-lean guidance without boilerplate. Sources/boundaries: archived
  `.agents/notes/engineering-practices.md` at `9fc6c19febf839fa56873be10788b515c4e29ae9`.
  (2026-09-25)
- **Generated-file gates compare inventory and bytes to index and working tree** using clean
  temporary generation, negative tests and one local/CI script: in-place regeneration misses
  new/untracked/stale outputs. **Tracked files max 5 MiB in either tree:** stage
  deliverables first; prefer reproducible generation, small losslessly compressed
  snapshots/raw checksums or pinned artifacts. No published-history rewrites without scope.
  This preventive budget follows p4-spectec-lean, not hosting limits. (2026-09-25)
- **Record uncertainty's confidence/revisit trigger.** (2026-09-23) **Park unfinished work
  as pushed WIP branches, never uncommitted worktrees.** Compare with main, delete
  merged/identical branches, archive obsolete worktrees before removal. Fragile untracked
  drafts and falsely unique branches prompted this. (2026-09-24)
- **Full gate before push; record its exit, not a log reader's.** `tail` once hid a failing
  gate; structural smoke missed codec paths. Builders run lint/types/affected tests and Lean
  if touched, full gate for cross-cutting work; integrators gate each batch once, then
  verify remote CI. This avoids duplication without losing integration coverage.
  `scripts/check.sh` runs non-oracle suites with parallel load scheduling; oracle workflows
  cover the rest. At most two heavy local jobs. (2026-09-24, 2026-09-25)
- **Docs split by subject:** artifact in `docs/`, resumable work in `.agents/`, sole entry
  point `AGENTS.md`; `test_docs_links.py` forbids docs links into agent state. **Compact at
  milestones; git is archive:** record tree hash in status first, promote artifact notes,
  remove completed history, preserve claims and review against archive. No tags (user
  instruction). This avoids stale diaries/plans while git retains every byte. **Skills live
  once in `.agents/skills/`**, reached through Claude's committed `.claude/skills` symlink.
  (2026-09-24)
