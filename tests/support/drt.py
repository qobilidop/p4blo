"""Shared drt fixtures and campaign helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.builder import AssemblyBuilder
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import (
    Case,
    LeanRunner,
    Outcome,
    compare_cases,
)
from p4blo.edsl.core import bit

CORPUS = Path(__file__).resolve().parents[2] / "tests/programs/corpus"

PROGRAMS = sorted(p for p in CORPUS.iterdir() if (p / f"{p.name}.txtpb").exists())

FAKE: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]

PORTS = 4

# A program with what the corpus lacks: masked and range key sets in a
# select, an exact table with a key narrower than a nibble, and a ternary
# table keyed on an 11-bit field, so that entries need priorities and STF
# needs its binary form.
MIXED = """
errors: "NoError" errors: "PacketTooShort" errors: "NoMatch" errors: "StackOutOfBounds"
errors: "HeaderTooShort" errors: "ParserTimeout" errors: "ParserInvalidArgument"
header_types {
  name: "h_t"
  fields { name: "kind" type { bits: 8 } }
  fields { name: "a" type { bits: 11 } }
  fields { name: "b" type { bits: 5 } }
}
header_types { name: "x_t" fields { name: "v" type { bits: 16 } } }
struct_types {
  name: "H"
  fields { name: "h" type { header: "h_t" } }
  fields { name: "x" type { header: "x_t" } }
}
struct_types {
  name: "M"
  fields { name: "ingress_port" type { bits: 9 } }
  fields { name: "egress_spec" type { bits: 9 } }
}
headers: "H"
metadata: "M"
blocks {
  name: "P" kind: BLOCK_KIND_PARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_OUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  states {
    name: "start"
    body { extract { target { member { base { var: "hdr" } field: "h" } } } }
    transition { select {
      keys { member { base { member { base { var: "hdr" } field: "h" } } field: "kind" } }
      keys { member { base { member { base { var: "hdr" } field: "h" } } field: "b" } }
      cases {
        sets { masked {
          value { bits { width: 8 value: "16" } } mask { bits { width: 8 value: "240" } } } }
        sets { dont_care {} }
        target { state: "parse_x" }
      }
      cases {
        sets { range { lo { bits { width: 8 value: "1" } } hi { bits { width: 8 value: "3" } } } }
        sets { exact { bits { width: 5 value: "7" } } }
        target { state: "parse_x" }
      }
      cases {
        sets { range { lo { bits { width: 8 value: "1" } } hi { bits { width: 8 value: "3" } } } }
        sets { dont_care {} }
        target { accept {} }
      }
      cases { sets { dont_care {} } sets { dont_care {} } target { reject {} } }
    } }
  }
  states {
    name: "parse_x"
    body { extract { target { member { base { var: "hdr" } field: "x" } } } }
    transition { direct { accept {} } }
  }
  start_state: "start"
}
blocks {
  name: "C" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  actions { name: "NoAction" }
  actions {
    name: "fwd"
    params { name: "port" type { bits: 9 } direction: DIRECTION_NONE }
    body { assign { target { member { base { var: "meta" } field: "egress_spec" } }
                    value { var: "port" } } }
  }
  actions {
    name: "drop"
    body { assign { target { member { base { var: "meta" } field: "egress_spec" } }
                    value { literal { bits { width: 9 value: "511" } } } } }
  }
  tables {
    name: "t_exact"
    keys { expr { member { base { member { base { var: "hdr" } field: "h" } } field: "kind" } }
           match_kind: MATCH_KIND_EXACT }
    keys { expr { member { base { member { base { var: "hdr" } field: "h" } } field: "b" } }
           match_kind: MATCH_KIND_EXACT }
    actions: "fwd" actions: "NoAction"
  }
  tables {
    name: "t_tern"
    keys { expr { member { base { member { base { var: "hdr" } field: "h" } } field: "a" } }
           match_kind: MATCH_KIND_TERNARY }
    keys { expr { member { base { member { base { var: "hdr" } field: "x" } } field: "v" } }
           match_kind: MATCH_KIND_EXACT }
    actions: "fwd" actions: "drop"
    default_action { action: "drop" }
  }
  tables {
    name: "t_lpm"
    keys { expr { member { base { member { base { var: "hdr" } field: "x" } } field: "v" } }
           match_kind: MATCH_KIND_LPM }
    actions: "fwd" actions: "NoAction"
  }
  body { apply { table: "t_exact" } }
  body { conditional {
    condition { is_valid { header { member { base { var: "hdr" } field: "x" } } } }
    then { apply { table: "t_tern" } }
    then { apply { table: "t_lpm" } }
  } }
}
blocks {
  name: "D" kind: BLOCK_KIND_DEPARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_IN }
  body { emit { value { member { base { var: "hdr" } field: "h" } } } }
  body { emit { value { member { base { var: "hdr" } field: "x" } } } }
}
exports { role: "parser" block: "P" }
exports { role: "ingress" block: "C" }
exports { role: "deparser" block: "D" }
"""


def golden(program_dir: Path) -> apb.BlockAssembly:
    return arch_wire.load_text(program_dir / f"{program_dir.name}.txtpb")


def mixed() -> apb.BlockAssembly:
    program = arch_wire.load_text(MIXED)
    assert validator.validate(program) == []
    return program


def all_states(program: apb.BlockAssembly) -> set[tuple[str, str]]:
    return {(b.name, s.name) for b in program.blocks for s in b.states}


def lean_report(
    program: apb.BlockAssembly, cases: list[Case], lean_binary: Path, tmp_path: Path, ports: int = 4
) -> tuple[Outcome, ...]:
    """Every case on Python and on Lean; the report and the Lean outcomes."""
    loaded = v1model.load(program)
    program_json = tmp_path / f"{program.name}.json"
    program_json.write_text(arch_wire.dump_json(program))
    seen: list[Outcome] = []
    with LeanRunner([lean_binary], program_json, ports) as runner:

        def run_lean(case: Case) -> Outcome:
            seen.append(runner.run(case))
            return seen[-1]

        report = compare_cases(program.name, loaded, cases, ports, run_lean)
    assert report.divergences == [], report.summary()
    return tuple(seen)


def fate_program() -> apb.BlockAssembly:
    """Drop, unicast and an attempted egress redirection, echoing ingress."""
    p = AssemblyBuilder("fate")
    h = p.header("h_t", redirect=bit(8), drop=bit(8), port=bit(16))
    p.headers = p.struct("headers", h=h)
    p.metadata = p.struct("metadata", ingress_port=bit(9), egress_spec=bit(9))
    with p.parser("P") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.h)
            s.accept()
    with p.control("C") as c:
        with c.body() as b:
            b.assign(c.meta.egress_spec, c.hdr.h.port.cast(bit(9)))
            with b.if_(c.hdr.h.drop != 0):
                b.assign(c.meta.egress_spec, 511)
            b.assign(c.hdr.h.port, c.meta.ingress_port.cast(bit(16)))
    with p.control("E") as e:
        with e.body() as b:
            with b.if_(e.hdr.h.redirect != 0):
                b.assign(e.meta.egress_spec, 1)
    p.export("egress", "E")
    with p.deparser("D") as d:
        with d.body() as b:
            b.emit(d.hdr.h)
    p.export("parser", "P")
    p.export("ingress", "C")
    p.export("deparser", "D")
    return p.build()
