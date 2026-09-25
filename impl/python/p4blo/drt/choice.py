"""Named decisions: what a generated program is made of.

A program family (`families.py`, and the scalar expressions of
`programs.py`) makes every decision through a `Chooser`: `choice(point,
options)` picks one labelled option at a named decision point and records
it as a feature, `point=label`; `integer(point, lo, hi)` picks a number
and records nothing. Every option is typed by construction, so any
sequence of decisions is a well-typed program. The same family code runs
under three choosers:

- `RandomChooser`, uniform from one `random.Random`, so that a seed names a
  program exactly (fixed campaigns, P4-SpecTec's generated vectors);
- a Hypothesis chooser, in the tests, which draws each decision from the
  test's data, so that shrinking moves each choice toward its first option
  and each number toward its lower bound and a failing program shrinks to
  a smaller program of the same types;
- `guided.GuidedChooser`, which weights the options by the rule coverage a
  campaign has seen so far.

The first option of a decision is the simplest one.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Sequence

__all__ = ["Chooser", "RandomChooser"]


class Chooser(ABC):
    """Makes and records the decisions of one sample."""

    def __init__(self) -> None:
        self.features: set[str] = set()

    def choice(self, point: str, options: Sequence[str]) -> str:
        """One of `options` at the decision point `point`, recorded as a
        feature. The first option is the simplest; shrinking goes there."""
        if not options:
            raise ValueError(f"no options at {point}")
        label = options[0] if len(options) == 1 else self.pick(point, options)
        self.features.add(f"{point}={label}")
        return label

    def chance(self, point: str) -> bool:
        return self.choice(point, ("no", "yes")) == "yes"

    @abstractmethod
    def pick(self, point: str, options: Sequence[str]) -> str:
        """The labelled option; `choice` records it."""

    @abstractmethod
    def integer(self, point: str, lo: int, hi: int) -> int:
        """A number in `[lo, hi]`, not recorded as a feature."""


class RandomChooser(Chooser):
    """Uniform decisions from one `random.Random`."""

    def __init__(self, rng: random.Random) -> None:
        super().__init__()
        self.rng = rng

    def pick(self, point: str, options: Sequence[str]) -> str:
        return self.rng.choice(list(options))

    def integer(self, point: str, lo: int, hi: int) -> int:
        return self.rng.randint(lo, hi)
