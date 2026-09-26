# Simplify assurance to the core IR

User-approved scope, 2026-09-25. Base/archive for retired features:
`5ee52d90f19d5d5a81bf972a115298ae167e691b`. Integrator branch:
`work/simplify-core`. No PR is required under the personal-project policy.

## Outcome and boundaries

Remove `impl/lean` (typed authoring and application proofs), concrete
architecture proof obligations, and the fixed execution-certificate experiment.
Retain `spec/ir` formal validity/progress/semantic/codec guarantees under their
existing premises. Retain `spec/arch` as executable tested support: assembly,
bindings, externs, entry functions, switch and the `p4blo-lean` endpoint.
The generic `ExternContract` remains a premise; concrete discharge claims retire.

Python authoring/interpreter/validator, Python examples, P4 importer, printer,
wire schemas and generated code, corpus inputs and external oracle inputs
stay unchanged. Keep valuable runtime regression/mutation tests even if their
old modules also tested the retired Lean authoring stack. Move shared packet
helpers and BMv2 profiles as needed; do not reduce unrelated semantic cases.
No new API or wire signature is introduced. `run`, `check`, `check-library`,
coverage and surviving codec modes retain their meanings. Certificate commands
and the separate Lean-user binary disappear intentionally.

## Ownership and dependency handoff

All author worktrees start from the committed base above, not a mutable tree.

- `simplify_lean`: `/private/tmp/p4blo-simplify-lean`, branch
  `work/simplify-lean`: Lean sources/configs, `impl/lean` deletion,
  `scripts/check-lean.sh`. Surviving README files belong to docs.
- `simplify_tests`: `/private/tmp/p4blo-simplify-tests`, branch
  `work/simplify-tests`: affected Python tests/assurance tools, certificate
  Python deletion, CI, `.gitignore`; README files belong to docs. Preserved
  runtime tests can move between test modules; corpus/example/oracle inputs
  remain unchanged. No Python runtime semantic edits.
- `simplify_docs`: `/private/tmp/p4blo-simplify-docs`, branch
  `work/simplify-docs`: public docs/READMEs and Python-first quickstart.
- Integrator: AGENTS, agent state/decisions/roadmap, website claim corrections,
  integration, independent review and final gates.

Authors commit their slices with checks and explicit integration dependencies;
no author waits for another's complete green tree. Integrator reviews patches,
combines them in one batch, builds Lean before differential tests, and runs
full gates against the combined revision. Independent read-only review covers
that final batch before main integration. No concurrent Lean rebuild/tests
in one worktree, no shared Docker-image rebuild.

## Acceptance and evidence

- Both surviving Lake packages build/audit/test with `--wfail`.
- Full required-Lean Python/schema gate passes; fresh generation matches index.
- Retained conformance answers, Python examples, corpus/oracle inputs and wire
  files remain byte-identical to base. Local comparison manifest is a convenience
  under `.artifacts/simplify-core`; git diff against the base is durable evidence.
- Assurance replay/mutation runner no longer depends on the removed user binary
  and its retained adversarial checks execute successfully in a frozen tree.
- Search active code/docs for removed paths/names and retired guarantee claims;
  preserve revision-qualified historical records.
- Review reports record confirmed defects/reproducers and final dispositions.
- Applicable remote CI passes on exact integrated main revision; clean up task
  worktrees/branches afterward. Preserve unique historical parked branches.

Current state: all author slices integrated. Lean `88922c4` -> `a9c01e4`,
Python `e3fab89` -> `57f81b9`, guard fix `d94ddf18` -> `d848cf3`,
docs `d6c3856` -> `4dfa1c1`; root scope `583ebf0`. Independent slice review
approved, one restored firewall vector guard. Both Lean packages passed
locally. Runtime equivalence: 89 fixtures/514 requests/363 CLI pairs unchanged.
Integrated code `f9cb19ee1b9afbb1b512a584eb147a01be331e03` passed final
independent review. Full required-Lean gate: 4,785 passed, four expected
failures, no skips; all other checks passed. Frozen assurance runner: exit0,
status passed, all28 phases, original three input hashes/six requests and
ten selected Python tests. The moved BMv2 forwarding profile passed locally.
Integrated-main CI remains pending. See
[review](../reviews/core-simplification-2026-09-25.md).
