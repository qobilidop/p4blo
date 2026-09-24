"""Real first-conditional prefix; checksum is pending, not executed/proved.

Full-body observation stops exactly once with a dedicated boundary sentinel.
Direct first-statement checks separately complete normally. All expected
state is detached and frozen before either execution path begins.
"""

from __future__ import annotations

import subprocess
import tomllib
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from google.protobuf import json_format

from p4blo import ir
from p4blo.drt._json import loads as strict_loads
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.tables import InstalledEntries, Match, TableRef
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_codec_leaves import same_json
from tests.test_lean_forwarder import assert_program_identity, freeze
from tests.test_lean_forwarder_action import run_json
from tests.test_lean_forwarder_apply import CASES as APPLICATION_CASES
from tests.test_lean_forwarder_apply import KEY, action, body, evaluator, expected_runs
from tests.test_lean_forwarder_apply import count as application_count
from tests.test_lean_forwarder_apply import environment as application_environment
from tests.test_lean_forwarder_tables import REF, encode, expected, inputs

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    f"{base}/{str(valid).lower()}": (base, valid)
    for base in APPLICATION_CASES
    for valid in [False, True]
}
GUARD = pb.Expr(
    is_valid=pb.IsValid(header=pb.Expr(member=pb.Member(base=pb.Expr(var="hdr"), field="ipv4")))
)


def field(name: str) -> pb.Expr:
    return pb.Expr(
        member=pb.Member(
            base=pb.Expr(member=pb.Member(base=pb.Expr(var="hdr"), field="ipv4")), field=name
        )
    )


def source_body() -> list[pb.Stmt]:
    checksum = field("version")
    for name in [
        "ihl",
        "diffserv",
        "totalLen",
        "identification",
        "flags",
        "fragOffset",
        "ttl",
        "protocol",
        "srcAddr",
        "dstAddr",
    ]:
        checksum = pb.Expr(
            binary=pb.Binary(op=pb.BINARY_OP_CONCAT, left=checksum, right=field(name))
        )
    target = pb.LValue(
        member=pb.LMember(
            base=pb.LValue(member=pb.LMember(base=pb.LValue(var="hdr"), field="ipv4")),
            field="hdrChecksum",
        )
    )
    return [
        pb.Stmt(
            conditional=pb.If(condition=GUARD, then=[pb.Stmt(apply=pb.Apply(table="ipv4_lpm"))])
        ),
        pb.Stmt(
            conditional=pb.If(
                condition=GUARD,
                then=[
                    pb.Stmt(
                        call_extern=pb.CallExtern(
                            instance="csum",
                            method="compute",
                            args=[pb.Arg(expr=checksum)],
                            result=target,
                        )
                    )
                ],
            )
        ),
    ]


def set_validity(env: Env, valid: bool) -> None:
    header = env.vars["hdr"]
    assert isinstance(header, Struct) and isinstance(header.fields[1], Header)
    header.fields[1].valid = valid


def environment(program: pb.Program, name: str, *, actual_entries: bool) -> Env:
    base, valid = CASES[name]
    result = application_environment(program, base, actual_entries=actual_entries)
    set_validity(result, valid)
    return result


def expected_states(program: pb.Program, name: str) -> dict[str, Env]:
    base, valid = CASES[name]
    states = expected_runs(program, base)
    for value in states.values():
        set_validity(value, valid)
    if not valid:
        states["after"] = deepcopy(states["before"])
    return states


def count(name: str) -> int:
    base, valid = CASES[name]
    return application_count(base) + 5 if valid else 3


def raw_environment(program: pb.Program, kind: int) -> Env:
    """Unvalidated unused storage: no metadata, and possibly shadowed hdr."""
    env = application_environment(program, "empty/drop/false/0/0", actual_entries=True)
    invalid = Struct(
        "headers",
        [True, Header("ipv4_t", False, [False, Struct("unused", [])] if kind == 3 else [])],
    )
    valid = Struct("headers", [True, Header("ipv4_t", True, [])])
    del env.vars["meta"]
    env.vars["hdr"] = invalid if kind < 2 else valid
    env.action = None if kind < 2 else "shadow"
    env.action_vars = None if kind < 2 else {"hdr": invalid, "keep": Bits(8, 11)}
    if kind % 2:
        env.scope = env.index.scopes["MyParser"]
    env.entries = (
        InstalledEntries(
            ir.Index.build(pb.Program()),
            {("poison", "unused"): []},
            {REF: pb.ActionCall(action="missing")},
        )
        if kind == 1
        else None
    )
    return env


