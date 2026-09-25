"""The test infrastructure must detect faults and preserve stateful reproducers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from p4blo import arch
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import __main__ as cli
from p4blo.drt.case import Case
from p4blo.drt.replay import load, replay, save
from p4blo.drt.replay import main as replay_main
from p4blo.drt.run import (
    Divergence,
    Outcome,
    ProtocolError,
    Report,
    compare,
    compare_cases,
    compare_program,
    python_outcome,
)
from p4blo.drt.state import Observation, encode, snapshot
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]
FAKE = [sys.executable, "-m", "p4blo.drt.fake_lean"]


@pytest.mark.parametrize("packet", [b"\x00\x01\x00", b""])
def test_both_clis_describe_state_only_divergences(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], packet: bytes
) -> None:
    case = Case(pb.Entries(), 0, packet)
    left = Outcome(outputs=(), state=(Observation("counter", "counter", values=(3,)),))
    right = Outcome(outputs=(), state=(Observation("counter", "counter", values=(2,)),))
    report = Report("register_bounds", 0, 4, cases=1)
    report.divergences.append(Divergence(0, case, left, right))
    monkeypatch.setitem(replay_main.__globals__, "replay", lambda *_: report)
    assert replay_main(["unused.json", "--fake"]) == 1
    replay_output = capsys.readouterr().out
    cli.show(report, ROOT / "tests/corpus/register_bounds", 1, None)
    excerpt_output = capsys.readouterr().out
    if not packet:
        assert "cannot be represented in STF" in excerpt_output
    for output in (replay_output, excerpt_output):
        assert "state counter: Python" in output
        assert '"0x3"' in output and '"0x2"' in output


def register_program() -> apb.BlockAssembly:
    return arch_wire.load_text(ROOT / "tests/corpus/register_bounds/register_bounds.txtpb")


def envelope(**changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "format": "p4blo.drt",
        "version": 1,
        "program": {},
        "ports": 4,
        "seed": 0,
        "requests": [],
    }
    result.update(changes)
    return result


@pytest.mark.parametrize("version", [True, 1.0])
def test_replay_requires_exact_integer_version(tmp_path: Path, version: object) -> None:
    path = tmp_path / "version.json"
    path.write_text(json.dumps(envelope(version=version)))
    with pytest.raises(ValueError, match="version"):
        load(path)


@pytest.mark.parametrize("value", [[], ""])
@pytest.mark.parametrize("field", ["program", "entries"])
def test_replay_requires_protobuf_object_envelopes(
    tmp_path: Path, field: str, value: object
) -> None:
    data = envelope()
    if field == "program":
        data[field] = value
    else:
        data["requests"] = [{"entries": value, "ingress_port": 0, "packet": ""}]
    path = tmp_path / "shape.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="object"):
        load(path)


@pytest.mark.parametrize(
    "requests",
    [[], ""],
)
def test_replay_requires_each_request_to_be_an_object(tmp_path: Path, requests: object) -> None:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(envelope(requests=[requests])))
    with pytest.raises(ValueError, match="object"):
        load(path)


@pytest.mark.parametrize(
    "fragment",
    [
        '"ports": 1, "ports": 4',
        '"program": {"name": "a", "name": "b"}',
        '"requests": [{"entries": {"tables": [], "tables": []}, "ingress_port": 0, "packet": ""}]',
        '"extension": NaN',
        '"extension": Infinity',
        '"extension": -Infinity',
    ],
)
def test_replay_rejects_recursive_duplicate_keys_and_non_json_constants(
    tmp_path: Path, fragment: str
) -> None:
    path = tmp_path / "ambiguous.json"
    data = envelope()
    for nested in ("program", "requests"):
        if fragment.startswith(f'"{nested}":'):
            del data[nested]
    path.write_text(json.dumps(data)[:-1] + "," + fragment + "}")
    with pytest.raises(ValueError):
        load(path)


def test_bad_protobuf_replay_is_a_controlled_cli_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "unknown-field.json"
    path.write_text(json.dumps(envelope(program={"unknown_field": 1})))
    assert replay_main([str(path), "--fake"]) == 2
    assert "replay failed:" in capsys.readouterr().err


@pytest.mark.parametrize("field", ["outputs", "state", "diagnostic"])
def test_ambiguous_peer_cannot_produce_false_agreement(tmp_path: Path, field: str) -> None:
    program = register_program()
    cases = [Case(pb.Entries(), 0, bytes.fromhex("0005ff"))]
    actual = python_outcome(arch.reference.load(program), cases[0], 4)
    assert actual.outputs is not None and actual.error is None and actual.diagnostic is None
    reply = {
        "outputs": [[port, packet.hex()] for port, packet in actual.outputs],
        "state": encode(actual.state),
        "diagnostic": None,
    }
    hidden = {"outputs": [[1, "ab"]], "state": {}, "diagnostic": "erased fault"}[field]
    # The last values agree exactly with Python. Plain json.loads used to
    # erase the first, conflicting occurrence and falsely pass this run.
    raw = "{" + json.dumps(field) + ":" + json.dumps(hidden) + "," + json.dumps(reply)[1:]
    peer = f"import sys; [print({raw!r}, flush=True) for _ in sys.stdin]"
    with pytest.raises(ProtocolError, match="duplicate JSON key") as error:
        compare_program(program, cases, 4, [sys.executable, "-c", peer])
    report = error.value.report
    assert report is not None and not report.passed and report.cases == 0
    assert report.inputs == tuple(cases) and report.program_ir == program
    bundle = tmp_path / f"ambiguous-{field}.json"
    save(report, bundle)
    assert replay(bundle, FAKE).passed


def test_replay_shape_checks_preserve_semantically_invalid_inputs(tmp_path: Path) -> None:
    data = envelope(
        requests=[{"entries": {}, "ingress_port": -1, "packet": "", "extension": True}],
        extension={"future": "metadata"},
    )
    path = tmp_path / "invalid-program.json"
    path.write_text(json.dumps(data))
    program, cases, ports, seed = load(path)
    assert program == apb.BlockAssembly()
    assert cases == [Case(pb.Entries(), -1, b"")]
    assert (ports, seed) == (4, 0)


@pytest.mark.parametrize("field", ["program", "entries"])
def test_replay_cli_normalizes_nested_protobuf_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], field: str
) -> None:
    data = envelope()
    if field == "program":
        data["program"] = {"name": {"not": "a string"}}
    else:
        data["requests"] = [{"entries": {"unknown_field": 1}, "ingress_port": 0, "packet": ""}]
    path = tmp_path / "protobuf-error.json"
    path.write_text(json.dumps(data))
    assert replay_main([str(path), "--fake"]) == 2
    assert "protobuf JSON" in capsys.readouterr().err


@pytest.mark.parametrize(
    "data, message",
    [
        ([], "object"),
        (None, "object"),
        (envelope(requests={}), "array"),
        (envelope(requests=[{}]), "ingress_port"),
        (envelope(requests=[{"ingress_port": 0}]), "entries"),
        (envelope(requests=[{"entries": {}, "ingress_port": 0}]), "packet"),
        (envelope(requests=[{"entries": {}, "ingress_port": 0, "packet": []}]), "packet"),
        (envelope(requests=[{"entries": {}, "ingress_port": 0, "packet": "zz"}]), "hex"),
        (envelope(ports=True), "ports"),
        (envelope(seed=1.0), "seed"),
    ],
)
def test_malformed_replay_envelopes_have_controlled_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], data: object, message: str
) -> None:
    path = tmp_path / "malformed.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=message):
        load(path)
    assert replay_main([str(path), "--fake"]) == 2
    assert "replay failed:" in capsys.readouterr().err


def test_replay_decoder_recursion_failure_is_a_controlled_cli_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "deep.json"
    path.write_text("{}")

    def exhausted(*_args: object, **_kwargs: object) -> None:
        raise RecursionError("injected decoder exhaustion")

    monkeypatch.setattr("p4blo.drt._json.json.loads", exhausted)
    assert replay_main([str(path), "--fake"]) == 2
    assert "decoder limit" in capsys.readouterr().err


def test_replay_keeps_the_prefix_that_establishes_register_state(tmp_path: Path) -> None:
    program = register_program()
    cases = [Case(pb.Entries(), 0, bytes.fromhex(p)) for p in ("0005ff", "000300")]

    # A broken implementation resets state before each packet. The second
    # request alone cannot expose the fault; replaying the prefix must.
    def reset_each_packet(case: Case) -> Outcome:
        return python_outcome(arch.reference.load(program), case, 4)

    report = compare_cases(
        "register_bounds", arch.reference.load(program), cases, 4, reset_each_packet
    )
    assert [d.number for d in report.divergences] == [1]
    assert report.divergences[0].python.outputs == ((0, bytes.fromhex("000308")),)
    bundle = tmp_path / "failure.json"
    save(report, bundle)
    recovered_program, recovered_cases, ports, seed = load(bundle)
    assert recovered_program == program
    assert recovered_cases == cases
    recovered = compare_cases(
        "register_bounds",
        arch.reference.load(recovered_program),
        recovered_cases,
        ports,
        reset_each_packet,
        seed,
    )
    assert recovered.divergences == report.divergences
    assert replay(bundle, FAKE).passed


def test_replay_preserves_values_stf_cannot_express(tmp_path: Path) -> None:
    program = register_program()
    # This is deliberately an invalid installation. The replay format must
    # preserve it too, including boolean action data and an empty packet.
    entries = pb.Entries(tables=[pb.TableEntries(block="C", table="unknown")])
    entries.tables[0].default_action.args.add(boolean=True)
    cases = [Case(entries, -1, b"")]
    report = compare_cases(
        "register_bounds", arch.reference.load(program), cases, 4, lambda _: Outcome()
    )
    bundle = tmp_path / "invalid.json"
    save(report, bundle)
    assert load(bundle)[1] == cases


def test_matching_errors_are_not_a_successful_valid_input_campaign() -> None:
    program = register_program()
    case = Case(pb.Entries(), 99, b"\x00")
    report = compare_cases(
        "register_bounds",
        arch.reference.load(program),
        [case],
        4,
        lambda _: Outcome(
            error="ingress_port 99 is not a port of this switch",
            state=snapshot(arch.reference.load(program)),
        ),
    )
    assert not report.divergences
    assert not report.passed


def test_protocol_failure_preserves_the_experiment_and_prior_divergences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    peer = (
        "import sys; "
        "[(print('{\"outputs\":[],\"state\":{}}' if i == 0 else 'not json', flush=True)) "
        "for i, _ in enumerate(sys.stdin)]"
    )

    def faulty_compare(program_dir, seed, count, ports, lean):
        return compare(program_dir, seed, count, ports, [sys.executable, "-c", peer])

    monkeypatch.setattr(cli, "compare", faulty_compare)
    assert cli.main([str(ROOT / "tests/corpus/register_bounds"), "2", "--save", str(tmp_path)]) == 2
    [bundle] = list(tmp_path.glob("*.json"))
    data = json.loads(bundle.read_text())
    assert data["completed_requests"] == 1
    assert data["divergences"] == [0]
    assert "not JSON" in data["protocol_error"]
    assert len(load(bundle)[1]) == 2
    assert replay(bundle, FAKE).passed


def test_report_inputs_do_not_alias_mutable_protobuf_entries() -> None:
    program = register_program()
    entries = pb.Entries()
    case = Case(entries, 0, b"\x00")

    def fail(_: Case) -> Outcome:
        raise ProtocolError("injected fault")

    with pytest.raises(ProtocolError) as error:
        compare_cases("register_bounds", arch.reference.load(program), [case], 4, fail)
    report = error.value.report
    assert report is not None and not report.passed
    entries.tables.add(block="changed")
    assert report.inputs[0].entries == pb.Entries()


def test_startup_failure_still_saves_concrete_inputs(tmp_path: Path) -> None:
    missing = tmp_path / "missing-lean"
    assert (
        cli.main(
            [
                str(ROOT / "tests/corpus/register_bounds"),
                "2",
                "--lean",
                str(missing),
                "--save",
                str(tmp_path),
            ]
        )
        == 2
    )
    [bundle] = list(tmp_path.glob("*.json"))
    assert len(load(bundle)[1]) == 2
    assert replay(bundle, FAKE).passed


def test_shutdown_failure_retains_completed_report(tmp_path: Path) -> None:
    peer = (
        "import sys; sys.stdin.readline(); "
        'print(\'{"outputs":[],"state":{}}\', flush=True); '
        "sys.stdin.read(); sys.exit(3)"
    )
    with pytest.raises(ProtocolError, match="exit 3") as error:
        compare_program(
            register_program(), [Case(pb.Entries(), 0, b"x")], 4, [sys.executable, "-c", peer]
        )
    report = error.value.report
    assert report is not None and report.cases == 1 and not report.passed
    assert len(report.divergences) == 1
    save(report, tmp_path / "shutdown.json")
    assert replay(tmp_path / "shutdown.json", FAKE).passed
