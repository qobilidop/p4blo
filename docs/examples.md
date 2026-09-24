# Python application examples

Accepted 2026-09-24. Planning is complete; implementation has not started.
This workstream follows completed assurance milestone 1 without reopening its
frozen acceptance criteria. Current execution status lives in [status.md](status.md).
Agent instructions remain in [AGENTS.md](../AGENTS.md); engineering procedures
live in [workflows.md](workflows.md#application-development).

## Purpose and selection

Build a minimal collection of complete Python eDSL applications familiar to
people who program packet processors. Each should introduce a distinct idea
and make its behavior observable through a small runnable packet sequence.

| Application | Story | Main contribution |
|---|---|---|
| IPv4 router | Select a next hop and update the packet | Longest-prefix lookup, actions, header edits and checksums |
| Stateful firewall | Admit permitted communication and its return traffic | Policy whose decisions depend on earlier packets |
| Flow-affine load balancer | Distribute flows across servers consistently under unchanged configuration | Hashing, staged lookup and host configuration |

Finish the router first to establish the authoring and review workflow. The
firewall and load balancer are parallel conceptual next steps, each runnable
independently. Familiarity and a compact, honest behavioral contract matter
more than reusing existing implementations or maximizing feature counts.

The firewall's protocol subset, state capacity, expiration policy and state
representation are not yet selected. The existing Bloom firewall does not
decide those choices. Router input validation and load-balancer rewrite and
configuration-change policies also need explicit contracts before coding.
Record scoped choices and their reasons in [decisions.md](decisions.md).

## Accepted organization

```text
examples/
  README.md
  __init__.py
  router/                 # firewall/ and load_balancer/ follow this pattern
    __init__.py
    README.md
    program.py            # complete typed eDSL; build() returns the IR
    demo.py               # host configuration, packet sequence, results
tests/
  examples/
    test_examples.py      # shared example checks
    router/
      test_router.py      # independent application expectations
      program.txtpb      # generated IR golden
      *.stf               # independent packet vectors
  corpus/                 # preserved semantic fixtures and upstream ports
```

The intended repository-root invocation is
`nix develop -c uv run python -m examples.router.demo`, with corresponding
firewall and load-balancer modules. These commands are planned, not available
yet. Examples use the existing project environment, with no separate package
or dependency set per application.

Each program keeps headers, parser, actions, tables, control and deparser
together. The demo supplies the host environment and retains loaded state
across packets. Its README explains the problem, contract, command, expected
results and source. Tests and any website excerpts use the canonical source.
Start without an examples framework or shared protocol library; extract
abstractions only when concrete usage demonstrates a readability benefit.

Existing corpus discovery, differential and oracle harnesses assume
`tests/corpus/`; Pyright currently includes only `python` and `tests`.
Adding directories alone supplies no coverage. Extend discovery, typing and
CI selection explicitly, guard against empty discovery, and retain all
existing cases and exact known-oracle discrepancy classifications.

The upstream forwarder and tutorial firewall remain regression fixtures with
their original contracts. The live VLAN gateway remains the website example
until a separately justified presentation change. No website replacement,
additional application, Lean-authored counterpart or new proof ladder is
required by this workstream.

## Finite acceptance

For each application, completion means a reviewed contract and runnable demo;
readable typed source; independent exact packet/fate/state expectations;
golden reconstruction; Python/Lean comparison and applicable oracle evidence
with precise exclusions; targeted adversarial checks; and a fresh-reader
review that runs and modifies the example without conversation context.
Failures from setup or compilation do not count as semantic fault detection.
Agreement between implementations does not replace intended-behavior checks.

- [ ] Router meets the application criteria above.
- [ ] Stateful firewall meets the application criteria above.
- [ ] Flow-affine load balancer meets the application criteria above.
- [ ] All three are discovered by applicable repository/CI gates, including
  the shared real-Lean fixture and `test_lean_agrees` naming convention.
- [ ] Confirmed correctness and usability findings are resolved; remaining
  limitations, deferred opportunities and evidence boundaries are explicit.
- [ ] Required integration gates pass on the final implementation; commands,
  revisions, skips, reviews and next steps are recorded in repository docs.

Iterations address concrete findings, rather than a fixed number of passes.
When this checklist is satisfied, stop. Additional applications and broader
research remain backlog. Evidence-driven improvements to the eDSL, diagnostics,
runtime or verification infrastructure are in scope; changes to meaning still
follow the semantics-first, paired-interpreter procedure in the workflow.

## Next step

Write the router's packet/configuration contract and independent demonstration
expectations, then build the smallest complete runnable version and its test
integration. Use that experience to refine the workflow before building the
other applications. No application implementation was added during planning.
