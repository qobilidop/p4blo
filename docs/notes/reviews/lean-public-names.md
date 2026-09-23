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

## Clean-build verification still pending

No build was run in the integrator's working tree while its gate was active.
A fresh post-commit worktree with neither package's `.lake` directory must
still build both packages, execute both audits/test drivers, run required
cross-language conformance (including scalar authoring, CRC and suffix
regressions), and check generated bindings. Existing build caches can retain
old import modules, so source inspection and in-place success are not a
substitute for that uncached reproduction. Its results will be recorded
after the committed migration is available.

Only this report was written by the reviewer, in the review worktree.
No main-worktree edits or commits were made.
