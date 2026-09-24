# Lean public names review

Reviewed 2026-09-23: the integrator's naming-migration working diff,
read-only from an independent worktree. No blocking code finding.

## Checked before the migration commit

- Compared all **41 tracked Lean source files** against their HEAD versions
  after applying the intended exact token substitutions and path mapping:
  `P4blo` to `P4bloIR` for the specification, and `P4bloLean` to `P4blo`
  for the user library. There were **zero non-rename differences**. This
  covers theorem statements/proofs, scalar semantics, CRC models, tests,
  command endpoint and exporter. No accidental prefix substitution such as
  `P4bloIRLean` appeared.
- The specification remains Lake package `p4blo-ir`, now exposing library
  `P4bloIR` from `ir/P4bloIR.lean` and `ir/P4bloIR/`. The user Lake package
  is now `p4blo`, exposing `P4blo` from `lean/P4blo.lean` and `lean/P4blo/`.
  Its only local dependency remains `p4blo-ir` at `../ir`; the specification
  adds no dependency on the user package or old-name compatibility bridge.
- Library default targets, test root names and manifest package identity
  agree. The specification and user proof audits remain default targets;
  printed theorem names are renamed while their exact axiom sets are
  preserved. The fixture exporter remains a default target.
- Executable names `p4blo-lean`, `userTests`, `scalarExamples`, and the
  Python executable lookup are unchanged. No JSON/protobuf field, schema
  descriptor identity, interpreter behavior or generated-binding change
  is part of this rename. Corpus sources/vectors and printer goldens are
  unchanged apart from README path references.
- The strengthened package-layout checks cover package/library identities,
  default targets, renamed source roots and absence of old source roots.
  Independently invoked all four layout guards with bytecode writing
  disabled: **passed**. `git diff --check` also passed.
- Active Lean README examples correctly use `P4blo.Scalar` authoring and
  `P4bloIR` values/execution in their proof statement. Historical mutation
  logs and reviews remain historical rather than being silently rewritten.

Minor active-documentation finding: the schema header still referred to
`P4blo.IR` when first inspected. The integrator corrected it to `P4bloIR.IR`;
the revised comment was inspected, and the integrator reports Buf regeneration
produced no generated-file drift. This is not a wire-format change.
The design's current-layout summary and implementation checklist now name
the public packages; the write-up explicitly preserves its historical scope.

## Independent clean-build verification

Reproduced commit `411ba827706b6fc03128d4e90700718ba892b68b` in the fresh
`p4blo-naming-review` worktree, with neither package's old build cache.
No build was run in the integrator's worktree. All commands below exited
zero; results were checked after completion, not inferred from partial logs.

- `nix develop -c elan show`, from the repository root: **no active
  toolchain**. The gate's explicit pinned toolchain is therefore necessary
  and sufficient; this reproduction did not rely on a default selection.
- `nix develop -c /Users/qobilidop/my/work/p4blo-naming-review/scripts/check-lean.sh`:
  both packages built successfully (**49 and 39 jobs**), including fresh
  `P4bloIR` and `P4blo` modules and both `ProofAudit`/`UserProofAudit`
  targets. Both test drivers passed: **336 specification checks**, **13
  eDSL known answers**, **6 negative typing checks**, and package API tests.
- `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees`:
  **114 passed, 959 deselected, no skips** (30.91 seconds). This includes
  CRC, suffix dispatch, certificates, generated/stateful programs and all
  13 scalar eDSL cross-language examples.
- `nix develop -c uv run pytest tests/test_package_layout.py`:
  **4 passed** (0.09 seconds).
- `nix develop -c buf lint` and `nix develop -c buf generate`: passed;
  `git diff --exit-code -- python/p4blo/v0` passed with **no binding drift**.
  The full worktree status was clean before this report was updated.

The Lean linker emitted the already known macOS static-library deployment
target warnings (library minimum 15 versus link target 14); neither build
nor test failed. This independent run did not repeat the expensive full
Python/oracle suite; the integrator's **1070 passed / 3 strict expected
discrepancies / no skips** result remains separately attributed evidence.

The fresh build closes the stale-import/cache risk. No remaining blocking
naming-migration finding was identified.

Only this report was written by the reviewer, in the review worktree.
No main-worktree edits or commits were made.
