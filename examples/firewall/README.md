# Stateful firewall

Allow an inside client to open a TCP pinhole to an approved service, then
forward matching packets in either direction unchanged. A reply arriving
before the client's SYN is dropped; the same reply after that SYN passes.

This is **bounded SYN-created pinhole filtering**, not TCP connection tracking.
It makes the relationship between service policy, earlier packets and current
packet fate visible in one complete program.

## Run it

From the repository root:

```sh
uv run python -m examples.firewall.demo
```

Expected output:

```text
Inbound before SYN: drop; occupied slots = 0/16
Outbound SYN: port 2, packet unchanged; occupied slots = 1/16
Inbound after SYN: port 1, packet unchanged; occupied slots = 1/16
```

The demo creates one program instance, installs an allowed HTTPS service
prefix and runs three packets through that same instance. Loading a new
instance clears the pinholes. Change `meta.server_port:443` to `:80` in
`demo.py` and all three packets drop: their destination service remains 443.

## Contract

- Port 1 is inside; port 2 is outside. Accepted traffic crosses to the other
  port. Other ingress ports drop. Ethernet addresses, IP TTL, checksums and
  payload remain unchanged; this is a transparent filter, not a router.
- The supported packet profile is untagged Ethernet carrying IPv4 version 4,
  IHL 5 and TCP with data offset 5. All 54 fixed header bytes must be present.
  IPv4 total length must be at least 40, its checksum must equal the canonical
  one's-complement result, and fragmentation and the reserved IPv4 flag are
  rejected. The DF flag is allowed. Unsupported and truncated headers drop
  before accessing flow state.
- The host is responsible for the payload envelope: the program does not
  reconcile IPv4 total length with available bytes or padding. TCP checksum,
  reserved TCP bits, sequence numbers and acknowledgement numbers are not
  validated. TTL is preserved, including zero, because this filter is not an
  IP forwarding hop. These are deliberate input and protocol boundaries.
- The host's `services` table matches the **server's** IPv4 prefix and TCP
  port in both directions. The longest matching prefix wins; default is deny.
  Policy is checked on **every** packet, including existing flows. Removing a
  rule immediately denies its flows but retains their records; reallowing the
  service permits those retained flows again.
- A flow is the exact 96-bit tuple `(client IPv4, server IPv4, client TCP port,
  server TCP port)`. An inside SYN with ACK, FIN and RST clear may open an empty
  slot. Other flag bits do not prevent opening. An existing exact record
  admits every subsequent matching packet, including retransmitted SYN, FIN
  and RST, while its service remains allowed.
- CRC-16/ARC over the tuple's 12 network-order bytes chooses one of 16 slots
  using the low four bits. Each register cell stores one validity bit and the
  full tuple. A hash collision **rejects the newcomer without eviction**, even
  when another slot is empty. Hash equality alone never grants access.
- Records do not expire, FIN/RST do not remove them, and a fresh program load
  is the reset mechanism. There is no handshake validation, sequence-window
  tracking, dynamic allocation, spoofing protection or concurrent-hardware
  atomicity claim. This small state model demonstrates filtering semantics;
  it is not a production security boundary.

## Read the program

[`program.py`](program.py) contains the complete packet-processing logic.
`Parse` extracts the fixed headers. `Filter.apply` closes the gate by default,
checks the packet profile and normalizes the two directions into client/server
metadata. The host-installed `services` table then decides whether flow state
may be consulted. `inspect_flow` computes the slot and compares the complete
record before admitting an existing flow or opening an empty slot. `Emit`
serializes the unchanged headers and remaining payload.

The 97-bit record combines occupancy and identity into one register cell.
This avoids a separate validity array and makes it possible to inspect the
entire state after every packet. Sixteen slots intentionally make capacity
and collisions easy to reproduce. No custom extern hides the flow policy.

The block classes are reusable independently. For example, compile the
control and its declared extern dependencies without selecting a pipeline:

```python
from examples.firewall.program import Filter, checksum, flow_hash, flows
from p4blo import edsl as p4

compiled = p4.BlockLibrary(Filter, externs=[checksum, flow_hash, flows]).compile()
```

The `blocks` library collects the three block definitions and their shared
extern declarations. It does not select an architecture or a complete program;
`blocks.compile()` produces declarations without global header/metadata roots
or exported roles. This is a core protobuf `BlockLibrary` that can be
validated independently. Types follow the blocks' parameter and local
declarations.

`build()` separately calls `v1model.assemble` with that library to select
parser, ingress and deparser; omitted checksum/egress stages are empty.
`egress_spec` carries the requested port or drop value 511; the core sees
ordinary typed fields. The demo selects `v1model.load` to bind the supplied
externs and `v1model.V1Model(ports=4)` to execute the packet profile. Extern
declarations describe typed calls; the registry supplies their execution.

`ChecksumWords`, `FlowTuple` and `FlowRecord` name the checksum input,
flow identity and writable register-record types. `orient_flow` is an ordinary
Python build helper: calling it records the direction branches in place.
`inspect_flow` is a declared action: calling it records an action call in the
IR. Neither helper processes a packet while `build()` runs. Symbolic
conditions such as `supported_packet` still require `with self.if_(...)`.

The demo inspects the `flows` runtime register by name through
`loaded.externs`. It reuses the same loaded object for all three packets,
so the cell written by the outbound SYN remains available to the reply.

## Evidence and boundaries

Verification assets live in [`tests/examples/firewall/`](../../tests/examples/firewall/).
The packet sequence constructs wire bytes with standard-library packing and
an independent Internet checksum, computes CRC with a bitwise reference
anchored to the `123456789` known answer, and checks exact output bytes, fate,
diagnostics and **all 16 register cells after every request** across an 890-request
sequence. It covers all
256 flag bytes before/after opening as applicable, both directions, service
removal/reallow, more-specific deny, each tuple component, all fixed-header
truncations, malformed profiles, collisions without eviction, full occupancy
and reset. The same independent expected outcomes are checked against Python
and the real Lean interpreter.

`program.txtpb` is a generated golden, and `pinhole.stf` supplies a short
independent packet trace with exact-length output expectations for the shared
architecture and external-oracle harnesses. Packet-vector oracle agreement
does not establish equality of hidden register state. The dedicated Python
and Lean tests do check that state. There is no separately authored Lean
application or whole-firewall proof.

After building Lean with the repository's standard workflow, run the focused
checks from the repository root:

```sh
P4BLO_REQUIRE_LEAN=1 uv run pytest tests/examples/firewall tests/examples/test_examples.py
```

The existing upstream-derived `tests/corpus/tutorial_firewall` remains a
separate Bloom-filter regression fixture with its own contract.
