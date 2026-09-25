"""Optional H/M calling-convention adapters over core block execution."""

from p4blo.arch.entry.control import run_control
from p4blo.arch.entry.deparser import run_deparser
from p4blo.arch.entry.outcome import ParseOutcome
from p4blo.arch.entry.parser import run_parser

__all__ = ["ParseOutcome", "run_control", "run_deparser", "run_parser"]
