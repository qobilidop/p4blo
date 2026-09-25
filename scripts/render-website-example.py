#!/usr/bin/env python3
"""Render the homepage walkthrough from the tested source; --check detects drift."""

from __future__ import annotations

import argparse
import html
import io
import keyword
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/corpus/vlan_gateway/vlan_gateway.py"
PAGE = ROOT / "website/index.html"
DOWNLOAD = ROOT / "website/vlan_gateway.py"
START = "<!-- BEGIN GENERATED GATEWAY -->"
END = "<!-- END GENERATED GATEWAY -->"

# Unique source anchors define whole, contiguous regions. No source is omitted.
STEPS = (
    (
        "wire",
        '"""A single-tag VLAN',
        "Describe the bytes on the wire.",
        "Ethernet comes first, then a four-byte VLAN tag. Field annotations carry exact bit "
        "widths: even the tag’s 3-bit priority and 12-bit VLAN ID are explicit. These Python "
        "classes describe packet headers, not ordinary Python records.",
        "WIRE FORMAT · 14 BYTES + 4 BYTES",
    ),
    (
        "contract",
        "class Headers(",
        "Separate the packet from its context.",
        "Headers hold parsed packet data. Metadata connects the program to its architecture: "
        "the host supplies ingress_port; the program chooses egress_port and drop. The core "
        "doesn’t know about a particular device.",
        "PACKET DATA + ARCHITECTURE CONTRACT",
    ),
    (
        "parse",
        "class Parse(",
        "Follow the tag.",
        "Extract Ethernet, then branch on EtherType. Only 0x8100 leads to the VLAN state. "
        "Extraction marks a complete header valid; a short packet leaves the tag invalid. "
        "The payload stays unread, ready to pass through unchanged.",
        "ETHERNET → VLAN → PAYLOAD",
    ),
    (
        "state",
        "admissions = Counter(",
        "Remember more than one packet.",
        "This extern declares a persistent counter for every 9-bit port value. The program "
        "records a call; the runtime provides the counter implementation. Reusing one loaded "
        "program preserves those counts across packets.",
        "PERSISTENT STATE · 512 COUNTERS",
    ),
    (
        "action",
        "class Gateway(",
        "Admit. Untag. Account.",
        "The table supplies a port. Restore the encapsulated EtherType before invalidating "
        "the VLAN header, count the admission, then clear drop. The explicit cast widens "
        "the port to the counter’s 32-bit index. Admissions count decisions, not physical "
        "transmissions.",
        "VLAN 42 → PORT 2 · ADMISSIONS[2] + 1",
    ),
    (
        "policy",
        "    access = p4.Table(",
        "Make permission an exact match.",
        "Three keys must match together: ingress port, VLAN ID and destination MAC. "
        "The host installs the entries; packet processing applies them. With the default "
        "policy shown here, a miss calls deny—even when the destination MAC is familiar.",
        "(INGRESS 1, VLAN 42, …:02) → DELIVER(2)",
    ),
    (
        "guard",
        "    def apply(self) -> None:\n        self.assign(self.meta.drop, True)",
        "Start closed. Check before lookup.",
        "Controls still run after a failed parse, so drop starts true. Only a valid tag, "
        "a VLAN ID from 1 to 4094 and a non-nested EtherType reach the table. "
        "with self.if_ records a packet-time branch; a normal Python if would run while "
        "building the program.",
        "UNTAGGED · TRUNCATED · NESTED → DROP",
    ),
    (
        "emit",
        "class Emit(",
        "A missing tag is the transformation.",
        "Emit writes valid headers in order. The admitted packet’s VLAN header is now "
        "invalid, so it contributes no bytes. The switch appends the untouched payload: "
        "a 38-byte input becomes a 34-byte output, with both MAC addresses preserved.",
        "ETHERNET + PAYLOAD · FOUR BYTES SHORTER",
    ),
    (
        "build",
        "def build() -> pb.Program:",
        "Build once. Inspect every operation.",
        "Assemble the parser, control, deparser and extern into one architecture-free IR. "
        "Running this complete source prints that IR. The linked demo installs the policy "
        "and replays packets; tests compare independent expected bytes and counter states "
        "against both Python and Lean execution.",
        "PYTHON eDSL → SHARED IR → EXECUTION",
    ),
)


