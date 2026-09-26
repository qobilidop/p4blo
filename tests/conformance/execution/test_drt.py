"""Differential random testing: the generator, the pipe harness, and the
replayable vectors it writes (docs/design.md, "Lean and differential random
testing").

The harness is exercised without Lean through `p4blo.drt.fake_lean`, which
speaks the pipe protocol with the Python interpreter behind it. The real
Lean binary is used when it is built and has a `run` mode, and skipped
with the reason otherwise.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

from p4blo import stf
from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.builder import AssemblyBuilder
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import (
    Case,
    Generator,
    LeanRunner,
    Outcome,
    ProtocolError,
    case_to_stf,
    compare,
    compare_cases,
    generate,
    run_python,
)
from p4blo.drt.coverage import parser_visits
from p4blo.drt.run import parse_reply, python_outcome
from p4blo.drt.state import snapshot
from p4blo.edsl.core import bit
from p4blo.v0 import p4blo_pb2 as pb

CORPUS = Path(__file__).resolve().parents[3] / "tests/programs/corpus"
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


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def test_generation_is_deterministic_per_seed() -> None:
    index = BoundIndex.build(golden(CORPUS / "forwarder"))
    first = generate(index, 7, 50)
    assert generate(index, 7, 50) == first
    assert generate(index, 8, 50) != first
    assert all(0 <= case.ingress_port < 4 for case in first)


@pytest.mark.parametrize("program_dir", PROGRAMS, ids=lambda p: p.name)
def test_every_generated_entries_installs_on_the_corpus(program_dir: Path) -> None:
    loaded = v1model.load(golden(program_dir))
    for case in generate(loaded.index, 3, 100):
        loaded.entries(case.entries)


def test_every_generated_entries_installs_and_covers_every_kind() -> None:
    loaded = v1model.load(mixed())
    kinds: Counter[str] = Counter()
    defaults = 0
    for case in generate(loaded.index, 5, 200):
        loaded.entries(case.entries)
        for te in case.entries.tables:
            defaults += te.HasField("default_action")
            for entry in te.entries:
                for kv in entry.keys:
                    kinds[kv.WhichOneof("kind") or "?"] += 1
                if te.table == "t_tern":
                    assert entry.priority >= 0
                else:
                    assert entry.priority == 0
    assert set(kinds) == {"exact", "lpm", "ternary"}
    assert defaults > 0


@pytest.mark.parametrize("name", ["forwarder", "stacks", "subparser_stack"])
def test_packets_reach_every_parser_state(name: str) -> None:
    program = golden(CORPUS / name)
    loaded = v1model.load(program)
    seen: set[tuple[str, str]] = set()
    outcomes: Counter[str] = Counter()
    for case in generate(loaded.index, 11, 300):
        visit = parser_visits(loaded, case.packet, case.ingress_port)
        seen |= visit.states
        outcomes["accept" if visit.accepted else visit.error] += 1
    assert seen == all_states(program)
    assert outcomes["accept"] > 0
    assert outcomes["PacketTooShort"] > 0
    if name != "forwarder":
        assert outcomes["BadHeaderType"] > 0


def test_packets_satisfy_masked_and_range_key_sets() -> None:
    program = mixed()
    loaded = v1model.load(program)
    seen: set[tuple[str, str]] = set()
    outcomes: Counter[str] = Counter()
    for case in generate(loaded.index, 2, 200):
        visit = parser_visits(loaded, case.packet, case.ingress_port)
        seen |= visit.states
        outcomes["accept" if visit.accepted else visit.error] += 1
    assert seen == all_states(program)
    # The reject case, the accept case and the deep state are all taken.
    assert outcomes["accept"] > 20
    assert outcomes["NoError"] > 5


def test_table_lookups_hit_and_miss() -> None:
    """Entries and packets draw key fields from one pool, so hits happen."""
    loaded = v1model.load(golden(CORPUS / "forwarder"))
    fates: Counter[str] = Counter()
    for case in generate(loaded.index, 13, 200):
        fates["forwarded" if run_python(loaded, case, PORTS) else "dropped"] += 1
    # The program's default action drops; only a hit (or a host default of
    # `ipv4_forward` or `NoAction`) lets a packet out.
    assert fates["dropped"] > 10
    assert fates["forwarded"] > 10


# ---------------------------------------------------------------------------
# The pipe
# ---------------------------------------------------------------------------


def test_parse_reply_rejects_what_is_not_the_protocol() -> None:
    assert parse_reply('{"outputs": [[1, "ab"]], "state": {}}') == Outcome(outputs=((1, b"\xab"),))
    assert parse_reply('{"error": "boom", "state": {}}') == Outcome(error="boom")
    assert parse_reply('{"outputs": [], "diagnostic": "why", "state": {}}') == Outcome(
        outputs=(), diagnostic="why"
    )
    for bad in [
        "nope",
        "[]",
        "{}",
        '{"outputs": [[1]]}',
        '{"outputs": [[1, "zz"]]}',
        '{"outputs": [], "diagnostic": 3}',
    ]:
        with pytest.raises(ProtocolError):
            parse_reply(bad)


@pytest.mark.parametrize(
    "reply",
    [
        '{"outputs": [[1, "ab"]], "outputs": [], "state": {}}',
        '{"outputs": [[1, "ab"]], "outp\\u0075ts": [], "state": {}}',
        '{"outputs": [], "state": {"r": {"kind": "counter", "values": ["0x1"], "values": []}}}',
        '{"outputs": [], "state": {"r": {"kind": "counter", "values": ["0x1"]}, '
        '"r": {"kind": "counter", "values": []}}}',
        '{"outputs": [], "state": {}, "diagnostic": "fault", "diagnostic": null}',
        '{"error": "original fault", "error": "replacement", "state": {}}',
        '{"outputs": [], "state": {}, "extension": NaN}',
        '{"outputs": [], "state": {}, "extension": Infinity}',
        '{"outputs": [], "state": {}, "extension": -Infinity}',
        '{"error": "fault", "state": {}, "diagnostic": []}',
    ],
)
def test_parse_reply_rejects_ambiguous_or_non_json_data(reply: str) -> None:
    with pytest.raises(ProtocolError):
        parse_reply(reply)


def test_reply_extensions_and_error_comparison_policy_are_unchanged() -> None:
    assert parse_reply('{"outputs": [], "state": {}, "extension": {"future": 1}}') == Outcome(
        outputs=()
    )
    # Diagnostic strings are well-typed, but errors still compare their
    # reason and state rather than optional diagnostic text.
    assert parse_reply('{"error": "boom", "state": {}, "diagnostic": "detail"}') == Outcome(
        error="boom"
    )


def test_reply_decoder_recursion_failure_is_a_protocol_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def exhausted(*_args: object, **_kwargs: object) -> None:
        raise RecursionError("injected decoder exhaustion")

    monkeypatch.setattr("p4blo.drt._json.json.loads", exhausted)
    with pytest.raises(ProtocolError, match="decoder limit"):
        parse_reply('{"outputs": [], "state": {}}')


def test_agreement_compares_error_reasons_and_diagnostic_presence() -> None:
    """Two errors agree only for the same stated reason, the Python
    exception class stripped; two drops agree only when both or neither
    carry a diagnostic, whatever it says."""
    lean = Outcome(error="table 't' has 2 keys")
    assert Outcome(error="InstallError: table 't' has 2 keys").agrees_with(lean)
    assert lean.agrees_with(Outcome(error="InstallError: table 't' has 2 keys"))
    assert not Outcome(error="ValueError: 600 does not fit in 9 bits").agrees_with(lean)
    assert not Outcome(error="InstallError: table 't' has 3 keys").agrees_with(lean)
    assert not Outcome(outputs=()).agrees_with(lean)
    dropped = Outcome(outputs=(), diagnostic="parser consumed 4 bits")
    assert dropped.agrees_with(Outcome(outputs=(), diagnostic="something else"))
    assert not dropped.agrees_with(Outcome(outputs=()))
    assert not Outcome(outputs=()).agrees_with(dropped)
    assert Outcome(outputs=((1, b"\x00"),)).agrees_with(Outcome(outputs=((1, b"\x00"),)))
    assert str(dropped) == "no packet (parser consumed 4 bits)"


@pytest.mark.parametrize("program_dir", PROGRAMS, ids=lambda p: p.name)
def test_python_against_python_through_the_pipe_agrees(program_dir: Path) -> None:
    report = compare(program_dir, 7, 60, PORTS, FAKE)
    assert report.cases == 60
    assert report.divergences == []
    assert report.both_errored == 0


def test_a_flipped_byte_is_a_divergence_on_every_case_with_output() -> None:
    program_dir = CORPUS / "forwarder"
    loaded = v1model.load(golden(program_dir))
    cases = generate(loaded.index, 7, 60, PORTS)
    with_output = sum(1 for case in cases if run_python(loaded, case, PORTS))
    report = compare(program_dir, 7, 60, PORTS, [*FAKE, "--flip"])
    assert len(report.divergences) == with_output > 0
    d = report.divergences[0]
    assert d.python.outputs is not None and d.lean.outputs is not None
    assert d.python.outputs != d.lean.outputs
    assert d.case == cases[d.number]


def test_a_dead_process_is_a_protocol_error(tmp_path: Path) -> None:
    program_json = tmp_path / "forwarder.json"
    program_json.write_text(arch_wire.dump_json(golden(CORPUS / "forwarder")))
    case = Case(pb.Entries(), 0, b"\x00")
    with LeanRunner([sys.executable, "-c", "import sys; sys.exit(3)"], program_json, 4) as runner:
        with pytest.raises(ProtocolError, match="exit 3"):
            runner.run(case)


def test_an_error_on_one_side_diverges_and_on_both_sides_agrees() -> None:
    loaded = v1model.load(golden(CORPUS / "forwarder"))
    cases = generate(loaded.index, 1, 3)
    # An entry with no keys for a one-key table: Python fails to install it.
    bad = pb.Entries(
        tables=[
            pb.TableEntries(
                block="MyIngress",
                table="ipv4_lpm",
                entries=[pb.Entry(action=pb.ActionCall(action="drop"))],
            )
        ]
    )
    cases.append(Case(bad, 0, b"\x00"))
    report = compare_cases("forwarder", loaded, cases, PORTS, lambda _: Outcome(error="x"))
    assert report.cases == 4
    # Both sides errored on the last case, but not for the same reason.
    assert report.both_errored == 1
    assert [d.number for d in report.divergences] == [0, 1, 2, 3]
    assert all(d.lean.error == "x" for d in report.divergences)
    assert report.divergences[3].python.error is not None
    assert report.divergences[3].python.error.startswith("InstallError: ")
    # A Lean that states the same reason, without Python's class prefix,
    # agrees.
    same = Outcome(error="table 'ipv4_lpm' has 1 keys", state=snapshot(loaded))
    report = compare_cases("forwarder", loaded, cases[3:], PORTS, lambda _: same)
    assert report.both_errored == 1
    assert report.divergences == []


def test_a_diagnostic_on_one_side_only_is_a_divergence() -> None:
    loaded = v1model.load(golden(CORPUS / "forwarder"))
    case = Case(pb.Entries(), 0, b"\x00")
    python = python_outcome(loaded, case, PORTS)
    assert python.diagnostic is None
    same = Outcome(outputs=python.outputs, state=python.state)
    report = compare_cases("forwarder", loaded, [case], PORTS, lambda _: same)
    assert report.divergences == []
    dropped = Outcome(
        outputs=python.outputs, diagnostic="egress_spec 9 is not a port", state=python.state
    )
    report = compare_cases("forwarder", loaded, [case], PORTS, lambda _: dropped)
    assert [d.number for d in report.divergences] == [0]


# ---------------------------------------------------------------------------
# Vectors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("program", ["forwarder", "mixed"])
def test_case_to_stf_parses_and_replays_to_the_same_outputs(program: str) -> None:
    loaded = v1model.load(mixed() if program == "mixed" else golden(CORPUS / program))
    index = loaded.index
    gen = Generator(index, 21, PORTS)
    for case in gen.cases(40):
        text = case_to_stf(index, case)
        statements = stf.parse(text)
        assert stf.to_entries(index, statements) == case.entries
        packets = [s for s in statements if isinstance(s, stf.Packet)]
        assert packets == [stf.Packet(packets[0].line, case.ingress_port, case.packet)]
        replayed = Case(stf.to_entries(index, statements), packets[0].port, packets[0].data)
        assert run_python(loaded, replayed, PORTS) == run_python(loaded, case, PORTS)


def test_case_to_stf_writes_the_outputs_as_comments() -> None:
    index = BoundIndex.build(golden(CORPUS / "forwarder"))
    case = Case(pb.Entries(), 1, b"\x01\x02")
    text = case_to_stf(index, case, comments={"python": [(2, b"\xab")], "lean": "error: boom"})
    assert text == ("packet 1 0102\n# python:\n# expect 2 ab $\n# lean:\n#   error: boom\n")
    statements = stf.parse(text)
    assert len(statements) == 1


def test_case_to_stf_refuses_an_empty_packet() -> None:
    index = BoundIndex.build(golden(CORPUS / "forwarder"))
    with pytest.raises(ValueError, match="empty packet"):
        case_to_stf(index, Case(pb.Entries(), 0, b""))


# ---------------------------------------------------------------------------
# The real thing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("program_dir", PROGRAMS, ids=lambda p: p.name)
def test_lean_agrees_with_python(program_dir: Path, lean_binary: Path) -> None:
    report = compare(program_dir, 42, 200, PORTS, [lean_binary])
    assert report.cases == 200
    index = BoundIndex.build(golden(program_dir))
    shown = "\n".join(
        case_to_stf(index, d.case, comments={"python": str(d.python), "lean": str(d.lean)})
        for d in report.divergences[:3]
    )
    assert report.divergences == [], f"{report.summary()}\n{shown}"
    # The generator promises installable entries and in-range ports, so an
    # error on both sides, even for the same reason, is a bug somewhere.
    assert report.both_errored == 0, report.summary()


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


def test_lean_agrees_on_error_reasons(lean_binary: Path, tmp_path: Path) -> None:
    """Both sides refuse an lpm prefix wider than the key and an ingress
    port that is not the switch's, in the same words."""
    program = golden(CORPUS / "forwarder")
    bad_width = pb.Entries()
    te = bad_width.tables.add(block="MyIngress", table="ipv4_lpm")
    entry = te.entries.add()
    entry.keys.add(lpm=pb.LpmValue(value="1", prefix_len=40))
    entry.action.action = "drop"
    cases = [Case(bad_width, 0, bytes(34)), Case(pb.Entries(), 600, bytes(34))]
    lean = lean_report(program, cases, lean_binary, tmp_path)
    assert [o.error for o in lean] == [
        "prefix length 40 exceeds width 32",
        "ingress_port 600 is not a configured v1model port",
    ]


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


