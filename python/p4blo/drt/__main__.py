"""`python -m p4blo.drt <program dir> <count> [--seed N] [--ports N]
[--lean PATH | --fake] [--show N] [--save DIR]`

Prints the summary and STF excerpts of the first divergences. `--save`
writes a self-contained JSON replay of the program and full input sequence,
plus the excerpts. Stateful failures require that JSON bundle; the single
packet excerpts omit prior extern state. Exit status 1 on divergence or
unexpected shared errors, 2 on a protocol error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from p4blo import ir
from p4blo.drt.case import Outputs, case_to_stf
from p4blo.drt.replay import save as save_replay
from p4blo.drt.run import Outcome, ProtocolError, Report, compare, default_lean_binary


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
        if e.report is not None:
            show(e.report, args.program_dir, args.show, args.save)
        return 2
    print(report.summary())
    show(report, args.program_dir, args.show, args.save)
    return 0 if report.passed else 1


def comment(outcome: Outcome) -> Outputs | str:
    """An outcome as `case_to_stf` comments it: an error or a drop with a
    diagnostic as text, otherwise the outputs as `expect` lines."""
    if outcome.error is not None or outcome.diagnostic is not None:
        return str(outcome)
    return outcome.outputs or ()


def show(report: Report, program_dir: Path, limit: int, save: Path | None) -> None:
    if save is not None and not report.passed:
        save.mkdir(parents=True, exist_ok=True)
        bundle = save / f"drt_{report.program}_seed{report.seed}.json"
        save_replay(report, bundle)
        print(f"# complete stateful replay: python -m p4blo.drt.replay {bundle}")
    if not report.divergences:
        return
    index = ir.Index.build(ir.load_text(program_dir / f"{program_dir.name}.txtpb"))
    for d in report.divergences[:limit]:
        comments = {"python": comment(d.python), "lean": comment(d.lean)}
        header = (
            f"# {report.program}: divergence on case {d.number} of seed {report.seed}, "
            f"found by python -m p4blo.drt\n"
        )
        header += "# " + d.describe().replace("\n", "\n# ") + "\n"
        try:
            text = header + "# Single-case excerpt; replay the JSON bundle for prior state.\n"
            text += case_to_stf(index, d.case, comments=comments)
        except ValueError as e:
            print(f"# case {d.number} cannot be represented in STF: {e}")
            continue
        print()
        print(text, end="")
        if save is not None:
            save.mkdir(parents=True, exist_ok=True)
            path = save / f"drt_{report.program}_seed{report.seed}_case{d.number}.stf"
            path.write_text(text)
            print(f"# written to {path}")


if __name__ == "__main__":
    sys.exit(main())
