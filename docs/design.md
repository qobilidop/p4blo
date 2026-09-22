# p4blo design

P4's semantic core as an IR, architecture-free, with an independent
Lean semantics validated against a runnable reference.

| | |
|---|---|
| Status | Draft |
| Date | 2026-09-22 |
| Authors | Bili Dong, with Claude Fable 5.1 |

That first sentence is the project. p4blo is a personal, educational
prototype whose purpose is to make the sentence concrete enough to
argue about, so that a serious version can later be proposed to the P4
community as an RFC rather than built alone. This document records
what p4blo is, what it claims, how the claims are tested, and what has
been decided. Progress lives in [status.md](status.md), dated choices
with their reasons in [decisions.md](decisions.md), the closed
behaviors in [semantics.md](semantics.md), and the construct table in
[coverage.md](coverage.md).

## Context and motivation

P4 today has no architecture-free semantic core with a serialized
form. The language specification describes P4 together with the
architecture model it runs under, and every executable semantics
either hardcodes one architecture or reproduces the whole language.
Compilers have their own IRs, but those are compiler IRs, not an
interchange format anyone else can consume.

The proposal p4blo makes is one paragraph and has no ask. P4 should
have a specified, architecture-free semantic core with a serialized
form. The P4 language is one frontend of that core among several.
Architectures and externs are specified outside it as contracts. An
RFC to standardize such an IR comes after this project, not inside
it. It must read as the serialized form of the elaborated core that
P4-SpecTec already defines, with the architecture taken out, never as
a third IR beside SpecTec and p4mlir.

p4blo supersedes the P4NAH demo design (2026-09-19) and the p4lean
design before it. P4NAH survives as the name of one rule inside p4blo.
Pakeles is a sibling, not a part: it is a parser IR designed from
first principles, where p4blo's parser fragment is P4's own parser
semantics, faithfully.

### Audience

The primary reader is the P4 language community: spec, compiler and
architecture people. "Educational" describes the artifacts, each small
enough to read in a sitting, not a separate audience. P4 users who
want to learn what a program means by reading an interpreter, and
formal-methods people who want a Lean foothold for P4, are served for
free.

## Goals and non-goals

### Goals

- Define a small, post-elaboration IR for P4's semantic core with a
  protobuf schema, a validator, and a readable text form.
- Give it two independent semantics, a Lean interpreter that is
  normative and a Python interpreter that is the runnable reference,
  and show that they agree.
- Show that a P4 block is a function and that an architecture is
  ordinary code outside the IR, by running one corpus under two
  architectures unchanged.
- Validate the whole against an external oracle on real programs.
- Publish a coverage table that walks P4's core construct by construct
  and says for each one whether it is in, elaborated away, or excluded.

### Non-goals

- Performance of any component.
- Running existing P4 source. There is no P4 text parser; the printer
  goes the other way.
- P4Runtime, hardware targets, or a p4c backend. The p4c backend is
  named in the README as the first thing a community version would
  build, with 4ward's route as precedent.
