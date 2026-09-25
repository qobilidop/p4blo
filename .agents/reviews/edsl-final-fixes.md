# Final-head fixes independent review

Reviewed `03c35e7..7082a48` on `work/edsl-ergonomics`, read-only, by an
AI agent (Claude Opus 5.5) separate from the author of the fixes:
`a6fb0ef` (coverage probe `build` stays stdlib-only), `07409ad`
(architecture prose scoped to the supplied adapters) and `7082a48`
(conceptual-prose lesson).

## Context

PR #2's head `03c35e7` failed CI's P4-SpecTec job at
`nix develop .#oracle -c python3 tests/oracle/coverage.py build` with
`ModuleNotFoundError: No module named 'p4blo'`: `ea1ef89` had added two
p4blo imports at module level. The local gate deselects oracle suites.

## Commands and results

- Bare-interpreter reproducer on copies: `python3 -I -B` running
  `coverage.py` at `03c35e7` fails with the CI error; at `7082a48` it
  imports cleanly. Every remaining p4blo and `tests.oracle` import is
  inside `materialize_corpus` or `materialize_generated`; `build` reaches
  neither.
- Grep of `.github/workflows/` and the oracle Dockerfiles for scripts run
  by a bare interpreter: `coverage.py`, `render-website-example.py`,
  `bmv2/driver.py`, `xdp/check.py`. An extended stdlib-only walk,
  including top-level `if`/`try`/`with`, found no non-stdlib import at
  module level in any of them.
- Every path and name cited by the new prose exists at `7082a48`:
  `spec/arch/proto/p4blo/arch/v0/assembly.proto` (`BlockBindings`),
  `spec/arch/P4bloArch/Assembly.lean`, `Switch.lean`,
  `docs/python-edsl.md`, `Architecture.run(loaded, entries, ingress_port,
  packet)`, `Registry.register` with `examples/custom_extern.py`, and
  `Block.params`.
- Grep of `docs/` and `README.md` for universal H/M, one-H-one-M,
  metadata-contract and calling-convention claims: none remain mandatory
  for every architecture or program. No new `docs/` link into `.agents/`.

## Confirmed findings

1. **Low.** `tests/oracle/xdp/check.py` runs as `CMD ["python3",
   "/opt/check.py"]` (`tests/oracle/xdp/Dockerfile`) but was missing from
   `BARE_INTERPRETER_SCRIPTS`. Reproducer: append `from p4blo import ir`
   to it; the boundary tests still passed. Fixed at `b43147d`, which also
   walks module-level `if`/`try`/`with` bodies (a nonblocking false
   negative the reviewer noted). With the fix, the same reproducer fails
   `test_bare_interpreter_scripts_import_only_stdlib_at_module_level`.

## Nonblocking observations

- `docs/arch-supports.md` said "the program's `M`" beside "selected `M`";
  aligned at `c1bcc39`.
- `sys.stdlib_module_names` is the test interpreter's (3.13); the BMv2
  and XDP images use Ubuntu's `python3`. Harmless for current imports.
- `docs/workflows.md` names only `run(...)`; the `Architecture` Protocol
  also declares `diagnostics`. Accurate for the STF driver, which only
  calls `run`. Left unchanged.
- `impl/python/p4blo/arch/contract.py`'s docstring ("An architecture names
  the fields of `M`") predates the split; it sits in the supplied
  architecture package, where the statement holds. Left unchanged.

## Checks the reviewer could not run

The repository pytest (a full gate was running in the same tree), the
oracle build, and the BMv2 and XDP images. The author ran afterwards,
each exiting 0: the coverage probe build and
`P4BLO_REQUIRE_SPECTEC_COVERAGE=1 pytest tests/external/test_spectec_coverage.py`
(9 passed, including a fresh-measurement match), and the boundary tests
after `b43147d`.
