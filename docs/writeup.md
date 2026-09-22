# p4blo, written up

A post for P4 spec, compiler and architecture people, to decide whether
the proposal below deserves an RFC. Every number in it comes from a file
in this repository or from a command run against it, and each is cited.

## 1. The sentence

P4's semantic core as an IR, architecture-free, with an independent Lean
semantics validated against a runnable reference.

That sentence is the project. p4blo is a personal, educational prototype
whose purpose is to make the sentence concrete enough to argue about, so
that a serious version can be proposed to the P4 community rather than
built alone.

The proposal is one paragraph and has no ask. P4 should have a
specified, architecture-free semantic core with a serialized form. The
P4 language is one frontend of that core among several. Architectures
and externs are specified outside it as contracts. An RFC to standardize
such an IR comes after this project, not inside it. It must read as the
serialized form of the elaborated core that P4-SpecTec already defines,
with the architecture taken out, never as a third IR beside SpecTec and
p4mlir. That paragraph is from `docs/design.md`. The rest of this post is
the evidence for and against it.

## 2. Why now

Four pieces exist in 2026 that make the proposal cheap to test, and none
of them takes the architecture out. The survey behind this section is
`docs/notes/prior-art-ir.md`.

P4-SpecTec is the P4 specification's own mechanization, on the official
track since 2026. Its elaborated IL, `spec/4-p4-ir/4.0-ir-syntax.watsup`,
is P4 after typing: implicit casts made explicit, every expression
annotated with its type. The architecture is not in the IL. It sits
outside, in `7-instantiation` and `9-arch`, where the v1model and ebpf
models bind blocks to a pipeline. That is the right cut, and it is why
p4blo uses the IL as its coverage checklist and SpecTec's simulator as
its first oracle. But the IL is a grammar inside a spec, not a serialized
form a tool can consume; it still holds type parameters, the
arbitrary-precision `int`, tuples, `switch`, `exit` and value sets; and
a program's executable meaning under SpecTec is always its meaning under
one of SpecTec's architectures.

p4mlir-incubator is a compiler IR for a future p4c, built on MLIR. A
compiler IR is made to be transformed inside one compiler; an
interchange format is made to be consumed by many tools with one fixed
meaning. It is the right project for p4c's future and the wrong shape
for this proposal, which is why the proposal says never a third IR.

4ward is the closest precedent. It is a p4c backend that emits a protobuf
IR, `simulator/ir.proto`, after p4c's midend, with names rather than
numeric ids, and a Kotlin simulator that runs it. It proves that a
protobuf P4 IR is workable and that p4c can be made to produce one. It
also keeps the architecture inside the IR: an `Architecture` message
names `v1model`, `psa` or `pna` and lists pipeline stages, and extern
semantics live per architecture in the simulator. It has no semantics
apart from that simulator, and every `Expr` carries a type annotation the
consumer must trust.

Nano-P4, a P4.org GSoC 2026 project, is an educational P4 dialect in
SpecTec with typing rules, a dynamic semantics and one hardcoded
NanoSwitch architecture. It is the same size of language as p4blo with
the opposite decision about the architecture, which makes it the foil
for claim 3 below rather than a competitor.

So the pieces are there: a spec-owned elaborated core to copy the
checklist from, a working protobuf route out of p4c, cedar-spec's method
of a Lean model checked by differential testing, and a small-language
precedent with the architecture hardcoded. What was missing was one
artifact that combines them with the architecture removed.

## 3. What was built

In the order a reader should look.

### The schema

`proto/p4blo/v0/p4blo.proto` is 669 lines, 71 messages and 5 enums,
proto3, package `p4blo.v0`. It reads in a sitting. The header comment
states the contract: what the schema cannot express, the validator in
`python/p4blo/validator.py` enforces, from name resolution and width
agreement through parser graph shape, per-kind statement rules, ternary
priorities and acyclic block calls.

Post-elaboration means the IR is P4 after the frontend has done its
work: monomorphic blocks, every width resolved, explicit casts, desugared
control flow. No generics, no `int`, no implicit casts, no tuples. Every
frontend, the Python eDSL now and a p4c backend later, owes the IR the
same elaboration. That is what keeps the Lean semantics free of type
inference.

Three decisions shape the schema, each logged with its reason in
`docs/decisions.md`.

