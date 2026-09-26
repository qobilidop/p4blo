# p4blo design

P4's semantic core as an IR, architecture-free, with an independent
Lean semantics validated against a runnable reference.

That sentence is the project. p4blo is a personal, educational prototype
whose purpose is to make the sentence concrete enough to argue about, so
that a serious version can later be proposed to the P4 community as an
RFC rather than built alone. This document records what p4blo is, what
it claims, how it is built and what is out of scope. The closed behaviors
are in [ir-semantics.md](ir-semantics.md), what the supplied architectures
and extern families decide in [arch-supports.md](arch-supports.md), the
construct table in
[p4-spec-coverage.md](p4-spec-coverage.md), and what is proved, tested and checked
against which oracle in [assurance.md](assurance.md).

## Context and motivation

P4 today has no architecture-free semantic core with a serialized form.
The language specification describes P4 together with the architecture
model it runs under, and every executable semantics either hardcodes one
architecture or reproduces the whole language. Compilers have their own
IRs, but those are compiler IRs, not an interchange format anyone else
can consume.

The proposal p4blo makes is one paragraph and has no ask. P4 should have
a specified, architecture-free semantic core with a serialized form. The
P4 language is one frontend of that core among several. Architectures
and externs are specified outside it as contracts. An RFC to standardize
such an IR comes after this project, not inside it. It must read as the
serialized form of the elaborated core that P4-SpecTec already defines,
with the architecture taken out, never as a third IR beside SpecTec and
p4mlir.

The primary reader is the P4 language community: spec, compiler and
architecture people. "Educational" describes the artifacts, each small
enough to read in a sitting, not a separate audience. P4 users who want
to learn what a program means by reading an interpreter, and
formal-methods people who want a Lean foothold for P4, are served for
free.

## Goals and non-goals

Goals:

- Define a small, post-elaboration IR for P4's semantic core, with a
  Lean definition of its syntax and meaning, a protobuf encoding, a
  validator and a readable text form.
- Give it two independent executable semantics, in Lean and Python,
  checked against P4-SpecTec and each other.
- Show that a P4 block is a function and that an architecture is
  ordinary code outside the IR, by testing independent blocks and their
  explicit composition under one scoped v1model architecture.
- Validate the whole against external oracles on real programs.
- Publish a coverage table that walks P4's core construct by construct
  and says for each one whether it is in, elaborated away, or excluded.
- Let people author programs in typed Python and run useful examples.
- Restrict formal verification to the architecture-free core IR. Test the
  architecture adapters, concrete externs and applications as executable code.

Non-goals: performance of any component; a P4 parser or typechecker of
p4blo's own (P4 source enters through P4-SpecTec's typing and
instantiation and the IL bridge, checked on the corpus, not verified); P4Runtime,
hardware targets or a p4c backend, which is the first thing a community
version would build with 4ward's route as precedent; replacing any
existing tool; a browser playground; universal correctness of the Python
implementation, which is tested against Lean, not proved; a Lean authoring
language, architecture-specific proofs, application proofs or execution
certificates.

## The four claims

Each claim has one experiment and one way to fail. The project makes
these claims and no others; their current status is in
[assurance.md](assurance.md).

1. **The core is small and post-elaboration.** The schema and its
   contract fit in a few pages: no generics, no `int`, no implicit casts,
   no tuples; every width resolved; references by name. Fails if a
   corpus program needs an escape hatch.
2. **The core is semantically complete for real programs.** Programs
   authored in the Python eDSL, printed to P4 text and run through
   external oracles under the supported v1model profile, match the reference interpreter
   packet for packet. Fails on any divergence not traceable to a
   documented closed behavior or a documented oracle defect.
3. **A block is a function; an architecture is ordinary code.** Core
   blocks compile and execute independently, and a separate v1model adapter
   chooses six pipeline stages, metadata and packet fate. Fails if core
   validity or execution requires a particular pipeline or architecture role.
4. **The semantics is mechanized and agrees with the reference.** A
   proof-visible Lean interpreter over the IR, differential testing
   against the Python interpreter with every divergence attributed to a
   bug on one side, and scoped proofs about the Lean definitions. Fails
   if a divergence cannot be attributed.

## Architecture

### One IR, three representations

There is one p4blo IR with three representations, and each concern has
one intended authority:

