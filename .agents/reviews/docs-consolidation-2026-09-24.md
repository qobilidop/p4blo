# Review: documentation consolidation 07fe2da..996035d

Independent read-only review, 2026-09-24, of the four commits that took
`docs/` from 25 files to six (assurance, design, coverage, semantics,
quickstart, workflows). Every deleted source was read at `07fe2da` and
compared with the new text; every theorem name in the "What is proved"
table was checked against the three audit files; every relative link and
anchor in the docs, README, AGENTS.md, the website and the package
READMEs was resolved by script. All findings were fixed in commit
`1e33004`.

## Blocking (4)

- **B1.** `docs/design.md` stated each concern's authority as achieved
  where the archived IR boundary plan called validity and codec
  correspondence obligations; the "closed scalar fragment" qualifier was
  gone. Fixed: the table now has an "Intended authority" column and a
  "Today" column naming what is proved and what is open.
- **B2.** The firewall README and assurance.md pointed at
  `lean/ASSURANCE.md` for the firewall theorems, which that file does not
  contain. Fixed: point at `TutorialFirewallProof.lean`,
  `TutorialFirewallBloom.lean` and `lean/UserProofAudit.lean`.
- **B3.** The release evidence dropped the qualifier that toolchains and
  oracle caches were shared, so "fresh checkout" read stronger than the
  original. Restored, with the SpecTec executable hash.
- **B4.** The design document's archive pointer for the IR survey named
  `docs/design.md` instead of `docs/notes/prior-art-ir.md` at the tag.
  Fixed.

## Minor, all fixed

Coverage listed eleven programs and lacked the gateway row; the corpus
table did not say the gateway postdates the milestone; the printer's
W+1 note from the CRC contract survived only in code; the Cedar
inspection pin was dropped; the firewall README lost "fragment behavior
and exhaustive flag combinations are not exercised"; the BMv2 readback
section lost the settling-heuristic caveat; a stale ruff exclusion
comment; a doubled path in the website README; and the earlier
compaction review record had its file names rewritten by the path
replacement, which is now reverted with a note.

## Verified as consistent

The claim, the profile, the wire table, the exclusions and trust list,
all fifteen proof rows, the known disagreements, the release numbers
(627, 4793, 2886, five discrepancies, one skip), the CI run ids, the
SpecTec commit and BMv2 image, and the application checkpoint at
`c94336d` all match their sources. No load-bearing fact was lost from
the tree: CRC known answers live in `tests/test_crc.py`, the firewall
index table and collision witness in its README, the readback protocol
with the BMv2 driver, certificate commands and formats in assurance.md
and the code, the eDSL split in design.md, the corpus rationale in
design.md, and the website preview in its README. Every remaining
mention of a deleted path carries an archive qualifier.

Verdict before fixes: 4 blocking, 9 minor. After fixes: clear.
