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
- **Prove scalar command prefixes before extending aggregate paths.**
  Structured assignment/if/tails use independent positional source updates,
  lower without synthetic sequencing nodes and follow actual `Execution.step`.
  Preserve exact values, all unrelated Run fields and names outside the
  possible target set. Declaration permissions and no-action storage are
  separate premises; constructive scope/frame witnesses establish nonvacuity.
  Confidence: high for this finite fragment, not complete program validity.
  Six adversarial edits distinguish proof rejection, compiled wrong source
  intent and a retained actual Python-write mismatch. Next prove field
  primitives, then factor the existing expression/command read/write seam
  for typed aggregate paths rather than copying a second AST. Confidence:
  medium in that API factoring; revisit if a forwarding body needs pervasive
  transport annotations. See `notes/typed-fields-plan.md` for obligations.
- **Generate host policy changes while retaining exact Bloom behavior.**
  The bounded `tcp-flow-policy-v1` varies both directional table snapshots,
  client ports, flags and packet sequences. Independent GF(2) CRC16 and zlib
  CRC32 expectations compare every cell; the model is not exact conntrack.
  Unique sequence IDs prevent aggregate packet matching from hiding temporal
  admission mistakes. Confidence: high within this profile, medium on
  generator diversity. A real table-hit fault shrinks to one SYN with absent
  rules and is killed only by state comparison. Original BMv2 checks fixed
  policies; its current protocol cannot replace rules mid-sequence. Revisit
  that limitation before claiming original-oracle coverage of host changes.
- **Check field primitives before generalizing the authoring store.**
  Exact nominal kind/declaration agreement excludes header-first lookup
  ambiguity; exact list shape excludes the existing short-list setter no-op.
  Prove precise rebuilt values, validity and every sibling with whole-Run
  preservation. Confidence: high. This returns a container, not a persistent
  nested frame update or a typed-value theorem. Three actual setter faults
  are rejected by the primitive equation proof; source-path/runtime mutation
  evidence belongs to the next increment. Keep those boundaries separate.
- **Use isolated CI for compile-only XDP capacity.** Local Docker disk
  pressure is not permission to delete unrelated images/volumes or change
  global VM settings. Export/remove only own artifacts and run the pending
  native gate on an experimental repository branch's clean runner instead.
  Confidence: high on isolation, medium on portability until actual CI.
  No BPF load, interface attachment, added runtime capability or image
  publication is authorized by this step. Retain object provenance plus
  corresponding upstream sources; merge only after native checks and review.
- **Separate aggregate shape, nominal coherence and write permission.**
  Use independent finite indexed shapes/stores with explicit header validity
  and positional scalar paths. Actual nested writes preserve the converted
  full source store and unrelated runtime state. Local name/width checks do
  not imply one consistent Index exists: repeated type names require equal
  kinds and layouts. Confidence: high on these separate obligations; no
  general program initializer or root permission follows from operational
  correspondence. Factor the existing expression read seam next, then writes,
  retaining concrete final theorems rather than arbitrary correctness
  callbacks. Confidence: medium on generic API ergonomics; revisit against
  a realistic already-parsed forwarding body and preserve scalar examples.
- **Reject ambiguous harness JSON without validating away bad IR inputs.**
  Recursive duplicate keys and nonstandard numeric constants are malformed
  envelopes, as are boolean/float replay versions and wrong object shapes.
  Reject them before information is lost; normalize decoding failures to
  controlled protocol/CLI errors. Confidence: high from actual false-
  agreement controls and retained regressions. Continue to represent negative
  ingress, invalid installations and empty program objects for experiments.
  Unknown semantic fields/aliases, resource budgets and general ProtoJSON
  parity remain separate decisions; this narrow hardening cannot settle them.
- **Own and verify the lifecycle of each offline XDP check container.**
  A real timeout reproduced a daemon container surviving its attached client.
  Generate an internal unique name, reclaim that exact target in `finally`,
  and verify absence with a successful bounded listing. Preserve nonroot,
  network-free, capability-free and read-only execution. Confidence: high
  for ordinary exception/timeout cleanup, not daemon outages, process death
  or late creation races. Revisit a split create/start lifecycle if that
  stronger guarantee becomes necessary. Never use global pruning as cleanup.
  Independent reproduction, review and post-fix evidence are retained in
  `notes/reviews/xdp-cleanup.md`; this changes no BPF or semantic claim.
- **Share scalar operators through typed read references.** `ExprWith` owns
  source operators, their independent denotation and lowering once. Scalar
  bindings and aggregate paths supply only reads; advertised field theorems
  discharge leaf laws through concrete Index/frame correspondence. Confidence:
  high in proof scope, medium in ergonomic factoring. Retain old scalar APIs
  and revisit against writable forwarding bodies before adding notation.
  Observe state after evaluation: pre-expression snapshots can miss a read
  side effect even when all snapshots and the result are individually right.
- **Prove actual representable leaf codecs before recursive transport.**
  Bound only protobuf uint32 fields, preserving semantically invalid leaf
  syntax for testing. Universal JSON-value round trips use production code
  and default axiom audits; independent protobuf answers additionally reject
  paired wrong encoder/decoder mappings. Confidence: high in this boundary.
  Use type-sensitive JSON comparisons because Python equates false with zero.
  KeyValue leaves follow; text parsing, recursive decoder termination and
  semantic-version/unknown-field policy require separate decisions.
