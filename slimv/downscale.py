"""`slimv downscale-test <file>` — measure the size *and* quality cost of
downscaling (e.g. 1080p → 720p) before committing to it.

slimv's profiles keep resolution by design. Downscaling can shrink a file
further, but it is lossy in a way VMAF-on-a-same-size-encode won't show. This
command makes the trade-off visible: it encodes a sample at native resolution
and at the target height, then scores the downscaled encode *fairly* — by
upscaling it back to native and running VMAF against the native lossless
reference, i.e. what a viewer on a native-resolution screen actually sees.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from . import ffmpeg
from .console import console, make_table
from .profiles import PROFILES
from .util import human_size


def run(file: str, start: int = 60, length: int = 30, scale: int = 720,
        profile: str = "qsv-hq", out: str | None = None) -> int:
    ffmpeg.require_tools()
    src = Path(file)
    if not src.exists():
        console.print(f"[red]File not found:[/red] {file}")
        return 1
    if profile not in PROFILES:
        console.print(f"[red]Unknown profile:[/red] {profile}")
        return 1
    p = PROFILES[profile]
    if not ffmpeg.has_encoder(p.codec):
        console.print(f"[red]Encoder for profile '{profile}' ({p.codec}) is not available.[/red]")
        return 1

    info = ffmpeg.probe(src)
    v = ffmpeg.video_stream(info) if info else None
    if not v:
        console.print("[red]Could not read a video stream.[/red]")
        return 1
    native_h = int(v.get("height") or 0)
    if scale >= native_h:
        console.print(
            f"[yellow]--scale {scale} is not smaller than the source height "
            f"{native_h}p — nothing to test.[/yellow]"
        )
        return 1
    full_dur = ffmpeg.duration(src) or 0.0

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", src.stem)[:60] or "sample"
    work = Path(out) if out else Path.cwd() / "slimv_downscale" / stem
    work.mkdir(parents=True, exist_ok=True)
    seg = ["-ss", str(start), "-t", str(length), "-i", str(src)]

    console.print(f"Native height: [b]{native_h}p[/b]   target: [b]{scale}p[/b]   "
                  f"profile: [b]{profile}[/b]   sample: [b]{length}s[/b] @ {start}s")
    console.print(f"Clips → [b]{work}[/b]\n")

    ref = work / "ref.mkv"
    console.print("Extracting a lossless reference at native resolution…")
    ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *seg,
                "-an", "-c:v", "ffv1", "-level", "3", str(ref)])
    ref_dur = ffmpeg.duration(ref) or float(length)

    console.print(f"Encoding native {native_h}p…")
    native = work / f"native_{native_h}p.mp4"
    ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(ref),
                *p.vargs, "-an", str(native)])

    console.print(f"Encoding downscaled {scale}p…")
    down = work / f"down_{scale}p.mp4"
    ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(ref),
                "-vf", f"scale=-2:{scale}", *p.vargs, "-an", str(down)])

    # Upscale the downscaled encode back to native for a fair VMAF comparison.
    # ffv1 (lossless, native to ffmpeg) keeps the reference exact without needing
    # an external x264/x265 build.
    up = work / f"down_{scale}p_upscaled_to_{native_h}p.mkv"
    ffmpeg.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(down),
                "-vf", f"scale=-2:{native_h}", "-c:v", "ffv1", "-level", "3",
                "-an", str(up)])

    has_vmaf = ffmpeg.has_libvmaf()
    v_native = ffmpeg.vmaf(native, ref) if has_vmaf else None
    v_down = ffmpeg.vmaf(up, ref) if has_vmaf else None

    def proj(sample_bytes: int) -> str:
        if ref_dur <= 0 or full_dur <= 0:
            return "n/a"
        return human_size(sample_bytes * (full_dur / ref_dur))

    nb = native.stat().st_size if native.exists() else 0
    db = down.stat().st_size if down.exists() else 0

    table = make_table(
        f"Downscale test — native {native_h}p vs {scale}p ({length}s sample, profile {profile})",
        ["Variant", "VMAF vs native", "Sample MB", "Proj. full size", "Δ size vs native"],
    )
    table.add_row(f"native {native_h}p",
                  "n/a" if v_native is None else f"{v_native:.2f}",
                  f"{nb / (1024 * 1024):.2f}", proj(nb), "—")
    dpct = (1 - db / nb) * 100 if nb else 0.0
    table.add_row(f"downscaled {scale}p",
                  "n/a" if v_down is None else f"{v_down:.2f}",
                  f"{db / (1024 * 1024):.2f}", proj(db), f"-{dpct:.0f}%")
    console.print(table)
    console.print(
        f"\n[dim]The {scale}p VMAF scores that encode upscaled back to {native_h}p — what a "
        f"viewer on a {native_h}p screen sees. Downscale only if that VMAF stays acceptable "
        f"AND the size win is worth it. Clips left in:[/dim]"
    )
    console.print(f"[b]{work}[/b]")
    return 0
