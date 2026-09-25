# Decisions

The decisions in force, grouped by topic, each with its reason and the
date it was made. This is a register, not a diary: an entry that is
superseded is rewritten in place with the new date and reason, and an
entry whose subject no longer exists is removed. The full chronological
log up to the last compaction is in git at tag `agents-archive/2026-09-24`
(`docs/decisions.md` there). A decision the design document already
settles is not repeated here.

## Environment and tooling

- **Ordinary commands are the documented default; pinned tools are
  optional.** `uv sync --locked` installs the Python environment and
  `.python-version` selects Python 3.13. `flake.nix`/`flake.lock` provide
  the same tools pinned, entered with `nix develop` or direnv, and CI uses
  them; the documentation does not assume them. Lean comes from elan, not
  nixpkgs, because nixpkgs lags Lean releases. The OCaml toolchain for the
  P4-SpecTec oracle lives in `devShells.oracle`, not the default shell,
  because only the oracle needs it. Node is in the flake so the pyright
  wheel never downloads its own. Historical command transcripts are
  preserved as written. (2026-09-24, supersedes the 2026-09-22 flake-only
  guidance.)
- **No devcontainer.** The uv-only tier already serves people who avoid
  Nix; a devcontainer that did not run the flake would drift. Revisit for
  a Windows contributor without WSL2 or for Codespaces. (2026-09-22)
- **Python 3.13, pure Python.** No native code in the `p4blo` package.
  The constraint is free now and reopening it later is not. (2026-09-22)
- **p4c and BMv2 come from `github.com/qobilidop/p4lang-builds`.** The
  official p4c image is amd64 only and crashed under emulation on ARM;
  those builds publish native amd64/arm64 images of p4c 1.2.5.15 and BMv2
  1.15.4 with immutable tags. p4c is pinned by index digest. (2026-09-22)
- **p4c through Docker is an optional local check.** The printer's goldens
  are typechecked with `p4test` when Docker is available and skipped
  otherwise; building p4c is out of proportion. (2026-09-22)
- **Every external input is pinned, and the pins are listed** in the table
  in `docs/workflows.md`: images by digest, GitHub Actions by commit, the
  oracle's opam repository by commit, sources by SHA-256. Anyone must be
  able to reproduce the build. (2026-09-22)
- **Fresh Lean caches across package moves; build before testing.** A
  copied IR build cache once shadowed renamed modules in standalone
  queries. Rebuild from empty build directories after a move, never move a
  build directory while binary consumers run, and build Lean before running
  conformance tests in the same worktree, because a concurrent rebuild
  removes the executable a test needs. (2026-09-23)
- **Isolated CI for compile-only XDP capacity.** Local Docker disk pressure
  is not permission to delete unrelated images or change global VM
  settings. Remove only own artifacts and run the native gate on a clean
  runner. Docker availability or a skipped kernel test is never an oracle
  pass. (2026-09-23)

## Repository layout and ownership

- **Lean owns the abstract IR, validity and meaning; protobuf owns the
  encoding.** Conversion between them is an explicit obligation with its
  own proofs, not a guarantee the organization supplies. The direction and
  its boundaries are in `docs/design.md`; the accepted plan is archived
  in git as `docs/notes/ir-spec-boundary.md`. (2026-09-23)
- **Three Lake packages, specifications under `spec/` and implementations
  under `impl/`.** `spec/ir/` is the IR specification `P4bloIR` (package
  `p4blo-ir`) with the wire schema beside it and nothing architectural in
  it; `spec/arch/` is the reference architecture specification `P4bloArch`
  (package `p4blo-arch`), depending on the IR, with the switch, the extern
  families, the certificate example and the `p4blo-lean` endpoint;
  `impl/lean/` is the user library `P4blo` (package `p4blo`), depending on
  both. The Python package lives under `impl/python/`. Wire identities and
  the endpoint's protocol are preserved. (2026-09-24, supersedes the
  two-package layout of 2026-09-23 and the temporary `P4bloLean` name.)
- **The IR carries extern state as data and takes the model as a
  function.** `ExternState` is a kind name with optional width, optional
  natural cells and private configuration; `Externs` pairs the instances
  with an `ExternModel` whose `call` the architecture supplies at load.
  This keeps `Run` unparameterized, so no proof signature changes, and
  keeps state first-order, so proofs and tests inspect register cells
  directly. A closure-carrying instance was rejected because its
  state-threading conversion is not a total definition Lean can reason
  about; a type parameter through every execution definition and theorem
  was rejected as invasive for no gain in what is expressible. The
  representation commits the IR to what the differential observations
  already report (kind, width, values). Confidence: high in the boundary,
  medium in the representation; revisit if an extern family needs
  structured state that cells cannot carry. (2026-09-24)
