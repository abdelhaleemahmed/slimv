"""Thin wrapper around ffmpeg/ffprobe. slimv never encodes itself — it builds
command lines and lets ffmpeg do the work, then parses the results."""
from __future__ import annotations

import functools
import json
import re
import shutil
import subprocess
from pathlib import Path


class ToolError(RuntimeError):
    pass


def find_tool(name: str) -> str | None:
    return shutil.which(name)


def require_tools() -> None:
    missing = [t for t in ("ffmpeg", "ffprobe") if not find_tool(t)]
    if missing:
        raise ToolError(
            f"Required tool(s) not on PATH: {', '.join(missing)}. "
            "Install ffmpeg and ensure ffmpeg/ffprobe are callable."
        )


def run(args: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command. With capture=True, stdout/stderr are returned as text."""
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


# --- ffprobe ---------------------------------------------------------------

def probe(path: str | Path) -> dict | None:
    """Full ffprobe JSON (format + streams) or None on failure."""
    args = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,bit_rate:stream=index,codec_type,codec_name,profile,"
        "width,height,r_frame_rate,bit_rate,pix_fmt,sample_rate,channels",
        "-of", "json", "--", str(path),
    ]
    r = run(args, capture=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def duration(path: str | Path) -> float | None:
    r = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", "--", str(path)],
        capture=True,
    )
    s = (r.stdout or "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def frame_count(path: str | Path, exact: bool = False) -> int | None:
    """Video frame count. Default reads container metadata (`nb_frames`) — fast, no
    decode — but that metadata can be *bogus* (some sources inflate it, claiming more
    frames/duration than the file actually holds). Pass exact=True to *decode* and
    count real frames (`nb_read_frames` via -count_frames) — authoritative but slow.
    verify uses the fast path first and falls back to exact only when needed. Returns
    None when unavailable."""
    key = "nb_read_frames" if exact else "nb_frames"
    args = ["ffprobe", "-v", "error", "-select_streams", "v:0"]
    if exact:
        args.append("-count_frames")
    args += ["-show_entries", f"stream={key}", "-of", "csv=p=0", "--", str(path)]
    r = run(args, capture=True)
    s = (r.stdout or "").strip()
    try:
        return int(s)
    except ValueError:
        return None


def video_stream(info: dict) -> dict | None:
    """First video stream from a probe() result."""
    if not info:
        return None
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    # fallback: ffprobe was called with select_streams elsewhere
    return info.get("streams", [{}])[0] if info.get("streams") else None


# --- capability queries (cached) -------------------------------------------

@functools.lru_cache(maxsize=1)
def _encoders_text() -> str:
    return run(["ffmpeg", "-hide_banner", "-encoders"], capture=True).stdout or ""


def has_encoder(name: str) -> bool:
    return re.search(rf"(?m)^\s*\S*\s+{re.escape(name)}\b", _encoders_text()) is not None


@functools.lru_cache(maxsize=1)
def _filters_text() -> str:
    return run(["ffmpeg", "-hide_banner", "-filters"], capture=True).stdout or ""


def has_libvmaf() -> bool:
    return "libvmaf" in _filters_text()


# --- quality measurement ---------------------------------------------------

def vmaf(distorted: str | Path, reference: str | Path, threads: int = 8) -> float | None:
    """VMAF mean of `distorted` vs `reference`. Reads the score from ffmpeg's
    stderr (no log file) to dodge Windows path-escaping issues in the filtergraph.
    For a trustworthy number the two inputs must be frame-aligned (see benchmark,
    which encodes from a lossless reference)."""
    args = [
        "ffmpeg", "-hide_banner", "-i", str(distorted), "-i", str(reference),
        "-lavfi", f"[0:v][1:v]libvmaf=n_threads={threads}", "-f", "null", "-",
    ]
    r = run(args, capture=True)
    blob = (r.stderr or "") + (r.stdout or "")
    m = re.search(r"VMAF score:\s*([0-9.]+)", blob)
    return round(float(m.group(1)), 2) if m else None


# Muxer timestamp grumbles that are NOT decode/corruption errors. A non-monotonic
# DTS means two packets shared a decode time (common with sloppy .flv/.avi source
# timestamps); ffmpeg nudges it forward and the pictures are intact. These lines
# come from the muxer, not the decoder, so they must not count as integrity
# failures. Matches both ffmpeg phrasings: "non monotonically increasing dts"
# and the older "Non-monotonous DTS".
_BENIGN_MUX_RE = re.compile(r"monoton.*dts|dts.*monoton", re.IGNORECASE)

# Audio-decoder complaints to ignore in the (video-only) integrity gate. With
# --copy-audio the audio stream is copied verbatim from the source, so any AAC/MP3/
# AC3 quirk the source has reappears in the output and is NOT an encode fault. Matches
# the decoder tag (e.g. "[aac @ 0x..]") or the specific AAC SBR complaint we've seen.
_AUDIO_ERR_RE = re.compile(
    r"\[(aac|mp3(float)?|ac3|eac3|dca|opus|vorbis|flac|pcm)[^\]]*@|env_facs_q",
    re.IGNORECASE)

# ffmpeg collapses a repeated line into a trailing "Last message repeated N times".
# It carries no error of its own — it inherits the (already-classified) line above it.
# Left uncounted this inflated the tally whenever a *benign* line (e.g. a DTS warning)
# repeated. A genuine error still registers via its own first occurrence, so dropping
# these is safe for a >0 gate.
_REPEAT_RE = re.compile(r"Last message repeated", re.IGNORECASE)


def decode_errors(path: str | Path, hwaccel: str | None = None) -> int:
    """Full-decode integrity check on the **video stream**. Returns the number of
    *real* video decode/corruption error lines ffmpeg emits while reading every
    frame; 0 == clean.

    Scope is deliberately video-only (`-an`): this gate exists to catch a corrupted
    *video* re-encode (e.g. a hardware-decoder early-bail truncation). Audio is not
    re-encoded when `--copy-audio` is used — it's a byte-for-byte copy of the source,
    so any AAC quirk the source carries (e.g. `env_facs_q 255 is invalid`) is
    reproduced verbatim in the output and must NOT be counted as an encode error.
    Counting copied-through audio complaints caused spurious KEEP-SOURCE verdicts
    (Precalc 3/4, English B2). Two filters make this robust: `-an` skips audio decode
    entirely, and `_AUDIO_ERR_RE` drops any audio-decoder line that still leaks
    through. Benign muxer timestamp warnings (non-monotonic DTS) are filtered too.

    hwaccel: optional decode backend (e.g. 'qsv' = Intel iGPU, 'cuda' = NVIDIA,
    'd3d11va'/'dxva2'). Hardware decode is far faster (qsv ~4x vs CPU here) but a
    hardware decoder can report/conceal corruption differently than software, so
    CPU (hwaccel=None) stays the safest default for the deletion gate."""
    args = ["ffmpeg"]
    if hwaccel:
        args += ["-hwaccel", hwaccel]
    args += ["-v", "error", "-i", str(path), "-an", "-f", "null", "-"]
    r = run(args, capture=True)
    lines = [ln for ln in (r.stderr or "").splitlines()
             if ln.strip()
             and not _BENIGN_MUX_RE.search(ln)
             and not _AUDIO_ERR_RE.search(ln)
             and not _REPEAT_RE.search(ln)]
    return len(lines)


def hardware_impl(verbose_log: str) -> str:
    """Classify a -v verbose encode log as hardware/software/unknown."""
    low = verbose_log.lower()
    if "hardware accelerated" in low:
        return "hardware"
    if "software implementation" in low:
        return "software"
    return "unknown"