Names, not ids. The first draft used global integer ids. It was switched
the same day, on a pointer to ONNX and on 4ward's stated principle,
because the text format is the golden format and must read like the
program it encodes; a schema change should show up as a readable diff.
Scopes are P4's and the validator resolves every reference once. Lean
pays with string-keyed maps, which costs nothing the project claims.

No types on expressions. 4ward, p4c and SpecTec annotate every node.
p4blo does not: every leaf is typed, every operator's result is
determined by its operands, run-time values carry their width, and the
validator computes every type once. Annotations would double the goldens
and add a consistency check for no semantic gain.

Dedicated packet and header nodes. `extract`, `emit`, `lookahead`,
`advance`, `verify`, `isValid`, `setValid`, `setInvalid`, `push_front`
and `pop_front` are statements and expressions of the IR, not method
calls on `packet_in`, `packet_out` and headers as in SpecTec, p4c and
4ward. The calling convention has no packet value, and the Lean side is
simpler without method dispatch. "Extern" then means declared externs
only. The printer reverses this.

Also fixed: one `Block` message with a kind tag, parser, control or
deparser, and one rule, that a block performs no effects. The calling
convention is

    parse   : Packet × M → H × M × bits consumed × accepted × error
    control : H × M × TableEntries → H × M
    deparse : H → Packet

A parser rejection is an outcome, not an exception. A control writes
fields of `M`; drop, forward and flood are decisions written as data, and
whoever called the block acts on them afterwards.

### The closed behaviors

`docs/semantics.md` lists everything P4 leaves open, undefined or
target-defined that p4blo closes, each with its choice, its reason and a
section reference to P4-16 1.2.5: reading a field of an invalid header,
extraction past the packet end, arithmetic overflow, shifts by the width
or more, table miss, lpm and ternary tie-breaking, header-stack index out
of range, uninitialized reads, the fixed order of the seven core errors,
and the parser loop bound. That bound is the no-consumption revisit
rule: entering a state with the cursor where it was at the last entry
raises `ParserTimeout`. Fuel was rejected because it makes the meaning of
a program depend on a number nobody specifies. A behavior is written
there before it is implemented, and a divergence that turns out to be an
unlisted open behavior is resolved by adding it, not by patching one
side.

### The reference interpreter

`python/p4blo/interp/` is about 1,700 lines of pure Python in thirteen
modules, ordered bottom up so that the package reads as one explanation:
values, packet, tables, environment, expressions, statements, then the
three entry points `run_parser`, `run_control` and `run_deparser`. None
mutates its arguments. Each function that implements a closed behavior
cites the section of `docs/semantics.md` it implements. It is the
runnable reference; Lean is normative.

### The eDSL

`python/p4blo/edsl/` is a builder that constructs IR: plain constructors
for declarations, operator overloading for expressions, explicit
constructs for control flow in the manner of JAX's `lax.cond`. It gives
integer literals a width from context and inserts nothing else; every
cast in a golden is one the author wrote. There is no decorator that
reads Python source, because the IR is the product and the eDSL should
teach it by use, not hide it.

### The corpus

Ten programs under `corpus/`, each with its eDSL source, its IR golden,
a README naming what was elaborated away, and vectors in STF, the text
format p4c and P4-SpecTec already use. Eight come from p4c's own test
suite with the STF file beside them, picked after the survey in
`docs/notes/corpus-candidates.md`, because those expected outputs were
produced by BMv2 and reviewed by the p4c maintainers. The ninth, the
p4lang tutorial forwarder, has no STF; its five vector files were
hand-derived and later confirmed by the oracle.

- `forwarder`, the tutorial `basic.p4`: lpm, TTL decrement, the IPv4
  checksum through a `checksum16` extern. Elaborated: typedefs;
  `standard_metadata` into three contract fields; `mark_to_drop` into
  `meta.drop = true`; `update_checksum`'s field list into one `bit<144>`
  argument.
- `acl`, p4c's `ternary2-bmv2`: the only v1model STF with runtime ternary
  adds and overlapping priorities, so it is the program that fixed the
  priority convention, larger wins. Elaborated: `switch` on `action_run`
  into a control local plus an if-chain; `setbyte(out reg, val)` bound per
  table into four action copies, named as p4c's own frontend names them.
- `stacks`, `header-stack-ops-bmv2`: fifteen BMv2-produced vectors over
  push, pop, holes and `next`. Elaborated: slice lvalues into a
  read-modify-write of the whole field; `hs.last` into
  `hs[hs.lastIndex]`; a sub-control instance into a block call.