- **Generated protobuf code is committed** at `impl/python/p4blo/v0/`, where the
  proto package path and the Python import path coincide. CI regenerates
  and fails on drift. (2026-09-22)
- **Shared verification assets live under `tests/`**: corpus programs,
  oracle drivers and build contexts, with `tests` an explicit package for
  adapter imports. Discovery asserts a nonempty corpus so a move cannot
  hide tests. (2026-09-23)
- **Public applications live under `examples/`, their verification under
  `tests/examples/`.** Published application sources have a different
  audience from test infrastructure and upstream fixtures. Shared example
  checks discover `examples/*/program.py` and require goldens, vectors and
  demos; both oracle catalogs include example vectors. (2026-09-24)
- **Existing public APIs may change for demonstrated usability gains.**
  Preserve the semantic contract and readable examples; keep authoring
  changes separate from semantics changes; migrate callers with diagnostic
  and golden tests. (2026-09-23)

## IR and wire syntax

- **Proto package `p4blo.v0`**, pre-1.0 by design; buf's version-suffix
  lint rule is excepted rather than renaming to `v1alpha1`. (2026-09-22)
- **One `Block` message with a kind tag.** Three messages would triple the
  shared machinery for locals, parameters and sub-block calls. (2026-09-22)
- **References by scoped name, not integer id.** The text format is the
  golden format and must read like the program. Scopes are P4's and the
  validator resolves every reference once. (2026-09-22)
- **Typed oneofs, not an ONNX-style generic node.** P4's core has about
  twenty fixed operators; a schema whose messages are the grammar is what
  the Lean decoder and readers need. (2026-09-22)
- **No type annotations on expressions.** Leaves are typed, operators
  determine their result, values carry widths at run time, the validator
  computes every type once. Annotations would double the goldens. (2026-09-22)
- **Dedicated nodes for packet and header operations.** extract, emit,
  lookahead, advance, verify, isValid, setValid, setInvalid, push and pop
  are IR statements and expressions, not method calls; "externs" means
  declared externs only. The printer reverses this. (2026-09-22)
- **`int<N>` is out of scope for v0.** No corpus program needs it and it
  doubles the arithmetic rules; additive when wanted. (2026-09-22)
- **Table `size` is an informative field** kept for a faithful printer
  roundtrip. (2026-09-22)
- **Field numbers 100 and above are reserved for annotations**, so
  semantics and metadata never mix. (2026-09-22)
- **Fields named after Python keywords are renamed**: `conditional`,
  `otherwise` (twice), `expr` and `lvalue`, so generated code never needs
  `getattr`. (2026-09-22)
- **Expressions and lvalues stay separate messages.** A dotted-path string
  sugar was rejected as a second syntax inside strings that cannot express
  indices; the eDSL is the authoring tool. (2026-09-22)
- **Elaborations, named in the coverage table.** A slice as an lvalue is a
  read-modify-write of the whole field; `switch` on `action_run` is a block
  local each action assigns plus an if-chain; P4 `type` is elaborated like
  `typedef`; functions are inlined; constructor parameters give one block
  per instantiation. Out by scope, each additive if wanted: `string`,
  non-header arrays, `packet_in.length()`, static extern methods, mutable
  initial entries and per-entry `const`, object initializers, abstract
  methods. Out by thesis: `range`, `optional` and `..` in entries, since
  core.p4 declares only exact, ternary and lpm. (2026-09-22)
- **Entry priority: larger wins, everywhere in the IR, and const entries
  take the language specification's numbering.** P4 1.2.5 §14.2.1.4 as
  P4-SpecTec mechanizes it (`$set_priorities_of_tableEntryListIR`): with
  the default `largest_priority_wins`, an annotated `const` entry keeps
  its `@priority` value and an unannotated one takes the previous
  entry's priority minus `priority_delta`, so the first listed entry
  ranks highest unless annotated otherwise. p4c's BMv2 backend numbers
  entries with a running counter that BMv2 then reads smaller-wins,
  which inverts the specification's order; p4c's STF vectors for
  `table-entries-priority-bmv2` encode that inversion, and pinned
  SpecTec fails them on the same packets. Reason: the reference for what
  P4 means is the specification's own mechanization, not the reference
  compiler's backend. The `priority` corpus program is re-derived under
  the specification's rule and BMv2's answer becomes a strict classified
  disagreement; the printer emits descending priority so that p4c,
  numbering by position, sees the same order. (2026-09-24, supersedes
  the 2026-09-22 mapping `IR = N + 1 - p4c`.)
