"""Real Lean execution conformance."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from p4blo.arch import validator
from p4blo.arch import wire as arch_wire
from p4blo.drt.case import Case
from p4blo.drt.coverage import rule_inventory
from p4blo.drt.run import compare_program
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt_coverage import (
    CAMPAIGN_PARTS,
    CORPUS,
    PARTS_DIR,
    PORTS,
    UNHIT,
    WITNESSES,
    Campaign,
    ledger_entry_names,
    run_part,
    witness_generator,
)


@pytest.mark.parametrize("part", CAMPAIGN_PARTS)
def test_lean_agrees_on_campaign_part(lean_binary: Path, part: str) -> None:
    """One part of the retained campaigns agrees with Lean and hits exactly
    the rule tags recorded for it in tests/conformance/coverage/parts/. Parts are
    separate tests so the parallel runner can spread them; the union check
    below joins the recorded sets. `P4BLO_UPDATE_COVERAGE_PARTS=1` rewrites
    a part's record instead of comparing, for a deliberate generator change."""
    inventory = rule_inventory([lean_binary])
    campaign = Campaign([lean_binary])
    run_part(campaign, part)
    assert campaign.failures == []
    assert campaign.coverage.unreported == 0, "every Lean reply must carry its coverage"
    assert campaign.coverage.unknown(inventory) == []
    hits = sorted(campaign.coverage.hits)
    record = PARTS_DIR / (part.replace(":", "-") + ".json")
    if os.environ.get("P4BLO_UPDATE_COVERAGE_PARTS") == "1":
        record.write_text(json.dumps({"part": part, "hits": hits}, indent=1) + "\n")
    recorded = json.loads(record.read_text(encoding="utf-8"))
    assert recorded["part"] == part
    assert hits == recorded["hits"], (
        f"{part} hits changed; if the generators changed on purpose, rerun with "
        "P4BLO_UPDATE_COVERAGE_PARTS=1 and review the diff"
    )


def test_lean_agrees_that_every_rule_tag_is_hit(lean_binary: Path) -> None:
    """The union of the recorded parts covers the inventory, except the tags
    tests/conformance/coverage/unhit-tags.json lists; a tag that stops being hit is a
    regression, a listed tag that is hit is stale, and the list may only
    shrink. The parts' own tests keep the records honest."""
    inventory = rule_inventory([lean_binary])
    records = {r.stem: json.loads(r.read_text(encoding="utf-8")) for r in PARTS_DIR.glob("*.json")}
    expected = {part.replace(":", "-") for part in CAMPAIGN_PARTS}
    assert set(records) == expected, f"records and parts differ: {set(records) ^ expected}"
    hit = set().union(*(set(r["hits"]) for r in records.values()))
    unhit = set(inventory) - hit
    known: dict[str, str] = json.loads(UNHIT.read_text(encoding="utf-8"))["unhit"]
    assert set(known) <= set(inventory), (
        f"unknown tags listed as unhit: {set(known) - set(inventory)}"
    )
    regressions = sorted(unhit - set(known))
    stale = sorted(set(known) - unhit)
    assert regressions == [], (
        f"{len(regressions)} rule tags stopped being hit by the retained campaigns:\n"
        + "\n".join(f"  {tag}: {inventory[tag]}" for tag in regressions)
    )
    assert stale == [], (
        "tags listed in tests/conformance/coverage/unhit-tags.json are now hit; remove them:\n"
        + "\n".join(f"  {tag}" for tag in stale)
    )
    # Not implied by the two checks above: a newly unhit tag added to the
    # file is neither a regression nor stale. The list is empty and may
    # only stay so.
    assert known == {}, "tests/conformance/coverage/unhit-tags.json grew; it may only shrink"


def test_the_unhit_list_names_reasons() -> None:
    document = json.loads(UNHIT.read_text(encoding="utf-8"))
    for tag, reason in document["unhit"].items():
        assert "." in tag and reason.strip(), tag


def test_lean_agrees_that_the_inventory_is_well_formed(lean_binary: Path) -> None:
    inventory = rule_inventory([lean_binary])
    assert len(inventory) > 100
    for tag, doc in inventory.items():
        assert tag == tag.strip() and "." in tag and " " not in tag, tag
        assert doc and "\n" not in doc, tag
    assert "parser.extract.tooShort" in inventory


def test_lean_agrees_that_tag_citations_name_ledger_entries(lean_binary: Path) -> None:
    """A tag docstring that cites the ledger names one of its entries."""
    names = ledger_entry_names()
    assert "Header equality" in names and "`pop_front(n)`" in names
    cited = {tag: doc for tag, doc in rule_inventory([lean_binary]).items() if "ledger:" in doc}
    assert len(cited) > 80
    for tag, doc in cited.items():
        match = re.match(r"ledger: (.+?)\.(?: |$)", doc)
        assert match is not None, f"{tag}: the citation must open the docstring: {doc}"
        assert match[1] in names, f"{tag} cites no ledger entry: {match[1]!r}"


def test_lean_agrees_that_every_reply_carries_coverage(lean_binary: Path) -> None:
    """A truncated packet reports the too-short extract; an install error and
    a malformed request still carry a list."""
    program = arch_wire.load_text(CORPUS / "forwarder" / "forwarder.txtpb")
    bad = pb.Entries()
    entry = bad.tables.add(block="MyIngress", table="ipv4_lpm").entries.add()
    entry.keys.add(lpm=pb.LpmValue(value="1", prefix_len=40))
    entry.action.action = "drop"
    cases = [Case(pb.Entries(), 0, b"\x00\x00"), Case(bad, 0, bytes(34))]
    report = compare_program(program, cases, PORTS, [lean_binary])
    assert report.divergences == [], report.summary()
    assert report.rule_coverage.unreported == 0
    assert report.rule_coverage.reported == 2
    assert report.rule_coverage.hits["parser.extract.tooShort"] == 1


def test_coverage_witness_programs_are_valid_and_current() -> None:
    """Every program of the Lean witness table passes the validator, and the
    committed table is what its generator produces, replies included: the
    replies are the Python reference interpreter's, and the Lean test
    requires Lean to give the same ones."""
    generator = witness_generator()
    table = json.loads(WITNESSES.with_suffix(".json").read_text(encoding="utf-8"))
    assert len(table["programs"]) > 50 and len(table["cases"]) > 100
    for program_json in table["programs"]:
        program = arch_wire.load_json(json.dumps(program_json))
        assert validator.validate(program) == [], program.name
    assert WITNESSES.with_suffix(".json").read_text(encoding="utf-8") == generator.render(), (
        "witnesses.json is stale; regenerate it with its generator"
    )