- **Challenge mutable aggregate copies with post-write full observations.**
  Bounded header/record assignments expose source, target and unrelated stored
  fields and validity after writes, even for invalid headers. Keep independently
  computed expected bytes alongside real Lean agreement and replayable live
  copy-alias mutants. Confidence: high for selected aliasing faults, medium
  for generated shape diversity. Extend to stack and call/copyback order when
  those become verified authoring features; do not infer them from this profile.
- **Factor command composition before claiming a writable field instance.**
  `CmdWith` owns one source AST/denotation/lowerer and composes per-leaf laws
  through the actual continuation machine. Preserve the scalar API with
  concrete adapters; add actual root permission relations first, then prove
  the field instance separately. Confidence: high in exact prefix/permission
  obligations, medium in the dependent API. The route-selected forwarding
  rewrite in `notes/field-commands-plan.md` is its ergonomics revisit trigger.
- **Keep successful call profiles inside the validated alias policy.**
  Read-only input may overlap an inout header, but writable overlap and
  action/enclosing-name collisions are invalid. Generate only valid calls
  and retain independent post-call snapshots, out-zero/invalid defaults and
  untouched payload. Confidence: high for selected copy faults, medium for
  shape diversity. Parser-error copyback and table-invoked actions need their
  own observation contracts; normal control calls cannot establish them.
- **Check decoded key meaning in addition to encoded round trips.**
  Paired ternary value/mask wire swaps preserve both round trips while changing
  the abstract key. Independent unequal-component decoded-value fixtures kill
  the fault; representability deliberately does not imply semantic key validity.
  Confidence: high. Keep raw leaf replays separate from execution DRT, select
  named campaign inputs explicitly and require each to exist so campaigns
  can coexist without an empty-input false pass. Investigate actual recursive
  decoder termination next, not a duplicate decoder used only in proofs.
- **Make the actual Expr decoder total before extending codec proofs.**
  Preserve accepted finite JSON, null/default behavior and diagnostic order
  through proof-carrying helpers with erasure laws. Checked structural bounds
  handle synthetic empty objects without changing their errors. Confidence:
  high in descent, medium in helper-refactor size; review the first Expr-only
  implementation before LValue and statement arrays. The pinned Except
  fixed-point machinery is not a drop-in alternative for non-tail recursion.
  Feasibility evidence and limits: `notes/codec-recursion-plan.md`. Logical
  termination is not a runtime resource bound; process failures must retain
  replay evidence rather than escape the observer.
- **Separate intended forwarding policy from faithful lowering.** A wrong
  same-width destination accessor passes generic correctness and differential
  agreement, but independent answers reject it. Add a complete constructor-
  based state view with inverse laws, then prove the authored body implements
  an independent hit/TTL policy for arbitrary stores and lift it to actual
  execution. Confidence: high in this bounded contract; no packet parser,
  routing table, checksum or architecture fate follows. Keep invalid-header
  stored values in scope because the body does not test validity. Revisit
  assumptions when integrating a complete authored application.
- **Resolve names before adding custom Lean authoring syntax.** Existing
  typed references and commands remain the sole source representations.
  A total unambiguous named-path resolver can remove positional mistakes;
  a later list-sequencing combinator can remove nested parentheses.
  Confidence: high in preserving meaning, medium in constructor diagnostics.
  Review against `notes/authoring-ergonomics-plan.md`; introduce an elaborator
  only if ordinary checked constructors remain materially awkward.
- **Anchor even a proved application state mapping independently.** A paired
  swap of both observed/reconstructed MAC fields and corresponding route
  fields preserves inverse laws and the universal forwarding policy. Keep a
  manually built asymmetric Store and independently named Snapshot as kernel
  and native known answers; those reject the coordinated relabeling.
  Confidence: high for this demonstrated shared-model fault, not universal
  observer adequacy. Revisit every new application view for the same trap.
- **Make command lists a transparent composition helper, not another AST.**
  A right fold over existing sequence nodes preserves source order, while
  the independent denotation law uses a left fold over source states. Keep
  exact old AST/export checks and order-sensitive branch/shared-tail answers.
  Confidence: high in equivalence, medium in larger-program ergonomics.
  Revisit notation only when a real application still needs it; do not imply
  runtime bindings with surface syntax the source language cannot express.
- **Observe operator constructors independently of their wire names.**
  A paired NOT/NEGATE name-table swap passed actual codec round-trip proofs
  and the first conformance observer, which reused that production table.
  Exhaustive independent constructor cases and a native known answer kill
  it without changing the theorem's scoped claim. Confidence: high for this
  demonstrated fault, not a guarantee against all shared-model mistakes.
  Apply the same independence review to each added codec constructor; retain
  exact process-failure inputs and pre-refactor transcripts as separate evidence.
