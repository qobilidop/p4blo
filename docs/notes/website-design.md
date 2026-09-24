# p4blo website design

Requested 2026-09-23: study <https://veil.dev/> and design a project website.
This is a presentation task after assurance milestone 1, not a new semantics
or proof milestone. The working prototype lives in `website/`.

## Reference study

Veil's live homepage was inspected as text and in Chrome at desktop size.
Its dark background, blue hero, restrained navigation and short introductory
copy establish a research-tool identity. Capabilities lead into real Lean
code and an interactive IDE example, then a direct playground invitation.
Documentation and source are easy to reach throughout the page.

The transferable structure is introduction → capabilities → concrete example
→ evidence → next action. p4blo uses its own copy, code and vector artwork.
No Veil assets, logos or implementation were copied.

## Design direction

- Ink background, muted blue-gray supporting surfaces, warm white text and
  pale mint emphasis. Mint ties the shared IR diagram to source highlights.
- A compact lowercase wordmark with three offset bars suggesting an explicit
  representation. System sans-serif for prose; system monospace for labels
  and code. Local assets make the preview independent of font services.
- A split desktop hero pairs the core proposition with an architecture
  diagram. On narrow screens, the explanation precedes the diagram.
- Three short capability columns introduce authoring, execution and checking.
  The source viewer switches between the actual Python and Lean forwarding
  actions, with one shared explanation of the assignment order.
- Forwarder/firewall source links and a separate evidence section lead to
  existing documentation. The quickstart is the principal call to action.

## Content boundaries

The homepage says that Lean defines meaning and protobuf carries syntax.
The two authoring paths feed the IR; the executable Lean semantics and
independent Python interpreter provide execution comparisons. The diagram
does not assert arbitrary producer/decoder equivalence.

Action excerpts match `tests/corpus/forwarder/forwarder.py` and
`lean/P4blo/Forwarder.lean`, apart from indentation and introductory comments.
They are explicitly excerpts. They preserve old-destination-to-source MAC
assignment and eight-bit TTL wraparound, including zero wrapping to 255.
The full-program links supply the declarations and surrounding pipeline.

Evidence copy derives from `docs/profile.md`, `docs/evidence.md`,
`lean/ASSURANCE.md` and the milestone 1 completion/adversarial reports.
The site identifies the educational prototype and scoped proof boundary.
There is no browser interpreter, invented benchmark, fabricated testimonial,
unqualified verification claim or live CI badge. Both language tabs are
source presentation; the site does not execute the displayed programs.

## Delivery and maintenance

Plain static HTML/CSS/JavaScript fits a single landing page and avoids adding
a second package toolchain to the project. Local relative asset paths allow
root or subpath hosting. Existing GitHub documents are the documentation
destination until a separate documentation-site decision is made.

The preview includes semantic landmarks, visible keyboard focus, a skip
link, keyboard-operable tabs, clipboard feedback, reduced-motion support
and a no-JavaScript fallback. Verification and independent review are
recorded in `docs/status.md` and `docs/notes/reviews/website-design.md`.
The user subsequently requested publication to GitHub Pages. The `Website`
workflow deploys only `website/`, on relevant pushes to `main` or manual
dispatch on `main`. Official Pages actions are pinned by commit; Pages and
OIDC write permissions are scoped to the deployment job. There is no custom
domain or separate service. The project URL is
<https://qobilidop.github.io/p4blo/>.
