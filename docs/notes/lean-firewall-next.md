# Next application: Lean-authored tutorial firewall

2026-09-23. Planning against committed `78aa246`. This advances the accepted
stateful-firewall milestone alongside the separately scoped real-forwarder
action proof. It does not replace that proof or claim the firewall milestone
complete. No source, runtime or oracle behavior changes in this planning step.

Read `firewall-port.md`, `firewall-boundaries.md`, `firewall-generated.md`,
their reviews, and the actual Python corpus source before implementing. The
existing CRC contract and original-program oracle discrepancies remain binding.

## Exact source and architecture boundary

Construct the existing `tutorial_firewall` Program in the Lean user package,
under `P4blo.TutorialFirewall`, matching both the typed Python builder and
`tests/corpus/tutorial_firewall/tutorial_firewall.txtpb` exactly. The pinned
original is the unchanged Apache-2.0 Stephen Ibanez tutorial solution already
vendored under `tests/oracle/`; preserve its notices in adapted source.
Neither the Lean source nor its compiled runner may load the golden or invoke
the Python builder to construct the Program. Full identity comparisons are
tests, not implementation inputs.

Keep all actual branches and declarations visible: fixed Ethernet/IPv4/TCP
extraction, both tables, the seven ingress locals, direction-dependent tuple
order, register reads/writes, and checksum computation last. No firewall
primitive, parser shortcut, new extern or new IR node is needed. Preserve:

- Two distinct 4096-cell one-bit Bloom registers, initially zero and persistent
  between requests. A double collision remains accepted; this is not exact
  connection tracking, timeout tracking or FIN deletion.
- Routing and old-destination MAC rewriting before direction classification;
  TTL subtraction wraps. Drop also sets egress to 511 so later lookup keys
  match the existing program. Do not introduce an early-return optimization.
- Firewall logic only under IPv4/TCP validity and an actual `check_ports` hit.
  Direction zero hashes forward address/port order; direction one reverses
  both. Outbound insertion requires the SYN bit, not a pure-SYN flag pattern.
- The complete 104-bit hash input and existing CRC16/CRC32 contracts. Masking
  with 4095 is the fixed modulo-4096 profile; do not generalize hash ranges.
- Fixed header sizes despite IHL/data-offset, no options parsing or checksum
  verification, and final checksum recomputation even after a routing/drop
  action. Preserve the known SpecTec CRC32 and mask discrepancies precisely.

Confidence: high in exact program identity as the first boundary and in no
new core constructs being necessary; medium in the best reusable authoring
surface. Revisit ergonomics when the actual port exposes repeated machinery,
not by silently changing the golden or original policy.

## Lean authoring and execution

Use typed named scalar/header paths where the existing surface supports them.
Reuse the committed forwarder's Ethernet/IPv4/metadata layout declarations
when they are definitionally identical; declare TCP and the enlarged roots
locally. Do not import ForwarderProof just to obtain protocol data. Avoid
lifting layouts into a new public protocol package in this increment; a small
shared source module can be reviewed separately if importing the source-only
Forwarder module becomes a real coupling problem. Confidence: medium; revisit
on another client or proof dependency, preserving the old public declarations.

Ordinary named Lean functions should expose table hits, hash calls, temporaries
and effect order. Parser/table/extern/action assembly may use the actual raw IR
constructors, explicitly labeled as unverified seams. No second command AST
or custom macro is required for this port. Do not claim a complete verified
frontend because the whole Program is authored in Lean. Typed field paths and
any reused proved lowering keep their actual bounded guarantees.

Provide `leanTutorialFirewall` syntax export plus a fixed-Program run mode
through the existing public `prepareSwitch`/`runSwitch` API. Requests contain
only entries, ingress port and packet, never a replacement Program. Keep the
returned extern state across requests in the same process. Stream complete
observations of both arrays after every request, including rejected/truncated
packets. Reuse the strict existing response observer; do not compare only
touched cells or final state. Allow a small shared runner helper with the
forwarder only if both old and new protocol tests protect the extraction.

## First bounded theorem

