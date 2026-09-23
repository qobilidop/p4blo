# Package-boundary review

Reviewed: 2026-09-23, plan commit `6e23c83`, independently in a separate
worktree. This first pass is read-only inspection of the accepted plan and
existing implementation, not approval of a migration diff or new proofs.

## Plan assessment

The proposed one-way dependency and reuse-first interpreter API fit the
existing code. No architecture-level blocker was found. Moving files does
not establish whole-program validity: `Index.build` checks names, while the
proved `ScalarTyping.Typed` relation covers closed scalar expressions only.
Keep those distinctions visible in the public API and checkpoint claims.

## Migration hazards and required checks

1. **Dependency builds do not replace explicit specification gates.** The
   current Lake package separately defaults to `P4blo`, `p4blo-lean`, and
   `ProofAudit`, and has its own `tests` driver. A new `lean/` package importing
   `P4blo` need not build the specification executable, run its tests, or run
   its proof audit. CI must explicitly build/test both package roots. Add a
   separate audit for user-library lowering theorems. Avoid duplicate public
   library names such as `Tests`/`ProofAudit` across the dependency graph.
2. **Preserve the protobuf module-relative source path.** Change Buf's module
   root from `proto` to `ir/proto`, not to `ir`. The generated bindings and
   descriptor identity should remain `p4blo/v0/p4blo.proto`, byte for byte.
   Run lint/generation and diff the committed generated directory.
3. **A stale binary can produce false reassurance.** Python's
   `default_lean_binary()` resolves `lean/.lake/build/bin/p4blo-lean`; the
   shared fixture's absence diagnostic also names `lean/`. Update both to
   the authoritative executable location and exercise a clean worktree
   with `P4BLO_REQUIRE_LEAN=1`. An old ignored `.lake` directory must not make
   a missing migrated build look healthy. Ignore both package build roots.
4. **Pins and fixture paths are part of the move.** Update the CI toolchain
   cache key, installation command, documentation, Lake manifests, and
   fixture-regeneration instructions in `Tests/Main.lean`. The user package
   should use the same pinned Lean toolchain. The spec tests load relative
   fixture paths and must run with the specification package as working
   directory. Preserve the executable protocol/name to avoid unnecessary
   certificate and DRT churn.
5. **Corpus relocation can silently weaken test discovery.** Corpus and
   oracle tests discover vectors by globbing a path; a wrong path can turn
   a meaningful suite into empty parametrization skips. Assert nonempty
   program/vector discovery and compare collection counts across the move.
   Update `pyproject.toml`'s explicit `corpus` typecheck include, oracle
   imports and Docker contexts, and both oracles' pin/cache paths. Preserve
   the relative IDs used by the strict BMv2 divergence marker.
6. **Do not mistake unchanged prose for harmless history.** The existing
   `P4blo/IR.lean` and `Json.lean` module headers assert protobuf syntax
   authority and unrestricted encode/decode identity, respectively. Update
   active API comments and workflows consistently with the new ownership;
   label historical notes rather than retroactively rewriting evidence.

## Minimal first verified Lean eDSL slice

Start with closed, width-indexed scalar expressions: positive-width bits
and boolean literals, modular addition, bit equality, and conditional
selection. This is a foundation increment, not completion of stage 0.

- Define a small construction datatype indexed by scalar type. Require
  positive widths and fitting literals through types or smart constructors
  with explicit failure; do not silently wrap an out-of-range source literal.
- Give it compositional value semantics that does not call `lower` or
  `P4blo.evaluate`. A small width-indexed finite value is enough; do not
  introduce a new generic framework merely to represent it.
- Lower to the existing raw `P4blo.Expr`, proving both
  `ScalarTyping.Typed (lower e) t` and exact value preservation through the
  real evaluator, including preservation of every initial `Run`.
  `Typed.sound` alone proves the result's type, not the intended result.
- Test authored syntax and negative diagnostics separately from the core
  proof. Width mismatch, width zero, overflow literal, and non-boolean
  condition should be rejected. Use independent boundary known answers
  for zero, maximum value, wraparound, equality, and both conditional arms.
- Export a small set of constructed expressions inside existing valid
  packet-observable program wrappers, then run Python and Lean through the
  shared conformance gate. A Lean-only round trip is insufficient.
- Mutate addition lowering to subtraction and reverse conditional arms:
  exact-preservation proofs should reject those changes. Independently
  mutate notation expansion (where the core theorem still holds) and
  demonstrate a known-answer test catches the changed author's meaning.

Next extend typed references under an explicit frame relation, then simple
assignment/sequence and a stateful application. Do not market an expression
proof or raw program wrapper as verified complete-program lowering. No
performance-driven duplicate interpreter is warranted by the current plan.

