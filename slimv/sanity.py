"""`slimv test <encoder>` — quick encode+decode sanity check for one encoder,
and report whether it ran on hardware or fell back to software."""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import ffmpeg
from .console import console


def run(encoder: str) -> int:
    ffmpeg.require_tools()
    if not ffmpeg.has_encoder(encoder):
        console.print(f"[red]Encoder '{encoder}' is not available in this ffmpeg.[/red]")
        console.print("Run [b]slimv hwcheck[/b] to see what's available.")
        return 1

    tmp = Path(tempfile.gettempdir()) / "slimv_test"
    tmp.mkdir(exist_ok=True)
    clip = tmp / "synthetic.mp4"
    out = tmp / f"enc_{encoder}.mp4"

    console.print("Generating a 5 s 1080p test clip…")
    ffmpeg.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30:duration=5",
        "-pix_fmt", "yuv420p", str(clip),
    ])

    console.print(f"Encoding with [b]{encoder}[/b] (verbose, to reveal hardware/software path)…")
    r = ffmpeg.run([
        "ffmpeg", "-hide_banner", "-v", "verbose", "-y", "-i", str(clip),
        "-c:v", encoder, "-t", "5", str(out),
    ], capture=True)
    log = (r.stderr or "") + (r.stdout or "")
    impl = ffmpeg.hardware_impl(log)
    if impl == "unknown" and encoder.startswith("lib"):
        impl = "software"  # lib* encoders (x264/x265/svtav1) are CPU by definition
    colour = {"hardware": "green", "software": "yellow", "unknown": "cyan"}[impl]
    console.print(f"  Implementation: [{colour}]{impl.upper()}[/{colour}]")
    for ln in log.splitlines():
        low = ln.lower()
        if any(k in low for k in ("hardware accelerated", "software implementation",
                                  "mfx", "nvenc", "qsv session", "d3d")):
            console.print(f"    [dim]{ln.strip()}[/dim]")

    if not out.exists():
        console.print("  [red]Encode produced no output.[/red]")
        return 1

    console.print("Decode test (reading every frame of the output)…")
    errs = ffmpeg.decode_errors(out)
    if errs == 0:
        console.print("  [green]DECODE OK — output is valid.[/green]")
    else:
        console.print(f"  [red]DECODE ERRORS: {errs} (output may be broken).[/red]")
    console.print(f"  Output size: {out.stat().st_size / 1024:.0f} KB")
    return 0 if errs == 0 else 2
