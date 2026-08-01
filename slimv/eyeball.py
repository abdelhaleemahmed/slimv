"""`slimv eyeball <path>` — write side-by-side sample clips (the original plus
each candidate profile) to a folder so you can *watch* them and judge quality
directly.

VMAF under-reads sharp screen text and handwriting, so a number alone can't
settle a profile choice for that content. This command leaves real clips on
disk — the original segment and one encode per profile, same in/out point — so
the eye can be the referee. Nothing is scored; nothing is deleted.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import ffmpeg
from .console import console, make_table
from .profiles import BENCH_DEFAULT, PROFILES
from .util import human_dur, human_size, iter_videos


def _representative(path: str) -> Path | None:
    """The file to sample: the given file, or (for a folder) the largest video —
    usually a full-length lecture, the fairest quality test."""
    vids = iter_videos(path)
    if not vids:
        return None
    return max(vids, key=lambda p: p.stat().st_size)


def run(path: str, start: int = 60, length: int = 30,
        out: str | None = None, profiles: list[str] | None = None) -> int:
    ffmpeg.require_tools()
    src = _representative(path)
    if src is None:
        console.print(f"[yellow]No video files under[/yellow] {path}")
        return 1

    names = profiles or list(BENCH_DEFAULT)
    names = [n for n in names if n in PROFILES and ffmpeg.has_encoder(PROFILES[n].codec)]
    if not names:
        console.print("[red]None of the requested profiles' encoders are available.[/red]")
        return 1

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", src.stem)[:60] or "sample"
    out_dir = Path(out) if out else Path.cwd() / "slimv_eyeball" / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"Representative file: [b]{src.name}[/b]")
    console.print(f"Sample: [b]{human_dur(start)}[/b] for [b]{length}s[/b] "
                  f"(to {human_dur(start + length)})")
    console.print(f"Profiles: [b]{', '.join(names)}[/b]")
    console.print(f"Writing clips to: [b]{out_dir}[/b]\n")

    seg = ["-ss", str(start), "-t", str(length), "-i", str(src)]

    # The original segment, as-is (stream copy). If the cut point isn't on a
    # keyframe some containers yield an empty copy — fall back to a visually
    # lossless re-encode so the reference clip always exists.
    orig = out_dir / f"00_original{src.suffix.lower()}"
    ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *seg,
                "-c", "copy", str(orig)])
    if not orig.exists() or orig.stat().st_size == 0:
        # Lossless, native to ffmpeg (no external x264 needed). Rare path — only
        # when the cut point isn't on a keyframe so the stream copy came up empty.
        orig = out_dir / "00_original.mkv"
        ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *seg,
                    "-c:v", "ffv1", "-level", "3", "-an", str(orig)])

    rows: list[tuple[str, Path]] = [("00 original", orig)]
    for n in names:
        clip = out_dir / f"{n}.mp4"
        if clip.exists():
            clip.unlink()
        console.print(f"  encoding {n}…")
        console.file.flush()
        ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *seg,
                    *PROFILES[n].vargs, "-an", str(clip)])
        rows.append((n, clip))

    table = make_table("Eyeball clips — watch them against 00_original",
                       ["Clip", "Size"])
    for label, f in rows:
        table.add_row(label, human_size(f.stat().st_size) if f.exists() else "[red]FAILED[/red]")
    console.print()
    console.print(table)
    console.print(
        "\n[dim]Open the folder and compare each profile to 00_original — trust your "
        "eyes on text/handwriting, where VMAF is unreliable.[/dim]"
    )
    console.print(f"[b]{out_dir}[/b]")
    return 0