- **Keep header-validity reads separate from scalar writable places.**
  A constrained HeaderPath/HeaderRef can observe stored validity but cannot
  supply an lvalue or writable Boolean scalar Ref. This preserves the current
  scalar-write validity laws. Prove concrete primitive evaluation/typing first,
  then use the existing generic read-family seam and add a separately named
  validity-guarded policy. Confidence: high in the proof boundary, medium in
  the small duplicated navigation and coercion ergonomics. Revisit a generic
  endpoint path when a second aggregate operation justifies its broader
  refactor. Reviewed scope/probe: `notes/header-validity-plan.md`.
- **Discharge initialization premises in bounded layers.** Independent source
  zero corresponds to the actual initializer under nominal agreement and an
  explicit maximum-depth fuel bound. Do not infer that bound from arbitrary
  nominal declarations or replace runtime fuel to simplify a proof. Prove
  Frame.forBlock next against every actual scope variable, including observer
  extras; call entry/copyback stay separate. Confidence: high in the zero
  correspondence, medium in the generic HashMap-loop proof cost. Prefer a
  concrete forwarding instance if generalization delays the useful bridge.
  Scope: `notes/initialization-bridge-plan.md`, `notes/source-zero.md`.
- **Use fresh Lean caches across package moves.** A standalone query exposed
  stale pre-rename modules in a copied IR build cache. Retaining the old cache
  outside the worktree, rebuilding both packages from empty build directories,
  and rerunning required DRT closes this dependency concern. Confidence: high
  for the reproduced cache issue; fresh CI remains independent confirmation.
  Never move build directories while binary consumers are still running.
- **Reuse checked recursive codec helpers for LValue and compose Arg laws.**
  LValue's index expression uses the already-total Expr decoder; no mutual
  recursion or new traversal helper is needed, and Arg's decoder is unchanged.
  Bound only embedded Expr wire fields and retain invalid semantic syntax.
  Confidence: high in this boundary, supported by exact original transcripts,
  independent decoded constructors and paired mapping faults. Revisit helper
  equivalence separately for statement arrays and their first-error order.
- **State frame initialization over actual map entries, not only a model.**
  The existing forIn loop admits exact lookup/scope/no-action proofs without
  a runtime refactor. Require actual zero success for every scope entry;
  preserve map keys even when stored declaration names disagree, and preserve
  the looked-up scope even when its block differs from the requested block.
  Confidence: high after constructive witnesses and compiling loop faults.
  The generic proof-cost uncertainty is resolved for this checkpoint. Revisit
  premise discharge in the source adapter, including extra observer variables
  and a real-built forwarding scope; do not infer global validation.
- **Distinguish the operation under test from its observer in fault controls.**
  The first scoped validity fault also matched observer reads, making a weak
  pre-read snapshot fail for the wrong reason. Test-only identity-mux operands
  isolate observer validity reads from the authored member read. The same
  single-hit side effect now survives the weak observer and fails the complete
  post-read observer, with exact independent packet answers and retained input.
  Confidence: high for this demonstrated gap, not universal observer immunity.
  Revisit observer independence for every new stateful operation and preserve
  the original scalar write/forwarding contracts when extending read syntax.
- **Discharge modeled frame values, but require explicit extra zeroability.**
  The source-frame adapter uses independent source zero for modeled roots;
  only unmodeled actual entries need additional zero-success evidence. Full
  coverage is a separate predicate, never inferred from root declarations.
  Concrete actual Index.build/lookup witnesses use kernel-checked cbv and are
  default-audited alongside the application theorem. Confidence: high after
  constructive positive and false-premise witnesses; the finite builder proof
  needed no production refactor. Revisit the extras API when real call entry
  needs scope-extension lemmas. Hand-extended observer fixtures do not stand
  in for the packet wrapper or prove argument binding.
- **Keep validity-guarded forwarding a separately named application.**
  Reuse the complete independent Snapshot and earlier hit/TTL policy; add
  both-header validity and a separate full-state invalid-drop-only theorem.
  Neither a valid-header premise nor the old body is changed. Confidence:
  high for this exact stored-state contract, medium in positional HeaderRef
  ergonomics. Revisit certified named header endpoints when further aggregate
  operations need them. Independent expected packets must also check exporter
  selection: choosing the old body passes its proofs and engine agreement but
  is not the intended guarded program. Metadata drop is not network fate.
- **Prove prefixes of the real flat body rather than reshaping the wrapper.**
  Strengthen the existing command induction with an arbitrary unexecuted
  statement suffix and derive the former whole-body APIs as empty-suffix
  instances. Keep the real branch empty-list transition explicit. Confidence:
  high after independent queue/step answers and a compiled statement-tail
  fault caught both logically and by Lean/Python replay. Revisit a general
  list-composition relation only if another non-command prefix needs one.
  No typing, execution or termination claim applies to the pending suffix.
- **Attempt certificate process-group cleanup once and fail closed.**
  The macOS CI trace shows a redundant final kill masking an already-raised
  timeout error; it does not establish why that kill was denied. Record the
  attempt before signalling, retain normal-exit cleanup, bound follow-up
  reaping and reject otherwise accepted output if cleanup fails. Confidence:
  high for this reproduced control-flow failure, limited for OS-level group
  identity and escaped descendants. Revisit with captured process evidence
  if the first signal is denied or a descendant survives the live test;
  retries alone do not close a failing CI checkpoint. Evidence and review:
  `notes/certificate-cleanup.md`, `notes/reviews/certificate-cleanup.md`.