| Concern | Intended authority | Today |
|---|---|---|
| Abstract syntax: expressions, statements, declarations | Lean, `spec/ir/P4bloIR/IR.lean` | in place |
| Validity: types, scopes, widths, legal combinations | Lean, `spec/ir/P4bloIR/Validity/` | a core-library checker proved sound for the declarative rules, agreeing with the Python validator on tested libraries, with progress proved for valid libraries; architecture bindings are checked separately; checker completeness and termination are open |
| Meaning: execution and observable behavior | Lean, `spec/ir/P4bloIR/` | in place |
| Serialization: messages, field numbers, encoding versions | the core and architecture protobuf schemas under `spec/ir/proto/` and `spec/arch/proto/` | in place |
| Correspondence between wire values and abstract libraries | codecs specified in Lean | roundtrip laws proved through Action and Block on the representable domain; BlockLibrary and architecture-binding composition are open |

The text form of the protobuf is the golden format; binary and JSON are
transports. These are distinct contracts, and passing one does not
establish the next:

```text
Serialized data
    | parse: supported, well-formed encoding?
Wire representation
    | decode: which abstract library?
Abstract library
    | validate: is that library legal?
Valid library
    | execute: what does it do?
Observable behavior
```

Parsing a protobuf message does not establish validity: variants may be
unset, widths illegal, references unresolved. Raw abstract syntax stays
ordinary, with validity a separate predicate and an executable validator,
so that raw syntax remains useful for diagnostics, malformed-input
testing and cross-language correspondence. Core library validity is
defined in Lean over the index and decided by an executable checker proved
sound; architecture H/M roots and exports have a separate tested binding
checker without a formal soundness claim. A valid library's well-formed machine never reaches an interpreter
error: every finite run ends in success or a declared parser error under
the documented extern, installation and entry premises.
Checker completeness, termination and the complete codec proofs are the
obligations that remain, as assurance.md records.

### The IR is post-elaboration

The IR is P4 after the frontend has done its work: monomorphic blocks,
resolved widths, explicit casts, desugared control flow, resolved names.
That is the gain of being free of frontend sugar, and it is what keeps
the Lean semantics free of type inference. Every frontend, including the Python eDSL and P4 importer, owes the IR
the same elaboration.

Declarations are referenced by name, scoped as P4 scopes them, and never
looked up dynamically: the validator resolves every reference once. This
follows ONNX and 4ward rather than BMv2's integer ids, so that the text
format reads like the program it encodes and a schema change shows up as
a readable diff. Expressions carry no type annotations: every leaf has a
known type, every operator's result is determined by its operands, and
run-time values carry their width, so no interpreter infers anything and
the goldens stay half the size.

The core schema is package `p4blo.v0`; architecture assembly uses
`p4blo.arch.v0`. `v1` is reserved for the RFC-shaped form. `buf` lints
both schemas and generates the Python bindings, committed under
`impl/python/p4blo/v0/` and `impl/python/p4blo/arch/v0/` so the proto
package paths and Python import paths coincide. Contributors without
`buf` have a working package; CI regenerates them and fails on any diff.

### Blocks and the P4NAH rule

Core blocks declare their own typed parameters. The P4NAH rule separates
block computation from architecture actions: packet fate is returned as
data for the caller to interpret. The supplied H/M entry helpers use this
calling convention:

```
parse   : Packet × M → H × M × bits consumed × accepted × error
control : H × M × TableEntries → H × M
deparse : H → Packet
```

In this convention, rejection is an outcome, not an exception: the
caller gets the partial headers, whether the parser accepted, and the
error, and decides what to do. A control writes fields of `M`; whoever
called it acts on them afterwards. Packet fate is data interpreted by the
architecture; it is not a core operation. Tables are inputs installed by the host. A block may call
another block; that is P4's own composition and it is in.

There is one `Block` message with a kind tag, parse, control or deparse,
and an explicit parameter list. The three kinds differ in which statements
they may contain, and the validator enforces those rules per kind.

A parser may loop, since a state may be revisited while extracting into
a header stack. The bound is the no-consumption revisit rule: a state
that consumed no bits since it was last entered may not be entered
again, and doing so is a parse error. Fuel was rejected because it makes
the meaning of a program depend on a number nobody specifies.

