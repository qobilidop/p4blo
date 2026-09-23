# Decisions

Dated choices with their reasons, newest last. A decision that the
design doc already settles is not repeated here; this file is for
everything decided while building. Overrule an entry by adding a new
one that says so.

## 2026-09-22

- **Nix flake as the development environment; uv for Python packages;
  elan for Lean.** One tool set for contributors and CI. Python
  packages are not packaged through Nix because uv does it with less
  friction and gives non-Nix contributors a working path. Lean comes
  from elan, not nixpkgs, because nixpkgs lags Lean releases.
- **No devcontainer for now.** The uv-only tier already serves people
  who avoid Nix. A devcontainer that did not run the flake would drift;
  one that did would be Nix in a box. Revisit for a Windows contributor
  without WSL2 or for Codespaces.
- **Python 3.13, pure Python.** Kept even with the playground deferred,
  because the constraint is free now and reopening it later is not.
- **Proto package `p4blo.v0`.** Pre-1.0 by design. buf's
  `PACKAGE_VERSION_SUFFIX` lint rule does not accept `v0`, so it is
  excepted in `buf.yaml` rather than renaming to `v1alpha1`, which says
  the same thing in a dialect nobody outside buf uses.
- **Generated protobuf code committed at `python/p4blo/v0/`.** The
  proto package path and the Python import path coincide, so the
  generated module's own imports resolve without a rewrite. CI
  regenerates and fails on drift.
- **STF as the vector format; P4-SpecTec's `sim` as the first oracle;
  BMv2 optional and second.** STF is text, readable, and already
  understood by both oracles, so pcap and its native library go away.
  P4-SpecTec runs natively on macOS, needs no Docker, and is the spec's
  own mechanization.
- **P4-SpecTec built in a separate CI job and a local script, not in
  the dev shell.** Its OCaml toolchain is heavy and only the oracle
  needs it.
- **One `Block` message with a kind tag.** Three messages would triple
  the shared machinery for locals, parameters and sub-block calls.
- **Parser loop bound is the no-consumption revisit rule.** Fuel makes
  meaning depend on an unspecified number; the revisit rule is one
  sentence and matches BMv2.
- **Two testing directories only: `corpus/` and `tests/`.** Vectors sit
  beside the program they test; oracle drivers and the differential
  loop are tests and live with the tests.
- **References by scoped name, not integer id.** The first draft used
  global integer ids. Switched the same day, on Bili's pointer to ONNX
  and on 4ward's stated principle, because the text format is the
  golden format and must read like the program; the hand-written
  forwarder is the first beneficiary. Scopes are P4's and the
  validator resolves every reference once. Lean pays with string-keyed
  maps, which costs nothing the project claims.
- **Typed oneofs, not an ONNX-style generic node.** ONNX's single
  `NodeProto` with a string `op_type` suits an operator set of
  hundreds that evolves separately from the file format. P4's core has
  about twenty fixed operators, and a schema whose messages are the
  grammar is what the Lean decoder and the readers need.
- **No type annotations on expressions.** 4ward, p4c and SpecTec
  annotate every node. p4blo does not: leaves are typed, operators
  determine their result, values carry widths at run time, and the
  validator computes every type once. Annotations would double the
  goldens and add a consistency check for no semantic gain.
- **Dedicated nodes for packet and header operations.** extract, emit,
  lookahead, advance, verify, isValid, setValid, setInvalid, push and
  pop are statements and expressions of the IR, not method calls on
  `packet_in`, `packet_out` and headers as in SpecTec, p4c and 4ward.
  The calling convention has no packet value, and the Lean side is
  simpler without method dispatch. "Externs" means declared externs
  only. The printer reverses this.
- **`int<N>` out by scope for v0.** Present in every prior IR and in
  core P4, but no corpus program needs it and it doubles the arithmetic
  rules. Additive when wanted.
- **Table `size` kept as an informative field.** It has no meaning; the
  printer needs it for a faithful roundtrip.
- **Field numbers 100 and above reserved for annotations**, as 4ward
  reserves 100 for source info, so semantics and metadata never mix.
- **p4c through Docker as an optional local check.** The printer's
  goldens are typechecked with `p4test` from the `p4lang/p4c` image when
  Docker is available and skipped otherwise. p4c is not in nixpkgs and
  building it is out of proportion; the image is pinned by tag for now
  and by digest once the oracle job exists.
- **`Stmt.if`, `If.else`, `Mux.else`, `Arg.in` renamed** to
  `conditional`, `otherwise`, `otherwise`, `expr` (with `Arg.out` to
  `lvalue`). The originals are Python keywords, and generated code would
  have forced `getattr` on every consumer. Found by the corpus agent
  while hand-writing the forwarder.
