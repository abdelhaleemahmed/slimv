"""``slimv report <dst> [--src SRC]`` — roll an encode run's ``_slimv_encode_log.csv``
into a single house-format summary box.

Shows, in the standard vertical box-drawing table: files done / total, total
source size → (expected) output size, saved % + reclaim + ratio, average speed,
and the mandatory source path. Add ``--src`` and it counts the whole source tree
so it can report the **total** file count and size, **project the final size
mid-run** (from the compression achieved so far), and give a real ETA by summing
the actual durations of the files still to encode; without ``--src`` the box
reflects only what the log already contains (i.e. a finished run).

Read-only: never touches the media or the log.
"""
from __future__ import annotations

import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import ffmpeg
from .console import console
from .util import human_dur, iter_videos

_LOG_NAME = "_slimv_encode_log.csv"
_VERIFY_NAME = "_slimv_verify_report.csv"
# statuses that produced a kept output file (everything else is a failure)
_DONE = {"OK", "WARN-dur", "KEPT-ORIGINAL"}


def _f(x) -> float:
    """Parse a CSV cell to float, treating blank/None/garbage as 0.0."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _gb(mb: float) -> str:
    """Course-scale size: GB (2 dp) once past a gigabyte, else whole MB."""
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.0f} MB"


def _course_title(dst_root: Path) -> str:
    """Output folder name, minus a trailing ' [HEVC]' tag."""
    name = dst_root.name
    low = name.lower()
    if low.endswith(" [hevc]"):
        name = name[: -len(" [HEVC]")]
    return name or dst_root.name


def _dedupe_last(rows: list[dict]) -> list[dict]:
    """One row per RelPath, last write wins — so a file that was re-encoded (e.g.
    ENCODE-FAIL then OK on a later run) is counted once, by its latest status."""
    by_rel: dict[str, dict] = {}
    for r in rows:
        by_rel[r.get("RelPath", "")] = r
    return list(by_rel.values())


def _verify_summary(dst_root: Path) -> str | None:
    """A 'Verify' row value if a verify report exists, else None."""
    vp = dst_root / _VERIFY_NAME
    if not vp.exists():
        return None
    with vp.open(newline="", encoding="utf-8") as fh:
        vr = _dedupe_last(list(csv.DictReader(fh)))
    if not vr:
        return None
    total = len(vr)
    safe = sum(1 for r in vr if r.get("Verdict") == "SAFE-TO-DELETE")
    if safe == total:
        return f"{safe} / {total} SAFE-TO-DELETE ✅"
    return f"{safe} / {total} safe · {total - safe} FLAGGED"


def _dw(s: str) -> int:
    """Display width: ✅ (U+2705) counts 1 in len() but renders 2 columns."""
    return len(s) + s.count("✅")


def _render_box(title: str, rows: list[tuple[str, str]]) -> list[str]:
    """Render the house vertical box: a full-width title banner (one cell spanning
    both columns), then one label|value row per line with a full ├─┼─┤ separator
    between every row."""
    lw = max(len(r[0]) for r in rows)
    rw = max(_dw(r[1]) for r in rows)
    # the title banner spans both columns: content width = lw + rw + 3 (the " │ "
    # the columns would use in the middle). Widen the value column if the title
    # is longer than the columns can hold, so everything still lines up.
    rw = max(rw, _dw(title) - lw - 3)
    inner = lw + rw + 5          # full inner width between the outer │ bars
    title_w = lw + rw + 3        # title cell content width
    split = "├─" + "─" * lw + "─┬─" + "─" * rw + "─┤"
    mid = "├─" + "─" * lw + "─┼─" + "─" * rw + "─┤"
    out = ["┌" + "─" * inner + "┐",
           "│ " + title + " " * (title_w - _dw(title)) + " │",
           split]
    for i, (label, val) in enumerate(rows):
        out.append("│ " + label.ljust(lw) + " │ " + val + " " * (rw - _dw(val)) + " │")
        if i < len(rows) - 1:
            out.append(mid)
    out.append("└─" + "─" * lw + "─┴─" + "─" * rw + "─┘")
    return out


def _remaining_seconds(remaining: list[Path], duration_fn: Callable[[Path], float | None],
                       secs_per_mb: float) -> float:
    """Sum the real durations of the not-yet-encoded files (probed concurrently).
    A file ffprobe can't read falls back to a size×bitrate estimate so one bad
    file never zeroes the ETA."""
    if not remaining:
        return 0.0

    def one(f: Path) -> float:
        d = duration_fn(f)
        if d is not None:
            return d
        return (f.stat().st_size / (1024 * 1024)) * secs_per_mb

    with ThreadPoolExecutor(max_workers=8) as ex:
        return float(sum(ex.map(one, remaining)))


def _parse_when(s) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None


def build_report(dst: str, src: str | None = None, title: str | None = None,
                 duration_fn: Callable[[Path], float | None] | None = None,
                 now: datetime | None = None):
    """Return (title, box_rows, meta). Pure — reads the log/source, computes,
    returns data; printing is the caller's job (keeps it unit-testable).

    ``duration_fn`` probes a file's length for the ETA (default ``ffmpeg.duration``);
    ``now`` fixes the clock for the elapsed-time row (default ``datetime.now()``);
    tests inject both to stay ffmpeg-free and deterministic."""
    duration_fn = duration_fn or ffmpeg.duration
    now = now or datetime.now()
    dst_root = Path(dst)
    log = dst_root / _LOG_NAME
    if not log.exists():
        raise FileNotFoundError(str(log))
    with log.open(newline="", encoding="utf-8") as fh:
        rows = _dedupe_last(list(csv.DictReader(fh)))

    done = [r for r in rows if r.get("Status") in _DONE]
    fails = [r for r in rows if r.get("Status") not in _DONE]

    src_done_mb = sum(_f(r.get("SrcMB")) for r in done)
    out_done_mb = sum(_f(r.get("OutMB")) for r in done)
    done_secs = sum(_f(r.get("SrcDur")) for r in done)
    speeds = [_f(r.get("SpeedxRT")) for r in done if _f(r.get("SpeedxRT"))]
    avg_speed = sum(speeds) / len(speeds) if speeds else None
    done_count = len(done)

    # Totals + projection: the source tree tells us the WHOLE job's file count and
    # size, so mid-run we can project the final output from the ratio achieved so far.
    total_files = done_count
    total_src_mb = src_done_mb
    src_path: Path | None = None
    files: list[Path] = []
    if src:
        src_path = Path(src)
        files = iter_videos(src_path)
        total_files = len(files)
        total_src_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)

    in_progress = done_count < total_files
    ratio_so_far = (out_done_mb / src_done_mb) if src_done_mb else 0.0
    expected_out_mb = (total_src_mb * ratio_so_far) if in_progress else out_done_mb
    saved_pct = (1 - expected_out_mb / total_src_mb) * 100 if total_src_mb else 0.0
    reclaim_mb = total_src_mb - expected_out_mb
    ratio = (total_src_mb / expected_out_mb) if expected_out_mb else 0.0

    eta = None
    remaining_secs = None
    if in_progress and avg_speed and files:
        # Real ETA: sum the actual durations of the files not yet encoded (probed
        # concurrently), then divide by the measured average speed. Only a file
        # ffprobe can't read falls back to a size×bitrate estimate.
        secs_per_mb = (done_secs / src_done_mb) if src_done_mb else 0.0
        done_rels = {r.get("RelPath") for r in done}
        remaining = [f for f in files if str(f.relative_to(src_path)) not in done_rels]
        remaining_secs = _remaining_seconds(remaining, duration_fn, secs_per_mb)
        eta = remaining_secs / avg_speed

    # Timing: first log timestamp = when the run started; elapsed = wall-clock from
    # then to now (in-progress) or to the last logged file (finished). Includes any
    # sleep/pause between resumes — it's the real span, not just encode time.
    whens = [w for w in (_parse_when(r.get("When")) for r in rows) if w]
    started = min(whens) if whens else None
    last_when = max(whens) if whens else None
    elapsed_secs = None
    if started:
        end = now if in_progress else (last_when or now)
        elapsed_secs = max(0.0, (end - started).total_seconds())

    t = "~" if in_progress else ""   # mark projected figures with a tilde
    box: list[tuple[str, str]] = [
        ("Files", f"{done_count} / {total_files} ✅"),
        ("Size", f"{_gb(total_src_mb)} → {t}{_gb(expected_out_mb)}"),
        ("Saved", f"{t}{saved_pct:.1f}% ({t}{_gb(reclaim_mb)}) — {ratio:.2f}:1"),
    ]
    if in_progress:
        prog = (done_count / total_files * 100) if total_files else 0.0
        box.append(("Encoded", f"{_gb(src_done_mb)} → {_gb(out_done_mb)} · {prog:.0f}% of course"))
    if avg_speed:
        box.append(("Speed", f"{avg_speed:.2f}× realtime"))
    if started:
        box.append(("Started", started.strftime("%Y-%m-%d %H:%M")))
        box.append(("Elapsed", f"{human_dur(elapsed_secs)} so far" if in_progress
                    else human_dur(elapsed_secs)))
    if eta is not None:
        box.append(("ETA", f"~{human_dur(eta)}"))
    vrow = _verify_summary(dst_root)
    if vrow:
        box.append(("Verify", vrow))
    if fails:
        cc = Counter(r.get("Status") for r in fails)
        box.append(("Failed", ", ".join(f"{n}×{s}" for s, n in cc.most_common())))
    box.append(("Source", str(src_path) if src_path else "(pass --src to record the source path)"))
    box.append(("Output", str(dst_root)))

    meta = {
        "done_count": done_count, "total_files": total_files,
        "total_src_mb": total_src_mb, "expected_out_mb": expected_out_mb,
        "saved_pct": saved_pct, "ratio": ratio, "reclaim_mb": reclaim_mb,
        "avg_speed": avg_speed, "eta": eta, "remaining_secs": remaining_secs,
        "started": started, "elapsed_secs": elapsed_secs,
        "in_progress": in_progress, "fails": len(fails),
    }
    return (title or _course_title(dst_root)), box, meta


def run(dst: str, src: str | None = None, title: str | None = None) -> int:
    try:
        t, box, _meta = build_report(dst, src=src, title=title)
    except FileNotFoundError as exc:
        console.print(f"[red]No encode log found:[/red] {exc}")
        console.print("[dim]Point 'report' at a slimv output folder — the one holding "
                      f"{_LOG_NAME}.[/dim]")
        return 1
    # print() (not console.print): values contain literal [brackets] in paths that
    # rich would treat as markup, and the box glyphs are already UTF-8 safe here.
    for line in _render_box(t, box):
        print(line)
    return 0
