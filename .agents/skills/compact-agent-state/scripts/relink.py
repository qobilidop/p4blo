"""Rewrite repository links after files move or are archived.

usage: python3 relink.py MOVES.json DELETED.txt

Run from anywhere inside the repository after the `git mv` and `git rm`
commands. MOVES maps old repo-relative paths to new ones (a directory
move is given file by file); DELETED lists repo-relative paths that no
longer exist. Every tracked text file gets exact old-path strings
replaced by new ones. Every tracked Markdown file additionally gets
relative links resolved: links to moved files are retargeted, links to
deleted files become plain text marked archived, and links inside moved
files are re-based on their new directory. Link labels are left alone,
so a label that names the old file must be fixed by hand afterwards.

Restore historical review text afterwards using an explicitly inspected list
of topic files: original verdicts keep the paths they were written with.
Do not restore entire notes blindly when they also hold current navigation.
Path fragments without a slash (`"ir"`, `-d lean`, `parents[N]`) are not found
by this script; search for them separately.
"""
import json
import os
import re
import subprocess
import sys

ROOT = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
).stdout.strip()
os.chdir(ROOT)
moves = json.load(open(sys.argv[1]))
deleted = [line.strip() for line in open(sys.argv[2]) if line.strip()]
inverse = {new: old for old, new in moves.items()}
tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s#]+)(#[^)\s]*)?\)")
SCHEME = re.compile(r"^[a-z]+:")
edits = 0
unresolved = []


def is_deleted(path: str) -> bool:
    return path in deleted or any(d.startswith(path.rstrip("/") + "/") for d in deleted)


def text_file(path: str) -> bool:
    if path.endswith((".png", ".gz", ".pcap", ".lock")):
        return False
    try:
        with open(path, "rb") as f:
            return b"\0" not in f.read(4096)
    except OSError:
        return False


for path in tracked:
    if not text_file(path):
        continue
    with open(path, encoding="utf-8") as f:
        original = f.read()
    text = original
    for old, new in sorted(moves.items(), key=lambda kv: -len(kv[0])):
        if old in text:
            text = text.replace(old, new)
    if path.endswith(".md"):
        new_dir = os.path.dirname(path)
        old_dir = os.path.dirname(inverse.get(path, path))

        def fix(match: re.Match) -> str:
            global edits
            label, target, fragment = match.group(1), match.group(2), match.group(3) or ""
            if SCHEME.match(target) or target.startswith("/"):
                return match.group(0)
            resolved = os.path.normpath(os.path.join(old_dir, target))
            if resolved in moves:
                resolved = moves[resolved]
            if is_deleted(resolved):
                edits += 1
                marker = resolved.removeprefix("docs/")
                return f"{label} (`{marker}`, archived)"
            if not os.path.exists(resolved):
                # already rewritten by the plain replacement above, or genuinely broken
                resolved_new = os.path.normpath(os.path.join(new_dir, target))
                if os.path.exists(resolved_new):
                    return match.group(0)
                unresolved.append(f"{path}: {target}")
                return match.group(0)
            if os.path.normpath(os.path.join(new_dir, target)) == resolved:
                return match.group(0)
            rel = os.path.relpath(resolved, new_dir or ".")
            if target.endswith("/"):
                rel += "/"
            edits += 1
            return f"[{label}]({rel}{fragment})"

        text = LINK.sub(fix, text)
    if text != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("rewrote", path)
print(f"{edits} links rewritten")
for line in unresolved:
    print("UNRESOLVED", line)
