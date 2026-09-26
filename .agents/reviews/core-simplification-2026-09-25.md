# Core-only assurance simplification review

Independent read-only reviewer: Codex agent `simplify_review`, 2026-09-25.
Base: `5ee52d90f19d5d5a81bf972a115298ae167e691b`.
Reviewed Lean slice `88922c4` (integrated as `a9c01e4`), Python slice
`e3fab89` plus fix `d94ddf18` (integrated as `57f81b9`, `d848cf3`), public
docs `d6c3856` (integrated as `4dfa1c1`) and root scope/website `583ebf0`.
This is AI-agent review, not human review.

## Findings and disposition

One confirmed unintended guard loss: the moved firewall fixture initially
omitted the assertion that both `connection.stf` and `collisions.stf` exist.
Without it, removing a vector silently reduced that parametrized suite.
`d94ddf18` restores the exact baseline assertion. The author's positive
fixture passed; a temporary list missing exactly `collisions.stf` raised
AssertionError. The reviewer approved the repair. No unresolved findings.

Integration sweep also removed a stale certificate comment and a retired
`Frame.forBlock_initialized` citation, regenerated the ledger cross-reference,
and reduced the gate-library inventory to the two surviving packages.
These final metadata cleanups await the integrated review below.

## Lean and behavior preservation

The reviewer inspected retained Lean modifications and audit/test/Lake config.
Core validity, progress, execution and invariant implementations are unchanged
and do not import retired helpers. Main audit retains 140 declarations and
codec audit 48; the 19 removed axiom pins refer to deleted declarations.
Assembly's eleven executable definitions, endpoint helper bodies and
Externs/Interp/Switch/Coverage are unchanged. Architecture contract-discharge
and non-vacuity claims retire; the core's generic ExternContract premise stays.

The reviewer independently ran the old/new executable comparison: 89 fixtures,
514 packet requests and 363 CLI pairs had identical exit/stdout/stderr.
The author additionally checked two scalar/six-block validation pairs.
Baseline binary SHA-256:
`d9ff11ea8095ac45b6fff7202cec54d6c1d99a58aef7035cdf986594fea782bb`.
New author binary SHA-256:
`fe144d4e4ce1983c928d02df00bbafc4a33d9904eb070f10a9838fd0251dc951`.
Fixture inventory SHA-256:
`47616bda573171696af487a56a248d50a05c2cde49209213e7d6206207be5744`.
Both package build/test logs passed with `--wfail`; fresh author gate exited0.
The reviewer inspected those logs, without claiming an independent rebuild.
Integrator `nix develop -c scripts/check-lean.sh` also exited0.

## Test and claim preservation

Independent normalized collection comparison: 5,765 to 5,279 cases; exactly
486 retired and no unexplained additions. Those are 420 Lean-authoring cases,
61 certificate cases, three quickstart cases, one non-vacuity case and one
user-executable registration. All 710 runtime cases in seven moved mixed
suites remain. 547 Python-only cases were accurately renamed, while real
Lean comparisons retain the required discovery prefix. Independent expected
values, generic Lean replay, runtime fault observers and BMv2's five forwarding
profiles remain. All ten assurance cases and three input hashes/six requests
remain, with module paths updated and the retired binary requirement removed.

Author focused validation: 1,081 passed, two expected failures, 37 deselected;
Ruff, formatting, Pyright and actionlint passed. Docs author: 20 focused tests
passed and the new Lean snippet produced expected output on the new endpoint.
Reviewer inspected runtime observer/helper diffs, inventories and validation
logs, and reviewed README/design/assurance/adapter docs and website claims.
They consistently retire external proof guarantees and retain conditional core
progress without claiming termination or Python equivalence. Historical
proof evidence is revision-qualified.

## Integrated evidence

Full repository gate, frozen adversarial runner, final integrated review and
exact-main remote CI remain pending. Author checks are not those gates.
