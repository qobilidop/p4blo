"""The P4 sources the IL bridge is checked on, pinned.

Every file under tests/frontend/ is a verbatim copy, checked here by
SHA-256 so that an edit cannot pass unnoticed:

- `p4c/`: p4lang/p4c at the commit P4-SpecTec's pin records as its `p4c`
  submodule, `testdata/p4_16_samples/`: the original sources of corpus
  programs (each corpus README names its source).
- `tutorials/basic.p4`: p4lang/tutorials at the commit the tutorial
  firewall is pinned to, `exercises/basic/solution/basic.p4`, the
  forwarder's source. The firewall's own source is tests/oracle/firewall.p4.

Both repositories are Apache-2.0; the files keep their SPDX headers where
upstream has them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

P4C_COMMIT = "6b7ec98e77dfc71c6e1309d9a76183cb31f35a8a"
TUTORIALS_COMMIT = "098ce0b7ae486f5b747a6b53ad1585f0d977b42e"

SHA256: dict[str, str] = {
    "p4c/header-stack-ops-bmv2.p4": (
        "0726eaf919627ae3ee133b4774ea036f4068085eebec72e69731c9c680981761"
    ),
    "p4c/issue1097-2-bmv2.p4": "c6b8d9237ef2a399c6f8ed9a54456a573332bc4f4fc8ac706dd56789186eb14d",
    "p4c/issue1824-bmv2.p4": "64cab42e025c25491c1a529173468e869f819d87594313465cf119e8d2c3a813",
    "p4c/issue655-bmv2.p4": "fbc11945e3798a2162ba5c94621fb8b873abe284417dbb56cbe222ce38203315",
    "p4c/parser_error-bmv2.p4": "3d3a7195bcbbd27d7112711c294763cdd6e2ed2b7e0d8a46ae0dfb209cf3e841",
    "p4c/subparser-with-header-stack-bmv2.p4": (
        "05078717dfd7bb9b125b2eebfb095dd91b2702dc828c9fffb112ead565548a7f"
    ),
    "p4c/table-entries-priority-bmv2.p4": (
        "29ab2e2e00b4a173804f66290072f6d042b466fa1626f4e3b4b403d511967706"
    ),
    "p4c/ternary2-bmv2.p4": "e23876480d775934165c6a2a81f11ab39937dd89eb638b1a128dd5c733e0d1ce",
    "tutorials/basic.p4": "f7294f2e4872c3c4f43161bd1a9a62e921d7b8a34cda274218ae862df5e3c834",
}


@dataclass(frozen=True)
class CorpusSource:
    """A corpus program's original source and how its translation compares
    with the golden written in the eDSL.

    `status` is one of:
      - "identical": the translation's text format is the golden's, byte
        for byte;
      - "normalized": equal once `p4blo.frontend.normalize` has put both in
        canonical form (declaration order, block-local names);
      - "documented": equal once the golden is adjusted by the differences
        its README or the bridge documents, which
        tests/test_frontend_spectec.py spells out one by one.
    """

    program: str
    source: Path
    status: str


CORPUS: tuple[CorpusSource, ...] = (
    CorpusSource("acl", HERE / "p4c/ternary2-bmv2.p4", "documented"),
    CorpusSource("csum16", HERE / "p4c/issue655-bmv2.p4", "identical"),
    CorpusSource("forwarder", HERE / "tutorials/basic.p4", "documented"),
    CorpusSource("parser_error", HERE / "p4c/parser_error-bmv2.p4", "identical"),
    CorpusSource("priority", HERE / "p4c/table-entries-priority-bmv2.p4", "documented"),
    CorpusSource("stacks", HERE / "p4c/header-stack-ops-bmv2.p4", "identical"),
    CorpusSource("stateful", HERE / "p4c/issue1097-2-bmv2.p4", "documented"),
    CorpusSource("subparser_stack", HERE / "p4c/subparser-with-header-stack-bmv2.p4", "identical"),
    CorpusSource("tutorial_firewall", ROOT / "tests/oracle/firewall.p4", "normalized"),
    CorpusSource("verify_error", HERE / "p4c/issue1824-bmv2.p4", "identical"),
)

# Corpus programs authored in the eDSL with no P4 original; they are
# checked through the printer instead (print, translate, compare).
NO_SOURCE: tuple[str, ...] = ("register_bounds", "vlan_gateway")
