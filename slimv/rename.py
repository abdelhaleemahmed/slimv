"""`slimv rename <folder> <text>` — bulk-remove a piece of text from filenames,
keeping the rest of the name and the extension.

DRY-RUN BY DEFAULT: it prints the ``old -> new`` changes and renames nothing
until ``--apply`` is given. Collisions and empty results are skipped, never
forced.
"""
from __future__ import annotations

from pathlib import Path

from .console import console


def _clean(stem: str, tidy: bool) -> str:
    """Optionally collapse double spaces and trim stray separators left behind."""
    if not tidy:
        return stem
    while "  " in stem:
        stem = stem.replace("  ", " ")
    return stem.strip(" -_.")


def run(folder: str, text: str, recursive: bool = False,
        exts: list[str] | None = None, ignore_case: bool = False,
        tidy: bool = False, apply: bool = False) -> int:
    root = Path(folder)
    if not root.is_dir():
        console.print(f"[red]Not a folder:[/red] {root}")
        return 2

    ext_set = {e.lower() if e.startswith(".") else "." + e.lower() for e in (exts or [])}
    files = root.rglob("*") if recursive else root.glob("*")

    planned = collisions = skipped = 0
    seen: set[str] = set()

    for f in sorted(files):
        if not f.is_file():
            continue
        if ext_set and f.suffix.lower() not in ext_set:
            continue

        stem, suffix = f.stem, f.suffix
        if ignore_case:
            idx = stem.lower().find(text.lower())
            new_stem = stem[:idx] + stem[idx + len(text):] if idx != -1 else stem
        else:
            new_stem = stem.replace(text, "")
        if new_stem == stem:
            continue

        new_stem = _clean(new_stem, tidy)
        if not new_stem:
            console.print(f"  [yellow]SKIP (name would be empty):[/yellow] {f.name}")
            skipped += 1
            continue

        target = f.with_name(new_stem + suffix)
        if target == f:
            continue
        key = str(target).lower()
        if target.exists() or key in seen:
            console.print(f"  [yellow]COLLISION (exists, skipped):[/yellow] {f.name}  ->  {target.name}")
            collisions += 1
            continue
        seen.add(key)

        console.print(f"  {f.name}\n    -> [b]{target.name}[/b]")
        planned += 1
        if apply:
            try:
                f.rename(target)
            except OSError as exc:
                console.print(f"    [red]FAILED:[/red] {exc}")

    verb = "RENAMED" if apply else "would rename (dry-run)"
    console.print(
        f"\n[bold]{planned}[/bold] file(s) {verb} | "
        f"{collisions} collision(s) skipped | {skipped} empty-name skipped"
    )
    if not apply and planned:
        console.print("[dim]Re-run with --apply to perform the rename.[/dim]")
    return 0