- **Decimal strings are always emitted, including zero, and a missing
  decimal string is rejected, never read as zero.** A protobuf string
  defaults to empty, not `"0"`; Lean's decoder had hidden the defect by
  supplying zero for an absent value. Explicit `"0"` and leading zeros are
  preserved. (2026-09-23)
- **The tested canonical wire domain is stated; arbitrary ProtoJSON parity
  is not promised.** The Python parser rejects unknown fields while Lean
  ignores them, and enum numbers and camelCase aliases differ. These forms
  are documented outside interchange parity in the profile. (2026-09-23)
- **The differential harness rejects ambiguous JSON without validating away
  bad IR inputs.** Duplicate keys, nonstandard numeric constants and wrong
  envelope shapes are malformed and rejected before information is lost;
  semantically invalid IR remains representable for experiments. (2026-09-23)

## Python eDSL

- **The typed eDSL is type-safe by construction where pyright allows and
  run-time checked where it does not.** The design is the "Python eDSL"
  section of `docs/design.md`; as implemented it deviates from the
  original note (archived as `docs/notes/edsl-v2-design.md`) in
  four places, each forced by the type checker: the width aliases `bitN`
  are places (`Var[L[N]]`) and a typed literal `bitN(v)` types as a place
  too, so a literal used as a target is caught at run time only; `Bool`,
  `Enum` and `Error` targets have no static place split; an extern's `in`
  parameters accept any value (`Val`) with the width checked at run time;
  sub-block call arguments are run-time checked. `assign` is overloaded
  over target kinds, so pyright reports a failed assignment as
  `reportCallIssue`, and the must-fail fixtures say so. Everything else in
  the note's table holds; `tests/test_pyright.py` guards the static rules.
  (2026-09-22)

## Semantics rulings

Rulings on behavior P4 leaves open are written in `docs/ir-semantics.md`,
or in `docs/arch-supports.md` when an architecture or extern family decides them;
these entries record why.

- **`docs/ir-semantics.md` is a deviation ledger, and it is the contract
  for "equivalent to P4-SpecTec up to elaboration and known deviation".**
  Every closed behavior has a fixed template: the behavior, p4blo's
  choice, the reason, the P4 specification section, the SpecTec rule or
  function at the pin, the Lean definition, the Python function and the
  test that exercises it, classified as *same*, *refines undefined*,
  *deviates* or *not representable*. An unlisted difference from SpecTec
  is a bug on one side, never a new ruling made in a fix. Reason: "up to
  known deviation" must be a checkable list; prose cannot be tested.
  (2026-09-24)
- **The Lean definitions are "executable and proved, checked against
  SpecTec", never "normative".** p4blo is an independent P4-inspired
  project; the reference for what P4 means is SpecTec's elaborated IL, and
  p4blo's IR is a serialized, architecture-free, closed refinement of it.
  Reason: the earlier wording claimed an authority the evidence does not
  give and that the project does not seek. (2026-09-24)
- **A local declared without an initializer inside a parser state, an
  action or an inlined function is re-zeroed at every entry by the
  elaboration.** The IR has only block locals, and a hoisted local keeps
  its value between entries; P4-SpecTec's `ParserState_eval` enters a
  fresh scope per state (`$enter_e`) so such a declaration re-defaults
  on every entry, and an action or function call does the same. The
  bridge therefore emits a zeroing assignment where the declaration
  stood, and the eDSL must do the same for a state-local it hoists.
  Reason: the IL bridge review showed both interpreters and SpecTec
  disagreeing on programs the validator accepts (`statelocal.p4`,
  `actlocal.p4`). This closes the "State-local variables" question on
  the semantics page and the coverage page. (2026-09-24)
- **The parser loop bound is the no-consumption revisit rule**, not fuel,
  because fuel makes meaning depend on an unspecified number and the rule
  matches BMv2. (2026-09-22)
- **Metadata contract fields are fixed** as the table in the design:
  `ingress_port` and `parser_error` provided; `egress_port`, `drop`,
  `flood` consumed; fate as booleans so the forwarder runs unchanged under
  the switch. Byte-aligned parsing is required; the control runs after a
  parser rejection. (2026-09-22)
- **Architecture rules the design left open.** A parse ending off a byte
  boundary drops the packet. An undeclared contract field reads as zero and
  swallows writes. `parser_error` is written after the parser's own `inout`
  writes and before the control. The filter forwards the original bytes,
  so its tests rewrite expectations to the input bytes. (2026-09-22)
