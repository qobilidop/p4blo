"""The filter architecture: parser, control, and the packet out as it came.

A filter decides; it does not rewrite. It runs the program's parser and
control and acts on the metadata they leave: `drop` discards the packet,
otherwise the original bytes leave on `egress_port`. There is no deparser,
so whatever the control did to the headers never reaches the wire; a
program that rewrites headers still runs here unchanged, its rewrites
merely go unseen.

The filter has no port count: any `bit<9>` egress port passes through, and
an ingress port that does not fit `bit<9>` is the caller's error, a
`ValueError` before anything runs (docs/decisions.md, "Port rules").
"""

from __future__ import annotations

from p4blo import interp
from p4blo.arch.loader import Loaded
from p4blo.interp.tables import InstalledEntries


class Filter:
    """A packet filter over a loaded program: one packet in, at most one out."""

    def __init__(self) -> None:
        self.diagnostics: list[str] = []

    def run(
        self, loaded: Loaded, entries: InstalledEntries, ingress_port: int, packet: bytes
    ) -> list[tuple[int, bytes]]:
        index, externs, meta = loaded.index, loaded.externs, loaded.metadata
        if not 0 <= ingress_port < 2**9:
            raise ValueError(f"ingress_port {ingress_port} does not fit in bit<9>")

        m = meta.zero()
        meta.write(m, "ingress_port", ingress_port)
        parsed = interp.run_parser(index, loaded.block("parser"), packet, m, externs)
        if parsed.consumed_bits % 8:
            self.diagnostics.append(
                f"parser consumed {parsed.consumed_bits} bits, not whole bytes; packet dropped"
            )
            return []
        meta.write(parsed.metadata, "parser_error", parsed.error)

        _, m = interp.run_control(
            index, loaded.block("control"), parsed.headers, parsed.metadata, entries, externs
        )

        if meta.flag(m, "drop"):
            return []
        return [(meta.number(m, "egress_port"), packet)]
