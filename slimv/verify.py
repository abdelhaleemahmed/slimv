"""`slimv verify <src> <dst>` — the deletion safety gate. For every source it
confirms the converted file exists, matches the original length, and decodes
cleanly. Only files that pass all three are marked SAFE-TO-DELETE. Read-only:
it never deletes anything.

Resume is **on by default**: it reuses a previous run's verdict for any output
that is byte-for-byte unchanged (same size + mtime) and previously passed,
skipping the expensive full-decode pass. Anything new, changed, or previously
NOT-safe is always re-checked from scratch — so resuming never weakens the gate.
Pass ``--full`` (``resume=False``) to force a complete re-decode of everything,
e.g. to re-scan for silent on-disk corruption that wouldn't change size/mtime."""
from __future__ import annotations

import csv
import datetime as _dt
from pathlib import Path

from . import ffmpeg
from .console import console
from .util import iter_videos, output_path_for

_HEADER = ["When", "RelPath", "SrcDur", "OutDur", "Delta", "OutExists",
           "DecodeErrors", "Verdict", "Reason", "OutSize", "OutMTime"]


def _fingerprint(p: Path) -> tuple[str, str]:
    """(size, mtime) of a file as strings — the cache key for resume. Empty if
    the file is missing."""
    try:
        st = p.stat()
        return str(st.st_size), str(int(st.st_mtime))
    except OSError:
        return "", ""


def _load_cache(report: Path) -> dict[str, dict]:
    """Prior report rows keyed by RelPath (empty dict if absent/unreadable)."""
    if not report.exists():
        return {}
    try:
        with report.open(newline="", encoding="utf-8") as fh:
            return {row["RelPath"]: row for row in csv.DictReader(fh)}
    except (OSError, csv.Error, KeyError):
        return {}