def test_lean_agrees_on_drop_redirection_and_the_port_rules(
    lean_binary: Path, tmp_path: Path
) -> None:
    program = fate_program()
    assert validator.validate(program) == []
    cases = [
        Case(pb.Entries(), ingress, bytes([redirect, drop, port >> 8, port & 0xFF]))
        for ingress, redirect, drop, port in [
            (6, 1, 0, 0),  # egress assignment cannot redirect selected port0
            (0, 1, 0, 0),
            (7, 1, 1, 3),  # ingress drop suppresses egress
            (0, 0, 0, 511),  # reserved drop port: no diagnostic
            (0, 0, 0, 9),  # beyond the count
            (0, 0, 0, 7),  # the last port
            (2, 0, 0, 4),
        ]
    ]
    cases.append(Case(pb.Entries(), 300, bytes(4)))  # ingress beyond the count: both error
    cases.append(Case(pb.Entries(), 512, bytes(4)))  # ingress beyond bit<9>: both error
    lean = lean_report(program, cases, lean_binary, tmp_path, ports=8)
    assert [o.diagnostic for o in lean[:7]] == [
        None,
        None,
        None,
        None,
        "egress_spec 9 is not a configured v1model port",
        None,
        None,
    ]
    assert lean[5].outputs == ((7, bytes([0, 0, 0, 0])),)
    assert [o.error for o in lean[7:]] == [
        "ingress_port 300 is not a configured v1model port",
        "ingress_port 512 is not a configured v1model port",
    ]