- **Port rules.** Ports are `0` to `ports - 1`; an out-of-range
  `egress_port` drops with a diagnostic; an out-of-range `ingress_port` is
  the caller's error before anything runs; the filter has no port count.
  BMv2's drop port 511 is just an out-of-range port here. (2026-09-22)
- **An out-of-range register read yields zero, diverging from BMv2
  knowingly.** BMv2 leaves the destination untouched. P4 leaves this
  implementation-defined; the divergence is a strict xfail on the one
  vector, not resolved. Revisit only if a corpus program depends on it.
  (2026-09-22)
- **CRC16/CRC32 are stateless extern families with exact byte-aligned
  widths**, full results and no padding or range reduction; the contract is
  `docs/assurance.md`. Independent known answers found pinned SpecTec's
  odd-byte padding defect; BMv2 confirms the standard behavior. (2026-09-23)
- **Statement execution uses an explicit continuation machine.** A total
  step function performs one semantic operation and the interpreter drives
  it through a proof-visible fixpoint, so finite traces imply the driver's
  result. Global termination for validated programs is a separate open
  theorem. (2026-09-23)

## Vectors, oracles and corpus

- **P4-SpecTec is the primary oracle for the IR's meaning; BMv2 is the
  tie-breaker where SpecTec is known wrong** (odd-byte CRC32 padding, LPM
  and ternary mask construction) and for what the simulator cannot judge
  (real longest prefix, const-entry and runtime ternary priorities).
  Reason: SpecTec is the mechanization of P4 itself, executes the same
  elaborated IL the coverage table walks, reports rule coverage, and can
  run single relations; BMv2 is one implementation. Comparison moves from
  printed P4 through the v1model shim to the block level once a
  single-block SpecTec runner exists, and to the IL level once an IL
  bridge exists. (2026-09-24, supersedes "first oracle and second" below
  as ranking; the vector conventions stand.)
- **Block-level comparison runs on a patched simulator.** A minimal
  `p4blo` architecture for SpecTec's simulator, kept as a patch under
  `tests/oracle/patches/` and applied by `tests/oracle/build.sh` at the
  pin, runs one parser, control or deparser on the given headers,
  metadata, entries and extern state and returns the block's outputs;
  the stamp and the CI cache key include the patch digest. Extern
  families run on v1model's own OCaml implementations, entries go
  through the same STF translation, and everything an architecture
  decides stays uncompared. Reason: through the printed pipeline the
  simulator could never show its register cells, so the CRC padding
  defect was invisible on the firewall's stateful vectors; block by
  block it is a strict expected failure like the others. Entries that
  would need v1model's STF name rewrites (a table name declared by two
  blocks, a `$valid$` key) are refused by the block driver rather than
  rewritten, because rewriting needs a map from block names to instance
  paths that no corpus program yet needs. Known differences are accepted
  only through checked models of the exact defect, never by tag: the
  CRC model asserts the binding's own result first, and the stack model
  checks P4's answer before applying the deviation. Offer the patch
  upstream when it stabilizes. (2026-09-24)
- **The conformance corpus is Lean's answers on fixed inputs, tracked
  as data.** `tests/conformance/` holds one fixture per input (program,
  request sequence from fresh state, and each reply with state and
  coverage), canonical so that a changed answer is a one-line diff;
  Python is checked against it without a Lean process and Lean by
  regeneration. `refresh` re-answers the tracked requests and never runs
  a generator; `export` adds inputs. A fixture records the digest of the
  semantics sources that answered it (the modules `spec/arch/Main.lean`
  imports, minus laws, audits, probes and tests) and of the binary, and
  a binary older than those sources is refused, so stale answers cannot
  be written locally; the required gate builds Lean first. Format
  version 2 lists only nonzero extern cells. Two contract fixtures
  exercise rejected installs, floods, drops and out-of-range ports so
  every reply shape the protocol allows is recorded. A changed answer is
  refreshed only after the semantics page states the changed behavior.
  (2026-09-24)
- **SpecTec is rendered into Lean elsewhere; this repository builds the
  IR, its meaning, the elaboration and the validation suite.** A separate
  project compiles P4-SpecTec's elaborated spec into Lean and verifies
  that compiler. p4blo therefore builds no Lean rendering or interpreter
  of SpecTec's rules, no trace-localized N+1 testing, no simulator patch
  beyond the two that exist, and no bridge census beyond the corpus. It
  keeps and freezes the oracle machinery as the rendering's test bed
  (conformance fixtures, block-runner requests, rule coverage), owns the
  block contract `p4blo.watsup` that the theorem will relate to
  `P4bloIR.Exec`, and keeps the bridge small as the elaboration side of
  that theorem. Reason: building the rendering twice wastes the effort
  and splits the trust; the plan's Phase 4 becomes a joint milestone
  whose first acceptance is that the executable rendering answers every
  fixture and block request as the OCaml simulator does. (2026-09-24)