- `subparser_stack`, `subparser-with-header-stack-bmv2`: a sub-parser
  extracting into `hs.next` through an `inout` argument, and a
  parser-scoped local read by a `select`.
- `stateful`, `issue1097-2-bmv2` plus vectors of our own: one
  `register<bit<8>>` read and written from two blocks, merged into one
  control. A seed guard was added so that state across packets is
  observable, and a `counter` so that the oracle exercises one at all.
- `csum16`, `issue655-bmv2`: six vectors on the 0xFFFF/0x0000 edge of
  one's-complement arithmetic, pinning the checksum extern the forwarder
  uses.
- `parser_error`, `parser_error-bmv2`: a failed extract consumes nothing,
  and the control runs after rejection with `parser_error` set.
- `verify_error`, `issue1824-bmv2`: user-declared errors, two
  `verify(false, ...)` in a row, and the header extracted before the
  failure surviving into the control.
- `priority`, `table-entries-priority-bmv2`: `@priority` on const
  entries, mapped from p4c's smaller-wins counter onto the IR's
  larger-wins numbering.
- `register_bounds`, written after the second review found that no
  random input could reach an out-of-range register index: a
  four-cell register indexed by a header byte, so reads past the end
  return zero and writes there vanish, visibly.

Each README's "Elaborated away" list is the evidence for claim 1: every
rewrite is named, and none is an escape hatch.

### The two architectures

`python/p4blo/arch/filter.py` is 45 lines; `python/p4blo/arch/switch.py`
is 50. Neither contains P4. The filter runs parser then control and
either drops the packet or forwards the original bytes. The switch runs
all three blocks over a few ports and implements drop, unicast and flood;
its output packet is the deparser's bytes followed by the payload the
parser did not consume.

They talk to a program only through the metadata contract in
`python/p4blo/arch/contract.py`: an architecture names the fields of `M`
it needs, each with a type and a direction. The vocabulary here is five
fields: `ingress_port` and `parser_error` provided; `egress_port`, `drop`
and `flood` consumed. Every field is optional, checked structurally at
load by name and type, and a field the program does not declare reads as
zero and swallows writes. Fate is booleans rather than an enum so that
the forwarder, which knows nothing of flooding, runs unchanged under the
switch.

### The printer and the oracle

`python/p4blo/printer.py` turns IR into P4-16 text inside a v1model shim
that maps the contract fields onto `standard_metadata`. It pays twice: it
feeds the oracle, and it is a frontend in reverse. Its goldens are
typechecked with `p4test` through Docker when Docker is available.

The oracle is P4-SpecTec's simulator, pinned at commit `2730cfd9` and
driven by `oracle/run.py` through its `sim` command on the same STF
vectors the Python side replays. Every vector file passes, 15 files over
ten programs, in its own CI job. It is the spec's own mechanization,
which is a stronger authority than a behavioral model for a semantics
project, and it runs natively without Docker.

What it cannot check is written in `oracle/README.md`. The simulator has
no longest-prefix rule: lpm entries match as ternary and ties need
priorities, so `oracle/run.py` translates each lpm `add` into a
full-width wildcard with the prefix length as its priority. The oracle
therefore confirms the forwarder's outputs but does not independently
check the longest-prefix rule of `docs/semantics.md`; the translation
supplies it. `no_packet` is unsupported and becomes a comment, with the
simulator's end-of-file leftover check carrying the assertion. `flood`
has no v1model mapping and no oracle sees it. Register state crosses the
boundary only as packet bytes. And because p4c refuses priorities on
`const entries`, the printer emits a ternary table's const entries as
ordinary entries, so the oracle sees host-mutable entries where the IR
has const ones.

### The Lean interpreter and differential testing

`lean/P4blo/` is about 3,700 lines of Lean, toolchain 4.34.0 pinned by
`lean/lean-toolchain`. It decodes the protobuf JSON mapping with Lean's
own JSON support, no protobuf library and no FFI, and mirrors the Python
package module for module, as its own docstrings say: `Value`, `Packet`,
`Tables`, `Env`, `Eval`, `Exec`, then `Interp` with the same three entry
points and the same calling convention. `Externs.lean` carries the Lean
models of `register`, `counter` and `checksum16`, pinned to the Python
ones. `Switch.lean` is the Lean twin of the Python switch, so that the
pipe compares whole packets in and out. `lake test` runs 181 checks on
the decoder, the index, every interpreter rule, the extern models and
the forwarder's vectors (`docs/status.md`).

