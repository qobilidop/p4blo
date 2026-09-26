"""The P4 sources the IL bridge is checked on, pinned.

Every file under tests/frontend/ but `probes/` is a verbatim copy, checked
here by SHA-256 so that an edit cannot pass unnoticed:

- `p4c/`: p4lang/p4c at the commit P4-SpecTec's pin records as its `p4c`
  submodule, `testdata/p4_16_samples/`. The first eight are the original
  sources of corpus programs (each corpus README names its source); the
  last five are programs the corpus does not include, with p4c's own STF
  vectors, which BMv2 produced and p4c's maintainers review.
- `tutorials/basic.p4`: p4lang/tutorials at the commit the tutorial
  firewall is pinned to, `exercises/basic/solution/basic.p4`, the
  forwarder's source. The firewall's own source is tests/oracle/firewall.p4.

Both repositories are Apache-2.0; the files keep their SPDX headers where
upstream has them.

`probes/` holds small programs written here, each naming what it probes,
with vectors whose expectations are P4-SpecTec's output
(tests/external/test_frontend_spectec.py, section 5).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

P4C_COMMIT = "6b7ec98e77dfc71c6e1309d9a76183cb31f35a8a"
TUTORIALS_COMMIT = "098ce0b7ae486f5b747a6b53ad1585f0d977b42e"

SHA256: dict[str, str] = {
    "p4c/gauntlet_side_effects_in_mux-bmv2.p4": (
        "9f5a23b87533f8338b493c7f5314a17cd98f7022a317f884422316c05640b028"
    ),
    "p4c/gauntlet_side_effects_in_mux-bmv2.stf": (
        "ebab172375706294ab878b14a4f82d30d732b9658651f66984c12b141a8059a7"
    ),
    "p4c/header-stack-ops-bmv2.p4": (
        "0726eaf919627ae3ee133b4774ea036f4068085eebec72e69731c9c680981761"
    ),
    "p4c/issue-2123-3-bmv2.p4": "827a62b98d65af48e5241ddc9ceb449e8d983f7c44261501732adea05768371b",
    "p4c/issue-2123-3-bmv2.stf": "4ad0979823cb50bc439421144d2e52c2626c41b14b35eec9f646cc351d4d6f24",
    "p4c/issue1000-bmv2.p4": "9fc0a85147177c863de37fff50cd889278ed288a68bef6e34eebc9ce5562f6c4",
    "p4c/issue1000-bmv2.stf": "b9b0b083c89db738f34d52dc3e9a974e46a670147049b2314dcbcbe66edffc37",
    "p4c/issue1097-2-bmv2.p4": "c6b8d9237ef2a399c6f8ed9a54456a573332bc4f4fc8ac706dd56789186eb14d",
    "p4c/issue1824-bmv2.p4": "64cab42e025c25491c1a529173468e869f819d87594313465cf119e8d2c3a813",
    "p4c/issue3488-1-bmv2.p4": "4cec7c4f2276b5d16c0334311a6f6acbbf8a8ea3c24726cce3b07e2466a49893",
    "p4c/issue3488-1-bmv2.stf": "a1e029d7d0df1b14baf47462e9971c779b679a51ac8639bc281a2aab3df49259",
    "p4c/issue655-bmv2.p4": "fbc11945e3798a2162ba5c94621fb8b873abe284417dbb56cbe222ce38203315",
    "p4c/issue995-bmv2.p4": "c5275836d6bffd0232a690dfdeb9f619019b20e9ab01a3e52f92de2f44bedfe6",
    "p4c/issue995-bmv2.stf": "0ffafd44cb7c249f41e33ad860d3da691bd92274ca822a1cd2bceddf350d022b",
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
      - "projected": normalized equality after removing only empty optional
        stages and making explicitly checked source/golden adjustments.
        The checksum and stateful goldens are split at their known original
        stage boundaries; imported stages are never merged.
      - "excluded": the unchanged source requires an unsupported v1model
        facility, tested by its specific exclusion rather than packet replay.
    """

    program: str
    source: Path
    status: str


CORPUS: tuple[CorpusSource, ...] = (
    CorpusSource("acl", HERE / "p4c/ternary2-bmv2.p4", "projected"),
    CorpusSource("csum16", HERE / "p4c/issue655-bmv2.p4", "excluded"),
    CorpusSource("forwarder", HERE / "tutorials/basic.p4", "projected"),
    CorpusSource("parser_error", HERE / "p4c/parser_error-bmv2.p4", "projected"),
    CorpusSource("priority", HERE / "p4c/table-entries-priority-bmv2.p4", "projected"),
    CorpusSource("stacks", HERE / "p4c/header-stack-ops-bmv2.p4", "projected"),
    CorpusSource("stateful", HERE / "p4c/issue1097-2-bmv2.p4", "projected"),
    CorpusSource("subparser_stack", HERE / "p4c/subparser-with-header-stack-bmv2.p4", "projected"),
    CorpusSource("tutorial_firewall", ROOT / "tests/oracle/firewall.p4", "projected"),
    CorpusSource("verify_error", HERE / "p4c/issue1824-bmv2.p4", "projected"),
)

# Corpus programs authored in the eDSL with no P4 original; they are
# checked through the printer instead (print, translate, compare).
NO_SOURCE: tuple[str, ...] = ("register_bounds", "vlan_gateway")

# p4c programs the corpus does not include, run from source on the Python
# interpreter against p4c's own vectors. Chosen for what they exercise:
NEW_PROGRAMS: dict[str, str] = {
    "gauntlet_side_effects_in_mux-bmv2": "a function call in each branch of `?:`",
    "issue-2123-3-bmv2": "slice assignments from `?:`, a two-key select on a slice",
    "issue1000-bmv2": "a three-key select on slices, sixteen vectors",
    "issue3488-1-bmv2": "`switch` on action_run, a serializable enum, const default actions",
    "issue995-bmv2": "a two-key select with masked keysets, eleven vectors",
}
