"""Coverage-guided generation: the semantics' rules drive the choices.

A guided campaign runs one program family (`p4blo.drt.families`) against
Lean for a budget of samples. After every sample it reads the rule tags the
Lean replies carried (`coverage`, `P4bloIR.Coverage`) and updates a `Guide`,
which the next sample's `GuidedChooser` consults at every labelled decision.
This is the loop of ESMeta's JESTfs for JavaScript, with p4blo's rule tags
in place of the specification's algorithm steps.

What is measured. The tags hit, and the (tag, feature) pairs hit, where a
feature is one labelled decision of the sample (`parser.stmt=advance`,
`select.key=enum`, `action.body=...`) and so names the construct that
encloses what was chosen. Pairing every tag of a run with every feature of
its program is the one-feature-sensitive criterion JESTfs found most
effective: a rule reached in a new context counts as new.

How choices are biased. A decision point's options are weighted, and an
option's weight is

    1 + TARGET_BONUS  if a tag the option aims at (`families.TARGETS`) is unhit

which steers toward the rules nobody has reached yet, as long as they stay
unhit; once every target is hit, choices are uniform. Numbers (`integer`)
are not weighted. Everything is a function of the seed: sample `i` draws
from `random.Random(f"{seed}/{i}")`, and the guide changes only through the
replies, which are deterministic, so a seed names a campaign exactly.
`--unguided` draws the same way with uniform weights, as the baseline the
guidance is measured against.

What it is worth. `tests/conformance/coverage/guided-measurement.json` records, for both
families over sixteen seeds of 200 programs, guided against uniform: the
programs until every target tag that all runs reach is hit, the program
of the last first-hit of any tag, and the tags and pairs reached. Its
`summary` is the evidence for any claim about the guidance, and
`python -m p4blo.drt guided measure` regenerates it. The pairs are
measured, not steered toward. An earlier weighting also added
`NOVELTY_BONUS * min(gain, 4) / 4` with `NOVELTY_BONUS` 2, where `gain` was
a decayed average (0.8) of the new tags and pairs per sample that took the
option. On 32 seeds it reached the targets later than the target term
alone, in both families, and did not reach more pairs, so it was removed.

    python -m p4blo.drt guided <family> <budget> [--seed N] [--profile lean|spectec]
        [--lean PATH | --fake] [--unguided] [--save DIR] [--show-pairs]
    python -m p4blo.drt guided measure [--seeds A:B] [--budget N] [--jobs N]
        [--lean PATH] [--out FILE]

Every sample must agree; a disagreement is printed with the path of its
replay bundle (`python -m p4blo.drt.replay`), and the exit status is 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from p4blo.drt.choice import Chooser
from p4blo.drt.coverage import RuleCoverage, rule_inventory
from p4blo.drt.families import FAMILIES, TARGETS, Profile, Sample
from p4blo.drt.replay import save as save_replay
from p4blo.drt.run import ProtocolError, Report, compare_program, default_lean_binary

__all__ = ["Guide", "GuidedChooser", "GuidedResult", "guided_campaign", "main", "measure"]

TARGET_BONUS = 4.0
PORTS = 4


@dataclass
class Guide:
    """The campaign's knowledge: the tags and the (tag, feature) pairs hit."""

    inventory: Mapping[str, str]
    targets: Mapping[str, Sequence[str]] = field(default_factory=lambda: TARGETS)
    tags: set[str] = field(default_factory=set)
    pairs: set[tuple[str, str]] = field(default_factory=set)

    def weight(self, feature: str) -> float:
        weight = 1.0
        if any(t in self.inventory and t not in self.tags for t in self.targets.get(feature, ())):
            weight += TARGET_BONUS
        return weight

    def observe(self, features: frozenset[str], tags: Sequence[str] | set[str]) -> tuple[int, int]:
        """Record one sample's tags; the number of new tags and new pairs."""
        new_tags = set(tags) - self.tags
        self.tags |= new_tags
        new_pairs = {(tag, feature) for tag in tags for feature in features} - self.pairs
        self.pairs |= new_pairs
        return len(new_tags), len(new_pairs)


class GuidedChooser(Chooser):
    """Decisions weighted by a `Guide`; `guide=None` draws uniformly."""

    def __init__(self, rng: random.Random, guide: Guide | None) -> None:
        super().__init__()
        self.rng = rng
        self.guide = guide

    def pick(self, point: str, options: Sequence[str]) -> str:
        if self.guide is None:
            return self.rng.choice(list(options))
        weights = [self.guide.weight(f"{point}={option}") for option in options]
        return self.rng.choices(list(options), weights)[0]

    def integer(self, point: str, lo: int, hi: int) -> int:
        return self.rng.randint(lo, hi)


