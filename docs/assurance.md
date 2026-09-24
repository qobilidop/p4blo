# Assurance

What p4blo claims, for which programs, and what backs each claim: proofs,
tests, external oracles and deliberate faults. Read this before inferring
a guarantee from a test count or a theorem name. The finite assurance
milestone closed on 2026-09-23 at code revision `3148a52`; the
[release evidence](#release-evidence) at the end records exactly what
ran then and at the application checkpoint that followed; later
checkpoints are recorded in the agent status file.

## The claim

For the documented profile below, the independent Python implementation
and the executable Lean specification agree across a reproducible
conformance suite, independently checked examples and a reviewed
catalogue of intentional faults. Selected foundational properties are
proved in Lean. Remaining trust boundaries, known divergences and
excluded features are explicit.

This is tested conformance, not a proof that Python is equivalent to
Lean. Test, proof and mutation counts are not probabilities of
correctness. Not claimed: universal Python correctness, all-P4
expressiveness, IR minimality proofs, whole-program validator soundness or
termination, full parser, checksum, firewall or forwarding-pipeline
proofs, a fully verified Lean frontend, or correctness of the Lean and
Python runtimes, compilers, JSON parsers or protobuf implementations.

## Supported profile

The profile is the current v0 IR, not all P4 and not arbitrary hostile
input. Lean's [abstract syntax](../ir/P4bloIR/IR.lean) and executable
semantics are authoritative; the [protobuf schema](../ir/proto/p4blo/v0/p4blo.proto)
defines transport syntax; [semantics.md](ir-semantics.md) records the closed
behaviors; [coverage.md](coverage.md) walks P4 construct by construct.

### Surface

- Types: unsigned fixed-width bits, booleans, named errors and enums,
  headers, structs and fixed-size header stacks. Valid bit widths are
  positive; wire-representable zero widths are not thereby valid programs.
- Expressions: literals, variables, field and stack reads, last index,
  validity, three unary and nineteen binary operators, casts, slices,
  concatenation, lazy Boolean and conditional selection, parser lookahead.
  Arithmetic wraps or saturates as specified; comparisons are unsigned.
- Statements: assignment, conditional, action, block and extern calls,
  table apply with optional hit destination, validity changes, stack push
  and pop, extraction, advance, verify and emit. Block kind restricts
  where each is legal.
- Parsers: named states, direct and select transitions, exact, masked,
  range and don't-care keysets, accept and reject, the no-consumption
  revisit rule. Calls copy inputs and outputs; parser-error copyback is
  part of the specified behavior.
- Tables: exact, LPM and ternary keys, literal action data, const entries
  and defaults, host-installed entries and default overrides,
  longest-prefix and largest-priority selection. A miss can run an action
  while `hit` remains false.
- Program declarations: types, errors, extern signatures and instances,
  blocks, exported roles and the headers/metadata contract. Host table
  configuration is separate from the program; decoding it does not
  establish validity.

The executable builtin extern profile is register, counter, checksum16,
CRC16/ARC and CRC32/ISO-HDLC. Family suffixes do not relax signature or
width checking. Registers and counters persist across packets; CRCs are
byte-aligned, stateless and return the full result. Custom externs need
their own model and evidence; the extensible Python registry does not
verify arbitrary plugins.

The IR is architecture-free. End-to-end regression uses the supplied
switch and filter adapters and their declared metadata and port rules, not
every P4 architecture. The twelve-program corpus includes complete Python
and Lean ports of the forwarder and the persistent tutorial Bloom firewall,
which admits Bloom false positives and is not exact connection tracking.
The three public [applications](../examples/README.md) are Python-authored
and run on both interpreters; they have no Lean-authored counterpart or
whole-pipeline proof.

### Inputs and validation

Execution evidence concerns finite programs accepted by the Python
validator, with matching builtin bindings, appropriate architecture
exports and valid host installations. Preparation and indexing on the
Lean side are checked by tests, not proved equivalent to the whole Python
validator. Codec tests intentionally include invalid-but-representable
IR; successful decoding is not permission to execute it.

Selected typed Lean expressions and commands have checked lowering and
execution theorems under explicit context, index and frame premises. The
complete applications also assemble raw IR; neither that assembly nor
Python's complete eDSL is a verified frontend. A human can still write
the wrong intended program in either language, so independent expected
examples check intent separately.

### Wire contract

The supported interchange profile is the canonical protobuf JSON emitted
by `p4blo.ir.dump_json` for programs, the corresponding snake-case
protobuf conversion for entries, and the matching Lean encoders: known
fields, full enum names, numeric uint32 values, booleans, ordered arrays,
explicit decimal-string bit and key values and at most one populated oneof
alternative. Default scalars and empty arrays are omitted; optional
message presence matters, since an absent optional is not a present empty
message.

The adapters also accept selected noncanonical inputs, tested explicitly,
but there is no unrestricted accepted-input or text-parser equivalence
claim:

| Input form | Current boundary |
|---|---|
| Missing or null fields | Lean treats null as absence, then applies field defaults; a missing required oneof or enum still fails. Independent codec fixtures test these cases. |
| Decimal bit and key strings | Nonempty ASCII digits; leading zeros may normalize. Empty, missing, null, signed, hex and JSON numbers are not decimal-string values. Python may reject later during validation or installation. |
| uint32 strings | Lean accepts decimal strings as an extension; canonical output uses numbers. Bounds are below 2^32, independent of semantic width or capacity validity. |
| Numeric enums, camelCase aliases | Not the cross-language contract; Python protobuf accepts forms the handwritten Lean adapter need not accept. |
| Unknown object keys | Python's public protobuf parsing rejects them; Lean ignores them. Do not carry required semantics in unknown keys or infer forward compatibility. |
| Duplicate keys, non-JSON constants | Not supported interchange. The DRT envelope, reply and replay parsers reject them; no theorem covers arbitrary production parser inputs. |

There is no wire-version negotiation. Codec laws are JSON-value left
inverses under explicit representability premises, not proofs about
protobuf, text parsing, semantic validation or intended mapping, and a
paired wrong encoder and decoder can satisfy a roundtrip law, which is
why independent literal and constructor answers accompany every law.

### Errors, state and limits

A successful drop is an empty output list, not an error. Parser rejection
is distinct from its error name (an explicit reject carries `NoError`);
architecture policy decides what follows. Decode, validation, binding and
installation errors are distinct from packet execution faults and from
harness protocol errors. Comparisons check error reasons and diagnostic
presence; matching errors do not make a generated-valid-input campaign
successful.

A host configuration rejected before packet execution must not execute
that packet or change persistent extern state. This is not transactional
rollback of an accepted program that mutates state and then faults.
Stateful tests retain the complete request prefix, not just a final
packet. Detailed diagnostics need not be formatted identically in both
languages.

This is a trusted-input development and simulation profile, not a
hardened service. uint32 wire bounds can still describe impractically
large allocations; JSON nesting, host memory and runtime limits apply.
There is no proved global resource bound or validated-program termination
theorem, and the Lean runner has no semantic fuel counter. The DRT client
defaults to a ten-second request deadline; a transport deadline is a
harness failure, never a semantic `ParserTimeout`.

### Exclusions and trust

Signed and variable-width integers, header unions, general loops, return
and exit, value sets, architecture-specific match kinds and services, and
complete P4 elaboration remain outside this profile. Syntax presence alone
is not tested semantic coverage.

Trust includes the Lean kernel for theorems; the compiled Lean runtime and
compiler for executable comparisons; Python and its runtime; protobuf and
JSON libraries; observers, test generators, oracle adapters and pinned
external tools. Default theorem audits reject unexpected axioms but cannot
prove that a theorem states the desired requirement. Independent expected
values, external oracles and actual mutations reduce shared mistakes; none
yields a probability of correctness.

## What is proved

Lean owns abstract syntax, validity and meaning; protobuf owns wire
syntax. The executable Lean semantics includes parser errors and explicit
extern state, and proofs establish named properties of those definitions
under stated assumptions. Each row is a distinct obligation, not an
interchangeable confidence score.

| Evidence | Exact boundary | Does not establish |
|---|---|---|
| `extract_emit` | Packing and extraction round trip under its stated premises | Whole parser or deparser correctness |
| `FieldLaws.read_declared`, `update_declared` | Exact field primitive results, validity and siblings, whole-Run preservation under actual nominal declarations and exact container shape | Stored-value typing, persistent nested lvalue writes, global validity |
| `ScalarTyping.check_sound` | Every accepted closed scalar expression evaluates at its inferred type and preserves the initial Run | Variables, aggregates, whole-program validation, Python |
| `ScalarTyping.checkIn_sound`, `checkIn_complete` | Contextual scalar checking is sound under actual typed-frame agreement and complete for its relation under a well-formed context | Aggregates, statements, whole-program validation, Python |
| `Scalar.lower_typed_in`, `evaluate_lower_in` | Typed source expressions lower to contextually typed IR and evaluate to the exact independent source value with the Run unchanged, under exact frame agreement | Intended surface elaboration, arbitrary initialization, writable statements, serialization |
| `Scalar.Env.frame_matches`, `Modes.scope_agrees` | Every well-formed source context has a constructively related runtime frame and declarations | Validity of an arbitrary block or program |
| `Scalar.Cmd.steps`, `execute_correct`, `CmdWith.steps_with` | Finite scalar and field command bodies follow the actual machine, produce exact source values, preserve unrelated state and leave arbitrary continuations unexecuted, under explicit block-frame premises | Aggregate paths beyond the discharged leaves, calls, global validity, Python equivalence |
| `Fields.Ref.evaluate`, `write_matches`, `validities_set`, `Fields.lower_typed`, `evaluate_lower` | Exact aggregate-store correspondence for nested scalar reads and writes, validity and unrelated state, under nominal, index, frame and permission premises | A general aggregate checker, initialization, intended surface selection |
| `FrameInitialization`, `CallEntry`, `CallReturn`, the guarded control call | Actual frame creation over every scope entry, four-root call entry, fixed-profile normal return and one observer-free whole control call, as bounded named transitions | All calls, parser-fault unwinding, the observer statements, complete applications |
| `ForwarderTables.lookup_correct`, `ForwarderApply.run_correct`, the selected action | Five installed route shapes, their actual application and hit timing, the forwarder's invalid-control identity | Parsing, checksum maintenance, architecture fate, other configurations |
| `TutorialFirewall` initialization, invalid body and Bloom insertion | All nine initialized roots; whole-Run identity of the invalid-IPv4 body; exact two-write insertion preserving both arrays and unrelated state | Readback, drop composition, hash bounds, exact connection tracking |
| `CodecLaws` through Action/Block | Production encoder/decoder left inverses over JSON values under v0 uint32 representability, checked by `ir/CodecProofAudit.lean` | Text parsing, protobuf correctness, semantic validity, version negotiation |
| `ScalarLaws` | Selected saturation, shift and branch laws of the actual evaluator | Completeness of the scalar semantics against P4 |
| `Execution.Finishes.sound` | A finite trace of the actual step function determines the actual runner's result | Existence of a trace for every valid program |
| `ExecutionCertificate.check_sound` | Accepted bounded checks bind the supplied initial machine, observation and claim to the runner | Codec correctness, universal Python equivalence, unobserved final state |

The checked theorem inventories are [`ir/ProofAudit.lean`](../ir/ProofAudit.lean),
[`ir/CodecProofAudit.lean`](../ir/CodecProofAudit.lean) and
[`lean/UserProofAudit.lean`](../lean/UserProofAudit.lean); their exact
statements and premises, not the labels above, define what is proved.
Warnings are errors in both Lean packages, and the audits check the
transitive axiom sets of advertised theorems, so `sorry`, custom axioms
and native-evaluation escapes cannot silently replace a proof. The exact
obligations, exclusions and mutation experiments of the scalar and field
authoring work are in [`lean/ASSURANCE.md`](../lean/ASSURANCE.md); the
forwarder, firewall and call theorems are stated in their modules under
`lean/P4blo/` and audited in `lean/UserProofAudit.lean`.

## What is tested

Differential tests check the Python implementation against the executable
Lean definitions the proofs are about; external oracles separately check
this account of P4, subject to the documented closed behaviors and adapter
limits. The two implementations share wire syntax and nothing else.

### Evidence by semantic family

Paths are repository-relative. Tests named `test_lean_agrees*` are
discovered by the required real-Lean gate; similarly named native or
Python unit suites are not automatically differential tests.

| Family | Independent tests and generated comparisons | Scoped proof, external evidence and limits |
|---|---|---|
| Scalars, operators, lazy branches | `tests/test_interp_expr.py`; `tests/test_drt_programs.py` exercises every scalar operator, width edges, truth tables, cast/slice/mux, faulting unselected lookahead and shrinking typed programs | Scalar typing and lowering theorems above; not complete P4 scalar semantics. Corpus oracles cover selected uses, not every operator. |
| Aggregates, fields, validity, stacks | `tests/test_drt_aggregate_copy.py`, `test_lean_edsl_field_commands.py`, `test_lean_edsl_header_reads.py`; strict detached state, alias faults and native/Python stack checks | Field laws under explicit premises; stack and subparser corpus programs supply selected oracle behavior. |
| Calls, initialization, normal return | `tests/test_drt_call_copy.py` generated in/out/inout with live alias, out-initial and copyback faults; scoped entry and return suites compare full state and pending continuations | Bounded named transitions, not all calls or parser-fault unwinding. |
| Packet, parser, deparser | `tests/test_interp_parser.py`, `test_interp_deparser.py`, `ir/Tests/Interp.lean`; corpus DRT, masked and range select in `test_drt.py`, byte cuts and persistent sequences in `test_firewall_boundaries.py` | `extract_emit`; pinned corpus and original-firewall oracles. Lookahead, advance, revisit timeout and subparser-error copyback have separate expected answers, not a parser theorem. |
| Tables, actions, host installation | `tests/test_interp_tables.py`, generated configurations in `test_drt.py`, `test_lean_forwarder_tables.py`, `test_lean_forwarder_action.py`, `test_lean_forwarder_apply.py`; strict configuration, full-state and default-hit observations | Forwarder lookup and application laws for five shapes; exact, LPM and ternary corpus and five explicit BMv2 application profiles, not every table family. |
| Persistent extern state | `tests/test_drt_stateful_programs.py` shrinking sequences, `test_drt_state.py`, `test_externs.py`, `test_extern_families.py`, `test_crc.py`; firewall full-array collision, truncation and generated-flow tests | Firewall initialization and Bloom insertion; original BMv2 checks packets and complete arrays. No generic extern theorem. |
| Architecture outcomes and errors | `tests/test_drt.py` drop, flood, ports and error reasons; `test_drt_replay.py` matching-error policy; corpus switch and filter vectors | Supplied architecture profiles only. Success, drop, parser rejection, execution error and protocol failure stay distinct. |
| Serialization and observation | `tests/test_codec_{leaves,expr,lvalue,stmt,declarations,tables,parser,blocks,program,entries}.py`; `test_wire_decimal.py`; `test_drt_protocol.py`, `test_drt_replay.py`; strict JSON type and frozen-state regressions | Component codec laws through Action/Block; independent wire answers catch roundtrip-preserving defects. Complete Program, Export and host Entries fixtures cover the public conversions; rejected-host sequences are tested, not proved. |
| Authored applications | Exact-golden source comparisons and independent packet and full-state profiles in `test_lean_forwarder*.py`, `test_lean_firewall*.py`, `test_firewall*.py`; twelve-program corpus rebuild and typecheck; `tests/examples/` for the three applications | Complete examples execute in both languages; selected proofs do not verify raw construction or the whole pipeline. |

### Corpus programs

Each corpus program under `tests/corpus/` has its typed eDSL source, its
generated golden, a README with provenance and contract, and STF vectors
replayed on the Python interpreter, on Lean and on both oracles.

| Program | Source | Vectors | Oracles |
|---|---|---|---|
| forwarder | p4lang tutorial basic; Python and Lean sources equal the golden | 5 hand-derived STF files plus TTL0/1 and invalid-control state checks | both, checksum included |
| acl | p4c `ternary2-bmv2` | p4c STF, 6 adds, 4 packets | both |
| stacks | p4c `header-stack-ops-bmv2` | p4c STF, 15 packets | both |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | p4c STF, 1 packet | both |
| stateful | p4c `issue1097-2-bmv2` plus own cross-packet vectors | 2 p4c packets plus 6 of ours | both |
| csum16 | p4c `issue655-bmv2` | p4c STF, 6 packets | both |
| parser_error | p4c `parser_error-bmv2` | p4c STF, 2 packets | both |
| verify_error | p4c `issue1824-bmv2` | p4c STF, 1 packet | both |
| priority | p4c `table-entries-priority-bmv2` | p4c STF, 3 packets | both |
| register_bounds | own program | 9 hand-derived packets | SpecTec; two packets diverge on BMv2 by the register rule [below](#known-disagreements-with-the-oracles) |
| tutorial_firewall | pinned p4lang tutorial solution; Python and Lean sources equal the golden | connection and Bloom-collision vectors, byte cuts, generated host-policy sequences | original BMv2 packets and all 8192 register cells at 30 prefix boundaries; SpecTec controls pass, its CRC and mask defects are classified below |
| vlan_gateway (added after the milestone, at `38d740e`; no Lean-authored counterpart) | original homepage example | one STF file with 11 packets; a 53-request packet, diagnostic and counter sequence in Python and Lean | both for packets; counters checked by independent expectations |

The public applications under `examples/` (router, stateful firewall,
load balancer) each have goldens, vectors and independent expectations
under `tests/examples/`, replayed on both oracles by the shared catalogs,
and ten reviewed source faults that both interpreters' independent
expected-answer tests reject.

### Differential and generated testing

Required CI fails if Lean cannot run. Every differential reply carries
the complete logical extern state, as hexadecimal strings, so a
state-only fault cannot hide behind matching packets. A failure is saved
as a versioned JSON bundle with the program and the whole request sequence
from fresh extern state, replayable with `python -m p4blo.drt.replay`.
Generated programs vary scalar expressions inside validated packet-visible
programs, stateful programs with independent register and counter bounds,
aggregate copies, sub-block calls and changing host policies, all with
type-preserving shrinking; invalid generated programs fail rather than
being filtered away.

## Known disagreements with the oracles

Every known disagreement is a strict expected failure restricted to a
dedicated exception that matches the exact vector, status and observed
mismatch. An oracle error, an unrelated mismatch or a corrected oracle
fails the test instead of hiding behind the exception. No adapter changes
an input to manufacture agreement.

**BMv2: an out-of-range register read.** p4blo's closed behavior is that a
read at or beyond a register's size yields zero and a write there is
ignored. BMv2 agrees about the write but leaves the read's destination
untouched, so a field keeps its parsed value. P4 leaves this
implementation-defined; the difference is documented, not resolved, and
shows on exactly the two `register_bounds` packets whose out-of-range read
destination is non-zero. The [BMv2 adapter README](../tests/oracle/bmv2/README.md)
has the diagnosis.

**Pinned P4-SpecTec: odd-byte CRC32.** SpecTec's simulator pads every hash
input to an even byte count by prepending a zero byte, which changes CRC32
of odd-length input. CRC16 has initial value zero and is unaffected.
Independent known answers from a hand-written P4 probe, confirmed by BMv2:

| Exact input bytes | Correct CRC32 (BMv2) | Pinned SpecTec |
|---|---|---|
| `0a0000010a0000023039005006` | `7dd597c3` | `a31aa886` |
| thirteen zero bytes | `0f744682` | `d1bb79c7` |
| ASCII `123456789` | `cbf43926` | `ce7745fe` |
| `01` | `a505df1b` | `36de2269` |
| `0001` | `36de2269` | `36de2269` |

The [pinned implementation](https://github.com/kaist-plrg/p4-spectec/blob/2730cfd9e74048bb5439da0f8afcef124079a064/p4spec/lib/backend-sim/hash.ml)
calls `pad_right_to_16` for every algorithm. This matters for the
firewall: its 104-bit tuple hashes to register index 1987 on BMv2 and 2182
on SpecTec, yet simple packet sequences pass on both, because a consistent
wrong hash preserves collision relationships. That is why primitive known
answers and complete register observations are required, and why BMv2 is
the CRC authority until upstream resolves the padding.

**Pinned P4-SpecTec: LPM and ternary mask construction.** Its
[table interface](https://github.com/kaist-plrg/p4-spectec/blob/2730cfd9e74048bb5439da0f8afcef124079a064/spec/9-arch/9.1-table-interface.watsup)
casts the key's base where it should cast the computed mask, so an exact
`/32` route `10.0.0.2` admits `10.0.0.3`. Python, Lean and unchanged
original BMv2 drop the route miss; SpecTec forwards it. Two strict tests
observe this on the unchanged original firewall and on the printed IR.

The first oracle also lacks a longest-prefix rule; the translation in
`tests/oracle/run.py` supplies prefix lengths as priorities, so SpecTec
confirms outputs while BMv2 independently decides longest prefix, const
entries and runtime ternary priorities. Neither oracle can observe `flood`.

## Adversarial checks

Agreement between two implementations is only evidence if a wrong
implementation would disagree. Deliberate faults are introduced in
isolated worktrees on both sides, on observers and on codecs, and each is
recorded as killed by a semantic disagreement, survived, or invalid because
it did not build. A compiler failure is never a semantic kill. Survivors
become new focused tests or broader generators; the regression is kept,
the mutation is not.

The finite acceptance command replays a reviewed catalogue from tracked
fixtures with no dependence on old artifacts:

```sh
uv sync --locked
scripts/check-lean.sh
uv run python scripts/check-assurance.py
```

It reconstructs three complete inputs pinned by SHA-256 of program,
requests, ports and seed (an empty forwarder table with drop default, two
overlapping routes, and the four-request firewall connection sequence),
runs ten selected Python and observer regressions by exact test identity,
then compiles a real Lean CRC32 fault in a cache-free copy of the
specification and requires exactly three state-only disagreements with
restored replay agreement. It then swaps parser and control in the codec
name table and in the test-only observer, shows that weak equality
survives, and requires exactly six independent native anchors to reject
the wrong mapping. Every scratch source is restored and rehashed; any
build failure, skip, timeout or incomplete restoration fails the command.
Evidence goes to a new directory under `.artifacts/assurance/`. This is
bounded sensitivity evidence, not a mutation score.

Recorded campaigns beyond the catalogue killed eager branches, state-only
out-of-bounds and persistence faults, copy aliasing, skipped copyback,
CRC XOR faults that preserve packets but permute register indices, and
the application source faults above. The user-package proof experiments
in `lean/ASSURANCE.md` distinguish proof rejection from compiled wrong
intent from runtime mismatch.

## Execution certificates

A narrow experiment connects proofs to actual execution.
`ExecutionCertificate.check_sound` proves that an accepted observation
equals the Lean execution result for the supplied initial machine; the
checker reexecutes the machine with a budget, and exhaustion is a verdict,
not a language fault. The fixed program reads register `r[0]`, increments
its `bit<8>` value, writes it back and increments counter `k[0]`.

```
uv run python -m p4blo.drt.certificate create --register 41 --counter 9 -o claim.json
uv run python -m p4blo.drt.certificate verify claim.json
```

The Python adapter decodes the exported program unchanged, builds its own
index and bindings, runs the production interpreter and serializes what
actually happened; only the compiled Lean checker's `accepted` verdict is
acceptance. The artifact carries the complete program as protobuf JSON
and canonical hexadecimal state; the decoded AST must equal the fixed
example. Running the checker trusts the compiler, runtime, codecs and
observation adapter, and a JSON artifact is not a kernel proof. Tampered
programs, initial values, results and budgets are rejected in
`tests/test_drt_certificate.py`. Generalizing beyond the fixed fragment
needs explicit validity and observation contracts first.

## Release evidence

Milestone 1 closed at code revision `3148a52f2212238da00fe76ebe8eab81d86b6023`
from a fresh detached checkout with no Python environment, Lean build
directories or retained artifacts, in the pinned environment. Installed
toolchains and external oracle caches were shared: this is a clean project
checkout, not a claim that every external tool was rebuilt from source on
a new machine. The corpus then had eleven programs. P4-SpecTec was checked
at commit `2730cfd9` (executable SHA-256 `c75a2129…`); BMv2 used the
immutable image
`sha256:2b255b53…`. Builds finished before their consumers ran.

| Gate | Result |
|---|---|
| `uv sync --locked` | exit 0 |
| `scripts/check-lean.sh` | exit 0; default audits, 627 spec checks, user-package tests |
| `P4BLO_REQUIRE_LEAN=1 scripts/check.sh` | exit 0; 4793 passed, five exact expected discrepancies, one optional local XDP skip |
| `P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees` | exit 0; 2886 passed, no skips |
| `uv run python scripts/check-assurance.py` | exit 0; fresh builds, all selected detections, restored replays |

The five expected discrepancies are the CRC known answers on SpecTec for
original and printed programs, the firewall route miss on SpecTec for
original and printed programs, and the BMv2 register vector, each under
its dedicated classifier. The one skip is the optional local XDP compile
image; the separate required XDP workflow ran without skips. Remote
workflows at the same revision: [CI](https://github.com/qobilidop/p4blo/actions/runs/35960620942),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/35960620935),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/35960620865),
[BMv2](https://github.com/qobilidop/p4blo/actions/runs/35960620846),
[XDP](https://github.com/qobilidop/p4blo/actions/runs/35960620983).
An independent release review checked the JUnit identities, source and
mutant hashes and replayed the retained inputs.

XDP is a separate compile-only experiment with pinned sources and its own
required workflow; it establishes no kernel execution and plays no role in
this P4 profile. The application collection that followed the milestone
was checked the same way on 2026-09-24 at `c94336d`, with 4837 tests
passing under the same skip and discrepancies.