- **Prove actual call entry before body execution and copyback.** The fixed
  four-root wrapper admits exact actual dispatch, ordered argument binding,
  whole-Run frame replacement and captured caller/continuation laws. Its
  source bridge discharges real initialization using a kernel-checked built
  declaration index. Confidence: high for this bounded operational result;
  an arbitrary preserved observer value is not implicitly well typed. Keep
  the empty-body witness explicit and revisit the fixed arity on a second
  real call shape. Scope and review: `notes/plain-call-entry.md` and its
  independent review.
- **Freeze full state and compare JSON types at proof/test boundaries.**
  Identity checks missed mutations of aliased caller/shared state; program
  bytes alone missed index lookup-table changes; ordinary Python equality
  accepted integer zero in place of Boolean false. Detached index/scope
  snapshots, immutable contents, type-sensitive complete JSON comparisons
  and exact case-set checks now have permanent survivor/rejection controls.
  Confidence: high for the demonstrated gaps, not universal observer
  correctness. Apply this discipline to the next internal-prefix observer;
  an exception after observation still invokes Python call copyback.
- **Parameterize the actual built body before composing the guarded call.**
  Keep the old empty-body entry API as an instance, but prove actual lookup
  and scope identity for the body-bearing program. Then compose actual
  local assignments and the existing flat-prefix theorem, leaving observer
  and return work pending. Confidence: high in the semantic composition,
  medium in symbolic Index.build proof reuse. Prefer small map-transport
  laws over copying initialization proofs if reduction is costly. Revisit
  after a second signature needs a more general API. The staged contract,
  exact identity checks and exclusions are in `notes/call-body-prefix-plan.md`.
- **Reuse one actual-built body family and preserve the empty API.** Symbolic
  body parameterization checks directly, including scope.block identity; no
  duplicate binder or initialization proof was needed. Existing entry bytes
  remain exact. Confidence: high for this verified reuse, medium for retaining
  the fixed signature as the future public API. Complete selected-block syntax
  checks distinguish arbitrary-body entry correctness from intended program
  syntax; wrong initializers/observer mappings can correctly pass entry proofs.
- **Prove normal return against the current callee-after Run.** Restore only
  the captured caller frame, then copy three fixed writable roots from the
  captured callee. Preserve current packet/extern/other shared effects rather
  than reverting to entry state. Confidence: high after actual-loop and
  restored-write feasibility proofs; keep typing, arbitrary lvalues and fault
  unwinding out of this slice. Distinct writes commute, so order requires a
  delegating trace observer rather than an order claim from final state alone.
  The reviewed boundary and tests are in `notes/plain-call-return-plan.md`.
- **Prove the two actual local writes without extending the source layout.**
  Use the reviewed plain-variable write law twice, then prove constructor
  source agreement and separate local declaration permissions. This keeps
  the unrelated observer-local extra outside the authored policy's roots
  and avoids a mixed one-command/one-raw-write proof. Confidence: high for
  this exact prefix, medium for a fixed two-local API. Revisit typed authoring
  of initializers when a second initializer shape requires expressions or
  more roots. Independent literal answers reject a paired body/source/result
  change that correctly preserves the generic proof; actual Python faults
  additionally require a saved clean-output mismatch and restored replay.
- **Check mutable copy isolation by branch, not equal snapshots alone.**
  Normal-return review reproduced three selective-alias faults that survived
  complete value snapshots and one Ethernet write. Require disjoint mutable
  aggregate objects and field lists, plus real Ethernet, IPv4, metadata and
  observer writes against the retained callee. Immutable leaf sharing remains
  allowed. Confidence: high for these fixed tree-shaped fixtures; no generic
  Stack/cycle or whole-Python memory theorem follows. Revisit this observer
  whenever a new mutable value shape enters the verified call profile. Keep
  the demonstrated survivors as permanent regressions. Evidence and review:
  `notes/plain-call-return.md`, `notes/reviews/plain-call-return.md`.
- **Require complete native state and exact Python types at the call prefix.**
  Review reproduced a packet cursor changing from int3 to float3.0 while the
  old shared-state equality passed. Recursive type-sensitive comparisons now
  reject numeric and mutable-container substitutes. Complete native Index,
  scope, installed-entry and shared-state comparators close the staged plan's
  coverage gap; corruption controls test the observers themselves. Confidence:
  high for the fixed observed representation and current constructors, not a
  universal observer theorem. Revisit whenever state constructors change.
  Keep the smaller JSON export distinct from the complete native checks.
- **Advance statement codecs through the real array traversal.** The checked
  attached-array erasure/descent probe supports a minimal total Stmt decoder
  with the same recurrence and diagnostics. Record old native transcripts
  before refactoring; preserve them alongside independent constructor and
  error-order anchors. Confidence: high in helper feasibility, medium-high in
  the nested statement roundtrip proof effort. Revisit proof organization if
  induction becomes unwieldy, not accepted syntax or the universal claim.
  Plan, probe and independent review are committed under `stmt-codec-plan`.
