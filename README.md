# p4blo

P4's semantic core as an IR, architecture-free, with an independent
Lean semantics validated against a runnable reference.

p4blo is a personal, educational prototype. It exists to make that
sentence concrete enough to argue about. The design, the four claims
it makes, and how each claim is tested are in
[docs/design.md](docs/design.md). Progress is in
[docs/status.md](docs/status.md).

## Getting started

Three tiers, from most to least reproducible.

1. **Nix flake with direnv** (recommended). Install
   [Nix](https://nixos.org/download/) and
   [direnv](https://direnv.net/), then `cd` into the repository and
   run `direnv allow`. Python, `uv`, `buf`, `protoc` and `elan` are
   pinned by `flake.lock`. Without direnv, prefix commands with
   `nix develop -c`.
2. **uv only.** Install [uv](https://docs.astral.sh/uv/) and run
   `uv sync`. This gives the Python package, tests, linter and type
   checker, but not the schema tools or Lean.
3. **Devcontainer.** Not provided yet; open an issue if you need one.

Then:

```
uv run pytest
```

## Layout

| Path | What |
|---|---|
| `proto/p4blo/v0/` | the IR schema, normative for syntax |
| `python/p4blo/` | the Python package: IR helpers, validator, interpreter, eDSL, printer, externs, architectures |
| `docs/` | design, closed behaviors, coverage table, status, decisions |
| `corpus/` | the example programs with their goldens and test vectors |
| `tests/` | everything that runs |

## License

Apache-2.0. See [LICENSE](LICENSE).
