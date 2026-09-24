"""Bind the fixed Lean execution certificate to the Python interpreter.

The program comes from Lean's exported AST. Python independently binds its
externs, runs its statements, and claims only the observation the Lean checker
accepts. This is one fixed low-level example, not a switch-program validator.

    python -m p4blo.drt.certificate create --register 41 --counter 9 -o claim.json
    python -m p4blo.drt.certificate verify claim.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from p4blo import ir
from p4blo.arch.externs import default_registry
from p4blo.arch.externs.counter import Counter
from p4blo.arch.externs.register import Register
from p4blo.drt.run import default_lean_binary
from p4blo.interp.api import InterpError
from p4blo.interp.env import Env
from p4blo.interp.errors import ParseError
from p4blo.interp.stmt import execute
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb

FORMAT = "p4blo.example-certificate"
EXAMPLE = "register-counter-v1"
VERSION = 1
DEFAULT_FUEL = 10
DEFAULT_TIMEOUT = 10.0

type Verdict = Literal["accepted", "mismatch", "exhausted"]


class Completion(TypedDict):
    kind: Literal["success", "interp", "parse"]
    message: NotRequired[str]


class Claim(TypedDict):
    completion: Completion
    register: list[object] | None
    counter: list[str] | None
    local: list[object] | None


class Artifact(TypedDict):
    format: str
    version: int
    example: str
    program: dict[str, object]
    initial: list[str]
    fuel: int
    claim: Claim


class CertificateError(Exception):
    """The checker process or its wire response could not be trusted."""


class InvalidCertificate(CertificateError):
    """The Lean checker rejected an invalid artifact."""


def _command(lean_binary: str | Path | None) -> str:
    return str(default_lean_binary() if lean_binary is None else lean_binary)


def _kill_owned_process_group(process: subprocess.Popen[bytes]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()


def _invoke(
    lean_binary: str | Path | None,
    mode: str,
    *,
    payload: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, str]:
    """Bound writes, reads and descendant-held pipes for one Lean invocation."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    command = [_command(lean_binary), mode]
    try:
        payload_bytes = None if payload is None else payload.encode("utf-8")
    except UnicodeError as error:
        raise CertificateError(f"Lean {mode} request is not UTF-8") from error
    if payload is not None:
        command.append("-")
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
    except OSError as error:
        raise CertificateError(f"cannot start {command[0]}: {error}") from error
    cleanup_attempted = False
    cleanup_error: OSError | None = None

    def cleanup_group() -> None:
        nonlocal cleanup_attempted, cleanup_error
        if cleanup_attempted:
            return
        cleanup_attempted = True
        try:
            _kill_owned_process_group(process)
        except OSError as error:
            cleanup_error = error

    try:
        stdout, stderr = process.communicate(input=payload_bytes, timeout=timeout)
    except subprocess.TimeoutExpired:
        cleanup_group()
        reap_error: OSError | None = None
        try:
            process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            # An escaped descendant may still own a pipe. Close our ends and
            # reap only the owned leader; never wait forever for that pipe.
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            except OSError as error:
                reap_error = error
        except OSError as error:
            reap_error = error
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            except OSError as wait_error:
                reap_error = wait_error
        if cleanup_error is not None:
            raise CertificateError(
                f"Lean {mode} timed out after {timeout:g}s; "
                f"process-group cleanup failed: {cleanup_error}"
            ) from cleanup_error
        if reap_error is not None:
            raise CertificateError(
                f"Lean {mode} timed out after {timeout:g}s; reap failed: {reap_error}"
            ) from reap_error
        if process.returncode is None:
            raise CertificateError(
                f"Lean {mode} timed out after {timeout:g}s; leader did not terminate"
            ) from None
        raise CertificateError(f"Lean {mode} timed out after {timeout:g}s") from None
    except OSError as error:
        cleanup_group()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        except OSError as reap_error:
            if cleanup_error is None:
                raise CertificateError(
                    f"Lean {mode} exchange failed: {error}; reap failed: {reap_error}"
                ) from reap_error
        if cleanup_error is not None:
            raise CertificateError(
                f"Lean {mode} exchange failed: {error}; "
                f"process-group cleanup failed: {cleanup_error}"
            ) from cleanup_error
        if process.returncode is None:
            raise CertificateError(
                f"Lean {mode} exchange failed: {error}; leader did not terminate"
            ) from error
        raise CertificateError(f"Lean {mode} exchange failed: {error}") from error
    finally:
        # A successful leader can leave descendants after closing the pipes.
        # The process group belongs to this invocation even on normal exit.
        cleanup_group()
    if cleanup_error is not None:
        raise CertificateError(f"Lean {mode} process-group cleanup failed: {cleanup_error}") from (
            cleanup_error
        )
    try:
        output = stdout.decode("utf-8")
        details = stderr.decode("utf-8").strip()
    except UnicodeError as error:
        raise CertificateError(f"Lean {mode} returned non-UTF-8 output") from error
    if process.returncode is None:
        raise CertificateError(f"Lean {mode} did not terminate")
    if details and process.returncode != 0:
        # Keep stderr as a diagnostic only. The JSON verdict remains the
        # authority for whether the artifact was accepted or rejected.
        details = f": {details}"
    else:
        details = ""
    if not output.strip():
        raise CertificateError(f"Lean {mode} returned no JSON (exit {process.returncode}{details})")
    return process.returncode, output