def checked_snapshots(raw: Any) -> tuple[pb.Program, dict[str, Any]]:
    assert type(raw) is dict and set(raw) == {"program", "snapshots", "raw"}
    program = json_format.ParseDict(raw["program"], pb.Program())
    assert_program_identity(program)
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    assert list(ingress.body) == source_body(), "complete independent conditional/checksum syntax"
    assert len(CASES) == 540 and type(raw["snapshots"]) is list and len(raw["snapshots"]) == 540
    found: dict[str, Any] = {}
    for record in raw["snapshots"]:
        assert type(record) is dict and set(record) == {
            "name",
            "input",
            "before",
            "after",
            "pending",
            "steps",
        }
        name = record["name"]
        assert type(name) is str and name in CASES and name not in found
        base, _ = CASES[name]
        route, _, _ = APPLICATION_CASES[base]
        assert same_json(record["input"], encode(inputs(route)))
        assert type(record["steps"]) is int and record["steps"] == count(name), (
            "literal prefix count"
        )
        assert same_json(record["pending"], encode(source_body()[1])), (
            "full pending checksum syntax"
        )
        states = expected_states(program, name)
        for phase in ["before", "after"]:
            assert same_json(record[phase], run_json(states[phase])), f"complete {phase}: {name}"
        found[name] = record
    assert set(found) == set(CASES)
    assert type(raw["raw"]) is list and len(raw["raw"]) == 4
    seen: set[int] = set()
    for record in raw["raw"]:
        assert type(record) is dict and set(record) == {"kind", "before", "after"}
        kind = record["kind"]
        assert type(kind) is int and kind in range(4) and kind not in seen
        answer = run_json(raw_environment(program, kind))
        assert same_json(record["before"], answer) and same_json(record["after"], answer)
        seen.add(kind)
    assert seen == set(range(4))
    return program, found


