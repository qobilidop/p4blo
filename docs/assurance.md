# Assurance

The delivered guarantees, supported inputs and exact premises of p4blo's
proofs, tests, external comparisons and deliberate faults. A test count or
theorem name alone does not establish a broader guarantee. [Design](design.md)
explains the intended architecture; [workflows](workflows.md) explains how to
run the checks. [Historical release evidence](#release-evidence) describes
its own revisions and must not be read as validation of a changed checkout.

## The claim

For the documented profile below, the independent Python implementation
and the executable Lean specification agree across a reproducible
conformance suite, independently checked examples and a reviewed
catalogue of intentional faults. Formal verification covers only the
architecture-free core IR. Architecture adapters, concrete extern families
and applications are tested executable code. Remaining trust boundaries,
known divergences and excluded features are explicit.

This is tested conformance, not a proof that Python is equivalent to
Lean. Test, proof and mutation counts are not probabilities of
correctness. Not claimed: universal Python correctness, all-P4
expressiveness, IR minimality proofs, universal Python validator soundness or
termination, full parser, checksum, firewall or forwarding-pipeline
proofs, a fully verified Lean frontend, or correctness of the Lean and
Python runtimes, compilers, JSON parsers or protobuf implementations.

## Supported profile

The profile is the current v0 IR, not all P4 and not arbitrary hostile
input. Lean's [abstract syntax](../spec/ir/P4bloIR/IR.lean) and executable
semantics are authoritative; the [protobuf schema](../spec/ir/proto/p4blo/v0/p4blo.proto)
defines transport syntax; [semantics.md](ir-semantics.md) records the closed
behaviors; [p4-spec-coverage.md](p4-spec-coverage.md) walks P4 construct by construct.

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
- Core library declarations: types, errors, extern signatures and instances,
  and any number of blocks of each kind. Architecture binding separately
  checks selected H/M roots, exports and their calling convention. Host table
  configuration is separate; decoding it does not establish validity.

The executable builtin extern profile is register, counter, checksum16,
CRC16/ARC and CRC32/ISO-HDLC. Family suffixes do not relax signature or
width checking. Registers and counters persist across packets; CRCs are
byte-aligned, stateless and return the full result. Custom externs need
their own model and evidence; the extensible Python registry does not
verify arbitrary plugins.

The IR is architecture-free. End-to-end regression uses the supplied
scoped v1model adapter and its declared metadata and port rules, not
every P4 architecture. The twelve-program corpus includes Python ports of
the forwarder and persistent tutorial Bloom firewall, which admits Bloom
false positives and is not exact connection tracking. The corpus and the
three public [applications](../examples/README.md) run their Python-authored
IR on both interpreters. No application or whole-pipeline proof is claimed.

### Inputs and validation

Execution evidence concerns finite programs accepted by the Python
validator, with matching builtin bindings, appropriate architecture
exports and valid host installations. Lean's core library checker,
`P4bloIR.Validity.check` (`p4blo-lean check-library`), follows the Python
validator's order and diagnostic codes; it is proved sound for the
declarative rules `Validity.Valid`, not complete, and it is not proved
equivalent to the Python validator. The architecture separately checks
H/M roots and exports with the tested `P4bloArch.Bindings.check`;
`p4blo-lean check` checks the combined assembly. This architecture checker
has no formal soundness guarantee. The Python and Lean checkers are compared
program by program, on every corpus program, example, a sample of both
DRT families and the shared [validator scenario catalog](../tests/support/validator_scenarios.py)
used by the Python validator tests: they
agree on acceptance and on the first diagnostic code, up to wire problems
that Lean's decoder rejects before any rule runs. For a program the
checker accepts, `P4bloIR.Progress` proves that the step machine never
reaches an `InterpError`, under four premises: the extern binding obeys
the extern contract, the table entries come from a successful
installation, the initial run fits the block kind, and every value the
architecture passes for a block parameter has the parameter's type. The
extern contract remains a caller assumption: no theorem discharges it for
the supplied families. `Installed.build` establishes `InstalledOk` when it
succeeds; typed entry values and the initial machine must satisfy the core
theorems' premises. Architecture entry functions are tested, not proved.
Under these premises, a finite control or deparser run ends in success:
parser errors come only from parser runs. Codec tests intentionally include invalid-but-representable
IR; successful decoding is not permission to execute it.

Python's eDSL and P4 importer are tested frontends, not verified translations.
A human can still write the wrong intended program, so independent expected
examples check intent separately.

### Wire contract

The supported interchange profile is the canonical protobuf JSON emitted
by `p4blo.arch.wire.dump_json` for architecture assemblies (and
`p4blo.ir.dump_json` for core libraries), the corresponding snake-case
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
theorem, and the Lean runner has no semantic fuel counter. Progress is
proved under the extern, installation and typed-entry premises above:
a finite run of a valid program ends in success or in a parser error the
program declares, never in an `InterpError`, and only a parser run ends in
the error; that every run is finite remains open. The DRT client
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
| `CodecLaws` through Action/Block | Production encoder/decoder left inverses over JSON values under v0 uint32 representability, checked by `spec/ir/P4bloIRTest/CodecProofAudit.lean` | Text parsing, protobuf correctness, semantic validity, version negotiation |
| `ScalarLaws` | Selected saturation, shift and branch laws of the actual evaluator | Completeness of the scalar semantics against P4 |
| `DeviationLaws.header_equal_invalid`, `header_equal_valid_invalid`, `header_equal_invalid_valid`, `header_equal_valid`, `header_equal_valid_iff`, `equal_bits_iff`, `equal_bool_iff`, `equalList_cons`, `equalList_scalar_iff`, `evaluate_eq`, `evaluate_eq_invalid_headers`, `evaluate_eq_valid_invalid`, `evaluate_ne`, `evaluate_ne_eq`, `evaluate_ne_eq_error` | Header `==` compares validity first; two valid headers whose fields are bits and booleans of matching kinds are equal exactly when every field value is the same; bits compare by width and value, booleans by value; `!=` gives the negation of `==` on every kind of operand and fails exactly when `==` does; all on `Value.equal` and through the evaluator from any run | That the compared headers share a type; fields that are themselves compound; anything about SpecTec, whose rule differs here |
| `DeviationLaws.elementOf_out_of_range`, `evaluate_index_out_of_range`, `readLValue_index_out_of_range`, `writeLValue_index_out_of_range`, `writeLValue_member_out_of_range` | An index at or past the size reads the zero invalid header of a declared element type; a write through it, or through one of its fields, leaves the run the operand reads left | Index and element typing; a field write whose path reads change the run |
| `DeviationLaws.evaluate_lastIndex`, `lastIndex_empty`, `lastIndex_nonempty`, `evaluate_last_empty`, `evaluate_last_nonempty` | `lastIndex` is `nextIndex - 1` in `bit<32>`, so `2^32 - 1` at zero; on a stack of fewer than `2^32` elements whose evaluation leaves the run unchanged, `hs[hs.lastIndex]` reads the zero invalid header when `nextIndex` is zero and element `nextIndex - 1` when `1 ≤ nextIndex ≤ size` | The parser-only rule; that the eDSL or a frontend elaborates `hs.last` this way |
| `DeviationLaws.pushFront_eq`, `pushFront_spec`, `pushFront_clamp`, `popFront_eq`, `popFront_spec`, `popFront_clamp` | Exact elements, size and `nextIndex` of the resulting stack value, including a count above the size | The statement's write back through its lvalue; the pop laws assume `nextIndex` at most the size |
| `DeviationLaws.evaluate_shl_large`, `evaluate_shr_large`, `wrap_zero_value` | A shift by the width or more evaluates to zero through the evaluator, whatever the amount's width or size | Shifts below the width |
| `DeviationLaws.toBytes_padded`, `write_fits` | The emitter's bytes are the emitted bits followed by fewer than eight zero bits, for every emitter whose value fits its width; one fitting write keeps that premise | Deparser traversal; what an architecture appends; the induction over a sequence of writes, which is not stated as a theorem |
| `DeviationLaws.enterState_revisit`, `enterState_first`, `enterState_again`, `step_state_revisit`, `step_advances`, `reaches_advances`, `reaches_cursor_le`, `recorded_empty`, `recorded_of_advances`, `reaches_recorded`, `enterState_advanced`, `enterState_no_consumption`, `reaches_state_revisit` | Entering a state at the cursor recorded for it raises `ParserTimeout` with the run unchanged, and the machine step starts unwinding with it; no machine step moves the cursor back or drops a record, so a state re-entered without timing out finds the cursor advanced, and a state re-entered in the same block with the cursor unchanged times out whatever ran in between, including a sub-parser's return and second application | That a loop without consumption reaches the second entry; parser termination |
| `DeviationLaws.lookup_hit`, `lookup_miss`, `lookup_longest_prefix`, `lookup_longest_lpm`, `keyValueMatches_exact`, `keyValueMatches_lpm`, `keyValueMatches_ternary`, `prefixLength_eq`, `prefixLength_single`, `rank_lpm` | A hit runs an installed entry matching every key with the longest total prefix, or the largest priority with a ternary key; a miss means none matches and runs the current default. The helpers are pinned: an exact value matches its number, an `lpm` value exactly the keys agreeing with it on their top prefix bits, a ternary value exactly the keys agreeing under its mask; the prefix length is the sum of the installed `lpm` lengths | Installation's canonicity and tie rejection; that the installed entries came from `Installed.build`; key positions past an entry's own key count, which the match does not check |
| `DeviationLaws.zero_bits`, `zero_boolean`, `zero_error`, `zeroHeader_eq` | The zero-value primitives return zero bits, `false` and `NoError`; a declared header's zero is invalid with zero fields | Frame construction; zero enums, structs and stacks beyond their header elements |
| `Execution.Finishes.sound` | A finite trace of the actual step function determines the actual runner's result | Existence of a trace for every valid program |
| `Build.build_ok` | `Index.build`'s maps read back into the program's lists: every declaration found by name is the program's under that name, program-level names share one namespace, and each block's scope is built from that block | That every name the program declares is found (only the directions later proofs use are stated) |
| `Validity.check_sound` | A program the Lean checker accepts satisfies `Validity.Valid`, the validator's rules as relations over the program and its index | That the checker accepts every `Valid` program; agreement with the Python validator, which `tests/conformance/semantics/test_lean_agrees_validity.py` tests on finite inputs |
| `Validity.progress`, `Steps.machineOk`, `finishes_documented`, `drive_documented` | From a well-formed machine of a `Valid` library, every step finishes with success or with a parser error the library declares, or reaches another well-formed machine; so no reachable machine and no finite run carries an `InterpError`. Premises: the extern binding obeys `ExternContract`, the entries satisfy `InstalledOk`, the initial run fits the block kind | Termination; the checks the entry points in `P4bloArch.Interp` make outside the machine |
| `Validity.progress_outside_parser`, `Steps.machineOkNP`, `finishes_outside_parser`, `finishes_kind`, `parse_error_is_parser`, `dispatch_np` | A control or deparser machine of a `Valid` program that starts without a fault or a pending parser state steps without any fault, so a finite run ends in success; with `finishes_documented`, a parser error ends only a parser run. Premises: those of `progress` | Termination |
| `Validity.build_installedOk` | A successful `Installed.build` satisfies `InstalledOk`: every lookup in a program table succeeds and selects an action of its block with data of its parameters' types | That installation succeeds for given host entries |
| `Validity.initial_ok`, `entryFrame_ok` | The machines the entry points start, from `Frame.forBlock` with each parameter set to a value of its type, are well formed | That the values an architecture passes are typed |

The checked theorem inventories are
[`spec/ir/P4bloIRTest/ProofAudit.lean`](../spec/ir/P4bloIRTest/ProofAudit.lean) and
[`spec/ir/P4bloIRTest/CodecProofAudit.lean`](../spec/ir/P4bloIRTest/CodecProofAudit.lean).
Their exact statements and premises, not the labels above, define what is
proved. The gate builds both Lean packages with `lake build --wfail`, so a
warning fails the build. The core audits pin transitive axiom sets; `sorry`,
custom axioms and native-evaluation escapes cannot silently replace a proof.
There is no architecture, concrete extern, authoring-language or application
proof inventory in the active project.

## What is tested

Differential tests check the Python implementation against the executable
Lean definitions the proofs are about; external oracles separately check
this account of P4, subject to the documented closed behaviors and adapter
limits. The two implementations share wire syntax and nothing else.

### Evidence by semantic family

Paths are repository-relative. Tests marked `lean` use the shared
`lean_binary` fixture and are discovered by the required real-Lean gate.
Names alone do not classify a dependency.

| Family | Independent tests and generated comparisons | Scoped proof, external evidence and limits |
|---|---|---|
| Scalars, operators, lazy branches | `impl/python/tests/interp/test_expr.py`; `tests/conformance/execution/test_drt_programs.py` exercises every scalar operator, width edges, truth tables, cast/slice/mux, faulting unselected lookahead and shrinking typed programs | Core scalar typing theorems above; not complete P4 scalar semantics. Corpus oracles cover selected uses, not every operator. |
| Aggregates, fields, validity, stacks | `tests/conformance/execution/test_drt_aggregate_copy.py`, `impl/python/tests/interp/test_expr.py`; strict detached state, alias faults and native/Python stack checks | Field laws under explicit premises; stack and subparser corpus programs supply selected oracle behavior. |
| Calls, initialization, normal return | `tests/conformance/execution/test_drt_call_copy.py` generated in/out/inout with live alias, out-initial and copyback faults; `tests/conformance/semantics/test_lean_call_copyback.py` checks parser-error copyback | Core validity/progress under explicit premises; generated cases and independent expectations test call behavior. |
| Packet, parser, deparser | `impl/python/tests/interp/test_parser.py`, `impl/python/tests/interp/test_deparser.py`, `spec/arch/P4bloArchTest/Interp.lean`; corpus DRT, masked and range select in `impl/python/tests/drt/test_drt.py`, byte cuts and persistent sequences in `tests/programs/corpus/tutorial_firewall/test_firewall_boundaries.py` | `extract_emit`; pinned corpus and original-firewall oracles. Lookahead, advance, revisit timeout and subparser-error copyback have separate expected answers, not a parser theorem. |
| Tables, actions, host installation | `impl/python/tests/interp/test_tables.py`, generated configurations in `impl/python/tests/drt/test_drt.py`, `tests/programs/corpus/forwarder/test_forwarder_tables_semantics.py`, `tests/programs/corpus/forwarder/test_forwarder_action_semantics.py`, `tests/programs/corpus/forwarder/test_forwarder_apply_semantics.py`; strict configuration, full-state and default-hit observations | Core lookup laws; exact, LPM and ternary corpus and five explicit BMv2 application profiles, not every table family or a forwarding proof. |
| Persistent extern state | `tests/conformance/execution/test_drt_stateful_programs.py` shrinking sequences, `tests/conformance/execution/test_drt_state.py`, `impl/python/tests/arch/test_externs.py`, `impl/python/tests/arch/test_extern_families.py`, `impl/python/tests/arch/test_crc.py`; firewall full-array collision, truncation and generated-flow tests | Original BMv2 checks packets and complete arrays. Concrete externs and firewall behavior are tested, not proved. |
| Architecture outcomes and errors | `tests/conformance/execution/test_drt.py` drop, unicast, ports and error reasons; `tests/programs/test_v1model.py` six-stage/drop/state witnesses; `impl/python/tests/drt/test_drt_replay.py` matching-error policy; corpus v1model vectors | Supplied architecture profiles only. Success, drop, parser rejection, execution error and protocol failure stay distinct. |
| Serialization and observation | `tests/conformance/codec/test_codec_{leaves,expr,lvalue,stmt,declarations,tables,parser,blocks,program,entries}.py`; `tests/conformance/codec/test_wire_decimal.py`; `impl/python/tests/drt/test_drt_protocol.py`, `impl/python/tests/drt/test_drt_replay.py`; strict JSON type and frozen-state regressions | Component codec laws through Action/Block; independent wire answers catch roundtrip-preserving defects. Complete library, architecture export and host Entries fixtures cover the public conversions; rejected-host sequences are tested, not proved. |
| Authored applications | Exact-golden source comparisons and independent packet and full-state profiles in `tests/programs/corpus/forwarder/test_forwarder*_semantics.py` and `tests/programs/corpus/tutorial_firewall/test_firewall*.py`; twelve-program corpus rebuild and typecheck; `tests/programs/examples/` for the three applications | Python-authored examples execute on both interpreters. Application construction and behavior are tested, with no application or whole-pipeline proof. |

### Corpus programs

Each corpus program under `tests/programs/corpus/` has its typed eDSL source, its
generated golden, a README with provenance and contract, and STF vectors
replayed on the Python interpreter, on Lean and on both oracles.

| Program | Source | Vectors | Oracles |
|---|---|---|---|
| forwarder | p4lang tutorial basic; Python source reproduces the golden | 5 hand-derived STF files plus TTL0/1 and invalid-control state checks | both, checksum included |
| acl | p4c `ternary2-bmv2` | p4c STF, 6 adds, 4 packets | both |
| stacks | p4c `header-stack-ops-bmv2` | p4c STF, 15 packets | both |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | p4c STF, 1 packet | both |
| stateful | p4c `issue1097-2-bmv2` plus own cross-packet vectors | 2 p4c packets plus 6 of ours | both |
| csum16 | p4c `issue655-bmv2` | p4c STF, 6 packets | both |
| parser_error | p4c `parser_error-bmv2` | p4c STF, 2 packets | both |
| verify_error | p4c `issue1824-bmv2` | p4c STF, 1 packet | both |
| priority | p4c `table-entries-priority-bmv2`, priorities by the specification's numbering | p4c STF, 3 packets, two expectations re-derived from P4-SpecTec | both for the golden; BMv2 on p4c's own source routes two packets the other way by p4c's numbering [below](#known-disagreements-with-the-oracles) |
| register_bounds | own program | 9 hand-derived packets | SpecTec; two packets diverge on BMv2 by the register rule [below](#known-disagreements-with-the-oracles) |
| tutorial_firewall | pinned p4lang tutorial solution; Python source reproduces the golden | connection and Bloom-collision vectors, byte cuts, generated host-policy sequences | original BMv2 packets and all 8192 register cells at 30 prefix boundaries; SpecTec controls pass, its CRC and mask defects are classified below |
| vlan_gateway | original homepage example | one STF file with 11 packets; a 53-request packet, diagnostic and counter sequence in Python and Lean | both for packets; counters checked by independent expectations |

The public applications under `examples/` (router, stateful firewall,
load balancer) each have goldens, vectors and independent expectations
under `tests/programs/examples/`, replayed on both oracles by the shared catalogs,
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

The same generated families also run on the P4-SpecTec simulator
through the printer and the v1model shim, so the primary oracle judges
generated programs and not only the corpus: `tests/oracles/generated.py`
derives programs and cases deterministically from seeds in six families
(scalar expressions, parser conditions, stateful sequences, aggregate
copies, sub-block calls, and corpus programs with random entries and
packets), and `tests/oracles/test_oracle_generated.py` runs sixty of them in CI.
A larger local campaign over seeds 0 to 1099, 1,100 programs and 3,851
vectors, passed with no unexplained disagreement; every non-pass was one
of two [classified simulator defects](oracle-discrepancies.md), the shift
limit and the table mask, each accepted only by a classifier that checks the exact failure
and, for the mask, that the simulator agrees with the corrected model.

The adequacy criterion is coverage of the semantics' own rules, not test
counts. `P4bloIR.Coverage` names 157 rules: one per case of the
evaluator, the statement executor, the parser's transitions, table
matching and calls, and one per closed behavior of
[ir-semantics.md](ir-semantics.md) that a machine step can observe.
`p4blo-lean run` reports, in every reply, the rules the request
exercised. An observer in the architecture package steps the
proof-visible machine and classifies each configuration before its step,
reusing the real evaluator for operand values and never an outcome;
`Execution.Finishes.sound` guarantees that such a trace determines the
runner's result, and the reply itself still comes from the runner.
`tests/conformance/execution/test_drt_coverage.py` reruns the retained campaigns at fixed seeds
and compares the unhit rules with `tests/conformance/coverage/unhit-tags.json`, which
lists every rule the generators cannot reach yet with the gap behind it;
a rule that stops being hit fails the test, and the list may only shrink.
It is empty: two menu-driven program families (`p4blo.drt.families`), a
control family and a parser family whose every choice is a labelled
decision, reach all 157 rules, and the retained campaigns hold them at
fixed seeds beside the corpus and the earlier families. A guided driver
(`python -m p4blo.drt guided`) steers those choices by the tags each run
reports, weighting the options aimed at a rule while that rule is unhit.
It also counts the pairs of a rule with each decision of the program that
reached it, ESMeta's one-feature-sensitive criterion, but does not steer
by them. It is deterministic by seed, and every program it makes is
validated and compared like any other. `tests/conformance/coverage/guided-measurement.json`
records what the steering is worth, over sixteen seeds of 200 programs per
family, guided against uniform choice. Guided campaigns hit every target
rule that all runs reach in fewer programs: a mean of 14 against 20 in the
control family, fewer in 14 of 16 seeds, and 35 against 74 in the parser
family, fewer in 15 of 16. They reach the same rules, and the program that
first hits the last new rule moves little: in the control family it comes
earlier in only 8 of 16 seeds. An earlier weighting also rewarded options
for new pairs. On the same seeds it hit the control family's last new rule
later than uniform choice did, a mean of 73 programs against 57, and it
was removed. Witness pairs in
`spec/arch/P4bloArchTest/fixtures/` pin each rule's condition from both
sides, one program that must report it and one that must not, with the
recorded reply anchoring what actually ran. The witness checks constrain both positive and negative classification,
separately from packet agreement.

The conformance corpus under `tests/conformance/` is the Lean semantics'
answers kept as data: one fixture per input, each a program, an ordered request
sequence from fresh extern state and the reply Lean gave to each request,
with outputs, diagnostic or error, complete extern state and rule tags.
The inputs are every corpus program and example with its STF vectors, two
contract fixtures that record rejected installs, unicast, drops, redirection attempts and
out-of-range ports, the
DRT's generated entries and packets at two seeds per program, and 36
seeds of the generated program families. `tests/conformance/test_fixtures.py`
checks the Python interpreter against every fixture with no Lean process,
comparing as the DRT compares, and in the `lean` marker gate answers every
fixture again on Lean and requires identical bytes. The corpus is a test
suite that needs neither implementation to be present, and a third
implementation can consume it the way Python does. It is not a proof and
says nothing beyond its inputs: it records what Lean answered, not that
the answers are P4's, which the oracles and the rule ledger address. When
the semantics changes an answer, the behavior is written in the semantics
documents first, and the fixtures are then refreshed deliberately, which
re-answers the recorded requests without regenerating any input, and
their diff reviewed; see `tests/conformance/README.md`.
Validator-only rules, installation checks, extern families and the
architecture's own rules are outside this inventory. 
### Checked against P4-SpecTec

Every closed behavior of the semantics page cites the SpecTec rule that
decides it at the pinned commit and is classed *same*, *refines
undefined*, *deviates* or *not representable*;
`tests/repository/test_ledger.py` and
`tests/oracles/test_spectec_rules.py` check the shape, the names and the
classes. [ledger-xref.md](ledger-xref.md) lays every entry out in one
generated table, with its class and each cited rule linked to its line
in the pinned SpecTec source. Separately, [p4-spec-coverage.md](p4-spec-coverage.md#rule-coverage-on-p4-spectec)
records which of SpecTec's architecture-free rules the corpus and
examples make the pinned simulator fire, with every unhit in-scope rule
excluded by hand with a reason or listed as reachable and not yet
exercised. A hit rule is exercised, not verified equivalent.

The corpus and examples are also compared with SpecTec block by block,
with nothing architectural in between. A patch applied at build time adds
a `p4blo` architecture to the pinned simulator that runs one parser,
control or deparser per request on given headers, metadata, entries and
extern state ([tests/oracles/README.md](../tests/oracles/README.md#the-block-runner)).
`tests/oracles/test_oracle_block.py` repeats every block run of every vector on it
and compares each block's outputs with the reference interpreter's: a
parser's headers, metadata, bits consumed, acceptance and error; a
control's headers and metadata; a deparser's bytes and bit count; and
every register and counter cell after each block. A parser's `error` on
accept is `NoError` by construction on both sides, so its comparison has
content only for a rejecting parser. Two documented differences are strict expected
failures, each explained entirely by a model of the simulator applied to
the reference interpreter, which checks the interpreter's own answer
before changing only what the deviation names: [odd-byte CRC32](oracle-discrepancies.md#crc32-of-an-odd-number-of-bytes) on
the tutorial firewall's Bloom filter cells that the pipeline comparison
cannot see; and the stored fields and index a stack keeps after
`push_front` and `pop_front`, the ledger's *deviates* entry, which no
deparser emits. The blocks' inputs are chosen by chaining them as the
parser/ingress/deparser projection does, so the comparison covers what the vectors reach, not every
input a block accepts; entries for a table name two blocks declare, or a
`$valid$` key name, are refused rather than resolved differently.
Table installation is still the STF runner's encoding on both runs, and
the extern families run on the simulator's V1Model implementations; the
block runner compares block semantics, not an architecture or the wire
format.

The IL bridge translates the instantiated P4 program IR exported by
P4-SpecTec, using the supported rows of [p4-spec-coverage.md](p4-spec-coverage.md).
It retains six distinct v1model stages, with explicit exclusions for unsupported
standard metadata and services such as the native `verify_checksum` intrinsic.
Core parser `verify` remains supported. The original checksum donor that uses
that intrinsic is now an explicit exclusion test, rather than a silently
ignored verification step.

Original-source comparisons preserve stage boundaries and account for the
canonical examples' documented authoring choices. In particular, some authored
examples compute stateless checksums in ingress while their donors use the
checksum stage. The printer/importer round trip checks stage structure and
packet/extern-state observations; it does not claim byte-identical IR because
user metadata and native standard metadata remain distinct. Nine supported originals retain exact normalized IR equality after the
checked projections spelled out in the tests. Fourteen accepted round trips
check all 100 STF requests and 336 generated requests; the priority round trip
remains excluded. Original P4/STF sources remain pinned and unchanged. These
are finite tests, not a verified frontend or a general P4 compiler claim.

The six-stage acceptance witness tests noncommuting mutations, payload,
ingress/egress drop suppression and persistent late-stage state on Python,
Lean and P4-SpecTec. BMv2 rejects arbitrary checksum-control operations and
stateful deparser operations, so a separate portable witness uses an empty
VerifyChecksum stage, native checksum update, and header-only emission. It
checks exact output bytes and same-stage egress state on both oracles. The
runtime serializes packets; this does not model BMv2's cross-pipeline scheduling.

## Known disagreements with the oracles

The [discrepancy guide](oracle-discrepancies.md) owns exact pins, native
reproducers, observed answers, governing contracts and selected behavior.
These differences bound what oracle agreement establishes:

- CRC32 input length and table masks follow the documented algorithms and
  language rules; the pinned P4-SpecTec implementations differ.
- Out-of-range register reads are unspecified by v1model. p4blo chooses zero;
  BMv2 preserves the destination. That difference does not make BMv2 wrong.
- Const-entry annotations in the p4c donor are a nonstandard extension.
  p4blo follows portable language ordering and prints explicit priorities.
- Egress destination and initialization follow the pinned BMv2 profile:
  ingress selects the destination, egress starts with a zero drop request,
  and a non-drop egress assignment cannot redirect output.
- Shift-size limits, partial-byte payload composition, header equality and
  stack operations further restrict P4-SpecTec comparisons. Its STF adapter
  supplies LPM priorities, so BMv2 supplies the independent longest-prefix
  check. Flood/multicast remains outside the supported profile.

Correctness suites restrict strict expected failures to diagnosed mismatches;
characterization suites assert each oracle's complete distinct answer.
Unrelated errors and newly corrected answers fail the old classification.
Native probes retain their source. Printed programs bind the documented
architecture profile explicitly, including the local egress drop request and
saved output destination. None of these exceptions grants blanket agreement
for an architecture or a program.

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
application source faults. The retired Lean authoring, application-proof,
architecture-proof and execution-certificate experiments are historical
only. Their sources and precise earlier boundaries remain recoverable at
[revision `5ee52d9`](https://github.com/qobilidop/p4blo/tree/5ee52d90f19d5d5a81bf972a115298ae167e691b),
including `impl/lean/ASSURANCE.md` and that revision's assurance page.
They supply no guarantee for the current project.

## Release evidence

The [immutable release record at the documentation baseline](https://github.com/qobilidop/p4blo/blob/de6aa7d9437ffc65c413b0adda7d3f8c558f84f6/docs/assurance.md#release-evidence)
preserves the milestone and application-checkpoint commands, results, exact
revisions, oracle identities, skips and remote CI links. It includes components
and proof scopes since retired. Those results establish only what ran at their
recorded revisions; the current guarantee is the scoped claim above, and a
changed checkout needs its own applicable validation.