- Replacing any existing tool.
- A browser playground. It was part of an earlier plan and remains a
  future item, but it is not a deliverable of this project. The
  constraints that would make it cheap later are kept anyway; see
  [Pure Python](#pure-python-always).

## The four claims

Each claim has one experiment and one way to fail. The project makes
these claims and no others.

1. **The core is small and post-elaboration.** The proto schema and
   its contract fit in a few pages. No generics, no `int`, no
   implicit casts, no tuples; every width resolved; names as ids.
   Fails if a corpus program needs an escape hatch.
2. **The core is semantically complete for real programs.** Four
   programs, authored in the Python eDSL, printed to P4 text and run
   through an external oracle under a v1model shim, match the
   reference interpreter packet for packet. Fails on any divergence
   not traceable to a documented closed behavior.
3. **A block is a function; an architecture is ordinary code.** Two
   architectures, a filter and a switch, each around fifty lines of
   Python with no P4 in them; every corpus program runs under both
   unchanged. Fails if the line counts say otherwise or a block needs
   a hook one architecture lacks.
4. **The semantics is mechanized and agrees with the reference.** A
   Lean interpreter over the IR, differential random testing against
   the Python interpreter with zero unexplained divergences, and one
   theorem. Fails if a divergence cannot be attributed to a bug in
   one side.

## Design

### The IR is post-elaboration

The IR is P4 after the frontend has done its work: monomorphic blocks,
resolved widths, explicit casts, desugared control flow, interned
names. That is the gain of being free of frontend sugar, and it is
what keeps the Lean semantics free of type inference. Every frontend,
Python now, others later, owes the IR the same elaboration.

Declarations are referenced by name, scoped as P4 scopes them, and
never looked up dynamically: the validator resolves every reference
once. This follows ONNX and 4ward rather than BMv2's integer ids, so
that the text format reads like the program it encodes and a schema
change shows up as a readable diff. Expressions carry no type
annotations: every leaf has a known type, every operator's result is
determined by its operands, and run-time values carry their width, so
no interpreter infers anything and the goldens stay half the size.

The schema lives at `proto/p4blo/v0/p4blo.proto` under the package
`p4blo.v0`. The version is `v0` because the schema is expected to
change while the project runs; `v1` is reserved for the RFC-shaped
form. `buf` lints the schema and generates the Python bindings, which
are committed under `python/p4blo/v0/`, so that the proto package path and
the Python import path coincide and contributors without `buf` still
have a working package. A CI step regenerates them and
fails on any diff.

### Blocks and the P4NAH rule

The one hardcoded thing is a block calling convention and the rule
that a block performs no effects. That rule is called P4NAH.

```
parse   : Packet × M → H × M × bits consumed × accepted × error
control : H × M × TableEntries → H × M
deparse : H → Packet
```

A rejection is an outcome, not an exception: the caller gets the
partial headers, whether the parser accepted, and the error, and
decides what to do.

A control writes fields of `M`; whoever called it acts on them
afterwards. Drop, forward, flood, clone and recirculate are decisions
written as data, executed by the architecture. Tables are inputs
installed by the host. A block may call another block; that is P4's
own composition and it is in.

There is one `Block` message with a kind tag, parse, control or
deparse, and one signature. The three kinds differ in which statements
they may contain, and the validator enforces those rules per kind.
Three separate messages would have tripled the shared machinery for
locals, parameters and sub-block calls for no gain in clarity.

A parser may loop, since a state may be revisited while extracting
into a header stack. The bound is the no-consumption revisit rule: a
state that consumed no bits since it was last entered may not be
entered again, and doing so is a parse error. Fuel was rejected
because it makes the meaning of a program depend on a number nobody
specifies. Whether the oracles behave the same way is checked in step
4 and is not assumed.

### Metadata contract

An architecture declares the `M` fields it needs, each with a width
and whether the architecture provides it before the block runs or
consumes it after. At load the program's `M` is checked structurally
against the declaration, by field name and width, and nothing else
about `M` concerns anyone. A program declares exactly one `H` type and
one `M` type.

The contract vocabulary used by the architectures in this repository,
by field name, each optional and only checked when present:

| Field | Type | Direction | Meaning |
|---|---|---|---|
| `ingress_port` | `bit<9>` | provided | port the packet arrived on |
| `parser_error` | `error` | provided | the parser's error, `NoError` on accept |
| `egress_port` | `bit<9>` | consumed | unicast destination |
| `drop` | `bool` | consumed | discard the packet; wins over the rest |
| `flood` | `bool` | consumed | send to every port but the ingress one |

Fate is a set of booleans rather than an enum so that a program that
knows nothing of flooding, such as the forwarder, runs unchanged under
an architecture that offers it, which is what claim 3 requires. The
v1model shim maps these names onto `standard_metadata`; flood has no
shim mapping and is checked between the two architectures instead.

### Externs

Register, counter, meter, hash and checksum are not core P4; they are
v1model, PSA and PNA externs. At the IR level an extern is exactly a
declared type with method signatures, an instance with constructor
arguments, and call sites. The reference interpreter binds each
instance to a registered Python callable at load, checks arity,
directions and widths, and refuses to load on any mismatch.

Every extern a corpus program uses ships twice, a Python
implementation and a Lean model, pinned to each other by vectors. That
pair is corpus material, not spec material. The Python package of
bindings is a convenience and lives in its own subpackage so the
boundary stays visible.

### Architectures

Python functions of one shape: given an ingress port and a packet,
return egress ports and packets. The filter runs parser then control.
The switch runs all three blocks over a few ports and implements drop,
unicast and flood. Neither contains P4. Their size is the experiment
for claim 3.

Three things every architecture here does the same way, because the IR
does not decide them. After a parser rejection the control still runs
over the partial headers, with `parser_error` set if the program
declares it, as v1model does. The payload is the bytes after the ones
the parser consumed, and a parse that ends, accepted or not, having consumed a
number of bits that is not a multiple of eight is treated as a program
bug: the packet is dropped with a diagnostic, since P4 targets require
byte-aligned parsing anyway. The output packet is the deparser's bytes
followed by the payload.

### Python eDSL

A builder that constructs IR: plain constructors for declarations,
operator overloading for expressions, explicit constructs for control
flow in the manner of JAX's `lax.cond`. No decorator that reads Python
source, because the IR is the product and the eDSL should teach it by
use, not hide it.

### Printer

IR to P4-16 text. Cheap, and it pays twice: it feeds the oracle and it
is a frontend in reverse.

### Pure Python, always

The Python package carries no native dependency: the protobuf runtime
is the pure-Python wheel, packets are `bytes` and `int`, and there is
no pcap dependency because the vector format is text. The package
targets Python 3.13 and uses nothing newer. Both constraints are
cheap now and are what would make a browser playground free later;
the first compiled dependency or the first 3.14-only feature would
silently close that door.

### Oracle

The oracle runs the printed programs wrapped in a v1model shim that
maps the metadata contract onto `standard_metadata`, replays the
corpus vectors, and reports the verdict. The first oracle is
P4-SpecTec's simulator, checked on 2026-09-22: its `sim` command takes
a P4 program and an STF file, supports the v1model and ebpf
architectures, and builds with opam and dune, so it runs natively on
macOS and Linux without Docker. It is also the spec's own
mechanization, which is a stronger authority than a behavioral model
for a semantics project. BMv2's `simple_switch` is the optional second
oracle, Linux-only through Docker.

### Lean and differential random testing

A Lean interpreter over the IR, decoding the protobuf JSON mapping
with Lean's own JSON support. Cedar's Lean protobuf library is the
upgrade if speed ever matters. Differential random testing: corpus
programs times random packets and table entries, both interpreters
run, outputs compared, every divergence attributed to a bug on one
side. A pipe to a Lean binary is enough; there is no FFI. Random
program generation is later, if ever. One theorem is proved; the
candidates are listed under [Open questions](#open-questions).

### Coverage table

Every construct of P4's core appears in [coverage.md](coverage.md)
with one of three statuses: in; elaborated away, with the elaboration
named; or excluded, with a reason. The checklist is P4-SpecTec's
elaborated IL, walked construct by construct, because it is exactly P4
core after sugar. The subset is a checklist, not a horizon: the schema
is designed for the full core and never bakes an exclusion into its
shape.

## What is normative

- **Syntax:** the protobuf schema, plus the validator for what a
  schema cannot express: widths agree, ids resolve, parse graph rules
  hold, each block kind contains only its statements. The text format
  is the readable representation and the golden format; binary and
  JSON are transports.
- **Meaning:** the Lean interpreter. Everything else, the Python
  interpreter, the printer, the eDSL, the prose, is tested against it.
  Until Lean exists the Python interpreter is provisional and the
  prose contract in [semantics.md](semantics.md) stands in.
- **Closed behaviors:** everything P4 leaves open and p4blo closes is
  listed in [semantics.md](semantics.md) with its choice: reading a
  field of an invalid header, extraction past the packet end,
  arithmetic overflow, shifts by the width or more, table miss, LPM
  and ternary tie-breaking, header-stack index out of range, and the
  parser loop bound.

## Scope

Three exclusion categories; only the third makes p4blo a subset.

- **Out by thesis:** anything architecture-dependent: intrinsic
  metadata, packet fate as externs, action selectors and profiles,
  direct counters and meters, clone and recirculate as operations.
- **Out by elaboration:** generics, `int`, implicit casts, tuples,
  `switch` on action runs, and other sugar the frontend removes.
- **Out by scope, each threatening no claim:** `int<N>`, varbit,
  header unions, value sets, `exit`, `return`, `for`, extern function
  objects. Each is an additive change to the schema if it is ever
  wanted; `int<N>` in particular is one more `Type` kind and a signed
  variant of each arithmetic rule.

**In:** `bit<N>`, `bool`, enums and errors, headers, structs, header
stacks with push, pop and index arithmetic; parser states with
extract, lookahead, advance, verify, select with masks and ranges;
sub-parser and sub-control instantiation; actions with data; tables
with exact, lpm and ternary keys, priorities, default actions, const
entries; `if`, assignment, slices, concatenation, explicit casts,
wrapping arithmetic; emit; declared externs.

### Corpus

Four programs, chosen to hit the hard semantics: the p4lang tutorial
forwarder (lpm, TTL, checksum); an ACL (ternary with priorities,
parser errors); an MPLS or VLAN program (header stacks); a stateful
program (register). Where a program can be sourced from p4c's own test
suite with an STF file beside it, it is, because those expected
outputs were produced by BMv2 and reviewed by the p4c maintainers,
which gives oracle-grade vectors before any oracle runs here. The
tutorial forwarder has no STF; its vectors start hand-written and are
confirmed by the oracle later. The concrete picks are recorded in
[status.md](status.md) when the eDSL step reaches them.

Each corpus program is rewritten in the eDSL, printed back to P4,
checked to typecheck in P4-SpecTec, and then replayed on both sides.

## Testing strategy

Five layers, each answering a different question.

1. **Unit and property tests on the primitives.** Wrapping arithmetic,
   casts, slices, concatenation, extract and emit, select matching with
   masks and ranges. Hand-computed cases plus Hypothesis properties,
   such as emit after extract returning the original bytes and
   arithmetic agreeing with arithmetic modulo the width. Most
   interpreter bugs live here and it needs no corpus.
2. **Validator tests.** One tiny malformed program per rule, each
   expecting a specific error. This is the executable form of the list
   of what a schema cannot express.
3. **Corpus goldens.** Each program's IR text and printed P4 are
   committed. The eDSL regenerates them and the test diffs. A schema
   change shows up as a golden diff and is reviewed like code.
4. **Vectors in STF.** STF, the Simple Test Framework format that p4c
   and P4-SpecTec already use, is the vector format: `add` lines
   install table entries, `packet` lines give an input port and hex
   bytes, `expect` lines give the expected output. One file per
   scenario replays on the Python interpreter through a small STF
   runner, on P4-SpecTec through its `sim` command against the printed
   program, and on BMv2 when that oracle is used. It is readable text,
   so there is no pcap dependency.
5. **Differential random testing.** Python against Lean, corpus
   programs times random packets and entries, every divergence
   attributed.

The oracle job is separate from the ordinary CI run. P4-SpecTec's
OCaml toolchain is heavy and only the oracle needs it, so it is built
in its own CI job and by a local script for whoever wants it, not in
the dev shell.

## Repository layout and development environment

```
p4blo/
  flake.nix, flake.lock, .envrc     tools: python, uv, buf, protoc, elan
  pyproject.toml, uv.lock           one Python project rooted here
  buf.yaml, buf.gen.yaml            schema lint and codegen config
  AGENTS.md                         instructions for agents
  README.md                         the sentence, the claims, the table
  docs/                             design, semantics, coverage,
                                    status, decisions
  proto/p4blo/v0/p4blo.proto        the IR
  python/p4blo/                     the package
    v0/                             generated protobuf code, committed
    ir.py                           load, save, text format helpers
    validator.py
    interp/                         the reference interpreter
    edsl/                           the builder
    printer.py                      IR to P4-16 text
    externs/                        registry and the corpus externs
    arch/                           filter.py, switch.py
  lean/                             a lake project: lakefile,
                                    lean-toolchain, P4blo/
  corpus/<program>/                 program.py, program.txtpb,
                                    program.p4, *.stf
  tests/                            pytest: unit, validator, corpus
                                    replay, oracle drivers, DRT
  .github/workflows/                ci.yml; lean.yml and oracle.yml
                                    when their steps arrive
```

One Python project is rooted at the repository root so that `uv run
pytest` works from there and `tests/` holds both unit tests and the
claim tests, which are all pytest even when they shell out to Lean or
replay vectors. The package still lives at `python/p4blo`. Only two
top-level directories concern testing: `corpus/`, which is source,
goldens and vectors for each program side by side, and `tests/`, which
is everything that runs. Directories for later steps are created when
their step arrives, not as placeholders.

The development environment has three layers, each owning what it is
best at.

- **Nix flake for tools.** `flake.nix` pins the interpreter and the
  build tools: Python 3.13, `uv`, `buf`, `protoc`, `elan`, and Node
  for the `pyright` wheel. Linters and type checker are Python
  packages managed by `uv`, so the `uv`-only path has them too.
  `flake.lock` pins nixpkgs, so every contributor and CI get identical
  tool versions. Locally `.envrc` with `use flake` enters it through
  direnv. In CI, each job installs Nix and runs every command through
  `nix develop -c`. The flake is self-contained and adds nothing to
  anyone's home configuration. It supports Linux and macOS on Intel
  and ARM; Windows contributors use WSL2.
- **uv for Python packages.** Nix provides the interpreter and `uv`;
  `uv` owns `pyproject.toml` and `uv.lock`. Because the package is
  pure Python the lock resolves identically on every platform.
  Contributors who do not want Nix get a working Python environment
  from `uv sync` alone.
- **Lean's own pinning.** Lean is versioned by `lean-toolchain` in
  `lean/`, which `elan` reads. Nix supplies `elan`, not Lean, because
  Lean in nixpkgs lags releases and would fight the toolchain file.

BMv2 stays outside the environment on purpose. It is an optional
second oracle, run through a Docker image pinned by digest, on Linux
only, in a job that runs on demand.

A devcontainer is deferred. The README documents three tiers: the
flake through direnv as the recommended path, `uv sync` for
Python-only work, and a devcontainer on request. A devcontainer that
did not itself run the flake would be a second environment definition
and would drift; one that did would be Nix in a box. Either becomes
worth it only for a Windows contributor without WSL2 or for a
zero-install Codespaces story, and both are a one-day addition on top
of the flake.

## Build order

Each step ends with something that can fail.

1. **Schema, validator, semantics, one packet.** The v0 schema, the
   validator with its negative tests, the closed-behaviors file, the
   forwarder hand-written in text format, the Python interpreter with
   primitive tests, and an STF runner replaying hand-written forwarder
   vectors. Fails if the forwarder does not fit the schema or the
   packet comes out wrong.
2. **Externs.** The registry with signature checks; the stateful
   program. Fails if an extern needs something the IR cannot say.
3. **eDSL, corpus, architectures.** The four programs authored in the
   eDSL; the two architectures; the metadata contract check. Claims 1
   and 3 become measurable. Fails on an escape hatch or on the line
   counts.
4. **Printer and oracle.** The printer, the v1model shim, the
   P4-SpecTec job, STF replay on both sides. Claim 2. Fails on any
   unexplained divergence.
5. **Lean.** The Lean interpreter, the extern models, differential
   random testing, the theorem. Claim 4.
6. **Coverage table, README, write-up.**

The hand-written forwarder in step 1 will be several hundred lines of
text format with ids instead of names and is the first artifact to rot
when the schema changes. It is still written, because it is the honest
test of claim 1, but it is kept minimal and regenerated from the eDSL
in step 3 rather than maintained by hand.

Done means: four claims green, coverage table published, README with
the sentence and the claim matrix, one blog post. The date is Bili's
to set. The honest "useful on its own" story is modest: a readable
Python P4 interpreter with a clean IR, good for teaching and for
testing table logic in pytest, until a p4c bridge exists.

## Alternatives considered

- **Three block messages instead of one with a kind tag.** Rejected;
  see [Blocks](#blocks-and-the-p4nah-rule).
- **Fuel as the parser loop bound.** Rejected; see the same section.
- **BMv2 as the first oracle.** It was the original plan. P4-SpecTec
  replaced it because it needs no Docker, runs on macOS, and is the
  spec's own mechanization. BMv2 stays as the optional second.
- **pcap as the vector format.** Rejected in favor of STF, which is
  text, already understood by both oracles, and needs no native
  library.
- **Packaging Python dependencies through Nix.** Rejected; `uv` does it
  with less friction and gives non-Nix contributors a path.
- **Lean from nixpkgs.** Rejected in favor of `elan` and
  `lean-toolchain`, which every Lean project uses.
- **A devcontainer from day one.** Deferred; see the environment
  section.
- **A decorator-based eDSL that reads Python source.** Rejected
  because it hides the IR, and the IR is the product.
- **A browser playground as a deliverable.** Removed from the current
  plan to keep the project to its four claims.
- **Naming.** See [Appendix: naming](#appendix-naming).

## Risks

- **P4-SpecTec's v1model coverage.** Its simulator may not handle
  every construct a corpus program uses. Discovered in step 4; the
  fallback for an affected program is BMv2.
- **Schema churn.** The hand-written forwarder and the goldens rot
  with every schema change until the eDSL exists. Accepted for steps 1
  and 2; the goldens become regenerated from step 3.
- **Flood under the shim.** The v1model shim may not express flood
  without BMv2 multicast groups. If not, flood is checked between the
  two architectures and the oracle covers drop and unicast.
- **The Lean and Python interpreters disagreeing for a good reason.**
  A divergence that is really an under-specified closed behavior is
  resolved by adding the behavior to [semantics.md](semantics.md),
  not by patching one side.
- **Scope creep toward a fifth claim.** The design makes four claims
  and no others; anything else is a future item.

## Open questions

- ~~The one theorem.~~ Settled: extract-then-emit roundtrip, proved as
  `P4blo.extract_emit` in `lean/P4blo/Theorems.lean` over the packing
  functions the interpreter calls. Parser determinism was not
  attempted.
- Whether the v1model shim can express flood without BMv2 multicast
  groups.
- Whether P4-SpecTec's simulator covers every construct the corpus
  needs, and whether it can also be driven as a second oracle for
  programs where BMv2 is the first.
- Whether p4blo parsers could one day lower to Pakeles; a question,
  not a plan.

## Neighbors

- [P4-SpecTec](https://github.com/kaist-plrg/p4-spectec): the P4
  spec's own executable mechanization, on the official track since
  2026. Its elaborated IL is the coverage checklist and its simulator
  the first oracle. p4blo does not re-mechanize P4; it serializes the
  elaborated core and takes the architecture out.
- [Nano-P4](https://github.com/pacokwon/nano-p4-spec) (P4.org GSoC
  2026): an educational P4 dialect with typing rules, dynamic
  semantics and one hardcoded NanoSwitch architecture, in SpecTec.
  The same size of language with the opposite decision about the
  architecture; the foil for claim 3.
- [4ward](https://github.com/4ward-p4/4ward): a p4c backend into a
  protobuf behavioral IR into a Kotlin simulator, no semantics; the
  proof that a protobuf P4 IR is workable and the precedent for a p4c
  bridge.
- [p4mlir-incubator](https://github.com/p4lang/p4mlir-incubator): a
  compiler IR for a future p4c, not an interchange format.
- [HOL4P4](https://github.com/kth-step/HOL4P4): mechanized semantics
  with an executable derived inside the prover; no serialized IR.
- [cedar-spec](https://github.com/cedar-policy/cedar-spec): the
  method: Lean model as the spec, a production implementation,
  differential random testing, protobuf across the boundary.
- [µP4](https://github.com/cornell-netlab/MicroP4) (SIGCOMM 2020):
  composed programs inside the language; p4blo takes the architecture
  out of it. The framing to be visibly different from.
- [BMv2](https://github.com/p4lang/behavioral-model): the optional
  second oracle.
- [p4c](https://github.com/p4lang/p4c): the source of corpus programs
  and their STF vectors.
- [ONNX](https://github.com/onnx/onnx): the precedent for a readable
  protobuf IR: references by name, a checker that owns what the schema
  cannot say. Its generic node with a string operator type is not
  followed, because P4's core has a fixed handful of operators and the
  typed schema is the grammar the Lean side decodes.

A construct-by-construct survey of the P4 IRs is in
[notes/prior-art-ir.md](notes/prior-art-ir.md).

## Appendix: naming

*p4blo*: `p4` plus `blo`, block cut short, read aloud as *Pablo*.
Pablo descends from Latin *Paulus*, "small", so the name says small
blocks in two languages. Name-shaped rather than claim-shaped, so the
tagline carries the claim. Sweep (2026-09-21): free on PyPI, crates.io
and npm; no repository of that name; the GitHub handle is an unrelated
empty account. Domains and trademarks unswept.

Considered and rejected: `p4sem` and `p4ir` name the method, and
`p4ir` is one letter from P4HIR; `p4blocks` is claim-shaped and
invites the µP4 reading; `p4nah` reads as dismissive of P4 the moment
it heads a community proposal; the small lane (`p4mini`, `p4tini`,
`p4nano`) is Nano-P4's, and `p4nano` collides with it outright;
`microp4` is µP4; `p4core` reads as core.p4; pa-words from other
languages (*pala*, *palikka*, *parva*, *pavé*, *parça*) each needed a
footnote that `blo` does not.