@dataclass
class GuidedResult:
    family: str
    seed: int
    samples: int = 0
    requests: int = 0
    coverage: RuleCoverage = field(default_factory=RuleCoverage)
    guide: Guide | None = None
    # (sample number, tag) in the order the tags were first hit.
    first_hits: list[tuple[int, str]] = field(default_factory=list)
    failures: list[tuple[int, Report, Path | None]] = field(default_factory=list)

    def summary(self, inventory: Mapping[str, str]) -> str:
        assert self.guide is not None
        return (
            f"{self.family}: seed {self.seed}, {self.samples} programs, {self.requests} requests, "
            f"{len(self.failures)} disagreed; {len(self.guide.tags & set(inventory))} of "
            f"{len(inventory)} tags, {len(self.guide.pairs)} (tag, feature) pairs"
        )


def sample_rng(seed: int, number: int) -> random.Random:
    """The generator of sample `number` of the campaign named by `seed`."""
    return random.Random(f"{seed}/{number}")


def guided_campaign(
    family: str,
    lean: Sequence[str | Path],
    *,
    seed: int,
    budget: int,
    inventory: Mapping[str, str],
    profile: Profile = "lean",
    guided: bool = True,
    save: Path | None = None,
    progress: Callable[[int, Sample, int, int], None] | None = None,
) -> GuidedResult:
    """Run `budget` samples of `family` against `lean`, steering by coverage.

    A sample whose run disagrees, or whose peer breaks the protocol, is kept
    as a failure with its replay bundle under `save`; the campaign goes on.
    """
    make = FAMILIES[family]
    guide = Guide(inventory)
    result = GuidedResult(family, seed, guide=guide)
    for number in range(budget):
        chooser = GuidedChooser(sample_rng(seed, number), guide if guided else None)
        sample = make(chooser, profile)
        try:
            report = compare_program(sample.program, sample.cases, PORTS, lean, number)
        except ProtocolError as e:
            assert e.report is not None
            report = e.report
        result.samples += 1
        result.requests += report.cases
        result.coverage.update(report.rule_coverage)
        tags = set(report.rule_coverage.hits)
        for tag in sorted(tags - guide.tags):
            result.first_hits.append((number, tag))
        new_tags, new_pairs = guide.observe(sample.features, tags)
        if progress is not None:
            progress(number, sample, new_tags, new_pairs)
        if not report.passed:
            bundle = None
            if save is not None:
                save.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256(sample.program.SerializeToString()).hexdigest()[:12]
                bundle = save / f"guided-{family}-seed{seed}-{number}-{digest}.json"
                save_replay(report, bundle)
            result.failures.append((number, report, bundle))
    return result


# ---------------------------------------------------------------------------
# Measurement: guided against uniform
# ---------------------------------------------------------------------------

ARMS = {"guided": True, "uniform": False}
MEASURED_FAMILIES = ("control", "parser")


def measured_run(
    family: str, seed: int, arm: str, budget: int, lean: Sequence[str | Path]
) -> dict[str, Any]:
    """One campaign's row: the tags and pairs it reached, the program of its
    last first-hit, and the program at which each target tag was first hit."""
    inventory = rule_inventory(lean)
    result = guided_campaign(
        family, lean, seed=seed, budget=budget, inventory=inventory, guided=ARMS[arm]
    )
    assert result.guide is not None
    if result.failures:
        raise AssertionError(f"{family} seed {seed} {arm}: a program disagreed")
    targets = {t for tags in TARGETS.values() for t in tags} & set(inventory)
    first = {tag: number for number, tag in result.first_hits}
    return {
        "family": family,
        "seed": seed,
        "arm": arm,
        "tags": len(result.guide.tags & set(inventory)),
        "pairs": len(result.guide.pairs),
        "last_new_tag": max(first.values(), default=None),
        "target_first_hits": {t: first[t] for t in sorted(targets) if t in first},
    }


def _measured_run(args: tuple[str, int, str, int, Sequence[str | Path]]) -> dict[str, Any]:
    return measured_run(*args)


