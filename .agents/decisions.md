# Decisions

Decisions in force, grouped by topic, with reasons and original dates. Rewrite
superseded entries in place with the new date/reason; remove only subjects that
no longer exist. The
chronological log is `docs/decisions.md` at archive
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6` (2026-09-24). Earlier registers are
this path at `26c93485861bc5442076a1060fcc8d1743952702` and
`9fc6c19febf839fa56873be10788b515c4e29ae9` (2026-09-25). Design and semantics
pages hold the contracts; this register keeps choices, reasons and boundaries.

## Environment and tooling

- **Ordinary commands by default; pinned tools optional.** `uv sync --locked`
  and `.python-version` select Python 3.13. `flake.nix`/`flake.lock` pin the
  same tools for `nix develop`, direnv and CI; docs do not require them. Lean
  comes from elan because nixpkgs lags; oracle-only OCaml lives in
  `devShells.oracle`. Preserve historical command transcripts. (2026-09-24)
- **No devcontainer:** uv serves contributors avoiding Nix; a non-flake
  container would drift. Revisit for Windows without WSL2.
  **Python 3.13, pure Python:** no native code in the package; imposing this
  now is free, reopening it later is not. (2026-09-22)
- **p4c/BMv2 from `github.com/qobilidop/p4lang-builds`:** native amd64/arm64
  p4c 1.2.5.15/BMv2 1.15.4 images with immutable tags; the official amd64-only
  p4c image crashed under ARM emulation. Pin p4c by index digest. Docker
  golden typechecking is optional locally, skipped without Docker, because
  building p4c is disproportionate. (2026-09-22)
- **Pin every external input for reproducibility.** `docs/workflows.md`
  lists image digests, Actions commits, opam repository commit and source
  SHA-256s. (2026-09-22)
- **Fresh Lean caches after package moves; build before testing.** Copied
  caches shadowed renamed modules in standalone queries; rebuild from empty
  build directories after a move. Never rebuild while the worktree's tests
  consume the executable.
  (2026-09-23)
- **CI restores main's compiled Lean `lib`/`ir`, never `bin`; only main
  saves.** Cold builds cost 346 s of 21 minutes. `lake build` rejects deleted
  source imports despite stale `.olean`s (`P4bloIR/Coverage.lean` removal probe,
  2026-09-25). Revisit if gates query outside `lake build`/`lake test`.
  **Parallel differential CI** uses two deterministic node-ID hash shards
  with `-n auto --dist load` inside each. Every selected case runs once across
  the pair, each runner builds/audits before testing, and only shard 1 saves
  main's build cache. The previous single runner spent 411 s in tests after
  a warm 50 s build. Its intended module groups never reached xdist in time;
  activating them would serialize unrelated tests, so remove them instead.
  Confidence: high on coverage preservation, performance pending remote
  measurement; revisit shard count if runner overhead dominates. (2026-09-25)
- **Proven prose-only changes skip specialist CI; Python/schema always run.**
  The user delegated this policy choice. A narrow regular-Markdown allowlist
  excludes parsed/executed docs; unknown paths, unavailable history, type/mode
  changes and classifier failure request full CI. PR scope covers the whole
  branch diff, not just its latest commit. Superseded PR runs cancel, main
  runs do not. This saves repeated oracle/Lean work without reducing cases
  for executable changes. Revisit the allowlist when a heavy gate gains a
  documentation input. (2026-09-25)
- **Docker disk pressure authorizes only own-artifact cleanup**, never
  unrelated images.
  (2026-09-23)

## Layout and ownership

- **Lean owns abstract syntax, validity and meaning; protobuf owns wire
  syntax.** Conversion has separate proof obligations. `spec/ir/` is
  `P4bloIR`/`p4blo-ir`, schema beside it, nothing architectural;
  `spec/arch/` is `P4bloArch`/`p4blo-arch`, depending on IR and supplying
  switch, externs, certificate example and `p4blo-lean`; `impl/lean/` is
  `P4blo`/`p4blo`, depending on both. Python lives in `impl/python/`.
  (ownership 2026-09-23; three-package layout 2026-09-24)
- **Lean follows Mathlib/Batteries layout:** client imports under `<Root>/`,
  gate-only tests/audits/probes in one singular `<Root>Test` library; bare
  `Tests` collides across packages. Roots contain only Lake's required files,
  README and at most one Main, except `spec/ir/proto/`, `spec/arch/proto/`
  and `impl/lean/ASSURANCE.md`. One `p4blo` binary has user subcommands;
  acronyms remain capitalized. `test_package_layout.py` pins this, replacing
  flat packages with unregistered probes and sixteen executable roots.
  (2026-09-24; architecture-schema exception 2026-09-25)
- **Extern state is first-order data; its model is a function.**
  `ExternState` carries kind, optional width, cells and private configuration;
  the architecture supplies `ExternModel` at load, keeping `Run`
  unparameterized and cells inspectable. Closure state threading lacked a
  total Lean definition; a type parameter through all theorems was invasive
  with no expressive gain. Confidence medium in the representation; revisit
  if cells cannot carry a family's structured state.
  (2026-09-24)
- **Commit generated protobuf code** in `impl/python/p4blo/v0/` and
  `impl/python/p4blo/arch/v0/`; CI regenerates and rejects drift.
  (2026-09-22; architecture path 2026-09-25)
- **Python is organized by concern.** `validator` groups rule categories
  behind one `validate`; `validator.typer` alone supplies expression types
  to interpreter, printer and STF (a top-level typer would cycle through
  diagnostic codes). The architecture-free printer has five binding hooks;
  `frontend` bridges P4-SpecTec IL. (2026-09-25)
- **Tests group by question** in `tests/`: unit, codec, programs, drt, lean,
  external and structure, with READMEs and pinned layout; data/drivers separate.
  Module stem or `bmv2` in the name assigns the `oracle` marker. Shared
  verification belongs in `tests/`; public applications in `examples/`,
  their checks in `tests/examples/`. (assets 2026-09-23; examples 2026-09-24;
  test grouping 2026-09-25)
- **Public APIs may change for demonstrated usability gains.** Preserve
  semantic contracts/readability, separate authoring from meaning changes,
  and migrate callers with diagnostic and golden tests. (2026-09-23)

## IR and wire syntax

- **`p4blo.v0` is deliberately pre-1.0:** except buf's version-suffix lint
  in `buf.yaml`, rather than rename to `v1alpha1`. (2026-09-22)
- **One kind-tagged Block** avoids tripling shared machinery; **scoped-name
  references** make goldens read like programs; **typed oneofs** describe
  about twenty fixed operators; **no expression annotations**, since typed
  leaves, value widths and one validator inference suffice and annotations
  double goldens. **Dedicated packet/header nodes** reverse directly in the
  printer, leaving externs to mean declared externs. **Separate expressions
  and lvalues:** dotted-path sugar is a second syntax unable to express
  indices. **Annotation fields start at 100** to separate metadata;
  **rename Python-keyword fields** to avoid `getattr`; **table size is
  informative** for printer roundtrips. (2026-09-22)
- **`int<N>` is outside v0:** no corpus need, twice the arithmetic rules;
  additive when wanted. **Elaborations:** slice lvalues become whole-field
  read-modify-write; `switch(action_run)` becomes an action-assigned local
  and if-chain; `type` like `typedef`; inline functions; instantiate a block
  per constructor arguments. Out by scope, additive: `string`, non-header
  arrays, `packet_in.length()`, static extern methods, mutable initial
  entries/per-entry `const`, object initializers, abstract methods. Out by
  thesis: `range`, `optional`, `..` in entries, since core.p4 declares only
  exact/ternary/lpm. The bridge performs coverage-table rewrites and refuses
  excluded rows by name. (2026-09-22; bridge 2026-09-24)
- **Larger entry priority wins; const numbering follows the specification.**
  Default `largest_priority_wins` preserves explicit `priority = n`; implicit
  entries decrement the preceding priority by `priority_delta`, beginning at
  `(k - 1) * delta + 1`. P4 ignores p4c's non-language `@priority`; p4c's
  BMv2 counter and smaller-wins ranking invert specification order. The
  `priority` corpus follows the specification and classifies the source's
  BMv2 disagreement strictly. Printed explicit priorities with
  `largest_priority_wins = true` pass both oracles. Reason: P4's mechanization,
  not a compiler backend, defines the reference meaning. (2026-09-24)
- **Emit decimal strings including zero; reject missing strings.** Protobuf
  defaults to empty and Lean's absent-as-zero decoder hid the defect.
  **Canonical interchange only:** unknown
  fields, enum numbers and camelCase differ between parsers. Reject ambiguous
  JSON before information is lost, without validating away invalid IR needed
  for experiments. (2026-09-23)

## Python eDSL

- **Blocks are the authoring unit; optional BlockLibrary is not a program.**
  It bundles blocks/shared type, error and extern declarations, without H/M
  roots, roles, ports or fate. Independently compiled core libraries validate
  without architecture programs; protobuf/Lean core also use BlockLibrary.
  Architecture BlockBindings selects H/M/exports. Core validity/progress and
  architecture binding/entry guarantees stay separate. Reason: the user
  rejected `p4.Program` conflating authoring with composition; arbitrary
  export names alone leave the wire H/M convention intact. (2026-09-25)
- **Assembly recompiles in one shared context, without a fragment linker.**
  This preserves declaration order and type/sub-block/extern identity. Core
  libraries exclude bindings; architecture's flat BlockAssembly adapter keeps
  old payload fields/bytes, intentionally changing descriptors/generated APIs.
  It preserves corpus transports without making assembly a complete program
  or returning binding choices to core. (2026-09-25)
- **Concrete externs belong to architecture support; registration is local
  and explicit.** Generic `edsl.Extern`; typed families/dynamic helpers in
  `arch.externs.declarations`; Registry binds independent Shapes through
  per-instance factories. Generic loading requires registry, contract and
  role kinds; `arch.reference` chooses the supplied environment. Python
  registration supplies neither Lean meaning nor printer support. Reason:
  core language must not imply a built-in switch or fixed services.
  (2026-09-25)
- **Readability before syntax.** Router/firewall/load-balancer examples use
  domain aliases, symbolic predicates and build-time helpers, with explicit
  assignments/runtime branches. Unchanged IR goldens and independent packet/
  state tests anchor acceptance. Keep examples self-contained; share code only
  for demonstrated authoring gains. (2026-09-25)
- **Four pyright-forced deviations from static type safety:** width aliases
  and typed literals type as places (literal targets fail at runtime);
  Bool/Enum/Error have no static place split; extern `in` accepts values with
  runtime width checks; sub-block arguments are runtime-checked. Overloaded
  `assign` failures are `reportCallIssue`; must-fail fixtures and
  `tests/unit/test_pyright.py` pin static rules. (2026-09-22)

## Semantics rulings

- **`docs/ir-semantics.md` is the deviation ledger** for equivalence up to
  elaboration/known deviation; architecture choices go in
  `docs/arch-supports.md`. Each entry has P4 section, pinned P4-SpecTec rule,
  Lean definitions/theorems, Python function and tests, classified same,
  refines undefined, deviates or not representable. `tests/ledger-classes.json`
  pins classes; `docs/ledger-xref.md` is generated. Unlisted differences are
  bugs, not rulings invented during fixes: the deviation list must be checkable.
  **Lean is executable and proved, checked against P4-SpecTec, never normative**:
  that would claim authority the evidence does not give this independent
  P4-inspired project; the reference is P4-SpecTec's elaborated IL. (2026-09-24)
- **Re-zero uninitialized parser-state/action/inlined-function locals on
  every entry.** P4-SpecTec enters fresh scopes; IR block locals retain values.
  Bridge review exposed validated disagreements, requiring elaboration resets.
  (2026-09-24; eDSL followed 2026-09-25)
- **Parser bound is no-consumption revisit, not fuel:** fuel makes meaning
  depend on an unspecified number; revisit agrees with BMv2. (2026-09-22)
- **Metadata/architecture rules:** design fixes fields; fate booleans let the
  forwarder run unchanged under switch. Require byte alignment; off-byte
  parsing drops; control runs after parser rejection. Undeclared contract
  fields read zero/swallow writes; `parser_error` follows parser `inout`
  writes and precedes control. Filter forwards original bytes, so its expected
  vectors use input bytes. **Port rules:** `0..ports-1`; invalid egress drops
  with diagnostic, invalid ingress is caller error before execution; filter
  has no port count. BMv2 drop port 511 is out of range here. (2026-09-22)
- **Out-of-range register reads yield zero**, unlike BMv2's unchanged target;
  P4 leaves this implementation-defined. Keep the exact vector's strict xfail;
  revisit only if a corpus program depends on it. (2026-09-22)
- **CRC16/CRC32 are stateless, exact byte-aligned widths, full results,
  no padding/range reduction.** Independent answers exposed P4-SpecTec's
  odd-byte defect; BMv2 confirms standard behavior. Contract:
  `docs/assurance.md`. (2026-09-23)
- **Statements use an explicit continuation machine:** total single-operation
  steps and a proof-visible fixpoint connect finite traces to results;
  termination for validated programs remains separate. (2026-09-23)

## Oracles and corpus

- **P4-SpecTec is primary for IR meaning; BMv2 breaks known defects**
  (odd-byte CRC32 padding, masks) and judges simulator limits (real lpm,
  const/runtime ternary priorities, shifts above its builtin limit of 2048).
  Reason: P4-SpecTec mechanizes P4. Compare printed P4 through v1model, blocks
  through patched simulation, and IL through the bridge. (2026-09-24)
- **Block simulation uses the minimal `p4blo` architecture** in
  `tests/oracle/p4blo.watsup` and OCaml patch `0001`, on given headers,
  metadata, entries and extern state. Build stamp/cache key include patch
  digest. Families use v1model implementations; refuse entries needing its
  STF name maps (no corpus need yet). Accept differences only via checked
  models of the exact defect, never tags. Reason: pipeline observations hid
  register cells. Offer upstream when stable; both patches may move to
  `p4-spectec-lean`, which already forks P4-SpecTec. (2026-09-24)
- **The IL bridge is the P4 frontend, not verified.** Patch `0002` exports
  instantiated IL JSON. Translate coverage-table constructs; merge v1model
  verify/ingress/egress/compute, skipping egress after drop. Map standard
  metadata to contract fields; rename colliding user fields, restoring names
  only where synchronization matches the printer shim. Drop follows
  `egress_spec == 511` at ingress end, written explicitly only when egress
  needs it; metadata parameter is `meta`. Fold only what IR cannot hold;
  name table-action copies like p4c. Corpus comparison encodes each documented
  difference explicitly so new differences fail. (2026-09-24)
- **P4-SpecTec's Lean rendering belongs to `p4-spectec-lean`.** p4blo owns IR,
  meaning, elaboration and validation; no duplicate rendering/interpreter,
  trace-localized N+1 testing, new simulator patches
  beyond the two, or bridge census beyond corpus. Freeze oracle machinery as
  the rendering's test bed and keep bridge small for the eventual theorem.
  `docs/design.md` gives consumed interfaces. Reason: duplicate rendering
  wastes effort and splits trust. (2026-09-24)
- **Conformance corpus is fixed Lean answers in `tests/conformance/`.**
  Canonical one-line answer diffs; `refresh` reanswers tracked inputs, never
  generates; `export` adds inputs. Record semantics/binary digests and reject
  stale binaries via `lake build --no-build`, time comparison fallback.
  Format 2 has only nonzero cells; two contract fixtures cover rejected
  installs/flood/drop/invalid ports. State changed semantics before refreshing.
  (2026-09-24)
- **P4-SpecTec coverage:** 8-dynamic rules/functions and 3-operations functions,
  builtins included; corpus, examples and fixed greedy seeds. Outside calls
  report `called_in_scope` without enforcement, avoiding eight exclusions for
  unions, compound assignment and overload helpers. Regenerate the inventory
  `tests/oracle/spectec-rules.json` at each pin bump.
  (2026-09-24)
- **STF vectors** use the dialect in `impl/python/p4blo/stf.py`. The simulator
  lacks longest-prefix selection, so `tests/oracle/run.py` supplies prefix
  priorities; BMv2 judges real lpm/const/runtime ternary priority. Printed
  ternary entries are non-const because p4c 1.2.5 refuses const priorities.
  Known gap: printed const lpm entries lack priorities; overlaps fail on
  P4-SpecTec until the printer adds them. (2026-09-22)
- **Corpus uses STF-bearing p4c tests plus own programs.** The unchanged
  tutorial firewall is independent input; a scoped BMv2 barrier reads all
  8192 cells. Valid only for pinned single-ingress FIFO; revisit before
  recirculation/asynchronous externs. (2026-09-22, 2026-09-23)
- **Challenge original-program oracles; do not copy them.** Strict pinned
  discrepancy tests have passing controls; never adapt inputs for agreement.
  Strict XPASS rejects stale exceptions; BMv2 xfails name exact vector/status/
  mismatch. Discover Lean `test_lean_agrees` tests across the tree. (2026-09-23)
- **Own and verify every Docker check container; never prune globally.**
  **XDP is pinned compile-only preflight**, no kernel or equivalence claim.
  (2026-09-23)

## Verification and proof boundaries

Exact theorem statements and premises remain in `impl/lean/ASSURANCE.md`
and the audit files; these entries record choices and limits.

- **Follow Cedar:** executable formal model, property proofs, typed generators,
  component differential testing; implementations share only wire syntax,
  with no universal Python/Lean equivalence claim. (2026-09-23)
- **Adequacy means rule coverage, not counts.** Lean witness pairs pin rule
  conditions; retained `tests/drt-coverage-parts/` union covers inventory except
  shrinking-only `tests/drt-unhit-tags.json`. Every unhit in-scope P4-SpecTec
  rule needs a reason. Keep guidance only when measured useful; the pair-reward
  term was measured and removed. (2026-09-24, 2026-09-25)
- **Replay complete experiments:** versioned program/request sequences from
  fresh state; observe logical extern state after every request as hex strings.
  Missing state fails. **Mutate both sides**
  in isolated worktrees; survivors become tests, build failures are
  not semantic kills. `scripts/check-assurance.py` replays a finite reviewed
  catalogue, not a mutation-score guarantee. (2026-09-23)
- **Survivors drive generation:** scalar boundaries, recursively typed
  expressions, stateful programs with independent register/counter bounds,
  host changes; type-preserving shrinking, invalid programs fail rather than
  filter, failures saved in `.artifacts/drt/`. Host changes within sequences
  are Python/Lean-only: original BMv2 cannot replace rules mid-sequence.
  Revisit before claiming original-oracle host-change coverage. (2026-09-23)
- **Proof trust is gated** with `lake build --wfail`: warnings fail the build
  while preserving severities
  observed by `#guard_msgs` (adopted 2026-09-25 from `p4-spectec-lean`).
  `<Root>Test` audits advertised theorems' transitive axioms, catching imported
  axioms/native shortcuts; intended theorem meaning still requires review.
  (2026-09-23)