- **Expressions and lvalues stay separate messages.** Hand-writing
  read-modify-write paths twice is the main bulk of the forwarder text.
  A dotted-path string sugar was considered and rejected: it is a
  second syntax inside strings and cannot express indices. The eDSL is
  the authoring tool; the hand-written file is a step-1 artifact.
- **STF dialect conventions**, recorded in `python/p4blo/stf.py`: a
  `packet` with no `expect` asserts that nothing came out; a priority
  on a non-ternary table is an error; an lpm key without `/n` is a
  full-width prefix; a hex or binary literal's written form fixes its
  width for wildcards; a table name declared in two blocks must be
  qualified with the block name.
- **Metadata contract fields fixed** as the table in the design doc:
  `ingress_port`, `parser_error` provided; `egress_port`, `drop`,
  `flood` consumed; fate as booleans, not an enum, so the forwarder
  runs unchanged under the switch. Byte-aligned parsing required by the
  architectures; the control runs after a parser rejection.
- **Corpus programs picked from p4c's test suite** after the survey in
  `docs/notes/corpus-candidates.md`: ACL is `ternary2-bmv2` (the only
  v1model STF with runtime ternary adds and overlapping priorities),
  header stacks is `header-stack-ops-bmv2` (fifteen BMv2-produced
  vectors over push, pop, holes and `next`), stateful is
  `issue1097-2-bmv2` (a register read and written from two blocks) plus
  vectors of our own for cross-packet state. Micro-programs with
  oracle-grade vectors (`parser_error-bmv2`, `issue1824-bmv2`,
  `table-entries-priority-bmv2`, `issue655-bmv2` for csum16, the lpm
  const-entries files) join as companions. No v1model MPLS or VLAN
  program has an STF, and the tutorial forwarder has none either.
- **Entry priority: larger wins, everywhere in the IR.** p4c's STF
  `add` priority has larger winning (its runner inverts for BMv2), while
  `const entries` have smaller `@priority` winning and list order
  otherwise. The frontend elaborates const entries into IR priorities
  where larger wins; the printer prints const entries in descending
  priority without annotations, so p4c sees the same order.
- **`expect` lines match a prefix unless they end in `$`**, as in p4c's
  runner, because its vectors name only the header bytes. The runner
  stays strict about unclaimed outputs.
- **Slice as an lvalue is elaborated** to a read-modify-write of the
  whole field rather than added to `LValue`; one elaboration named in
  the coverage table, no new node for Lean.
- **Per-table action copies keep the corpus STF adjusted.** p4c
  elaborates `setbyte(out reg, val)` bound per table into `setbyte`,
  `setbyte_1`... and its runner resolves names per table; p4blo's
  corpus copy of the STF names the elaborated actions directly and
  sets `Key.name` to p4c's key names so the vectors read unchanged.
- **Architecture rules the design left open.** A parse that ends off a
  byte boundary drops the packet whether or not it accepted, since the
  payload is undefined either way. A contract field the program does
  not declare reads as its zero value and swallows writes, so a program
  without `egress_port` sends to port 0 and one without `flood` runs
  unchanged under the switch. `parser_error` is written after the
  parser's own `inout` writes and before the control, as v1model does.
  The filter forwards the original bytes, so a vector that expects a
  rewritten packet fails under it by construction; the filter tests
  rewrite expectations to the input bytes.
- **Printed ternary entries are not const.** p4c 1.2.5 refuses
  priorities on `const entries` and rejects `@priority`, so the printer
  emits a ternary table's const entries as ordinary `entries` with
  `largest_priority_wins = true`, sorted by descending priority. The
  oracle therefore sees host-mutable entries where the IR has const
  ones; nothing in the vectors depends on the difference.
- **Independent review after each step.** Step 1's review is kept at
  `docs/notes/reviews/step1.md`; its confirmed findings are fixed on
  main and its rulings are in `docs/semantics.md`.
- **P4-SpecTec oracle pinned and translated.** Commit `2730cfd9`
  (2026-09-22) built by `oracle/build.sh` with opam outside the flake.
  Its simulator has no longest-prefix rule: lpm entries match as
  ternary and ties need priorities, so `oracle/run.py` translates each
  lpm `add` into a wildcard at the key's full width with
  `priority = prefix length`. The oracle therefore confirms outputs but
  does not independently check longest-prefix; BMv2 would. `no_packet`
  is unsupported there and becomes a comment; the end-of-file leftover
  check carries the assertion. Known gap: printed const lpm entries
  carry no priorities, so a program whose const lpm entries overlap
  will fail on this oracle until the printer adds them.
