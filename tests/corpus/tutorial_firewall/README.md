# Tutorial stateful firewall

Typed Python adaptation of Stephen Ibanez's Apache-2.0 tutorial solution,
[`p4lang/tutorials@098ce0b7ae486f5b747a6b53ad1585f0d977b42e`](https://github.com/p4lang/tutorials/blob/098ce0b7ae486f5b747a6b53ad1585f0d977b42e/exercises/firewall/solution/firewall.p4).
The unchanged original is pinned separately in `tests/oracle/firewall.p4`;
the repository's root LICENSE contains Apache-2.0.

The two 4096-bit Bloom filters preserve the tutorial's false positives.
Only outbound SYN sets bits; inbound traffic hashes the reversed tuple
and requires both bits, but only when the direction table hits. There is
no connection timeout, FIN deletion or transport checksum verification.
The parser extracts fixed 20-byte IPv4/TCP headers regardless of options.
Routing rewrites MAC addresses and decrements TTL with wraparound; the
final stage recomputes IPv4 checksum even though verification is absent.

The port uses ordinary actions, tables, conditionals, register calls and
byte-aligned full CRC externs. Masking each CRC by 4095 implements the
original base-zero modulo-4096 hash range. Empty verify/egress stages
disappear; checksum computation is last in the combined control.

`connection.stf` reuses the original pinned smoke packets and configuration
with only table/key/action names mapped to the IR metadata contract.
`collisions.stf` pins a two-flow Bloom false positive: internal ports 749
and 13602 independently set the two cells needed by unsolicited port
12346. One populated cell must still reject; two must accept. Distinct
TCP sequence numbers prevent earlier outputs satisfying later expectations.

`tests/test_firewall.py` adds exact register-state checks, known indices,
packet-shape/direction cases, and original-source comparisons. SpecTec's
known odd-byte CRC32 bug permutes these register indices consistently, so
packet-only examples can pass despite wrong state. See
`docs/notes/crc-contract.md` and `docs/notes/firewall-port.md` for assurance
limits. This increment is not a Lean-authored example or a correctness proof.