- **Port the actual forwarder next, preserving its original policy.** The
  complete guarded control theorem is a bounded synthetic profile, not the
  corpus forwarder: that program wraps TTL0, uses the old destination as
  source MAC, passes non-IPv4 and recomputes checksums even after default drop.
  Advance exact-golden Lean authoring, real execution and a modest invalid-
  IPv4 control property. Label raw declaration/parser/table/extern assembly
  as unverified; eliminate those seams incrementally. Confidence: high in
  application choice, medium in reusable builder/API shape. Revisit on a
  second real client or a proposed semantic change. The plan maps remaining
  action-frame, parser, table, checksum and architecture obligations in
  `notes/lean-forwarder-next.md`; do not substitute the guarded policy.
- **Keep codec consistency separate from intended wire behavior.** Actual
  total statement decoding and universal representable roundtrips now use
  genuine array membership and nested induction. Six compiling challenges
  distinguish two proof rejections from four faults that keep roundtrips:
  paired tags/branches, diagnostic indices and null defaults. Frozen
  independent constructor/error observations catch those faults. Confidence:
  high for the scoped laws and demonstrated detections, not universal Python
  codec equivalence. Preserve the old source identities separately from the
  changed decoder and test witnesses; 25 retained campaign observations are
  20 distinct requests, not 25 independent inputs. Revisit when constructors,
  omission/default rules or the pinned array library change. Evidence:
  `notes/stmt-codec.md` and its independent final review.
- **Prove the real selected table action before generalizing action authoring.**
  Table action data enters through `Work.tableAction`, not the expression/
  lvalue argument path. Add an unshadowed block-write law, then the exact
  four-assignment trace and return that retains inner block updates while
  restoring outer action layers. Confidence: high in this boundary, medium
  in retaining a direct fixed-body proof as the best reusable surface.
  Revisit on a second action needing parameter writes or copyback. Do not
  change the one command AST or weaken BlockFrame premises to fit this
  example. Reviewed plan: `notes/forwarder-action-next.md`.
- **Base active-frame root laws on actual map membership.** An action name
  alone neither establishes shadowing nor permits dropping the action map.
  The root-write prerequisite uses the actual missing action lookup and
  successful block lookup, with exact whole-Run results; action-hit read/write
  laws need no block premise. Confidence: high after constructive witnesses
  and four actual compiled frame faults rejected by the proofs. Keep these
  operational laws separate from source permissions and global validity.
  The old block API is a corollary, not a silently broadened contract. Scope
  and independent review: `notes/action-root-writes.md`.
- **Compose nine foundational declaration codecs next.** Remaining decoders
  form an acyclic graph after total statements; do not refactor them merely
  to add proofs. Reuse type/literal/list laws in a focused declaration-law
  module, keeping every direction and invalid-but-wire-representable shape.
  Confidence: high in feasibility after the independently checked probe,
  medium-high in nine laws remaining review-sized; split the six foundational
  laws from three extern-related laws if needed. Capture independent raw
  baselines first, and challenge the shared Direction name table explicitly.
  Full Program, text/binary codecs and semantic validity remain separate.
  Plan and review: `notes/program-codec-next.md` and its matching report.
- **Match runtime observations to the theorem's state boundary.** The real
  forwarder's invalid-control theorem preserves the entire Run; packet tests
  alone let an actual unintended ingress metadata write survive. Add direct,
  detached exact-type state checks, retain the weak observer's demonstrated
  survivor, and observe post-drop checksum separately. Confidence: high for
  these finite profiles, not universal Python object observation. Keep
  exact-golden authoring and public in-memory execution distinct from a
  complete verified frontend. Revisit the small ordinary declaration helpers
  on a second real client; add no macro or second AST prematurely. Scope and
  independent review: `notes/lean-forwarder.md`.
- **Keep action-layer field updates operational and target-specific.** Lift
  the authoritative root-write law through existing recursive field writes,
  requiring only the written root to be absent from the active action map.
  Other modeled roots may still be action-shadowed. Confidence: high for
  exact Run preservation and mixed-layer correspondence; medium for the
  long-term public adapter shape. Revisit on a second verified action, not
  by weakening the existing block-only command API. Independent proof review,
  witnesses and the precisely labeled false-conclusion challenge are in
  `notes/field-action-writes.md`. The full selected-action theorem remains
  a separate obligation.
- **Retain independent anchors when roundtrips and observers agree wrongly.**
  Nine declaration laws now compose actual total codecs under wire bounds.
  Shared Direction names and paired instance labels can preserve every law;
  independently authored native anchors still reject paired test-fixture and
  constructor-observer corruption that makes the Python checks pass.
  Confidence: high in these scoped laws and demonstrated detections, not
  universal wire-language or Python equivalence. Preserve exact old source
  provenance and distinguish the direct codec campaign from failed packet
  preflight. Revisit on any mapping/default/observer change. Evidence and
  independent review: `notes/declaration-codec.md`.
