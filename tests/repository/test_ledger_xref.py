"""docs/ledger-xref.md is exactly what scripts/ledger-xref.py writes.

The cross-reference table is generated from the ledger, so it can only
lie by going stale. Regenerating it here and comparing catches that, and
checking its rows against this directory's own ledger parser
(ledger.py) catches the generator skipping or reordering entries.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from tests.support import ledger

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ledger-xref.py"


def generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ledger_xref", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


def test_the_table_is_current() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_one_row_per_entry_in_ledger_order() -> None:
    module = generator()
    table = (ROOT / "docs" / "ledger-xref.md").read_text(encoding="utf-8")
    rows = [line for line in table.splitlines() if line.startswith("| [")]
    expected = [e.name for e in ledger.entries()]
    assert [e.name for e in module.entries(ledger.LEDGER.read_text())] == expected
    assert len(rows) == len(expected)
    for row, name in zip(rows, expected, strict=True):
        assert row.startswith(f"| [{name.rstrip('.').replace('|', chr(92) + '|')}]("), name


def test_every_spectec_name_links_to_the_pinned_source() -> None:
    table = (ROOT / "docs" / "ledger-xref.md").read_text(encoding="utf-8")
    module = generator()
    cited = sum(len(module.BACKTICKED.findall(e.get("SpecTec"))) for e in ledger.entries())
    assert table.count(f"({module.SPECTEC_REPO}/blob/") == cited
