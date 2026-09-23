"""Pinned original firewall fixture: no p4blo printer or IR translation.

Source: p4lang/tutorials@098ce0b7ae486f5b747a6b53ad1585f0d977b42e,
exercises/firewall/solution/firewall.p4, Apache-2.0 (root LICENSE).
Packet expectations are independent known answers, not interpreter output.
"""

import hashlib
from pathlib import Path

from p4blo import stf
from tests.oracle.bmv2.run import Phase, Plan

SOURCE = Path(__file__).with_suffix(".p4")
SHA256 = "5e1286ddbbc583d00fb5cbbb7c5f7a07076b4c200b0e9ed931c58e6b03230b19"

# Full fixed Ethernet/IPv4/TCP headers. Sequence numbers distinguish the
# rejected ACK from the established ACK without changing their five-tuple.
# This matters because both external runners compare aggregate output queues.
VECTOR = SOURCE.with_suffix(".stf").read_text()

COMMANDS = [
    "table_add MyIngress.ipv4_lpm MyIngress.ipv4_forward 10.0.0.1/32 => 00:00:00:00:00:11 1",
    "table_add MyIngress.ipv4_lpm MyIngress.ipv4_forward 10.0.0.2/32 => 00:00:00:00:00:22 2",
    "table_add MyIngress.check_ports MyIngress.set_direction 1 2 => 0",
    "table_add MyIngress.check_ports MyIngress.set_direction 2 1 => 1",
]

# This is deliberately a fixed-profile adapter, not a general STF compiler.
# Keep both control-plane encodings reviewed together; reject fixture drift.
CONFIGURATION = (
    "add MyIngress.ipv4_lpm 32 hdr.ipv4.dstAddr:0x0a000001 "
    "MyIngress.ipv4_forward(dstAddr:17, port:1)",
    "add MyIngress.ipv4_lpm 32 hdr.ipv4.dstAddr:0x0a000002 "
    "MyIngress.ipv4_forward(dstAddr:34, port:2)",
    "add MyIngress.check_ports standard_metadata.ingress_port:1 "
    "standard_metadata.egress_spec:2 MyIngress.set_direction(dir:0)",
    "add MyIngress.check_ports standard_metadata.ingress_port:2 "
    "standard_metadata.egress_spec:1 MyIngress.set_direction(dir:1)",
)


def source() -> str:
    data = SOURCE.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("original firewall source differs from the pinned upstream bytes")
    return data.decode()


def plan(vector: str = VECTOR) -> Plan:
    lines = vector.splitlines()
    if tuple(lines[:4]) != CONFIGURATION:
        raise ValueError("firewall profile configuration changed; review both oracle encodings")
    statements = stf.parse("\n".join(lines[4:]))
    if any(not isinstance(s, stf.Packet | stf.Expect) for s in statements):
        raise ValueError("firewall profile permits only packets/expectations after initial rules")
    return Plan(
        phases=[
            Phase(
                commands=list(COMMANDS),
                packets=[s for s in statements if isinstance(s, stf.Packet)],
                expects=[s for s in statements if isinstance(s, stf.Expect)],
            )
        ],
        ports=[1, 2],
        notes=[],
    )