- **Const entry priorities follow p4c's counter, not list order.** p4c
  numbers const entries with a running counter that continues past
  annotated ones, smaller winning on BMv2; the priority corpus maps
  that to IR priorities as `IR = N + 1 - p4c`. This corrects the
  earlier "list order otherwise" wording.
- **p4c vectors that write `expect` before `packet`** are reordered in
  the corpus copy, bytes untouched, since p4blo's replay pairs a packet
  with the expects that follow it. A dialect extension letting an
  `expect` just before a `packet` belong to it is possible but not
  done.
- **STF key names may index stacks** (`extra[0].h`), as p4c's do; the
  runner resolves the element's header type.
- **The STF runner rejects non-canonical entries with a line number**
  rather than masking as p4c's runner does; entries are canonical
  everywhere else, and a vector that writes one is a mistake worth
  pointing at.
- **Coverage rulings on the sixteen undecided rows.** `string` and
  string literals, SpecTec's non-header arrays, `packet_in.length()`,
  static extern methods, mutable initial entries and per-entry `const`,
  object initializers and abstract methods: out by scope, each an
  additive change if wanted. P4 `type` (newtype): elaborated to its
  underlying type like typedef. Functions and their calls: elaborated
  by inlining at the call site, as p4c does. Constructor parameters on
  parsers and controls: elaborated into one block per instantiation
  with the arguments substituted, the same rule as block instances.
  `range` and `optional` match kinds and `..` in entries: out by
  thesis, since core.p4 declares only exact, ternary and lpm.
- **`switch` on `action_run` is elaborated** into a block local that
  each action assigns a distinct value to, followed by an if-chain; the
  ACL corpus does it and names it.
- **The one theorem is the extract-then-emit roundtrip**, stated over
  the pure packing functions the Lean interpreter's emit and extract
  call and lifted to the emitter's bytes, not over the monadic
  interpreter loop. That is what is provable without Mathlib in a day
  and what the design meant; the module doc says exactly what the
  monad plumbing leaves uncovered.
- **Every external input is pinned, and the pins are listed.** After
  Bili's requirement that anyone reproduce the build and any agent
  resume the work: the p4c image by digest, GitHub Actions by commit,
  the oracle's opam-repository by commit inside a flake shell of its
  own, all in the table in `docs/workflows.md`. The earlier choice to
  keep OCaml out of the default shell stands; it lives in
  `devShells.oracle`.
- **AGENTS.md is the resumption entry point** and `docs/workflows.md`
  the procedures; `docs/status.md` carries an "Open threads" section.
  Nothing needed to continue the work may live outside the repository.
- **eDSL v2 proposed, not yet built** (`docs/notes/edsl-v2-design.md`).
  Bili asked for an eDSL that is as type safe as possible and never
  refers to things by string. Two surveys (pakeles and p4py; the HDL
  and compiler eDSLs) and two pyright probes led to: headers and blocks
  as classes, states and actions as methods, widths as `Literal` type
  parameters, `Bits[Any]` where the type system has no width
  arithmetic, no source reading, goldens unchanged. Awaiting Bili's
  review of the open questions before code.
- **eDSL v2 design accepted (Bili, 2026-09-22)** as recommended in
  `docs/notes/edsl-v2-design.md`, all fifteen points. Build order: the
  typed surface with the forwarder golden as its acceptance test, then
  the corpus rewrite and the pyright diagnostics suite in parallel,
  then a review. The v1 builder becomes `p4blo.edsl.core`, the
  implementation layer and the documented dynamic API for generated
  programs; goldens do not change.
- **p4c and BMv2 from Bili's multi-arch builds.** The official p4c image
  is amd64 only and crashed under emulation on ARM; github.com/qobilidop/
  p4lang-builds publishes native amd64 and arm64 images of p4c 1.2.5.15
  and BMv2 1.15.4 with immutable version tags. p4c is pinned by its index
  digest; the BMv2 image makes the optional second oracle cheap.
- **eDSL v2 as implemented deviates from the note in four places**,
  each forced by the type checker and accepted: the width aliases
  `bitN` are places (`Var[L[N]]`) and a typed literal `bitN(v)` types as
  a place too, because annotated fields must be assignable and action
  parameters must accept literals, so a literal used as a target is
  caught at run time only; `Bool`, `Enum` and `Error` targets have no
  static place split; an extern's `in` parameters accept any value
  (`Val`) with the width checked at run time, since binding `T` to a
  place type would reject cast rvalues; sub-block call arguments are
  run-time checked, as a callable protocol from annotations cannot be
  expressed. `assign` is overloaded over target kinds, so pyright
  reports a failed assignment as `reportCallIssue`; four must_fail
  headers say so. Everything else in the note's table holds.
