# Minimal architecture review and adversarial checks

Independent AI-agent review, not human review. Base `14e6f44`; implementation
through `8e80f65`. Reviewed files and checks below have bounded coverage.
No deliberate fault was committed or retained in an implementation tree.

## Runtime and binding review

The Python author independently reviewed the Lean V1Model/Profile/Coverage
implementation, root's `562e571` native printer binding and `d3b9e95` printer
fixture migration at `8e80f65`. The reviewer did not independently review its
own Python runtime implementation. No new confirmed semantic defect remained.

Four concrete printed programs were run against pinned P4-SpecTec and the
stable Lean endpoint built at `1453102` (reviewed Lean source/Main bytes equal
to `8e80f65`):

- Egress writes 3, Compute reads 3, output keeps selected port 1.
- Omitted Egress still supplies reset egress_spec 0 to Compute.
- Egress writes drop 511 then 3; output is restored without redirection.
- An absent egress request field selects port 0.

All four passed. Fifteen direct role read/write acceptance/rejection probes
passed. Seven native stage requests preserved expected state counts 6/5/5;
dropped replies omitted emission coverage. The 56-case printer module had
50 passes, five Docker mount skips and one stale forwarder golden failure
that the pending caller migration repaired in `c87d64a`. The reviewer did not
rebuild Lean or rerun BMv2 and did not claim the full gate.

## Independent stage-order faults

A separate reviewer at `8e80f65` temporarily swapped Verify and Ingress in
its own Python adapter. `test_stage_order_and_drop_state` failed on all five
emitted packets: trace `00013245` instead of independent `00012345`.
The baseline passed before and after restoration.

The same independent mutation was then applied to the Lean adapter. Both
packages successfully compiled (117/141 build jobs); the architecture native
assertion for six-stage order failed. A seven-request Python/Lean replay
produced five trace divergences, two matching drops, zero execution/protocol
errors and unchanged state counts. This is a semantic kill, not a build failure.
Replay used the root's migrated compare_program read-only because the committed
review base's caller still named the retired adapter; the fixture bytes matched
the committed review copy.

After restoration, both-package Lean build/audit/test gate exited 0 and the
seven-request replay reported seven agreements, zero divergences and zero
errors. Both reviewer trees were clean; no intentional fault commits exist.
Temporary scripts/logs under /private/tmp are conveniences, not required
handoff evidence. The reproducer is the stated two-stage swap and committed
`tests/programs/v1model_fixtures.py` / `tests/programs/test_v1model.py` witness.

## Caller, frontend and evidence review

The Python author independently reviewed the frontend test handoff `999c35e`
and caller migration `c87d64a`. Exact original-source normalized comparisons
remain after guarded removal of empty optional stages and explicit expected-only
checksum/stateful splits. Four malformed CRC shape regressions passed. Review
found the generator catalogue accidentally renamed the core `control` family to
`ingress`; the seed inventory test failed. `cd1e06e` repairs it and the focused
reproducer passes. Review also found duplicate migration prose in arch-supports,
obsolete priority-annotation language, and old assurance/flood prose; the pending
documentation and driver follow-ups repair those. No heavy tests were claimed.

The separate reviewer independently compared `c87d64a` and `4fbe19d` with the
baseline. All 89 fixtures and 514 requests remain identical as inputs. Only two
former flood output lists change; zero extern-state answers change. There are
118 changed coverage observations, 13 changed diagnostic observations and three
renamed request error strings. The latter are distinct from diagnostics.

All 710 cases across the seven detailed semantic modules remain: 309 apply,
121 firewall, 79 Bloom, 64 action, 58 body, 40 forwarder and 39 table cases.
The earlier 470-case count described only the separately migrated subset, not
the entire retained collection. Three assurance hashes match their new pins;
the six requests (1, 1, 4) and ten-fault catalogue remain. Independent baseline
known-answer checks passed. Eighteen Filter-only corpus vector comparisons and
ten Filter/flood-only adapter cases retire; v1model replacements and other
renames do not count as removed behavior tests.

Review found the BMv2 runner still skipped a program declaring retired flood
metadata before profile validation, making its CLI report success. Adding bool
flood to the committed stage fixture reproduces the skip without using Docker.
The driver follow-up must reject it explicitly and retain a negative test.

## Integrated gates pending final checkpoint

At `4fbe19d` plus the documented fixes, the required-Lean full Python/schema
script exited 0: 4,798 passes, four expected failures, no skips; lint, format,
types, schema, fresh generation and workflow checks passed. Existing corpus
oracle suites passed 146 cases with five expected failures. The remaining oracle
batch passed 340 cases with eight expected failures, exposing the repaired
family key and stale coverage measurement. Fresh measurement preserves every
hit and instruction count; final replay, driver fix, frozen assurance and
exact-main CI remain required before completion.
