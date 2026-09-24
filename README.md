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
| The core is small and post-elaboration | eleven corpus programs use existing core constructs and explicit extern contracts, without application escape hatches | [`ir/proto/p4blo/v0/p4blo.proto`](ir/proto/p4blo/v0/p4blo.proto), [`docs/coverage.md`](docs/coverage.md), [`tests/corpus/`](tests/corpus/) |
| The core supports the tested real programs | corpus packet replays on two oracles, plus original firewall packet/state checks; precise known discrepancies remain explicit | [`tests/oracle/`](tests/oracle/), [`docs/notes/firewall-port.md`](docs/notes/firewall-port.md) |
| A block is a function; an architecture is ordinary code | a filter in 45 lines and a switch in 50, no P4 in either; every program runs under both with the same fate decisions | [`python/p4blo/arch/`](python/p4blo/arch/) |
| The semantics is mechanized and agrees with the reference | a proof-visible Lean interpreter, scalar soundness and value laws, corpus and generated-program comparison against Python | [`ir/`](ir/), `python/p4blo/drt/` |

Status per claim, with what is green and what is pending, is in
[`docs/status.md`](docs/status.md). Not claimed: performance, running
existing P4 source, P4Runtime, hardware, or a replacement for any tool.
The first thing a community version would build is a p4c backend;
[4ward](https://github.com/4ward-p4/4ward) shows the route.

The current development focus is the bounded
[Milestone 1](docs/milestone-1.md): useful Python and Lean authoring, a strong
specification, and tested implementation conformance. The broader
[verification program](docs/verification.md) records longer-term directions,
not additional requirements for finishing this milestone.
The tests compare persistent extern state as well as packets. Recorded
mutation campaigns challenge both implementations; failing experiments
retain concrete replay bundles. These are layered evidence, not a proof of
universal Python–Lean equivalence or whole-program type safety.
The [execution-claim experiment](docs/certificates.md) also runs a fixed
stateful program in production Python and checks its claimed result with
a Lean checker whose acceptance theorem is proved. Its compiled runtime
and observation adapter remain explicit trust boundaries.

The [tutorial firewall](tests/corpus/tutorial_firewall/README.md) preserves
Bloom-filter false positives and compares all 8,192 register cells against
unchanged original P4 on BMv2. Stronger probes exposed pinned SpecTec CRC32
padding and table-mask defects that simpler packet sequences missed. They
remain strict, precisely classified expected discrepancies—not model changes
to manufacture agreement. The independent
[Lean-authored firewall](lean/P4blo/TutorialFirewall.lean) now runs the complete
program with persistent state. Initialization and Bloom-insertion properties
are proved under explicit premises; a complete firewall pipeline proof is not
claimed. See [its assurance note](docs/notes/lean-firewall-port.md).

## Reading order

1. [`docs/design.md`](docs/design.md): what p4blo is, why, and how each
   claim is tested.
2. [`ir/P4bloIR/IR.lean`](ir/P4bloIR/IR.lean): the abstract IR;
   [`ir/proto/p4blo/v0/p4blo.proto`](ir/proto/p4blo/v0/p4blo.proto) defines
   its wire syntax. Read them with
   [`docs/semantics.md`](docs/semantics.md), the closed behaviors.
3. [`tests/corpus/forwarder/`](tests/corpus/forwarder/): the tutorial forwarder as a
   p4blo program, authored in the typed Python eDSL and checked by
   pyright, with its IR golden and test vectors. Every corpus directory
   has a README naming what was elaborated away.
4. [`python/p4blo/interp/`](python/p4blo/interp/): the reference
   interpreter, written to be read as an explanation of P4's core.
5. [`ir/P4bloIR/`](ir/P4bloIR/): the same semantics in Lean, normative
   for meaning. The independent [Lean user library](lean/README.md) imports
   this specification and exposes verified scalar authoring and execution:
   `import P4blo` for users, `import P4bloIR` for the IR contract.
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

To author and run the complete forwarder and persistent firewall in either
language, follow the [tested quickstart](docs/quickstart.md). It uses the
existing APIs and executables; no Docker or P4 oracle is needed.

For repository checks:

```
scripts/check.sh              # every Python and schema check CI runs
scripts/check-lean.sh         # both Lean packages, audits and tests
```

The oracle needs P4-SpecTec: `nix develop .#oracle -c tests/oracle/build.sh`
builds it in a pinned OCaml environment; see
[`tests/oracle/README.md`](tests/oracle/README.md). The printer's goldens are
typechecked with p4c through Docker when it is available.

## Layout

| Path | What |
|---|---|
| `ir/` | authoritative Lean syntax/semantics, scoped proofs, wire schema and conformance endpoint |
| `python/p4blo/` | IR helpers, validator, interpreter, eDSL, printer, externs, architectures, STF runner, differential loop |
| `lean/` | user-facing `P4blo`, depending on `P4bloIR`; verified typed scalar authoring under explicit frame premises and reference execution API |
| `tests/corpus/` | eleven programs: eDSL source, IR golden, README, STF vectors |
| `tests/oracle/` | the two oracles: P4-SpecTec's simulator and BMv2 |
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
