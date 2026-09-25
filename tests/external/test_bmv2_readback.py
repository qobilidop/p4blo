"""Fail-closed optional register readback, without requiring Docker."""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from tests.oracle.bmv2 import driver


def test_post_readback_profile_rejects_writes_and_ambiguous_requests() -> None:
    valid = {"port": 1, "data": "001122"}
    assert driver._post_profile([1], None, None) == ([], None)
    assert driver._post_profile([1], ["register_read C.r"], valid) == (
        ["register_read C.r"],
        (1, b"\x00\x11\x22"),
    )
    for commands in [
        [],
        "register_read C.r",
        ["register_write C.r 0 1"],
        ["register_read C.r 0"],
        ["register_read C.r\nreset_state"],
        ["register_read C.r"] * 2,
        [3],
    ]:
        with pytest.raises(driver.DriverError):
            driver._post_profile([1], commands, valid)
    for sentinel in [
        None,
        {},
        {"port": True, "data": "00"},
        {"port": 2, "data": "00"},
        {"port": 1, "data": ""},
        {"port": 1, "data": "AA"},
        {"port": 1, "data": "0"},
        {"port": 1, "data": "00", "extra": 1},
    ]:
        with pytest.raises(driver.DriverError):
            driver._post_profile([1], ["register_read C.r"], sentinel)


def transcript(lines: list[str]) -> str:
    return (
        "Obtaining JSON from switch...\nDone\nControl utility for runtime P4 table manipulation\n"
        + "\n".join(lines)
        + "\nRuntimeCmd: \nregister index omitted, reading entire array\n"
    )


def test_complete_register_transcript_rejects_extra_or_malformed_state() -> None:
    program = {"register_arrays": [{"name": "C.r", "size": 3, "bitwidth": 1}]}
    valid = transcript(["RuntimeCmd: C.r= 0, 1, 0"])
    assert driver._parse_register_readback(valid, ["register_read C.r"], program) == {
        "C.r": [0, 1, 0]
    }
    for output in [
        valid + "Fatal error: crashed\n",
        valid.replace("C.r=", "C.s="),
        valid.replace("0, 1, 0", "0, 1"),
        valid.replace("0, 1, 0", "0, 1, 0, 0"),
        valid.replace("0, 1, 0", "0, 2, 0"),
        valid.replace("0, 1, 0", "0, -1, 0"),
        valid.replace("0, 1, 0", "00, 1, 0"),
        valid.replace("0, 1, 0", "0, x, 0"),
        transcript(["RuntimeCmd: C.r= 0, 1, 0"] * 2),
        valid[:-1],
        transcript(["RuntimeCmd: Error: no register"]),
    ]:
        with pytest.raises(driver.DriverError):
            driver._parse_register_readback(output, ["register_read C.r"], program)


@pytest.mark.parametrize("packets", [[], [b"wrong"], [b"sentinel", b"sentinel"]])
def test_completion_rejects_missing_wrong_or_duplicate_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packets: list[bytes]
) -> None:
    output = tmp_path / "out.pcap"
    output.write_bytes(
        driver.pcap_header() + b"".join(driver.pcap_record(i, 0, p) for i, p in enumerate(packets))
    )
    monkeypatch.setattr(driver, "MIN_RUN", 0)
    monkeypatch.setattr(driver, "SETTLE", 0)
    monkeypatch.setattr(driver, "START_TIMEOUT", 1)
    monkeypatch.setattr(driver.time, "sleep", lambda _: None)
    monkeypatch.setattr(driver.time, "monotonic", Mock(side_effect=[0, 0.25, 0.5, 1]))
    proc = Mock(spec=subprocess.Popen)
    proc.poll.return_value = None
    with pytest.raises(driver.DriverError, match="completion packet|deadline"):
        driver._wait_for_completion(proc, [output], (output, b"sentinel"))


def test_completion_checks_process_before_accepting_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out.pcap"
    output.write_bytes(driver.pcap_header() + driver.pcap_record(1, 0, b"sentinel"))
    monkeypatch.setattr(driver.time, "sleep", lambda _: None)
    proc = Mock(spec=subprocess.Popen)
    proc.poll.return_value = 2
    proc.returncode = 2
    with pytest.raises(driver.DriverError, match="exited with code 2"):
        driver._wait_for_completion(proc, [output], (output, b"sentinel"))


def test_completion_does_not_accept_quiet_output_before_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out.pcap"
    output.write_bytes(driver.pcap_header())
    ticks = iter([0.0, 0.25, 0.5])
    calls = 0

    def clock() -> float:
        nonlocal calls
        calls += 1
        if calls == 3:
            output.write_bytes(driver.pcap_header() + driver.pcap_record(1, 0, b"sentinel"))
        return next(ticks)

    monkeypatch.setattr(driver.time, "monotonic", clock)
    monkeypatch.setattr(driver.time, "sleep", lambda _: None)
    monkeypatch.setattr(driver, "MIN_RUN", 0)
    monkeypatch.setattr(driver, "SETTLE", 0)
    proc = Mock(spec=subprocess.Popen)
    proc.poll.return_value = None
    driver._wait_for_completion(proc, [output], (output, b"sentinel"))
    assert calls == 3


def test_legacy_completion_does_not_acquire_readback_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out.pcap"
    output.write_bytes(driver.pcap_header())
    ticks = iter([0.0, 61.0, 62.0])
    calls = 0

    def clock() -> float:
        nonlocal calls
        calls += 1
        if calls == 2:
            output.write_bytes(driver.pcap_header() + driver.pcap_record(1, 0, b"packet"))
        return next(ticks)

    monkeypatch.setattr(driver.time, "monotonic", clock)
    monkeypatch.setattr(driver.time, "sleep", lambda _: None)
    proc = Mock(spec=subprocess.Popen)
    proc.poll.return_value = None
    driver._wait_for_completion(proc, [output])
    assert calls == 3
