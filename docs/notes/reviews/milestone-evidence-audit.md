# Finite milestone evidence audit

Read-only audit: the existing semantic evidence is substantive; close the
four concrete packaging/domain gaps below. No new proof/application ladder
is needed. This is not exhaustive coverage or completed release-gate evidence.
Inspected current IR/source/test families at milestone scope 169a2c9 without
executing tests, rebuilding binaries or changing implementation.

## Concrete closeout gaps

1. **Top-level wire boundary.** Component codec laws and independent fixtures
   now reach Action/Block. Export/Program and host TableEntries/Entries still
   need the small complete-field/default/error matrix already required by the
   milestone. Include nested field propagation and valid-invalid-valid request
   sequences proving rejected installation never runs the packet or changes
   persistent extern state. Existing decimal request tests are useful seeds,
   not coverage of every top-level field. No universal host-codec theorem is
   needed.
2. **Input-domain clarity.** Python public protobuf JSON parsing rejects
   unknown fields by default; the actual Lean adapter ignores unknown keys.
   Canonical generated JSON and arbitrary accepted JSON are different claims.
   Name the supported cross-language wire profile and explicitly classify
   aliases, null/defaults, unknown keys and parser limits. Do not silently
   convert existing accepted-input differences into a universal parity claim.
3. **Reproduction packaging.** The existing retained regression cases are
   substantive, but temporary campaign logs/ignored bundles are not a fresh
   checkout interface. The finite acceptance command should reconstruct a
   selected named inventory from tracked fixtures, verify identity/nonempty
   counts, replay it and run selected live-fault sensitivities. It need not
   reproduce every historical raw log or byte count.
4. **Current coverage documentation.** coverage.md's final corpus narrative
   is stale (established programs labeled in flight; operations listed as absent
   despite the firewall). Replace that prose with current evidence links rather
   than assuming a source-node count proves meaningful execution coverage.

## Existing evidence to reuse, not rebuild from scratch

| Semantic family | Existing independent evidence anchors | Finite matrix check |
| --- | --- | --- |
| Scalar/Boolean/expression evaluation | test_drt_programs: every operator, width edges, truth tables, shrinking typed programs, faulting unselected branches | Record lazy branch/error behavior separately from ordinary pure expressions; do not mark lookahead entirely missing |
| Aggregate storage and calls | test_drt_aggregate_copy, test_drt_call_copy, scoped entry/return/field tests with strict frozen state and live alias faults | Separate normal completion/copy isolation from error unwind; locate an actual cross-language fault-unwind case or add one small fixture if absent |
| Packet/parser behavior | Corpus parser/stacks, test_firewall_boundaries, ir/Tests/Interp.lean and test_interp_parser.py; test_drt.py masked/range profile and test_drt_programs faulting-lookahead branches | Successful lookahead/advance, revisit timeout and subparser error copyback have explicit native and Python known answers; do not mislabel these separate unit suites as direct DRT |
| Tables/actions | Existing exact/LPM/ternary corpus DRT, installation generators, real Forwarder table/action/application profiles and BMv2 cases | Keep parser range matching distinct from unsupported table range matching; distinguish default miss action from explicit NoAction |
| Persistent externs | test_drt_stateful_programs, register/counter/CRC tests, original-firewall full-array prefixes and generated sequences | Link width/OOB/read-after-write and valid-malformed-valid sequence observations; reuse complete arrays, not only packets |
| Whole-switch outcomes/errors | test_drt flood/drop/port rules and explicit error reasons, diagnostic-presence checks | Preserve distinction between parser rejection, runtime error, diagnostic and successful drop; matching errors are not valid-case success |
| Wire and harness | Codec suites, wire-decimal tests, test_drt_protocol/replay plus strict JSON/type regressions | Identify missing top-level inputs above; preserve protocol crash/hang/duplicate handling and original complete request sequence |
| Authored examples | Complete exact-golden Python/Lean forwarder and persistent firewall, original and printed oracle profiles | State the typed Lean fragment versus raw Program assembly and original-source versus printer-mediated oracle boundaries |

Specific existing parser anchors were checked: Python test_lookahead_reads_without_consuming_and_a_header_result_is_valid,
test_advance_skips_bits, test_revisiting_a_state_without_consuming_is_parser_timeout
and test_sub_parser_error_copies_back_before_propagating have corresponding
named native checks in ir/Tests/Interp.lean. test_drt.py additionally executes
masked/range-select profiles; generated expression tests already execute
faulting-lookahead short-circuit paths. No unexplained parser discrepancy was
identified here. A direct shared-program parser/unwind fixture could improve
assurance, but lack of every evidence kind in every matrix cell is not by
itself a release blocker.