def summarize(runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Per family and arm, from the rows alone. The common targets are the
    target tags every run of the family hit, guided or not; `to_targets` is
    the program at which a run has hit them all, so every run is timed on
    the same set."""
    summary: dict[str, Any] = {}
    for family in sorted({r["family"] for r in runs}):
        rows = [r for r in runs if r["family"] == family]
        common = set.intersection(*(set(r["target_first_hits"]) for r in rows))
        arms: dict[str, Any] = {}
        for arm in ARMS:
            mine = sorted((r for r in rows if r["arm"] == arm), key=lambda r: r["seed"])
            if not mine:
                continue
            columns = {
                "to_targets": [max(r["target_first_hits"][t] for t in common) for r in mine],
                "last_new_tag": [r["last_new_tag"] for r in mine],
                "tags": [r["tags"] for r in mine],
                "pairs": [r["pairs"] for r in mine],
            }
            arms[arm] = {
                name: {
                    "mean": round(statistics.mean(values), 1),
                    "median": statistics.median(values),
                    "per_seed": values,
                }
                for name, values in columns.items()
            }
        summary[family] = {"common_targets": len(common), "arms": arms}
    return summary


def measure(
    lean: Sequence[str | Path],
    *,
    seeds: Sequence[int],
    budget: int,
    families: Sequence[str] = MEASURED_FAMILIES,
    jobs: int = 1,
) -> dict[str, Any]:
    """Guided and uniform campaigns of every family and seed, as the
    document `tests/conformance/coverage/guided-measurement.json` holds."""
    work = [(f, s, arm, budget, lean) for f in families for s in seeds for arm in ARMS]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as pool:
            runs = list(pool.map(_measured_run, work))
    else:
        runs = [_measured_run(w) for w in work]
    return {
        "command": "python -m p4blo.drt guided measure",
        "budget": budget,
        "seeds": list(seeds),
        "target_bonus": TARGET_BONUS,
        "summary": summarize(runs),
        "runs": runs,
    }


def render(document: Mapping[str, Any]) -> str:
    return json.dumps(document, indent=1, sort_keys=True) + "\n"


def measure_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m p4blo.drt guided measure",
        description=(
            "guided against uniform campaigns, as "
            "tests/conformance/coverage/guided-measurement.json"
        ),
    )
    parser.add_argument("--seeds", default="1:17", help="`A:B`, half-open")
    parser.add_argument("--budget", type=int, default=200)
    parser.add_argument("--jobs", type=int, default=1, help="campaigns run at once")
    parser.add_argument("--lean", type=Path, default=None, help="the p4blo-lean executable")
    parser.add_argument("--out", type=Path, default=None, help="write the document here")
    args = parser.parse_args(argv)
    start, stop = (int(x) for x in args.seeds.split(":", 1))
    lean = [args.lean or default_lean_binary()]
    document = measure(lean, seeds=range(start, stop), budget=args.budget, jobs=args.jobs)
    text = render(document)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(json.dumps(document["summary"], indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["measure"]:
        return measure_main(argv[1:])
    parser = argparse.ArgumentParser(
        prog="python -m p4blo.drt guided",
        description="run a program family against Lean, steered by the rule tags it hits",
    )
    parser.add_argument("family", choices=sorted(FAMILIES))
    parser.add_argument("budget", type=int, help="number of programs")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--profile", choices=["lean", "spectec"], default="lean")
    parser.add_argument("--lean", type=Path, default=None, help="the p4blo-lean executable")
    parser.add_argument(
        "--fake", action="store_true", help="run Python against itself (no tags, no guidance)"
    )
    parser.add_argument("--unguided", action="store_true", help="uniform choices, the baseline")
    parser.add_argument("--save", type=Path, default=None, help="write replay bundles here")
    parser.add_argument(
        "--show-pairs", action="store_true", help="print how many pairs each feature reached"
    )
    args = parser.parse_args(argv)

    if args.fake:
        lean: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]
    else:
        lean = [args.lean or default_lean_binary()]
    inventory = rule_inventory(lean)

    def progress(number: int, sample: Sample, new_tags: int, new_pairs: int) -> None:
        if new_tags:
            print(f"  program {number}: {new_tags} new tags, {new_pairs} new pairs")

    result = guided_campaign(
        args.family,
        lean,
        seed=args.seed,
        budget=args.budget,
        inventory=inventory,
        profile=args.profile,
        guided=not args.unguided,
        save=args.save,
        progress=progress,
    )
    print(result.summary(inventory))
    for number, tag in result.first_hits:
        print(f"  first hit at program {number}: {tag}")
    unhit = result.coverage.unhit(inventory)
    print(f"  {len(unhit)} tags unhit by this campaign")
    if args.show_pairs and result.guide is not None:
        per_feature: dict[str, int] = {}
        for _tag, feature in result.guide.pairs:
            per_feature[feature] = per_feature.get(feature, 0) + 1
        for feature, count in sorted(per_feature.items(), key=lambda kv: -kv[1]):
            print(f"  {count:5} pairs  {feature}")
    for number, report, bundle in result.failures:
        where = f"; replay {bundle}" if bundle is not None else ""
        print(f"DISAGREEMENT at program {number}: {report.summary()}{where}")
        for d in report.divergences[:3]:
            print("  " + d.describe().replace("\n", "\n  "))
        if report.protocol_error:
            print(f"  protocol error: {report.protocol_error}")
    return 1 if result.failures else 0