Differential random testing is `python/p4blo/drt/`. A generator walks
the parser symbolically so that random packets reach deep states,
satisfies most `verify` conditions and leaves some to fail, truncates
some packets to reach `PacketTooShort`, and draws table entries and key
fields from a shared pool so that lookups hit. The Lean binary,
`p4blo-lean run`, answers one JSON line per case; extern state persists
across a case sequence on both sides. Two sides agree when their outputs
are equal as sequences of port and bytes, or when both report an error;
anything else is a divergence that prints as a replayable STF vector.

The recorded sweep is 18,000 random cases over nine programs with
zero divergences, before the tenth was added (`docs/status.md`); CI runs 200 per program on every
push (`.github/workflows/lean.yml`, `tests/test_drt.py`). One slice,
reproduced while writing this:

    nix develop -c uv run python -m p4blo.drt corpus/forwarder 500 --seed 1 \
        --lean lean/.lake/build/bin/p4blo-lean
    forwarder: seed 1, 500 cases, 500 agreed, 0 diverged, 0 errored on both sides

### The theorem

The one theorem is `P4blo.extract_emit` in `lean/P4blo/Theorems.lean`.
For any header type declared in a program and any list of field values
that fit its fields, bits of the declared widths and booleans, emitting
the header produces a bit string of the header's declared width; reading
that string back from the emitter's bytes at cursor zero yields the same
bits with the cursor advanced by the width; and extracting those bits
rebuilds the identical valid header. Its core is the inverse pair
`unpackFields_packFields` and `packFields_unpackFields`, stated over the
exact packing functions the Lean interpreter's emit and extract call.
It is proved in Lean 4.34 with core only, no Mathlib and no `sorry`;
`#print axioms` lists only `propext`, `Classical.choice` and
`Quot.sound`.

What it does not cover, as its module doc says: the monadic plumbing
around those calls, that is the lvalue read and write of the target,
`hs.next` and the `PacketTooShort` path; emit of structs and stacks; and
several headers in one packet. Parser determinism, the alternative
candidate named in `docs/design.md`, was not attempted.

## 4. The four claims

Each claim has one experiment and one way to fail. Here is each with its
result and, honestly, what would make it fail that has not been tested.

### Claim 1: the core is small and post-elaboration

The experiment: the schema and its contract fit in a few pages, and no
corpus program needs an escape hatch. The result: 669 lines of proto, and
ten programs authored with named elaborations only. `docs/coverage.md`
walks every production of SpecTec's IL: 177 rows, of which 84 are in, 38
are elaborated with the rewrite named, 26 are excluded by elaboration, 10
by thesis, 19 by scope, and none is undecided.

Untested: ten programs. They are small, they were chosen for the
constructs p4blo covers, and none has a constructor parameter, a
function, a header union or `int<N>`. The elaborated rows that no corpus
program has exercised, functions inlined, newtypes, named arguments, are
rulings, not performed rewrites. A p4c backend feeding real programs at
scale is the experiment that would fail this claim, and it has not been
run.

### Claim 2: the core is semantically complete for real programs

The experiment: corpus programs, printed to P4 under the v1model shim and
run through an external oracle, match the reference interpreter packet
for packet. The result: all 15 vector files pass on P4-SpecTec, with no
divergence to explain.

Untested: one oracle. BMv2, the optional second, has not been run. The
longest-prefix rule is not independently checked; the translation into
priorities supplies it. `flood` is checked by no oracle. Register state
crosses the boundary only as packet bytes, and the printed ternary
entries are not const. Where the reference and the oracle agree, they
agree on 46 `packet` lines across 14 files, every one of them a packet
of a few dozen bytes.

### Claim 3: a block is a function; an architecture is ordinary code

The experiment: two architectures of around fifty lines of Python with no
P4 in them, and every corpus program running under both unchanged. The
result: filter 45 lines, switch 50; every program runs under both, and
`tests/test_corpus.py` checks that the filter's fate decisions match the
switch's on every vector.

