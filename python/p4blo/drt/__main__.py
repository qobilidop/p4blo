"""`python -m p4blo.drt <program dir> <count> [--seed N] [--ports N]
[--lean PATH | --fake] [--show N] [--save DIR]`

Prints the report's summary and the first divergences, each as the STF
vector that replays it with both sides' outputs as comments. `--save`
also writes each of those vectors to a file, named by program, seed and
case number, so it can be dropped under `corpus/<program>/` once the
divergence is attributed. Exit status 1 when anything diverged, 2 on a
protocol error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from p4blo import ir
from p4blo.drt.case import case_to_stf
from p4blo.drt.run import ProtocolError, Report, compare, default_lean_binary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m p4blo.drt", description=__doc__)
    parser.add_argument("program_dir", type=Path, help="a corpus program directory")
    parser.add_argument("count", type=int, help="number of cases")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ports", type=int, default=4)
    parser.add_argument("--lean", type=Path, default=None, help="the p4blo-lean executable")
    parser.add_argument(
        "--fake", action="store_true", help="run Python against itself through the pipe"
    )
    parser.add_argument("--show", type=int, default=3, help="divergences to print")
    parser.add_argument("--save", type=Path, default=None, help="write shown divergences here")
    args = parser.parse_args(argv)

    if args.fake:
        lean: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]
    else:
        lean = [args.lean or default_lean_binary()]
    try:
        report = compare(args.program_dir, args.seed, args.count, args.ports, lean)
    except ProtocolError as e:
        print(f"protocol error: {e}", file=sys.stderr)
        return 2
    print(report.summary())
    show(report, args.program_dir, args.show, args.save)
    return 1 if report.divergences else 0


def show(report: Report, program_dir: Path, limit: int, save: Path | None) -> None:
    if not report.divergences:
        return
    index = ir.Index.build(ir.load_text(program_dir / f"{program_dir.name}.txtpb"))
    for d in report.divergences[:limit]:
        comments = {
            "python": d.python.error if d.python.error is not None else (d.python.outputs or ()),
            "lean": d.lean.error if d.lean.error is not None else (d.lean.outputs or ()),
        }
        header = (
            f"# {report.program}: divergence on case {d.number} of seed {report.seed}, "
            f"found by python -m p4blo.drt\n"
        )
        text = header + case_to_stf(index, d.case, comments=comments)
        print()
        print(text, end="")
        if save is not None:
            save.mkdir(parents=True, exist_ok=True)
            path = save / f"drt_{report.program}_seed{report.seed}_case{d.number}.stf"
            path.write_text(text)
            print(f"# written to {path}")


if __name__ == "__main__":
    sys.exit(main())
