"""What a differential campaign exercised.

Two measures live here. `RuleCoverage` is the adequacy criterion: the rule
tags of the Lean semantics (`P4bloIR.Coverage`) that the Lean side reports
for every request, accumulated over a campaign and compared with the
inventory `p4blo-lean coverage-inventory` prints, so Python never hard-codes
the list. The criterion is the specification's rules, not the Python
interpreter's, which is the peer under test.

`parser_visits` is the older, Python-side measure: which parser states a
packet reaches on the reference interpreter. The generator's claim is that
its packets get deep into the parser; this is how the tests check it.
`run_parser` keeps its environment to itself, so the run is repeated here
with the environment in hand: the parser's revisit bookkeeping
(`Env.visits`) records every (block, state) entered, sub-parsers included.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from p4blo.arch import Loaded
from p4blo.interp.env import Env
from p4blo.interp.errors import ParseError
from p4blo.interp.packet import Packet
from p4blo.interp.stmt import run_states

__all__ = ["ParserVisit", "RuleCoverage", "parser_visits", "rule_inventory"]


@dataclass
class RuleCoverage:
    """Rule tags hit over a campaign, with how many requests hit each."""

    hits: Counter[str] = field(default_factory=Counter)
    # Requests whose reply carried a coverage list, possibly empty.
    reported: int = 0
    # Requests whose reply carried none: an older peer, or the fake.
    unreported: int = 0

    def add(self, tags: Iterable[str] | None) -> None:
        """Record one reply's tags; `None` means the reply had no list."""
        if tags is None:
            self.unreported += 1
            return
        self.reported += 1
        self.hits.update(set(tags))

    def update(self, other: RuleCoverage) -> None:
        """Merge another campaign's coverage into this one."""
        self.hits.update(other.hits)
        self.reported += other.reported
        self.unreported += other.unreported

    def unhit(self, inventory: Iterable[str]) -> list[str]:
        """The inventory's tags no request hit, sorted."""
        return sorted(set(inventory) - set(self.hits))

    def unknown(self, inventory: Iterable[str]) -> list[str]:
        """Tags a reply named that the inventory does not list, sorted."""
        return sorted(set(self.hits) - set(inventory))

    def describe(self, inventory: dict[str, str]) -> str:
        """Hit and unhit tags against the inventory, one per line."""
        unhit = self.unhit(inventory)
        lines = [
            f"rule coverage: {len(inventory) - len(unhit)} of {len(inventory)} tags hit "
            f"over {self.reported} requests"
        ]
        if self.unreported:
            lines.append(f"  {self.unreported} replies carried no coverage (an older or fake peer)")
        lines += [
            f"  hit   {tag} ({self.hits[tag]})" for tag in sorted(inventory) if tag in self.hits
        ]
        lines += [f"  unhit {tag}: {inventory[tag]}" for tag in unhit]
        lines += [f"  not in the inventory: {tag}" for tag in self.unknown(inventory)]
        return "\n".join(lines)


def rule_inventory(command: Sequence[str | Path], timeout: float = 30) -> dict[str, str]:
    """Every rule tag with its docstring, from `<command> coverage-inventory`.

    `command` is the executable and any leading arguments, as for
    `LeanRunner`. Each output line is a tag, a tab, and the docstring.
    """
    result = subprocess.run(
        [*(str(c) for c in command), "coverage-inventory"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    inventory: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        tag, sep, doc = line.partition("\t")
        if not sep or not tag or tag in inventory:
            raise ValueError(f"bad coverage inventory line: {line!r}")
        inventory[tag] = doc
    return inventory


@dataclass(frozen=True)
class ParserVisit:
    # (block name, state name) of every state entered.
    states: frozenset[tuple[str, str]]
    accepted: bool
    # A name from Program.errors; "NoError" on an accept or a plain reject.
    error: str


def parser_visits(loaded: Loaded, packet: bytes, ingress_port: int = 0) -> ParserVisit:
    index = loaded.index
    decl = index.blocks[loaded.block("parser")]
    metadata = loaded.metadata.zero()
    loaded.metadata.write(metadata, "ingress_port", ingress_port)
    env = Env.for_block(index, decl, loaded.externs, packet=Packet(packet))
    env.vars[decl.params[1].name] = metadata
    accepted, error = True, "NoError"
    try:
        run_states(decl, env)
    except ParseError as e:
        accepted, error = False, e.error.name
    return ParserVisit(frozenset(env.visits), accepted, error)
