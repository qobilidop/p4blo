"""Installed selection with independent finite known answers.

Every lookup observes the complete initial installed/index state as well as
its selected action. Packet tests compare both interpreters and inject an
incorrect shortest-prefix implementation.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from p4blo import arch
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import tables
from p4blo.interp.api import InterpError
from p4blo.interp.tables import InstalledEntries, InstallError, Match
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.forwarder.forwarder import build
from tests.programs.test_forwarder_semantics import assert_program_identity, freeze

ROOT = Path(__file__).resolve().parents[2]
REF = ("MyIngress", "ipv4_lpm")
SHAPES = {
    "empty": [],
    "network": ["network"],
    "host": ["host"],
    "network-host": ["network", "host"],
    "host-network": ["host", "network"],
}
PROFILES = {
    f"{shape}/{mode}/{str(high).lower()}": (shape, mode, high)
    for shape, mode, high in itertools.product(SHAPES, ["drop", "noop", "forward"], [False, True])
}
# Deliberately no shift/mask/longest-prefix code in the answer oracle.
ADDRESSES = [
    0,
    0x0A0001FF,
    0x0A000200,
    0x0A000201,
    0x0A000202,
    0x0A000203,
    0x0A0002FF,
    0x0A000300,
    0xFFFFFFFF,
]
NETWORK_ANSWERS = {0x0A000200, 0x0A000201, 0x0A000202, 0x0A000203, 0x0A0002FF}


def call(which: str, high: bool = False) -> pb.ActionCall:
    if which in {"drop", "noop"}:
        return pb.ActionCall(action={"drop": "drop", "noop": "NoAction"}[which])
    mac, port = {
        ("network", False): (0x222222222222, 2),
        ("network", True): (0xFFFFFFFFFFFF, 511),
        ("host", False): (0x333333333333, 3),
        ("host", True): (0xFFFFFFFFFFFE, 510),
        ("forward", False): (0x444444444444, 1),
        ("forward", True): (0, 0),
    }[which, high]
    return pb.ActionCall(
        action="ipv4_forward",
        args=[
            pb.Literal(bits=pb.BitsLiteral(width=48, value=str(mac))),
            pb.Literal(bits=pb.BitsLiteral(width=9, value=str(port))),
        ],
    )


def entry(which: str, high: bool = False) -> pb.Entry:
    value, prefix = {"network": (0x0A000200, 24), "host": (0x0A000202, 32)}[which]
    return pb.Entry(
        keys=[pb.KeyValue(lpm=pb.LpmValue(value=str(value), prefix_len=prefix))],
        action=call(which, high),
    )


def inputs(name: str) -> pb.Entries:
    shape, mode, high = PROFILES[name]
    table = pb.TableEntries(
        block=REF[0], table=REF[1], entries=[entry(which, high) for which in SHAPES[shape]]
    )
    if mode != "drop":
        table.default_action.CopyFrom(call(mode, high))
    return pb.Entries(tables=[table])


def expected(name: str, address: int) -> Match:
    shape, mode, high = PROFILES[name]
    if "host" in SHAPES[shape] and address == 0x0A000202:
        return Match(call("host", high), True)
    if "network" in SHAPES[shape] and address in NETWORK_ANSWERS:
        return Match(call("network", high), True)
    return Match(call(mode, high), False)


def observe(program: apb.BlockAssembly, name: str) -> None:
    index = BoundIndex.build(program)
    original_index = freeze(index)
    installed = InstalledEntries.build(index, inputs(name))
    assert freeze(index) == original_index, "installer changed source index"
    shape, mode, high = PROFILES[name]
    independent = InstalledEntries(
        index, {REF: [entry(w, high) for w in SHAPES[shape]]}, {REF: call(mode, high)}
    )
    assert freeze(installed) == freeze(independent), "whole installed state"
    frozen = freeze(installed)
    for address in ADDRESSES:
        keys = [Bits(32, address)]
        frozen_keys = freeze(keys)
        result = installed.lookup(REF, keys)
        assert freeze(installed) == frozen, "lookup changed installed state"
        assert freeze(keys) == frozen_keys, "lookup changed query"
        assert freeze(result) == freeze(expected(name, address)), "independent selection"
    installed.set_default(REF, None)
    independent.default_actions[REF] = call("drop")
    assert freeze(installed) == freeze(independent), "restored declaration default"


@pytest.mark.parametrize("name", PROFILES)
def test_python_forwarder_tables(
    validated: apb.BlockAssembly,
    name: str,
) -> None:
    program = validated
    observe(program, name)


@pytest.mark.parametrize("fault", ["first", "last", "miss-hit", "default", "mutate", "bool-hit"])
def test_python_lookup_observer_faults(
    validated: apb.BlockAssembly,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    program = validated
    real_lookup = InstalledEntries.lookup
    hits = 0

    def broken(self: InstalledEntries, table: tables.TableRef, keys: list[Bits]) -> Match:
        nonlocal hits
        result = real_lookup(self, table, keys)
        hits += 1
        if fault in {"first", "last"} and keys[0].value == 0x0A000202:
            return Match(self.entries[table][0 if fault == "first" else -1].action, True)
        if fault == "miss-hit" and not result.hit:
            return Match(result.action, True)
        if fault == "default" and not result.hit:
            return Match(call("drop"), False)
        if fault == "mutate":
            self.entries[table][0].action.args[1].bits.value = "7"
        if fault == "bool-hit":
            result.hit = 1  # type: ignore[assignment]
        return result

    name = "host-network/forward/false" if fault == "last" else "network-host/forward/false"
    with monkeypatch.context() as patch:
        patch.setattr(InstalledEntries, "lookup", broken)
        if fault == "mutate":
            weak = InstalledEntries.build(BoundIndex.build(program), inputs(name))
            before = freeze(weak)
            answer = weak.lookup(REF, [Bits(32, 0)])
            assert freeze(answer) == freeze(expected(name, 0))
            assert freeze(weak) != before and hits == 1
        with pytest.raises(AssertionError):
            observe(program, name)
    assert hits > 0


def test_python_table_rejections(
    validated: apb.BlockAssembly,
) -> None:
    program = validated
    index = BoundIndex.build(program)
    for which in ["network", "host"]:
        installed = InstalledEntries.build(index)
        installed.install(REF, entry(which))
        with pytest.raises(InstallError):
            installed.install(REF, entry(which))
    bad: list[pb.Entry] = []
    for value, prefix in [(0x0A000201, 24), (0, 33)]:
        item = entry("network")
        item.keys[0].lpm.CopyFrom(pb.LpmValue(value=str(value), prefix_len=prefix))
        bad.append(item)
    item = entry("network")
    del item.keys[:]
    bad.append(item)
    item = entry("network")
    item.priority = 1
    bad.append(item)
    for action in [pb.ActionCall(action="missing"), call("host"), call("host")]:
        item = entry("network")
        item.action.CopyFrom(action)
        bad.append(item)
    bad[-2].action.args[0].bits.width = 47
    bad[-1].action.args[1].bits.value = "512"
    installed = InstalledEntries.build(index)
    for item in bad:
        before = freeze(installed)
        with pytest.raises(InstallError):
            installed.install(REF, item)
        assert freeze(installed) == before
    with pytest.raises(InstallError):
        installed.install(("Other", "ipv4_lpm"), entry("network"))
    for keys in [[], [Bits(32, 0), Bits(32, 1)]]:
        with pytest.raises(InterpError):
            installed.lookup(REF, keys)
    with pytest.raises(InstallError):
        installed.set_default(REF, pb.ActionCall(action="missing"))


def packet_case() -> Case:
    return Case(
        inputs("network-host/drop/false"),
        0,
        bytes.fromhex(
            "00000000010100000000000108004500001a00010000001100000a0001010a000202deadbeefcafe"
        ),
    )


def packet_expected(host: bool = True) -> list[tuple[int, bytes]]:
    return [
        (
            3 if host else 2,
            bytes.fromhex(
                ("333333333333" if host else "222222222222")
                + "00000000010108004500001a00010000ff11a4cf0a0001010a000202deadbeefcafe"
            ),
        )
    ]


def test_lean_agrees_overlapping_routes_packet(
    validated: apb.BlockAssembly,
    lean_binary: Path,
) -> None:
    """Executable end-to-end anchor, not a newly proved application contract."""
    program = validated
    bundle = ROOT / ".artifacts/drt/forwarder-tables-lpm.json"
    try:
        report = compare_program(program, [packet_case()], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is not None:
            bundle.parent.mkdir(parents=True, exist_ok=True)
            save(error.report, bundle)
        raise
    if not report.passed:
        bundle.parent.mkdir(parents=True, exist_ok=True)
        save(report, bundle)
    assert report.passed and report.agreed == 1
    assert run_python(arch.reference.load(program), packet_case(), 4) == packet_expected()


def test_lean_agrees_shortest_prefix_fault_replay(
    validated: apb.BlockAssembly,
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    program = validated
    original = tables.beats
    hits = 0

    def shortest(candidate: pb.Entry, best: pb.Entry, ternary: bool) -> bool:
        nonlocal hits
        if not ternary:
            hits += 1
            return tables.prefix_length(candidate) < tables.prefix_length(best)
        return original(candidate, best, ternary)

    bundle = tmp_path / "shortest-prefix.json"
    with monkeypatch.context() as fault:
        fault.setattr(tables, "beats", shortest)
        with pytest.raises(AssertionError, match="independent selection"):
            observe(program, "network-host/drop/false")
        assert hits == 1
        report = compare_program(program, [packet_case()], 4, [lean_binary])
        save(report, bundle)
        assert hits == 2 and report.agreed == 0 and len(report.divergences) == 1
        assert report.protocol_error is None and report.both_errored == 0
        saved_program, cases, ports, seed = replay.load(bundle)
        assert saved_program == program and cases == [packet_case()] and (ports, seed) == (4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert hits == 3 and live.agreed == 0 and len(live.divergences) == 1
        divergence = live.divergences[0]
        assert divergence.lean.outputs == tuple(packet_expected())
        assert divergence.python.outputs == tuple(packet_expected(False))
        for outcome in [divergence.lean, divergence.python]:
            assert outcome.error is None and outcome.diagnostic is None
        assert divergence.lean.state == divergence.python.state
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1 and restored.both_errored == 0


@pytest.fixture(scope="module")
def validated() -> apb.BlockAssembly:
    program = build()
    assert_program_identity(program)
    return program