- **Certificates are bounded actual-machine reexecution**, neither a faster
  verifier nor a proof term. (2026-09-23)
- **Review observers adversarially; anchor every roundtrip independently.**
  Paired faults preserve laws. Independent known answers and constructor
  observations reject them.
  (2026-09-23)
- **Total decoders recurse well-foundedly over finite JSON**, no proof-only
  duplicate. **Fixed-application evidence is separate
  from generic replay:** exact state/numeric contracts accompany packets;
  exhaust named malformed profiles before random traffic. (2026-09-23)
- **First validity boundary is closed scalar.** Exact frames differ from
  declaration validity; aggregate shape, nominal coherence and write permission
  are separate; initialization uses bounded layers; call laws concern actual
  execution. (2026-09-23)
- **Core library validity is over the index:** `Valid p idx`, checked in Python
  validator order/codes by `Validity.check`, proved by `Validity.check_sound`;
  no completeness claim. Architecture H/M/
  exports use `P4bloArch.Bindings.check_sound`. Progress needs `ExternContract`
  (five reference families via `P4bloArch.Contract.bind_contract`) and a Run
  fitting block kind; `InstalledOk` follows real `Installed.build`; csum16
  inhabits premises by kernel check. Wire-shape errors are Lean `DECODE`.
  Termination/completeness remain open. (2026-09-24; library split 2026-09-25)
