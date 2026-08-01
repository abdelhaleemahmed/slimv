"""Shared rich console + small table helper."""
from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

# Windows consoles often default to a legacy codepage (cp1252) that can't encode
# arrows/bullets; force UTF-8 so output never crashes regardless of terminal.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

console = Console()


def make_table(title: str, columns: list[str]) -> Table:
    t = Table(title=title, title_style="bold cyan", header_style="bold")
    for c in columns:
        t.add_column(c)
    return t
