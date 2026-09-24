# Firewall application review — 2026-09-24

Independent read-only review of candidate `f874b6f` in the isolated example
review worktree; source SHA-256
`ae6b5247c8e6d9468011f66d19d556bdd4b165cee6bad24ee953cbc1499cdf98`.
No confirmed correctness or usability defects remain.

The reviewer confirmed fixed zones, normalized exact tuples, per-packet service
policy, no aging/FIN/RST deletion and the documented input-envelope boundary.
Additional checks exercised the all-zero tuple (record exactly `1 << 96`),
collision rejection without eviction, and revoke/reallow without state loss.
The demo and its suggested service-port edit work as documented; review edits
were in-memory, not changes to canonical source.

The author ran 890 independent requests through Python and Lean, comparing
packets and all sixteen 97-bit cells after every request, including fresh-load
reset. The focused application/shared suite passed 12 tests; both actual P4
oracles passed the nine-packet STF with no skips. Full Pyright and Ruff passed.
Independent reviewer checks of both new applications and package layout passed
19 non-Lean tests (7 deselected), and full Pyright passed.

Integrator source-fault checks each fail both independent-answer tests:
admit a mismatching tuple, evict a collision resident, bypass service policy.
Baseline and restored runs each pass both tests. Reproducible recipe:
`docs/notes/mutations/example-programs.py`; local evidence:
`.artifacts/examples-mutations/firewall/`. These are program faults evaluated
under unchanged interpreters; no new interpreter-mutation claim is made.

A later demonstration-fidelity pass replaced the demo's deliberately unchecked
TCP checksum placeholders with valid SYN/SYN-ACK packets, including acknowledgment
one. A test checks the actual demo fixtures' IPv4 lengths/checksums, TCP
pseudoheader checksums, reversed endpoints and flags. The independent reviewer
confirmed those properties and unchanged demo output. Eight focused firewall
tests pass in the integrated tree. Program source, golden and STF are unchanged.
