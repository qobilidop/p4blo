"""The architecture-free reference execution machinery.

`stmt.run_block` executes a block in an explicit environment. Optional
H/M calling-convention adapters live in p4blo.arch.entry.
Extern implementations and host inputs are supplied by the caller.
"""

from __future__ import annotations

from p4blo.interp.api import ExternBinding, ExternResult, Externs, InterpError
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits

__all__ = [
    "Bits",
    "ExternBinding",
    "ExternResult",
    "Externs",
    "InstalledEntries",
    "InterpError",
]