Start with actual Index.build and Frame.forBlock success for the authored
ingress, discharging initialization of its real seven locals and all nominal
header/metadata declarations. Then prove the actual ingress **body** is a
whole-Run identity when the actual IPv4 header is invalid. Both outer guards
are false, so no table, hash, register or checksum action executes. Use actual
execution, not an alternate evaluator or a hypothesis asserting that the
whole body is already correct.

The premise should expose the real built index/scope and actual header
lookup; do not demand arbitrary unused stored fields be semantically valid
if the runtime never reads them. Keep unused TCP/local/shared state arbitrary
where those read premises permit. Prove the actual initialized seven-local
frame separately as a constructive witness, not an unnecessary restriction
on the body theorem. Preserve arbitrary incoming persistent state. State
exact Run equality, including arrays, packet/emitter, entries, visits, scope,
locals, metadata and action bindings under the stated frame premises.

This is a control-body claim, not parser behavior, outer runControl copyback,
packet fate, source-global validity or a complete firewall theorem. Explicit
finite trace derivations and native queue-boundary tests are not an indexed
exact-step theorem unless a numeric count appears in its proved conclusion.
Register new advertised roots in the default user audit, with constructive
kernel witnesses and no new axioms, sorry or native proof escapes.

## Independent tests and adversarial acceptance

1. Exported complete syntax equals both builder and unchanged golden, passes
   public validation, and preserves every declaration, local, parameter,
   statement order and fixed width. Tests must not patch either reference.
2. Replay both original corpus STF files with explicit nonempty inventory.
   Exercise Python, generic Lean-from-export and direct in-memory authored
   execution against the same independent expected packets and state.
3. Reuse the existing connection, both partial-collision orders, double
   collision, shape, bypass and edge sequences. Preserve unique packet
   sequence numbers. Check every one of 8192 cells after every request, not
   just equality between the two runtimes. The known indices and independently
   calculated checksums remain separate anchors.
4. Reuse all unchanged-program byte-cut boundaries and valid/malformed/valid
   persistence, then the existing deterministic targeted/generated flow-policy profiles as
   appropriate for the fixed runner. No empty generator or silently omitted
   fixture may count as coverage. Keep exact current program/config/request
   identity in saved mismatch bundles. The existing parser_observer() clone
   adds diagnostic bytes and is separate evidence, not the immutable Program
   served by this runner. Generated mid-sequence entry replacement is tested
   by Python/Lean; existing BMv2 samples use constant-rule prefixes. Do not
   attribute the dynamic replacement cases to the original-program oracle.
5. Check the invalid-body theorem boundary with detached, exact-type complete
   Python state and complete native sentinels. Include nonzero prior registers,
   asymmetric headers, arbitrary unused TCP contents and initialized-local
   identities. Retain a packet-invisible state fault caught by this observer;
   packet-only success cannot stand in for the whole-Run boundary.
6. Challenge actual authored branches (SYN removal, missed table-hit guard,
   reverse-order error, accepting either filter), and the fixed runner's
   persistence/complete-state observer. At least one compiling production
   Python or Lean fault must produce a saved real packet/state mismatch,
   fail live replay, and pass after exact restoration. Build failures,
   wrong hook with zero hits, protocol failures and runtime semantic mismatches
   are distinct evidence. Existing retained inputs may be reused, but must
   not be counted as new independent inputs merely because another fault uses
   them. No intentional mutation enters main.

Run both Lean packages/audits/native tests before consumers, required real-Lean
agreement, focused firewall/runner tests and the full repository gate. Existing
original-source BMv2 full-array and SpecTec discrepancy tests remain unchanged;
no Docker rebuild or security relaxation is needed. Do not treat any unavailable
oracle as a pass. Independent read-only review and reproducible evidence must
precede small logical commits/pushes and status updates.

## Follow-on properties, not this port's completion claim

After the exact port, target actual Bloom insertion monotonicity and conditional
reverse-flow acceptance under explicit parsing/routing/classification/hash and
table-entry assumptions. Separate hash arithmetic, index bounds, register
execution and control branching instead of assuming whole firewall execution.
Never prove the false claim that every unsolicited flow drops: the existing
double-collision witness is a permanent counterexample.

General CRC equivalence, original-P4-to-IR compiler correctness, architecture
metadata beyond the pinned profile, arbitrary topology/concurrency and full
Python equivalence remain open. Even completion of the first bounded theorem
and all port tests does not close those obligations.
