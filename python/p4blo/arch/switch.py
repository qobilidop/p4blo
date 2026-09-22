"""The switch architecture: parser, control, deparser, over a few ports.

The switch runs all three blocks. The packet that leaves is the deparser's
bytes followed by the payload the parser did not consume. Its fate is the
metadata the control wrote: `drop` wins over everything, then `flood` sends
the packet to every port but the one it arrived on, otherwise it goes to
`egress_port` alone.
"""

from __future__ import annotations

from p4blo import interp
from p4blo.arch.loader import Loaded
from p4blo.interp.tables import InstalledEntries


class Switch:
    """A switch with `ports` ports, numbered from zero."""

    def __init__(self, ports: int) -> None:
        self.ports = ports
        self.diagnostics: list[str] = []

    def run(
        self, loaded: Loaded, entries: InstalledEntries, ingress_port: int, packet: bytes
    ) -> list[tuple[int, bytes]]:
        index, externs, meta = loaded.index, loaded.externs, loaded.metadata

        m = meta.zero()
        meta.write(m, "ingress_port", ingress_port)
        parsed = interp.run_parser(index, loaded.block("parser"), packet, m, externs)
        if parsed.consumed_bits % 8:
            self.diagnostics.append(
                f"parser consumed {parsed.consumed_bits} bits, not whole bytes; packet dropped"
            )
            return []
        meta.write(parsed.metadata, "parser_error", parsed.error)

        headers, m = interp.run_control(
            index, loaded.block("control"), parsed.headers, parsed.metadata, entries, externs
        )

        emitted = interp.run_deparser(index, loaded.block("deparser"), headers, externs)
        out = emitted + packet[parsed.consumed_bits // 8 :]

        if meta.flag(m, "drop"):
            return []
        if meta.flag(m, "flood"):
            return [(port, out) for port in range(self.ports) if port != ingress_port]
        return [(meta.number(m, "egress_port"), out)]
