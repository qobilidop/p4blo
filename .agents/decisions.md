# Decisions

The decisions in force, grouped by topic, each with its reason and the
date it was made. This is a register, not a diary: an entry that is
superseded is rewritten in place with the new date and reason, and an
entry whose subject no longer exists is removed. The chronological log
is in git: `docs/decisions.md` at the first archive commit
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6` (2026-09-24), and this file
at the second, `26c93485861bc5442076a1060fcc8d1743952702` (2026-09-25).
A decision the design document already settles is not repeated here.

## Environment and tooling

- **Ordinary commands are the documented default; pinned tools are
  optional.** `uv sync --locked` installs the Python environment and
  `.python-version` selects Python 3.13. `flake.nix`/`flake.lock` provide
  the same tools pinned, entered with `nix develop` or direnv, and CI uses
  them; the documentation does not assume them. Lean comes from elan, not
  nixpkgs, which lags Lean releases. The OCaml toolchain for the
  P4-SpecTec oracle lives in `devShells.oracle`, not the default shell.
  Historical command transcripts are preserved as written. (2026-09-24)
- **No devcontainer**; the uv-only tier serves people who avoid Nix.
  Revisit for a Windows contributor without WSL2. (2026-09-22)
- **Python 3.13, pure Python.** No native code in the `p4blo` package.
  (2026-09-22)
- **p4c and BMv2 come from `github.com/qobilidop/p4lang-builds`**, native
  amd64/arm64 images of p4c 1.2.5.15 and BMv2 1.15.4 with immutable tags,
  because the official p4c image is amd64 only and crashed under
  emulation on ARM; p4c is pinned by index digest, and p4c through Docker
  is an optional local check of the printer's goldens, skipped without
  Docker, since building p4c is out of proportion. (2026-09-22)
- **Every external input is pinned, and the pins are listed** in
  `docs/workflows.md`: images by digest, GitHub Actions by commit, the
  oracle's opam repository by commit, sources by SHA-256. (2026-09-22)
- **Fresh Lean caches across package moves; build before testing.** A
  copied build cache once shadowed renamed modules. Rebuild from empty
  build directories after a move, and never rebuild Lean while a test in
  the same worktree runs the executable. (2026-09-23)
- **Local Docker disk pressure is not permission to delete unrelated
  images**; remove only own artifacts. (2026-09-23)

## Repository layout and ownership

- **Lean owns the abstract IR, validity and meaning; protobuf owns the
  encoding.** Conversion between them is an explicit obligation with its
  own proofs. (2026-09-23)
- **Three Lake packages, specifications under `spec/` and implementations
  under `impl/`.** `spec/ir/` is `P4bloIR` (package `p4blo-ir`) with the
  wire schema beside it and nothing architectural in it; `spec/arch/` is
  `P4bloArch` (package `p4blo-arch`): the switch, the extern families, the
  certificate example and the `p4blo-lean` endpoint; `impl/lean/` is the
  user library `P4blo` (package `p4blo`); the Python package is
  `impl/python/`. (2026-09-24)
- **Lean package roots follow the Mathlib and Batteries layout.** Under
  `<Root>/` if a client may import it; under `<Root>Test/` if only the
  gate runs it (tests, proof audits and probes), as one `lean_lib` named
  `<Root>Test`, singular, because Lake module names are global across a
  workspace and a bare `Tests` in two packages collides; at the root only
  what Lake requires, with `spec/ir/proto/`, `spec/arch/proto/` and
  `impl/lean/ASSURANCE.md` as the named exceptions. The user package's
  executables are subcommands of one `p4blo` binary. Acronyms stay
  capitalized (`P4bloIR`, as Lean core's `Lean.Compiler.IR`).
  `tests/structure/test_package_layout.py` pins the roots. (2026-09-24;
  architecture schema exception added 2026-09-25)
- **The IR carries extern state as data and takes the model as a
  function.** `ExternState` is a kind name with optional width, cells and
  private configuration; the architecture supplies the `ExternModel` at
  load. This keeps `Run` unparameterized and state first-order. A closure
  in the instance and a type parameter through every theorem were both
  rejected. Confidence medium in the representation; revisit if a family
  needs structured state that cells cannot carry. (2026-09-24)
- **Generated protobuf code is committed** at `impl/python/p4blo/v0/` and
  `impl/python/p4blo/arch/v0/`; CI regenerates and fails on drift.
  (2026-09-22; architecture path added 2026-09-25)
- **The Python package is organized by concern**: `p4blo.validator` is a
  package by rule category with one public `validate`; expression types
  come from `p4blo.validator.typer` alone, which the interpreter, the
  printer and the STF reader call (a top-level module would need the
  diagnostic codes and create an import cycle); `p4blo.printer` prints P4
  with no architecture of its own and the architectures bind it through
  five hooks; `p4blo.frontend` is the bridge from SpecTec's IL.
  (2026-09-25)
- **Tests are grouped by the question they answer** under
  `tests/{unit,codec,programs,drt,lean,external,structure}/`, each with
  a README; data and drivers stay in their own directories; the layout is
  pinned. The `oracle` marker, assigned by module stem or by `bmv2` in
  the name, marks what drives an external oracle. (2026-09-25)
- **Shared verification assets live under `tests/`**; public applications
  under `examples/` with their verification under `tests/examples/`.
  (2026-09-23, 2026-09-24)
- **Existing public APIs may change for demonstrated usability gains.**
  Preserve the semantic contract and readable examples; keep authoring
  changes separate from semantics changes; migrate callers with
  diagnostic and golden tests. (2026-09-23)

## IR and wire syntax

- **Proto package `p4blo.v0`**, pre-1.0 by design; buf's version-suffix
  lint rule is excepted in `buf.yaml` rather than renaming to `v1alpha1`.
  (2026-09-22)
- **One `Block` message with a kind tag**; **references by scoped name,
  not integer id**; **typed oneofs, not a generic node**; **no type
  annotations on expressions** (leaves are typed, values carry widths,
  the validator computes every type once); **dedicated nodes for packet
  and header operations**, so "externs" means declared externs only;
  **expressions and lvalues stay separate messages**; **field numbers 100
  and above are reserved for annotations**; **fields named after Python
  keywords are renamed**; **table `size` is informative**. (2026-09-22)
- **`int<N>` is out of scope for v0**; additive when wanted. (2026-09-22)
- **Elaborations, named in the coverage table.** A slice as an lvalue is
  a read-modify-write of the whole field; `switch` on `action_run` is a
  block local each action assigns plus an if-chain; P4 `type` is
  elaborated like `typedef`; functions are inlined; constructor
  parameters give one block per instantiation. Out by scope, each
  additive if wanted: `string`, non-header arrays, `packet_in.length()`,
  static extern methods, mutable initial entries and per-entry `const`,
  object initializers, abstract methods. Out by thesis: `range`,
  `optional` and `..` in entries, since core.p4 declares only exact,
  ternary and lpm. The bridge performs the rewrites the page's Bridge
  column marks and refuses excluded rows by name. (2026-09-22, performed
  2026-09-24)
- **Entry priority: larger wins, everywhere in the IR, and const entries
  take the language specification's numbering.** With the default
  `largest_priority_wins`, an entry written with `priority = n` keeps `n`
  and an entry without one takes the previous priority minus
  `priority_delta`, the first starting at `(k - 1) * delta + 1`, so the
  first listed entry ranks highest; p4c's `@priority` annotation is not
  part of the language and the specification ignores it. p4c's BMv2
  backend numbers with a running counter that BMv2 reads smaller-wins,
  inverting the order; the `priority` corpus program follows the
  specification and BMv2's answer is a strict classified disagreement.
  The printer writes explicit `priority = n` with
  `largest_priority_wins = true`, which both oracles honor. Reason: the
  reference for what P4 means is the specification's mechanization, not
  the reference compiler's backend. (2026-09-24)
- **Decimal strings are always emitted, including zero, and a missing
  one is rejected, never read as zero.** (2026-09-23)
- **The tested canonical wire domain is stated; arbitrary ProtoJSON parity
  is not promised.** Unknown fields, enum numbers and camelCase aliases
  differ between the two parsers and are documented outside interchange
  parity. The differential harness rejects ambiguous JSON before any
  information is lost; semantically invalid IR stays representable for
  experiments. (2026-09-23)

## Python eDSL

- **Blocks are the public authoring unit; an optional `BlockLibrary` is
  not a complete program.** It bundles block definitions and shared type,
  error and extern declarations, with no global H/M roots, export roles,
  ports or packet-fate policy. Independent compilation produces a core
  library that can be validated without a complete architecture program.
  The protobuf and Lean core use BlockLibrary too. Architecture BlockBindings
  selects H/M roots and exports; core validity and progress concern libraries,
  while architecture binding checks and entry theorems retain their guarantees.
  Reason: the user rejected `p4.Program` as conflating core authoring with
  architecture composition; arbitrary export names alone do not remove the
  wire envelope's H/M calling convention. (2026-09-25)
- **Architecture assembly recompiles a library in one shared context.**
  It does not link independently compiled protobuf fragments. This preserves
  declaration order and shared type, sub-block and extern identities without
  introducing a linker. Core protobuf libraries exclude binding fields; an
  explicitly architecture-owned flat BlockAssembly adapter preserves existing
  payload fields/bytes. Descriptor names and generated APIs change intentionally.
  Reason: keep old corpus transports without putting binding choices back into
  the core or claiming that an assembly is a complete program. (2026-09-25)
- **Concrete extern declarations are architecture support; registration is
  explicit and local.** `edsl.Extern` is generic; supplied typed families and
  dynamic helpers live in `arch.externs.declarations`. A Registry binds
  independently described implementation Shapes through per-instance
  factories. Generic loading requires registry, contract and role kinds;
  `arch.reference` explicitly selects the supplied environment. Python
  registration provides neither Lean semantics nor printer support.
  Reason: core language constructs must not appear to include a built-in
  switch or a fixed set of stateful services. (2026-09-25)
- **Example readability precedes new syntax.** The router, firewall and
  load balancer use domain type aliases, symbolic predicates and ordinary
  build-time helpers, retaining explicit assignments and runtime branches.
  Their unchanged IR goldens and independent packet/state tests are the
  acceptance anchors. Keep each example self-contained; extract a shared
  library only for a demonstrated authoring gain. (2026-09-25)

- **The typed eDSL is type-safe by construction where pyright allows and
  run-time checked where it does not**, deviating from its design note in
  four places the type checker forced: width aliases and typed literals
  type as places, so a literal used as a target is caught at run time
  only; `Bool`, `Enum` and `Error` targets have no static place split;
  extern `in` parameters accept any value with the width checked at run
  time; sub-block call arguments are run-time checked. `assign` is
  overloaded over target kinds, so pyright reports a failed assignment as
  `reportCallIssue`, and the must-fail fixtures say so.
  `tests/unit/test_pyright.py` guards the static rules. (2026-09-22)
- **A local declared without an initializer inside a parser state or an
  action is re-zeroed at every entry** by the eDSL, as the bridge does
  (see Semantics rulings; the ruling is of 2026-09-24, the eDSL followed
  on 2026-09-25).

## Semantics rulings

Rulings on behavior P4 leaves open are written in `docs/ir-semantics.md`,
or in `docs/arch-supports.md` when an architecture or extern family
decides them; these entries record why.

- **`docs/ir-semantics.md` is a deviation ledger and the contract for
  "equivalent to P4-SpecTec up to elaboration and known deviation".**
  Every closed behavior has a fixed template (P4 section, SpecTec rule
  at the pin, Lean definitions and theorems, Python function, tests) and
  a class: same, refines undefined, deviates, not representable; the
  classes are pinned in `tests/ledger-classes.json` and
  `docs/ledger-xref.md` is generated from the entries. An unlisted
  difference from SpecTec is a bug on one side, never a ruling made in a
  fix. Reason: "up to known deviation" must be a checkable list.
  (2026-09-24)
- **The Lean definitions are "executable and proved, checked against
  SpecTec", never "normative".** p4blo is an independent P4-inspired
  project; the reference for what P4 means is SpecTec's elaborated IL.
  (2026-09-24)
- **A local declared without an initializer inside a parser state, an
  action or an inlined function is re-zeroed at every entry by the
  elaboration**, because SpecTec enters a fresh scope per state and per
  call and the IR has only block locals. Reason: the bridge review showed
  both interpreters and SpecTec disagreeing on validated programs.
  (2026-09-24)
- **The parser loop bound is the no-consumption revisit rule**, not fuel.
  (2026-09-22)
- **Metadata contract fields are fixed** as the design's table; fate as
  booleans so the forwarder runs unchanged under the switch; byte-aligned
  parsing required; the control runs after a parser rejection. **Port
  rules**: ports are `0` to `ports - 1`; an out-of-range `egress_port`
  drops with a diagnostic; an out-of-range `ingress_port` is the caller's
  error before anything runs; the filter has no port count; BMv2's drop
  port 511 is an out-of-range port here. **Architecture rules the design
  left open**: a parse ending off a byte boundary drops the packet; an
  undeclared contract field reads as zero and swallows writes;
  `parser_error` is written after the parser's own `inout` writes and
  before the control; the filter forwards the original bytes, so its
  tests rewrite expectations to the input bytes. (2026-09-22)
- **An out-of-range register read yields zero, diverging from BMv2
  knowingly.** BMv2 leaves the destination untouched; P4 leaves this
  implementation-defined; a strict xfail on the one vector, not resolved.
  Revisit only if a corpus program depends on it. (2026-09-22)
- **CRC16/CRC32 are stateless extern families with exact byte-aligned
  widths**, full results and no padding; the contract is in
  `docs/assurance.md`. (2026-09-23)
- **Statement execution uses an explicit continuation machine.** A total
  step function performs one operation and the interpreter drives it
  through a proof-visible fixpoint, so finite traces imply the driver's
  result. (2026-09-23)

## Vectors, oracles and corpus

- **P4-SpecTec is the primary oracle for the IR's meaning; BMv2 is the
  tie-breaker where SpecTec is known wrong** (odd-byte CRC32 padding, mask
  construction) and for what the simulator cannot judge (real longest
  prefix, const-entry and runtime ternary priorities; shift amounts above
  2048, which its builtins refuse).
  Reason: SpecTec is the mechanization of P4 itself. Comparison happens
  at three levels: printed P4 through the v1model shim, block by block on
  the patched simulator, and at the IL level through the bridge.
  (2026-09-24)
- **Block-level comparison runs on a patched simulator.** A minimal
  `p4blo` architecture, whose SpecTec-language definition is the tracked
  file `tests/oracle/p4blo.watsup` and whose OCaml is patch `0001`, runs
  one block on the given headers, metadata, entries and extern state;
  the build stamp and the CI cache key include the patch digest. Extern
  families run on v1model's OCaml implementations; entries needing
  v1model's STF name rewrites are refused rather than rewritten. Known
  differences are accepted only through checked models of the exact
  defect, never by tag. Reason: through the pipeline the simulator could
  never show its register cells. Offer the patch upstream when it
  stabilizes; both patches are candidates to move to `p4-spectec-lean`,
  which forks SpecTec anyway. (2026-09-24)
- **The IL bridge is the frontend from P4 source.** Patch `0002` exports
  the instantiated IL structurally as JSON and `p4blo.frontend`
  translates it as the coverage page prescribes. v1model in reverse:
  verify, ingress, egress and compute merge into one control whose egress
  part runs only when the packet is not dropped; `standard_metadata`
  fields become the contract fields, every user field named like one is
  renamed and the contract name is given back only where the program
  synchronizes the field exactly as the printer's shim does; the drop is
  translated as v1model decides it, from `egress_spec` being 511 at the
  end of ingress, written out only where an egress part needs it; the
  metadata parameter is `meta`; constant folding is kept to what the IR
  cannot hold; per-table action copies are named as p4c names them.
  Corpus goldens are compared with the bridge's output and every
  documented difference is an explicit change in the test. Not a
  verified frontend. (2026-09-24)
- **SpecTec is rendered into Lean elsewhere; this repository builds the
  IR, its meaning, the elaboration and the validation suite.** The user's
  project `p4-spectec-lean` compiles P4-SpecTec's elaborated spec into
  Lean and verifies that compiler. p4blo builds no Lean rendering or
  interpreter of SpecTec's rules, no trace-localized N+1 testing, no
  simulator patch beyond the two that exist, and no bridge census beyond
  the corpus; it freezes the oracle machinery as the rendering's test bed
  and keeps the bridge small as the elaboration side of the eventual
  theorem. The interfaces that project consumes are in `docs/design.md`.
  Reason: building the rendering twice wastes the effort and splits the
  trust. (2026-09-24)
- **The conformance corpus is Lean's answers on fixed inputs, tracked as
  data** under `tests/conformance/`, canonical so a changed answer is a
  one-line diff; `refresh` re-answers tracked requests and never runs a
  generator, `export` adds inputs; a fixture records the digest of the
  semantics sources and of the binary, and a stale binary is refused by
  asking Lake (`lake build --no-build`), with a time comparison as the
  fallback; format 2 lists only nonzero cells; two contract fixtures
  cover rejected installs, floods, drops and out-of-range ports. A changed
  answer is refreshed only after the semantics page states the changed
  behavior. (2026-09-24)
- **The SpecTec coverage scope is the rules and functions of 8-dynamic
  and the functions of 3-operations, builtins included**, measured over
  the corpus, the examples and a fixed greedy set of generated seeds;
  functions outside those sections are reported as `called_in_scope` but
  not enforced (eight exclusions' worth); the rule inventory at the pin is
  the tracked fixture `tests/oracle/spectec-rules.json`, regenerated at a
  pin bump. (2026-09-24)
- **STF is the vector format.** Dialect conventions are recorded in
  `impl/python/p4blo/stf.py`. The simulator has no longest-prefix rule, so
  `tests/oracle/run.py` supplies prefix lengths as priorities; BMv2
  decides real lpm, const-entry and runtime ternary priorities; printed
  ternary entries are not const, since p4c 1.2.5 refuses priorities on
  them. Known gap: printed const lpm entries carry no priorities, so a
  program whose const lpm entries overlap fails on SpecTec until the
  printer adds them. (2026-09-22)
- **Corpus programs come from p4c's test suite** where STF vectors exist,
  plus programs of our own. **The original tutorial firewall is an
  independent oracle input**, its state observed through a scoped BMv2
  barrier reading all 8192 cells; valid for the pinned single-ingress
  FIFO implementation, revisit before recirculation or asynchronous
  externs. (2026-09-22, 2026-09-23)
- **An original-program oracle is evidence to challenge, not a definition
  to copy**: strict discrepancy tests with passing controls record pinned
  SpecTec's defects; inputs are never adapted to manufacture agreement;
  strict XPASS prevents stale exceptions; a BMv2 expected failure names
  the exact vector, status and mismatch. (2026-09-23)
- **Conformance suites are discovered, not enumerated**: required Lean CI
  selects `test_lean_agrees` tests across the tree. (2026-09-23)
- **Every Docker check container is owned and verified**; never prune
  globally. (2026-09-23)
- **XDP is a compile-only preflight** with pinned sources and no kernel
  load or behavioral-equivalence claim. (2026-09-23)

## Verification method

- **Verification follows Cedar's method**: an executable formal model,
  property proofs, typed generators and component-level differential
  testing; universal Python-Lean equivalence is not claimed, and the
  models share wire syntax only. (2026-09-23)
- **The adequacy criterion for generated testing is coverage of the
  semantics' rules, not test counts.** The Lean machine reports the rules
  each case exercises; witness pairs pin each rule's condition; the
  retained campaigns' hits are recorded per part under
  `tests/drt-coverage-parts/` and their union must cover the inventory
  except `tests/drt-unhit-tags.json`, which may only shrink; SpecTec's
  rules are measured over p4blo's inputs and every unhit in-scope rule is
  excluded with a reason. Guidance toward unhit rules is kept only where
  measured to help; the pair-rewarding term was measured and removed.
  (2026-09-24, 2026-09-25)
- **Replay the whole experiment**: a differential failure is a versioned
  bundle with the program and the complete request sequence. **Observe
  logical extern state after every request**, as hexadecimal strings;
  missing state fails. (2026-09-23)
- **Adversarial verification is recurring work**: mutants on both sides
  in isolated worktrees, survivors become tests; a build failure is not a
  semantic kill. `scripts/check-assurance.py` replays a finite, reviewed
  catalogue from tracked fixtures. (2026-09-23)
- **Mutation survivors drive generated-program coverage**: systematic
  scalar boundaries, recursively typed generated expressions, generated
  stateful programs with independent register and counter bounds, and
  generated host policy changes; shrinking preserves types; invalid
  generated programs fail rather than being filtered; failed programs
  are retained under `.artifacts/drt/`. Host changes within one sequence
  are Python/Lean-only evidence: the original BMv2 protocol cannot
  replace rules mid-sequence, so revisit that limitation before claiming
  original-oracle coverage of host changes. (2026-09-23)
- **Proof trust is a build gate.** The gate builds with
  `lake build --wfail`, so a warning fails the build without rewriting
  the severities `#guard_msgs` tests observe (adopted from
  `p4-spectec-lean`, 2026-09-25); the audit modules of the `<Root>Test`
  libraries check advertised theorems' transitive axioms. (2026-09-23)