## Evidence

Inspected package configuration, CI, DRT binary lookup/shared fixture, corpus
and oracle discovery, protobuf generation roots, raw syntax, scalar typing,
evaluation and value definitions, and the existing axiom audit. No source
edits, build runs, semantic mutants, or new theorem checking were performed
in this initial design review. Migration diff review remains pending.

## Migration working-diff review

Reviewed the integrator's uncommitted migration read-only on 2026-09-23.
No clean-checkout build has been independently performed yet; that review
is intentionally deferred until the migration commit exists.

Confirmed defect, fixed during review:

- The new user-library smoke test asserted that the forwarder drops an
  empty packet. The existing contract runs control after parser rejection;
  invalid IPv4 bypasses the drop table, so zero metadata unicasts the empty
  packet to port 0. An independent Python run against the pre-migration
  worktree produced exactly `[(0, b'')]`. The integrator corrected the
  expected output and requires no diagnostic, without changing semantics.

Checked in the revised diff:

- `check-lean.sh` passes the explicit `+<pinned toolchain>` to every Lake
  invocation, compares the two pins first, and explicitly builds/tests both
  package roots. The specification default targets retain `ProofAudit` and
  the conformance executable. The user package currently has no new
  theorems, so it needs no new axiom audit yet; wording must not imply that
  it has one. A separate audit remains required when lowering proofs land.
- The integrator's test run exposed that `lake -d` does not relocate a test
  subprocess's working directory. The revised script uses package-scoped
  subshells for `lake test`, preserving each driver's relative fixture paths.
  `bash -n` on the revised script succeeds. Actual clean-build behavior is
  not inferred from this syntax check.
- Buf's module root is `ir/proto`; the relocated schema changes only
  comments. The generated Python bindings have no working diff. Generation
  itself is part of the integrator's gate, not an independently rerun check.
- DRT resolves the executable under `ir/.lake`; the shared missing-binary
  diagnostic, both ignored build directories, CI toolchain cache keys and
  installation path are updated. A stale `lean/.lake` binary is no longer
  the default candidate.
- `p4blo-ir` preserves `P4blo` module identities. The user package's local
  dependency points to `../ir`, exposes `P4bloLean`, and uses a distinct test
  executable name. No reverse dependency was added.
- Execution aliases really reuse the reference entry points;
  `prepareSwitch` performs indexing, extern binding and architecture checks.
  Both its API comments and README explicitly disclaim full validation.
- The JSON header's unconditional roundtrip claim is replaced with tested
  profile/representability and unknown-field trust limitations.

No remaining code blocker found in this inspected migration diff. Corpus
relocation has not happened in this increment, so its discovery hazards
remain future acceptance criteria rather than migration defects. Preserve
historical review paths, but update active linked paths in
`corpus/register_bounds/README.md` and `oracle/bmv2/README.md`; both still
refer to the removed `lean/P4blo/Externs.lean` at review time.

This review does not substitute for the two-package build, full regression
suite, required differential gate, descriptor regeneration, or clean-worktree
reproduction. The integrator runs the current gate; independent reproduction
will be recorded separately after a committed interface is available.

## Independent clean-worktree reproduction

Reproduced commit `931e47f` in the review worktree on 2026-09-23, after
confirming that neither `ir/.lake` nor `lean/.lake` existed. The worktree
also started without a Python virtual environment; `uv sync --locked`
created its own environment from the pinned Nix Python 3.13.15.

Commands ran from the review checkout root, inside its Nix environment:

| Check | Actual result |
|---|---|
| `scripts/check-lean.sh` (absolute script path) | Exit 0; specification and user library built from no Lake cache, specification audit/test driver and user API test driver passed |
| `elan show` at checkout root | `no active toolchain`; explicit toolchain invocation works without an elan default |
| `uv run pytest tests/test_package_layout.py -q` | 3 passed, exit 0 |
| `P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees -q` | 95 passed, 910 deselected, no skips, exit 0 |
| Combined layout/conformance selection | 98 passed, 907 deselected, no skips, exit 0 |
| `buf lint`, `buf generate`, generated-binding `git diff --exit-code` | Each exit 0; no generated drift |
| `git status --short` after gates, before this report addition | Clean |

The pinned Lean native archives emitted macOS deployment-target linker
warnings (archive target 15.0 versus link minimum 14.0). They did not prevent
build or execution; no Lean proof warning or test failure occurred.

The full Python/oracle suite was not independently rerun in this review;
the integrator's separate evidence covers that gate. No main-worktree edits
or commits were made. The package migration is independently reproduced
for these checks, with no remaining finding blocking the next increment.
