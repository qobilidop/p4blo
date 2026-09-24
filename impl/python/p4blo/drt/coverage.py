"""Which parser states a packet reaches on the reference interpreter.

The generator's claim is that its packets get deep into the parser; this
is how the tests check it. `run_parser` keeps its environment to itself,
so the run is repeated here with the environment in hand: the parser's
revisit bookkeeping (`Env.visits`) records every (block, state) entered,
sub-parsers included.
"""

from __future__ import annotations

from dataclasses import dataclass

from p4blo.arch import Loaded
from p4blo.interp.env import Env
from p4blo.interp.errors import ParseError
from p4blo.interp.packet import Packet
from p4blo.interp.stmt import run_states

__all__ = ["ParserVisit", "parser_visits"]


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
