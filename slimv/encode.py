"""`slimv encode <src> <dst> --profile <name>` — batch re-encode a tree into a
mirrored output tree, verifying and logging every file. Resumable: files whose
output already exists are skipped."""
from __future__ import annotations

import csv
import datetime as _dt
import shutil
from pathlib import Path

from . import ffmpeg
from .console import console
from .profiles import PROFILES, apply_overrides
from .util import iter_videos, output_path_for

_LOG_HEADER = ["When", "RelPath", "Profile", "SrcMB", "OutMB", "Reduct%",
               "SrcDur", "OutDur", "Delta", "Status"]


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _verdict(src_dur, out_dur, tol=1.0):
    if out_dur is None:
        return "OUT-UNREADABLE", ""
    if src_dur is None:
        return "OK", ""
    delta = round(out_dur - src_dur, 2)
    ad = abs(delta)
    status = "OK" if ad <= tol else ("WARN-dur" if ad <= 3 else "MISMATCH-dur")
    return status, delta


def _decode_args(hwdec: str | None) -> list[str]:
    """Input (decode) hwaccel args, inserted before -i. Moves the source decode off
    the CPU onto a GPU so the CPU stays free for other work. For 'qsv' we keep frames
    GPU-resident (`-hwaccel_output_format qsv`) for a full decode→encode iGPU pipeline
    and size the hardware frame pool with `-extra_hw_frames 24` — the sweet spot on a
    Gen9 iGPU (smaller pools starve the pipeline; much larger ones exhaust iGPU memory)."""
    if not hwdec:
        return []
    if hwdec == "qsv":
        return ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv", "-extra_hw_frames", "24"]
    return ["-hwaccel", hwdec]


def run(src: str, dst: str, profile: str, skip: int = 0, limit: int | None = None,
        audio_kbps: int = 128, keep_smaller: bool = False,
        gq: int | None = None, crf: int | None = None, cq: int | None = None,
        preset: str | None = None, scale: int | None = None,
        hwdec: str | None = None, copy_audio: bool = False) -> int:
    ffmpeg.require_tools()
    if profile not in PROFILES:
        console.print(f"[red]Unknown profile '{profile}'.[/red] Run [b]slimv profiles[/b].")
        return 1
    p = PROFILES[profile]
    if not ffmpeg.has_encoder(p.codec):
        console.print(f"[red]Profile '{profile}' needs encoder '{p.codec}', not available here.[/red]")
        return 1
    # apply any ad-hoc CLI overrides (--gq/--crf/--preset/--scale)
    p, _warn = apply_overrides(p, gq=gq, crf=crf, cq=cq, preset=preset, scale=scale)
    for w in _warn:
        console.print(f"[yellow]warning: {w}[/yellow]")
    in_args = _decode_args(hwdec)
    if in_args:
        console.print(f"[dim]decode on {hwdec} (CPU-free): {' '.join(in_args)}[/dim]")

    root = Path(src).resolve()
    dst_root = Path(dst).resolve()
    dst_root.mkdir(parents=True, exist_ok=True)
    log = dst_root / "_slimv_encode_log.csv"
    if not log.exists():
        with log.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(_LOG_HEADER)

    files = iter_videos(root)
    batch = files[skip: (skip + limit) if limit else None]
    console.print(
        f"[cyan]Encoding {len(batch)} of {len(files)} file(s) with profile "
        f"'[b]{profile}[/b]' ({' '.join(p.vargs)})[/cyan]\n"
    )

    idx = skip
    for f in batch:
        idx += 1
        rel = f.relative_to(root)
        out = output_path_for(f, root, dst_root)
        out.parent.mkdir(parents=True, exist_ok=True)
        # where the original would be copied if it turns out smaller (keeps its
        # own extension so a kept .mkv stays .mkv)
        kept = out.with_suffix(f.suffix)
        src_mb = f.stat().st_size / (1024 * 1024)
        console.print(f"[yellow][{idx}/{len(files)}] {rel} ({src_mb:.1f} MB)[/yellow]")
        if out.exists() or (keep_smaller and kept.exists()):
            console.print("   [dim]output exists, skipping[/dim]")
            continue

        tmp = out.with_suffix(out.suffix + ".partial.mp4")
        if tmp.exists():
            tmp.unlink()
        # Audio: copy the source stream verbatim (no CPU, no quality loss) when asked —
        # right when the source is already AAC at a fine bitrate, so re-encoding it to
        # AAC would only waste CPU and add a lossy generation for zero benefit.
        audio_args = ["-c:a", "copy"] if copy_audio else ["-c:a", "aac", "-b:a", f"{audio_kbps}k"]
        r = ffmpeg.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
            *in_args, "-i", str(f), *p.vargs,
            *audio_args, "-movflags", "+faststart",
            str(tmp),
        ])
        if r.returncode != 0 or not tmp.exists():
            console.print("   [red]ENCODE-FAIL[/red]")
            if tmp.exists():
                tmp.unlink()
            _append(log, [_now(), str(rel), profile, f"{src_mb:.1f}", "", "", "", "", "", "ENCODE-FAIL"])
            continue

        sd = ffmpeg.duration(f)
        od = ffmpeg.duration(tmp)
        status, delta = _verdict(sd, od)
        if status == "OUT-UNREADABLE":
            tmp.unlink()
            console.print("   [red]OUT-UNREADABLE[/red]")
            _append(log, [_now(), str(rel), profile, f"{src_mb:.1f}", "", "", sd, "", "", status])
            continue

        tmp_mb = tmp.stat().st_size / (1024 * 1024)
        # keep-smaller: if the re-encode isn't actually smaller, keep the original
        if keep_smaller and tmp_mb >= src_mb:
            tmp.unlink()
            shutil.copy2(f, kept)
            console.print(f"   [blue]→ kept original {src_mb:.1f} MB "
                          f"(re-encode was {tmp_mb:.1f} MB, not smaller)[/blue]")
            _append(log, [_now(), str(rel), profile, f"{src_mb:.1f}", f"{src_mb:.1f}",
                          0, sd, sd, 0, "KEPT-ORIGINAL"])
            continue

        tmp.replace(out)
        out_mb = out.stat().st_size / (1024 * 1024)
        red = round((1 - out_mb / src_mb) * 100) if src_mb else 0
        colour = "green" if status == "OK" else "magenta"
        console.print(f"   [{colour}]→ {out_mb:.1f} MB ({red}% smaller) Δ={delta}s [{status}][/{colour}]")
        _append(log, [_now(), str(rel), profile, f"{src_mb:.1f}", f"{out_mb:.1f}",
                      red, sd, od, delta, status])

    console.print(f"\n[cyan]Done. Log: {log}[/cyan]")
    return 0


def _append(log: Path, row: list) -> None:
    with log.open("a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(row)