- **BMv2 is the second oracle** (`oracle/bmv2/`), built on the pinned
  multi-arch p4c and BMv2 images grafted into one. It decides what
  P4-SpecTec cannot: longest prefix from a real lpm table, const-entry
  priorities, and runtime ternary priorities (inverted as p4c's own
  runner does, since BMv2 has the smaller priority winning). It cannot
  see `flood`, which no corpus program declares today.
- **The BMv2 oracle prints `stack.last`, not `stack[stack.lastIndex]`.**
  p4c compiles the two spellings differently: the member form becomes
  BMv2's `stack_field` select key, the index form a dynamic expression
  `simple_switch` refuses to load. The IR has only the index form (the
  coverage table elaborates `.last` to it), so the rewrite lives in the
  oracle runner rather than the printer, whose output is a golden shared
  with the other oracle and the p4c typecheck.
- **An out-of-range register read diverges from BMv2, knowingly.** p4blo
  yields zero; BMv2's `register_read` leaves the destination untouched,
  so a field keeps its parsed value. P4 leaves this
  implementation-defined; p4blo's choice is in `docs/semantics.md` and
  implemented in both interpreters, so the divergence is recorded as a
  strict xfail in `tests/test_oracle_bmv2.py` and in
  `corpus/register_bounds/README.md`, not resolved. Revisit only if a
  corpus program comes to depend on the difference.
- **The eDSL review's findings are all fixed** (`notes/reviews/edsl-v2.md`).
  Two mattered: the typed const entries were checked nowhere, because a
  fallback `Table` overload accepted any sequence of keys and every
  corpus program used the form that selected it, so a tuple of keys now
  selects only the typed overloads; and `select` compared keysets with
  Python equality, which on two eDSL literals built an expression and
  asked it for a truth value, so keysets are now compared as the IR
  holds them, which also makes the duplicate and unreachable-case checks
  work for literals and enums for the first time. An enum assignment
  across two enum types is now a static error too, through a protocol
  that puts the type parameter in a contravariant position. An action
  may call another action, which the IR allowed and the surface refused.
  `StateRef.__call__` is defined only outside type checking, so pyright
  keeps its better diagnostic and an untyped program still gets an
  EdslError.
- **Node in the flake.** The `pyright` wheel downloads its own Node
  when none is on the path, which is a hidden unpinned dependency.
  The flake provides Node so the download never happens.
- **Port rules.** A switch's ports are `0` to `ports - 1`, and both
  architectures and Lean's `Switch` apply the same two rules. An
  `egress_port` outside that range drops the packet with the
  diagnostic "egress_port N is not a port of this switch", the way a
  misaligned parse is dropped; the filter has no port count and passes
  any `bit<9>` port through. An `ingress_port` outside the range is
  the caller's error, raised before anything runs (a `ValueError` from
  the architecture's `run`, an `error` reply from `p4blo-lean run`),
  and so is one that does not fit `bit<9>` under the filter; the STF
  parser rejects such a port with its line. 511, BMv2's drop port, is
  just an out-of-range port here: a program that writes it without
  `drop` is dropped by these architectures for that reason and by
  BMv2 for its own, and the oracle does not judge fates through the
  port count anyway.

## 2026-09-23

- **Verification beyond the prototype, accepted by Bili.** The next
  substantial work strengthens the Lean specification and its connection
  to Python, before pursuing the p4c bridge. `docs/verification.md` gives
  the stages and their acceptance criteria. Cedar's executable formal
  model, property proofs, typed generators and component-level DRT are
  the precedent; universal equivalence of Python and Lean is not claimed.
- **Replay the whole experiment.** STF remains the corpus/oracle format,
  but a differential failure needs a versioned JSON bundle with the exact
  program and input sequence, because extern state survives packets and
  STF cannot express every IR value. Seeds and single-packet excerpts are
  useful diagnostics, not self-contained stateful reproductions.
- **Observe logical extern state after every request.** Differential
  replies include named register widths/cells, counter values and checksum
  instance presence, including on errors. Naturals use hexadecimal strings;
  instance ordering is irrelevant. Missing state or unsupported adapters
  fail instead of silently comparing packets alone. Internal errors are
  not claimed transactional: observing the state makes any mismatch
  visible, while valid-input campaigns reject all such errors anyway.
  Review caught Python's decimal-conversion limit on a valid bit<16384>
  register; hexadecimal preserves arbitrary widths without changing
  interpreter-global security settings.
