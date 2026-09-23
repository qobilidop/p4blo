"""The half of the BMv2 oracle that runs inside the container.

oracle/bmv2/run.py, on the host, prints the program, translates the vector
and judges; this script, installed in the image as `p4blo-bmv2-driver`,
compiles and replays. Everything crosses the container boundary as JSON on
stdin and stdout, so no host directory is bind-mounted and the pcap FIFOs
below live in the container's own filesystem. Standard library only, Python
3.12 (the image's interpreter).

    p4blo-bmv2-driver compile   stdin: P4 source
                                stdout: {"ok": bool, "json": <BMv2 JSON>,
                                         "output": <compiler output>}
    p4blo-bmv2-driver replay    stdin: {"json": <BMv2 JSON>,
                                        "ports": [int, ...],
                                        "phases": [{"commands": [str, ...],
                                                    "packets": [{"port": int,
                                                                 "data": hex}]}]}
                                stdout: {"phases": [<phase result>, ...]}
    p4blo-bmv2-driver --version the versions of the tools in the image

A phase is one run of simple_switch: its commands are fed to
simple_switch_CLI before any of its packets is sent, which is how the host
side keeps a vector's `add` lines ahead of the packets that follow them.
Packets go in the way p4c's backends/bmv2/bmv2stf.py sends them, through
`--use-files` with one pcap FIFO per port: the switch opens the FIFOs at
startup in `-i` order and blocks on each until a writer appears, so this
script opens them for writing in the same order and writes the pcap header
at once; the reader thread then blocks on every FIFO's first record until
the packets are written and the FIFOs closed, after the CLI is done. Packets
carry increasing timestamps because the reader merges its files by
timestamp. Outputs are read from the per-port `_out.pcap` files, which the
switch flushes per packet.

There is no signal for "every packet has been processed": this BMv2 build
has its logging macros compiled out, so the per-packet debug lines are
absent, and the Thrift API exposes no port counters. As p4c's runner does
(a flat two-second sleep), the run is called complete once the output files
have stopped growing for a while after the inputs were closed. A phase's
result is

    {"error": null | str,
     "cli": str,                          the CLI's output
     "outputs": {"<port>": [hex, ...]},   the per-port pcaps, in order
     "log": str}                          the switch's log and stderr
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import json
import os
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

THRIFT_PORT = 9090
# A bound on the switch loading its JSON and opening its ports, generous so
# that a loaded CI runner is not mistaken for a hang.
START_TIMEOUT = 60.0
# After the inputs are closed the switch gets at least MIN_RUN seconds,
# p4c's own allowance, and the run is complete once the output files have
# also not grown for SETTLE seconds.
MIN_RUN = 2.0
SETTLE = 1.0
# Room in each FIFO for a phase's packets on that port, since they are all
# written before the switch necessarily reads any (Linux allows 1 MiB
# unprivileged).
PIPE_SIZE = 1 << 20
LOG_TAIL_LINES = 60


class DriverError(Exception):
    pass


# ---------------------------------------------------------------------------
# pcap
# ---------------------------------------------------------------------------

PCAP_MAGIC = 0xA1B2C3D4
LINKTYPE_ETHERNET = 1


def pcap_header() -> bytes:
    """A little-endian pcap file header: version 2.4, no time zone
    correction, 65535 snap length, Ethernet link type."""
    return struct.pack("<IHHiIII", PCAP_MAGIC, 2, 4, 0, 0, 65535, LINKTYPE_ETHERNET)


def pcap_record(ts_sec: int, ts_usec: int, data: bytes) -> bytes:
    return struct.pack("<IIII", ts_sec, ts_usec, len(data), len(data)) + data


def read_pcap(blob: bytes) -> list[bytes]:
    """The packets of a pcap file, in order; the switch writes them with
    libpcap's default (host) byte order, and either is accepted."""
    if len(blob) < 24:
        if not blob:
            return []
        raise DriverError(f"pcap file of {len(blob)} bytes has no header")
    (magic,) = struct.unpack("<I", blob[:4])
    if magic in (0xA1B2C3D4, 0xA1B23C4D):
        order = "<"
    elif magic in (0xD4C3B2A1, 0x4D3CB2A1):
        order = ">"
    else:
        raise DriverError(f"not a pcap file: magic {magic:#x}")
    packets: list[bytes] = []
    offset = 24
    while offset < len(blob):
        if offset + 16 > len(blob):
            raise DriverError("truncated pcap record header")
        _, _, incl_len, _ = struct.unpack(order + "IIII", blob[offset : offset + 16])
        offset += 16
        if offset + incl_len > len(blob):
            raise DriverError("truncated pcap record")
        packets.append(blob[offset : offset + incl_len])
        offset += incl_len
    return packets


