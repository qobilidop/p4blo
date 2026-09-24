# IPv4 router

A host installs routes; each admitted packet uses the longest matching prefix,
gets the selected interface/next-hop MAC addresses, loses one TTL hop and leaves
with an updated IPv4 header checksum. A missing route drops the packet.

## Run

From the repository root:

```sh
uv run python -m examples.router.demo
```

```text
specific route: port 2, TTL 63, destination MAC 00:00:00:00:02:02
broad route: port 1, TTL 63, destination MAC 00:00:00:00:01:01
no route: drop
```

The demo sends the same packet to `10.0.2.1` under three configurations: both
`10.0.0.0/8` and `10.0.2.0/24`, the broad route alone, then an empty table.
Change the `/24` action's `port:2` to `port:3` to redirect only the first case.
Ports in the demo's architecture are 0 through 3.

## Read the program

[`program.py`](program.py) declares Ethernet/IPv4 layouts, a two-state parser,
one routing table, one forwarding action and a deparser. `build()` returns the
IR; no packet processing runs while Python constructs the program.

`Route.apply` starts with `drop=True`, because control executes even after
parser failure. A complete supported IPv4 header and matching checksum open
the gate to table lookup. `forward` rewrites both MAC addresses from explicit
host parameters, decrements TTL and recomputes the checksum. Only that action
clears drop. `Emit` writes valid headers; the switch appends unconsumed payload.

[`demo.py`](demo.py) is the host: it supplies table entries and packet bytes to
the switch. This separation is why changing a route does not rebuild the IR.
The checksum helper is ordinary Python composition of typed eDSL expressions,
not a separate runtime implementation.

## Exact scope

- Untagged Ethernet with EtherType `0x0800`, version 4, IHL 5 and a complete
  20-byte IPv4 header. Options, fragments (MF or nonzero offset), reserved flag
  and other EtherTypes drop. DF may be set or clear.
- TTL 0 and 1 drop without wrapping; TTL 2 forwards as 1. The input checksum
  must equal the canonical Internet checksum over the other header words.
  A total-length field below 20 drops.
- The remaining bytes are opaque. Their length is not reconciled with the
  IPv4 total-length field; payload truncation and trailing padding are preserved.
  Input-envelope validation belongs to the caller for this educational profile.
  No transport checksum validation, ARP, ICMP generation, MTU handling or
  fragmentation is implemented.
- Host configuration is trusted. It can change the default action and install
  any representable MAC/port. Under the demo's four-port switch an out-of-range
  egress drops with an architecture diagnostic. Table size is descriptive,
  not an enforced capacity limit. The filter adapter agrees on fate but keeps
  original bytes, whereas the switch emits the rewritten packet.

## Evidence

[`tests/examples/router/`](../../tests/examples/router/) contains the generated
IR golden, exact-length STF answers and independent Python wire expectations.
The tests cover overlapping routes in both installation orders, misses, deny
overrides, checksum/TTL/profile boundaries, every short-header truncation,
opaque payloads and architecture port bounds. The shared suite reconstructs
the golden, runs the documented demo and compares generated cases with Lean;
the independent packet sequence also runs in both interpreters. The two
existing P4-oracle jobs discover the STF vectors. These are tested behaviors,
not a whole-router proof or a complete IPv4 implementation.