- **Adversarial verification is recurring work.** At Bili's request,
  intentionally mutate both implementations in isolated worktrees, record
  killed and surviving mutants, improve tests for survivors, and repeat.
  Build failures do not count as detected semantic inconsistencies.
  Scoped decisions and commits proceed autonomously and remain recorded
  for later user review.
- **A first sound validity boundary is the closed scalar fragment.**
  `ScalarTyping.check` produces syntax-directed evidence, and
  `check_sound` proves the existing evaluator succeeds with exactly that
  type and preserves every initial Run. It does not copy the evaluator
  or require statement execution to become transparent first. Variables,
  lookahead, aggregates and statements remain outside the theorem; the
  checker is not a replacement for whole-program validation.
- **Mutation survivors drive generated-program coverage.** The first
  campaign killed four state/register mutants but missed wrapping
  saturating-add in Python and a wrong oversized shift in Lean. Add
  systematic scalar boundaries plus recursively typed Hypothesis
  expressions embedded in validated packet-observable IR programs.
  Shrinking preserves types; invalid generated programs fail rather than
  being filtered away. Retain concrete failed programs under
  `.artifacts/drt/`, independent of Hypothesis's local example cache.
- **Proof trust is a build gate.** Warnings are errors in the Lean package;
  a default `ProofAudit` target checks advertised theorems' transitive axiom
  sets against the reviewed standard foundations. This is stronger than
  grepping for `sorry`: an imported custom axiom or native proof shortcut
  also changes the audit. It checks proof dependencies, not whether a
  theorem states the intended semantic property.
- **Statement execution uses an explicit continuation machine.** A total
  step function performs one semantic operation; the actual interpreter
  drives it using Lean's proof-visible `partial_fixpoint`. Finite traces
  imply the actual driver result. Block-return continuations run during
  fault unwinding; action returns and table hit writes remain success-only.
  This preserves existing behavior without treating a resource budget as
  ParserTimeout. Global termination for validated programs is a separate,
  still-open theorem.
- **Prototype certificates by bounded reexecution.** The total checker
  uses the actual machine step and proves accepted observations equal the
  actual driver's result for the complete supplied initial machine.
  Exhaustion is a checker verdict, not a P4 fault. Start with a standalone
  register/counter control fragment and include exact fault tags/messages
  and relevant persistent/local state. This is deliberately not a faster
  verifier, a whole-switch certificate or universal Python verification.
  Concrete acceptance relies on the compiled checker and serialization;
  the artifact itself is not a kernel-checkable proof term.
- **Bind the certificate experiment at the decoded AST boundary.** The
  Lean executable exports its fixed example's protobuf JSON; the claim
  envelope carries that complete program and rejects a different decoded
  AST, initial values or observation. Sharing syntax is intentional;
  Python must run its own production interpreter, not reuse Lean results.
  The standalone control is not a valid whole-switch program. Use explicit
  accepted/mismatch/exhausted/invalid outcomes and canonical hexadecimal
  state values. `docs/certificates.md` records the wire contract and trust
  boundary before adding the Python producer.
- **Discover conformance suites rather than enumerate files.** Required
  Lean CI selects `lean_agrees` tests across the test tree. New certificate
  and stateful suites must not silently fall outside the gate. Build Lean
  before running conformance in a worktree: a concurrent rebuild can remove
  the executable while tests need it, producing a real but avoidable failure.
- **Fix zero serialization at the source, not in the claim producer.**
  The Python certificate bridge exposed that Lean's JSON encoder omitted
  decimal-string zero values. A protobuf string defaults to empty, not to
  `"0"`; Python correctly could not execute the exported empty bit literal.
  Always emit decimal strings, including zero, for literals and table keys.
  Lean-only round trips had hidden the defect because its decoder supplied
  zero for an absent value. Keep the producer's actual input unmodified by
  an adapter-specific repair and add explicit wire regressions.
- **Generate stateful programs as well as their input sequences.** Fixed
  stateful corpus programs cannot vary cell widths, independent register
  and counter bounds, arithmetic or operation ordering. Generate typed
  switch contexts with those choices and compare every request's packets
  and complete abstract extern state. Shrink configurations and packet
  lists together without filtering invalid programs. Deterministic cases
  force boundary and persistence behavior; generated sequences explore
  combinations. Include both program and inputs in replay artifact names.