- **Execution certificates are bounded reexecution of the actual
  machine**, not a faster verifier or a proof term. (2026-09-23)
- **Observers are reviewed as adversarially as evaluators**, and
  **independent anchors accompany every roundtrip proof and observer**,
  since paired faults preserve every law. (2026-09-23)
- **Decoders are total through well-founded recursion over finite JSON**,
  with no proof-only duplicate decoder. (2026-09-23)
- **Fixed-application evidence is kept separate from generic IR replay**,
  and exact state and numeric contracts beside packet equivalence; a
  named malformed profile is exhausted before broad random traffic.
  (2026-09-23)

## Lean authoring and proof boundaries

The exact theorem statements are in `impl/lean/ASSURANCE.md` and the
audit files; these entries record the shape.

- **The first sound validity boundary is the closed scalar fragment**;
  exact frame agreement is distinct from declaration validity; aggregate
  shape, nominal coherence and write permission are separate obligations;
  initialization is discharged in bounded layers; call laws are proved
  operationally against the actual machine. (2026-09-23)
- **Core library validity is defined over the index and decided by a
  checker proved sound; completeness is not claimed.** `Valid p idx`
  states the library contract, `Validity.check` decides it in the Python
  validator's order with its codes, `Validity.check_sound` is proved.
  Architecture H/M roots and exports are checked separately by
  `P4bloArch.Bindings.check`, with `P4bloArch.Bindings.check_sound`. Progress
  takes two premises: `ExternContract`, proved for the five reference
  families (`P4bloArch.Contract.bind_contract`), and that the run fits
  the block kind; `InstalledOk` is discharged from the real
  `Installed.build`; a kernel-checked instance on csum16 shows the
  premises are inhabited. Wire-shape problems are `DECODE` on the Lean
  side. Termination and completeness stay open. (2026-09-24, 2026-09-25)
