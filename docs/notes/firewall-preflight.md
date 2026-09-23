# Tutorial firewall: original-program preflight

Audited and executed on 2026-09-23 in an isolated worktree. This is an
oracle feasibility result, not a completed p4blo port or an equivalence
proof. No implementation or schema change was made for this audit.

## Source and profile

- Upstream: `p4lang/tutorials`, commit
  `098ce0b7ae486f5b747a6b53ad1585f0d977b42e` (resolved using
  `git ls-remote https://github.com/p4lang/tutorials.git refs/heads/master`).
- Exact source: [exercises/firewall/solution/firewall.p4](https://github.com/p4lang/tutorials/blob/098ce0b7ae486f5b747a6b53ad1585f0d977b42e/exercises/firewall/solution/firewall.p4).
- Source bytes: 8766; SHA-256
  `5e1286ddbbc583d00fb5cbbb7c5f7a07076b4c200b0e9ed931c58e6b03230b19`.
- Its SPDX header identifies Stephen Ibanez, 2019, Apache-2.0. Preserve
  attribution and the upstream license when vendoring or adapting it.
- [Upstream exercise](https://github.com/p4lang/tutorials/blob/098ce0b7ae486f5b747a6b53ad1585f0d977b42e/exercises/firewall/README.md)
  supplies the tutorial intent. The executable solution, not the prose,
  determines the behavior being compared. In particular, the solution
  computes the IPv4 checksum although the README describes checksum
  controls as unnecessary/empty.
- Preflight profile: the **unchanged complete solution**, one v1model
  switch, fresh zeroed registers, sequential packets, two static /32
  routes, port 1 internal and port 2 external. This simplifies only the
  topology/control-plane configuration, not the P4 program. It does not
  reproduce the tutorial's four-switch Mininet topology or P4Runtime.

## Semantics to preserve

The solution maintains two 4096-cell, one-bit Bloom filters. CRC16 and
CRC32 hash the ordered IPv4/TCP five-tuple; incoming packets reverse the
addresses and ports before hashing. Only outbound packets with SYN set
update both filters; inbound packets need both bits set. Direction checking
is conditional on a `check_ports` table hit. IPv4 forwarding rewrites MACs,
decrements TTL, and recomputes the IPv4 checksum. The parser consumes fixed
Ethernet, IPv4 and TCP headers, not options selected by IHL/data-offset.
[Source](https://github.com/p4lang/tutorials/blob/098ce0b7ae486f5b747a6b53ad1585f0d977b42e/exercises/firewall/solution/firewall.p4)

Do not strengthen the claim to connection tracking: no timeout or FIN
deletion, and false positives are intentional Bloom-filter behavior.
Non-TCP, invalid headers, absent direction entries, TTL underflow, fragments
and malformed packets need explicit regression profiles; the preflight
below does not settle them. No transport checksum validation is performed
by this solution; the smoke packets use a zero TCP checksum.

## Execution evidence

Both oracles executed the original source, **not a p4blo-printed program**.
Both finished with exit status 0 and agreed with independently constructed
full expected packet bytes (including rewritten MACs, TTL and IPv4 checksum):

| Request, in one persistent sequence | Expected and observed |
|---|---|
| External ACK for flow 10.0.0.1:12345 -> 10.0.0.2:80 before establishment | drop |
| Internal SYN for that flow | forward to port 2 |
| The same external ACK after the SYN | forward to port 1 |
| External ACK for internal port 12346 instead | drop |

P4-SpecTec pin: `2730cfd9e74048bb5439da0f8afcef124079a064`, with p4c
include submodule `6b7ec98e77dfc71c6e1309d9a76183cb31f35a8a`, as already
pinned by this repository. Output ended:

```text
[PASS] Transmitted (2) 000000000022000000000001080045000028000000003F0667CE0A0000010A0000023039005000000000000000005002200000000000
[PASS] Transmitted (1) 000000000011000000000001080045000028000000003F0667CE0A0000020A0000010050303900000000000000005010200000000000
passed
```

There was one existing elaboration warning about `sink` having no clauses;
it did not prevent execution. SpecTec's end-of-sequence leftover check
asserts the two drops; no unsupported `no_packet` directive was used.

BMv2 image: `p4blo-bmv2`, native arm64, local image ID
`sha256:30ae13925d7bb34f0e9967e07dcb36f4954191f52676621804783196f19f5a4f`.
The checked-in Dockerfile identifies its reproducible base inputs; this
local image ID identifies the artifact actually exercised. Tool versions:

```text
p4c-bm2-ss: Version 1.2.5.15 (SHA: 325e90e BUILD: Release)
simple_switch: 1.15.4-unknown
```

The existing `oracle.bmv2.run._driver` compiled the downloaded P4 text and
replayed one phase with ports `[1, 2]`, the four inputs above, and these
control-plane commands:

```text
table_add MyIngress.ipv4_lpm MyIngress.ipv4_forward 10.0.0.1/32 => 00:00:00:00:00:11 1
table_add MyIngress.ipv4_lpm MyIngress.ipv4_forward 10.0.0.2/32 => 00:00:00:00:00:22 2
table_add MyIngress.check_ports MyIngress.set_direction 1 2 => 0
table_add MyIngress.check_ports MyIngress.set_direction 2 1 => 1
```

The compiler returned `ok: true` with empty diagnostics. Replay returned
`error: null`; the CLI confirmed all four entries. Its complete output map
contained exactly the two expected packets above, one on each port. The
preflight asserted exact map equality and no CLI error. BMv2 used the
existing file/FIFO driver, with no privileged container or live network
interfaces. As with the current corpus runner, completion relies on its
documented output-settling heuristic.

## Reproduction independent of temporary artifacts

Download the pinned raw source to a chosen absolute path and verify the
SHA-256 above. Put the following complete vector in a file:

```text
add MyIngress.ipv4_lpm 32 hdr.ipv4.dstAddr:0x0a000001 MyIngress.ipv4_forward(dstAddr:17, port:1)
add MyIngress.ipv4_lpm 32 hdr.ipv4.dstAddr:0x0a000002 MyIngress.ipv4_forward(dstAddr:34, port:2)
add MyIngress.check_ports standard_metadata.ingress_port:1 standard_metadata.egress_spec:2 MyIngress.set_direction(dir:0)
add MyIngress.check_ports standard_metadata.ingress_port:2 standard_metadata.egress_spec:1 MyIngress.set_direction(dir:1)
packet 2 0000000000010000000000aa08004500002800000000400666ce0a0000020a0000010050303900000000000000005010200000000000
packet 1 0000000000010000000000aa08004500002800000000400666ce0a0000010a0000023039005000000000000000005002200000000000
expect 2 000000000022000000000001080045000028000000003f0667ce0a0000010a0000023039005000000000000000005002200000000000$
packet 2 0000000000010000000000aa08004500002800000000400666ce0a0000020a0000010050303900000000000000005010200000000000
expect 1 000000000011000000000001080045000028000000003f0667ce0a0000020a0000010050303900000000000000005010200000000000$
packet 2 0000000000010000000000aa08004500002800000000400666ce0a0000020a0000010050303a00000000000000005010200000000000
```

Invoke the existing built oracle with absolute paths:

```text
<checkout>/p4spectec sim <checkout>/spec -arch v1model -i <checkout>/p4c/p4include -p <original-source.p4> -stf <vector.stf>
```

The exact command used in the audit was:

```sh
/Users/qobilidop/.cache/p4blo/p4-spectec/p4spectec sim /Users/qobilidop/.cache/p4blo/p4-spectec/spec -arch v1model -i /Users/qobilidop/.cache/p4blo/p4-spectec/p4c/p4include -p /Users/qobilidop/my/work/p4blo-firewall-audit/.artifacts/firewall/firewall.p4 -stf /Users/qobilidop/my/work/p4blo-firewall-audit/.artifacts/firewall/preflight.stf
```

The /32 matches and explicit equal priorities avoid needing a claim about
SpecTec's independent longest-prefix selection, which it does not provide.
The BMv2 run used native LPM table entries.

## Next implementation tasks and confidence

1. **Vendor/pin the original source and license, then promote the direct
   source preflight to a required oracle test.** Keep it separate from the
   existing printed-program checks, so a printer bug cannot replace the
   supposed original. Test source checksum and retain the exact profile.
2. **Add CRC16 and CRC32 extern contracts**, independent Python/Lean models,
   typed eDSL bindings, observer support and printer bindings. The existing
   register/checksum families provide the pattern. Confidence: high that
   no new IR node is needed for this firewall. For its fixed 4096 range,
   masking a full CRC with 4095 is sufficient; general range reduction can
   remain an extern contract instead of adding a remainder node solely
   for this example. Confidence: medium on the best public extern API;
   revisit when `xdp-filter`/Katran needs hashing.
3. **Pin primitive hashes with externally observed known answers.** The
   five-tuple is 104 bits in network field order. SpecTec's pinned
   `p4spec/lib/backend-sim/hash.ml` implements CRC16-ARC (initial zero) and
   reflected CRC32 (initial/final XOR all ones). Its `adjust` formula uses
   `value % (max - base) + base`; do not infer the general v1model range
   contract from that implementation. The firewall has base zero and
   max 4096, so the suspected nonzero-base discrepancy is irrelevant to
   this preflight. Non-byte-aligned hash input behavior needs a separate
   contract/test before advertising support.
4. **Port readable Python and Lean eDSL programs**, using table hit results,
   ordinary conditional statements, existing register externs and explicit
   metadata mapping. Reuse header/forwarding patterns, but preserve every
   relevant original branch rather than turning the whole firewall into
   an extern. Expand the profile gradually after direct-source checks.
5. **Observe complete state after each request and prove scoped claims.**
   The current original-program smoke test observes packets only. It does
   not validate actual register indices, and even a consistently wrong
   hash can pass a simple outbound/reverse sequence. Add independent
   primitive CRC known answers, partial and double collision sequences,
   and an oracle register-state observation path. Prove bit monotonicity
   and established reverse-flow acceptance only under explicit routing,
   classification and parsing assumptions; do not prove a false blanket
   claim that every unsolicited flow is dropped.
6. **Adversarially challenge the port and its observation harness.** Mutants
   should include swapping CRC algorithms, wrong input byte order, failing
   to reverse ports, AND instead of OR in rejection, SYN-independent
   insertion, reset-between-packets, and skipping the table-hit condition.
   Run mutations on both Python and Lean implementations, keeping build
   failures separate from semantic detections.

Implementation gates were not rerun for this read-only research/report.
Both original-program execution probes passed; `git diff --check` passed.
No general firewall equivalence, CRC equivalence, state observation,
malformed-packet coverage or new Lean theorem is claimed here.

## Promotion to a permanent gate

The unchanged source is now vendored at `tests/oracle/firewall.p4`, with its
original SPDX notices and SHA-256 checked before execution. The root
`LICENSE` supplies Apache-2.0. `tests/oracle/firewall.stf` and its small
adapter run directly in both existing oracle CI jobs, without our printer.

The permanent vector improves the smoke experiment above: every TCP packet
has a distinct sequence number. These numbers do not enter the five-tuple
hash, but prevent a prematurely forwarded ACK from satisfying the later
expected ACK in an aggregate output queue. A synthetic wrong observation
with the premature ACK is explicitly rejected. Both original-program tests
and the pin/observer/configuration-drift tests pass locally (6 tests). This still observes packets,
not Bloom register state; full per-request state and collision coverage remain
required for the port. The BMv2 completion heuristic is unchanged.

The subsequent CRC implementation preflight found a pinned SpecTec bug for
odd-byte CRC32 inputs, including this 13-byte key. A consistently wrong hash
can still pass this simple sequence. The CRC increment records exact failing
known answers and controls separately; this gate must not be cited as proof
of CRC values, register indices or collision behavior.
