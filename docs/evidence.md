# Current-profile evidence matrix

This is a navigation map for [milestone 1](milestone-1.md), not a claim of
exhaustive testing. The [profile](profile.md) defines the supported domain.
The matrix identifies independent expectations and actual cross-language
comparisons separately; a blank proof/oracle boundary is not silently filled
by a test. Latest executed gates and exact revisions are in [status](status.md).

Paths in the table are repository-relative. `test_lean_agrees` tests are
discovered by the required real-Lean gate; the similarly named native/Python
unit suites do not automatically constitute a direct differential test.

| Family | Independent tests and generated comparisons | Scoped proof / external evidence and limits |
|---|---|---|
| Scalars, operators, lazy branches | `tests/test_interp_expr.py`; `tests/test_drt_programs.py` exercises every scalar operator, width edges, truth tables, cast/slice/mux, faulting unselected lookahead and shrinking typed programs | `ScalarTyping.checkIn_sound/checkIn_complete`, `ScalarLaws`, source `Scalar.evaluate_lower_in`; not complete P4 scalar semantics or Python equivalence. Corpus oracles cover selected uses, not every operator. |
| Aggregates, fields, validity, stacks | `tests/test_drt_aggregate_copy.py`, `test_lean_edsl_field_commands.py`, `test_lean_edsl_header_reads.py`; strict detached state, alias faults and native/Python stack checks | `FieldLaws`, `Fields.evaluate_lower` and field-command laws under explicit nominal/index/frame/permission premises; stack/subparser corpus supplies selected oracle behavior. |
| Calls, initialization, normal return | `tests/test_drt_call_copy.py` generated in/out/inout and live alias/out-initial/copyback faults; scoped entry/return suites compare full state and pending continuations | `FrameInitialization`, `CallEntry`, `CallReturn`, actual guarded control-call proofs are bounded named transitions, not all calls or parser-fault unwind. |
| Packet/parser/deparser | `tests/test_interp_parser.py`, `test_interp_deparser.py`, `ir/Tests/Interp.lean`; corpus DRT, masked/range select in `test_drt.py`, byte cuts/persistent sequences in `test_firewall_boundaries.py` | Selected `extract_emit` theorem; pinned corpus/original-firewall oracles. Lookahead, advance, revisit timeout and subparser-error copyback have separate native/Python expected answers, not a general parser theorem. |
| Tables/actions/host installation | `tests/test_interp_tables.py`, generated corpus configurations in `test_drt.py`, `test_lean_forwarder_tables.py`, `test_lean_forwarder_action.py`, `test_lean_forwarder_apply.py`; strict configuration/full-state/default-hit observations | `ForwarderTables.lookup_correct` covers five installed shapes; `ForwarderApply.run_correct` composes their actual actions/hit timing. Exact/LPM/ternary corpus and five explicit BMv2 application profiles, not every possible table family. |
| Persistent extern state | `tests/test_drt_stateful_programs.py` shrinking sequences, `test_drt_state.py`, `test_externs.py`, `test_extern_families.py`, `test_crc.py`; firewall full-array collision/truncation/generated-flow tests | `TutorialFirewall.Bloom` insertion and selected initialization/invalid-body laws. Original BMv2 firewall checks packets and complete arrays; no generic extern correctness theorem or exact connection tracking. |
| Architecture outcomes/errors | `tests/test_drt.py` drop/flood/ports/error reasons; `test_drt_replay.py` matching-error policy; corpus switch/filter vectors | Supplied architecture profiles only. No all-architecture theorem. Success/drop, parser rejection, execution error and protocol failure stay distinct. |
| Serialization and observation | `tests/test_codec_{leaves,expr,lvalue,stmt,declarations,tables,parser,blocks,program,entries}.py`; `test_wire_decimal.py`; `test_drt_protocol.py`, `test_drt_replay.py`, strict JSON/type and frozen-state regressions | Actual component `CodecLaws` through Action/Block, checked by `ir/CodecProofAudit.lean`; independent wire answers catch roundtrip-preserving defects. Complete Program/Export and host Entries fixtures cover public protobuf conversions; rejected-host sequences and strict raw configuration observers are tested, not universal codec/validator proofs. |
| Authored applications | Exact-golden source comparisons and independent packet/full-state profiles in `test_lean_forwarder*.py`, `test_lean_firewall*.py`, `test_firewall*.py`; twelve-program corpus rebuild/typecheck | Complete examples execute in both languages; selected source/lowering/application proofs do not verify all raw construction or the whole pipeline. Original-forwarder ingress-prefix and firewall-readback drafts are parked, not evidence. |

