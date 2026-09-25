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
      + NOVELTY_BONUS * (new tags and pairs per use, over its recent uses)

The first term steers toward the rules nobody has reached yet, as long as
they stay unhit; the second rewards the options that keep finding new
contexts for known rules, and fades as they stop doing so, because each
use's gain is averaged with a decay. Numbers (`integer`) are not weighted.
Everything is a function of the seed: sample `i` draws from
`random.Random(f"{seed}/{i}")`, and the guide changes only through the
replies, which are deterministic, so a seed names a campaign exactly.
`--unguided` draws the same way with uniform weights, as the baseline the
guidance is measured against.

    python -m p4blo.drt guided <family> <budget> [--seed N] [--profile lean|spectec]
        [--lean PATH | --fake] [--unguided] [--save DIR] [--show-pairs]

Every sample must agree; a disagreement is printed with the path of its
replay bundle (`python -m p4blo.drt.replay`), and the exit status is 1.
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from p4blo.drt.choice import Chooser
from p4blo.drt.coverage import RuleCoverage, rule_inventory
from p4blo.drt.families import FAMILIES, TARGETS, Profile, Sample
from p4blo.drt.replay import save as save_replay
from p4blo.drt.run import ProtocolError, Report, compare_program, default_lean_binary

__all__ = ["Guide", "GuidedChooser", "GuidedResult", "guided_campaign", "main"]

TARGET_BONUS = 4.0
NOVELTY_BONUS = 2.0
# How much of an option's past average gain survives each new use.
DECAY = 0.8
PORTS = 4


@dataclass
class Arm:
    """What choosing one option has yielded: a decayed average of the new
    tags and pairs per sample that took it."""

    uses: int = 0
    gain: float = 0.0

    def record(self, new: int) -> None:
        self.uses += 1
        self.gain = new if self.uses == 1 else DECAY * self.gain + (1 - DECAY) * new


@dataclass
class Guide:
    """The campaign's knowledge: tags and pairs hit, and per-option arms."""

    inventory: Mapping[str, str]
    targets: Mapping[str, Sequence[str]] = field(default_factory=lambda: TARGETS)
    tags: set[str] = field(default_factory=set)
    pairs: set[tuple[str, str]] = field(default_factory=set)
    arms: dict[str, Arm] = field(default_factory=dict)

    def weight(self, feature: str) -> float:
        weight = 1.0
        if any(t in self.inventory and t not in self.tags for t in self.targets.get(feature, ())):
            weight += TARGET_BONUS
        arm = self.arms.get(feature)
        if arm is not None and arm.uses:
            weight += NOVELTY_BONUS * min(arm.gain, 4.0) / 4.0
        return weight

    def observe(self, features: frozenset[str], tags: Sequence[str] | set[str]) -> tuple[int, int]:
        """Record one sample's tags; the number of new tags and new pairs."""
        new_tags = set(tags) - self.tags
        self.tags |= new_tags
        gains: dict[str, int] = {f: len(new_tags) for f in features}
        new_pairs = 0
        for tag in tags:
            for feature in features:
                pair = (tag, feature)
                if pair not in self.pairs:
                    self.pairs.add(pair)
                    gains[feature] += 1
                    new_pairs += 1
        for feature, gain in gains.items():
            self.arms.setdefault(feature, Arm()).record(gain)
        return len(new_tags), new_pairs


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


def main(argv: list[str] | None = None) -> int:
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
