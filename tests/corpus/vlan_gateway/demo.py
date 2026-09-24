"""Run from the repository: uv run python -m tests.corpus.vlan_gateway.demo."""

from p4blo import arch, stf
from p4blo.drt.state import snapshot
from tests.corpus.vlan_gateway.vlan_gateway import build


def main() -> None:
    loaded = arch.load(build())
    policy = stf.to_entries(
        loaded.index,
        stf.parse(
            "add access meta.ingress_port:1 hdr.vlan.vid:42 "
            "hdr.ethernet.dst:0x000000000002 deliver(port:2)"
        ),
    )
    entries = loaded.entries(policy)
    switch = arch.Switch(ports=4)
    payload = bytes.fromhex("4500001400010000401166d60a0000010a000002")
    for vlan in (42, 43, 42):
        packet = bytes.fromhex("0000000000020000000000018100")
        packet += vlan.to_bytes(2, "big") + bytes.fromhex("0800") + payload
        output = switch.run(loaded, entries, 1, packet)
        result = (
            f"port {output[0][0]}, {len(output[0][1])} bytes, tag removed" if output else "drop"
        )
        print(f"VLAN {vlan}: {result}; admissions[2] = {snapshot(loaded)[0].values[2]}")


if __name__ == "__main__":
    main()
