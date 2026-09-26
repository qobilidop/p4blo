"""Shared printer native-tool lifecycle helpers."""

from __future__ import annotations

import functools
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# p4test through Docker
# ---------------------------------------------------------------------------

# p4c 1.2.5.15 from Bili's multi-arch builds (github.com/qobilidop/p4lang-builds),
# pinned by the digest of its image index so amd64 and arm64 hosts both run it
# natively. Update with `docker buildx imagetools inspect <image>:<tag>`.
P4C_IMAGE = (
    "ghcr.io/qobilidop/p4lang-builds/p4c"
    "@sha256:794edb1682e286792fbf7b1ca5da2ed7be52ddbeab3659a3bbfb4e1906684e48"
)

_DOCKER_EXIT_CODES = {125, 126, 127}


class PrinterCleanupError(RuntimeError):
    """Owned-container cleanup was not confirmed; never an optional skip."""


def run_p4test(arguments: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    """Bound client execution and independently verify owned-container cleanup."""
    name = f"p4blo-p4test-{uuid4().hex}"
    try:
        return subprocess.run(
            ["docker", "run", "--rm", "--name", name, *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    finally:
        cleanup_error: Exception | None = None
        try:
            subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as error:
            cleanup_error = error
        try:
            remaining = subprocess.run(
                ["docker", "ps", "--all", "--quiet", "--filter", f"name=^/{name}$"],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise PrinterCleanupError(f"Cannot verify p4test container absence: {name}") from error
        if remaining.stdout.strip():
            raise PrinterCleanupError(f"p4test container survived cleanup: {name}")
        if cleanup_error is not None:
            raise PrinterCleanupError(f"p4test cleanup command failed: {name}") from cleanup_error


@functools.cache
def p4test_available() -> str | None:
    """None when p4test runs, otherwise the reason to skip."""
    if shutil.which("docker") is None:
        return "docker is not installed"
    try:
        image = subprocess.run(
            ["docker", "image", "inspect", P4C_IMAGE],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Preserve the old cold-image implicit-pull allowance. A warm image
        # needs only a short version probe, not the full compiler budget.
        probe = run_p4test(
            [P4C_IMAGE, "p4test", "--version"],
            timeout=30 if image.returncode == 0 else 600,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"docker did not run: {e}"
    if probe.returncode != 0:
        return f"{P4C_IMAGE} did not run: {probe.stderr.strip()}"
    return None


def p4test(path: Path, attempt: int = 0) -> None:
    """Typecheck `path` with p4test; skip on a Docker problem, fail on a
    p4test error."""
    reason = p4test_available()
    if reason is not None:
        pytest.skip(reason)
    result = run_p4test(
        [
            "-v",
            f"{path.parent}:/w",
            P4C_IMAGE,
            "p4test",
            f"/w/{path.name}",
        ],
        timeout=600,
    )
    if result.returncode == 0:
        return
    if result.returncode in _DOCKER_EXIT_CODES or "No such file or directory" in result.stderr:
        pytest.skip(f"docker could not run p4test on {path}: {result.stderr.strip()}")
    if "internal compiler error" in result.stderr:
        # Kept from the days of an amd64-only image under emulation, whose C
        # preprocessor crashed now and then; harmless with a native image.
        if attempt < 2:
            return p4test(path, attempt=attempt + 1)
        pytest.skip(f"p4c crashed under emulation on {path}: {result.stderr.strip()[:200]}")
    pytest.fail(f"p4test rejected {path}:\n{result.stderr}")
