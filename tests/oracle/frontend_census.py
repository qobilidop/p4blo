"""The IL bridge's census: every v1model program of p4c's samples, from source.

A local tool, not a test and not run in CI. It takes every program of
p4c's `testdata/p4_16_samples/` that includes `v1model.p4` and has an STF
vector beside it, at the p4c commit P4-SpecTec's pin records as its `p4c`
submodule (the one tests/frontend/catalog.py pins), exports it with
P4-SpecTec's `il-export`, translates it with `p4blo.frontend`, and replays
p4c's own vector on the Python interpreter as
`tests/frontend/p4c_stf.replay` does. Each program gets one outcome:

    pass             translated, and the vector passes
    fail             translated, and the vector fails
    replay-error     translated, but the STF adapter cannot replay the vector
    excluded         refused by a coverage row (docs/p4-spec-coverage.md)
    not-translated   an IL production the bridge does not attempt
    invalid          the translation does not validate (a bridge defect)
    crash            anything else raised (a bridge defect)
    spectec-rejects  P4-SpecTec's typing or instantiation refuses the source

The result, `frontend-census.json` beside this file, is sorted and carries
no paths or timings, so a rerun on the same pins reproduces it byte for
byte; `--check` reruns and fails on any difference, which is how the
numbers quoted elsewhere stay tied to a command.

    uv run python tests/oracle/frontend_census.py            # rewrite the result
    uv run python tests/oracle/frontend_census.py --check    # compare with it

The oracle is found as tests/oracle/run.py finds it (`$P4BLO_ORACLE_BIN`,
`$P4BLO_ORACLE_DIR`, the default directory) and must have `il-export`. The
samples are fetched once, sparsely, into `~/.cache/p4blo/p4c-census`, or
read from `--p4c DIR`, a p4c checkout at the pinned commit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "impl" / "python"))
sys.path.insert(0, str(ROOT))

from p4blo.frontend import Excluded, FrontendError, NotTranslated, translate  # noqa: E402
from p4blo.frontend.export import Exporter, ExportError, find_exporter  # noqa: E402
from tests.frontend import catalog, p4c_stf  # noqa: E402

RESULT = Path(__file__).resolve().parent / "frontend-census.json"
P4C_REPO = "https://github.com/p4lang/p4c"
SAMPLES = "testdata/p4_16_samples"
DEFAULT_P4C_DIR = Path.home() / ".cache" / "p4blo" / "p4c-census"
FORMAT = "p4blo-frontend-census/1"


def fetch_samples(p4c: Path) -> Path:
    """The samples directory of a p4c checkout at the pinned commit, fetching
    only that directory into `p4c` if it is not there yet."""
    commit = catalog.P4C_COMMIT
    head = subprocess.run(
        ["git", "-C", str(p4c), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    if head != commit or not (p4c / SAMPLES).is_dir():
        p4c.mkdir(parents=True, exist_ok=True)
        git = ["git", "-C", str(p4c)]
        if not (p4c / ".git").exists():
            subprocess.run([*git, "init", "-q"], check=True)
            subprocess.run([*git, "remote", "add", "origin", P4C_REPO], check=True)
        subprocess.run([*git, "sparse-checkout", "set", SAMPLES], check=True)
        subprocess.run(
            [*git, "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", commit],
            check=True,
        )
        subprocess.run([*git, "checkout", "-q", "--detach", commit], check=True)
    return p4c / SAMPLES


def programs(samples: Path) -> list[Path]:
    """The v1model programs with a vector, by name. A few samples are links
    into other backends' test directories, which the sparse fetch leaves
    dangling; none of them is a v1model program."""
    return sorted(
        p
        for p in samples.glob("*.p4")
        if p.is_file()
        and p.with_suffix(".stf").is_file()
        and "v1model.p4" in p.read_text(errors="replace")
    )


def outcome(exporter: Exporter, source: Path) -> dict[str, str]:
    """One program's outcome and the reason, without paths."""
    name = source.stem

    def result(kind: str, detail: str = "") -> dict[str, str]:
        return {"program": name, "outcome": kind, "detail": detail}

    try:
        export = exporter.export(source)
    except ExportError:
        return result("spectec-rejects")
    try:
        program = translate(export, name).program
    except Excluded as e:
        return result("excluded", e.row)
    except NotTranslated as e:
        return result("not-translated", f"{e.production}: {e.detail}")
    except FrontendError as e:
        return result("invalid", str(e).splitlines()[0])
    except Exception as e:  # noqa: BLE001 - a crash is an outcome here
        return result("crash", f"{type(e).__name__}: {e}")
    try:
        problems = p4c_stf.replay(program, source.with_suffix(".stf").read_text())
    except Exception as e:  # noqa: BLE001 - so is an adapter limit
        return result("replay-error", f"{type(e).__name__}: {e}")
    return result("fail", problems[0]) if problems else result("pass")


def census(exporter: Exporter, samples: Path, jobs: int) -> dict[str, object]:
    sources = programs(samples)
    with ThreadPoolExecutor(jobs) as pool:
        results = list(pool.map(lambda p: outcome(exporter, p), sources))
    stamp = exporter.root / ".p4blo-built"
    spectec = stamp.read_text().split()[0] if stamp.is_file() else ""
    counts = Counter(r["outcome"] for r in results)
    rows = Counter(r["detail"] for r in results if r["outcome"] == "excluded")
    return {
        "format": FORMAT,
        "p4c_commit": catalog.P4C_COMMIT,
        "p4_spectec_commit": spectec,
        "programs_total": len(results),
        "outcomes": dict(sorted(counts.items())),
        "excluded_by_row": dict(sorted(rows.items(), key=lambda kv: (-kv[1], kv[0]))),
        "programs": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The IL bridge's census of p4c's samples.")
    parser.add_argument("--check", action="store_true", help="compare with the tracked result")
    parser.add_argument("--p4c", type=Path, default=DEFAULT_P4C_DIR, help="p4c checkout")
    parser.add_argument("--jobs", type=int, default=6, help="programs exported at once")
    args = parser.parse_args(argv)
    exporter = find_exporter()
    if exporter is None or exporter.missing() is not None:
        why = "no oracle" if exporter is None else exporter.missing()
        print(f"frontend_census: {why}; run tests/oracle/build.sh", file=sys.stderr)
        return 2
    text = json.dumps(census(exporter, fetch_samples(args.p4c), args.jobs), indent=1) + "\n"
    if args.check:
        if RESULT.read_text() != text:
            print(f"frontend_census: the result differs from {RESULT.name}", file=sys.stderr)
            return 1
        return 0
    RESULT.write_text(text)
    print(json.dumps(json.loads(text)["outcomes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
