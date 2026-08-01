"""`slimv analyze <path>` — inspect a video or a whole library and recommend
how to shrink it."""
from __future__ import annotations

import tempfile
from collections import Counter
from pathlib import Path

from . import ffmpeg
from .console import console, make_table
from .profiles import PROFILES
from .util import iter_videos, human_size, human_dur

# codecs considered "old / worth re-encoding to HEVC"
_OLD = {"h264", "mpeg4", "msmpeg4v3", "wmv3", "vp8", "flv1", "mpeg2video", "vc1"}
_MODERN = {"hevc", "av1", "vp9"}


def _measured_ratio(old_rows: list[dict], sample_length: int) -> tuple[float, str, int] | None:
    """Encode short samples of a bitrate-spread of the old-codec files and return
    (avg output/input size ratio, profile used, samples measured). This replaces
    the static 45–60% guess with a number measured on *this* content.

    The ratio is per-second output vs source bytes on the sampled segment; it's a
    projection aid, not a guarantee (a whole file varies), but it beats a constant.
    """
    for prof in ("qsv", "nvenc", "balanced"):
        if prof in PROFILES and ffmpeg.has_encoder(PROFILES[prof].codec):
            break
    else:
        return None
    p = PROFILES[prof]

    picks = [r for r in old_rows if r.get("path") and r["dur"] > sample_length]
    picks.sort(key=lambda r: r["mbps"])
    if not picks:
        return None
    n = min(5, len(picks))
    idxs = sorted({round(i * (len(picks) - 1) / (n - 1)) if n > 1 else 0 for i in range(n)})
    picks = [picks[i] for i in idxs]

    work = Path(tempfile.gettempdir()) / "slimv_analyze"
    work.mkdir(parents=True, exist_ok=True)
    clip = work / "sample.mp4"
    console.print(f"\n[cyan]Measuring[/cyan] {len(picks)} sample(s) with profile "
                  f"[b]{prof}[/b] ({sample_length}s each)…")

    ratios: list[float] = []
    for r in picks:
        start = max(0, int(r["dur"] / 2 - sample_length / 2))
        if clip.exists():
            clip.unlink()
        ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", str(start), "-t", str(sample_length), "-i", str(r["path"]),
                    *p.vargs, "-an", str(clip)])
        if not clip.exists() or clip.stat().st_size == 0:
            continue
        out_dur = ffmpeg.duration(clip) or sample_length
        out_bps = clip.stat().st_size * 8 / out_dur
        in_bps = r["mbps"] * 1e6
        if in_bps > 0:
            ratios.append(min(out_bps / in_bps, 1.0))
    if not ratios:
        return None
    return sum(ratios) / len(ratios), prof, len(ratios)


