# Python application examples

Accepted and completed 2026-09-24. All three applications are implemented,
independently reviewed and checked together locally and on CI. This
workstream follows completed assurance milestone 1 without reopening its
frozen acceptance criteria. Engineering procedures are in
[workflows.md](workflows.md#application-development).

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

The router uses a guarded fixed-header IPv4 profile. The firewall uses exact,
SYN-created TCP pinholes in sixteen direct-mapped slots; collisions reject
without eviction, policy applies on every packet and state lasts until reload.
Each README defines the supported profile and explicit limitations. Scoped
choices and their reasons are recorded in [decisions.md](decisions.md).
The load balancer dispatches UDP requests through service and group/bucket
tables, preserving IP addresses, UDP fields and payload, and assuming backends
share the VIP.

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
`uv run python -m examples.router.demo`, with corresponding
firewall and load-balancer modules. All three commands are available.
Follow the [development setup](../README.md#development) once.
Examples use the existing environment, with no separate package
or dependency set per application.

Each program keeps headers, parser, actions, tables, control and deparser
together. The demo supplies the host environment and retains loaded state
across packets. Its README explains the problem, contract, command, expected
results and source. Tests and any website excerpts use the canonical source.
Start without an examples framework or shared protocol library; extract
abstractions only when concrete usage demonstrates a readability benefit.

The shared example suite discovers `examples/*/program.py`, requires matching
test assets and checks goldens, exact vectors, demos and generated real-Lean
cases. Pyright includes `examples`; both existing oracle catalogs also discover
`tests/examples/*/*.stf`. Existing corpus cases and exact known-oracle
discrepancy classifications are preserved. New application-specific comparisons
use the shared `check_lean` helper and required fixture/name convention.

The upstream forwarder and tutorial firewall remain regression fixtures with
their original contracts. The live VLAN gateway remains the website example
until a separately justified presentation change. No website replacement,
additional application, Lean-authored counterpart or new proof ladder is
required by this workstream.

## Completion criteria

For each application, completion means a reviewed contract and runnable
demo; readable typed source; independent exact packet/fate/state
expectations; golden reconstruction; Python/Lean comparison and applicable
oracle evidence with precise exclusions; targeted adversarial checks; and a
fresh-reader review that runs and modifies the example without
conversation context. Failures from setup or compilation do not count as
semantic fault detection. Agreement between implementations does not
replace intended-behavior checks.

All three applications met these criteria on 2026-09-24 at implementation
revision `c94336d`, with clean independent reviews (archived in git) and
all required gates passing; [status.md](status.md) records the checks.
Additional applications and broader research remain backlog.
Evidence-driven improvements to the eDSL, diagnostics, runtime or
verification infrastructure are in scope for future application work;
changes to meaning still follow the semantics-first, paired-interpreter
procedure in the workflow.