- **The IL bridge is the frontend from P4 source.** P4 text enters
  p4blo through P4-SpecTec's own typing and instantiation: a patch adds
  an `il-export` command that prints the instantiated IL structurally as
  JSON, and `p4blo.frontend` translates it construct by construct as the
  coverage page prescribes, refusing excluded rows by name. Choices the
  translation makes, each recorded on the coverage page: v1model's
  verify, ingress, egress and compute controls merge into one control
  whose egress part runs only when the packet is not dropped;
  `standard_metadata` fields become the contract fields and a user field
  that collides with a contract name is renamed; `mark_to_drop` becomes
  `drop = true` and `egress_port = 511`, so a program that reads the
  drop port afterwards keeps its meaning; the metadata parameter is
  named `meta`; constant folding is kept to what the IR cannot hold
  (named constants, `int` arithmetic, division, enum members, stack
  sizes) so a printed program reads back as printed; per-table action
  copies are named as p4c names them. Corpus goldens are compared with
  the bridge's output and each documented difference is written as an
  explicit change in the test, so any new difference fails. Not a
  verified frontend. (2026-09-24)
- **The SpecTec coverage scope is the rules and functions of 8-dynamic
  and the functions of 3-operations, including table-defined and builtin
  ones**, measured over the corpus, the examples and a fixed greedy set of
  generated seeds. Functions outside those sections that the dynamic
  sections call are reported as `called_in_scope` but not enforced,
  because enforcing them costs eight exclusions for header unions,
  compound assignment and overload-resolution helpers. Revisit when a
  pin bump changes that cost. (2026-09-24)
- **Its rule inventory is a tracked fixture.** `tests/oracle/spectec-rules.json`
  lists every architecture-free declaration at the pin, generated by
  `scripts/spectec-rules.py`; the ledger cites those names and a test
  checks them without OCaml. A pin bump regenerates the fixture and
  re-classifies every entry whose cited rule changed. (2026-09-24)
- **STF is the vector format; P4-SpecTec's `sim` is the first oracle and
  BMv2 the second.** STF is text, readable and understood by both. Dialect
  conventions, recorded in `impl/python/p4blo/stf.py`: a `packet` without
  `expect` asserts no output; `expect` matches a prefix unless it ends in
  `$`; key names may index stacks; non-canonical entries are rejected with
  a line number; a hex or binary literal's written form fixes its width;
  a table declared in two blocks is qualified; a priority on a
  non-ternary table is an error; an lpm key without `/n` is a full-width
  prefix. p4c vectors that write
  `expect` before `packet` are reordered in the corpus copy, and
  per-table action copies name p4c's elaborated actions. (2026-09-22)
- **Corpus programs come from p4c's test suite**, chosen by a survey of
  its STF-bearing v1model programs (archived in git as
  `docs/corpus-candidates.md`), plus programs of our own where p4c has no
  vector. (2026-09-22)
- **P4-SpecTec is pinned by commit and translated.** Its simulator has no
  longest-prefix rule, so `tests/oracle/run.py` turns each lpm `add` into a
  full-width wildcard with `priority = prefix length`; `no_packet` becomes a
  comment. It confirms outputs but does not independently check longest
  prefix; BMv2 does. Known gap: printed const lpm entries carry no
  priorities, so a program whose const lpm entries overlap fails on this
  oracle until the printer adds them. (2026-09-22)
- **BMv2 decides what SpecTec cannot**: real lpm, const-entry and runtime
  ternary priorities. Its runner prints `stack.last` rather than the index
  form p4c compiles differently. It cannot see `flood`, which no corpus
  program declares. (2026-09-22)
- **Printed ternary entries are not const**, because p4c 1.2.5 refuses
  priorities on `const entries`; nothing in the vectors depends on the
  difference. (2026-09-22)
- **The original tutorial firewall is an independent oracle input.** The
  unchanged pinned solution runs directly on both oracles; its state is
  observed through a scoped BMv2 barrier (a distinct sentinel packet, then
  complete register reads of all 8192 cells). Valid for the pinned
  single-ingress FIFO implementation; revisit before recirculation or
  asynchronous externs. (2026-09-23)
- **An original-program oracle is evidence to challenge, not a definition
  to copy.** Exact strict discrepancy tests with passing controls record
  pinned SpecTec's CRC and table-mask defects; inputs are never adapted to
  manufacture agreement, and strict XPASS prevents stale exceptions.
  (2026-09-23)
