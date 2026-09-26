"""Package checks without native oracle dependencies."""

from __future__ import annotations

from p4blo.drt.coverage import RuleCoverage, rule_inventory
from p4blo.drt.run import compare, parse_reply
from tests.support.drt_coverage import CORPUS, FAKE, PORTS


def test_the_fake_reports_no_rule_tags() -> None:
    """The Python stand-in has no rule tags and does not pretend to."""
    assert rule_inventory(FAKE) == {}
    report = compare(CORPUS / "forwarder", 7, 5, PORTS, FAKE)
    assert report.rule_coverage.reported == 5
    assert report.rule_coverage.hits == {}


def test_an_older_peer_without_coverage_is_counted_not_refused() -> None:
    outcome = parse_reply('{"outputs": [], "state": {}}')
    assert outcome.coverage is None
    coverage = RuleCoverage()
    coverage.add(outcome.coverage)
    coverage.add(parse_reply('{"outputs": [], "state": {}, "coverage": ["a.b"]}').coverage)
    assert (coverage.reported, coverage.unreported) == (1, 1)
    assert coverage.unhit(["a.b", "c.d"]) == ["c.d"]
    assert coverage.unknown(["c.d"]) == ["a.b"]
    assert "1 replies carried no coverage" in coverage.describe({"a.b": "x", "c.d": "y"})
