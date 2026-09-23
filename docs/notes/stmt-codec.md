# Total statement codec

2026-09-23. Implementation follows [the reviewed plan](stmt-codec-plan.md)
at base `1d1168c`. Worktree: `/Users/qobilidop/my/work/p4blo-stmt-codec`.
This checkpoint is in progress; no final proof/gate claim yet.

## Independent old-decoder baseline

Before changing production `Json.lean`, the registered test-only endpoint
gained `stmt` and an explicit constructor-matching descriptor. Its tags,
branch order and argument observations do not use `Stmt.toJson`. Python
fixtures independently describe all fourteen constructors, asymmetric nested
branches, omission/default cases, optional fields, argument order and exact
first-error paths. `CodecKind` is the sole shared Python harness change.

The unchanged partial decoder at `1d1168c` passed:

- `nix develop -c scripts/check-lean.sh`: exit 0, both packages, default
  audits and native tests (`/tmp/p4blo-stmt-baseline-lean.log`).
- `nix develop -c uv run pytest tests/test_codec_leaves.py tests/test_codec_expr.py tests/test_codec_lvalue.py tests/test_codec_stmt.py -q`:
  495 passed, exit 0 (`/tmp/p4blo-stmt-baseline-focused.log`).
- Ruff format/check and Pyright for the new fixture: exit 0.

The complete source of captured requests is `tests.test_codec_stmt.requests`:
28 canonical constructor cases, 42 exact malformed cases, 9 normalization
cases, all 79 requests distinct. The baseline stores raw byte stdin, stdout,
stderr and exit status for every request, plus exact expected JSON and source
SHA-256 hashes. Every capture was checked against strict `same_json` first.
Artifact `.artifacts/codec/stmt-baseline.json`: 104543 bytes, SHA-256
`303a5bb6b682463d1029951070bb16120bf8c343c38a774d0eafccc89d95979e`.
The artifact is intentionally ignored local evidence, not a tracked golden
generated from the implementation. Production `Json.lean`'s recorded hash
can be checked against `git show 1d1168c:ir/P4bloIR/Json.lean`.
Independent [baseline review](reviews/stmt-codec-baseline.md) is clear;
the total decoder and proof campaign require a separate final review.

Reconstruct in a checkout of the old production decoder with these frozen
test-only fixture/endpoint changes applied, first building both Lean packages.
Run the following Python through `nix develop -c uv run python` with the
worktree root as its scoped working directory (adjust the absolute root for
a new isolated reproduction):

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_stmt import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-stmt-codec')
old_json = subprocess.check_output(
    ['git', 'show', '1d1168c:ir/P4bloIR/Json.lean'], cwd=root)
assert (root / 'ir/P4bloIR/Json.lean').read_bytes() == old_json
path = root / '.artifacts/codec/stmt-baseline.json'
assert not path.exists(), 'Never overwrite retained old-decoder evidence'
rows = []
for request, expected in requests():
    raw = (json.dumps(request, separators=(',', ':')) + '\n').encode()
    result = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')],
                            input=raw, capture_output=True, timeout=10, check=False)
    assert result.returncode == 0 and not result.stderr
    assert same_json(loads(result.stdout.decode('utf-8')), expected)
    rows.append(dict(request=request, expected=expected, stdin_hex=raw.hex(),
                     stdout_hex=result.stdout.hex(), stderr_hex=result.stderr.hex(),
                     returncode=result.returncode))
assert len(rows) == 79
assert len({json.dumps(r['request'], sort_keys=True) for r in rows}) == 79
artifact = dict(format='p4blo.stmt-baseline.v0', base=subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), sources={
    p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in [
        'ir/P4bloIR/Json.lean', 'ir/Tests/CodecLaws.lean', 'tests/test_codec_stmt.py']}, rows=rows)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(artifact, indent=2) + '\n')
```

This is finite native compatibility evidence. The later checked unfolding
law states the original recurrence with ordinary helpers, not equality to
the former opaque partial constant. Neither establishes universal raw-text
or Python equivalence, duplicate-text-key behavior, runtime resource bounds,
whole-program validity or execution semantics.