- **Whitelist the exact BMv2 discrepancy, not every failure on its node.**
  The expected-failure marker requires the exact vector, semantic-failure
  status and the two known packet mismatches, so an oracle error cannot
  hide as the expected discrepancy. (2026-09-23)
- **Conformance suites are discovered, not enumerated.** Required Lean CI
  selects `test_lean_agrees` tests across the tree; a new external-oracle
  test must be selected by the job that builds that oracle. (2026-09-23)
- **Every Docker check container is owned and verified.** Unique names,
  bounded cleanup with absence verification, cleanup of only demonstrably
  owned stalled containers, and a short warm printer probe that keeps the
  cold CI allowance. Never prune globally. (2026-09-23)
- **XDP is a compile-only preflight of the Ethernet-allow xdp-filter
  build**: pinned sources, offline ELF/BTF/map checks, an FD-only
  non-attaching design, no kernel load and no behavioral-equivalence claim.
  A failed upstream snapshot download is not evidence either way; pins are
  retained and the run rechecked at the next checkpoint. (2026-09-23)

## Verification method

- **Verification beyond the prototype follows Cedar's method**: an
  executable formal model, property proofs, typed generators and
  component-level differential testing. Universal equivalence of Python and
  Lean is not claimed; the models stay independently implemented, sharing
  wire syntax only. (2026-09-23)
- **The adequacy criterion for generated testing is coverage of the
  ledger's behaviors and of SpecTec's rules, not test counts.** The Lean
  step machine reports the rules each case exercises; generators are
  biased toward unhit rules and unhit rule-in-construct pairs, following
  ESMeta's feature-sensitive coverage; SpecTec's own coverage command
  measures its rules over p4blo's inputs. An in-scope rule that no
  retained case hits fails a test unless it is excluded with a reason.
  (2026-09-24)
- **No new application or typed-source-language theorems until the
  SpecTec IL bridge exists.** The theorems so far establish p4blo's
  internal consistency; the bridge is what would make a claim about P4.
  Proof effort goes to whole-program validity, progress, termination under
  the stated discipline, codec composition and per-entry deviation
  theorems. The parked drafts stay parked. (2026-09-24)
- **Replay the whole experiment.** A differential failure is saved as a
  versioned JSON bundle with the program and the complete request sequence
  from fresh extern state; seeds and STF excerpts are supplementary.
  (2026-09-23)
- **Observe logical extern state after every request**, including on
  errors, as hexadecimal strings so arbitrary widths survive. Missing state
  fails instead of silently comparing packets alone. (2026-09-23)
- **Adversarial verification is recurring work.** Mutate both
  implementations in isolated worktrees, record killed and surviving
  mutants, improve tests for survivors. A build failure is not a semantic
  kill; a reused input is counted once. (2026-09-23)
- **Mutation survivors drive generated-program coverage**: systematic
  scalar boundaries, recursively typed generated expressions, generated
  stateful programs with independent register and counter bounds, and
  generated host policy changes. Shrinking preserves types; invalid
  generated programs fail rather than being filtered. Failed programs are
  retained under `.artifacts/drt/`. Host changes within one sequence are
  Python/Lean-only evidence: the original BMv2 protocol cannot replace
  rules mid-sequence, so revisit that limitation before claiming
  original-oracle coverage of host changes. (2026-09-23)
- **Proof trust is a build gate.** Warnings are errors; default
  `ProofAudit` targets check advertised theorems' transitive axioms, which
  catches imported axioms and native shortcuts that grepping for `sorry`
  would miss. It checks dependencies, not whether a theorem states the
  intended property; that is review's job. (2026-09-23)
- **Execution certificates are bounded reexecution of the actual machine**,
  bound at the decoded AST with the complete program and initial state,
  produced by executing production Python unchanged. Exhaustion is a checker
  verdict, not a P4 fault. Process-group cleanup is attempted once and
  failure is fail-closed. Not a faster verifier or a proof term. (2026-09-23)
- **Observers are reviewed as adversarially as evaluators.** Compare and
  save evidence before judging against known answers; freeze full state and
  compare JSON with type sensitivity, since Python equates false with zero;
  observe state after evaluation, not before; isolate the operation under
  test from the observer's own reads; check mutable copy isolation by
  branch, not equal snapshots; require complete native state and exact
  Python types at proof and test boundaries. Demonstrated survivors stay as
  permanent regressions. (2026-09-23)