- **Deviation theorems cover runtime closed behavior only.** Installation,
  binding and architecture entries have no theorem because their meaning is
  outside the IR evaluator. (2026-09-24)
- **Applications are named policies with asymmetric known-answer anchors**:
  paired relabeling preserves proofs; readback/ingress proofs stay parked.
  **One shared operator AST and one command AST; notation waits for a real
  application. Codec proofs proceed baseline
  first.** (2026-09-23)
- **No new application/typed-source theorems until simulation with the
  P4-SpecTec rendering.** Existing proofs give internal consistency; IL bridge
  landed 2026-09-24 and the P4 claim now awaits `p4-spectec-lean`. Proof effort
  goes to termination/codec composition. (2026-09-24; reason 2026-09-25)

## Scope and process

- **Full architecture-independent P4 is a north star, not a deliverable.**
  (2026-09-23) **Three complete, frozen scopes:** assurance milestone 1 at `3148a52`
  (2026-09-23), router/firewall/load-balancer collection at `c94336d`
  (2026-09-24), architecture-free semantics at `26c9348` (2026-09-25).
  Architecture/applications/XDP/claim 3 stay green, not extended: value is
  the IR and meaning. Playground out; p4c backend deferred behind verification,
  the community version's first job. (2026-09-22 to 2026-09-25)
