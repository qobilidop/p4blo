# Website design review

Reviewed 2026-09-23 in `/private/tmp/p4blo-website-review`, based on
`c6d18c0` plus the proposed `website/` and design note. Independent read-only
review; no files changed by the reviewer.

## Findings

No confirmed actionable defects found.

The homepage's supported-profile and assurance language agrees with
`docs/profile.md`, `docs/evidence.md` and the quickstart. It distinguishes
selected proofs from tested complete applications, acknowledges Bloom false
positives, and describes TTL wraparound and assignment order accurately.

Both displayed code excerpts match their linked source action definitions,
allowing for introductory comments and Python indentation. A scripted check
passed for 17 unique HTML IDs, 10 ARIA references and 22 distinct link/asset
targets. GitHub source links resolve to existing paths in the checkout;
local assets and fragment destinations exist.

Static inspection found coherent progressive enhancement: both examples
remain available without JavaScript; JavaScript adds tab semantics, roving
keyboard focus, arrow/Home/End navigation and optional clipboard feedback.
CSS supplies visible focus, reduced-motion behavior, responsive layouts and
local scrolling for code.

## Verification boundaries

This review checked source and local link targets, not live GitHub HTTP
responses. Browser rendering, actual keyboard/clipboard behavior and
desktop/mobile screenshots belong to the integrator's separate verification.
No formal accessibility certification or screen-reader test was performed.

Python/schema, Lean and oracle gates were not rerun: this change adds
presentation assets without modifying their implementations or inputs.

## GitHub Pages deployment supplement

The reviewer also checked `.github/workflows/pages.yml` and the updated
website documentation after the user requested publication. No confirmed
actionable defects found. Automatic deployment is limited to pushes on
`main` affecting `website/**` or the workflow itself. The job condition also
prevents manual dispatch from deploying another branch. Only `website/` is
uploaded. Pages/OIDC write permissions are scoped to the deployment job;
actions use full commit pins. Concurrency, timeout, environment URL and the
JavaScript syntax check are configured consistently.

The README and design note match the workflow's triggers, upload scope and
project-subpath layout. The supplement does not independently validate pin
provenance, repository Pages settings or successful publication. The
integrator resolved pins through GitHub's API and ran `nix develop -c
actionlint` successfully; publication requires live verification separately.