def _object(output: str, mode: str) -> dict[str, object]:
    def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(output, object_pairs_hook=unique_fields)
    except (ValueError, UnicodeError) as error:
        raise CertificateError(f"Lean {mode} returned malformed JSON") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CertificateError(f"Lean {mode} returned no JSON object")
    return value


def export_example_program(
    *, lean_binary: str | Path | None = None, timeout: float = DEFAULT_TIMEOUT
) -> pb.Program:
    """Fetch and decode the exact AST exported by the fixed Lean example."""
    code, output = _invoke(lean_binary, "certificate-example-program", timeout=timeout)
    if code != 0:
        raise CertificateError(f"Lean program export exited {code}")
    _object(output, "certificate-example-program")
    try:
        return ir.load_json(output)
    except (ValueError, TypeError) as error:
        raise CertificateError(f"Lean program export is not a Program: {error}") from error


def _natural(value: int, name: str, *, limit: int | None = None) -> int:
    if type(value) is not int or value < 0 or (limit is not None and value >= limit):
        bound = f" below {limit}" if limit is not None else ""
        raise ValueError(f"{name} must be a nonnegative integer{bound}")
    return value


def _observed_bits(value: Bits) -> list[object]:
    if (
        type(value.width) is not int
        or value.width <= 0
        or type(value.value) is not int
        or value.value < 0
        or value.value.bit_length() > value.width
    ):
        raise CertificateError("Python produced a malformed bits value")
    return [value.width, hex(value.value)]


def _observe(program: pb.Program, register_value: int, counter_value: int) -> Claim:
    """Execute the imported AST with the real Python statement interpreter."""
    index = ir.Index.build(program)
    block = index.blocks["C"]
    externs = default_registry().bind(index)
    register = externs["r"]
    counter = externs["k"]
    if not isinstance(register, Register) or not isinstance(counter, Counter):
        raise CertificateError("the example extern bindings have unexpected types")
    if register.width != 8 or len(register.cells) != 1 or len(counter.counts) != 1:
        raise CertificateError("the example extern bindings have unexpected shapes")
    register.cells[0] = Bits(8, register_value)
    counter.counts[0] = counter_value
    env = Env.for_block(index, block, externs)
    completion: Completion = {"kind": "success"}
    try:
        execute(block.body, env)
    except ParseError as error:
        completion = {"kind": "parse", "message": error.error.name}
    except InterpError as error:
        completion = {"kind": "interp", "message": str(error)}
    # Observe the final environment, not objects retained before execution:
    # replacing or deleting a binding must not certify stale state.
    register = env.externs.get("r")
    counter = env.externs.get("k")
    register_state: list[object] | None = None
    if isinstance(register, Register):
        if type(register.width) is not int or register.width <= 0:
            raise CertificateError("Python produced a malformed register width")
        cells: list[str] = []
        for cell in register.cells:
            if not isinstance(cell, Bits) or cell.width != register.width:
                raise CertificateError("Python produced inconsistent register cell widths")
            _observed_bits(cell)
            cells.append(hex(cell.value))
        register_state = [register.width, cells]
    counter_state: list[str] | None = None
    if isinstance(counter, Counter):
        if any(type(value) is not int or value < 0 for value in counter.counts):
            raise CertificateError("Python produced a malformed counter value")
        counter_state = [hex(value) for value in counter.counts]
    local = env.vars.get("value")
    return {
        "completion": completion,
        "register": register_state,
        "counter": counter_state,
        "local": _observed_bits(local) if isinstance(local, Bits) else None,
    }