- **Website is static/dependency-free**, GitHub Pages from `website/`, with
  walkthrough generated from tested VLAN gateway. (2026-09-24)
- **Review independently after each step**, report revision/patch, reproducers,
  checks/limits in `.agents/reviews/`; fix findings on the working branch before
  integration so the
  report identifies the work actually merged. (2026-09-25)
- **Substantive work uses PRs; trivial nonbehavioral maintenance may use main.**
  Autonomous commits/pushes/merges are authorized, never protection bypasses.
  Integrate sub-agent commits on PR branches; distinguish review/local/remote
  evidence, require final-head remote CI, recheck SHA. Merge coherent commits;
  squash WIP preserving rationale/attribution; rebase only on explicit linear
  preference. Reason: adopt the user's p4-spectec-lean practice to protect main
  while keeping useful history. (2026-09-25)
- **PRs explain problem, result, tradeoffs, validation/limits without chat
  context.** Re-read final diff; one AI-disclosure sentence names the verified
  session agent/model; agent review is not human review. Adopt Git/Google/
  GitHub and p4-spectec-lean guidance without boilerplate. Sources/boundaries:
  archived `.agents/notes/engineering-practices.md` at
  `9fc6c19febf839fa56873be10788b515c4e29ae9`. (2026-09-25)