- **Independent anchors accompany every roundtrip proof and observer.**
  Paired encoder/decoder or observer faults can preserve every law and every
  agreement; independently authored known answers and constructor
  observations that do not reuse the production name tables reject them.
  Representability deliberately includes semantically invalid syntax; only
  protobuf uint32 fields are bounded. (2026-09-23)
- **Decoders are total through well-founded recursion over finite JSON**,
  with erasure laws preserving the previous behavior and diagnostics; there
  is no proof-only duplicate decoder. Old raw transcripts are retained
  before a refactor and pinned to their source commit. (2026-09-23)
- **Fixed-application protocol evidence is kept separate from generic IR
  replay**, and exact state and numeric contracts are kept beside packet
  equivalence: a consistent wrong hash or a server reset survives
  packet-only gates. (2026-09-23)
- **Exhaust a named malformed profile before broad random traffic**, such
  as every byte truncation of one frame with persistence across
  valid-malformed-valid sequences. (2026-09-23)
- **Adversarial acceptance is finite and reconstructible.**
  `scripts/check-assurance.py` replays a reviewed catalogue of Python,
  Lean, codec and observer faults from tracked fixtures; it is not a
  mutation-score guarantee or a requirement to rerun history. (2026-09-23)

## Lean authoring and proof boundaries

The exact theorem statements, premises and exclusions are in
`impl/lean/ASSURANCE.md` and the audit files; these entries record the shape.

- **The first sound validity boundary is the closed scalar fragment**, and
  verified authoring starts with an independently meaningful scalar
  language: Fin/Bool denotations that never call the interpreter, exact
  computation and whole-Run preservation, scalar equality made
  proof-visible. (2026-09-23)
- **Exact frame agreement is distinct from declaration validity.**
  Constructive frame, declaration and permission witnesses rule out vacuous
  premises; no whole-program validity follows from a body theorem.
  (2026-09-23)
- **Aggregate shape, nominal coherence and write permission are separate
  obligations**, and header-validity reads are kept apart from writable
  places. (2026-09-23)
- **One shared operator AST and one command AST**, with the scalar API
  preserved through adapters and command lists as a transparent
  composition helper, not another AST. Custom notation waits for a real
  application that needs it; names are resolved before any elaborator.
  (2026-09-23)
- **Initialization is discharged in bounded layers**: source zero under
  nominal agreement and explicit fuel, frame initialization stated over the
  actual map entries, modeled values discharged and unmodeled extras given
  explicit zeroability. (2026-09-23)
- **Call laws are proved operationally against the actual machine**: entry
  before body, prefixes of the real flat body with an arbitrary pending
  suffix, normal return against the current callee-after Run, root laws on
  actual map membership, action-layer updates target-specific. (2026-09-23)
- **Applications are separately named policies with independent anchors.**
  A proved state mapping is still anchored by a hand-built asymmetric known
  answer, because a paired relabeling preserves the proofs. The forwarder
  is ported preserving its original policy; the tutorial firewall reuses
  ordinary IR assembly and proves initialization and exact Bloom insertion.
  Selection hit is not a forwarding default. Further readback and ingress
  proofs are parked. (2026-09-23)
- **Whole-program validity is defined over the index and decided by a
  checker proved sound; completeness is not claimed.** `Valid p idx` in
  `spec/ir/P4bloIR/Validity/` states the typing and side conditions the
  protobuf contract lists, `Validity.check` decides it in the Python
  validator's order with its codes, and `check_sound` is proved; a
  program the checker rejects may still be valid, which the Python
  correspondence test bounds empirically. Progress (`Progress.lean`)
  takes two premises the IR cannot discharge: `ExternContract`, that the
  architecture's bindings answer typed calls with typed values (binding
  mismatches are load errors), and that the run fits the block kind;
  `InstalledOk` is discharged from the real `Installed.build`. Wire-shape
  problems Python reports as codes are `DECODE` on the Lean side, since
  the decoder rejects them before any rule runs. Termination (C2) and
  completeness stay open. (2026-09-24)
- **Deviation theorems cover the run-time closed behaviors only.** The
  ledger entries that belong to installation, binding or the
  architecture (host entries are canonical, entries name their action,
  binding, and the implementation-closed choices of extern families) have
  no theorem in `P4bloIR.DeviationLaws`: their meaning lives in
  `Installed.build` and in the architecture package, outside the IR's
  evaluator, and the plan's arch-free scope stops there. Reason: a
  theorem about installation would be about the architecture's
  contract, not the IR's meaning. Revisit when a single-block SpecTec
  runner makes installation observable at the IR level. (2026-09-24)
