"""Exact pinned P4-SpecTec differences on unchanged native v1model sources."""

from __future__ import annotations

import subprocess

ACTUAL = {
    "v1model_egress_redirect": (3, "0002"),
    "v1model_egress_spec_read": (2, "0202"),
}


class KnownV1ModelDisagreement(Exception):
    """Only the observed packet mismatch, never compiler or runner errors."""


def known(name: str, done: subprocess.CompletedProcess[str]) -> bool:
    if name not in ACTUAL or done.returncode != 1 or done.stdout:
        return False
    port, data = ACTUAL[name]
    expected = (
        f"[FAIL] Remaining packets to be matched:\n({port}) {data}"
        "[FAIL] Expected packets to be output:\n(2) 0002\n\n  source: sim\n"
        if name == "v1model_egress_redirect"
        else "expected (2) 0002 but got (2) 0202\n\n  source: sim\n"
    )
    _, marker, error = done.stderr.partition("error: ")
    return marker == "error: " and error == expected
