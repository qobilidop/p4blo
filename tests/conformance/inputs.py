"""The fixed input set of the exported conformance corpus.

`python -m p4blo.conformance export` answers these on Lean and writes one
fixture per input under `fixtures/`. Three kinds, each named in the
fixture's `source` header:

- `stf`: every corpus program and public example with each of its STF
  vectors, one fixture per vector file, its packets as requests in order
  with the entries installed before each, as the vector replays them.
- `drt`: every corpus program and example with the DRT's generated host
  entries and packets, `p4blo.drt.generate.generate` at fixed seeds.
- `family`: the generated program families of `tests/oracle/generated.py`
  at fixed seeds, through its `materialize`, with the switch it uses there.

The fixtures hold the concrete programs and requests, so a later change to
a generator changes no check; it changes what the next export writes.
"""

from __future__ import annotations

from pathlib import Path

from p4blo import ir, stf
from p4blo.conformance import Input
from p4blo.drt.case import Case
from p4blo.drt.generate import generate
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]
PORTS = 4
# Two seeds of eight cases per program: enough to cross every program's
# tables and parser with generated entries, small enough to read.
DRT_SEEDS = (1, 2)
DRT_COUNT = 8
# `materialize` picks the family by the seed modulo the number of
# families, so consecutive seeds spread over all of them; how many each
# family gets follows from `generated.FAMILIES`, not from this range.
FAMILY_SEEDS = range(36)


def programs() -> list[tuple[str, Path]]:
    """Every corpus program and public example, as (label, golden)."""
    corpus = sorted((ROOT / "tests/corpus").glob("*/*.txtpb"))
    examples = sorted((ROOT / "tests/examples").glob("*/program.txtpb"))
    return [(f"corpus-{p.parent.name}", p) for p in corpus if p.stem == p.parent.name] + [
        (f"example-{p.parent.name}", p) for p in examples
    ]


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def stf_cases(program: pb.Program, vector: Path) -> tuple[Case, ...]:
    cases: list[Case] = []

    def collect(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        cases.append(Case(entries, port, packet))
        return []

    # Replay only groups packets with the entries installed before them;
    # its expectation failures against the empty answers are irrelevant.
    stf.replay(ir.Index.build(program), stf.parse(vector.read_text()), collect)
    return tuple(cases)


def stf_inputs() -> list[Input]:
    found: list[Input] = []
    for label, golden in programs():
        program = ir.load_text(golden)
        for vector in sorted(golden.parent.glob("*.stf")):
            source = {"kind": "stf", "program": _relative(golden), "vector": _relative(vector)}
            cases = stf_cases(program, vector)
            found.append(Input(f"stf-{label}-{vector.stem}", source, program, cases, PORTS))
    return found


def drt_inputs() -> list[Input]:
    found: list[Input] = []
    for label, golden in programs():
        program = ir.load_text(golden)
        index = ir.Index.build(program)
        for seed in DRT_SEEDS:
            source = {
                "kind": "drt",
                "program": _relative(golden),
                "generator": "p4blo.drt.generate.generate",
                "seed": seed,
                "count": DRT_COUNT,
            }
            cases = tuple(generate(index, seed, DRT_COUNT, PORTS))
            found.append(Input(f"drt-{label}-seed{seed}", source, program, cases, PORTS))
    return found


def family_inputs() -> list[Input]:
    from tests.oracle import generated

    found: list[Input] = []
    for seed in FAMILY_SEEDS:
        g = generated.materialize(seed)
        source = {
            "kind": "family",
            "generator": "tests/oracle/generated.py materialize",
            "seed": seed,
            "family": g.family,
            "description": g.description,
        }
        name = f"family-seed{seed:02d}"
        found.append(Input(name, source, g.program, g.cases, generated.SWITCH_PORTS))
    return found


def inputs() -> list[Input]:
    return [*stf_inputs(), *drt_inputs(), *family_inputs()]