def create_example_certificate(
    register: int,
    counter: int,
    *,
    fuel: int = DEFAULT_FUEL,
    lean_binary: str | Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Artifact:
    """Create one concrete claim; verification is a separate Lean call."""
    register = _natural(register, "register", limit=256)
    counter = _natural(counter, "counter")
    fuel = _natural(fuel, "fuel")
    program = export_example_program(lean_binary=lean_binary, timeout=timeout)
    raw_program = _object(ir.dump_json(program), "program encoding")
    return {
        "format": FORMAT,
        "version": VERSION,
        "example": EXAMPLE,
        "program": raw_program,
        "initial": [hex(register), hex(counter)],
        "fuel": fuel,
        "claim": _observe(program, register, counter),
    }


def verify_example_certificate(
    artifact: Artifact | str,
    *,
    lean_binary: str | Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Verdict:
    """Ask the fixed Lean checker; reject missing or contradictory verdicts."""
    try:
        payload = artifact if isinstance(artifact, str) else json.dumps(artifact, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise InvalidCertificate(f"artifact is not JSON: {error}") from error
    code, output = _invoke(
        lean_binary, "check-example-certificate", payload=payload, timeout=timeout
    )
    reply = _object(output, "check-example-certificate")
    if code == 2 and set(reply) == {"error"} and isinstance(reply["error"], str):
        raise InvalidCertificate(reply["error"])
    if set(reply) != {"verdict"}:
        raise CertificateError(f"Lean checker returned no exact verdict object (exit {code})")
    verdict = reply["verdict"]
    expected = {"accepted": 0, "mismatch": 1, "exhausted": 1}
    if not isinstance(verdict, str) or verdict not in expected or code != expected[verdict]:
        raise CertificateError(f"Lean checker verdict/exit mismatch: {verdict!r}, exit {code}")
    if verdict == "accepted":
        return "accepted"
    if verdict == "mismatch":
        return "mismatch"
    return "exhausted"


def _arg_nat(text: str) -> int:
    try:
        return int(text, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="run Python and write an example claim")
    create.add_argument("--register", type=_arg_nat, required=True)
    create.add_argument("--counter", type=_arg_nat, required=True)
    create.add_argument("--fuel", type=_arg_nat, default=DEFAULT_FUEL)
    create.add_argument("-o", "--output", default="-", help="artifact path or '-' for stdout")
    verify = commands.add_parser("verify", help="check a saved artifact with Lean")
    verify.add_argument("artifact", help="artifact path or '-' for stdin")
    for command in (create, verify):
        command.add_argument("--lean", type=Path, default=None, help="p4blo-lean executable")
        command.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            artifact = create_example_certificate(
                args.register,
                args.counter,
                fuel=args.fuel,
                lean_binary=args.lean,
                timeout=args.timeout,
            )
            output = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
            if args.output == "-":
                sys.stdout.write(output)
            else:
                Path(args.output).write_text(output)
            return 0
        source = sys.stdin.read() if args.artifact == "-" else Path(args.artifact).read_text()
        verdict = verify_example_certificate(source, lean_binary=args.lean, timeout=args.timeout)
        print(json.dumps({"verdict": verdict}))
        return 0 if verdict == "accepted" else 1
    except (CertificateError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
