"""Run with: nix develop -c uv run python -m examples.firewall.demo."""

from examples.firewall.program import build
from p4blo import arch, stf
from p4blo.drt.state import snapshot

# 10.0.0.1:40000 -> 192.0.2.1:443, followed by its SYN-ACK.
# These fixed packets include valid IP/TCP checksums; SYN-ACK acknowledges SYN.
SYN = bytes.fromhex(
    "0000000000020000000000010800"
    "45000028007b400040066e530a000001c0000201"
    "9c4001bb00000000000000005002200025e50000"
)

REPLY = bytes.fromhex(
    "0000000000010000000000020800"
    "45000028007b400040066e53c00002010a000001"
    "01bb9c4000000000000000015012200025d40000"
)


def main() -> None:
    loaded = arch.load(build())
    policy = stf.to_entries(
        loaded.index,
        stf.parse("add services meta.server:0xc0000200/24 meta.server_port:443 allow()"),
    )
    entries = loaded.entries(policy)
    switch = arch.Switch(ports=4)
    for label, port, packet in (
        ("Inbound before SYN", 2, REPLY),
        ("Outbound SYN", 1, SYN),
        ("Inbound after SYN", 2, REPLY),
    ):
        outputs = switch.run(loaded, entries, port, packet)
        result = f"port {outputs[0][0]}, packet unchanged" if outputs else "drop"
        occupied = sum(value != 0 for value in snapshot(loaded)[2].values)
        print(f"{label}: {result}; occupied slots = {occupied}/16")


if __name__ == "__main__":
    main()
