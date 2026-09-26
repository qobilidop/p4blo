"""Package checks without native oracle dependencies."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

from p4blo import stf
from p4blo.arch import v1model
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
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
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt import CORPUS, FAKE, PORTS, PROGRAMS, all_states, golden, mixed

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
