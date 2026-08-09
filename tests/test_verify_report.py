"""Tests for `slimv verify-report` — live verify progress + --list-corrupted."""
import csv
from datetime import datetime
from pathlib import Path

from slimv.verify_report import build_verify_report, _load_rows

CHECK = "✅"
_VH = ["When", "RelPath", "SrcDur", "OutDur", "Delta", "OutExists",
       "DecodeErrors", "Verdict", "Reason", "OutSize", "OutMTime"]


def _write(dst, name, rows):
    dst.mkdir(parents=True, exist_ok=True)
    with (dst / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(_VH)
        for r in rows:
            w.writerow(r)


def _row(rel, when, verdict="SAFE-TO-DELETE", reason="ok", dur=600.0):
    return [when, rel, dur, dur, 0, "True", 0, verdict, reason, "1", "1"]


def test_counts_and_corrupted(tmp_path):
    dst = tmp_path / "Course [HEVC]"
    _write(dst, "_slimv_verify_report.csv", [
        _row("a.mp4", "2026-01-01T00:00:00"),
        _row("b.mp4", "2026-01-01T00:01:00"),
        _row("c.mp4", "2026-01-01T00:02:00", "KEEP-SOURCE", "decode errors (99)"),
    ])
    title, box, meta, corrupted = build_verify_report(str(dst))
    d = dict(box)
    assert title.endswith("— verify")
    assert meta["verified"] == 3 and meta["safe"] == 2 and meta["corrupted"] == 1
    assert d["Verified"] == f"3 / 3 {CHECK}"           # no --src -> total = verified
    assert d["Safe"] == "2"
    assert "KEEP-SOURCE" in d["Corrupted"]
    assert [r["RelPath"] for r in corrupted] == ["c.mp4"]


def test_merges_shard_reports(tmp_path):
    dst = tmp_path / "C [HEVC]"
    _write(dst, "_verify.a.csv", [_row("a.mp4", "2026-01-01T00:00:00")])
    _write(dst, "_verify.b.csv", [_row("b.mp4", "2026-01-01T00:00:30")])
    rows = _load_rows(dst)
    assert set(rows) == {"a.mp4", "b.mp4"}             # both shards gathered


def test_progress_current_and_eta_with_src(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    for n in ("a", "b", "c", "d"):
        (src / f"{n}.mp4").write_bytes(b"\0")
    dst = tmp_path / "out [HEVC]"
    # only a,b verified so far -> c is the current/next; d also remains
    _write(dst, "_slimv_verify_report.csv", [
        _row("a.mp4", "2026-01-01T00:00:00", dur=600.0),
        _row("b.mp4", "2026-01-01T00:01:00", dur=600.0),
    ])
    _t, box, meta, _c = build_verify_report(
        str(dst), src=str(src), duration_fn=lambda f: 600.0,
        now=datetime(2026, 1, 1, 0, 2, 0))
    d = dict(box)
    assert meta["verified"] == 2 and meta["total"] == 4 and meta["in_progress"]
    assert d["Verified"] == f"2 / 4 {CHECK}"
    assert d["Current"] == "c.mp4"                     # first unverified in order
    # verified 1200 s over a 60 s wall span -> 20x realtime; 2 remaining x600s /20x = 60s
    assert meta["xrt"] == 20.0
    assert round(meta["eta"]) == 60
    assert "ETA" in d


def test_list_corrupted_paths(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    dst = tmp_path / "out [HEVC]"
    _write(dst, "_slimv_verify_report.csv", [
        _row("ok.mp4", "2026-01-01T00:00:00"),
        _row("sub/bad.mp4", "2026-01-01T00:01:00", "KEEP-SOURCE", "decode errors (5)"),
    ])
    _t, _b, _m, corrupted = build_verify_report(str(dst), src=str(src))
    assert len(corrupted) == 1
    # the run() path joins src + RelPath for the full source path
    full = Path(str(src)) / corrupted[0]["RelPath"]
    assert full.name == "bad.mp4" and "sub" in str(full)
