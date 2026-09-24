"""The homepage must present the tested program, byte for byte, without elisions."""

from __future__ import annotations

import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Walkthrough(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_source = False
        self.source: list[str] = []
        self.regions: list[str] = []
        self.notes: list[str] = []
        self.buttons: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "code" and attributes.get("id") == "gateway-source":
            self.in_source = True
        for name, target in (
            ("data-step", self.regions),
            ("data-note", self.notes),
            ("data-go", self.buttons),
        ):
            value = attributes.get(name)
            if value is not None:
                target.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "code":
            self.in_source = False

    def handle_data(self, data: str) -> None:
        if self.in_source:
            self.source.append(data)


def test_displayed_and_downloaded_source_are_the_complete_tested_program() -> None:
    expected = (ROOT / "tests/corpus/vlan_gateway/vlan_gateway.py").read_text()
    page = Walkthrough()
    page.feed((ROOT / "website/index.html").read_text())
    assert "".join(page.source) == expected
    assert (ROOT / "website/vlan_gateway.py").read_text() == expected
    assert page.regions == page.notes == page.buttons
    assert len(set(page.regions)) == 9


def test_website_generator_is_current() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/render-website-example.py"), "--check"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
