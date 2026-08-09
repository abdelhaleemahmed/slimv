"""`slimv verify <src> <dst>` — the deletion safety gate. For every source it
confirms the converted file exists, matches the original length, and decodes
cleanly. Only files that pass all three are marked SAFE-TO-DELETE. Read-only:
it never deletes anything.

Resumable & interruptible: the report is rewritten (atomically) after **every
file**, so a run you Ctrl-C — or one that's killed by a sleep/restart — can be
re-run and it **skips everything already verified**, continuing where it left
off. Resume reuses a prior verdict for any output that is byte-for-byte unchanged
(same size + mtime) and previously passed, skipping the costly full-decode.
Anything new, changed, or previously NOT-safe is always re-checked, so resuming
never weakens the gate. Pass ``--full`` (``resume=False``) to force a complete
re-decode of everything.

Shardable for parallel runs: ``--skip N`` / ``--limit N`` select a slice of the
file list, and ``--report PATH`` sends each shard's report to its own file so two
processes verifying different slices don't clobber each other."""
from __future__ import annotations

import csv
import datetime as _dt
import time
from pathlib import Path

from . import ffmpeg
from .console import console
from .util import iter_videos, output_path_for

_HEADER = ["When", "RelPath", "SrcDur", "OutDur", "Delta", "OutExists",
           "DecodeErrors", "Verdict", "Reason", "OutSize", "OutMTime"]


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


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


def _write_report(report: Path, known: dict[str, dict]) -> None:
    """Rewrite the whole report from the in-memory rows, atomically (write a
    temp then replace) so an interrupt mid-write never leaves a torn file. Called
    after every file, which is what makes an interrupted run resumable."""
    report.parent.mkdir(parents=True, exist_ok=True)
    tmp = report.with_suffix(report.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_HEADER)
        w.writeheader()
        for r in known.values():
            w.writerow({k: r.get(k, "") for k in _HEADER})
    for _ in range(5):                     # a concurrent reader can briefly lock it
        try:
            tmp.replace(report)
            return
        except OSError:
            time.sleep(0.3)
    # last resort: leave tmp in place; the next per-file write will try again


def _verify_one(f: Path, out: Path, kept_original: bool, tol: float, quick: bool,
                hwaccel: str | None, prev: dict | None) -> tuple[dict, bool]:
    """Verify one file. Returns (report_row_without_RelPath, cache_hit)."""
    osize, omtime = _fingerprint(out)
    sd = ffmpeg.duration(f)
    od = delta = dec = ""
    verdict, reason = "SAFE-TO-DELETE", "ok"

    cache_hit = (
        prev is not None
        and prev.get("Verdict") == "SAFE-TO-DELETE"
        and out.exists()
        and prev.get("OutSize") == osize and osize != ""
        and prev.get("OutMTime") == omtime
    )

    if cache_hit:
        # Output unchanged since it last passed — trust the prior verdict and skip
        # the costly decode. Carry the recorded numbers forward.
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

    row = {"When": _now(), "RelPath": "", "SrcDur": sd, "OutDur": od, "Delta": delta,
           "OutExists": out.exists(), "DecodeErrors": dec, "Verdict": verdict,
           "Reason": reason, "OutSize": osize, "OutMTime": omtime}
    return row, cache_hit


def _resolve_out(f: Path, root: Path, dst_root: Path) -> tuple[Path, bool]:
    """The output path for a source, and whether keep-smaller kept the original
    under its own extension instead of producing a .mp4."""
    out = output_path_for(f, root, dst_root)
    if not out.exists():
        kept = out.with_suffix(f.suffix)
        if kept.exists():
            return kept, True
    return out, False


def run(src: str, dst: str, tol: float = 1.0, quick: bool = False,
        resume: bool = True, hwaccel: str | None = None,
        skip: int = 0, limit: int | None = None, report_path: str | None = None) -> int:
    ffmpeg.require_tools()
    src_in = Path(src).resolve()
    dst_in = Path(dst).resolve()

    # Single-file mode: `slimv verify <src_file> <out_file_or_folder>`. Verify just
    # that one file against an explicit output path (or its mirror inside a folder).
    # No report is read or written, so a one-off check never touches a folder report.
    if src_in.is_file():
        root = src_in.parent
        if dst_in.is_dir():
            out, kept_original = _resolve_out(src_in, root, dst_in)
        else:
            out, kept_original = dst_in, False
        row, _ = _verify_one(src_in, out, kept_original, tol, quick, hwaccel, None)
        v = row["Verdict"]
        colour = "green" if v == "SAFE-TO-DELETE" else "red"
        console.print(f"[{colour}]{v:<15}[/{colour}] {src_in.name}")
        console.print(f"[dim]{row['Reason']}[/dim]")
        return 0 if v == "SAFE-TO-DELETE" else 2

    root = src_in
    files = iter_videos(root)
    dst_root = dst_in
    report = Path(report_path) if report_path else dst_root / "_slimv_verify_report.csv"
    prior = _load_cache(report) if resume else {}
    known = dict(prior)          # merge base: rows we don't re-touch are preserved

    batch = files[skip:(skip + limit) if limit else None]
    total = len(batch)
    if skip or limit:
        console.print(f"[dim]shard: files {skip + 1}–{skip + total} of {len(files)} "
                      f"→ report {report.name}[/dim]")
    reused = 0
    for i, f in enumerate(batch, 1):
        rel = str(f.relative_to(root))
        out, kept_original = _resolve_out(f, root, dst_root)
        row, cache_hit = _verify_one(f, out, kept_original, tol, quick, hwaccel, prior.get(rel))
        row["RelPath"] = rel
        known[rel] = row
        if cache_hit:
            reused += 1
        v = row["Verdict"]
        colour = "green" if v == "SAFE-TO-DELETE" else "red"
        tag = "[dim](cached)[/dim] " if cache_hit else ""
        console.print(f"[dim][{i}/{total}][/dim] [{colour}]{v:<15}[/{colour}] {tag}{rel[-55:]}")
        console.file.flush()
        _write_report(report, known)   # persist after EVERY file → resumable

    verdicts = [r.get("Verdict") for r in known.values()]
    safe = sum(1 for x in verdicts if x == "SAFE-TO-DELETE")
    keep = sum(1 for x in verdicts if x and x != "SAFE-TO-DELETE")
    reused_note = f"   (reused {reused} cached)" if reused else ""
    console.print(
        f"\n[cyan]SAFE-TO-DELETE: {safe}   KEEP-SOURCE: {keep}{reused_note}   Report: {report}[/cyan]"
    )
    if keep == 0 and safe:
        console.print("[green]ALL VERIFIED — these sources are safe to remove.[/green]")
    elif keep:
        console.print(f"[yellow]*** {keep} file(s) NOT safe — review the report before deleting anything. ***[/yellow]")
    return 0 if keep == 0 else 2
