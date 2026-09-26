"""Deterministic lifecycle failures without disturbing Docker or other jobs."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.support import printer_runtime as printer


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "exit",
        "start",
        "timeout",
        "rm-timeout",
        "rm-start",
        "survivor",
        "ps-exit",
        "ps-timeout",
    ],
)
def test_owned_container_cleanup(monkeypatch: pytest.MonkeyPatch, failure: str | None) -> None:
    calls: list[list[str]] = []

    def command(argv: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert options["timeout"] == (0.1 if argv[1] == "run" else 15)
        if argv[1] == "run":
            if failure == "start":
                raise OSError("client unavailable")
            if failure == "timeout":
                raise subprocess.TimeoutExpired(argv, 0.1)
            return subprocess.CompletedProcess(argv, 1 if failure == "exit" else 0, "answer", "")
        if argv[1] == "rm":
            if failure == "rm-timeout":
                raise subprocess.TimeoutExpired(argv, 15)
            if failure == "rm-start":
                raise OSError("cleanup unavailable")
            return subprocess.CompletedProcess(argv, 1, "", "already absent")
        assert argv[1] == "ps" and options["check"] is True
        if failure == "ps-exit":
            raise subprocess.CalledProcessError(1, argv)
        if failure == "ps-timeout":
            raise subprocess.TimeoutExpired(argv, 15)
        return subprocess.CompletedProcess(argv, 0, "id" if failure == "survivor" else "", "")

    monkeypatch.setattr(subprocess, "run", command)
    if failure in (None, "exit"):
        result = printer.run_p4test(["image", "p4test"], timeout=0.1)
        assert result.stdout == "answer" and result.returncode == (failure == "exit")
    elif failure == "start":
        with pytest.raises(OSError, match="client unavailable"):
            printer.run_p4test(["image", "p4test"], timeout=0.1)
    elif failure == "timeout":
        with pytest.raises(subprocess.TimeoutExpired):
            printer.run_p4test(["image", "p4test"], timeout=0.1)
    else:
        with pytest.raises(printer.PrinterCleanupError):
            printer.run_p4test(["image", "p4test"], timeout=0.1)
    assert len(calls) == 3
    name = calls[0][4]
    assert name.startswith("p4blo-p4test-") and len(name.removeprefix("p4blo-p4test-")) == 32
    assert calls == [
        ["docker", "run", "--rm", "--name", name, "image", "p4test"],
        ["docker", "rm", "--force", name],
        ["docker", "ps", "--all", "--quiet", "--filter", f"name=^/{name}$"],
    ]


@pytest.mark.parametrize("warm", [False, True])
def test_probe_budget(monkeypatch: pytest.MonkeyPatch, warm: bool) -> None:
    def inspect(argv: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        assert argv == ["docker", "image", "inspect", printer.P4C_IMAGE]
        assert options["timeout"] == 15
        return subprocess.CompletedProcess(argv, 0 if warm else 1, "", "")

    def run(arguments: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        assert arguments == [printer.P4C_IMAGE, "p4test", "--version"]
        assert timeout == (30 if warm else 600)
        return subprocess.CompletedProcess(arguments, 0, "version", "")

    monkeypatch.setattr(printer.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(subprocess, "run", inspect)
    monkeypatch.setattr(printer, "run_p4test", run)
    assert printer.p4test_available.__wrapped__() is None


def test_probe_cleanup_failure_is_not_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(printer.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(
        subprocess, "run", lambda argv, **_: subprocess.CompletedProcess(argv, 0, "", "")
    )

    def fail(arguments: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        raise printer.PrinterCleanupError("unconfirmed cleanup")

    monkeypatch.setattr(printer, "run_p4test", fail)
    with pytest.raises(printer.PrinterCleanupError, match="unconfirmed cleanup"):
        printer.p4test_available.__wrapped__()


@pytest.mark.parametrize("failure", ["compiler", "timeout", "cleanup"])
def test_compile_failures_are_not_skipped(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    path = Path("/owned/golden.p4")
    monkeypatch.setattr(printer, "p4test_available", lambda: None)

    def run(arguments: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        assert arguments == ["-v", "/owned:/w", printer.P4C_IMAGE, "p4test", "/w/golden.p4"]
        assert timeout == 600
        if failure == "timeout":
            raise subprocess.TimeoutExpired(arguments, timeout)
        if failure == "cleanup":
            raise printer.PrinterCleanupError("unconfirmed cleanup")
        return subprocess.CompletedProcess(arguments, 1, "", "syntax error")

    monkeypatch.setattr(printer, "run_p4test", run)
    error = {
        "compiler": pytest.fail.Exception,
        "timeout": subprocess.TimeoutExpired,
        "cleanup": printer.PrinterCleanupError,
    }[failure]
    with pytest.raises(error):
        printer.p4test(path)