Untested: two architectures, both written to the same contract, and
both simple. Neither has egress-side processing, cloning, recirculation
or multicast groups, and no architecture with a different block set,
PSA's pairs of parsers and deparsers for instance, has been tried.
`flood` is compared between the two architectures and checked by nothing
else. The claim fails if a real architecture needs a hook a block cannot
express as a field of `M`, and that has only been argued, not shown.

### Claim 4: the semantics is mechanized and agrees with the reference

The experiment: a Lean interpreter, differential random testing with zero
unexplained divergences, and one theorem. The result: 18,000 cases, zero
divergences; 181 Lean checks; `extract_emit` proved with core Lean only.

Untested: random programs. Only the inputs are random; the programs are
the nine corpus programs plus one mixed program in `tests/test_drt.py`
that adds masked and range select cases and an exact table. Constructs
no corpus program holds, `Mux`, `Lookahead`, `Advance`, `RangeValue`,
`Apply.hit`, the saturating operators, the comparisons, the boolean
operators and the bool casts, are covered by unit tests on the Python
side and by the differential loop only where the mixed program reaches
them (`docs/coverage.md`, last section). The Lean interpreter was also
written to mirror the Python one; their agreement shows that the prose
in `docs/semantics.md` can be implemented twice the same way, not that
the prose is right. The oracle checks rightness, and it covers less.
The theorem covers one header through the emitter and back, not the
interpreter loop around it.

## 5. What p4blo is not

It is not fast, and does not try to be. It does not run existing P4
source; there is no P4 text parser, the printer goes the other way. It is
not P4Runtime, not a hardware target, not a p4c backend, not a browser
playground, and not a replacement for any tool.

A community version would build, first, a p4c backend that emits p4blo,
by 4ward's route: run p4c's frontend and midend, then emit protobuf. That
turns nine programs into p4c's whole test suite, which is the experiment
claim 1 needs.

Second, `int<N>`. It is in every prior IR and in core P4; it is out of
v0 because no corpus program needed it and it doubles the arithmetic
rules. It is one more `Type` kind and a signed variant of each rule.

Then the rest of the by-scope list from `docs/coverage.md`, each an
additive change to the schema: varbit and the length form of `extract`;
header unions; value sets; `return` and `exit`; `for` with `break` and
`continue`; `string` and string literals; signed literals;
`packet_in.length()`; static extern methods; mutable initial entries and
per-entry `const`; object initializers and abstract extern methods;
SpecTec's fixed-size arrays over non-header elements; and annotations
beyond the three with semantic residue. What is out by thesis stays out:
intrinsic metadata, packet fate as externs, action profiles and
selectors, direct counters and meters, the `range` and `optional` match
kinds, clone and recirculate as operations. Those are the architecture,
and the point of the proposal is that they live in a contract beside the
IR, not inside it.

## 6. What it took

One day. The repository's 134 commits all carry the date 2026-09-22,
from 00:21 to 08:44 local time, under one author, with a set of agents
doing the building in isolated worktrees, 20 of which were merged back,
and Claude Fable 5.1 named as co-author on the agent commits. Each build
step ended with something that could fail, and the work was reviewed
twice by an independent, read-only agent: after step 1, kept at
`docs/notes/reviews/step1.md` with 14 reproducers, 8 confirmed defects
fixed on main and the rulings it forced written into
`docs/semantics.md`; and after step 5, over everything that landed
since, kept beside it. Every choice the design did not already settle is a
dated entry with its reason in `docs/decisions.md`, and a survey preceded
each pick: `docs/notes/prior-art-ir.md` for the schema,
`docs/notes/corpus-candidates.md` for the corpus.

## 7. Where to look

The reading order from `README.md`.

1. `docs/design.md`: what p4blo is, why, and how each claim is tested.
2. `proto/p4blo/v0/p4blo.proto`: the IR, normative for syntax. Read it
   with `docs/semantics.md`, the closed behaviors.
3. `corpus/forwarder/`: the tutorial forwarder as a p4blo program,
   authored in the Python eDSL, with its IR golden and test vectors.
   Every corpus directory has a README naming what was elaborated away.
4. `python/p4blo/interp/`: the reference interpreter, written to be read
   as an explanation of P4's core.
5. `lean/P4blo/`: the same semantics in Lean, normative for meaning.
6. `docs/coverage.md`: every construct of P4-SpecTec's elaborated IL and
   its status in p4blo.
7. `docs/decisions.md`: every choice made while building, with its
   reason.
