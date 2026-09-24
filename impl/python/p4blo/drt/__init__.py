"""Differential random testing: Python against Lean (docs/design.md, "Lean
and differential random testing").

Corpus programs times random packets and table entries, both interpreters
run under the switch architecture, outputs compared, every divergence
reported with a case that can be replayed. The Lean side is a subprocess
speaking a line protocol; there is no FFI.

    case.py       a Case and its rendering as an STF vector
    generate.py   random cases from a seed, shaped by the program
    run.py        run a case on Python, on Lean over the pipe, and compare
    coverage.py   Lean rule tags over a campaign; parser states reached on Python
    fake_lean.py  a stand-in for `p4blo-lean run`, backed by Python
    __main__.py   `python -m p4blo.drt`
"""

from __future__ import annotations

from p4blo.drt.case import Case, case_to_stf
from p4blo.drt.coverage import RuleCoverage, rule_inventory
from p4blo.drt.generate import Generator, generate
from p4blo.drt.run import (
    Divergence,
    LeanRunner,
    Outcome,
    ProtocolError,
    Report,
    compare,
    compare_cases,
    run_python,
)

__all__ = [
    "Case",
    "Divergence",
    "Generator",
    "LeanRunner",
    "Outcome",
    "ProtocolError",
    "Report",
    "RuleCoverage",
    "case_to_stf",
    "compare",
    "compare_cases",
    "generate",
    "rule_inventory",
    "run_python",
]