- **Generated-file gates compare inventory and bytes to index and working
  tree** from clean temporary generation, with negative tests and one local/CI
  script: in-place regeneration plus diff misses new/untracked/stale outputs.
  **Tracked files max 5 MiB in either tree:** stage deliverables before gates;
  prefer reproducible generation, small losslessly compressed snapshots/raw
  checksums or pinned
  artifacts; no published-history rewrites without scope. Adopt p4-spectec-lean's
  preventive budget while files fit (~0.5 MiB largest), not a hosting limit.
  (2026-09-25)
- **Record uncertainty's confidence/revisit trigger.** (2026-09-23)
  **Park unfinished work as pushed WIP branches, never uncommitted worktrees;**
  compare to main, delete merged/identical branches, archive obsolete worktrees
  before removal. Fragile untracked drafts and falsely unique branches prompted
  this. (2026-09-24)
- **Full gate before push, recorded exit status rather than log-reader exit:**
  `tail` once pushed red main; structural smoke checks once missed codec path
  failures. Builders run lint/types/affected tests plus Lean if touched, full
  gate for cross-cutting work; integrator gates each batch once, then final
  remote CI. This avoids redundant gates without losing integration coverage.
  `scripts/check.sh` parallelizes non-oracle suites with load scheduling;
  oracle workflows cover the rest. At most two heavy local jobs.
  (2026-09-24, 2026-09-25)
- **Docs split by subject:** public artifact in `docs/`, resumable work in
  `.agents/`, sole entry point `AGENTS.md`; `test_docs_links.py` forbids docs
  links into agent state. **Compact at milestones; git is archive:** record
  tree hash in `status.md` first, promote artifact notes, remove completed
  history, preserve
  claims, review against archive. No tags (user instruction; earlier tag
  deleted). Reason: stale diary/plan growth, with every byte already in git.
  **Skills live once in `.agents/skills/`**, reached by Claude's committed
  `.claude/skills` symlink. (2026-09-24)
