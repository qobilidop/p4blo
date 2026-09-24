# Milestone 1 usability closeout

2026-09-23. Bounded pass against committed main `169a2c9`, in the isolated
`work/milestone-usability` worktree. No interpreter, IR, proof, application
source, golden, protocol, CLI or framework changes. Parked ingress/readback
work is not resumed or required by this pass.

## User path and corrected claims

`docs/quickstart.md` provides root-relative, pinned-environment commands to
build and run both existing complete programs from each language. It links
the four source files and their independent vectors, explains build-time
Python versus recorded runtime branches, and makes the raw Lean assembly
boundary explicit. No claim that the complete eDSL/frontends or pipelines
are verified is added.

Python uses `build`, `arch.load`, `Switch`, `stf_driver` and `assert_replay`.
One loaded object retains the firewall's registers across its four packets.
Lean uses the existing fixed in-memory `leanForwarder run` and
`leanTutorialFirewall run` servers, one process per complete sequence; Python
only resolves STF configuration and checks replies in this path. Neither
runner parses a golden or substitutes a decoded Program for its authored
Lean Program. Both produce independently expected output-port sequences
`[[2]]` and `[[], [2], [1], []]` and check all expected packet bytes.

A separate small Lean snippet constructs a checked expression, evaluates
wrapping addition and instantiates the exact unchanged-Run lowering theorem.
The import/API names and a rejected overflowing literal are executed, not
just shown. The guide distinguishes Lean preparation from Python validation,
ordinary drops from diagnostics, per-request server errors from process exit,
and persistence from arbitrary error rollback.

The root README now links the finite milestone and runnable guide rather
than presenting only gates or the broader proof roadmap. Root/corpus READMEs
no longer say the complete Lean firewall is unimplemented or that the
forwarder's only proved property is invalid-body identity. The Lean README
acknowledges read-only validity expressions while retaining the scalar-write
and raw-complete-assembly boundaries.

## Tests and calibration

`tests/test_quickstart.py` extracts the exact marked snippets from the guide.
It runs both complete source paths, the pinned Lean fragment/imports, a
symbolic Python truth-value diagnostic, nonempty unknown-table installation,
out-of-range egress diagnostics and both servers' usage/request-error paths.
The four Lean-dependent tests use the shared `lean_binary` fixture and
`test_lean_agrees` prefix (the two server cases are parametrized).

Initial test assumptions were corrected against actual APIs: Python
`bit8(256)` is not rejected immediately at construction, and an empty host
table section performs no installation. The retained tests exercise actual
failure boundaries instead. These were fixture calibration, not discovered
production defects or semantic mutation kills. Lean's checked literal
negative is an elaboration diagnostic, not a runtime conformance fault.

## Executed checks

Fresh worktree caches were built before any consumer tests. No shared or
mutable oracle image was built, and no application behavior was modified.

- `nix develop -c scripts/check-lean.sh`: exit 0; both packages, default
  audits and native tests (`/tmp/p4blo-usability-lean.log`).
- `nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest
  tests/test_quickstart.py tests/test_lean_forwarder.py
  tests/test_lean_firewall.py tests/test_corpus.py -q`: **240 passed**, exit 0
  (`/tmp/p4blo-usability-apps.log`). This includes exact corpus regeneration
  and existing application coverage; it is not the whole repository gate.
- All three complete marked shell blocks were independently executed from
  the worktree root through `bash -c`, including their `nix develop` prefixes:
  exits 0, matching expected output. The test harness normally executes the
  extracted payload in the already-selected environment to avoid nesting Nix
  in CI.
- `nix develop -c uv run ruff check tests/test_quickstart.py`,
  `ruff format --check tests/test_quickstart.py`, and
  `pyright tests/test_quickstart.py`: exits 0; no type warnings/errors.
- After review requested absolute paths inside the documented heredocs,
  the final quickstart-only gate reran: **6 passed**, exit 0
  (`/tmp/p4blo-usability-final-focused.log`). Only path construction and
  documentation spacing changed after the 240-test gate. Local README/guide
  links resolve and `uv sync --locked` exits 0.

Independent root review is **CLEAR**: complete source/docs inspection and
the final six quickstart cases passed without skips. The integrated report
is `docs/notes/reviews/milestone-usability.md`. Root owns the final integrated
full gate and milestone status; this note does not mark the milestone done.

## Decision and revisit boundary

High confidence in documenting and testing existing APIs rather than adding
another runner or hiding the raw IR seams. Medium confidence in the long
copy-paste Lean-server snippet as the best eventual UX: revisit only after
real user feedback demonstrates a repeated task worth a supported CLI.
Current commands are reproducible and tested; a new authoring framework is
not needed to finish this finite milestone.
