# Block-library boundary independent review

## Initial Lean review

Compared `97cc1d8` with `b816fb0` in the isolated
`work/edsl-library-review` worktree. Reviewed the contract in
`.agents/notes/edsl-wire-boundary.md`. This is an AI-agent review.

No confirmed defect found in the Lean split.

The four architecture-specific validity guarantees removed from core
`Valid` (H/M resolution, distinct roles, resolved and correctly signed
exports) are retained in `Bindings.Valid`. `BlockAssembly.check_sound`
composes those with core validity. Core progress retains its existing
premises, and the seven concrete entry theorems and their axiom audits
move to the architecture package. An independent text normalization check
confirmed `EntryLaws.lean` is byte-identical to its predecessor after
import, namespace and qualified helper-name substitutions. Its termination
and final-frame limitations are unchanged.

`Switch.load` validates bindings before loading roles and rejects a block
whose kind differs from its role. Core libraries impose no global H/M
roots, exports, or fixed block-kind counts. Recursive symbol searches
found no architecture assembly/binding/helper symbols in production IR
Lean; protobuf mentions the former fields only as reserved names.

Commands and evidence:

- `git diff 97cc1d8 b816fb0 -- spec/ir spec/arch impl/lean`: inspected
  schema, decoder, validator, theorem, endpoint and caller changes.
- `git diff 2a5a671 b816fb0 -- spec/ir spec/arch impl/lean`: establishes
  that every Lean source in the implementation agent worktree matches
  this reviewed revision. Differences are Python fixture/schema files.
- Executed the existing `spec/arch/.lake/build/bin/archTests` binary in
  `/Users/qobilidop/my/work/p4blo-library-lean/spec/arch`: exit 0, all
  tests passed, including scalar/six-block validity, missing roots,
  duplicate roles, unresolved exports, signature and role-kind rejection.
  This reused the implementation agent's build; it was not an independent
  rebuild or a claim about Python integration.
- Independently constructed JSON for a single scalar `inout bit<8>`
  control, and for two parsers, two controls and two deparsers, with no
  struct roots or bindings. Invoked that same built `p4blo-lean
  check-library -` on each: both exit 0 and print `accept`.
- Python text comparison of old/new EntryLaws with only the namespace
  migration substitutions: assertion passed.

Limitations: no full gate run here while Python architecture integration
is pending; no independent proof rebuild, oracle, mutation campaign or
remote CI review in this initial pass. The integrated final PR revision
still requires review and applicable gate evidence.

## Integrated Python review at 3bd8e03

Reviewed the architecture projection, validator, loader, metadata contract,
printer, eDSL assembly, extern declaration migration, application callers,
six-block witness, and public documentation relative to `97cc1d8`.
No confirmed design or semantic defect found in this pass.

Used the integrator's Python interpreter with `PYTHONPATH` explicitly set
to this isolated worktree's `impl/python`, from this worktree's root:

- `python -m pytest tests/unit/test_explicit_loader.py
  tests/unit/test_block_library_wire.py tests/programs/test_block_libraries.py
  -q`: 16 passed.
- `python -m pytest tests/unit/test_extern_registration.py
  tests/unit/test_extern_families.py tests/unit/test_validator.py
  tests/unit/test_arch.py tests/unit/test_edsl_exports.py -q`: 373 passed,
  3 skipped, 1 failed. The failure is a pending migration assertion:
  `test_scalar_block_compiles_without_program_roots_or_exports` compares
  protobuf repeated-field `[]` to tuple `()`. Reported to integrator;
  this is not a semantic rejection of scalar libraries.
- Independent scratch check on the forwarder golden: project into library
  and bindings, reconstruct assembly, assert exact serialized bytes;
  mutate each projection and then the reconstruction, assert the other
  values stay unchanged. All assertions passed.
- Independent invalid-binding cases on that golden: missing H root,
  missing M root, duplicate role, missing exported block, and each of the
  five entry parameter directions changed individually. Python validator
  and the previously described matching-source Lean binary rejected all
  nine cases with matching first codes (REF_UNRESOLVED, EXPORT_DUPLICATE,
  LVALUE_READONLY or EXPORT_SIGNATURE as appropriate).

This pass does not claim final-revision approval: migration corrections,
full integration gates and final-SHA review remain pending.

## Frozen implementation review at 70b51cd

Reviewed exact revision `70b51cdd28b331832fc9a6182b60218e68be38a6`,
including its complete delta from `3bd8e03`: adapter migrations, codec wire
alias fixes, scalar regression assertion, qualified ledger references,
structural ledger scanner, and checkpoint/design claims.

No confirmed defects or unresolved correctness findings. The previous scalar
assertion failure is fixed. The DRT snapshot now reconstructs the assembly
from the core library plus bindings before freezing it; oracle printing does
the same, and metadata access explicitly uses the bound roots. The ledger
scanner preserves architecture qualification and includes a negative
assertion against leaking unqualified architecture names.

Independent command, using this worktree's sources as before:

`python -m pytest tests/unit/test_edsl_exports.py
 tests/unit/test_block_library_wire.py tests/programs/test_block_libraries.py
 tests/structure/test_ledger.py tests/structure/test_ledger_xref.py
 tests/unit/test_explicit_loader.py -q`

Result: 43 passed, exit 0. This covers the corrected scalar witness, core
wire boundary, two blocks of each kind, explicit binding rejection and
ledger symbol separation. No root-worktree changes or shared heavy builds
were performed during the integrator's frozen assurance experiment.

Review disposition: implementation approved at the exact revision above.
The status accurately distinguishes prior checks from pending frozen-tree
assurance, BMv2 and final remote CI. Approval is code review evidence, not
an independent rerun of those gates; their completion and exact PR-head CI
remain integration obligations. A later metadata-only checkpoint requires
its delta to be reviewed before merge.
