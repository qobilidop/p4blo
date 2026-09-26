# Tests

Keep a test beside the thing whose behavior it specifies. Package tests are
outside the installed package, at `impl/python/tests/`. The root test tree
contains checks that span implementations, external tools or whole programs.
The Lean packages under `spec/` keep their own tests and audits.

| Location | Question answered |
|---|---|
| [`impl/python/tests/`](../impl/python/tests) | Does each Python component implement its contract? Includes interpreter, validator, authoring, printer and differential-runner unit tests, plus eDSL typing fixtures. |
| [`conformance/`](conformance) | Do independent implementations agree on wire encoding and execution? Includes fixed replies, semantic boundaries, generated cases, rule coverage and deliberate faults. |
| [`oracles/`](oracles) | Do external P4 tools agree? Includes drivers, patches, pinned inputs and tests of the adapters themselves. |
| [`programs/`](programs) | Does each program do what its author intended? Corpus sources and application verification assets stay beside their behavior tests. Public application sources remain in `examples/`. |
| [`repository/`](repository) | Are discovery, generated outputs, imports, documentation and CI still trustworthy? |
| [`support/`](support) | Shared builders, catalogs, packet constructors and independent expected answers. No tests and no imports from test modules. |

These checks establish different facts. A golden detects an authoring change;
a known answer checks intent; differential tests check agreement; an oracle
provides an external answer; a deliberate fault checks the sensitivity of the
comparison. Retain those independent checks even when they use the same program.

## Running tests

Use the development environment in [the README](../README.md#development).
`uv run pytest` discovers both roots. Importlib mode lets different components
use the same test filename without making the package tests an installed module.

```
uv run pytest impl/python/tests                     # Python package components
uv run pytest -m 'not lean and not oracle'           # all checks without native tools
P4BLO_REQUIRE_LEAN=1 uv run pytest -m lean            # after scripts/check-lean.sh
uv run pytest -m spectec                            # after tests/oracles/build.sh
uv run pytest -m bmv2                               # after building the BMv2 image
uv run pytest -m p4c                                # optional printer typechecking
scripts/check.sh                                    # Python/schema local gate
```

A real Lean comparison takes `lean_binary` and declares `pytest.mark.lean`.
External checks declare `spectec`, `bmv2` or `p4c`. The shared hook derives the
`oracle` category from those three markers. Pure adapter and fake-peer tests
have no native dependency marker. Filenames and test names do not choose CI.
Missing optional tools produce skips; a skip is not agreement evidence.

The local gate excludes external oracles and runs Lean checks when available;
`P4BLO_REQUIRE_LEAN=1` makes missing Lean a failure. `P4BLO_ALL_TESTS=1` includes
external checks too. Python CI selects `not lean and not oracle`; specialist
jobs select their marker across both roots. The two Lean shards are a complete,
disjoint partition. [Workflows](../docs/workflows.md) documents pins and gates.