- **Produce claims by executing production Python unchanged.** The fixed
  certificate adapter loads Lean's exported syntax, independently binds
  Python's environment/externs and runs `stmt.execute`. It serializes actual
  completion and observed state, not a separately calculated answer.
  Creation and verification are separate commands; only Lean acceptance
  accepts a claim. Strict verdict/exit-code checks and bounded subprocess
  lifetimes extend the harness's fail-closed rule to this experiment.
- **Review the observer adversarially, not just the evaluator.** The first
  certificate adapter passed its tests but certified stale extern objects
  after binding replacement and erased inconsistent cell widths. Resolve
  bindings from the final environment and reject malformed representations
  before projection. Retain these mutants as tests. Always clean up owned
  subprocess groups, including after a successful leader exits, and reject
  duplicate JSON response keys rather than silently choosing one verdict.
- **Lean owns the abstract IR; protobuf owns its encoding (direction
  agreed, migration pending).** Bili agreed that Lean should define
  abstract syntax, validity, and meaning, with an explicit verified
  conversion to the versioned protobuf representation. This revises the
  earlier normative-syntax split as a target, not an implemented guarantee.
  Generation is optional; stable wire metadata and conversion obligations
  matter more than which file generates which. The rationale, proposed
  obligations, organization context, and unresolved plan are in
  [notes/ir-spec-boundary.md](notes/ir-spec-boundary.md). Bili requested
  documentation only, no commit yet, while continuing to adjust the plan.
- **A separate user-facing Lean package (design agreed, not built).**
  Bili accepted the prior-art-informed design in
  [notes/ir-spec-boundary.md](notes/ir-spec-boundary.md): a Lean library
  imports the authoritative IR package and provides an ergonomic typed
  eDSL, verified lowering, and an interpreter API. Use selective
  proof-producing elaboration, not a general compiler from arbitrary Lean.
  Reuse reference execution initially; introduce distinct execution
  representations only for concrete benefits, with refinement proofs.
  Validity, meaning preservation, serialization, and application properties
  remain separate obligations. A small stateful end-to-end example is the
  proposed first milestone; exact syntax, proof interfaces, and sequencing
  remain open. Documentation only for now; leave changes uncommitted while
  Bili continues the design discussion.
- **Use progressively demanding examples toward the broader north star.**
  Bili agreed that full architecture-independent P4 expressiveness with a
  minimal semantic core is a north star, not the next deliverable. The
  intermediate roadmap consolidates the existing corpus, then supports
  the tutorial stateful firewall, `xdp-filter`, conditional flowlet switching,
  and a bounded Katran configuration. Each stage requires precise scope,
  readable Python/Lean authoring, original-program comparison, scoped
  proofs, adversarial checks, and justification of IR additions. Preserve
  the firewall's Bloom-filter limitations. Use P4-SpecTec for P4 and original
  Linux BPF execution for XDP; do not imply a general eBPF translator or
  Linux model. Flowlet switching depends on a feasible time/randomness
  oracle; Katran's exact profile requires an audit. Details and sources are
  in [notes/ir-spec-boundary.md](notes/ir-spec-boundary.md). This records
  direction only; implementation remains deferred and changes uncommitted
  while the design discussion continues.
- **Implement the accepted plan autonomously, Python and Lean only.**
  Bili removed Rust from scope, then explicitly authorized implementation
  and resumed small tested commits and pushes. This supersedes the earlier
  discussion-only/no-commit instructions. `implementation.md` tracks the
  finite example-driven roadmap; full P4 expressiveness remains a north
  star. Record uncertain decisions and revisit triggers instead of waiting
  for feedback. Confidence: high on scope, medium on sequencing; revisit
  sequencing when source audits expose infrastructure or semantic gaps.
- **Migrate ownership before adding language features.** Preserve the
  existing `P4blo` spec module names and executable protocol when moving
  them to `ir/`; the new user library will use `P4bloLean` modules to avoid
  import collisions. Keep the schema alongside the spec, not in a separate
  top-level `proto/`. Confidence: medium; revisit naming if public API use
  exposes avoidable friction. This is a structural boundary, not a claim
  that whole-program validity or all codec proofs already exist.
- **Existing public APIs may change for demonstrated usability gains.**
  Bili explicitly authorized redesigning the Python eDSL as well as other
  components. Preserve the semantic contract and readable examples; keep
  authoring changes separate from semantics changes and migrate callers
  with diagnostic/golden tests. Confidence: high on permission, medium on
  which redesign is best. Revisit using the firewall and Lean authoring
  experience rather than rewriting the working Python surface speculatively.
