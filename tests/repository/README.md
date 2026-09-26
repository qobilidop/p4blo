# Repository checks

Is the repository still shaped the way its documents say, so that the
other tests check what they claim to?

These tests sit beside the six layers of the testing strategy in
[`docs/design.md`](../../docs/design.md#testing-strategy) rather than in
one of them: they check no semantics, but they keep the evidence the
layers produce findable and honest. They check package ownership, test
discovery and import boundaries (`test_package_layout.py`,
`test_boundaries.py`), check that every relative link resolves and that
`docs/` never links into `.agents/` (`test_docs_links.py`), that the
ledger in `docs/ir-semantics.md` is well formed and cites names that
exist (`test_ledger.py`) and that its generated cross-reference table
is current (`test_ledger_xref.py`), that the quickstart and the
homepage run the program they show (`test_quickstart.py`,
`test_website.py`), and that the package imports (`test_smoke.py`).
Repository hygiene checks cover staged and working
file sizes (`test_file_sizes.py`) and reject missing, stale or modified
generated protobuf outputs (`test_generated.py`). Their negative fixtures
use temporary Git repositories; the generation check itself also runs in
the local and schema CI gates.

```
uv run pytest tests/repository
```
