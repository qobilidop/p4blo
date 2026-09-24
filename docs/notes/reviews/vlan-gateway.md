# VLAN gateway and website review

Reviewed 2026-09-24 in the isolated `p4blo-example-review` worktree, based on `10cbbec` plus the proposed example and presentation files. Final workflow, maintenance documentation and browser-driven UI fixes were read from the integrator checkout without modification.

## Findings

No confirmed implementation defects remain from this review. Confidence is high in the bounded example behavior and generated-source linkage. Browser behavior relies on the integrator’s separately recorded visual and interaction checks.

The gateway presents a coherent complete program: typed headers, parser selection, host-installed policy, tag removal, persistent counters and deparsing contribute to one observable transformation. The source initializes drop before its validity guard, handles the documented VLAN boundaries, and restores EtherType before invalidating the tag. In this exact parser, valid VLAN implies successful preceding Ethernet extraction; the README correctly requires revisiting that argument if parsing is extended.

Independent expectations cover packet bytes, diagnostics and all 512 counter cells across persistent sequences. They correctly distinguish policy admissions from transmission: out-of-range output ports increment counters before architecture rejection. The Lean test checks independent expected outcomes in addition to Python/Lean agreement.

The generator preserves the complete canonical source through nine contiguous anchored regions. Tests compare decoded displayed text and the download against that source, and detect generator drift. Pages deployment includes canonical-source and renderer triggers and checks drift before uploading only `website/`.

Static UI review found named step controls, arrow/Home/End navigation, copy feedback, reduced-motion handling and readable source/notes without JavaScript. The final mobile focal point is independent of note height, avoiding selection feedback. Removing the focus-within visibility override allows the mobile card to disappear outside the walkthrough.

## Independent checks

Executed in the review worktree:

```sh
nix develop -c uv sync --locked
nix develop -c uv run pytest tests/test_vlan_gateway.py tests/test_website.py -q
```

Result: **4 passed, 1 skipped**. The skip was the Lean fixture because this worktree had no built Lean executable.

No browser execution, screen-reader testing, Lean rebuild, full suite or mutations were completed by this reviewer. The attempted mutation runner was blocked at the Nix daemon; its subsequent escalation wait was interrupted before execution. No source mutations were applied.

## Integrator-reported adversarial evidence

The integrator subsequently ran the bounded campaign in a separate mutation worktree using the existing Python environment and compiled Lean interpreter. These results were reported to this reviewer; their raw artifacts were not independently reread.

| Source fault | First independent mismatch, zero-based | Reported detection |
|---|---:|---|
| Remove the initial `drop=True` assignment in `Gateway.apply` | 5 | Untagged input incorrectly escapes on port 0 |
| Remove `self.set_invalid(self.hdr.vlan)` | 0 | Output retains four unwanted tag bytes |
| Replace `admissions.count(port.cast(p4.bit32))` with `admissions.count(p4.bit32(0))` | 0 | Packet output remains correct, but counter 0 changes instead of counter 2 |

For each fault, Python and Lean agreed on the wrong program; both independent expectation tests rejected it with assertion failures. Thus paired agreement alone would miss these authored-program faults, while the expected packet/state answers detect them.

The first campaign attempt exposed a retention-path defect: saving a failure bundle raised `FileNotFoundError` because `.artifacts/drt` did not exist. The integrator added directory creation to the Lean test and reran the campaign. That initial harness failure is **not** credited as a semantic detection.

The reported completed campaign exited successfully, with baseline and restored gateway tests passing. Final gateway and website checks reported **5 passed**. The reproducible recipe is `docs/notes/mutations/vlan-gateway.py`; successful logs, mutants, replay bundles and manifest are retained under `.artifacts/vlan-gateway/2026-09-24-checked/`. The initial failed attempt remains separately identified under `.artifacts/vlan-gateway/2026-09-24/`.

These are three selected source faults against unchanged APIs and interpreters, not exhaustive coverage or a whole-program correctness proof.
