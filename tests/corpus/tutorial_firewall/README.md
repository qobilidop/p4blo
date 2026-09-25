# Tutorial stateful firewall

Typed Python adaptation of Stephen Ibanez's Apache-2.0 tutorial solution,
[`p4lang/tutorials@098ce0b7ae486f5b747a6b53ad1585f0d977b42e`](https://github.com/p4lang/tutorials/blob/098ce0b7ae486f5b747a6b53ad1585f0d977b42e/exercises/firewall/solution/firewall.p4).
The unchanged original is pinned separately in `tests/oracle/firewall.p4`
by `tests/oracle/firewall.py`; the repository's root LICENSE contains
Apache-2.0. An independent [Lean source](../../../impl/lean/P4blo/TutorialFirewall.lean)
constructs the same complete IR without reading the golden. Follow the
[quickstart](../../../docs/quickstart.md) to author and run either version.

## What the port preserves

Fixed Ethernet/IPv4/TCP extraction, including the original's lack of IHL
and data-offset option handling; IPv4 routing with MAC rewriting and
wrapping TTL decrement; the exact direction-table hit guard; SYN-only
outbound insertion, where "SYN" means the SYN bit is set, so SYN+ACK also
inserts; reverse-ordered inbound five-tuples; two independent 4096-cell
one-bit Bloom filters; and final IPv4 checksum recomputation. IPv4 and
TCP checksum verification is absent in the original and stays absent. The
two Bloom filters keep the tutorial's false positives: inbound traffic
hashes the reversed tuple and requires both bits, but only when the
direction table hits. There is no connection timeout, FIN deletion or
aging; this is not exact connection tracking.

The port introduces no IR construct and no extern beyond the byte-aligned
CRC16 and CRC32 services of [arch-supports.md](../../../docs/arch-supports.md#extern-families).
Masking each CRC by 4095 implements the original base-zero modulo-4096
hash range. The empty verify and egress stages are erased and checksum
computation runs last in the one control, as in the forwarder.
`mark_to_drop` maps to the architecture's drop metadata; the egress port
is also set to 511 so that direction-table lookup keys are preserved after
a routing drop. This is a fixed sequential two-port profile, not a claim
about arbitrary v1model metadata or topologies.

| Firewall behavior | Existing mechanism |
|---|---|
| Fixed Ethernet/IPv4/TCP parsing | header declarations, extraction, select, validity |
| Routing and direction classification | LPM and exact tables, action parameters, table hit |
| Direction-dependent tuple order | ordinary actions and conditional calls |
| 104-bit key and 12-bit index | concatenation, explicit width assertion, bitwise mask and cast |
| Bloom insertion and lookup | register reads and writes, booleans and branches |
| MAC, TTL and checksum output | assignment, wrapping subtraction, checksum extern, deparser |

Two authoring costs are visible next to the original: a table hit needs a
declared boolean plus `apply_table(..., hit=...)` rather than an
expression-valued apply, and an extern result must be assigned before it
can be masked or cast. The wide concatenations need explicit `as_` width
witnesses because Python's type system cannot compute widths.

## Vectors and independent expectations

`connection.stf` reuses the original pinned smoke packets and
configuration, with only table, key and action names mapped to the IR
metadata contract. `collisions.stf` pins a two-flow Bloom false positive.
Distinct TCP sequence numbers keep earlier outputs from satisfying later
expectations. The following independently calculated indices use the
104-bit key `10.0.0.1, 10.0.0.2, internal_port, 80, 6` in network order:

| Internal port | CRC16 index | CRC32 index |
|---|---:|---:|
| 12345 | 1990 | 1987 |
| 12346 | 966 | 2093 |
| 749 | 966 | 747 |
| 13602 | 780 | 2093 |

Ports 749 and 13602 jointly authorize an inbound packet for 12346 without
that flow ever sending SYN; either partial match alone rejects, in both
orders. `tests/programs/test_firewall.py` asserts independently expected packet
bytes and all 8192 register cells after every request, in Python and in
Lean, not merely that the two agree. It also covers SYN-only insertion,
FIN non-deletion, reverse-flow RST, non-TCP forwarding, TTL underflow, a
fixed parser shape despite IHL and data-offset 6, direction-table misses,
a 43-byte frame with nine TCP bytes, a routing miss and an invalid
incoming IPv4 checksum that is recomputed without verification. The
checksum expectation uses a test-only one's-complement sum, not the
production extern. `tests/programs/test_firewall_boundaries.py` adds every byte
truncation of one frame and valid-malformed-valid persistence sequences;
`tests/programs/test_firewall_generated.py` adds generated flow and host-policy
sequences with full-cell CRC expectations from independent GF(2) and zlib
implementations. Host changes within one sequence are Python and Lean
evidence only. General fragment behavior and exhaustive TCP flag
combinations are not exercised.

## On the oracles

Both P4 oracles run the unchanged original and the printed IR. BMv2
matches every packet and, through the driver's register readback
profile, all 8192 cells at thirty sequence-prefix boundaries; see the
[BMv2 adapter](../../oracle/bmv2/README.md#register-readback). The
pinned P4-SpecTec has two defects that these probes expose and that
simpler packet sequences miss: it pads odd-byte CRC32 input, so the
104-bit tuple lands at index 2182 instead of 1987 while collision
relationships and packet fates are preserved, and it casts an LPM or
ternary key's base where it should cast the mask, so a `/32` route miss
is forwarded. Both are strict, narrowly classified expected
discrepancies; the diagnoses and the exact known answers are in
[assurance.md](../../../docs/assurance.md#known-disagreements-with-the-oracles).
Packet-only agreement with an oracle cannot establish hash or state
semantics for this program; that is why the primitive CRC probes in
`tests/unit/test_crc.py` and the complete register observations exist.

## Faults the tests catch

Four validator-accepted wrong ports are rejected by both interpreters'
independent expectations, without any build or runtime error:

| Wrong port | Witness that detects it |
|---|---|
| require either Bloom filter instead of both | the third collision request is accepted with only one cell set |
| insert without SYN | an initial outbound ACK forwards normally but changes state |
| ignore the direction-table hit | a bypassed outbound SYN forwards normally but changes state |
| do not reverse TCP ports | an established reverse ACK is rejected |

The middle two show that packet-only conformance is insufficient. Actual
Python and Lean CRC faults that XOR one bit likewise preserve every packet
while permuting register indices, and are caught only by state
comparison. Synthetic observer faults that omit cells, report touched
cells only, shift CRC32 to SpecTec's index, reset state or admit a
premature ACK are all rejected; the driver's malformed command, sentinel,
process and transcript failures are tested separately.

## The Lean port

`P4blo.TutorialFirewall.program` is authored directly in Lean from the
typed source library and shared Ethernet, IPv4 and metadata layouts; its
complete protobuf export equals the Python corpus program and the text
golden byte for byte. Ordinary parser, action, table, extern and operator
assembly remains an explicitly unverified seam. `p4blo leanTutorialFirewall run`
prepares the same in-memory program through the public API and keeps
extern state across requests; `tests/lean/test_lean_firewall.py` runs both
vectors, the collision profiles, all byte cuts, the persistence sequences
and the generated campaigns against the same independent expectations,
and separately checks a fixed-server transcript so that a server reset
cannot hide behind generic differential agreement.

Proved under explicit premises: successful initialization of all nine
roots, whole-Run identity of the invalid-IPv4 body, and exact two-write
Bloom insertion preserving both arrays and unrelated state. Not proved:
readback, the drop decision, hash bounds, control composition or any
whole-firewall correctness property. The theorems are stated in
[`TutorialFirewallProof.lean`](../../../impl/lean/P4blo/TutorialFirewallProof.lean)
and [`TutorialFirewallBloom.lean`](../../../impl/lean/P4blo/TutorialFirewallBloom.lean)
and audited in [`impl/lean/P4bloTest/UserProofAudit.lean`](../../../impl/lean/P4bloTest/UserProofAudit.lean).
