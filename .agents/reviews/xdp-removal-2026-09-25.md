# XDP removal independent review

Independent read-only AI-agent review of
`fe927ef2f33532dd218e20540d2ff114ebc2c57a` against
`b7860a596a2689968cd9d15286f6129f01ce57ea`, in detached worktree
`/private/tmp/p4blo-remove-xdp-review`. This is not human review.

No confirmed defects. Removal is confined to the compile-only XDP experiment,
its workflow, associated structural registrations and current documentation.
Interpreters, schemas, proofs, P4 oracle inputs, surviving validation workflows
and the CI scope classifier are unchanged.

## Independent checks

- `git diff --check b7860a5 fe927ef`: exit 0. `git diff --exit-code` over
  `impl`, `spec`, P4 oracle inputs, conformance infrastructure, surviving
  validation workflows and `scripts/ci-scope.py`: exit 0.
- Boundaries, workflow guards and scope-classifier tests: 85 passed, using
  the main `.venv` interpreter with `PYTHONPATH` selecting review sources,
  `PYTHONDONTWRITEBYTECODE=1` and pytest `-p no:cacheprovider`.
- Real collection with `-k lean_agrees`: 3,045 selected, unchanged.
  With `-m 'not oracle'`: 5,275 selected, 490 deselected; 5,765 total.
- Push and pull-request events describing the actual reviewed revision pair
  both returned `full=true` from the classifier.
- Deleted-module AST inventory: 16 ordinary XDP cases plus one optional-image
  case removed. The two other removed collection entries are the XDP
  bare-interpreter registration and specialist-workflow registration.
- Directory listings confirm the removed oracle tree, workflow and dedicated
  test module are absent. Repository-wide XDP/eBPF searches find only deliberate
  decision/roadmap references, revision-qualified historical evidence and
  unrelated upstream P4-SpecTec coverage/vector names. Historical counts and
  evidence links are preserved. Review worktree remained clean.

The integrator separately ran all 154 structure tests successfully. No Lean
or Docker rebuild, full local gate or remote CI was performed by the reviewer;
the full local gate and applicable final-head remote checks remain required
before integration. No findings require reproducers or fixes.

## Final integration evidence

The reviewer also approved exact head
`c3d8a76e6c1d7e68851ecffd8dab04b661ff96c2`; only the faithful report and status
checkpoint differed from the reviewed implementation. The integrator's full
required-Lean local gate exited 0 with 5,271 passed, four expected failures
and no skips. All ten remote checks passed on that head before merge
`da6f6202e3014b195bba864844f9923d1223ddd7` in PR #7. The status page links the
four surviving workflow runs. These gate results are integrator evidence,
not independent reruns.

The closing status/report patch was independently reviewed against `da6f620`.
The reviewer queried PR #7 directly, confirmed its merge SHA, reviewed head,
all ten successful checks and matching workflow links. No findings; local
results remain attributed to the integrator. The clean review worktree was
removed and its absence verified.