- **Shared verification assets live under `tests/`.** Move the corpus and
  oracle drivers/build contexts there, preserving all program/golden/vector
  bytes and oracle pins. Make `tests` an explicit Python package for stable
  adapter imports. Confidence: high; revisit if published examples need a
  separate installation/distribution story, not merely another root folder.
  Assert nonempty/minimum corpus discovery and preserve relative vector IDs
  so migration cannot hide tests or the strict BMv2 divergence. The move
  also puts oracle Python code under pyright; retain that stronger gate.
- **Make scalar equality proof-visible.** The typed Lean eDSL's semantic
  preservation proof needs to unfold bit/bool equality, but `Value`'s
  nested-recursive derived BEq is opaque. Give `Value.equal` explicit bits
  and bool cases using the identical width/value comparisons, with audited
  definitional equations and tests against the prior derived comparison.
  Confidence: high; this exposes existing meaning rather than introducing
  a separate evaluator or adding an axiom. Compound equality is unchanged.
- **Preserve the original firewall as an independent oracle input.**
  Pin and vendor the unchanged tutorial solution with its Apache-2.0
  notices, separately from p4blo-printer output. Run the stateful sequence
  directly on SpecTec and BMv2 in their existing CI jobs. Distinct TCP
  sequence numbers preserve identical flow hashes but prevent aggregate
  queues from confusing rejected and accepted requests. Confidence: high
  for oracle feasibility; packet-only observations remain insufficient for
  full state/CRC assurance. Revisit the adapter when register observation
  and collision witnesses are added for the actual port.
- **Start verified Lean authoring with an independently meaningful scalar
  language.** Index constructors by scalar type, require positive widths
  and fitting literals, and give them Fin/Bool source denotations that do
  not call lowering or the interpreter. Prove exact computation and whole-
  Run preservation, not just result typing. Confidence: high for the closed
  fragment; typed references/frames are the next boundary. Scoped notation
  and ordinary constructors avoid a premature custom statement parser.
  Confidence: medium on syntax; revisit with packet/stateful programs.
  Independent expected packets guard the surface that the kernel proofs
  do not verify. `lean/ASSURANCE.md` records the remaining decisions, exact
  exclusions and the three reproducible mutation experiments.
- **Preflight an authentic small XDP build before broad translation.**
  Start investigation with upstream's Ethernet-only default-allow feature
  build, preserving MAC lookup order, all per-CPU map slots, wrapped counters
  and distinct actions. Confidence: medium on milestone ordering; revisit
  after firewall integration. Keep GPL oracle inputs separate and review
  redistribution before porting source. Prefer an FD-only kernel harness
  without interface attachment, pinned maps or live-frame execution; never
  infer a passing oracle from Docker availability or a skipped kernel test.
  `notes/xdp-preflight.md` records exact pins, checks and remaining authority
  boundaries. This decision authorizes no global kernel security changes.
- **Add byte CRC services without enlarging core IR syntax.** Use stateless
  `crc16`/`crc32` extern contracts with exact positive byte-aligned widths,
  full results and no implicit range reduction. Confidence: high on meaning,
  medium on API generality; revisit for non-byte inputs or another polynomial.
  Independent original-P4 known answers found pinned SpecTec's odd-byte
  padding defect, while BMv2 confirms the selected standard behavior. Keep
  narrowly classified strict expected discrepancies plus passing controls;
  do not adapt input to manufacture agreement. The simple original firewall
  flow sequence cannot detect a consistent wrong hash. Full state/collision
  observations remain required for the port. See `notes/crc-contract.md`
  and `notes/reviews/crc-externs.md` for exact findings and review fixes.
- **Reserve `P4blo` for the user-facing Lean library.** Supersede the earlier
  temporary choice to preserve the specification's `P4blo` namespace and
  name the frontend `P4bloLean`. The independent spec is now `P4bloIR`
  (Lake package `p4blo-ir`); the user library is `P4blo` (Lake package
  `p4blo`). This follows Bili's requested public naming and makes the IR
  dependency explicit. Confidence: high. Preserve the `p4blo-lean` executable
  and all wire identities; no duplicate compatibility library is needed
  before the initial API stabilizes. Historical review logs retain the
  original symbols so their evidence remains attributable to their commits.
- **Extend verified authoring through exact typed-frame agreement.**
  Follow `notes/typed-frames-plan.md`: context-indexed scalar reads first,
  then assignment/sequence/if proved against the existing execution machine.
  Keep source values and environments independent of the IR evaluator and
  distinguish declaration agreement, value agreement and write permission.
  Confidence: high on obligations, medium on positional context representation;
  revisit when typed packet fields expose ergonomic or transport overhead.
  Prove related frames exist rather than hiding an impossible precondition.
  This is a scoped body fragment, not a whole-program validity claim.
