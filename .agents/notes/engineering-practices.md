# Engineering-practice maintenance

Scope authorized 2026-09-25: learn from local p4-spectec-lean and strong
external examples, then improve p4blo. No semantic scope or AL integration
is opened. Inspection began from p4blo `045f3de`; the neighboring checkout
was on its active M3 work, observed at `b458a61`.

## Adopted practices and reasons

- p4-spectec-lean's `AGENTS.md`: substantive work goes through PRs;
  independent review and final-revision remote CI precede merging.
  Descriptions explain the problem, behavior, tradeoffs and evidence,
  with one verified author/model sentence. Coherent commits retain their
  rationale and attribution. Apply this workflow to this maintenance.
- Its `scripts/check-file-sizes.py`: enforce a 5 MiB budget against both
  Git's index and working files. Checking disk alone misses a staged
  large blob after the working copy has been shrunk or removed. Current
  p4blo files all fit, so no snapshot format changes are necessary.
- Its independently checked generated quotations illustrate a broader
  practice: validate the boundary independently and challenge the check
  with negative inputs. Here the concrete gap is protobuf regeneration:
  in-place generation plus `git diff` misses omitted new files and stale
  files. Fresh generation must match the submitted inventory and bytes.

External primary guidance, inspected 2026-09-25:

- [Google: change descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html):
  preserve rationale and context in the permanent record; update it after
  review changes the implementation.
- [Google: small changes](https://google.github.io/eng-practices/review/developer/small-cls.html):
  size by one self-contained outcome, including relevant tests; separate
  mechanical refactors from behavior changes.
- [Git: contributing patches](https://git-scm.com/docs/SubmittingPatches):
  independently explain the problem and justification of each commit.
- [GitHub: helping reviewers](https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes):
  focused PRs and clear context make review effective.
- [GitHub: merging](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request):
  satisfy repository review/check requirements; choose the merge method
  deliberately. No repository protection settings were changed.
- [GitHub: large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github):
  history growth matters; deleting a file later leaves historical blobs.
  Our 5 MiB budget is intentionally stricter than the platform limits.

## Adaptation boundaries

Keep optional Nix setup and ordinary documented commands as p4blo decided.
Keep its independent Lean/Python semantics; the neighboring project's
upstream-mirroring discipline is appropriate for a port, not for two
independent implementations. Keep the existing Lake test-library layout,
warnings-as-errors and axiom audits. Inspection found no Lean module
omitted from the combined three-package build; do not invent a missing
build merely because an umbrella module does not directly import it.

No bulk style migration, new dependency, compressed-fixture conversion,
history rewrite or expansion of semantic claims is needed. Use the full
name P4-SpecTec in new prose; preserve literal formats and historical
records. The status file and independent review record carry the actual
validation results and remaining work.