After the frozen milestone, the twelfth corpus program is the
[Python VLAN gateway](../tests/corpus/vlan_gateway). Its 53-request sequence
in `tests/test_vlan_gateway.py` has independent expected packets, architecture
diagnostics and complete admission-counter state, checked in Python and Lean.
Its STF vector runs on both P4 oracles, which observe packets only. No
whole-gateway proof or Lean-authored source is claimed. Current checks and
the source-mapped website walkthrough are recorded in [status](status.md).

The checked theorem inventories are [IR audit](../ir/ProofAudit.lean),
[codec audit](../ir/CodecProofAudit.lean) and
[user-package audit](../lean/UserProofAudit.lean). Their exact statements and
premises, not the row labels above, define what is proved.

## Corpus programs

| Program | Source | Vectors | Oracles |
|---|---|---|---|
| forwarder | p4lang tutorial basic; Python and Lean sources equal the golden | 5 hand-derived STF files plus TTL0/1 and invalid-control state checks | 5/5 on both, checksum included |
| acl | p4c `ternary2-bmv2` | p4c STF, 6 adds, 4 packets | 4/4 on both |
| stacks | p4c `header-stack-ops-bmv2` | p4c STF, 15 packets | 15/15 on both |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | p4c STF, 1 packet | both |
| stateful | p4c `issue1097-2-bmv2` plus own cross-packet vectors | 2 p4c packets plus 6 of ours | 8/8 on both |
| csum16 | p4c `issue655-bmv2` | p4c STF, 6 packets | 6/6 on both |
| parser_error | p4c `parser_error-bmv2` | p4c STF, 2 packets | both |
| verify_error | p4c `issue1824-bmv2` | p4c STF, 1 packet | both |
| priority | p4c `table-entries-priority-bmv2` | p4c STF, 3 packets | both |
| register_bounds | own program from the second review | 9 hand-derived packets | SpecTec passes; two packets diverge on BMv2 by the recorded out-of-range register rule, a strict xfail |
| tutorial_firewall | pinned p4lang tutorial solution; Python and Lean sources equal the golden | connection/Bloom false positives, byte cuts, generated host-policy sequences | original BMv2 packets and all 8192 register cells at 30 prefix boundaries; SpecTec controls pass, exact CRC/mask probes are strict expected discrepancies |
| vlan_gateway | original p4blo homepage example | one STF file with 11 packets; independent 53-request packet/diagnostic/counter sequence in Python and Lean | packet vectors pass both; counters checked by Python/Lean expectations |

The three public applications under `examples/` have their own goldens,
vectors and independent expectations under `tests/examples/`, replayed on
both oracles by the shared catalogs.

## Known disagreements, not hidden passes

Pinned P4-SpecTec has four exact strict CRC/mask expected discrepancies in
the original-source probes. BMv2 register out-of-bounds read leaves the old
destination, whereas this profile returns zero; the one exact vector is a
strict expected discrepancy. Passing control cases remain required. See
[CRC contract](crc-contract.md), [firewall analysis](evidence/firewall-port.md)
and [BMv2 adapter](../tests/oracle/bmv2/README.md). Arbitrary ProtoJSON acceptance
also differs as documented in the profile; that is outside canonical-wire
parity, not an unexplained runtime disagreement.

XDP is a separate compile-only experiment, with no kernel-execution evidence
and no role in this P4 milestone. Required P4 oracle unavailability cannot be
counted as a pass. CI selection and pins are in [workflows](workflows.md).

## Reproducible acceptance

The direct top-level fixtures and rejected-host state/packet-entry checks are
reviewed in interchange (`notes/reviews/milestone-interchange.md`, archived). The
[finite catalogue](evidence/milestone-adversarial.md) reconstructs selected input
bundles and checks actual Python, Lean, codec and observer faults with
`scripts/check-assurance.py`; setup failures never count as detections.
The six [quickstart](quickstart.md) snippet/API tests exercise both languages.
Final combined clean-checkout and remote gates pass at `3148a52`, as recorded
in the [completion report](evidence/milestone-1-completion.md) and its independent
review. The accepted finite milestone is complete.

The independent static audit (`notes/reviews/milestone-evidence-audit.md`, archived)
found these concrete closeout gaps, not a need for another general proof
project. Gate success, mutation sensitivity and theorem counts are distinct
evidence, never probabilities of correctness. Check off the finite milestone
only after the corresponding implementation and final gates actually pass.
