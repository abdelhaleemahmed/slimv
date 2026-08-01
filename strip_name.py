#!/usr/bin/env python3
"""
strip_name.py — bulk-remove a piece of text from filenames, keep the rest.

DRY-RUN BY DEFAULT: it only shows what it *would* do. Add --apply to rename.

Examples
--------
  # Preview: remove "[TutsNode.com] - " from every file in a folder
  python strip_name.py "D:\\Courses\\MyCourse" "[TutsNode.com] - "

  # Actually do it, including sub-folders
  python strip_name.py "D:\\Courses\\MyCourse" "[TutsNode.com] - " --recursive --apply

  # Only .mp4 files, case-insensitive match, tidy leftover spaces/dashes
  python strip_name.py "D:\\Courses" "SomeName" --ext .mp4 --ignore-case --tidy --apply
"""
import argparse
import sys
from pathlib import Path


def clean(stem: str, tidy: bool) -> str:
    """Optionally tidy leftover separators after the text is removed."""
    if not tidy:
        return stem
    # collapse repeated spaces, strip stray leading/trailing separators
    while "  " in stem:
        stem = stem.replace("  ", " ")
    return stem.strip(" -_.")


def main() -> int:
    p = argparse.ArgumentParser(description="Remove a text fragment from filenames.")
    p.add_argument("folder", help="Folder to scan")
    p.add_argument("text", help="The exact text to remove from each filename")
    p.add_argument("-r", "--recursive", action="store_true", help="Include sub-folders")
    p.add_argument("--ext", action="append", default=[],
                   help="Only touch these extensions (repeatable), e.g. --ext .mp4 --ext .mkv")
    p.add_argument("--ignore-case", action="store_true", help="Match the text case-insensitively")
    p.add_argument("--tidy", action="store_true",
                   help="Collapse double spaces and trim stray -_. left behind")
    p.add_argument("--apply", action="store_true", help="Actually rename (default: dry-run)")
    args = p.parse_args()

    root = Path(args.folder)
    if not root.is_dir():
        print(f"ERROR: not a folder: {root}")
        return 2

    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in args.ext}
    files = (root.rglob("*") if args.recursive else root.glob("*"))

    planned, skipped, collisions = 0, 0, 0
    seen_targets: set[str] = set()

    for f in sorted(files):
        if not f.is_file():
            continue
        if exts and f.suffix.lower() not in exts:
            continue

        # only rename the stem; never touch the extension
        stem, suffix = f.stem, f.suffix
        if args.ignore_case:
            idx = stem.lower().find(args.text.lower())
            new_stem = (stem[:idx] + stem[idx + len(args.text):]) if idx != -1 else stem
        else:
            new_stem = stem.replace(args.text, "")

        if new_stem == stem:
            continue  # text not present -> leave untouched

        new_stem = clean(new_stem, args.tidy)
        if not new_stem:
            print(f"  SKIP (name would be empty): {f.name}")
            skipped += 1
            continue

        target = f.with_name(new_stem + suffix)
        if target == f:
            continue

        key = str(target).lower()
        if target.exists() or key in seen_targets:
            print(f"  COLLISION (exists, skipped): {f.name}  ->  {target.name}")
            collisions += 1
            continue
        seen_targets.add(key)

        print(f"  {f.name}\n    -> {target.name}")
        planned += 1
        if args.apply:
            try:
                f.rename(target)
            except OSError as e:
                print(f"    FAILED: {e}")

    mode = "RENAMED" if args.apply else "would rename (dry-run)"
    print(f"\n{planned} file(s) {mode} | {collisions} collision(s) skipped | {skipped} empty-name skipped")
    if not args.apply and planned:
        print("Re-run with --apply to perform the rename.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