def run(path: str, measure: bool = False, sample_length: int = 30) -> int:
    ffmpeg.require_tools()
    files = iter_videos(path)
    if not files:
        console.print(f"[yellow]No video files found under[/yellow] {path}")
        return 1

    console.print(f"Scanning [b]{len(files)}[/b] file(s) under {path} ...")
    rows = []
    total_bytes = 0
    total_dur = 0.0
    for f in files:
        info = ffmpeg.probe(f)
        v = ffmpeg.video_stream(info) if info else None
        if not v:
            continue
        dur = float(info.get("format", {}).get("duration") or 0)
        br = float(info.get("format", {}).get("bit_rate") or 0)
        rows.append({
            "name": f.name,
            "path": f,
            "codec": v.get("codec_name", "?"),
            "res": f'{v.get("width","?")}x{v.get("height","?")}',
            "pix": v.get("pix_fmt", "?"),
            "dur": dur,
            "mbps": br / 1e6,
            "bytes": f.stat().st_size,
        })
        total_bytes += f.stat().st_size
        total_dur += dur

    if not rows:
        console.print("[yellow]Could not read any video streams.[/yellow]")
        return 1

    # summary
    console.print(
        f"\n[bold cyan]Total:[/bold cyan] {len(rows)} files, "
        f"{human_size(total_bytes)}, {human_dur(total_dur)}"
    )
    codecs = Counter(r["codec"] for r in rows)
    res = Counter(r["res"] for r in rows)
    avg_mbps = sum(r["mbps"] for r in rows) / len(rows)

    ct = make_table("By codec", ["Codec", "Files"])
    for c, n in codecs.most_common():
        ct.add_row(c, str(n))
    rt = make_table("By resolution", ["Resolution", "Files"])
    for c, n in res.most_common():
        rt.add_row(c, str(n))
    console.print(ct)
    console.print(rt)
    console.print(f"Average overall bitrate: [b]{avg_mbps:.2f} Mbps[/b]")

    # recommendation
    console.print("\n[bold cyan]Recommendation[/bold cyan]")
    n_modern = sum(1 for r in rows if r["codec"] in _MODERN)
    n_old = sum(1 for r in rows if r["codec"] in _OLD)
    if n_modern > len(rows) / 2:
        console.print(
            "  Most files are already HEVC/AV1/VP9 — re-encoding will save little. "
            "Leave as-is unless you need a different container/codec."
        )
    elif n_old:
        console.print(
            "  Mostly older codecs (H.264/MPEG-4). Re-encoding to H.265 should hold "
            "quality and cut size substantially."
        )
        old_rows = [r for r in rows if r["codec"] in _OLD]
        old_bytes = sum(r["bytes"] for r in old_rows)
        modern_bytes = total_bytes - old_bytes
        measured = _measured_ratio(old_rows, sample_length) if measure else None
        if measured:
            ratio, prof_used, n_meas = measured
            projected = old_bytes * ratio + modern_bytes
            saved = (1 - projected / total_bytes) * 100 if total_bytes else 0
            console.print(
                f"  [green]Measured[/green] on {n_meas} sample(s) via '{prof_used}': "
                f"projected output ~[b]{human_size(projected)}[/b] "
                f"(from {human_size(total_bytes)})  →  [b]~{saved:.0f}% smaller[/b]."
            )
            console.print(
                "  [dim](Measured on short samples of this content — a projection, "
                "not a guarantee; whole-file results vary.)[/dim]"
            )
        else:
            lo = total_bytes * 0.40
            hi = total_bytes * 0.55
            console.print(
                f"  Projected output: ~{human_size(lo)}–{human_size(hi)} "
                f"(from {human_size(total_bytes)})  →  ~45–60% smaller."
            )
            if not measure:
                console.print(
                    "  [dim]Add [b]--measure[/b] to sample-encode and project the real "
                    "saving on this content instead of this estimate.[/dim]"
                )
        if ffmpeg.has_encoder("hevc_qsv"):
            prof = "qsv"
            console.print("  Suggested profile: [green]qsv[/green] (fast Intel hardware; frees CPU/NVIDIA).")
        elif ffmpeg.has_encoder("hevc_nvenc"):
            prof = "nvenc"
            console.print("  Suggested profile: [green]nvenc[/green] (fast NVIDIA hardware).")
        else:
            prof = "balanced"
            console.print("  Suggested profile: [green]balanced[/green] (x265 CPU; smallest, slower).")
        p = Path(path)
        console.print(f'  Benchmark first:  [b]slimv benchmark "{files[0]}"[/b]')
        console.print(f'  Then encode:      [b]slimv encode "{p}" "{p}_slimv" --profile {prof}[/b]')

    # sample listing
    st = make_table("First 15 files", ["File", "Codec", "Res", "Pix", "Dur", "Mbps", "Size"])
    for r in rows[:15]:
        st.add_row(
            r["name"][:48], r["codec"], r["res"], r["pix"],
            human_dur(r["dur"]), f'{r["mbps"]:.2f}', human_size(r["bytes"]),
        )
    console.print(st)
    return 0