- **Codec laws are composed in baseline-first slices** and object helpers
  are extracted only at demonstrated reuse; historical baseline hashes stay
  pinned to their commits. (2026-09-23)

## Scope and milestones

- **Full architecture-independent P4 is a north star, not a deliverable.**
  Progress goes through progressively demanding examples, Python and Lean
  only, implemented autonomously in small reviewed commits. (2026-09-23)
- **Assurance milestone 1 is finite and complete** (2026-09-23, revision
  `3148a52`): frozen IR profile, whole-program interchange, evidence
  matrix, finite adversarial acceptance and a tested two-language
  quickstart. It is not universal Python correctness, and no theorem is
  required merely because it is the next composable one. (2026-09-23)
- **The playground is out of the plan** (2026-09-22) and **the p4c backend
  is deferred behind verification**; it is the community version's first
  job and the experiment that would really test claim 1. (2026-09-22)
- **The website is static and dependency-free**, published from `website/`
  only through GitHub Pages; its walkthrough is generated from the tested
  VLAN gateway source and checked for drift. (2026-09-23, 2026-09-24)
- **The application collection is the router, the stateful firewall and the
  flow-affine load balancer**, chosen for familiarity and distinct lessons,
  each with an explicit bounded profile: guarded fixed-header IPv4 for the
  router; exact SYN-created pinholes in sixteen slots, no aging, for the
  firewall; UDP service and CRC16 bucket dispatch with shared VIP and no
  NAT for the load balancer. Complete 2026-09-24 at `c94336d`. Applications
  are iterated as users of the project: eDSL or infrastructure changes are
  in scope when an example exposes a real problem. (2026-09-24)
- **The active scope is the architecture-free IR semantics plan**
  (`notes/ir-semantics-plan.md`, adopted 2026-09-24). Architectures, the
  application collection, XDP and claim 3 are frozen at their current
  evidence: kept green, not extended. Reason: the project's value is the
  IR and its meaning; everything architectural exists to test that and
  already does. (2026-09-24)

## Process

- **Independent review after each step.** A read-only reviewer looks for
  confirmed defects with reproducers; findings are fixed on `main`.
  (2026-09-22)
- **Uncertain choices record a confidence and a revisit trigger** instead
  of waiting for feedback. (2026-09-23)
- **Obsolete worktrees are archived before removal**, with hashes checked
  independently; branches and reflog-only commits are preserved.
  (2026-09-24)
- **Unfinished work is parked as a pushed branch, never as an uncommitted
  worktree**, with a work-in-progress commit that says what it holds and
  lacks; a branch is retained only after its content is compared with
  `main`, and a merged or byte-identical one is deleted. Reason: two
  proof drafts and a set of reviews existed for a day only as untracked
  files on one machine, and two "unique" branches turned out to hold
  nothing `main` lacked. (2026-09-24)
- **A push is gated on the recorded exit status, never on a command
  that reads the log.** Reason: on 2026-09-24 a push was chained behind
  `tail` of a gate log whose last line was `exit=1`; `tail` succeeds, so
  main was red on origin for one commit. Gate a push with
  `grep -qx exit=0 <log> && git push`, or read the status in a separate
  step and decide. (2026-09-24)
- **The full gate runs before a step is pushed; structural tests are a
  smoke check.** Reason: during the specification split the layout, link
  and boundary tests all passed while every codec test was failing on an
  endpoint path, which only `scripts/check.sh` showed. (2026-09-24)
- **Documentation is split by subject.** `docs/` describes the artifact
  and is written for people, to be published on its own; `.agents/`
  describes the work and is the resumable state. `docs/` never links into
  `.agents/`, which `tests/test_docs_links.py` enforces, so the split
  survives publication. `AGENTS.md` is the single entry point and names
  every agent file. (2026-09-24, supersedes the 2026-09-22 placement of
  status, decisions and notes under `docs/`.)
- **`.agents/` is compacted at milestone boundaries; git is the archive.**
  Status holds current state only, decisions are a topical register of
  what is in force, and finished notes and reviews are deleted after the
  tree is tagged `agents-archive/<date>`. Compaction changes no claim and
  is reviewed against the tag; the procedure is the `compact-agent-state`
  skill. Notes that turn out to describe the artifact are promoted into
  `docs/` instead. Reason: the resume read had grown to a diary, stale
  plans sat beside live ones, and git already kept every byte.
  (2026-09-24)
- **Skills live in `.agents/skills/`**, the location the Agent Skills
  convention and Codex, Cursor, Gemini CLI and Copilot read. Claude Code
  reads only `.claude/skills/`, so that path is a committed symlink to
  `../.agents/skills`; each skill exists once. (2026-09-24)
