# Firewall byte-boundary review

Independent read-only review on 2026-09-23 of the test/document increment
in `p4blo-firewall-boundaries`, based on `50322dd`.

## Structural assessment

No correctness blocker found in the inspected tests. The scope is explicit:
every byte cut of one fixed 54-byte Ethernet/IPv4/TCP SYN, not all malformed
traffic, arbitrary bit cuts, options or architectures. Atomic extraction
expectations derive from the three header lengths, not either interpreter.
The incomplete TCP payload remains observable after routing, including at
length 48 where flags are present but extraction cannot complete.

The test-only observer preserves serialized parser identity, validates the
resulting program, and emits independently predicted error/validity bytes.
It is appropriately separated from the unchanged-program oracle and does
not claim direct access to Lean's internal cursor. This adds tests, not a
Lean-authored firewall or a parser/lowering theorem.

Persistent-state cases establish flow 12345, introduce malformed flow 12346,
check the established return and reject the unrelated return. Complete
arrays are checked after each input, with independently fixed hash cells.
The original BMv2 checks compile the unchanged pinned P4 source and reuse
the previously reviewed sentinel/fresh-prefix observer. Exact packet bytes,
counts and order remain judged; state is observed at each prefix end. Empty
pcap records are not normalized or silently skipped. No new expected
failure or production semantic change is introduced.

The replay improvement compares and saves before narrower known
answers. Both the 55-request observer sweep and five-request malformed-flow
sequence retain all concrete inputs, not only a failing request. Protocol
errors with retained reports also take that path; the independent
known-answer assertions remain intact.

## Evidence and remaining integration

Inspected implementer logs: 165 Python checks, 56 Lean comparisons, 13
original BMv2 selected cuts, seven original BMv2 persistence cases (28
prefixes), and initial full gate 1413 passed / five existing strict expected
divergences. These are attributed log observations, not independent runs.
The initial full gate predates final replay-retention mutation/restoration.

Independently directly invoked **165 Python checks and 56 Lean checks**
against the restored candidate and stable executable: exit 0. No rebuild or
implementation-source/cache edit was performed. Also verified the saved
cut-48 bundle's exact program and complete five requests against the tracked
test constructors, four ports and seed zero, then independently replayed it:
**five agreed, zero divergences/errors**, exit 0.

Independently compiled the original pinned P4 in the existing BMv2 image
and executed cuts **0, 48 and 54**, plus cut-48 persistence: all passed,
process exit 0, covering **seven fresh-prefix full-state snapshots**. This
independent sample includes empty input, flags-present incomplete TCP, and
the complete insertion boundary. It does not duplicate all 41 author-run
prefix observations or claim a fresh image build.

Bundle identity: 79,266 bytes, SHA-256
`960b3340ef5927ec501bf506cf04de9d7a621ded004d72777efca12276dea3a3`.
Inspected implementer live-fault logs: the actual cut-48 gate automatically
saved before failing; replay had three agreements and two payload-only
divergences at requests 0 and 2, with no interpreter errors. Each faulty
Python output lost 14 bytes of incomplete TCP payload. This is runtime
detection, not build rejection. The restored `Packet.read` has zero tracked
diff. The final reproduction section includes the exact two-line semantic
patch, selected tracked-source test that saves the bundle, replay command,
live/restored exits and byte-level witness. Its input order and artifact
identity match the independently inspected bundle. No untracked helper is
required to recreate the experiment.

Integration must add this file to the BMv2 workflow selector; automatic Lean
discovery follows the shared fixture and `test_lean_agrees` naming convention.
The integrator still owns final restored full gates and CI wiring.

Review disposition: **clear for integration**, subject to those ordinary
restored gates and the documented CI selection; no unresolved finding in
the implementation/test increment.
