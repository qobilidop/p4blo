# Parser codec laws review

Final review: clear. The initial structural review below is followed by final
campaign, provenance and restored-execution checks.

2026-09-23. Read-only review of `p4blo-parser-codecs` against the independently
reviewed baseline `9d68d7d`. No candidate sources changed or builds started.

The five public laws concern the actual `Target`, `KeySet`, `SelectCase`,
`Transition`, and `State` encoders/decoders. They compose the existing universal
array, literal, expression and statement codec laws, rather than introduce an
alternate codec. Local body equalities reduce the actual object/default
representation and preserve field/list order. Empty lists, empty state names,
present empty selects and arbitrary target names are included.

The representability predicates add only embedded numeric wire bounds.
They do not require matching key-set types or arity, ascending ranges, resolved
targets, valid parser statements, or termination of a parser graph. Target
roundtrip is unconditional. The mixed kernel witness deliberately includes all
target/set forms, unequal arities/types and a nested conditional body; fifteen
negative witnesses check overflowing fields through both operands and nested
type/expression/statement positions. No new semantic validity promise appears.

Default audit registrations cover all five laws and the mixed witness. A fresh
pinned Lean 4.34.0 query with warnings as errors exited 0 and independently
reported exactly `propext`, `Classical.choice`, and `Quot.sound` for all six
roots. Independent focused execution against the frozen candidate binary
passed all 283 tests in `tests/test_codec_parser.py` (5.23 seconds, exit 0).
Production JSON and baseline expectations remain unchanged in the reviewed
increment; the prior baseline report retains the original-source transcript
provenance.

The owner reports both package/default gates, all 1332 codec tests and 1699
required Lean comparisons passing. Those broader gate results are attributed,
not independently rerun here. Final clearance still requires inspection of the
actual isolated fault patches, proof/runtime detection distinctions, original
231-row transcript replay, retained fault observations and restored source
identities. In particular, runtime consumers using the baseline audit layer
while an unchanged new proof rejects a fault must be labeled as such, not as a
passing candidate full audit.

## Final evidence closure

Independently read the final evidence note and inspected the actual compilation,
proof and executed-test logs. Each actual Json fault compiled. One-sided case
reversal fails the unchanged proof's ordered-array equality. Paired Target and
masked-operand permutations preserve all five universal roundtrip laws, but
ordinary real-endpoint pytest execution rejects 24 and 10 cases respectively.
Error-order and empty-select faults reject two and four cases. These are real
assertion failures, not shared-fixture setup errors.

The order-only proof failure is correctly limited: it breaks the proof's
definitional sequencing step, not evidence of a false successful-roundtrip
statement. The recorded closed asymmetric success control still kernel-checks.
The empty-select mutation additionally has a genuine false empty-case result.
Baseline runtime/audit layers deliberately permit endpoint execution despite
the separate unchanged new proof failing; the note does not claim those builds
pass the final candidate's new audits.

The paired-observer challenge provides concrete false-assurance evidence:
under the Target fault, changing Python expectations yields all 283 passing
tests, while unchanged native anchors reject four checks. Changing only the
Lean descriptor instead also yields 283 passing tests but six native failures.
The directly written native constructor/descriptor anchors are therefore a
meaningful independent layer, not merely duplicate expected values.

Independently executed the inspected read-only reconstruction and replay
recipes, adding explicit expected cardinality, per-campaign request uniqueness,
and fixed digest assertions. Results:

- All five exact Json patches reconstruct; four retained mutant source hashes
  match their artifacts.
- Thirteen baseline source hashes match historical git objects at `9d68d7d`,
  not the later witness sources. All 231 current request/answer pairs retain
  their exact order and original compact-plus-LF stdin.
- Both restored actual endpoints reproduce all 231 historical raw stdout,
  stderr and exit-status rows exactly; all 76 successful canonical outputs
  pass the public protobuf wrapper checks.
- Four bundles contain 24/10/2/4 genuine mismatches, each with clean process
  status and strict source-matched expected/actual observations. Their forty
  deterministic harness views match, and both restored endpoints agree on
  all inputs. This is forty observations over **34 distinct requests**, not
  forty independent inputs.
- All six final candidate/fault-tree source pairs are byte-identical. Actual
  Json retains its original `0d844312...c443e` digest; no deliberate production
  mutation survives.
- The retained 411355-byte baseline retains SHA-256
  `454ff7c9b2c68b02ec81eb07d0897355b75721fad2ebe742000ffcb348a5e2bb`;
  all four campaign bundle hashes match the final note.

An independent final native endpoint self-test also passed all 133 checks with
exit 0 and empty stderr. Together with the earlier independent 283 focused
tests and six fresh axiom queries, these close the review without rebuilding
or modifying either candidate. Owner broader gates remain attributed above;
the integrator owns the combined full gate.

No remaining blocker. Full Program composition, text/binary equivalence,
semantic validity and parser execution/termination are not supplied by these
five wire-only laws. Action/Block requires its own next checkpoint.