- **Compose table codecs next without semantic premises.** The reviewed
  four-law slice covers Key, ActionCall, Entry and Table using existing
  expression/literal/key-value/list laws. A checked unregistered probe proves
  the first three; Table composition remains work. Confidence: high for
  these prerequisites, medium-high for the complete composition and medium
  for the lasting file split. Revisit when Block/Program composition exposes
  reuse needs. Review corrected an important distinction: Entry action
  absence/null/empty all accept an empty call, but a present-empty Table
  default differs from absence. Freeze those independent answers before
  proofs; do not change the decoder to match an assumed presence rule.
  Scope, six kernel default anchors and review: `notes/table-codec-next.md`.
- **Use the exact tutorial firewall as the next Lean application.** Reuse
  existing source layouts and ordinary IR assembly without adding a firewall
  primitive. First establish golden identity, persistent full-array replay,
  actual initialization and a bounded invalid-IPv4 body identity. Confidence:
  high in this application boundary, medium in retaining direct Forwarder
  layout imports and the eventual effect/result surface. Revisit on a real
  coupling problem or second client, not by changing application policy.
  Keep arbitrary unused state separate from initialization, unchanged-program
  boundaries separate from the parser-observer clone, and dynamic host-entry
  replacement separate from constant-rule BMv2 evidence. Scoped Bloom
  properties follow; exact connection tracking and whole-pipeline equivalence
  are not claimed. Plan and review: `notes/lean-firewall-next.md`.
- **Prove actual selected-action completion before table composition.**
  Use the real literal table-action entry, complete independent field policy,
  exact ordered block-map updates and action-only layer restoration. Keep
  arbitrary continuation pending and derive public normal completion from the
  existing execution relation. Confidence: high in this fixed boundary after
  constructive witnesses, standard audits and five compiled model faults;
  medium in direct four-assignment composition as a reusable frontend API.
  Revisit for a second action needing parameter mutation or out/inout copyback.
  Strengthen auxiliary observers after each individual mutation: Boolean/int
  equality and a subsequent repairing write each hid an actual transient
  fault. The existing TTL0 input also catches a different destination-write
  fault; count it once, not as a new witness. Scope and independent review:
  `notes/forwarder-action.md`.
- **Separate fixed-application protocol evidence from generic IR replay.**
  A compiling firewall-server reset preserves all generic interpreter checks
  but loses flow history. Retain exact fixed request/reply transcripts and
  require complete arrays plus independent policy answers. Confidence: high
  after independent review and real reset/source/register-write campaigns.
  The new transcript and register-write fault reuse existing inputs; do not
  inflate independent witness counts. Keep small fixed wrappers for now;
  confidence in that duplication is medium, with extraction triggered by a
  third application or divergent behavior. Scope: `notes/lean-firewall-port.md`.
- **Distinguish proof-script sensitivity from a false codec law.** Four
  table laws preserve all wire-representable shapes and production bytes.
  A paired flag fault breaks a stronger intermediate proof equation while
  its empty-table roundtrip remains provable. Record exactly that, alongside
  independent semantic/error answers and paired observer challenges.
  Confidence: high in the scoped composition and source-matched evidence.
  Revisit private object-lookup factoring at Block, not by raising limits
  or strengthening wire bounds. Scope: `notes/table-codec.md`.
- **Compose forwarding through bounded actual-installed routes next.**
  Prove five concrete installation shapes for every IPv4 query and fitting
  route payload, with independent numeric selection. Then compose real table
  application and the first control conditional, leaving checksum pending.
  Confidence: high in semantic boundaries, medium in symbolic loop proof
  engineering; the probe's kernel-limit failure remains documented. Factor
  actual loop equations rather than assume lookup correctness or quietly
  freeze symbolic data. Revisit generic LPM only when a second configuration
  needs it. Plan/review: `notes/forwarder-table-next.md`.
- **Finish Program codecs in dependency-sized baseline-first slices.**
  Parser Target/KeySet/SelectCase/Transition/State precede Action/Block and
  Export/Program. Host entries are a separate pair, not Program members.
  Confidence: high for the five parser laws after the complete probe,
  medium-high for later composition and medium for lasting helper placement.
  Extract private object helpers only at the demonstrated Block reuse seam.
  Preserve permissive defaults and error ordering without semantic validation
  premises. Plan/review: `notes/program-codec-completion.md`.
- **Prove firewall initialization separately from unused-state preservation.**
  The actual nine-root initialization is constructive, while invalid-body
  identity requires only the built index and actual action-first header read.
  Do not narrow the latter theorem to pristine locals or block-only frames.
  Confidence: high after thirteen audited roots, independent full-state tests
  and compiling source/Python faults. A local mutation invisible to generic
  packet/extern DRT is evidence for a stronger Env observer, not a fabricated
  divergent packet bundle. Scope/review: `notes/lean-firewall-proof.md`.
- **Anchor parser wire syntax before advertising its universal laws.**
  Preserve the unchanged production decoder and permissive semantic domains;
  retain 231 exact source-pinned transcripts before proof witnesses change
  the test sources. Independent constructor observations, error precedence
  and actual public-protobuf outputs supplement roundtrip equations.
  Confidence: high in this finite baseline, not a complete Program guarantee.
  Revisit any unobserved field without recapturing old provenance. Scope and
  review: `notes/parser-codec.md`.
