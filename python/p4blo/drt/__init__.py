"""Differential random testing: Python against Lean (docs/design.md, "Lean
and differential random testing").

Corpus programs times random packets and table entries, both interpreters
run under the switch architecture, outputs compared, every divergence
reported with a case that can be replayed.

    case.py       a Case and its rendering as an STF vector
    generate.py   random cases from a seed, shaped by the program
    coverage.py   which parser states a packet reaches on Python
"""

from __future__ import annotations

from p4blo.drt.case import Case, case_to_stf
from p4blo.drt.generate import Generator, generate

__all__ = ["Case", "Generator", "case_to_stf", "generate"]