- **Deviation theorems cover the run-time closed behaviors only**; the
  entries that belong to installation, binding or the architecture have
  no theorem, because their meaning lives outside the IR's evaluator.
  (2026-09-24)
- **Applications are separately named policies with independent
  anchors.** A proved state mapping is still anchored by a hand-built
  asymmetric known answer, because a paired relabeling preserves the
  proofs. Further readback and ingress proofs are parked. (2026-09-23)
- **No new application or typed-source-language theorems until the
  simulation theorem with the SpecTec rendering exists.** The theorems so
  far establish p4blo's internal consistency; the IL bridge landed on
  2026-09-24, and the claim about P4 now waits on `p4-spectec-lean`.
  Proof effort goes to termination and codec composition. (2026-09-24,
  reason updated 2026-09-25)
- **One shared operator AST and one command AST**; custom notation waits
  for a real application. **Codec laws are composed in baseline-first
  slices.** (2026-09-23)

## Scope and milestones

- **Full architecture-independent P4 is a north star, not a deliverable.**
  (2026-09-23)
- **Three finite scopes are complete and frozen**: assurance milestone 1
  (`3148a52`, 2026-09-23), the application collection of router, stateful
  firewall and load balancer (`c94336d`, 2026-09-24), and the
  architecture-free IR semantics scope (`26c9348`, 2026-09-25).
  Architectures, applications, XDP and claim 3 are kept green, not
  extended. The playground is out; the p4c backend is deferred behind
  verification. (2026-09-22 to 2026-09-25)
