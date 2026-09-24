# p4blo website

A responsive landing-page design inspired by the clear research-tool
presentation at [Veil](https://veil.dev/). The rationale and source mapping
are in [the design note](../docs/notes/website-design.md).

## Preview

From the repository root:

```sh
nix develop -c python -m http.server 4173 --bind 127.0.0.1 --directory website
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
then regenerate the highlighted block and downloadable source:

```sh
nix develop -c uv run python scripts/render-website-example.py
nix develop -c uv run pytest tests/test_website.py tests/test_vlan_gateway.py
nix develop -c node --check website/main.js
```

The generated files are committed, so deployment needs no site build.
The renderer's `--check` detects drift in CI and before Pages deployment;
pytest additionally checks the actual rendered code text against the source.
The gateway tests need the built Lean executable for required conformance;
see `docs/workflows.md`. The adjacent corpus README documents the example's
single-tag profile and the difference between admissions and transmissions.
Keep assurance language aligned with `docs/profile.md` and `docs/evidence.md`.
