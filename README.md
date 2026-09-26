# p4blo

P4's semantic core as an architecture-free IR, with independent Lean and
Python implementations. This personal, educational prototype explores a
serialized core that frontends and architectures can share.

[Project website](https://qobilidop.github.io/p4blo/) ·
[Quickstart](docs/quickstart.md) · [Design](docs/design.md) ·
[Assurance](docs/assurance.md)

Author typed Parser, Control and Deparser blocks independently, combine them
in libraries, or bind them to the supplied six-stage v1model packet profile.
The project includes a validator, interpreter, P4 printer, scoped P4-SpecTec
importer, and runnable router, firewall and load-balancer examples.

Lean proofs cover selected architecture-free core properties under explicit
premises. Architecture adapters, concrete externs, Python execution and
applications are tested, with independent expected answers and P4-SpecTec/BMv2
comparisons. This is not full P4 support, a verified frontend, a proof of
Python–Lean equivalence, or a performance or hardware implementation claim.
Read [the supported profile and guarantees](docs/assurance.md) and
[known oracle differences](docs/oracle-discrepancies.md) for the boundaries.

## Getting started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
from the repository root:

```sh
uv sync --locked
uv run python -m examples.router.demo
uv run pytest tests/programs/examples -m "not lean and not oracle"
```

`.python-version` selects Python 3.13; uv can download it if needed. The locked
environment includes the package, tests, linter and type checker. These demos
need no compiler, Docker or external oracle.

Continue with the [applications](examples/README.md), the
[tested quickstart](docs/quickstart.md), or the
[Python authoring guide](docs/python-edsl.md). The [design](docs/design.md)
explains the architecture and source layout; [core semantics](docs/ir-semantics.md),
[architecture support](docs/arch-supports.md) and [P4 coverage](docs/p4-spec-coverage.md)
define the supported behavior.

## Development

Commands throughout the documentation assume the required tools are on PATH.
Choose how to install them; the project does not require a particular system
package manager.

| Work | Additional tools |
|---|---|
| Python examples and application tests | None beyond the uv environment above |
| Full Python/schema/workflow gate | Node.js, `buf`, `protoc`, `actionlint` |
| Lean packages and real differential tests | `elan`/`lake`; the checked-in `lean-toolchain` files select the compiler |
| P4-SpecTec oracle | Git, Make, opam, a C toolchain, pkg-config, GMP and zstd development files; [builder details](tests/oracles/README.md) |
| BMv2 and P4 printer typechecks | Docker and the corresponding pinned images; [workflow details](docs/workflows.md) |

Optional: [Nix](https://nixos.org/download/) provides pinned development tools
through `flake.nix` and `flake.lock`. With [direnv](https://direnv.net/) shell
integration enabled, run `direnv allow` once: `.envrc` loads the environment
when you enter the repository, so commands need no prefix. Alternatively,
enter the environment once with `nix develop` (add `.#oracle` to select the
shell with optional OCaml build prerequisites).

For repository checks after installing their tools:

```
scripts/check.sh              # Python/schema gate; external oracles excluded
scripts/check-lean.sh         # both Lean packages, core proof audits and tests
```

For dependency markers, oracle setup, pins and change-specific checks, see
[workflows](docs/workflows.md) and [the test guide](tests/README.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