- **Advance firewall proof through exact two-write Bloom insertion.**
  Preserve complete runtime state, both full arrays and the first-write
  boundary. Prove one-valued membership preservation, not false numeric
  monotonicity for arbitrary natural cells. Keep noncanonical Lean-only cells
  distinct from representable Python one-bit values. Confidence: high in the
  semantic boundary after independent first-call feasibility review; medium
  in reusable API placement. Start application-specific; revisit extraction
  for readback or a second client. Hash bounds, reverse-flow inputs and actual
  table/SYN composition follow separately. Scope: `notes/firewall-bloom-next.md`.
- **Keep parser wire laws separate from independent wire intent.** Five
  actual roundtrip laws preserve permissive syntax; paired tag/operand
  mutations can preserve those equations while violating independent wire
  answers. Error-order proof-script failure is not a false roundtrip claim.
  Confidence: high after six default audits, constructive witnesses and
  restored source-matched campaigns. Historical replay sources remain pinned;
  later registration-only additions are checked separately, never rewritten
  into old evidence. Scope: `notes/parser-codec.md`, `notes/table-codec.md`.
- **Bound forwarding selection before composing actual application.** The
  independent numeric policy now matches actual installed lookup for five
  shapes, arbitrary IPv4 queries and fitting route payloads. Keep selection
  hit separate from a forwarding default; no-hit does not imply drop.
  Confidence: high in these scoped laws after nine audits and independent
  full configuration tests. A fitting wrong fixture payload can preserve
  the universal law, so independent intended inputs remain essential.
  Revisit generic lookup only for another configuration requiring it.
  Scope and new two-route replay: `notes/forwarder-tables.md`.
- **Clean up only demonstrably owned stalled probe containers.** The p4c
  version probe already has a 600-second client timeout; it does not ensure
  container lifecycle completion. After matching the exact ID, immutable
  image, command, start time, empty mounts and absent processes, removing that
  one ephemeral container released the full gate. Confidence: high in
  ownership and absence, low in the daemon's underlying failure mechanism.
  Add bounded unique-name cleanup and absence verification as a separate
  harness change; do not restart Docker, prune or weaken compiler checks.
- **Keep Bloom expectations independent of runtime variable lookup.** A
  real position-alias fault fooled both expected-value construction and
  execution when the observer used Env.read. Supply intended positions from
  independent profiles and observe full state after each actual call, not
  just the final arrays. Confidence: high after the survivor regression,
  thirteen audited roots and independent campaign review. A repaired later
  write must not hide an earlier unrelated mutation. Retain the original
  four-packet input once even when another fault produces three divergences.
  Scope: `notes/firewall-bloom.md`.
- **Extract codec object facts only at demonstrated Block reuse.** Nine
  unchanged table-private facts now live in an internal CodecObject namespace.
  The actual nine-field Block lookup probe demonstrates reuse without field-
  presence case explosion. Confidence: high in preserved public Table laws
  and unchanged production bytes; medium in lasting helper placement. Revisit
  for Export/Program needs, not speculative abstractions. Historical proof
  hashes stay at their original commits; current helper identities and exact
  moved statements are reviewed separately. Scope: `notes/block-codec.md`.
- **Use a short warm printer probe without weakening cold CI coverage.**
  The reviewed fix uses a 15-second local inspect, 30-second warm version
  probe, prior 600-second cold implicit-pull allowance and unchanged compiler
  budget. Each cleanup command is bounded at 15 seconds. Cleanup uncertainty
  has its own failure class outside optional availability skips. Confidence:
  high in ownership/failure handling, medium in the warm budget; revisit on
  measured slow-host failures. Keep the differently secured XDP helper
  separate until there is a real shared policy. Scope/review:
  `notes/printer-lifecycle.md`.
- **Compose actual forwarding actions before the guarded ingress prefix.**
  The table application law preserves the exact success-only hit write and
  arbitrary pending continuation. Defaults may forward while remaining misses;
  applying to an invalid header uses its stored key, with no invented guard.
  Confidence: high after twelve audits, complete-state tests and actual
  runtime/source faults; medium in the small Effect API pending its next
  ingress client. The 270 cases cycle 24 state profiles, not a 6480-case
  Cartesian sweep. A new no-route request reuses old TTL0 packet bytes but
  differs from all 26 prior requests in full configuration. Scope/review:
  `notes/forwarder-apply.md`.
- **Explicitly select application oracles in dedicated CI.** The new
  five-vector forwarding BMv2 profile was not discovered by existing corpus/
  firewall selectors. Add its exact node with availability preflight and
  independently verify it needs no Lean fixtures. Confidence: high in this
  scoped selector; a general no-skip mechanism remains distinct. Revisit
  discovery when another application adds a separate original-oracle test.
  Scope/review: `notes/reviews/forwarder-apply-ci.md`.
- **Retain pinned XDP inputs during upstream snapshot failure.** At
  `ff47066`, XDP run `35949452182` and its single retry fail before compilation
  with Ubuntu snapshot HTTP 503 responses. The preceding `425fbc9` XDP job
  passes. Confidence: high in the observed external download failure, not
  its duration or upstream cause. Keep all pins, TLS and required checks;
  do not count the failed run as assurance or immediately loop retries.
  Recheck on the next normal checkpoint run before considering a separately
  reviewed availability fix.