- **The website is static and dependency-free**, published from
  `website/` through GitHub Pages; its walkthrough is generated from the
  tested VLAN gateway source. (2026-09-24)

## Process

- **Independent review after each step**, filed under `.agents/reviews/`,
  with the reviewed revision or patch, reproducible findings, checks and
  limitations; findings fixed on the working branch before integration.
  Reason: review must cover what is merged, and a report is evidence only
  when a later reader can identify its subject. (2026-09-25)
- **PRs are the default for substantive changes; final-revision CI gates
  merging.** Trivial non-behavioral maintenance may go directly to `main`.
  Authorized work includes autonomous commits, pushes and merges, without
  bypassing protections. Integrate sub-agent commits on the PR branch,
  keep review and local/remote evidence distinct, and verify the final
  head SHA before merging. Preserve coherent commits with a merge commit;
  squash WIP/fixups with their rationale and attribution retained; rebase
  only for an explicit linear-history preference. Reason: adopt the
  user's p4-spectec-lean workflow so defects are caught before main changes,
  while preserving independently useful history. (2026-09-25)
- **PR descriptions carry durable rationale and concise AI disclosure.**
  Explain the problem, outcome, tradeoffs, validation and relevant limits
  without conversation context. Re-read against the final diff. Name the
  authoring agent/model from active-session evidence in one sentence;
  agent review is not human review. Reason: apply the user's practices in
  p4-spectec-lean and Git/Google/GitHub contribution guidance without a
  boilerplate template. Sources and adoption boundaries are in
  `notes/engineering-practices.md`. (2026-09-25)
