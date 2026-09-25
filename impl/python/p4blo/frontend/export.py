"""Run P4-SpecTec's `il-export` on a P4 source file.

The command exists only in a P4-SpecTec checkout built by
tests/oracle/build.sh, which applies tests/oracle/patches/0002-il-export.patch.
It parses the program, runs the spec's typing relation `Program_ok` and its
instantiation relation `Program_inst`, and prints both results as JSON
(`p4blo.frontend.il`). The checkout is found as the oracle tests find it:
`$P4BLO_ORACLE_BIN`, else `$P4BLO_ORACLE_DIR/p4spectec`, else
`~/.cache/p4blo/p4-spectec/p4spectec`; the spec and `p4c/p4include` are
taken from the checkout the binary sits in.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from p4blo.frontend import il

__all__ = ["DEFAULT_ORACLE_DIR", "ExportError", "Exporter", "find_exporter"]

DEFAULT_ORACLE_DIR = Path.home() / ".cache" / "p4blo" / "p4-spectec"
# Typing and instantiation take about a second; the limit only guards a hang.
TIMEOUT_SECONDS = 300


class ExportError(Exception):
    """P4-SpecTec rejected the program, or the command could not run."""


@dataclass(frozen=True)
class Exporter:
    """A built P4-SpecTec checkout that has the `il-export` command."""

    binary: Path
    root: Path

    @property
    def spec(self) -> Path:
        return self.root / "spec"

    @property
    def include(self) -> Path:
        return self.root / "p4c" / "p4include"

    def missing(self) -> str | None:
        """Why this checkout cannot export, or None when it can."""
        if not os.access(self.binary, os.X_OK):
            return f"{self.binary} is not an executable"
        if not self.spec.is_dir():
            return f"{self.spec} is not a directory; is {self.root} a P4-SpecTec checkout?"
        if not (self.include / "core.p4").is_file():
            return f"{self.include} has no core.p4; tests/oracle/build.sh fetches it"
        help_text = subprocess.run(
            [str(self.binary), "help"], capture_output=True, text=True, check=False
        )
        if "il-export" not in help_text.stdout + help_text.stderr:
            return f"{self.binary} has no il-export command; rebuild with tests/oracle/build.sh"
        return None

    def export_text(self, source: Path, includes: Sequence[Path] = ()) -> str:
        """The raw JSON for `source`."""
        command = [str(self.binary), "il-export", str(self.spec)]
        for include in (self.include, *includes):
            command += ["-i", str(include)]
        command += ["-p", str(Path(source).resolve())]
        try:
            done = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise ExportError(f"il-export timed out on {source}") from e
        if done.returncode != 0:
            # The spec's diagnostics go to stderr; its elaboration warnings
            # come first, so the tail is what went wrong.
            tail = "\n".join(done.stderr.strip().splitlines()[-30:])
            raise ExportError(f"P4-SpecTec rejected {source}:\n{tail}")
        return done.stdout

    def export(self, source: Path, includes: Sequence[Path] = ()) -> il.Export:
        """The typed and instantiated IL of `source`."""
        return il.loads(self.export_text(source, includes))


def find_exporter(environ: Mapping[str, str] | None = None) -> Exporter | None:
    """The checkout the environment points at, or None when nothing is built."""
    env = os.environ if environ is None else environ
    bin_var = env.get("P4BLO_ORACLE_BIN")
    if bin_var:
        binary = Path(bin_var).expanduser().resolve()
        exporter = Exporter(binary, binary.parent)
    else:
        root = Path(env.get("P4BLO_ORACLE_DIR") or DEFAULT_ORACLE_DIR).expanduser().resolve()
        exporter = Exporter(root / "p4spectec", root)
    return exporter if exporter.binary.is_file() else None
