"""`slimv hwcheck` — what encoders/GPUs are available and how to confirm a
hardware encoder is genuinely being used."""
from __future__ import annotations

import platform
import shutil

from . import ffmpeg
from .console import console, make_table
from .profiles import PROFILES

# encoders we probe for, with friendly descriptions
_ENCODERS = [
    ("libx265",   "H.265 CPU (x265) — best quality per byte"),
    ("hevc_qsv",  "H.265 Intel Quick Sync (iGPU hardware)"),
    ("hevc_nvenc", "H.265 NVIDIA NVENC (GPU hardware)"),
    ("hevc_amf",  "H.265 AMD AMF (GPU hardware)"),
    ("libx264",   "H.264 CPU (x264)"),
    ("h264_qsv",  "H.264 Intel Quick Sync"),
    ("h264_nvenc", "H.264 NVIDIA NVENC"),
    ("libsvtav1", "AV1 CPU (SVT-AV1) — maximum compression"),
    ("av1_qsv",   "AV1 Intel Quick Sync"),
    ("av1_nvenc", "AV1 NVIDIA NVENC"),
]


def list_gpus() -> list[str]:
    sysname = platform.system()
    try:
        if sysname == "Windows":
            r = ffmpeg.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_VideoController | "
                 "Select-Object -ExpandProperty Name"],
                capture=True,
            )
            return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        if sysname == "Linux":
            r = ffmpeg.run(["bash", "-c", "lspci | grep -iE 'vga|3d|display'"], capture=True)
            return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        if sysname == "Darwin":
            r = ffmpeg.run(["system_profiler", "SPDisplaysDataType"], capture=True)
            return [ln.split(":", 1)[1].strip()
                    for ln in (r.stdout or "").splitlines() if "Chipset Model" in ln]
    except Exception:
        pass
    return []


def nvidia_status() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    r = ffmpeg.run(
        ["nvidia-smi", "--query-gpu=name,memory.used,memory.free,utilization.gpu",
         "--format=csv,noheader"],
        capture=True,
    )
    return (r.stdout or "").strip() or None


def run() -> int:
    ffmpeg.require_tools()

    console.print("\n[bold cyan]GPUs[/bold cyan]")
    gpus = list_gpus()
    if gpus:
        for g in gpus:
            console.print(f"  • {g}")
    else:
        console.print("  (could not enumerate; ffmpeg encoders below still apply)")
    nv = nvidia_status()
    if nv:
        console.print(f"  [dim]NVIDIA live:[/dim] {nv}")

    table = make_table("Encoders available in this ffmpeg", ["", "Encoder", "Description"])
    for name, desc in _ENCODERS:
        ok = ffmpeg.has_encoder(name)
        table.add_row(
            "[green]yes[/green]" if ok else "[dim]no[/dim]",
            f"[green]{name}[/green]" if ok else f"[dim]{name}[/dim]",
            desc if ok else f"[dim]{desc}[/dim]",
        )
    console.print(table)

    console.print("\n[bold cyan]Recommendation[/bold cyan]")
    if ffmpeg.has_encoder("hevc_qsv"):
        console.print("  • [green]qsv[/green] — Intel Quick Sync present: fast, frees CPU + NVIDIA. Recommended.")
    if ffmpeg.has_encoder("hevc_nvenc"):
        console.print("  • [green]nvenc[/green] — NVIDIA present: fastest for big batches (use when the card is idle).")
    if ffmpeg.has_encoder("libx265"):
        console.print("  • [green]balanced / quality / archive[/green] — x265 CPU: smallest files, slower.")
    if ffmpeg.has_encoder("libsvtav1"):
        console.print("  • [green]av1[/green] — maximum compression (slow encode, newer playback).")

    console.print("\n[bold cyan]Confirming a HARDWARE encoder is REALLY used[/bold cyan]")
    console.print(
        "  GPU utilization graphs lie for some paths (esp. Intel QSV on older iGPUs).\n"
        "  Trust these instead:\n"
        "    1) [b]slimv test <encoder>[/b]  → reads ffmpeg's 'hardware accelerated implementation'\n"
        "    2) ffmpeg.exe at ~0% CPU while the output file keeps growing\n"
        "    3) GPU-Z / HWiNFO 'Video Engine Load' sensor (reads the driver directly)\n"
        "  See section 8B of the guide for the full explanation."
    )
    return 0
