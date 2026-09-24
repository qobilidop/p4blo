# Complete Lean-authored forwarder review

Final review: clear; chronological investigation follows below. The running
full integration gate remains separately attributed, not claimed complete here.

2026-09-23. Read-only candidate
`/Users/qobilidop/my/work/p4blo-lean-forwarder`; reviewer owns this report only.

## Structural inspection and initial independent checks

Read the complete Forwarder, ForwarderProof, ForwarderTests, ForwarderMain
and Python conformance test modules. The authored Program preserves the
existing corpus's actual behavior: IPv4 validity gates ingress; non-IPv4
packets pass on default port zero; TTL zero wraps; source MAC becomes the old
destination MAC; checksum recomputation still occurs after a table miss drops
the packet. Raw parser/action/table/extern construction is honestly exposed
as assembly rather than a verified frontend.

The public invalid-IPv4 theorem is properly bounded to execution of the
actual ingress body with its actual index and initialized frame. It proves
identical whole Run, not merely packet equivalence. The frame construction
uses the actual initialization and source-zero correspondence, not a callback
asserting success. Arbitrary invalid header stored contents are permitted;
this is not whole-program value validity or parser/pipeline correctness.

Independent fresh axiom queries for all seven new roots reported exactly
the existing standard three axioms. Compiled userTests exited 0, including
24 invalid-state cases, two checksum-after-drop cases and four direct
in-memory public-switch packet cases. No candidate rebuild was performed.

## Confirmed Python observation survivor

The initial 15 Python tests observed packets and one checksum side effect,
but not the full state covered by the invalid-header Lean theorem. A scoped
process-local mutation of actual `stmt.execute_one` delegated normally and
then, for each MyIngress conditional, assigned
`env.vars['meta'].fields[0] = Bits(9, 7)`.

Independent execution of the entire original file: 15 passed, actual fault
executed 40 times, process exit 0. Thus a genuine unintended metadata write
survived the current packet checks. The owner is adding direct full-state
body/control observations and a retained regression for this survivor.

An earlier attempt hooked `stmt.run_block`; it executed zero times through
the public control entrypoint, so its passing tests are explicitly NOT mutant
survival evidence. Public control imports `execute` directly; the successful
probe targeted its actual `execute_one` dispatch instead.

Also requested fail-closed handling in the fixed-program observer: strict
duplicate-rejecting JSON, nonempty stderr rejection and negative fixtures.
The initial `compare_and_save` handled returned mismatch reports but not a
ProtocolError carrying its retained report; the owner will ensure those
failures also save complete input before failing. These are test-observer
changes, not production semantics changes.

Final disposition awaits those fixes, independent reruns, and the documented
actual source/proof mutations with restoration. No whole forwarding, table
selection, parser, checksum or architecture theorem is inferred here.

## Final repair and evidence review

The pending statement above is historical. Independently inspected the final
test changes and ran all 50 focused cases: exit 0, 0.80 seconds. The 24 direct
Python cases now execute the actual body using a real Env.for_block, comparing
detached type-tagged complete Env contents before and after. The retained
actual execute_one ingress-write mutant still survives the weak packet DRT
and exact ARP answer, then is rejected by the strong state observation.
Cursor integer-to-float, installed-entry clearing, index, scope and mutable
extern corruption controls also pass their required rejection checks.

Strict duplicate-rejecting reply parsing, exact port types, empty stderr and
ProtocolError report retention are now tested. The latter is explicitly a
transport-unit regression, not a semantic Lean fault. The complete-state
observer covers the finite constructed profile; it is not a theorem that all
possible Python objects or arbitrary host environments are observed.

Inspected the actual isolated campaign logs. Wrong header selection fails
the unchanged invalid_guard proof at its arbitrary Ethernet-value goal, while
the exporter alone compiles and the independent Program identity check fails.
Wrong default, reordered MAC assignments and wrong checksum destination all
compile the default audits and are rejected by full independent Program
identity. These are application-intent failures, not interpreter divergence;
the narrower invalid-input theorem correctly survives those three faults.

The actual Python SUB replacement with saturation produces a clean packet
mismatch: port 2 on both sides, TTL/checksum 0011a3d0 versus ff11a4cf, no
interpreter/protocol error. Inspected the failing selected-test/live-replay
and successful restored-replay logs. Independently checked both retained
bundle copies are identical, 27697 bytes, SHA-256
`27376cf7dfe17455b40b849323b35186b471c0b432b01495aa7bd3d9dc0b9c4b`.
Loaded inputs equal the tracked authored Program and exact edge_case(0), ports
4 and seed 0; independently replayed against the restored candidate binary:
one agreement, zero both-error cases, exit 0.

Independent individual cmp commands confirmed restored authored source,
proof source and production Python expr.py match candidate bytes; the latter
also has empty tracked diff in the isolated tree. Fresh executions of both
exporters match at 6085 bytes with SHA-256
`c1f7c1c16d10c1c11f536cb0a5ff54a42fd11d6a2c30c8a4ac06633d6adc4669`.
Inspected restored full Lean/native success and final required-conformance
log: 867 passed, 1570 deselected. Those gate results are owner-executed;
focused tests, proof queries, initial compiled native execution and restored
artifact checks above were independently executed by this reviewer.

No remaining blocker found in the bounded checkpoint. The durable note
correctly separates the original fixture calibration, proof rejection,
compiled wrong-intent detection, state-only survivor/repair, and actual
Python–Lean packet mismatch. Complete corpus authoring plus these checks is
useful application progress, not full pipeline verification. The follow-on
action plan must also remember actual ingress.locals is empty: checksum
writes hdrChecksum directly, so no real checksum temporary should be assumed.

### Final nonvacuity guards

Independently inspected the final two assertion additions: the module fixture
requires the five known STF filenames as a subset (new vectors remain allowed),
and every collected STF must contain at least one packet request before DRT
or fixed-runner comparison. Both close silent coverage-loss paths without
changing semantics or weakening any existing expectation. Clear.

Inspected owner final logs: focused 50 passed (0.79 seconds), Ruff, formatting
and Pyright all successful. No Lean source/binary changed. The already-running
full gate collected the prior test revision; it is not evidence for these two
new guards. Root's post-integration full gate must cover the final files.
