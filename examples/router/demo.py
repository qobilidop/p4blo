"""Run: uv run python -m examples.router.demo."""

from examples.router.program import build
from p4blo import arch, stf

POLICY = """
add routes hdr.ipv4.dst:0x0a000000/8 forward(src_mac:0x100, dst_mac:0x101, port:1)
add routes hdr.ipv4.dst:0x0a000200/24 forward(src_mac:0x200, dst_mac:0x202, port:2)
"""
# Ethernet + IPv4 (10.0.0.1 -> 10.0.2.1, TTL 64) + opaque "hello" payload.
PACKET = bytes.fromhex(
    "000000000002000000000001080045000019007b4000401124580a0000010a00020168656c6c6f"
)


def main() -> None:
    loaded = arch.load(build())
    switch = arch.Switch(ports=4)
    for label, policy in (
        ("specific route", POLICY),
        ("broad route", POLICY.splitlines()[1]),
        ("no route", ""),
    ):
        entries = loaded.entries(stf.to_entries(loaded.index, stf.parse(policy)))
        outputs = switch.run(loaded, entries, 0, PACKET)
        if outputs:
            port, packet = outputs[0]
            print(f"{label}: port {port}, TTL {packet[22]}, destination MAC {packet[:6].hex(':')}")
        else:
            print(f"{label}: drop")


if __name__ == "__main__":
    main()
