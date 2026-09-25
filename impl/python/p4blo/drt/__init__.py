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
    families.py   program families aimed at the rules, driven by a Chooser
    guided.py     coverage-guided campaigns over those families
    fake_lean.py  a stand-in for `p4blo-lean run`, backed by Python
    __main__.py   `python -m p4blo.drt`

Coverage-guided generation. The families of `families.py` build programs
from named decisions, and `python -m p4blo.drt guided <family> <budget>`
runs one against Lean, reads the rule tags of every reply, and weights the
next programs' decisions toward options whose target tags are unhit; it
counts the (tag, feature) pairs reached, the one-feature-sensitive
criterion of ESMeta's JESTfs. It is deterministic by `--seed`;
`--unguided` is the uniform baseline. `guided.py` has the weights, the
command line and the measurement against the baseline.
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
