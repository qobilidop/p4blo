"""Three source faults, run by both interpreters against independent expectations.

Run with the main checkout's Python environment. Supply a disposable worktree
containing the current gateway source and test. Only that source is mutated;
it is restored even when the campaign fails. No interpreter is rebuilt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELATIVE = Path("tests/programs/corpus/vlan_gateway/vlan_gateway.py")
FAULTS = (
    (
        "initial-drop",
        "    def apply(self) -> None:\n        self.assign(self.meta.egress_spec, 511)\n",
        "    def apply(self) -> None:\n",
    ),
    ("tag-validity", "        self.set_invalid(self.hdr.vlan)\n", ""),
    (
        "counter-index",
        "        admissions.count(port.cast(p4.bit32))\n",
        "        admissions.count(p4.bit32(0))\n",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    worktree, out = args.worktree.resolve(), args.out.resolve()
    assert worktree != ROOT, "never mutate the integrator's tree"
    assert (worktree / ".git").is_file(), "an isolated git worktree is required"
    assert not out.exists(), "refuse to overwrite previous evidence"
    out.mkdir(parents=True)
    target = worktree / RELATIVE
    original = target.read_text()
    assert original == (ROOT / RELATIVE).read_text()
    command = [sys.executable, "-m", "pytest", str(worktree / "tests/programs/corpus/vlan_gateway/test_vlan_gateway.py"), "-q"]
    rows = []

    def run(name: str, fault: bool = False) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command + (["-k", "persistent_admissions"] if fault else []),
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=120,
        )
        (out / f"{name}.log").write_text(result.stdout + result.stderr)
        return result

    baseline = run("baseline")
    assert baseline.returncode == 0 and "3 passed" in baseline.stdout, baseline.stdout
    try:
        for name, old, new in FAULTS:
            assert original.count(old) == 1, name
            mutated = original.replace(old, new)
            target.write_text(mutated)
            (out / f"{name}.py").write_text(mutated)
            result = run(name, fault=True)
            assert result.returncode == 1 and "2 failed" in result.stdout, result.stdout
            assert len(re.findall(r"(?m)^E\s+AssertionError:", result.stdout)) == 2, result.stdout
            bundle = worktree / ".artifacts/drt/vlan-gateway.json"
            assert bundle.is_file(), "Lean test must retain the executed input"
            shutil.copyfile(bundle, out / f"{name}.json")
            rows.append({
                "fault": name,
                "source_sha256": hashlib.sha256(mutated.encode()).hexdigest(),
                "old": old,
                "new": new,
                "pytest_exit": result.returncode,
            })
            print(f"{name}: independent Python and real-Lean expectations both failed")
    finally:
        target.write_text(original)
    restored = run("restored")
    assert restored.returncode == 0 and "3 passed" in restored.stdout, restored.stdout
    assert target.read_text() == original
    (out / "manifest.json").write_text(json.dumps({
        "python": sys.executable,
        "test_command": command,
        "source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "faults": rows,
        "restored": True,
    }, indent=2) + "\n")
    print("Restored: all three gateway tests passed.")


if __name__ == "__main__":
    main()
