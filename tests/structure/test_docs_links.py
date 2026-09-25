"""Every relative link in tracked Markdown resolves, and docs/ never links into .agents/.

docs/ describes the artifact and will be published on its own; .agents/
describes the work and stays in the repository. A link from the former into
the latter would break on the published site, so the dependency runs one way.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s#]+)(?:#[^)\s]*)?\)")
FENCE = re.compile(r"^(```|~~~)")


def tracked_markdown() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md", "AGENTS.md"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [ROOT / name for name in output.decode().split("\0") if name]


def relative_links(path: Path) -> list[tuple[int, str]]:
    """Link targets outside fenced code, with their line numbers."""
    links: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE.match(line.strip()):
            fenced = not fenced
            continue
        if fenced:
            continue
        for target in LINK.findall(line):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("/"):
                continue
            if "/" not in target and "." not in target:
                continue  # a code sample such as ``[...](Extern)``, not a path
            links.append((number, target))
    return links


def test_relative_links_resolve() -> None:
    files = tracked_markdown()
    assert len(files) > 20, "git ls-files found too few Markdown files"
    broken: list[str] = []
    for path in files:
        for number, target in relative_links(path):
            if not (path.parent / target).exists():
                broken.append(f"{path.relative_to(ROOT)}:{number}: {target}")
    assert not broken, "broken relative links:\n" + "\n".join(broken)


def test_docs_never_link_into_agents() -> None:
    agents = ROOT / ".agents"
    crossing: list[str] = []
    for path in tracked_markdown():
        if not path.is_relative_to(ROOT / "docs"):
            continue
        for number, target in relative_links(path):
            resolved = (path.parent / target).resolve()
            if resolved.is_relative_to(agents):
                crossing.append(f"{path.relative_to(ROOT)}:{number}: {target}")
    assert not crossing, "docs/ links into .agents/:\n" + "\n".join(crossing)
