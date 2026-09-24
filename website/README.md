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
script for accessible language tabs and optional clipboard copying, and a
local SVG favicon. There are no build steps, dependencies, external fonts,
tracking scripts or network-loaded assets. Both language excerpts remain
readable without JavaScript. Narrow code blocks scroll inside their panel.

Navigation links to the existing repository documentation and sources.
The `Website` workflow in `.github/workflows/pages.yml` publishes this
directory to <https://qobilidop.github.io/p4blo/> on changes to `website/`
or its deployment workflow on `main`. It also supports manual dispatch on
`main`. GitHub Pages uses the GitHub Actions publishing source. Assets use
relative paths so the site works under the `/p4blo/` project subpath.

The snippets are excerpts of the actual forwarder actions, not standalone
programs or an in-browser runtime. When the source APIs change, compare each
excerpt with its linked source and recheck the descriptive action sequence.
Keep assurance language aligned with `docs/profile.md` and `docs/evidence.md`.
