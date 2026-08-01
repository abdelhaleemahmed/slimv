"""`slimv benchmark <file>` — encode a short sample with several profiles and
score each with VMAF, so you can pick quality-vs-size on your own content.

Method: extract a LOSSLESS reference segment (ffv1), encode that with each
profile, then VMAF each output against the lossless reference. Encoding from the
same reference guarantees frame-perfect alignment, so the VMAF numbers are
trustworthy (no spurious low scores from drift).

The measurement engine (:func:`measure`) is shared with
:mod:`slimv.recommend`, which adds an automatic decision on top of the same
numbers."""
from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from . import ffmpeg
from .console import console, make_table
from .profiles import PROFILES, BENCH_DEFAULT


@dataclass
class Result:
    """One profile's measured outcome on the benchmark sample."""
    profile: str
    vmaf: float | None
    size_mb: float
    speed_xrt: float
    hardware: bool


def measure(file: str, start: int = 60, length: int = 30,
            candidates: list[str] | None = None) -> list[Result]:
    """Encode a lossless sample of ``file`` with each candidate profile and
    measure VMAF, size, and speed.

    Args:
        file: A representative source video.
        start: Sample start, in seconds.
        length: Sample length, in seconds.
        candidates: Profile names to test. Defaults to the available subset of
            :data:`slimv.profiles.BENCH_DEFAULT`.

    Returns:
        A list of :class:`Result`, one per profile that encoded successfully.

    Raises:
        FileNotFoundError: If ``file`` does not exist.
        RuntimeError: If no candidate profile's encoder is available.
    """
    ffmpeg.require_tools()
    src = Path(file)
    if not src.exists():
        raise FileNotFoundError(file)
    has_vmaf = ffmpeg.has_libvmaf()

    # Per-input subdir so samples from different files don't overwrite each other.
    import re
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", src.stem)[:60] or "sample"
    work = Path(tempfile.gettempdir()) / "slimv_bench" / stem
    work.mkdir(parents=True, exist_ok=True)
    ref = work / "ref.mkv"
    console.print(f"Extracting a {length}s lossless reference (frame-exact VMAF)…")
    ffmpeg.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(start), "-t", str(length), "-i", str(src),
        "-an", "-c:v", "ffv1", "-level", "3", str(ref),
    ])
    ref_dur = ffmpeg.duration(ref) or float(length)

    names = candidates or BENCH_DEFAULT
    names = [p for p in names if ffmpeg.has_encoder(PROFILES[p].codec)]
    if not names:
        raise RuntimeError("none of the requested profiles' encoders are available")
    console.print(f"Testing: [b]{', '.join(names)}[/b]\n")

    results: list[Result] = []
    for name in names:
        p = PROFILES[name]
        out = work / f"{name}.mp4"
        if out.exists():
            out.unlink()
        console.print(f"  encoding {name}…")
        console.file.flush()
        t0 = time.perf_counter()
        ffmpeg.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(ref),
            *p.vargs, "-an", str(out),
        ])
        elapsed = max(time.perf_counter() - t0, 0.001)
        mb = out.stat().st_size / (1024 * 1024)
        xrt = ref_dur / elapsed
        score = ffmpeg.vmaf(out, ref) if has_vmaf else None
        results.append(Result(name, score, mb, xrt, p.hardware))
    return results


def results_table(results: list[Result], length: int) -> make_table:
    """Build a rich table of measured results, smallest first."""
    table = make_table(
        f"Benchmark ({length}s sample) — smallest first",
        ["Profile", "VMAF", "Size (MB)", "Speed ×RT", "HW"],
    )
    for r in sorted(results, key=lambda x: x.size_mb):
        table.add_row(
            r.profile,
            "n/a" if r.vmaf is None else f"{r.vmaf:.2f}",
            f"{r.size_mb:.2f}",
            f"{r.speed_xrt:.2f}",
            "yes" if r.hardware else "no",
        )
    return table


def run(file: str, start: int = 60, length: int = 30) -> int:
    try:
        results = measure(file, start=start, length=length)
    except FileNotFoundError:
        console.print(f"[red]File not found:[/red] {file}")
        return 1
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if not ffmpeg.has_libvmaf():
        console.print("[yellow]libvmaf not in this ffmpeg — sizes/speeds only, no quality score.[/yellow]")
    console.print(results_table(results, length))
    console.print(
        "[dim]Rule: among profiles whose quality is acceptable, pick the smallest.\n"
        "VMAF ~95+ = transparent for natural video; for screen/text content it reads\n"
        "lower (~92 = transparent in practice) — also eyeball one clip to be sure.\n"
        "Run [b]slimv recommend[/b] to have slimv pick the winner automatically.[/dim]"
    )
    return 0