- **Generated-file checks compare inventory and bytes with both index
  and working tree from a clean temporary generation.** An in-place
  `buf generate` followed by `git diff` misses untracked new outputs and
  can leave stale outputs behind. One script serves local and schema CI
  gates; negative tests challenge the guard. (2026-09-25)
- **A tracked file may not exceed 5 MiB in index or working tree.**
  Stage new deliverables before the gate. Prefer reproducible generation,
  small losslessly compressed snapshots with raw checksums, or pinned
  external artifacts; never rewrite published history without explicit
  scope. Reason: adopt p4-spectec-lean's preventive artifact budget while
  every current file fits without migration (largest about 0.5 MiB).
  This is a project budget, not a hosting limit. (2026-09-25)
- **Uncertain choices record a confidence and a revisit trigger.**
  (2026-09-23)
- **Unfinished work is parked as a pushed branch, never as an uncommitted
  worktree**; a merged or byte-identical branch is deleted; obsolete
  worktrees are archived before removal. (2026-09-24)
- **Gates.** The full gate runs before a push, gated on the recorded exit
  status and never on a command that reads the log (a `tail` once pushed
  a red main). A builder hands back with lint, types, the tests covering
  its files and the Lean gate when it touched Lean, and the full gate
  only for a cross-cutting change; the integrator combines changes on the
  PR branch in batches and gates once per batch before push, with final
  remote CI before merge. `scripts/check.sh` deselects the oracle suites and runs the
  rest in parallel with fixture-heavy modules pinned to one worker, under
  a minute in all; the oracle workflows run the rest. At most two heavy
  jobs share the machine at once. (2026-09-24, 2026-09-25)
- **Documentation is split by subject.** `docs/` describes the artifact
  for people and never links into `.agents/`; `.agents/` is the resumable
  state; `AGENTS.md` is the single entry point. (2026-09-24)
- **`.agents/` is compacted at milestone boundaries; git is the archive.**
  The tree's commit is recorded as the archive commit in `status.md`; no
  git tags are created (user's instruction, 2026-09-24; the one earlier
  tag was deleted). Notes that describe the artifact are promoted into
  `docs/`. (2026-09-24)
- **Skills live in `.agents/skills/`**, with `.claude/skills` a committed
  symlink to it. (2026-09-24)
