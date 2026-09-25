# p4blo website

A responsive landing page inspired by the research-tool presentation at
[Veil](https://veil.dev/): a short introduction, the capabilities, real
code with a scrolling explanation, then a direct next action. It presents
the project with the same evidence boundaries as `docs/assurance.md` and
never claims more than the documentation does; the repository documents
remain the documentation destination.

## Preview

From the repository root after [development setup](../README.md#development):

```sh
uv run python -m http.server 4173 --bind 127.0.0.1 --directory website
```

Open <http://127.0.0.1:4173>. Alternatively, open `index.html` directly;
clipboard availability depends on the browser. Stop the server with Ctrl-C.

## Implementation

The directory is a complete static site: semantic HTML, local CSS, a small
script for scrolling code annotations and optional clipboard copying, and a
local SVG favicon. There are no browser dependencies, external fonts,
tracking scripts or network-loaded assets. The full Python source and all
nine annotations remain readable without JavaScript. Narrow code scrolls
inside its panel. The note is sticky on desktop and a bounded floating card
on mobile; keyboard users can choose steps with arrows/Home/End.

Navigation links to the existing repository documentation and sources.
The `Website` workflow in `.github/workflows/pages.yml` publishes this
directory to <https://qobilidop.github.io/p4blo/> on changes to `website/`
or its deployment workflow, canonical example or renderer on `main`. It also supports manual dispatch on
`main`. GitHub Pages uses the GitHub Actions publishing source. Assets use
relative paths so the site works under the `/p4blo/` project subpath.

The walkthrough presents the complete tested
[`vlan_gateway.py`](../tests/corpus/vlan_gateway/vlan_gateway.py), not a browser
runtime. Edit that canonical source and the explanatory steps in the renderer,
then regenerate the highlighted block and downloadable source. The final
syntax check also needs Node.js, as listed in the development setup:

```sh
uv run python scripts/render-website-example.py
uv run pytest tests/structure/test_website.py tests/programs/test_vlan_gateway.py
node --check website/main.js
```

The generated files are committed, so deployment needs no site build.
The renderer's `--check` detects drift in CI and before Pages deployment;
pytest additionally checks the actual rendered code text against the source.
The gateway tests need the built Lean executable for required conformance;
see `docs/workflows.md`. The adjacent corpus README documents the example's
single-tag profile and the difference between admissions and transmissions.
Keep assurance language aligned with `docs/assurance.md`.
