"""A broken comparator must fail, never hang or be coerced to agreement."""

from __future__ import annotations

import json
import sys
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
