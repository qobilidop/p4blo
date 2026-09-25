# Flow-affine UDP load balancer

A client sends UDP requests to one virtual IP (VIP). The load balancer chooses
one of two servers and forwards the request with that server's Ethernet
address. Repeated packets from the same flow choose the same server while the
host configuration stays unchanged. Different flows can choose different
servers; changing a request's payload does not change its selection.

This is a direct-server-return style **request dispatcher**, not NAT. Backend
servers must accept the VIP locally and provide their own return path. The
example models the dispatcher's input and output; it does not simulate the
servers, address resolution or a complete deployment.

## Run

From the repository root:

```sh
uv run python -m examples.load_balancer.demo
```

Expected output:

```text
UDP 10000 -> 8080, ping: port 1, backend MAC 00:00:00:00:01:01, TTL 63
UDP 10240 -> 8080, ping: port 2, backend MAC 00:00:00:00:02:02, TTL 63
UDP 10000 -> 8080, pong: port 1, backend MAC 00:00:00:00:01:01, TTL 63
UDP 10000 -> 8081, ping: drop
```

The first two requests reach different backends. The third changes only the
first flow's payload and stays on port 1. Port 8081 has no configured service,
so the last request drops.

## Read the program

[`program.py`](program.py) contains the complete typed Python eDSL program.
Its `build()` returns the IR consumed by interpreters, tests and the P4 printer.

1. `Ethernet`, `IPv4` and `UDP` describe the fixed wire headers. `Parse`
   extracts IPv4 only for EtherType `0x0800`, then UDP only for protocol 17.
2. `Balance.apply` begins with drop set. Complete supported headers and a valid
   IPv4 checksum are required before any table can admit a packet.
3. `services` maps an exact `(destination IP, destination UDP port)` to an
   eight-bit backend group. A separate `service_found` flag prevents a miss
   from accidentally using the metadata's default group zero.
4. CRC-16/ARC hashes the network-order concatenation of source IP, destination
   IP, source UDP port and destination UDP port (96 bits). Its low two bits
   select one of four buckets. Every parsed flow is UDP, so the protocol need
   not be an additional hash input.
5. `backends` maps `(group, bucket)` to an explicit interface MAC, backend MAC
   and egress port. `deliver` rewrites Ethernet addresses, decrements TTL and
   recomputes the IPv4 checksum. `Emit` writes all headers followed by the
   unparsed payload.

[`demo.py`](demo.py) supplies host-installed table entries and sample packets.
The demo maps buckets 0 and 1 to server 1, and 2 and 3 to server 2. Four buckets
keep the configuration visible; this is not a claim of uniform distribution
for arbitrary traffic or a production-sized selection space.

Try changing the **bucket 1** entry in `POLICY` to server 2's MACs and port.
The first and third output lines should then report port 2; the second and
fourth remain unchanged. This illustrates why affinity is conditional on
configuration: remapping a bucket moves its existing flows. There is no flow
cache or automatic migration policy.

The block classes are reusable independently. For example, compile the
control and its declared extern dependencies without selecting a pipeline:

```python
from examples.load_balancer.program import Balance, checksum, flow_hash
from p4blo import edsl as p4

compiled = p4.BlockLibrary(Balance, externs=[checksum, flow_hash]).compile()
```

The `blocks` library collects the three block definitions and their shared
extern declarations. It does not select an architecture or a complete program;
`blocks.compile()` produces declarations without global header/metadata roots
or exported roles. This is a core protobuf `BlockLibrary` that can be
validated independently. Types follow the blocks' parameter and local
declarations.

`build()` separately calls `reference.assemble` with that library to select the
parser, control and deparser of the supplied architecture. Its metadata
contract gives fields such as `drop` and `egress_port` their host meaning;
the core sees ordinary block parameters and typed fields. The demo selects
`reference.load`, passes `supplied_registry()` to bind declared externs to
their implementations, and chooses `Switch(ports=4)`. Extern declarations
describe typed calls; the registry supplies their execution.

`ChecksumWords` and `FlowTuple` name the expression widths. The ordinary
Python helpers `checksum_data` and `flow_key` compose symbolic expressions;
`self.assign` records their uses in packet-time operations. Likewise,
`supported_packet` names an expression that `with self.if_(...)` turns into
a runtime branch.

## Behavioral contract

- Untagged Ethernet, IPv4 version 4 with IHL 5, and a complete eight-byte UDP
  header. Other EtherTypes/protocols and truncated required headers drop.
- IPv4 total length must be at least 28 and UDP length at least 8. TTL must
  exceed 1. Reserved flag, more-fragments flag and nonzero fragment offset
  drop; either setting of don't-fragment is accepted.
- The IPv4 checksum must equal the canonical checksum recomputed with its
  checksum field zeroed. Only TTL and the IPv4 checksum change within the IP
  packet; both IP addresses, all UDP fields and all payload bytes are preserved.
- Service and backend table misses drop. Explicit deny entries drop. Host
  configuration is trusted and supplies unique exact keys and valid action
  values. Tables have informational declared sizes, not enforced capacity.
- The demo uses a four-port switch (0–3). A configured out-of-range nine-bit
  egress port causes an architecture diagnostic and no output. There are no
  persistent extern cells; checksum and hash externs are stateless.

**Scope:** declared IPv4/UDP lengths are not reconciled with each other or
with the actual payload length. UDP checksums are neither checked nor changed.
Bytes beyond parsed headers are opaque and preserved, including trailing bytes.
There is no TCP support, IPv4 options, fragmentation, health checking, NAT,
server discovery, automatic rebalancing, consistent hashing, ICMP generation
or affinity guarantee across configuration changes. Unsupported header forms
fail closed; this bounded profile is not a full packet validator.

## Evidence and provenance

This is an original educational p4blo application. Its direct-server-return
request contract is deliberately independent of the existing corpus fixtures.

[`tests/examples/load_balancer/`](../../tests/examples/load_balancer/) contains
an IR golden, exact-length STF packet expectations, and independent wire
answers for every hash bucket, service/group isolation, configuration changes,
payload affinity, validation boundaries and adapter diagnostics. The checksum
and bitwise CRC reference in test support use Python's standard library and
explicit known answers, not the interpreter's extern implementations.

The application sequence checks complete outputs, diagnostics and stateless
extern observations in Python and through the shared Lean conformance harness.
The STF vectors also run through applicable P4 oracle harnesses. These are
finite execution checks, not a whole-program proof or a deployment benchmark.
