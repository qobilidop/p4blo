# Python application examples

Complete applications for readers who already know networking and want to
learn how p4blo expresses packet-processing behavior. Start with the
[IPv4 router](router/README.md), then choose either independent next step:

| Application | What it teaches | Run from the repository root |
|---|---|---|
| [Router](router/README.md) | Route selection and packet rewriting | `nix develop -c uv run python -m examples.router.demo` |
| [Stateful firewall](firewall/README.md) | Policy and persistent exact pinholes | `nix develop -c uv run python -m examples.firewall.demo` |
| [Load balancer](load_balancer/README.md) | Service selection and flow-affine backend dispatch | `nix develop -c uv run python -m examples.load_balancer.demo` |

The firewall and load balancer do not import or require running the router.
Each application is intentionally small, with its supported packet profile and
limitations stated in its README.

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
