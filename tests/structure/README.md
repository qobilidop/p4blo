# Structure tests

Is the repository still shaped the way its documents say, so that the
other tests check what they claim to?

These tests sit beside the six layers of the testing strategy in
[`docs/design.md`](../../docs/design.md#testing-strategy) rather than in
one of them: they check no semantics, but they keep the evidence the
layers produce findable and honest. They pin the package and test
layout and the import boundaries (`test_package_layout.py`,
`test_boundaries.py`), check that every relative link resolves and that
`docs/` never links into `.agents/` (`test_docs_links.py`), that the
ledger in `docs/ir-semantics.md` is well formed and cites names that
exist (`test_ledger.py`) and that its generated cross-reference table
is current (`test_ledger_xref.py`), that the quickstart and the
homepage run the program they show (`test_quickstart.py`,
`test_website.py`), that the package imports (`test_smoke.py`), and that
the XDP profile compiles (`test_xdp_build.py`, compile-only, never a
kernel execution oracle).

```
uv run pytest tests/structure
```

`test_xdp_build.py` skips without its Docker image unless
`P4BLO_REQUIRE_XDP_BUILD=1`; its own CI workflow sets it.