def highlight(source: str) -> str:
    """Standard-library Python tokens, preserving source text exactly."""
    lines = source.splitlines(keepends=True)
    result: list[str] = []
    row, column = 1, 0
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.DEDENT):
            continue
        start_row, start_column = token.start
        if start_row > len(lines):
            continue
        while row < start_row:
            result.append(html.escape(lines[row - 1][column:]))
            row, column = row + 1, 0
        result.append(html.escape(lines[row - 1][column:start_column]))
        value = html.escape(token.string)
        style = ""
        if token.type == tokenize.STRING:
            style = "syntax-string"
        elif token.type == tokenize.COMMENT:
            style = "syntax-comment"
        elif token.type == tokenize.NUMBER:
            style = "syntax-number"
        elif token.type == tokenize.NAME and keyword.iskeyword(token.string):
            style = "syntax-keyword"
        elif token.type == tokenize.NAME and token.string[:1].isupper():
            style = "syntax-function"
        result.append(f'<span class="{style}">{value}</span>' if style else value)
        row, column = token.end
    while row <= len(lines):
        result.append(html.escape(lines[row - 1][column:]))
        row, column = row + 1, 0
    return "".join(result)


def render(source: str) -> str:
    regions: list[str] = []
    notes: list[str] = []
    buttons: list[str] = []
    remaining = source
    total = len(STEPS)
    for index, (name, anchor, title, body, caption) in enumerate(STEPS):
        assert source.count(anchor) == 1, f"source anchor changed: {anchor}"
        assert remaining.startswith(anchor)
        if index + 1 < total:
            next_anchor = STEPS[index + 1][1]
            assert remaining.count(next_anchor) == 1
            part, tail = remaining.split(next_anchor, 1)
            remaining = next_anchor + tail
        else:
            part, remaining = remaining, ""
        regions.append(
            f'<span class="code-step" id="step-{name}" data-step="{name}">{highlight(part)}</span>'
        )
        notes.append(
            f'<article class="step-note" data-note="{name}">'
            f'<p class="step-count">{index + 1:02d} / {total:02d}</p>'
            f"<h3>{html.escape(title)}</h3><p>{html.escape(body)}</p>"
            f'<p class="step-caption">{html.escape(caption)}</p></article>'
        )
        buttons.append(
            f'<button type="button" data-go="{name}" '
            f'aria-label="Step {index + 1}: {html.escape(title)}" '
            f'title="{html.escape(title)}"><span aria-hidden="true"></span></button>'
        )
    assert not remaining
    return (
        '<div class="walkthrough" id="gateway-walkthrough">\n'
        '  <div class="editor">\n'
        '    <div class="editor-toolbar"><span class="source-name">'
        '<span class="mini-dot" aria-hidden="true"></span> vlan_gateway.py</span>'
        '<span class="editor-label">PYTHON eDSL</span>'
        '<button class="copy-button" type="button" hidden>Copy source</button></div>\n'
        '    <pre tabindex="0" aria-label="Complete Python VLAN gateway source">'
        '<code id="gateway-source">' + "".join(regions) + "</code></pre>\n"
        '    <div class="editor-footer"><span>Complete source · no elisions</span>'
        '<a href="vlan_gateway.py" download>Download Python source ↗</a></div>\n'
        '  </div>\n  <aside class="note-panel" aria-label="Code walkthrough">\n'
        '    <p class="eyebrow">Follow the packet</p>\n    '
        + "\n    ".join(notes)
        + '\n    <nav class="step-navigation" aria-label="Walkthrough steps" hidden>'
        + "".join(buttons)
        + "</nav>\n  </aside>\n</div>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = SOURCE.read_text()
    page = PAGE.read_text()
    assert page.count(START) == page.count(END) == 1, "generated markers must be unique"
    before, rest = page.split(START)
    _, after = rest.split(END)
    rendered = before + START + "\n" + render(source) + "\n" + END + after
    if args.check:
        if page != rendered or not DOWNLOAD.exists() or DOWNLOAD.read_text() != source:
            raise SystemExit("Homepage source drift: run scripts/render-website-example.py")
        print("Homepage source and download match the tested gateway.")
    else:
        PAGE.write_text(rendered)
        DOWNLOAD.write_text(source)


if __name__ == "__main__":
    main()
