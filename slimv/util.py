"""Shared helpers: file discovery, size/duration formatting."""
from __future__ import annotations

import re
from pathlib import Path

_UNIT_RE = re.compile(
    r"^(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m)?(?:(\d+(?:\.\d+)?)s)?$"
)


def parse_duration(text: str | int | float) -> int:
    """Parse a duration into whole seconds, accepting seconds *or* minutes.

    Accepted forms::

        90            90 seconds (plain number)
        30s           30 seconds
        2m            2 minutes
        1m30s         1 minute 30 seconds
        1h5m          1 hour 5 minutes
        1:30          mm:ss  -> 90 seconds
        1:02:03       hh:mm:ss

    Raises:
        ValueError: if the text is not a recognizable duration.
    """
    if isinstance(text, (int, float)):
        if text < 0:
            raise ValueError("duration cannot be negative")
        return int(round(text))
    s = str(text).strip().lower()
    if not s:
        raise ValueError("empty duration")

    if ":" in s:
        parts = s.split(":")
        if any(p.strip() == "" for p in parts) or len(parts) > 3:
            raise ValueError(f"bad clock duration: {text!r}")
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            raise ValueError(f"bad clock duration: {text!r}")
        while len(nums) < 3:
            nums.insert(0, 0.0)
        h, m, sec = nums
        return int(round(h * 3600 + m * 60 + sec))

    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return int(round(float(s)))

    m = _UNIT_RE.match(s)
    if not m or not any(m.groups()):
        raise ValueError(
            f"bad duration: {text!r} (use e.g. 90, 30s, 2m, 1m30s, or 1:30)"
        )
    h = float(m.group(1) or 0)
    mnt = float(m.group(2) or 0)
    sec = float(m.group(3) or 0)
    return int(round(h * 3600 + mnt * 60 + sec))

# Container extensions we treat as video files.
VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
    ".ts", ".webm", ".m4v", ".mpg", ".mpeg", ".m2ts",
}


def iter_videos(path: str | Path) -> list[Path]:
    """Return a sorted list of video files. Accepts a single file or a folder
    (searched recursively)."""
    p = Path(path)
    if p.is_file():
        return [p]
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")
    return sorted(
        x for x in p.rglob("*")
        if x.is_file()
        and x.suffix.lower() in VIDEO_EXTS
        # skip slimv's own in-progress temp files (e.g. "name.mp4.partial.mp4")
        and not x.name.endswith(".partial.mp4")
    )


def human_size(num_bytes: float) -> str:
    """Bytes -> human-readable string (MB/GB)."""
    mb = num_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def human_dur(seconds: float | None) -> str:
    """Seconds -> H:MM:SS (or 'n/a')."""
    if seconds is None:
        return "n/a"
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def output_path_for(src: Path, root: Path, dst_root: Path, ext: str = ".mp4") -> Path:
    """Mirror src's path under dst_root, swapping the extension."""
    rel = src.relative_to(root)
    return (dst_root / rel).with_suffix(ext)
