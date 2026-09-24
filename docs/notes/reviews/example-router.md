# Router application review — 2026-09-24

Independent read-only review in `/Users/qobilidop/my/work/p4blo-example-review`
against the first router implementation and shared test integration.
No confirmed correctness or usability defects remain.

Reviewer checks:

- Documented Nix demo matches the README.
- Non-Lean application suite: 6 passed, 2 deselected; full Pyright: zero errors.
- In-memory route override moves only the specific-route case to port 3.
- Ten independently constructed packets preserve DSCP, identification,
  protocol, DF and payload while decrementing TTL and updating the checksum.
- Trusted default replacement forwards valid packets without bypassing the
  TTL or truncated-header gates.
- Both oracle catalogs discover the new vector and its source-equivalent IR.

The reviewer checked agreement between implementation and the documented
fixed-header, canonical-checksum, fragment and payload-envelope boundaries.
The 60 expected outcomes are built without eDSL/runtime packet construction;
the checksum helper has an independent fixed-byte known answer.

Integrator checks additionally pass: both Lean packages and audits; all 10
selected router/discovery/oracle tests, including actual P4-SpecTec and BMv2;
and a restored-baseline application mutation experiment. The recipe is
`docs/notes/mutations/example-programs.py`; exact local logs and source hashes
are under `.artifacts/examples-mutations/router/`.

Three source faults (TTL guard weakened, checksum update removed, wrong egress)
each fail both independent-answer tests under unchanged Python and Lean
interpreters. Baseline and restored runs each pass both tests. This checks
authored program intent; it is not a new mutation of interpreter semantics.
The existing finite assurance gate covers interpreter mutation separately.

The initial integrator test run omitted the stateless checksum observation
from expected state. Both interpreters and packets agreed; correcting the
explicit expected observation resolved the harness mistake before this review.

The broad integration run subsequently found one existing layout assertion
that required oracle catalogs to contain corpus vectors only (4817 other
tests passed). The guard now requires the exact union with nonempty application
vectors. The corrected layout and all examples pass together (12 tests), and
format/lint/type/schema/actionlint checks pass. This discovery fix was made by
the integrator after the independent application review; no program behavior
changed. Full command/exception evidence is in `docs/status.md`.