Do not turn this pass into a new general parser, termination, validator or call
proof project. Operator, call-copy, persistence and architectural-outcome
generators already exist and should not be reimplemented for new counts.

## Exact proof and oracle qualifications for the matrix

- ScalarTyping.checkIn_sound/checkIn_complete and Scalar.evaluate_lower_in
  cover their stated scalar/context fragment. FieldLaws.read_declared and
  update_declared, Fields.evaluate_lower and concrete field-command execution
  extend selected aggregates/commands under actual index/frame premises. None
  proves the complete Python validator or all raw application assembly.
- FrameInitialization, plain CallEntry/CallReturn and GuardedControlCall provide
  actual finite call/initialization boundaries, not general parser-fault unwind
  correctness. The independent copy/alias tests are separate Python evidence.
- ForwarderAction.run_correct, ForwarderTables.lookup_correct (under its actual
  installed family), and ForwarderApply.run_correct cover independent named
  application policies. They do not cover the parser/checksum/full pipeline.
  The parked ForwarderIngress work must not appear as a landed proof.
- TutorialFirewallProof's invalid-IPv4 identity and Bloom.insertion cover named
  actual-body/state boundaries. Persistent Python/Lean/oracle execution supplies
  the broader application evidence. Parked readback is not a required missing
  theorem. Bloom false positives remain intended behavior, not exact tracking.
- CodecLaws and the Declaration/Table/Parser/BlockCodecLaws modules establish
  actual JSON-value encoder/decoder left inverses under numeric representability.
  They do not prove text-parser equivalence, every accepted wire form, validity,
  intended enum mapping, or any execution property. Independent descriptor and
  malformed/default tests are essential precisely because paired faults can
  satisfy these laws.
- test_oracle.py/test_oracle_bmv2.py cover printed corpus programs through pinned
  adapters; test_firewall.py, test_crc.py and original firewall boundary/generated
  profiles add original-source controls. test_apply_packets_bmv2 covers five
  complete forwarding profiles. Keep exact SpecTec CRC/mask and BMv2 bound
  divergences qualified. Not every operator has an external oracle witness;
  never fill that cell with a unit test or claim all architectures.

The row labels above identify existing theorem families, not new requirements
to broaden their premises. The final matrix should link the exact public names
from the checked audit modules when presenting an individual theorem.

## Error, resource and validator boundaries

The suite already distinguishes diagnostic presence, error reasons, parser
rejection, drop and valid-case success; tests/test_drt.py and
test_drt_replay.py explicitly reject treating matching errors as successful
valid-input campaigns. Protocol crash, hang, malformed reply and cleanup have
separate tests/test_drt_protocol.py coverage. Preserve these categories in the
profile rather than normalizing failures into empty outputs.

Document the actual resource envelope instead of promising one that does not
exist: uint32 representability permits impractically large allocations and
recursive JSON can exceed host parser limits. Harness process deadlines are
not semantic ParserTimeout and do not prove general termination or resource
safety. A trusted, finite validated-program profile with stated operational
budgets is sufficient; hostile-input service hardening is not implicitly part
of this milestone. Any claimed controlled rejection must have its own concrete
test, not follow from a roundtrip law.

Python validator acceptance and Lean runtime/index preparation are not a proved
equivalent global validity relation. Invalid-but-wire-representable codec inputs
must remain in codec testing without being described as executable valid
programs. Source permission, storage existence and numeric wire bounds are
different assumptions. The accepted milestone already labels these limits;
the profile should make them visible at the public entry points.

## Suggested finite sensitivity catalogue

Choose approximately one representative per already demonstrated failure
mode, using existing retained tests: arithmetic wrap, lazy branch selection,
atomic packet cursor, aggregate/call-copy alias, persistent state-only fault,
table default/LPM choice, serialization paired mapping, and protocol/observer
corruption. Include at least one actual compiling Lean runtime fault checked
against Python, one actual Python fault, and one paired codec/observer survivor
rejected by independent literal/native evidence. Existing CRC state-only
campaign and codec enum challenges already provide candidates.

Define each selected case by exact tracked fixture, expected affected behavior,
detector and restoration check. Distinguish a compiled proof rejection from a
runtime mismatch and a valid-but-unintended fixture from runtime corruption.
The catalogue is finite sensitivity evidence, not a mutation-score threshold.
After its named checks, current-profile matrix, top-level interchange,
usability and final required gates are satisfied, stop.
