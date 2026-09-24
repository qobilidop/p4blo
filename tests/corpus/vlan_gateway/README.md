# VLAN access gateway

A complete Python eDSL example for the project's homepage. A host-installed
policy admits a single tagged frame from a particular ingress port and VLAN
to a particular destination MAC. The action selects an egress port, removes
the VLAN tag, restores the encapsulated EtherType and records one admission.
Everything after the parsed headers is preserved byte for byte.

The example is original to p4blo. It uses existing core constructs and extern
contracts; no eDSL or interpreter extension is needed.

| Artifact | Purpose |
|---|---|
| [vlan_gateway.py](vlan_gateway.py) | Complete typed Python source; `build()` returns the IR |
| [vlan_gateway.txtpb](vlan_gateway.txtpb) | Generated IR golden, checked against the source |
| [gateway.stf](gateway.stf) | Host policy and independent packet expectations, used by both P4 oracles |
| [demo.py](demo.py) | Three packets on one persistent four-port switch |
| [test_vlan_gateway.py](../../test_vlan_gateway.py) | Independent packet, diagnostic and full-counter-state answers in Python and Lean |

## Try it

From the repository root:

After the repository [development setup](../../../README.md#development):

```sh
uv run python -m tests.corpus.vlan_gateway.demo
```

```text
VLAN 42: port 2, 34 bytes, tag removed; admissions[2] = 1
VLAN 43: drop; admissions[2] = 1
VLAN 42: port 2, 34 bytes, tag removed; admissions[2] = 2
```

The table entry matches ingress 1, VLAN 42 and destination MAC
`00:00:00:00:00:02`, and calls `deliver(port=2)`. Each input has 38 bytes;
an admitted output has 34. The 20-byte payload is opaque to this program.
The demo's STF string configures the host table; packet processing itself
is entirely the Python eDSL source. Reusing `loaded` preserves counter state.

## Exact boundary

- Only outer EtherType `0x8100`, VLAN IDs 1–4094 and a complete four-byte
  tag qualify. Untagged, priority-tagged (VID 0), reserved VID 4095,
  truncated and outer service-tagged frames drop. Priority and
  drop-eligibility bits do not affect lookup.
- Inner EtherTypes `0x8100` and `0x88a8` drop, so the gateway does not
  turn stacked tags into an apparently untagged output. Other inner
  EtherTypes and all payload bytes are left uninterpreted. This is not a
  complete IEEE 802.1Q implementation, an IP validator or a learning switch.
- Controls run after parser failure. Initializing `drop=True` before the
  validity guard is essential. In this two-state parser, valid VLAN implies
  successful Ethernet and VLAN extraction; no later parser operation can
  reject after the VLAN has become valid. A parser extension must revisit
  this argument, especially if it adds `verify` after the final extraction.
- The mutable table defaults to `deny`. The host is trusted to install
  appropriate entries/defaults and valid destination ports; this program
  does not enforce host configuration or prohibit forwarding to ingress.
- `admissions[port]` counts action decisions, not physical transmissions.
  Under the four-port adapter, an installed port 4 or 511 increments its
  counter and then drops with an architecture diagnostic. Tests pin that
  distinction and all 512 cells, including counters untouched by drops.
- The switch deparses valid headers and appends unconsumed payload. The
  filter adapter makes the same fate decisions but keeps original bytes.
  P4 oracle STF tests observe packets, not counter state; state expectations
  are checked independently against Python and Lean.

The homepage's highlighted source is generated directly from this file by
`scripts/render-website-example.py`; it contains no elisions or parallel
implementation. The ordinary corpus gate, both P4 oracles and required
`test_lean_agrees` discovery automatically include this program.