def run(src: str, dst: str, tol: float = 1.0, quick: bool = False,
        resume: bool = True, hwaccel: str | None = None) -> int:
    ffmpeg.require_tools()
    src_in = Path(src).resolve()
    dst_in = Path(dst).resolve()

    # Single-file mode: `slimv verify <src_file> <out_file_or_folder>`. Verify just
    # that one file against an explicit output path (or its mirror inside a folder).
    # We don't read or overwrite the folder's _slimv_verify_report.csv in this mode,
    # so a one-off file check never clobbers a whole-folder report / resume cache.
    if src_in.is_file():
        root = src_in.parent
        files = [src_in]
        explicit_out = None if dst_in.is_dir() else dst_in
        dst_root = dst_in if dst_in.is_dir() else dst_in.parent
        report = None
        cache = {}
    else:
        root = src_in
        files = iter_videos(root)
        explicit_out = None
        dst_root = dst_in
        report = dst_root / "_slimv_verify_report.csv"
        cache = _load_cache(report) if resume else {}

    rows_out = [_HEADER]
    total = len(files)
    safe = keep = reused = 0
    for i, f in enumerate(files, 1):
        rel = f.relative_to(root)
        out = explicit_out if explicit_out is not None else output_path_for(f, root, dst_root)
        # keep-smaller may have kept the original (not smaller) under its source
        # extension instead of producing a .mp4. That kept copy IS the output —
        # verify it like any other, don't report it "converted MISSING".
        kept_original = False
        if not out.exists():
            kept = out.with_suffix(f.suffix)
            if kept.exists():
                out, kept_original = kept, True

        osize, omtime = _fingerprint(out)
        sd = ffmpeg.duration(f)
        od = delta = dec = ""
        verdict, reason = "SAFE-TO-DELETE", "ok"

        prev = cache.get(str(rel))
        cache_hit = (
            prev is not None
            and prev.get("Verdict") == "SAFE-TO-DELETE"
            and out.exists()
            and prev.get("OutSize") == osize and osize != ""
            and prev.get("OutMTime") == omtime
        )

        if cache_hit:
            # Output unchanged since it last passed — trust the prior verdict and
            # skip the costly decode. Carry the recorded numbers forward.
            reused += 1
            od = prev.get("OutDur", "")
            delta = prev.get("Delta", "")
            dec = "cached"
            reason = "ok (cached)"
        elif not out.exists():
            verdict, reason = "KEEP-SOURCE", "converted MISSING"
        else:
            od = ffmpeg.duration(out)
            if od is None:
                verdict, reason = "KEEP-SOURCE", "converted unreadable"
            else:
                delta = round(od - sd, 2) if sd is not None else ""
                if isinstance(delta, float) and abs(delta) > tol:
                    # Duration differs beyond tolerance — but a VFR source re-encodes to
                    # the SAME frames with a slightly drifted duration. If both frame
                    # counts are known and match, the content is intact (a timing
                    # artifact, not a truncation), so it's still safe.
                    sfc, ofc = ffmpeg.frame_count(f), ffmpeg.frame_count(out)
                    if sfc is not None and ofc is not None and abs(sfc - ofc) <= 1:
                        reason = f"ok (VFR: {ofc} frames match, duration drift Δ={delta})"
                    else:
                        # Metadata frame counts disagree (or are missing). This is either a
                        # real truncation OR bogus/inflated source metadata (some sources
                        # claim more frames+duration than they actually hold). Settle it with
                        # an authoritative *decoded* frame count on both before condemning.
                        sfe = ffmpeg.frame_count(f, exact=True)
                        ofe = ffmpeg.frame_count(out, exact=True)
                        if sfe is not None and ofe is not None and abs(sfe - ofe) <= 1:
                            reason = (f"ok ({ofe} real frames match; source metadata "
                                      f"duration/frames inflated, Δ={delta})")
                        else:
                            verdict, reason = "KEEP-SOURCE", \
                                f"length mismatch (Δ={delta}; real frames src={sfe} out={ofe})"
            if verdict == "SAFE-TO-DELETE" and not quick:
                dec = ffmpeg.decode_errors(out, hwaccel=hwaccel)
                if dec > 0 and hwaccel:
                    # A hardware decoder can throw a transient/spurious error burst
                    # mid-batch. Before condemning the file, confirm with an
                    # authoritative CPU (software) re-decode — the reliable ground truth.
                    dec = ffmpeg.decode_errors(out, hwaccel=None)
                if dec > 0:
                    verdict, reason = "KEEP-SOURCE", f"decode errors ({dec})"
            if verdict == "SAFE-TO-DELETE" and kept_original:
                reason = "ok (kept original — not smaller)"

        if verdict == "SAFE-TO-DELETE":
            safe += 1
            colour = "green"
        else:
            keep += 1
            colour = "red"
        tag = "[dim](cached)[/dim] " if cache_hit else ""
        shown = str(rel)[-55:]
        console.print(f"[dim][{i}/{total}][/dim] [{colour}]{verdict:<15}[/{colour}] {tag}{shown}")
        console.file.flush()  # so a count-up is visible live, even when piped to a file
        rows_out.append([_now(), str(rel), sd, od, delta, out.exists(), dec,
                         verdict, reason, osize, omtime])

    if report is not None:  # folder mode only — never clobber a folder report for a single-file check
        dst_root.mkdir(parents=True, exist_ok=True)
        with report.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rows_out)

    reused_note = f"   (reused {reused} cached)" if reused else ""
    report_note = f"   Report: {report}" if report is not None else ""
    console.print(
        f"\n[cyan]SAFE-TO-DELETE: {safe}   KEEP-SOURCE: {keep}{reused_note}{report_note}[/cyan]"
    )
    if keep == 0 and safe:
        console.print("[green]ALL VERIFIED — these sources are safe to remove.[/green]")
    elif keep:
        console.print(f"[yellow]*** {keep} file(s) NOT safe — review the report before deleting anything. ***[/yellow]")
    return 0 if keep == 0 else 2


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")
