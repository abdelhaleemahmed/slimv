"""``slimv verify-report <dst>`` — a live progress report for a ``verify`` run.

Reads the verify report(s) a ``verify`` writes incrementally — the canonical
``_slimv_verify_report.csv`` plus any ``_verify*.csv`` shard files from a parallel
(sharded) run — and shows a house box: files verified / total, the file currently
being checked, verify speed, an ETA, and the safe / corrupted counts, with the
source + output paths.

``--list-corrupted`` skips the box and prints the **full path** of every file that
failed verification (KEEP-SOURCE — decode errors / length mismatch), so you can
act on them (re-encode, inspect, or delete a bad output). Read-only.
"""
from __future__ import annotations

import csv
import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Callable


def _shard_files(dst_root: Path) -> list[str]:
    """`_verify*.csv` in dst, glob-escaping the dir so a '[HEVC]' in the folder
    name isn't parsed as a character class (which would match nothing)."""
    return glob.glob(os.path.join(glob.escape(str(dst_root)), "_verify*.csv"))

from . import ffmpeg
from .console import console
from .report import _course_title, _dw, _f, _render_box, _remaining_seconds  # reuse
from .util import human_dur, iter_videos

_CANON = "_slimv_verify_report.csv"
_SAFE = "SAFE-TO-DELETE"


def _parse_when(s) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None


def _load_rows(dst_root: Path) -> dict[str, dict]:
    """All verify rows keyed by RelPath, gathered from the canonical report and any
    shard files (``_verify*.csv``). Prefer a decoded verdict over a stale/cached one:
    later files and non-cached rows win."""
    out: dict[str, dict] = {}
    paths = [dst_root / _CANON] + [Path(p) for p in _shard_files(dst_root)]
    for p in paths:
        if not p.exists():
            continue
        try:
            with p.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    rel = row.get("RelPath", "")
                    prev = out.get(rel)
                    # keep the freshest by When (a re-verify supersedes a cached row)
                    if prev is None or (_parse_when(row.get("When")) or datetime.min) >= \
                            (_parse_when(prev.get("When")) or datetime.min):
                        out[rel] = row
        except (OSError, csv.Error):
            continue
    return out


def build_verify_report(dst: str, src: str | None = None,
                        duration_fn: Callable[[Path], float | None] | None = None,
                        now: datetime | None = None):
    """Return (title, box_rows, meta, corrupted). Pure/read-only."""
    duration_fn = duration_fn or ffmpeg.duration
    now = now or datetime.now()
    dst_root = Path(dst)
    rows = _load_rows(dst_root)

    verified = len(rows)
    corrupted = [r for r in rows.values() if r.get("Verdict") != _SAFE]
    safe = verified - len(corrupted)

    # Total + which files remain — from the source tree if given, else the log.
    total = verified
    src_path: Path | None = None
    remaining_files: list[Path] = []
    if src:
        src_path = Path(src)
        files = iter_videos(src_path)
        total = len(files)
        done_rels = set(rows.keys())
        remaining_files = [f for f in files if str(f.relative_to(src_path)) not in done_rels]

    # Speed: aggregate over the verify's wall span, from the row timestamps + SrcDur.
    whens = [w for w in (_parse_when(r.get("When")) for r in rows.values()) if w]
    verified_secs = sum(_f(r.get("SrcDur")) for r in rows.values())
    elapsed = (max(whens) - min(whens)).total_seconds() if len(whens) >= 2 else 0.0
    xrt = (verified_secs / elapsed) if elapsed else None
    fpm = (verified / (elapsed / 60)) if elapsed else None

    # ETA: real remaining durations (probed) over the measured verify speed.
    in_progress = verified < total
    eta = None
    if in_progress and xrt and remaining_files:
        secs_per_file = (verified_secs / verified) if verified else 0.0
        # size fallback only for an unreadable file; secs_per_mb from what we know
        secs_per_mb = 0.0  # ETA leans on real durations here
        remaining_secs = _remaining_seconds(remaining_files, duration_fn, secs_per_mb)
        if remaining_secs <= 0:      # every probe failed -> fall back to a per-file avg
            remaining_secs = len(remaining_files) * secs_per_file
        eta = remaining_secs / xrt

    # Current / next file being verified (first unverified in source order).
    current = "— (complete)" if not in_progress else (
        str(remaining_files[0].relative_to(src_path)) if remaining_files else "…")

    t = "~" if in_progress else ""
    box: list[tuple[str, str]] = [
        ("Verified", f"{verified} / {total} ✅"),
        ("Current", current),
    ]
    if xrt is not None:
        box.append(("Speed", f"{fpm:.1f} files/min · {xrt:.1f}× realtime"))
    if eta is not None:
        box.append(("ETA", f"~{human_dur(eta)}"))
    box.append(("Safe", f"{safe}"))
    box.append(("Corrupted", f"{len(corrupted)}" + ("  ← KEEP-SOURCE (see --list-corrupted)" if corrupted else "")))
    if src_path is not None:
        box.append(("Source", str(src_path)))
    box.append(("Output", str(dst_root)))

    meta = {"verified": verified, "total": total, "safe": safe,
            "corrupted": len(corrupted), "xrt": xrt, "fpm": fpm, "eta": eta,
            "in_progress": in_progress}
    return (_course_title(dst_root) + " — verify"), box, meta, corrupted


def run(dst: str, src: str | None = None, list_corrupted: bool = False) -> int:
    dst_root = Path(dst)
    if not (dst_root / _CANON).exists() and not _shard_files(dst_root):
        console.print(f"[red]No verify report in {dst_root}[/red] — run [b]slimv verify[/b] first.")
        return 1
    title, box, meta, corrupted = build_verify_report(dst, src=src)

    if list_corrupted:
        if not corrupted:
            console.print("[green]No corrupted files — every verified output passed.[/green]")
            return 0
        # Full path: the SOURCE path when --src is given (to re-encode/inspect the
        # original), otherwise the output path.
        root = Path(src) if src else dst_root
        console.print(f"[yellow]{len(corrupted)} corrupted file(s):[/yellow]")
        for r in corrupted:
            rel = r.get("RelPath", "")
            full = root / rel
            reason = r.get("Reason", "")
            print(f"{full}\t({reason})")
        return 2

    for line in _render_box(title, box):
        print(line)
    if meta["corrupted"]:
        console.print(f"[yellow]→ {meta['corrupted']} corrupted; "
                      f"run with [b]--list-corrupted[/b] for full paths.[/yellow]")
    return 0
