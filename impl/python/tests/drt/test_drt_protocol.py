"""Package checks without native oracle dependencies."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

from p4blo.drt.case import Case
from p4blo.drt.run import LeanRunner, ProtocolError, parse_reply
from p4blo.v0 import p4blo_pb2 as pb


@pytest.mark.parametrize(
    "reply",
    [
        '{"error": 1}',
        '{"error": "x", "outputs": []}',
        '{"outputs": [[true, "00"]]}',
        '{"outputs": [[1.5, "00"]]}',
        '{"outputs": [["1", "00"]]}',
        '{"outputs": [[-1, "00"]]}',
        '{"outputs": [[1, null]]}',
        '{"outputs": ["10"]}',
    ],
)
def test_malformed_replies_cannot_be_coerced_to_agreement(reply: str) -> None:
    with pytest.raises(ProtocolError):
        parse_reply(json.dumps({**json.loads(reply), "state": {}}))


@pytest.mark.parametrize("coverage", ['"a"', "[1]", "[null]", "{}", "null"])
def test_malformed_coverage_is_a_protocol_error(coverage: str) -> None:
    with pytest.raises(ProtocolError, match="coverage"):
        parse_reply('{"outputs": [], "state": {}, "coverage": ' + coverage + "}")


def test_coverage_is_optional_and_never_part_of_agreement() -> None:
    """An older peer sends no list; a list never changes agreement."""
    older = parse_reply('{"outputs": [], "state": {}}')
    newer = parse_reply('{"outputs": [], "state": {}, "coverage": ["stmt.emit"]}')
    assert older.coverage is None
    assert newer.coverage == frozenset({"stmt.emit"})
    assert older == newer and older.agrees_with(newer)
    error = parse_reply('{"error": "x", "state": {}, "coverage": []}')
    assert error.coverage == frozenset()


def test_dead_peer_buffered_write_preserves_error_and_closes_streams(tmp_path: Path) -> None:
    with LeanRunner(
        [sys.executable, "-c", "import sys; sys.exit(3)"], tmp_path / "unused.json", 4
    ) as runner:
        process, stderr, worker = runner.process, runner.stderr, runner.worker
        assert process is not None and stderr is not None and worker is not None
        assert process.stdin is not None and process.stdout is not None
        # Force the peer to exit before the small request enters the real
        # buffered pipe. Both flush() and close() then encounter the broken pipe.
        assert process.wait(timeout=5) == 3
        with pytest.raises(ProtocolError, match="exit 3"):
            runner.run(Case(pb.Entries(), 0, b"x"))
        assert process.stdin.closed and process.stdout.closed and stderr.closed
        assert not worker.is_alive()
        assert runner.process is None and runner.stderr is None
        runner.close()  # Cleanup remains safe to repeat, including on context exit.


@pytest.mark.parametrize("packet_size", [1, 1_000_000])
def test_unresponsive_peer_times_out_even_when_it_does_not_read(
    tmp_path: Path, packet_size: int
) -> None:
    program_json = tmp_path / "program.json"
    program_json.write_text("{}")
    with LeanRunner(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        program_json,
        4,
        timeout=0.2,
    ) as runner:
        process = runner.process
        with pytest.raises(ProtocolError, match="timed out"):
            runner.run(Case(pb.Entries(), 0, bytes(packet_size)))
        assert process is not None and process.poll() is not None


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup")
def test_timeout_reaps_descendants_that_inherit_protocol_pipes(tmp_path: Path) -> None:
    start = time.monotonic()
    with LeanRunner(
        [sys.executable, "-c", "import os,time; os.fork(); time.sleep(60)"],
        tmp_path / "unused.json",
        4,
        timeout=0.2,
    ) as runner:
        with pytest.raises(ProtocolError, match="timed out"):
            runner.run(Case(pb.Entries(), 0, b"x"))
        assert runner.worker is not None and not runner.worker.is_alive()
    assert time.monotonic() - start < 5


@pytest.mark.parametrize(
    ("ending", "message"),
    [
        ("sys.exit(3)", "exit 3"),
        ("print('extra', flush=True)", "unsolicited output"),
        ("import time; time.sleep(60)", "shutdown timed out"),
    ],
)
def test_valid_final_reply_does_not_hide_broken_shutdown(
    tmp_path: Path, ending: str, message: str
) -> None:
    peer = (
        "import sys; sys.stdin.readline(); "
        'print(\'{"outputs":[],"state":{}}\', flush=True); '
        "sys.stdin.read(); " + ending
    )
    with pytest.raises(ProtocolError, match=message):
        with LeanRunner(
            [sys.executable, "-c", peer], tmp_path / "unused.json", 4, timeout=0.2
        ) as runner:
            runner.run(Case(pb.Entries(), 0, b"x"))


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup")
def test_executable_probe_uses_bounded_process_group_cleanup(tmp_path: Path) -> None:
    start = time.monotonic()
    reason = LeanRunner.probe(
        [sys.executable, "-c", "import os,time; os.fork(); time.sleep(60)"],
        tmp_path / "unused.json",
        timeout=0.2,
    )
    assert reason is not None and "timed out" in reason
    assert time.monotonic() - start < 5
