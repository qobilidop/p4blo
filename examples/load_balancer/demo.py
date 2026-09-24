"""Run: uv run python -m examples.load_balancer.demo."""

from struct import pack

from examples.load_balancer.program import build
from p4blo import arch, stf

POLICY = """
add services hdr.ipv4.dst:0x0a000064 hdr.udp.dst_port:8080 select_group(group:1)
add backends meta.group:1 meta.bucket:0 deliver(src_mac:0x100, dst_mac:0x101, port:1)
add backends meta.group:1 meta.bucket:1 deliver(src_mac:0x100, dst_mac:0x101, port:1)
add backends meta.group:1 meta.bucket:2 deliver(src_mac:0x200, dst_mac:0x202, port:2)
add backends meta.group:1 meta.bucket:3 deliver(src_mac:0x200, dst_mac:0x202, port:2)
"""
# Ethernet + IPv4: client 192.0.2.1 -> VIP 10.0.0.100; TTL 64, 32 IP bytes.
PREFIX = bytes.fromhex("000000000002000000000001080045000020007b400040116dedc00002010a000064")


def main() -> None:
    loaded = arch.load(build())
    entries = loaded.entries(stf.to_entries(loaded.index, stf.parse(POLICY)))
    switch = arch.Switch(ports=4)
    for source_port, destination_port, payload in (
        (10000, 8080, b"ping"),
        (10240, 8080, b"ping"),
        (10000, 8080, b"pong"),
        (10000, 8081, b"ping"),
    ):
        packet = PREFIX + pack("!HHHH", source_port, destination_port, 12, 0) + payload
        outputs = switch.run(loaded, entries, 0, packet)
        label = f"UDP {source_port} -> {destination_port}, {payload.decode()}"
        if outputs:
            port, result = outputs[0]
            print(f"{label}: port {port}, backend MAC {result[:6].hex(':')}, TTL {result[22]}")
        else:
            print(f"{label}: drop")


if __name__ == "__main__":
    main()