# ---------------------------------------------------------------------------
# One phase
# ---------------------------------------------------------------------------


def _open_fifo_writer(path: Path, proc: subprocess.Popen[bytes], deadline: float):
    """Open a FIFO for writing once the switch has it open for reading.

    A blocking open would hang forever if the switch died first, so this
    polls with O_NONBLOCK (ENXIO until a reader is there) and then makes
    the descriptor blocking again for the writes.
    """
    while True:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
            break
        except OSError as e:
            if e.errno != errno.ENXIO:
                raise
        if proc.poll() is not None:
            raise DriverError(f"simple_switch exited with code {proc.returncode} while starting")
        if time.monotonic() > deadline:
            raise DriverError(f"simple_switch did not open {path.name} in {START_TIMEOUT}s")
        time.sleep(0.02)
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
    try:
        fcntl.fcntl(fd, fcntl.F_SETPIPE_SZ, PIPE_SIZE)
    except OSError:
        pass  # the default 64 KiB then; enough for any corpus vector
    return os.fdopen(fd, "wb", buffering=0)


def _wait_for_thrift(proc: subprocess.Popen[bytes], deadline: float) -> None:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", THRIFT_PORT)) == 0:
                return
        if proc.poll() is not None:
            raise DriverError(f"simple_switch exited with code {proc.returncode} while starting")
        if time.monotonic() > deadline:
            raise DriverError(f"simple_switch's Thrift server did not come up in {START_TIMEOUT}s")
        time.sleep(0.05)


def _run_cli(commands: list[str]) -> str:
    """Feed the commands to simple_switch_CLI and check that each took."""
    if not commands:
        return ""
    result = subprocess.run(
        ["simple_switch_CLI", "--thrift-port", str(THRIFT_PORT)],
        input="\n".join(commands) + "\n",
        capture_output=True,
        text=True,
        timeout=START_TIMEOUT,
    )
    output = result.stdout + result.stderr
    added = output.count("Entry has been added with handle")
    defaulted = output.count("Setting default action of")
    wanted_adds = sum(c.startswith("table_add ") for c in commands)
    wanted_defaults = sum(c.startswith("table_set_default ") for c in commands)
    problems = [
        line
        for line in output.splitlines()
        if line.startswith(("Invalid", "Error", "Traceback")) or "Exception" in line
    ]
    if result.returncode != 0 or problems or added != wanted_adds or defaulted != wanted_defaults:
        raise DriverError(
            f"simple_switch_CLI installed {added} of {wanted_adds} entries and "
            f"{defaulted} of {wanted_defaults} defaults (exit {result.returncode}):\n{output}"
        )
    return output


def _wait_for_completion(proc: subprocess.Popen[bytes], outputs: list[Path]) -> None:
    """Return once the output files have stopped growing for SETTLE seconds,
    and not before MIN_RUN seconds have passed."""

    def size() -> int:
        return sum(p.stat().st_size for p in outputs if p.exists())

    start = time.monotonic()
    last = size()
    quiet_since = start
    while True:
        time.sleep(0.05)
        if proc.poll() is not None:
            raise DriverError(f"simple_switch exited with code {proc.returncode} mid-run")
        now = time.monotonic()
        current = size()
        if current != last:
            last = current
            quiet_since = now
        if now - start >= MIN_RUN and now - quiet_since >= SETTLE:
            return