@pytest.fixture(scope="module")
def export(lean_binary: Path) -> Any:
    assert lean_binary.is_file()
    result = subprocess.run(
        [str(ROOT / "lean/.lake/build/bin/forwarderIngress")],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.stderr == ""
    return strict_loads(result.stdout)


@pytest.fixture(scope="module")
def checked(export: Any) -> tuple[pb.Program, dict[str, Any]]:
    return checked_snapshots(export)


class PrefixBoundary(Exception):
    """Exact successful observation stop, NOT whole-body normal return."""


def observe(
    program: pb.Program,
    name: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    whole: bool = True,
    raw_kind: int | None = None,
) -> None:
    base, stored_valid = CASES[name]
    valid = stored_valid if raw_kind is None else False
    route, address, _ = APPLICATION_CASES[base]
    outer = (
        environment(program, name, actual_entries=True)
        if raw_kind is None
        else raw_environment(program, raw_kind)
    )
    states = (
        expected_states(program, name)
        if raw_kind is None
        else {"before": deepcopy(outer), "after": deepcopy(outer)}
    )
    frozen = {phase: freeze(value) for phase, value in states.items()}
    assert freeze(outer) == frozen["before"]
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    actual_body = list(ingress.body)
    assert actual_body == source_body()
    real_evaluate, real_execute, real_one = evaluator(), stmt.execute, stmt.execute_one
    real_apply, real_lookup, real_action = stmt.apply, InstalledEntries.lookup, stmt.run_action_call
    counts = dict(guard=0, key=0, apply=0, lookup=0, action=0, branch=0, body=0, stop=0)
    marker = PrefixBoundary("before exact actual checksum statement")

    def read(value: pb.Expr, env: Env) -> Value:
        if env is outer and value == GUARD:
            counts["guard"] += 1
            assert counts["guard"] == 1 and freeze(env) == frozen["before"], "pre-guard state/count"
            result = real_evaluate(value, env)
            assert freeze(result) == freeze(valid), "independent IPv4 validity"
            assert freeze(env) == frozen["before"], "guard read changed state"
            return result
        if env is outer and value == KEY:
            counts["key"] += 1
            assert valid and counts["guard"] == 1
            result = real_evaluate(value, env)
            assert freeze(result) == freeze(Bits(32, address))
            assert freeze(env) == frozen["before"]
            return result
        return real_evaluate(value, env)

    def lookup(self: InstalledEntries, ref: TableRef, keys: list[Bits]) -> Match:
        counts["lookup"] += 1
        assert valid and self is outer.entries and ref == REF
        assert freeze(keys) == freeze([Bits(32, address)])
        result = real_lookup(self, ref, keys)
        assert freeze(result) == freeze(expected(route, address))
        assert freeze(keys) == freeze([Bits(32, address)]) and freeze(outer) == frozen["before"]
        return result

    def apply_table(ap: pb.Apply, env: Env) -> None:
        counts["apply"] += 1
        assert valid and env is outer and ap == pb.Apply(table="ipv4_lpm")
        assert freeze(env) == frozen["before"]
        assert real_apply(ap, env) is None
        assert freeze(env) == frozen["after"]

    def action_call(call: pb.ActionCall, env: Env) -> None:
        counts["action"] += 1
        assert valid and env is outer and call == action(base)
        assert freeze(env) == frozen["before"]
        assert real_action(call, env) is None
        assert freeze(env) == frozen["after"]

    def execute(statements: Iterable[pb.Stmt], env: Env) -> None:
        items = list(statements)
        if env is outer:
            counts["branch"] += 1
            assert items == ([pb.Stmt(apply=pb.Apply(table="ipv4_lpm"))] if valid else [])
            assert freeze(env) == frozen["before"]
            assert real_execute(items, env) is None
            assert freeze(env) == frozen["after"]
        else:
            counts["body"] += 1
            assert valid and items == body(program, base)
            assert freeze(env) == frozen["entered"]
            assert real_execute(items, env) is None
            assert freeze(env) == frozen["activeEnd"]

    def one(statement: pb.Stmt, env: Env) -> None:
        if env is outer and statement == actual_body[1]:
            counts["stop"] += 1
            assert whole and counts["stop"] == 1, "exact checksum boundary hit"
            assert freeze(env) == frozen["after"], "complete checksum-boundary state"
            raise marker
        assert statement.WhichOneof("kind") != "call_extern", "checksum executed before boundary"
        real_one(statement, env)

    with monkeypatch.context() as hooks:
        hooks.setattr(stmt, "evaluate", read)
        hooks.setattr(InstalledEntries, "lookup", lookup)
        hooks.setattr(stmt, "apply", apply_table)
        hooks.setattr(stmt, "run_action_call", action_call)
        hooks.setattr(stmt, "execute", execute)
        hooks.setattr(stmt, "execute_one", one)
        if whole:
            with pytest.raises(PrefixBoundary) as stopped:
                real_execute(actual_body, outer)
            assert stopped.value is marker
        else:
            assert one(actual_body[0], outer) is None
    assert counts == dict(
        guard=1,
        key=int(valid),
        apply=int(valid),
        lookup=int(valid),
        action=int(valid),
        branch=1,
        body=int(valid),
        stop=int(whole),
    )
    assert freeze(outer) == frozen["after"]


@pytest.mark.parametrize("name", CASES)
def test_lean_agrees_ingress_prefix(
    checked: tuple[pb.Program, dict[str, Any]], name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    observe(checked[0], name, monkeypatch)


DIRECT = [
    next(
        n
        for n, (b, v) in CASES.items()
        if b.startswith(route + "/") and APPLICATION_CASES[b][1] == 0x0A000202 and v == valid
    )
    for route in ["network-host/drop/false", "empty/drop/false", "empty/noop/false"]
    for valid in [False, True]
]


@pytest.mark.parametrize("name", DIRECT)
def test_lean_agrees_direct_first_conditional(
    checked: tuple[pb.Program, dict[str, Any]], name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    observe(checked[0], name, monkeypatch, whole=False)


@pytest.mark.parametrize("kind", range(4))
def test_lean_agrees_raw_invalid_prefix(
    checked: tuple[pb.Program, dict[str, Any]], kind: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    observe(checked[0], next(iter(CASES)), monkeypatch, raw_kind=kind)
    observe(checked[0], next(iter(CASES)), monkeypatch, raw_kind=kind, whole=False)


def test_ingress_exporter_default_target() -> None:
    config = tomllib.loads((ROOT / "lean/lakefile.toml").read_text())
    assert "forwarderIngress" in config["defaultTargets"]
    assert {"name": "forwarderIngress", "root": "ForwarderIngressMain"} in config["lean_exe"]


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "count",
        "count-bool",
        "pending-guard",
        "pending-concat",
        "cursor-type",
        "sibling",
        "raw-metadata",
        "raw-kind-bool",
    ],
)
def test_lean_agrees_ingress_snapshot_rejections(export: Any, fault: str) -> None:
    altered = deepcopy(export)
    record = altered["snapshots"][0]
    if fault == "missing":
        altered["snapshots"].pop()
    elif fault == "duplicate":
        altered["snapshots"][-1] = deepcopy(record)
    elif fault == "count":
        record["steps"] -= 1
    elif fault == "count-bool":
        record["steps"] = True
    elif fault == "pending-guard":
        pending = source_body()[1]
        pending.conditional.condition.is_valid.header.member.field = "ethernet"
        record["pending"] = encode(pending)
    elif fault == "pending-concat":
        pending = source_body()[1]
        pending.conditional.then[0].call_extern.args[0].expr.binary.right.member.field = "srcAddr"
        record["pending"] = encode(pending)
    elif fault == "cursor-type":
        record["after"]["packet"][2] = 3.0
    elif fault == "sibling":
        record["after"]["frame"]["vars"]["hdr"][2][0][3][1][2] = 0
    elif fault == "raw-metadata":
        altered["raw"][0]["after"]["frame"]["vars"]["meta"] = ["bool", False]
    else:
        altered["raw"][0]["kind"] = False
    with pytest.raises(AssertionError):
        checked_snapshots(altered)


@pytest.mark.parametrize(
    "fault",
    [
        "invert",
        "ethernet",
        "sibling",
        "cursor",
        "installed",
        "early-checksum",
        "spoof-stop",
    ],
)
def test_lean_agrees_ingress_observer_faults(
    checked: tuple[pb.Program, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    program, _ = checked
    name = next(
        n
        for n, (base, valid) in CASES.items()
        if base.startswith("network-host/drop/false/")
        and valid
        and not APPLICATION_CASES[base][2][0]
    )
    real_read, real_one = evaluator(), stmt.execute_one
    hits = 0

    def broken_read(value: pb.Expr, env: Env) -> Value:
        nonlocal hits
        result = real_read(value, env)
        if value != GUARD:
            return result
        hits += 1
        if fault == "invert":
            assert type(result) is bool
            return not result
        if fault == "ethernet":
            return real_read(
                pb.Expr(
                    is_valid=pb.IsValid(
                        header=pb.Expr(member=pb.Member(base=pb.Expr(var="hdr"), field="ethernet"))
                    )
                ),
                env,
            )
        if fault == "sibling":
            meta = env.vars["meta"]
            assert isinstance(meta, Struct)
            meta.fields[0] = Bits(9, 7)
        elif fault == "cursor":
            assert env.packet is not None
            env.packet.cursor = float(env.packet.cursor)  # type: ignore[assignment]
        elif fault == "installed":
            assert env.entries is not None
            env.entries.defaults[REF] = pb.ActionCall(action="NoAction")
        return result

    def broken_one(statement: pb.Stmt, env: Env) -> None:
        nonlocal hits
        if statement == source_body()[0]:
            hits += 1
            if fault == "spoof-stop":
                raise PrefixBoundary("a different exception is not successful observation")
            real_one(statement, env)
            real_one(source_body()[1], env)
        else:
            real_one(statement, env)

    with monkeypatch.context() as mutation:
        if fault in {"early-checksum", "spoof-stop"}:
            mutation.setattr(stmt, "execute_one", broken_one)
        else:
            mutation.setattr(stmt, "evaluate", broken_read)
        if fault in {"sibling", "cursor", "installed"}:
            weak = environment(program, name, actual_entries=True)
            before = freeze(weak)
            assert evaluator()(GUARD, weak) is True
            assert hits == 1 and freeze(weak) != before
        with pytest.raises(AssertionError):
            observe(program, name, monkeypatch)
    assert hits > 0