### Metadata contract

The v1model adapter selects one H and one M root; the core library does not.
Its reserved optional fields are `ingress_port: bit<9>`, `parser_error: error`,
`egress_spec: bit<9>` and `egress_port: bit<9>`. `egress_spec` is writable only
in ingress/egress; the other fields are supplied read-only values. Reads are
restricted to stages where native interfaces supply them. The profile checker
also follows aliases through nested calls and actions. Other ordinary metadata
remains private program data. Exact availability and rejection rules are in
[architecture support](arch-supports.md#the-metadata-contract).

### Externs

Register, counter, hash and checksum are not core P4; they are v1model,
PSA and PNA externs. At the IR level an extern is exactly a declared type
with method signatures, an instance with constructor arguments, and call
sites. The reference interpreter binds each instance to a registered
Python callable at load, checks arity, directions and widths, and refuses
to load on any mismatch. Every extern a corpus program uses ships twice,
a Python implementation and a Lean model, pinned to each other by
vectors and by independent known answers; that pair is corpus material,
not spec material. The supplied families are register, counter,
checksum16 and the byte-aligned CRC16 and CRC32 services, specified in
[arch-supports.md](arch-supports.md#extern-families).

### Architectures

The sole supplied packet architecture is scoped v1model: parser,
verify-checksum, ingress, egress, compute-checksum and deparser. Omitted
optional stages are empty. The ordinary Python adapter and its independent
Lean implementation decide metadata initialization, stage sequencing, packet
fate and payload handling; they carry no architecture-specific proof claim.

Ingress chooses an output destination or drops. Egress observes the selected
`egress_port`; resetting/writing `egress_spec` affects its drop request, not
the saved destination. A drop skips downstream stages and their effects.
Parser rejection still reaches ingress with `parser_error`; unconsumed bytes
remain payload. The model is serial across packets. The exact target profile,
BMv2 backend limitations and unchanged-source oracle discrepancies are in
[architecture support](arch-supports.md) and
[oracle discrepancies](oracle-discrepancies.md).

### Python eDSL

`p4blo.edsl` is typed by construction: every reference is a Python
object that pyright resolves, and widths are types. Headers and structs
are classes whose annotated fields are real attributes (`ttl: bit8`), so
a misspelled field is an unknown attribute; parsers, controls and
deparsers are classes whose states and actions are methods, so a `select`
target is `self.parse_ipv4` and a table's action list holds the methods
themselves; block classes can be compiled independently or collected in a
`BlockLibrary` with their shared declarations. Its compiled core protobuf
value can be validated with any number of blocks of each kind, with no
pipeline roles or global H/M roots. An architecture binds its selected blocks
in a separate `BlockAssembly` envelope or with explicit `BlockBindings`.
The [authoring guide](python-edsl.md) explains
this boundary. Widths are `Literal` type parameters, `Bits[L[8]]`, spelled
through the aliases `bit1`..`bit64`; `Var[W]` is a place of that width
and `Bits[W]` any value, so assigning to an expression is a static error.
`concat`, slices and `lookahead` have widths the type system cannot
compute and return `Bits[int]`, a hole no typed place accepts until
`x.as_(bit16)` asserts the width at run time and narrows it for the
checker. Operator overloading builds expressions and control flow stays
explicit (`with self.if_(...)`, `mux`), in the manner of JAX's
`lax.cond`; no decorator reads Python source, because the IR is the
product and the eDSL should teach it by use, not hide it. A state or
action body is called once with a recording `self`, and an expression has
no truth value: `if x == y:` raises and names the cause.

The typed surface is a front over `p4blo.edsl.core`, the builder that
produces the goldens; its plain constructors and string names are the
documented dynamic API for generated programs. The core's run-time checks
stay authoritative, and pyright is an earlier line, not a replacement.
`impl/python/tests/edsl/test_typing.py` tests the split with must-pass and must-fail
fixtures:

| Checked by pyright | Checked at run time only |
|---|---|
| names of fields, states, actions, tables and blocks | that an `int` literal fits its width |
| equal widths in arithmetic, comparison and assignment | widths of extern `in` arguments (`Val[T]`) |
| assignment to a non-place (a `Bits` where a `Var` is wanted) | arguments of a sub-block call against its parameters |
| cast target widths | select key sets against the key type |
| a `concat`, slice or `lookahead` used without `as_` | a literal used as a place |
| action argument names, count and widths, in calls, defaults and entries | whether a `Bool`, `Enum` or `Error` value is a place |
| extern method names and argument count; an `Out`/`InOut` argument being a place of the declared width | every rule the validator owns |

Four places deviate from the original design because the type checker
forced them: the width aliases and typed literals type as places, so a
literal used as a target is caught only at run time; `Bool`, `Enum` and
`Error` targets have no static place split; extern `in` parameters accept
any value with the width checked at run time; and a failed `assign`
surfaces as `reportCallIssue` because `assign` is overloaded over target
kinds.

The [Python authoring guide](python-edsl.md) explains independent blocks,
block libraries, readability patterns from the three applications, and the explicit extern
declaration, registration and binding lifecycle. Concrete extern families
live in architecture support, outside the generic eDSL.

### The Lean packages

Two Lake packages have a one-way dependency. `spec/ir/`, package `p4blo-ir`
imported as `P4bloIR`, owns abstract syntax, validity, executable semantics,
JSON codecs and scoped proofs with axiom audits. Nothing architectural lives
here: no ports, packet fate or concrete extern families. An extern's logical
state is data; its call model is supplied by the caller. Core progress assumes
that model satisfies `ExternContract`, installed entries satisfy `InstalledOk`
and the initial machine meets the theorem's typed-entry premises. These are
assumptions, not guarantees about the supplied architecture.

`spec/arch/`, package `p4blo-arch` imported as `P4bloArch`, depends on the IR
and supplies executable bindings, v1model, five extern families and the
`p4blo-lean` endpoint used by differential tests. It compiles and runs tests,
but carries no formal architecture-specific guarantee. Python is the program
authoring interface; there is no separate Lean authoring package.

| Boundary | Assurance |
|---|---|
| Core validity and execution | Scoped Lean theorems under their explicit premises |
| protobuf to and from abstract IR | Component codec laws on the representable domain plus cross-language tests; complete-library composition remains open |
| Architecture and extern execution | Native tests, Python/Lean comparison and applicable external oracles |
| Python execution to IR semantics | Differential and property tests, independent answers and deliberate faults |
| Authored program to intended behavior | Independent packet/state expectations, regressions and applicable oracle comparisons |

Each package puts client modules under `<Root>/` and gate-only modules under
`<Root>Test/`. Its root contains Lake's files, the root module, README and at
most one `Main.lean`, with wire schemas under `proto/`. The default test
libraries are `P4bloIRTest` and `P4bloArchTest`; `lake build` checks the core
audits and `lake test` runs each driver. `spec/arch/Main.lean` is the only
application endpoint. `tests/repository/test_package_layout.py` pins the layout.

Application tests check intent separately from core properties. External
oracles and known answers stay because a theorem can establish the wrong
specification; none upgrades Python's tested conformance into equivalence.

### Printer and oracles

The architecture-free printer emits core declarations and blocks. The
v1model printer binds six native stage interfaces, mirrors supported standard
metadata and prints extern families in their target form. Empty optional
stages remain explicit. A separate block printer selects parser/control/
deparser for P4-SpecTec's one-block-per-request adapter; it never merges the
v1model controls into one semantic block.

P4-SpecTec supplies independently implemented P4 evaluation rules. BMv2's
`simple_switch`, compiled by pinned p4c, supplies a second packet oracle.
Portable source and packet witnesses run on both, while runtime-only stage
operations that BMv2 cannot compile are tested without claiming that external
coverage. The source frontend preserves each V1Switch stage and refuses
unsupported native metadata/functions. It remains a tested translation, not a
verified compiler; imported blocks are validated and compared using original
source vectors and printer roundtrips.

The original-source probes are kept separate from printer binding: for example,
the explicit egress metadata reset used by our printer must not conceal the
pinned simulators' different native initialization. Every discrepancy records
its authority, chosen behavior and exact evidence in
[oracle discrepancies](oracle-discrepancies.md). Where a contract permits
multiple answers, the document states p4blo's policy rather than declaring an
oracle incorrect. The P4-SpecTec STF adapter supplies LPM prefix priorities;
BMv2 independently judges longest prefix and target table behavior.

### Differential testing and proofs

The Python interpreter is compared with the Lean interpreter through a
pipe to the `p4blo-lean` binary: corpus programs and generated programs
times random packets and table entries, with the complete logical extern
state observed after every request, every divergence attributed to a bug
on one side, and every failure saved as a replayable bundle. Statement
execution in Lean is an explicit continuation machine driven by a
proof-visible fixpoint, so finite traces support proofs about the actual
interpreter rather than a model of it. Deliberate faults in both
implementations, in observers and in codecs check that the tests would
notice. Formal proofs cover only the architecture-free core. Exactly which
properties are proved, and what
each does not establish, is the subject of assurance.md.

### Coverage table

Every construct of P4's core appears in [p4-spec-coverage.md](p4-spec-coverage.md) with
one of three statuses: in; elaborated away, with the elaboration named;
or excluded, with a reason. The checklist is P4-SpecTec's elaborated IL,
walked construct by construct, because it is exactly P4 core after sugar.
The subset is a checklist, not a horizon: the schema is designed for the
full core and never bakes an exclusion into its shape.

## Scope

Three exclusion categories; only the third makes p4blo a subset.

- **Out by thesis:** anything architecture-dependent: intrinsic metadata,
  packet fate as externs, action selectors and profiles, direct counters
  and meters, clone and recirculate as operations.
- **Out by elaboration:** generics, `int`, implicit casts, tuples,
  `switch` on action runs, and other sugar the frontend removes.
- **Out by scope, each threatening no claim:** `int<N>`, varbit, header
  unions, value sets, `exit`, `return`, `for`, extern function objects.
  Each is an additive change to the schema if it is ever wanted.

In: `bit<N>`, `bool`, enums and errors, headers, structs, header stacks
with push, pop and index arithmetic; parser states with extract,
lookahead, advance, verify, select with masks and ranges; sub-parser and
sub-control instantiation; actions with data; tables with exact, lpm and
ternary keys, priorities, default actions, const entries; `if`,
assignment, slices, concatenation, explicit casts, wrapping arithmetic;
emit; declared externs.

### Corpus and applications

Corpus programs live under `tests/programs/corpus/`, chosen to hit the hard
semantics. Where a program can be sourced from p4c's own test suite with
an STF file beside it, it is, because those expected outputs were
produced by BMv2 and reviewed by the p4c maintainers, which gives
oracle-grade vectors before any oracle runs here. The tutorial forwarder
and firewall are pinned from p4lang's tutorials and carry hand-derived
and independently computed vectors. Each program is authored in the eDSL,
printed back to P4, typechecked by p4c, and replayed on both interpreters
and both oracles. The public applications under `examples/` are complete
Python programs with runnable demos, written for readers who know
networking; their verification assets live under `tests/programs/examples/`.

## Testing strategy

Six layers, each answering a different question.

1. **Unit and property tests on the primitives.** Wrapping arithmetic,
   casts, slices, concatenation, extract and emit, select matching with
   masks and ranges; hand-computed cases plus Hypothesis properties.
2. **Validator tests.** One tiny malformed program per rule, each
   expecting a specific error: the executable form of what a schema
   cannot express.
3. **Corpus goldens.** Each program's IR text and printed P4 are
   committed; the eDSL regenerates them and the test diffs, so a schema
   change is reviewed like code.
4. **Vectors in STF.** The Simple Test Framework format that p4c and
   P4-SpecTec already use: `add` lines install entries, `packet` lines
   give a port and bytes, `expect` lines give the output. One file per
   scenario replays on the Python interpreter, on Lean, and on both
   oracles.
5. **Differential and generated testing** against Lean, with complete
   extern state, shrinking and retained replays.
6. **Proofs and deliberate faults.** Scoped theorems with audited axioms,
   and mutation campaigns that check the tests would notice a wrong
   implementation.

The test suites under `tests/` are grouped by the question they answer,
each directory with a README in these terms: `unit/` holds layers 1 and
2, `codec/` applies layer 1 to the wire encoding, `programs/` holds
layers 3 and 4 for the corpus and the applications, `drt/` holds layer
5 and the fault side of layer 6, `lean/` compares the Lean semantics with
Python and with independent answers, and `external/` replays on the two
oracles. `structure/` sits beside the layers: it checks no semantics, but
pins the layout, the links and the ledger that make the evidence
findable.

Every external input, from the oracle commits to the Docker image
digests and the GitHub Actions, is pinned and listed in
[workflows.md](workflows.md), so anyone can reproduce the checks.

## Repository layout

```
p4blo/
  README.md, AGENTS.md              the front door; the agents' entry point
  docs/                             design, ir-semantics (with its generated
                                    ledger-xref), arch-supports, coverage,
                                    assurance, quickstart, workflows
  .agents/                          agent working state: status, decisions, roadmap
  spec/ir/                          Lake package p4blo-ir (P4bloIR): the IR
    P4bloIR/                        abstract IR, semantics, codecs, proofs
    P4bloIRTest/                    tests, proof audits, fixtures
    proto/p4blo/v0/p4blo.proto      versioned wire encoding
  spec/arch/                        Lake package p4blo-arch (P4bloArch): the
    P4bloArch/                      executable v1model, bindings, extern families
    P4bloArchTest/                  tests and fixtures
    proto/p4blo/arch/v0/assembly.proto  architecture binding wire encoding
    Main.lean                       the p4blo-lean conformance endpoint
  impl/python/p4blo/                     the Python package
    v0/                             generated core protobuf code, committed
    ir.py                           load, save, text form
    validator/                      validation, one module per rule group, and
                                    the one expression typer (validator/typer.py)
    interp/                         the reference interpreter
    printer/                        IR to P4-16 text, with no architecture
    edsl/                           the typed eDSL; core/ is the builder beneath it
    arch/                           bindings, contract, v1model, extern families
                                    and block-runner printing
      v0/                           generated architecture protobuf code
    drt/                            the differential loop
  examples/<application>/           public Python programs, demos, READMEs
  tests/                            everything that runs
    unit/, codec/, programs/,       the suites, one directory per question
    drt/, lean/, external/,         of the testing strategy above
    structure/
    corpus/<program>/               source, golden, README, STF vectors
    examples/<application>/         application goldens, vectors, tests
    oracle/                         P4-SpecTec and BMv2 drivers, original programs
    pyright/                        the eDSL's static-check fixtures
  scripts/, .github/workflows/      the gates, four validation workflows and website publishing
```

One Python project is rooted at the repository root so that `uv run
pytest` works from there. Python dependencies are locked by `uv`; Lean has
matching `lean-toolchain` pins in `spec/ir/` and `spec/arch/` selected through
`elan`; schema checks, oracles and other specialist gates have their own
pinned tools. The README's development section is the single entry point
for setup.

## Alternatives considered

- **Protobuf as the abstract syntax authority**, the original
  arrangement, with Lean only for meaning. Replaced by one IR defined in
  Lean with a protobuf encoding, so that validity and meaning are stated
  over the same syntax the proofs use and the encoding can change without
  touching the semantics.
- **Three block messages instead of one with a kind tag.** Rejected; it
  triples the shared machinery for locals, parameters and calls.
- **Fuel as the parser loop bound.** Rejected; it makes meaning depend on
  an unspecified number.
- **BMv2 as the first oracle.** Replaced by P4-SpecTec, which needs no
  Docker and is the spec's own mechanization; BMv2 stays as the second,
  for what SpecTec cannot judge.
- **pcap as the vector format.** Rejected in favor of STF, which is text
  and already understood by both oracles.
- **A decorator-based eDSL that reads Python source.** Rejected because
  it hides the IR, and the IR is the product.
- **The string-referenced eDSL.** Table action lists, state targets and
  exports named things by string, so a typo surfaced at build time at
  best. Replaced by the typed surface; the builder stays as
  `p4blo.edsl.core`.
- **An FFI between Python and Lean.** Rejected; a pipe is enough, and an
  FFI would be a throughput choice, not an additional guarantee.
- **A browser playground.** Removed to keep the project to its four
  claims; pure Python and Python 3.13 are kept so that it stays cheap.

## Relation to p4-spectec-lean

`p4-spectec-lean` is a separate project that compiles P4-SpecTec's
elaborated specification into Lean and verifies that compiler. p4blo
builds no rendering or interpreter of SpecTec's rules; the mechanized
relation between the two semantics is a joint milestone whose first
acceptance is that the executable rendering answers every conformance
fixture and block-level request below exactly as SpecTec's own
simulator does, and whose theorem relates the rendered block contract
to `P4bloIR.Exec` under the bridge's elaboration. p4blo owns what that
project consumes, each with a stable, documented format:

| Interface | Where | Format |
|---|---|---|
| the block contract in SpecTec's language | `tests/oracles/p4blo.watsup` | watsup at the pinned P4-SpecTec commit |
| the program-IL export | `tests/oracles/patches/0002-il-export.patch`, documented in `tests/oracles/README.md` | `p4spectec-il-export/1` JSON: variants as `{"t","c","a"}`, records as `{"t","s"}` |
| the conformance corpus | `tests/conformance/` and its README | `p4blo.conformance` version 2: program, requests, Lean's replies with state and rule tags |
| block-level requests and replies | `tests/oracles/block.py`, documented in the oracle README | JSON lines per block, value shapes as the README defines them |
| the rule inventory at the pin | `tests/oracles/spectec-rules.json` | one item per declaration: kind and name |

A change to any of these formats bumps its version. The two simulator
patches are candidates to move to that project, which forks SpecTec
anyway. Two alignments are pending on that project's side: the two repositories pin different
P4-SpecTec commits, and p4blo bumps to the other's pin once it is fixed;
and that project's program export, upstream's own JSON of the booted
program, replaces patch `0002` when it exists, after which the bridge
reads the same bytes both projects use.

## Neighbors

- [P4-SpecTec](https://github.com/kaist-plrg/p4-spectec): the P4 spec's
  own executable mechanization. Its elaborated IL is the coverage
  checklist and its simulator the first oracle. p4blo does not
  re-mechanize P4; it serializes the elaborated core and takes the
  architecture out.
- [Nano-P4](https://github.com/pacokwon/nano-p4-spec): an educational P4
  dialect with typing rules, dynamic semantics and one hardcoded
  architecture, in SpecTec. The same size of language with the opposite
  decision about the architecture; the foil for claim 3.
- [4ward](https://github.com/4ward-p4/4ward): a p4c backend into a
  protobuf behavioral IR into a Kotlin simulator, no semantics; the proof
  that a protobuf P4 IR is workable and the precedent for a p4c bridge.
- [p4mlir-incubator](https://github.com/p4lang/p4mlir-incubator): a
  compiler IR for a future p4c, not an interchange format.
- [HOL4P4](https://github.com/kth-step/HOL4P4): mechanized semantics with
  an executable derived inside the prover; no serialized IR.
- [cedar-spec](https://github.com/cedar-policy/cedar-spec), inspected at
  `acb0db7d`: the method. A Lean model as the specification, a production implementation,
  differential random testing with typed generators, and retained
  regressions. p4blo adopts that and keeps the two models independently
  implemented: sharing semantic algorithms would weaken the comparison.
- [µP4](https://github.com/cornell-netlab/MicroP4): composed programs
  inside the language; p4blo takes the architecture out of it.
- [BMv2](https://github.com/p4lang/behavioral-model) and
  [p4c](https://github.com/p4lang/p4c): the second oracle, and the source
  of corpus programs and their STF vectors.
- [ONNX](https://github.com/onnx/onnx): the precedent for a readable
  protobuf IR: references by name, a checker that owns what the schema
  cannot say. Its generic node with a string operator type is not
  followed, because P4's core has a fixed handful of operators and the
  typed schema is the grammar the Lean side decodes.

The construct-by-construct survey of these IRs that shaped the schema is
archived in git as `docs/notes/prior-art-ir.md` at commit
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6`.

## Appendix: naming

*p4blo*: `p4` plus `blo`, block cut short, read aloud as *Pablo*. Pablo
descends from Latin *Paulus*, "small", so the name says small blocks in
two languages. Name-shaped rather than claim-shaped, so the tagline
carries the claim. Considered and rejected: `p4sem` and `p4ir` name the
method, and `p4ir` is one letter from P4HIR; `p4blocks` is claim-shaped
and invites the µP4 reading; `p4nah` reads as dismissive of P4 the moment
it heads a community proposal; the small lane (`p4mini`, `p4nano`) is
Nano-P4's; `p4core` reads as core.p4.
