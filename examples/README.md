# Python application examples

Complete applications for readers who already know networking and want to
learn how p4blo expresses packet-processing behavior. Start with the
[IPv4 router](router/README.md), then choose either independent next step:

| Application | What it teaches | Run from the repository root |
|---|---|---|
| [Router](router/README.md) | Route selection and packet rewriting | `uv run python -m examples.router.demo` |
| [Stateful firewall](firewall/README.md) | Policy and persistent exact pinholes | `uv run python -m examples.firewall.demo` |
| [Load balancer](load_balancer/README.md) | Service selection and flow-affine backend dispatch | `uv run python -m examples.load_balancer.demo` |

The firewall and load balancer do not import or require running the router.
Each application is intentionally small, with its supported packet profile and
limitations stated in its README.

The [Python authoring guide](../docs/python-edsl.md) explains the eDSL,
named exports and explicit extern registration. For a small extension outside
the supplied v1model profile, run `uv run python -m examples.custom_extern`.

Each application has a complete `program.py`, a host-side `demo.py` and a
behavioral contract in its README. Run from the repository root using the
environment created by `uv sync --locked`; see the [setup guide](../README.md#getting-started).
Python builds IR; the interpreter executes that IR for each packet. Table
entries are host inputs. The v1model architecture turns metadata into packet
delivery or drop decisions.

Verification lives under [`tests/programs/examples/`](../tests/programs/examples). Existing
upstream ports and focused semantic fixtures remain under
[`tests/programs/corpus/`](../tests/programs/corpus). How a new application is organized,
checked and reviewed is in [`docs/workflows.md`](../docs/workflows.md#application-development).
