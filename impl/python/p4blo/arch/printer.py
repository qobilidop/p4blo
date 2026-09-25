"""Printer support for an explicitly bound reference pipeline."""

from __future__ import annotations

from p4blo.arch.bindings import BoundIndex
from p4blo.printer import PACKET, PrintError, ProgramPrinter

MISSING_ROLE_NAMES = {
    "parser": "MyParser",
    "control": "MyIngress",
    "deparser": "MyDeparser",
}


class BoundProgramPrinter(ProgramPrinter):
    """Core declaration printer with reference pipeline fallback blocks."""

    def missing_roles(self) -> None:
        assert isinstance(self.index, BoundIndex)
        h, m = self.index.bindings.headers, self.index.bindings.metadata
        for role, name in MISSING_ROLE_NAMES.items():
            if role in self.roles:
                continue
            if name in self.index.program_names:
                raise PrintError(f"no block exported as {role!r} and the name {name!r} is taken")
            self.line(0)
            extra = self.role_params(role)
            match role:
                case "parser":
                    params = ", ".join(
                        [f"packet_in {PACKET}", f"out {h} hdr", f"inout {m} meta", *extra]
                    )
                    self.line(0, f"parser {name}({params}) {{")
                    self.line(1, "state start {")
                    self.line(2, "transition accept;")
                    self.line(1, "}")
                case "control":
                    params = ", ".join([f"inout {h} hdr", f"inout {m} meta", *extra])
                    self.line(0, f"control {name}({params}) {{")
                    self.line(1, "apply {")
                    self.line(1, "}")
                case _:
                    params = ", ".join([f"packet_out {PACKET}", f"in {h} hdr", *extra])
                    self.line(0, f"control {name}({params}) {{")
                    self.line(1, "apply {")
                    self.line(1, "}")
            self.line(0, "}")
