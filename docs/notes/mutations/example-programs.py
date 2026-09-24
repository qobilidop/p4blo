"""Exercise selected application-source faults in an isolated worktree.

Run with the root project's Python environment, passing a disposable worktree
containing the same example source/tests and an existing Lean executable via
the installed p4blo package. No interpreter is rebuilt or modified here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAULTS = {
    "load_balancer": {
        "constant-bucket": (
            "self.assign(self.meta.bucket, self.meta.flow_hash.cast(p4.bit2))",
            "self.assign(self.meta.bucket, 0)",
        ),
        "source-port-omitted": (
            "p4.concat(ip.src, ip.dst, udp.src_port, udp.dst_port).as_(",
            "p4.concat(ip.src, ip.dst, udp.dst_port, udp.dst_port).as_(",
        ),
        "service-miss-uses-group-zero": (
            "with self.if_(self.meta.service_found):",
            "with self.if_(self.meta.ingress_port >= 0):",
        ),
        "stale-checksum": (
            "        self.assign(self.hdr.ipv4.checksum, checksum.compute(checksum_data(self.hdr.ipv4)))\n",
            "",
        ),
    },
    "firewall": {
        "tuple-mismatch-admitted": (
            "with self.if_(self.resident == self.record):",
            "with self.if_(self.resident != self.record):",
        ),
        "collision-evicts-resident": (
            "& (self.resident == 0)", "& (self.resident >= 0)",
        ),
        "policy-bypassed": (
            "with self.if_(self.meta.permitted):",
            "with self.if_(self.meta.ingress_port > 0):",
        ),
    },
    "router": {
        "ttl-wrap": ("& (ip.ttl > 1)", "& (ip.ttl >= 0)"),
        "stale-checksum": (
            "        self.assign(self.hdr.ipv4.checksum, checksum.compute(checksum_data(self.hdr.ipv4)))\n",
            "",
        ),
        "wrong-route-port": (
            "self.assign(self.meta.egress_port, port)",
            "self.assign(self.meta.egress_port, 0)",
        ),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", choices=FAULTS)
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    worktree = args.worktree.resolve()
    assert worktree != ROOT and (worktree / ".git").is_file(), "use an isolated git worktree"
    source = worktree / f"examples/{args.application}/program.py"
    original = source.read_text()
    artifacts = ROOT / f".artifacts/examples-mutations/{args.application}"
    artifacts.mkdir(parents=True, exist_ok=True)
    results = []

    def run(label: str, failure: bool) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", f"tests/examples/{args.application}",
             "-k", "independent", "-q"],
            cwd=worktree, text=True, capture_output=True, timeout=120,
        )
        output = result.stdout + result.stderr
        (artifacts / f"{label}.log").write_text(output)
        (artifacts / f"{label}.py").write_text(source.read_text())
        valid = (
            result.returncode == 1 and "2 failed" in output and "AssertionError" in output
            if failure else result.returncode == 0 and "2 passed" in output
        )
        results.append({"case": label, "exit": result.returncode, "expected_result": valid})
        assert valid, f"{label}: setup failure or unexpected result; inspect {artifacts}"

    try:
        run("baseline", False)
        for label, (before, after) in FAULTS[args.application].items():
            assert original.count(before) == 1, label
            source.write_text(original.replace(before, after))
            run(label, True)
        source.write_text(original)
        run("restored", False)
    finally:
        source.write_text(original)
        summary = {
            "application": args.application,
            "source_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "scope": "program faults executed under unchanged Python and Lean interpreters",
            "results": results,
        }
        (artifacts / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