- **Reject missing decimal strings instead of manufacturing numeric zero.**
  Lean's Nat-based IR cannot preserve protobuf's invalid empty-string value.
  Use the protobuf string default first, then decimal decoding, for bits
  literals and LPM/ternary value/mask fields. Confidence: high; eight executable
  cross-language regressions reproduced the prior mismatch. Preserve explicit
  `"0"` and leading zeros; do not change native numeric-field defaults or claim
  full ProtoJSON parity. Invalid request decoding must preserve extern state
  and leave the service usable for later valid requests. The complete codec
  representability and semantic-version contract still needs formalization.
- **Observe original firewall state through a scoped BMv2 barrier.**
  Replay fresh-switch sequence prefixes, append a distinct non-stateful
  final sentinel, wait for it and output settling, then allow only complete
  register reads. Parse the entire pinned CLI transcript and compare all
  8192 cells, including zeros. Confidence: high for the pinned single-ingress
  FIFO implementation and this ingress-only firewall; medium as a reusable
  observer. Revisit before recirculation, asynchronous externs or another
  worker model. No general quiescence proof is claimed. Preserve legacy
  requests without the new deadline. See `notes/firewall-port.md` and its
  independent review for original-source state evidence and limitations.
- **Treat the original-program oracle as evidence to challenge, not a
  definition to copy.** Firewall route-miss probes exposed a separate pinned
  SpecTec LPM/ternary mask construction defect. Keep exact original/printed
  discrepancy tests and passing controls; BMv2 and the IR retain the intended
  route rejection. Confidence: high from source inspection and reproduction.
  Revisit on oracle upgrades; strict XPASS prevents stale exceptions.
  Packet equivalence alone is also insufficient for the fixed-width Bloom
  hashes: SpecTec's wrong CRC32 indices preserve their collision relation.
  Current support is a bounded, externally checked Python port, not universal
  translation correctness or a completed Lean firewall proof milestone.
- **Retain exact state and numeric contracts beside packet equivalence.**
  Actual Python and Lean CRC32 XOR-one mutations each preserve firewall
  packet behavior while permuting register indices. Existing full-state and
  independent known-answer gates detect both compiled faults; weaker packet
  gates survive. Confidence: high for these selected mutants, not general
  mutation adequacy. Record patches, complete replay reconstruction and
  restored baselines in `notes/mutations/firewall-hash-state.md`. Passing
  proof audits do not certify an external algorithm absent a theorem stating
  that contract. Revisit CRC refinement with an independent specification,
  not a theorem that merely restates the implementation being checked.
- **Keep exact frame agreement distinct from declaration validity.**
  Contextual scalar expressions use independent positional Fin/Bool values,
  while their lowering theorem observes actual action-first frame lookup.
  A constructive frame witness establishes nonvacuity, not that arbitrary
  block initialization is valid. Confidence: high on this separation;
  assignments must additionally establish real declaration and write-mode
  agreement. Context checking is sound and complete only for its declared
  scalar fragment. The reviewed `Quot.sound` addition to the typing audit
  comes from standard list membership/uniqueness, not a new trusted axiom.
  Surface accessors and exported inputs retain independent known answers
  because a valid-but-unintended source term can satisfy every lowering
  theorem. Confidence: medium on positional-reference ergonomics; revisit
  when writable places and packet fields are authored.
- **Save differential evidence before judging independent expected answers.**
  A genuine Python-read mutation exposed an assertion ordering gap: the
  authoring test failed before retaining its concrete program/request.
  Compare and save first, then judge agreement against known answers.
  Confidence: high; regressions replay an actual live/restored read fault
  and independently reject a shared wrong source program. This does not
  weaken known-answer checks or equate agreement with intended semantics.
- **Exhaust a named malformed profile before broad random traffic.**
  Check every byte truncation of one fixed firewall frame and state across
  valid-malformed-valid sequences; compare selected unchanged-original BMv2
  prefixes. Confidence: high within this bounded profile. A separate observer
  exposes parser error/validity without changing the parser or pretending to
  read Lean's internal cursor. Preserve failed-header payload and undefined-
  value boundaries. The actual consume-on-fault mutation is killed at runtime
  and saved/replayed. Generated flows remain a deliberate next step requiring
  independent expected state, not just a larger number of agreeing samples.
