# Program tests

Does every corpus program rebuild from its source and behave as its
README and vectors say, and do the tutorial firewall and the homepage's
VLAN gateway give the answers written for them independently?

These are layers 3 and 4 of the testing strategy in
[`docs/design.md`](../../docs/design.md#testing-strategy).
`test_corpus.py` discovers every program under
[`../corpus/`](corpus) by itself: it validates the program, rebuilds
its golden from the eDSL source byte for byte and replays its STF vectors
on the Python interpreter. The other files hold the per-program checks
that a golden and a vector cannot express: the forwarder's tutorial
shape, the firewall's packets, boundaries, generated flows and complete
register state, and the VLAN gateway's wire and counter answers.

```
uv run pytest tests/programs
```

The firewall files also hold probes on the original P4 source that run
on the external oracles; they skip when an oracle is not built, and the
oracle workflows select them with `-k spectec` and `-k bmv2`. The public
application examples have their own tests beside their assets in
[`../examples/`](examples).
