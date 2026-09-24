# IR specification and verified language packages

Implementation plan accepted: 2026-09-23. Bili authorized autonomous
implementation, small tested commits and pushes. This is not a completed
migration or a claim that the proposed proofs already exist. Track execution
in [../implementation.md](implementation.md) and [../status.md](status.md).
This checkpoint incorporates the subsequent agreement on a separate
user-facing Lean package and the design informed by the prior-art survey.
It also records the P4 expressiveness north star and the agreed progression
of P4 and XDP examples. These are targets, not claims of existing support.

## Agreed direction

There is one p4blo IR, with different representations. Lean defines what
a program is, whether it is valid, and what it means. Protobuf defines how
programs are exchanged. An explicitly specified, verified conversion
connects them.

| Concern | Intended authority |
|---|---|
| Abstract syntax: expressions, statements, declarations | Lean |
| Validity: types, scopes, widths, legal combinations | Lean |
| Meaning: execution and observable behavior | Lean |
| Serialization: messages, field numbers, encoding versions | Protobuf schema |
| Correspondence between wire values and abstract programs | Conversion specified in Lean |

This revises the earlier "protobuf is normative for syntax, Lean for
meaning" arrangement. Active instructions now assign abstract syntax to
Lean and encoding to protobuf. Whole-program validity formalization and
verified conversions remain obligations, not completed guarantees.

The goal is not to derive everything from one file. It is to give every
accepted program one unambiguous meaning and every implementation a checked
connection to that meaning.

## Distinct boundaries

```text
Serialized data
    | parse: supported, well-formed encoding?
Wire representation
    | decode: which abstract program?
Abstract program
    | validate: is that program legal?
Valid program
    | execute: what does it do?
Observable behavior
```

These are distinct contracts, not a requirement for separate packages or
directories. Parsing a protobuf message does not establish program
validity: variants may be unset, widths illegal, or references unresolved.

Prefer ordinary raw abstract syntax, a separate `WellFormed` predicate,
and an executable validator. A validated program can pair raw syntax with
evidence of validity. Do not force every scoping and typing constraint into
the initial syntax datatype: raw syntax is useful for diagnostics,
malformed-input testing, and production correspondence.

## Target obligations, not existing guarantees

1. **Encoding preserves programs.** For a program representable in encoding
   version `v`, `decode_v(encode_v(program)) = ok program`. State the domain
   explicitly: Lean's unbounded `Nat` does not always fit protobuf's
   `uint32`. Equality concerns the abstract program, not byte-for-byte
   identity of every possible serialization; annotation handling must be
   specified separately.
2. **Validation is sound and ideally complete.** Acceptance implies
   `WellFormed(program)`; conversely, well-formed programs should be
   accepted. Soundness alone admits a useless reject-everything checker.
3. **Production execution agrees with the model.** Compare observable
   Python execution with Lean execution of the decoded program,
   under explicit validity, input, initial-state, architecture, and extern
   assumptions. Packet output alone is insufficient for stateful programs.
4. **Trust boundaries remain explicit.** A proof about in-memory conversion
   does not verify binary/JSON parsers, generated bindings, compilers, or
   the compiled Lean executable. Document and test those remaining parts.
   Differential agreement is evidence, not universal Python equivalence.

The current Lean validity theorem covers a closed scalar fragment, not
whole programs. The current Lean adapter uses handwritten protobuf-JSON
conversion, not a verified protobuf binary parser.

Keep the specification small and executable. Build on the existing
transition machine and reference runner, with proofs connecting them,
rather than maintaining unrelated definitions of execution. Architecture
and extern implementations remain outside the core; their contracts state
the assumptions required by execution proofs.

## Generation is optional machinery

Do not let protobuf wrapper messages dictate the semantic model, or let
incidental Lean refactoring silently change persistent wire formats.
Field/enum numbers, defaults, presence, and version history require explicit
wire-layout decisions; constructor order is not a stable numbering policy.

Proposed progression:

1. Preserve the existing schema while making its Lean correspondence
   explicit.
2. Prove conversion properties and check schema/mapping coverage in CI.
3. Add narrowly scoped generation where it removes demonstrated duplication.

