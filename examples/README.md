# Python application examples

Complete applications for readers who already know networking and want to
learn how p4blo expresses packet-processing behavior. Start with the
[IPv4 router](router/README.md). The stateful firewall and flow-affine load
balancer are the next planned applications; their implementations are not
available yet.

Each application has a complete `program.py`, a host-side `demo.py` and a
behavioral contract in its README. Run from the repository root in the pinned
Nix environment (or use `uv sync` for the Python-only convenience environment).
Python builds IR; the interpreter executes that IR for each packet. Table
entries are host inputs. The switch architecture turns metadata into packet
delivery or drop decisions.

Verification lives under [`tests/examples/`](../tests/examples/). Existing
upstream ports and focused semantic fixtures remain under
[`tests/corpus/`](../tests/corpus/). The accepted collection and outstanding
work are recorded in [`docs/examples.md`](../docs/examples.md).
