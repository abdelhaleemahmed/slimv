"""`slimv check <path>` — health scan of a file or folder: report each file's
codec, find corrupted/unreadable files, and print summary stats.

Unlike :mod:`slimv.verify` (which compares a source tree against a converted
tree), ``check`` inspects a single location on its own. Unlike
:mod:`slimv.analyze` (stats + a re-encode recommendation), ``check`` adds a
full-decode integrity pass so it can flag broken files.
"""
from __future__ import annotations

from collections import Counter

from . import ffmpeg
from .console import console, make_table
from .util import iter_videos, human_size, human_dur


def run(path: str, quick: bool = False, list_all: bool = False) -> int:
    """Scan ``path`` (a file or folder) and report codecs, corruption, and stats.

    Args:
        path: A video file, or a folder searched recursively.
        quick: If True, skip the full-decode integrity pass (ffprobe only —
            fast, but only catches files that are unreadable at the header).
        list_all: If True, print a row for every file, not just problems.

    Returns:
        0 if every file is healthy, 2 if any file is corrupt/unreadable.
    """
    ffmpeg.require_tools()
    files = iter_videos(path)
    if not files:
        console.print(f"[yellow]No video files found under[/yellow] {path}")
        return 1

    mode = "ffprobe only (quick)" if quick else "full decode"
    console.print(f"Scanning [b]{len(files)}[/b] file(s) under {path}  [dim](integrity: {mode})[/dim]")

    rows = []
    problems = []
    total_bytes = 0
    total_dur = 0.0
    codecs = Counter()
    resolutions = Counter()

    total = len(files)
    for i, f in enumerate(files, 1):
        if not quick:
            console.print(f"[dim][{i}/{total}] checking {f.name[:50]}[/dim]")
            console.file.flush()
        info = ffmpeg.probe(f)
        v = ffmpeg.video_stream(info) if info else None
        size = f.stat().st_size
        total_bytes += size

        if not v:
            # ffprobe could not read a video stream -> treat as corrupt/unreadable
            problems.append((f, "unreadable (no video stream)"))
            rows.append({"name": f.name, "codec": "?", "res": "?", "size": size,
                         "status": "UNREADABLE"})
            continue

        codec = v.get("codec_name", "?")
        res = f'{v.get("width","?")}x{v.get("height","?")}'
        dur = float((info.get("format") or {}).get("duration") or 0)
        codecs[codec] += 1
        resolutions[res] += 1
        total_dur += dur

        status = "OK"
        if not quick:
            errs = ffmpeg.decode_errors(f)
            if errs > 0:
                status = f"CORRUPT ({errs} decode errors)"
                problems.append((f, status))
        rows.append({"name": f.name, "codec": codec, "res": res, "size": size,
                     "status": status})

    # -- summary ------------------------------------------------------------
    healthy = sum(1 for r in rows if r["status"] == "OK")
    console.print(
        f"\n[bold cyan]Totals[/bold cyan]: {len(rows)} files, "
        f"{human_size(total_bytes)}, {human_dur(total_dur)}"
    )
    if codecs:
        ct = make_table("By codec", ["Codec", "Files"])
        for c, n in codecs.most_common():
            ct.add_row(c, str(n))
        console.print(ct)
    if resolutions:
        rt = make_table("By resolution", ["Resolution", "Files"])
        for c, n in resolutions.most_common():
            rt.add_row(c, str(n))
        console.print(rt)

    # -- health -------------------------------------------------------------
    console.print(
        f"\n[bold cyan]Health[/bold cyan]: "
        f"[green]{healthy} healthy[/green]"
        + (f", [red]{len(problems)} corrupt/unreadable[/red]" if problems else ", [green]0 problems[/green]")
        + ("" if not quick else "  [dim](quick mode: header check only)[/dim]")
    )
    if problems:
        console.print("[red]Problem files:[/red]")
        for f, reason in problems:
            console.print(f"  [red]✗[/red] {f}  [dim]({reason})[/dim]")

    # -- optional full listing ---------------------------------------------
    if list_all or len(rows) <= 40:
        tbl = make_table("Files", ["File", "Codec", "Res", "Size", "Status"])
        for r in rows:
            colour = "green" if r["status"] == "OK" else "red"
            tbl.add_row(r["name"][:48], r["codec"], r["res"],
                        human_size(r["size"]), f'[{colour}]{r["status"]}[/{colour}]')
        console.print(tbl)
    else:
        console.print(f"[dim](Run with --list to see all {len(rows)} files.)[/dim]")

    return 0 if not problems else 2