- **Finish a bounded assurance milestone, not universal Python correctness.**
  The user accepted `milestone-1.md`: freeze the current IR/profile, close
  whole-program interchange coverage, consolidate independent/adversarial
  evidence and usable clean-checkout acceptance, then stop. This supersedes
  automatic continuation of every application, validator or codec proof in
  the broader roadmap. Confidence: high that it matches the intended useful
  deliverable; no numerical confidence-of-correctness claim. Already-reviewed
  Action/Block work remains closeout; further readback/ingress proofs are
  parked with WIP retained. Simple Export/Program composition is optional,
  never an excuse to reopen the milestone. Revisit scope only for a concrete
  acceptance gap or a new user-approved milestone; this is not a wire-version
  migration and does not disable existing XDP CI.
- **Close reviewed Block laws without extending the proof ladder.** Integrate
  the existing Action/Block laws with independent wire/error observations;
  roundtrip-preserving enum faults and paired observers justify retaining both
  evidence kinds. Confidence: high within the stated representability profile,
  not whole-program validity. Historical Table/Parser replay hashes remain
  fixed; newer public/audit registrations are checked at their own reviewed
  checkpoint. Export/Program and host-entry testing are the finite next task,
  not an automatic requirement for every additional theorem.
- **State the tested canonical wire domain instead of promising arbitrary
  ProtoJSON parity.** The current Python parser rejects unknown fields while
  Lean ignores them; enum numbers and camelCase aliases also differ. Confirmed
  all three differences directly against the public protobuf parser and real
  codec endpoint. Keep current semantics, document these noncanonical forms
  outside interchange parity, and test top-level boundaries independently.
  Confidence: high in the observed scope; this is not safe version negotiation
  or untrusted-input hardening. Revisit only when a real producer needs another
  accepted form. The reviewed profile also removes stale totality/termination
  implications and maps evidence without numerical correctness claims.
- **Make the adversarial acceptance finite and reconstructible.** Reuse ten
  reviewed Python/observer regressions and three pinned complete inputs, then
  compile actual Lean CRC and paired codec/observer faults in a fresh source
  copy. Require the precise semantic disagreements, independent native
  detections, byte restoration and saved-input replays. Confidence: high in
  this bounded sensitivity evidence, not exhaustive fault coverage. A shared
  wrong observer that survives equality is explicitly demonstrated, then
  rejected by independent literal anchors. Revisit the catalogue for a changed
  input/API or a concrete survivor, not to extend this milestone indefinitely.
  The command and evidence boundaries are in `notes/milestone-adversarial.md`.
- **Observe rejected-host configuration without numeric type coercion.**
  Independent review reproduced two survivors: hex serialization hid a
  counter's integer-to-Boolean mutation, and ordinary dataclass equality hid
  a metadata Boolean-to-integer mutation. Keep serialized protocol answers,
  but also freeze the raw externs, index, metadata, roles and installed state
  with explicit type identity. Confidence: high for the finite rejected-host
  fixtures after retained negative regressions and actual source faults;
  this is not global validator equivalence or rollback after execution errors.
  Revisit when the observed configuration gains new state. Evidence and
  independent review: `notes/milestone-interchange.md`.
- **Whitelist the exact BMv2 discrepancy, not every failure on its node.**
  The old broad strict xfail accepted a simulated oracle error. Require a
  dedicated exception only for the exact vector, semantic-failure status and
  two known packet mismatches. Actual pytest regressions make errors and
  changed mismatches fail, and corrected output strict-XPASS. Confidence:
  high after independent tests and immutable-image replay. Revisit on a
  deliberate vector/oracle pin change; never broaden the classifier merely
  to obtain green CI. Evidence: `notes/milestone-oracle-classification.md`.
- **Present p4blo with a static research-project website.** At the user's
  request, study Veil's live site and adapt its introduction, capabilities,
  real-code and next-action structure into an original p4blo design. Use
  dependency-free HTML/CSS/JavaScript in `website/`, with real source excerpts
  and explicit evidence boundaries; existing GitHub documents remain the
  documentation destination. Confidence: high in this small, reversible
  delivery; visual direction remains open to user feedback. Revisit the
  static approach if the project needs a full documentation renderer or
  actual browser execution. The user then explicitly requested GitHub Pages
  publication: deploy only this directory via pinned official actions on
  `main`, with deployment permissions scoped to one job and no custom domain.
  This presentation work does not reopen assurance milestone 1.

## 2026-09-24

- **Archive obsolete worktree contents before removing their build caches.**
  The user requested local cleanup. Keep main, the two documented parked
  proof drafts and three trees with unique history/review content; remove
  86 merged-history checkouts after archiving tracked edits, untracked files
  and non-cache ignored evidence. Preserve every branch and the one commit
  found only in a worktree HEAD reflog. Confidence: high after independent
  archive/hash/index/reflog review and filesystem/count checks. Revisit the
  remaining trees only after separate content review or a new proof scope;
  historical worktree paths do not imply active work. Details and recovery:
  `notes/worktree-cleanup.md`.