An eventual generator could consume Lean syntax plus an explicit wire-layout
description and emit `.proto` and conversion scaffolding. This is an option,
not a selected framework or a prerequisite for verification. Keep Python
execution independent of the Lean reference; sharing generated syntax
does not require sharing semantics implementations.

## Adversarial boundary testing

The zero-literal defect already found in this repo is the motivating case:
Lean omitted decimal-string zero; its decoder supplied zero for an absent
field, hiding the bug in Lean-only round trips. Protobuf instead supplied
an empty string. See [the review](notes/reviews/zero-encoding.md).

Require cross-implementation round trips in both directions, initially
Lean/Python. Exercise malformed inputs, defaults,
missing variants, numeric limits, and unknown fields. Deliberately mutate
the mapping as well as the interpreters, and preserve regressions for
survivors. Two matching codec bugs must not count as sufficient evidence.

Specify whether the JSON interface is a restricted interchange profile or
full ProtoJSON; these are different promises. An old executor must not
silently ignore a new field that changes behavior. Explicitly nonsemantic
annotations need a separate policy. Wire compatibility alone does not
establish semantic compatibility.

Relevant encoding references:

- [Protobuf language guide](https://protobuf.dev/programming-guides/proto3/)
- [ProtoJSON specification](https://protobuf.dev/programming-guides/json/)

## Package organization

The agreed direction is one Python `p4blo` distribution containing distinct
IR support, eDSL, and interpreter components. Rust is outside the current
plan; do not add its scaffolding. eDSL and interpreter depend on shared IR
support, not on each other. The formal IR contract is shared across
languages; generated bindings belong with their language package.

The target responsibilities are:

```text
ir/       Authoritative Lean IR specification and encoding contract
lean/     User-facing Lean eDSL and interpreter package
python/   User-facing Python eDSL and interpreter package
tests/    Shared corpus and cross-implementation verification
docs/     Design, decisions, status, workflows
```

These describe the semantic components, not an exhaustive list of build
and repository-support files. Package-local tests stay with their library.
Do not create empty future directories. The specification and schema now
live in `ir/`; `lean/` is the independent user package with a reference
execution API. Shared corpus and oracle tooling live under `tests/`. The
typed eDSL remains work in progress; structural migration does not complete
the planned proof and application milestones.

The two Lean packages have a one-way dependency: the user-facing package
imports the IR specification, never the reverse. Separate packaging does
not require duplicating definitions. Lean-to-Lean calls pass the actual IR
values directly; protobuf is for exchanging programs with other languages,
files, or processes, not an obligatory boundary between Lean libraries.

Package names follow that boundary: `lean/` is Lake package `p4blo`, imported
as `P4blo`; `ir/` is Lake package `p4blo-ir`, imported as `P4bloIR`. The user
API owns the project name. The stable conformance executable remains named
`p4blo-lean`; an executable protocol name need not equal a library namespace.

Use "interpreter" for core IR execution; "simulator" can describe its
composition with architecture and extern models. eDSL lowering correctness
is a separate obligation from interpreter correctness. Test combinations of
the available eDSLs and interpreters against the same IR contract; agreement
between production implementations alone does not establish conformance.

## Lean eDSL: friendly surface, small typed core

The selected direction combines verified lowering with selective
proof-producing elaboration:

```text
Human-friendly notation
          | elaboration
Small typed construction language
          | verified lowering
Raw IR + proof of well-formedness
```

The construction language is internal to the Lean package, not another
competing definition of p4blo. Track useful local invariants in its types:
expression widths, references, values versus assignable locations, and
which statements a block permits. Global conditions such as call-graph
restrictions may use proved validation instead of increasingly complicated
dependent types. Successfully compiled programs carry validity evidence;
the exact interface for rejected source programs remains to be designed.

Prioritize named fields, familiar expressions, reusable definitions,
inference where unambiguous, helpful diagnostics, and minimal visible proof
plumbing. Host Lean functions may construct and parameterize programs;
arbitrary Lean computation is not automatically packet-time behavior.

Give the typed construction language small, compositional semantics and
prove lowering preserves it. Validity alone is insufficient: a compiler
that replaces every program with a valid no-op could preserve validity.
Defining source meaning solely as the result of lowering would likewise
hide lowering bugs rather than check them.

Prove small lowering functions correct once. Elaborators can assemble
applications of those theorems; more sophisticated transformations can
produce checked proofs for each translation. Such proofs must connect the
actual source definition to the actual generated output. The initial
notation-to-typed-program boundary remains explicitly tested and reviewed:
kernel checking does not by itself prove that custom notation matches the
author's intention. A general compiler from arbitrary Lean is not a goal.

## Lean interpreter: reuse first, prove refinements when useful

Expose a useful interpreter API in the Lean package from the start, with
loading, execution, diagnostics, and state inspection. Initially it can
reuse the executable reference semantics. Call that reuse, not a verified
independent second engine.

Introduce distinct implementation machinery when it offers a concrete
benefit, such as resolving names to indexed locations before execution.
For each refinement, prove a relation between implementation states and
specification states, covering results, faults, and persistent extern state.
Do not duplicate a full interpreter merely for symmetry with Python.

Keep termination separate from correctness of terminating executions.
External callbacks and actual I/O require stated assumptions or separately
verified models. Proofs about Lean functions do not automatically verify
their compiled machine code, compiler/runtime, or external interfaces.

## Compositional assurance

| Boundary | Intended primary assurance |
|---|---|
| Lean eDSL to IR | Validity and semantic-preservation proofs |
| Lean execution to IR semantics | Reference reuse initially; refinement proofs for distinct implementations |
| Protobuf to/from abstract IR | Codec proofs on the representable domain plus cross-language tests |
| Python execution to IR semantics | Differential/property tests, adversarial mutations, scoped certificates |
| Authored program to intended application behavior | User-facing properties and proofs, or tests |

Make it natural to prove an application property, such as an ACL never
forwarding packets from forbidden sources, and transport it through
compilation and verified execution. A correct compiler can faithfully
compile an incorrect ACL. Stronger Lean guarantees do not upgrade Python's
tested conformance into universal equivalence.

Extend adversarial work to lowering and the proof statements: change an
operator, swap references, omit a state update, corrupt a codec default,
or weaken a validity rule or theorem assumption. Some faults should break
proofs; others must fail independent tests or review. Retain external
oracles and known-answer cases because a proof can establish the wrong
specification. Preserve the existing proof-axiom audit throughout.

## Prior art and what to borrow

These are design precedents, not selected dependencies or claims that
their guarantees automatically apply to p4blo.

| Project | Relevant lesson | Limit for our use |
|---|---|---|
| [Kôika](https://github.com/mit-plv/koika) | Embedded authoring language, executable semantics, verified compilation | Its circuit compiler theorem does not automatically cover its separate C++ simulation backend |
| [Lean-MLIR](https://github.com/opencompl/lean-mlir) | Typed representations, denotations, compositional transformation proofs | Do not adopt SSA or an entire framework merely for reuse |
| [Veil](https://github.com/verse-lab/veil) | Domain-oriented Lean syntax and integrated automated/interactive proofs | Condition-generation soundness and proof discharge have separate trust boundaries |
| [CakeML](https://cakeml.org/) | Proof-producing translation can connect source definitions to generated syntax | Supported source subset and the exact theorem still need to be specified |
| [Lean4Lean](https://github.com/digama0/lean4lean) | Separate implementation, abstract theory, and connecting verification modules | Study the structure; do not assume blanket proof coverage or full implementation independence |
| [Fiat Cryptography](https://github.com/mit-plv/fiat-crypto) | Domain-specific verified compilation with explicitly documented backend boundaries | An AST-level proof does not establish correctness of output printing or serialization |
| [Cedar](https://github.com/cedar-policy/cedar-spec) | Independent production implementation checked against an executable model | Differential testing is not a universal equivalence proof |

Further reading:

- [Lean-MLIR ITP paper](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2024.9)
- [Veil CAV paper](https://verse-lab.org/papers/veil-cav25.pdf)

Borrow proof patterns and user-experience ideas, not entire frameworks by
default. The initial typed-core/verified-lowering design leaves room for
proof-producing frontend extensions without requiring two complete
competing frontend implementations.

## North star and intermediate goals

Bili's north star is an IR expressive enough for all architecture-independent
behavior of a pinned P4 version, after removing syntactic sugar, while
remaining minimal. Interpret architecture independence as explicit external
contracts, not an inability to interact with architecture services. Minimize
the total semantic, lowering, and proof complexity, not just constructor
count. Existing exclusions and restrictions must be revisited; a feature
not appearing in the current corpus is not a permanent justification for
excluding it. Preserve semantic requirements even when expressed through
annotations, such as atomicity.

Separate language-defined behavior from implementation/environment choices
and the simulator's default profile. A deterministic permitted behavior is
not a representation of every permitted behavior. Pin the language version
and state equivalence/refinement assumptions before claiming completeness.
The existing IR-to-P4 printer tests supported programs; eventual P4-to-IR
lowering is needed to challenge expressiveness from the source side.

This is a north star, not a prerequisite for the next deliverable. Guide
intermediate development with increasingly demanding examples, including
neighboring packet-processing domains. Re-expressing an XDP datapath is in
scope for that exploration; implementing an arbitrary eBPF virtual machine
or Linux environment is not implied.

## Example-driven progression

Bili agreed to this progression. Difficulty means implementation and
assurance effort, not source-code size. Retain small feature-specific tests
alongside the examples; no flagship establishes full language coverage.

| Stage | Example | Intended demonstration |
|---|---|---|
| 0 | Existing IPv4 forwarder and small stateful corpus | The new package/proof workflow works end to end |
| 1 | P4 tutorial stateful firewall | A complete application depending on packet history |
| 2 | xdp-tools' `xdp-filter` datapath | Useful packet-processing semantics shared across source ecosystems |
| 3 | ETH flowlet-switching example, conditional | Explicit time/randomness inputs and persistent decisions |
| 4 | A bounded Katran configuration | A substantial production-origin datapath fits naturally |

The main commitment is firewall first, `xdp-filter` second, and a bounded
Katran profile as the larger destination. Flowlet switching is a targeted
bridge, not a prerequisite that blocks unrelated progress if its oracle
integration is unavailable. None of the new candidates has been executed
or ported as part of this design discussion; source/oracle preflight and
revision pinning are required before implementation commitments.

### Stage 0: consolidate the foundation

Use an existing small example to exercise ergonomic Lean source, verified
lowering for the supported fragment, the Lean and Python execution APIs,
and comparison with original P4 behavior. The existing Python/IR corpus is
not new work to recreate; the new Lean authoring/proof path is the checkpoint.
This refines the earlier proposal for a small stateful end-to-end slice.

### Stage 1: tutorial stateful firewall

Use the [P4 tutorial firewall](https://github.com/p4lang/tutorials/blob/master/exercises/firewall/README.md)
and its reference solution. It combines routing, TCP fields, hashing,
persistent registers, and direction-dependent filtering. Compare against
the original P4 on P4-SpecTec, supplemented by BMv2 where appropriate.

Acceptance sequences include rejection before corresponding outbound
initiation, changed decisions after state is populated, multiple flows
sharing state, and deliberate Bloom-filter collisions. Apply those claims
under explicitly configured boundary rules and input assumptions. Preserve
the original filter's false-positive behavior; do not silently replace it
with exact connection tracking or claim it blocks every unsolicited flow.

Milestone claim: p4blo can express, execute, and help verify a complete
stateful networking application.

### Stage 2: xdp-filter

Use the [xdp-tools filtering utility](https://github.com/xdp-project/xdp-tools/blob/main/xdp-filter/README.org).
Begin with a named feature configuration and expand to the selected full
datapath configuration. Its
[packet-processing implementation](https://github.com/xdp-project/xdp-tools/blob/main/xdp-filter/xdpfilt_prog.h)
interleaves parsing with early policy decisions and updates counters on
matches. Preserve that order, malformed-packet behavior, dynamic rule
configuration, relevant state, and distinct pass/drop/abort outcomes.
Do not assume that parsing every header before filtering is equivalent.

Compare against the original compiled BPF program running in Linux, not
P4-SpecTec. The [kernel's BPF_PROG_RUN facility](https://docs.kernel.org/bpf/bpf_prog_run.html)
provides a candidate packet/context replay mechanism without live interface
attachment. Use a suitable Linux test environment; CPU selection, per-CPU
state, and concurrency assumptions need explicit treatment. Sequential
replay is not a concurrency proof. Translate the datapath, not the loader
or CLI; map semantics must not silently become different table semantics.

Milestone claim: p4blo captures useful packet-processing semantics outside
P4. A manual rewrite demonstrates expressiveness and tested agreement, not
a verified general eBPF translator.

### Stage 3: flowlet switching, conditional

Use the [ETH flowlet-switching example](https://github.com/nsg-ethz/p4-learning/blob/master/exercises/05-Flowlet_Switching/README.md)
to exercise timestamps, flowlet identifiers, hashing, and persistent path
selection. Establish a credible oracle/replay strategy for controlled time
and randomness first. Our inspected SpecTec pin has an unimplemented
v1model random helper, so support cannot be presumed from the architecture
name alone.

Test timeout boundaries, timestamp wraparound, and hash collisions.
State path-stability properties under explicit configuration and collision
assumptions. A changed flowlet identifier need not yield a different path.

Milestone claim: reproducible reasoning about stateful behavior that depends
on environmental inputs. Do not substitute wall-clock timing for replayable
inputs or quietly change the source algorithm to make the oracle run.

### Stage 4: bounded Katran configuration

Select a pinned configuration of [Katran](https://github.com/facebookincubator/katran)
after a source audit, retaining meaningful backend-selection and
packet-transformation behavior. It has
[documented production origins](https://engineering.fb.com/2018/05/22/open-source/open-sourcing-katran-a-scalable-network-load-balancer/).
The profile, environment/state model, and exclusions remain to be selected.
Validate against the original BPF datapath under corresponding conditions.
Do not call an independently simplified lookalike full Katran support.

Milestone claim: p4blo can model and validate a substantial production-origin
datapath. This is not a throughput, deployment-readiness, or full-Linux
equivalence claim.

### Acceptance bar for every stage

1. **Precise scope:** pinned upstream source, selected configuration,
   environment assumptions, and exclusions.
2. **Readable authoring:** Python and Lean eDSL versions, without concealing
   application logic in an opaque extern. Necessary services have explicit
   contracts and independently checked models.
3. **Independent comparison:** original-program execution, packet sequences,
   relevant state, malformed inputs, and configuration changes where
   applicable. A round trip through our own printer is not a replacement.
4. **Scoped Lean proofs:** named application properties and lowering
   guarantees, with fragments, assumptions, and remaining gaps stated.
   Tested source equivalence is not a universal source-translation theorem.
5. **Adversarial evidence:** deliberate faults detected by proofs or tests,
   with survivors investigated and recorded.
6. **IR design review:** justify every new primitive against possible
   elaboration and its effect on total implementation/proof complexity.

Keep P4-SpecTec as the primary P4 oracle and Linux BPF execution as the
primary XDP oracle. Neither alone establishes the whole IR's correctness.
Compare complete relevant observations, not packets alone. Stronger Lean
proofs do not turn differential agreement with Python into a universal proof.

## Implementation choices to resolve incrementally

The architecture and example progression are approved for implementation.
Record reversible choices, their confidence and revisit triggers instead
of waiting for user feedback on every unsettled detail. Expand from
the first slice without requiring proofs for every existing IR feature.
Judge readability, diagnostics, generated IR, and proof effort together.
Supporting priorities remain:

1. Establish Lean ownership of abstract syntax, validity, and meaning in
   the design and reconcile the older normative-syntax wording.
2. Formalize the existing encoding boundary, including representability
   and rejection rules.
3. Prove codec properties and expand cross-language adversarial testing.
4. Expand Lean validation beyond the closed scalar fragment.

Still to settle: exact surface syntax and typed-core representation;
proof-producing frontend scope; stage-0 example and application property;
upstream pins, feature profiles, and oracle feasibility for later examples;
theorem interfaces and initial fragment; sequencing against the existing
verification roadmap; JSON profile; version/annotation policy; initial
codec proof scope; whether schema generation is worthwhile; and package
names, build configuration, and directory migration details.
The earlier discussion-only/no-commit instruction was explicitly lifted.
Keep implementation claims narrower than the target until their gates pass.