def _stop(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _tail(path: Path) -> str:
    try:
        text = path.read_text(errors="replace")
    except FileNotFoundError:
        return ""
    return "\n".join(text.splitlines()[-LOG_TAIL_LINES:])


def run_phase(
    json_path: Path, ports: list[int], commands: list[str], packets: list[dict], workdir: Path
) -> dict:
    ports = sorted(set(ports))
    for packet in packets:
        if packet["port"] not in ports:
            raise DriverError(f"packet on port {packet['port']}, which has no interface")
    prefix = workdir / "port"
    log_base = workdir / "switch"
    for port in ports:
        os.mkfifo(f"{prefix}{port}_in.pcap")
    command = [
        "simple_switch",
        "--log-file",
        str(log_base),
        "--log-flush",
        "--use-files",
        "0",
        "--thrift-port",
        str(THRIFT_PORT),
        "--device-id",
        "0",
    ]
    for port in ports:
        command += ["-i", f"{port}@{prefix}{port}"]
    command.append(str(json_path))
    stderr_path = workdir / "switch.stderr"
    with stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(command, stdout=stderr, stderr=subprocess.STDOUT, cwd=workdir)
    writers = []
    result: dict = {"error": None, "cli": "", "outputs": {}}
    try:
        deadline = time.monotonic() + START_TIMEOUT
        # In -i order, which is the order the switch opens them in.
        for port in ports:
            writer = _open_fifo_writer(Path(f"{prefix}{port}_in.pcap"), proc, deadline)
            writer.write(pcap_header())
            writers.append(writer)
        _wait_for_thrift(proc, deadline)
        result["cli"] = _run_cli(commands)
        # Timestamps one second apart, in vector order: the reader merges
        # its files by timestamp, so the order across ports is this one.
        for number, packet in enumerate(packets, start=1):
            writers[ports.index(packet["port"])].write(
                pcap_record(number, 0, bytes.fromhex(packet["data"]))
            )
        for writer in writers:
            writer.close()
        writers = []
        _wait_for_completion(proc, [Path(f"{prefix}{port}_out.pcap") for port in ports])
    except DriverError as e:
        result["error"] = str(e)
    finally:
        for writer in writers:
            writer.close()
        _stop(proc)
    if result["error"] is None and proc.returncode not in (0, -signal.SIGTERM):
        result["error"] = f"simple_switch exited with code {proc.returncode}"
    outputs: dict[str, list[str]] = {}
    for port in ports:
        out = Path(f"{prefix}{port}_out.pcap")
        try:
            outputs[str(port)] = [p.hex() for p in read_pcap(out.read_bytes())]
        except (OSError, DriverError) as e:
            outputs[str(port)] = []
            if result["error"] is None:
                result["error"] = f"could not read {out.name}: {e}"
    result["outputs"] = outputs
    # The switch adds .txt to the log file's name itself.
    result["log"] = "\n".join(
        part for part in (_tail(log_base.with_suffix(".txt")), _tail(stderr_path)) if part
    )
    return result


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def compile_program(source: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="p4blo-bmv2-") as tmp:
        p4 = Path(tmp) / "prog.p4"
        out = Path(tmp) / "prog.json"
        p4.write_text(source)
        result = subprocess.run(
            ["p4c-bm2-ss", str(p4), "-o", str(out)],
            capture_output=True,
            text=True,
            cwd=tmp,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0 or not out.is_file():
            return {"ok": False, "json": None, "output": output}
        return {"ok": True, "json": json.loads(out.read_text()), "output": output}


def replay(request: dict) -> dict:
    phases = []
    with tempfile.TemporaryDirectory(prefix="p4blo-bmv2-") as tmp:
        json_path = Path(tmp) / "prog.json"
        json_path.write_text(json.dumps(request["json"]))
        for number, phase in enumerate(request["phases"]):
            workdir = Path(tmp) / f"phase{number}"
            workdir.mkdir()
            try:
                result = run_phase(
                    json_path, request["ports"], phase["commands"], phase["packets"], workdir
                )
            except DriverError as e:
                result = {"error": str(e), "cli": "", "outputs": {}, "log": ""}
            phases.append(result)
            if result["error"] is not None:
                break
    return {"phases": phases}


def versions() -> str:
    lines = []
    for command in (["p4c-bm2-ss", "--version"], ["simple_switch", "--version"]):
        result = subprocess.run(command, capture_output=True, text=True)
        lines.append(f"{command[0]}: {(result.stdout + result.stderr).strip()}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="p4blo-bmv2-driver")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("command", nargs="?", choices=["compile", "replay"])
    args = parser.parse_args(argv)
    if args.version:
        print(versions())
        return 0
    if args.command == "compile":
        json.dump(compile_program(sys.stdin.read()), sys.stdout)
    elif args.command == "replay":
        json.dump(replay(json.load(sys.stdin)), sys.stdout)
    else:
        parser.error("a command is required")
    return 0


if __name__ == "__main__":
    sys.exit(main())
