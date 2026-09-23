# p4blo

P4's semantic core as an IR, architecture-free, with an independent
Lean semantics validated against a runnable reference.

p4blo is a personal, educational prototype. It exists to make that
sentence concrete enough to argue about, so that a serious version can
be proposed to the P4 community rather than built alone. The proposal
it makes has no ask: P4 should have a specified, architecture-free
semantic core with a serialized form; the P4 language is one frontend
of that core; architectures and externs are specified outside it as
contracts.

## The four claims

Each claim has one experiment and one way to fail. The evidence lives
in this repository and runs in CI.

| Claim | Experiment | Where |
|---|---|---|
| The core is small and post-elaboration | the schema and its contract fit in a few pages; ten corpus programs need only named elaborations, no escape hatch | [`proto/p4blo/v0/p4blo.proto`](proto/p4blo/v0/p4blo.proto), [`docs/coverage.md`](docs/coverage.md), [`corpus/`](corpus/) |
| The core is semantically complete for real programs | every corpus vector matches P4-SpecTec's simulator packet for packet, through a printed P4 program under a v1model shim | [`oracle/`](oracle/), `tests/test_oracle.py` |
| A block is a function; an architecture is ordinary code | a filter in 45 lines and a switch in 50, no P4 in either; every program runs under both with the same fate decisions | [`python/p4blo/arch/`](python/p4blo/arch/) |
| The semantics is mechanized and agrees with the reference | a Lean interpreter, differential random testing against the Python one, one theorem | [`lean/`](lean/), `python/p4blo/drt/` |

Status per claim, with what is green and what is pending, is in
[`docs/status.md`](docs/status.md). Not claimed: performance, running
existing P4 source, P4Runtime, hardware, or a replacement for any tool.
The first thing a community version would build is a p4c backend;
[4ward](https://github.com/4ward-p4/4ward) shows the route.

The current development focus is a stronger Lean specification and stronger
evidence that Python implements it. [The verification program](docs/verification.md)
states the milestones, acceptance criteria, and limits of each guarantee.

## Reading order

1. [`docs/design.md`](docs/design.md): what p4blo is, why, and how each
   claim is tested.
2. [`proto/p4blo/v0/p4blo.proto`](proto/p4blo/v0/p4blo.proto): the IR,
   normative for syntax. Read it with
   [`docs/semantics.md`](docs/semantics.md), the closed behaviors.
3. [`corpus/forwarder/`](corpus/forwarder/): the tutorial forwarder as a
   p4blo program, authored in the typed Python eDSL and checked by
   pyright, with its IR golden and test vectors. Every corpus directory
   has a README naming what was elaborated away.
4. [`python/p4blo/interp/`](python/p4blo/interp/): the reference
   interpreter, written to be read as an explanation of P4's core.
5. [`lean/P4blo/`](lean/P4blo/): the same semantics in Lean, normative
   for meaning.
6. [`docs/coverage.md`](docs/coverage.md): every construct of
   P4-SpecTec's elaborated IL and its status in p4blo.
7. [`docs/decisions.md`](docs/decisions.md): every choice made while
   building, with its reason.
8. [`docs/workflows.md`](docs/workflows.md): the gates, where every
   external input is pinned, and how to make each kind of change.

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
scripts/check.sh              # every Python and schema check CI runs
cd lean && lake build && lake test
```

The oracle needs P4-SpecTec: `nix develop .#oracle -c oracle/build.sh`
builds it in a pinned OCaml environment; see
[`oracle/README.md`](oracle/README.md). The printer's goldens are
typechecked with p4c through Docker when it is available.

## Layout

| Path | What |
|---|---|
| `proto/p4blo/v0/` | the IR schema, normative for syntax |
| `python/p4blo/` | IR helpers, validator, interpreter, eDSL, printer, externs, architectures, STF runner, differential loop |
| `lean/` | the Lean interpreter, extern models, the theorem, the run mode for differential testing |
| `corpus/` | ten programs: eDSL source, IR golden, README, STF vectors |
| `oracle/` | the two oracles: P4-SpecTec's simulator and BMv2 |
| `docs/` | design, semantics, coverage, status, decisions, notes |
| `tests/` | everything that runs, including `pyright/`, the eDSL's static-check fixtures |

## Neighbors

P4-SpecTec is the P4 spec's own mechanization and this project's
coverage checklist and first oracle; Nano-P4 is the same size of
language with the opposite decision about the architecture; 4ward is
the precedent for a protobuf P4 IR and a p4c bridge; cedar-spec is the
method. The full list with links is in
[`docs/design.md`](docs/design.md#neighbors).

## License

Apache-2.0. See [LICENSE](LICENSE).
