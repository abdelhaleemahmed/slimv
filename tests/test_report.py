"""Tests for `slimv report` — the CSV-to-house-box summary command."""
import csv
from datetime import datetime
from pathlib import Path

import pytest

from slimv.report import (
    _course_title, _dedupe_last, _dw, _f, _gb, _render_box, build_report,
)

CHECK = "\u2705"  # ✅, double-width

_HEADER = ["When", "RelPath", "Profile", "SrcMB", "OutMB", "Reduct%",
           "SrcDur", "OutDur", "Delta", "Status", "EncSec", "SpeedxRT"]


def _write_log(dst, rows):
    dst.mkdir(parents=True, exist_ok=True)
    with (dst / "_slimv_encode_log.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(_HEADER)
        for r in rows:
            w.writerow(r)


def _row(rel, src_mb, out_mb, status="OK", dur=600.0, spd=5.0):
    red = round((1 - out_mb / src_mb) * 100) if src_mb else 0
    return ["2026-01-01T00:00:00", rel, "nvenc-hq", f"{src_mb}", f"{out_mb}",
            red, dur, dur, 0.0, status, 100.0, spd]


# ---- small helpers -------------------------------------------------------

def test_f_parses_and_tolerates_blanks():
    assert _f("12.5") == 12.5
    assert _f("") == 0.0
    assert _f(None) == 0.0
    assert _f("n/a") == 0.0


def test_gb_switches_units():
    assert _gb(512) == "512 MB"
    assert _gb(2048) == "2.00 GB"


def test_course_title_strips_hevc_tag():
    assert _course_title(Path(r"C:/out/CBTNuggets - GitLab Training [HEVC]")) == "CBTNuggets - GitLab Training"
    assert _course_title(Path("/out/Plain Name")) == "Plain Name"


def test_dedupe_last_keeps_latest_status():
    rows = [
        {"RelPath": "a.mp4", "Status": "ENCODE-FAIL"},
        {"RelPath": "a.mp4", "Status": "OK"},
        {"RelPath": "b.mp4", "Status": "OK"},
    ]
    out = _dedupe_last(rows)
    assert len(out) == 2
    a = [r for r in out if r["RelPath"] == "a.mp4"][0]
    assert a["Status"] == "OK"


# ---- box rendering -------------------------------------------------------

def test_render_box_rows_are_visually_equal_width_with_double_width_emoji():
    lines = _render_box("Title", [("Files", f"2 / 4 {CHECK}"), ("Size", "4.00 GB")])
    widths = {len(ln) + ln.count(CHECK) for ln in lines}  # ✅ renders 2 cols
    assert len(widths) == 1, f"misaligned right border: {lines}"
    assert lines[0].startswith("\u250c") and lines[-1].startswith("\u2514")
    assert any(CHECK in ln for ln in lines)


def test_render_box_title_spans_full_width():
    lines = _render_box("Title", [("Files", "2 / 4"), ("Size", "4.00 GB")])
    # top border is unbroken (no column tee), the title row is ONE cell (only the
    # two outer bars), and the column split begins on the line below the title.
    assert "\u252c" not in lines[0]          # \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510   (no \u252c)
    assert lines[1].count("\u2502") == 2      # \u2502 Title     \u2502  (single spanning cell)
    assert "\u252c" in lines[2]               # \u251c\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2524  columns start here


def test_dw_counts_check_as_two():
    assert _dw("ok") == 2
    assert _dw("ok" + CHECK) == 4  # 3 chars + 1 extra col for the wide ✅


# ---- build_report: completed run (no --src) ------------------------------

def test_completed_run_totals(tmp_path):
    dst = tmp_path / "Course [HEVC]"
    _write_log(dst, [
        _row("1.mp4", 100.0, 50.0),
        _row("2.mp4", 100.0, 30.0),
    ])
    title, box, meta = build_report(str(dst))
    d = dict(box)
    assert title == "Course"
    assert meta["done_count"] == 2 and meta["total_files"] == 2
    assert not meta["in_progress"]
    assert d["Files"] == f"2 / 2 {CHECK}"
    assert d["Size"] == "200 MB \u2192 80 MB"                 # no ~ when complete
    assert d["Saved"].startswith("60.0% (120 MB) \u2014")     # reclaim = 200-80
    assert d["Source"].startswith("(pass --src")


# ---- build_report: in-progress with --src (projection) -------------------

def test_in_progress_projection(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for n in ("a", "b", "c", "d"):
        (src / f"{n}.mp4").write_bytes(b"\0" * (1024 * 1024))  # 1 MB each -> 4 MB total
    dst = tmp_path / "out [HEVC]"
    _write_log(dst, [
        _row("a.mp4", 1.0, 0.5, dur=600.0, spd=5.0),
        _row("b.mp4", 1.0, 0.5, dur=600.0, spd=5.0),
    ])
    # stub durations (ffmpeg-free) and a fixed clock 1h after the logged start
    title, box, meta = build_report(
        str(dst), src=str(src), duration_fn=lambda f: 600.0,
        now=datetime(2026, 1, 1, 1, 0, 0))
    d = dict(box)
    assert meta["in_progress"] is True
    assert meta["done_count"] == 2 and meta["total_files"] == 4
    assert round(meta["expected_out_mb"]) == 2   # 4 MB * (0.5 ratio)
    assert round(meta["saved_pct"]) == 50
    assert d["Files"] == f"2 / 4 {CHECK}"
    assert d["Size"] == "4 MB \u2192 ~2 MB"       # total -> ~expected
    assert "~" in d["Saved"]
    assert "% of course" in d["Encoded"] and "ETA" not in d["Encoded"]  # ETA is its own row now
    # time rows: start from the log, elapsed against the injected clock, ETA kept
    assert d["Started"] == "2026-01-01 00:00"
    assert d["Elapsed"] == "1:00:00 so far"
    assert d["ETA"] == "~4:00"               # 1200 s remaining / 5.0\u00d7 = 240 s
    assert d["Source"] == str(src)
    # ETA = real durations of the 2 remaining files (c,d) / avg speed 5.0 = 1200/5
    assert meta["remaining_secs"] == 1200.0
    assert round(meta["eta"]) == 240


def test_eta_sums_real_remaining_durations(tmp_path):
    """ETA must come from the actual durations of the not-yet-encoded files, not a
    bitrate estimate \u2014 a file's byte size must not affect it when its duration is known."""
    src = tmp_path / "src"
    src.mkdir()
    # 'a' already done; 'b','c' remain, with deliberately different byte sizes
    (src / "a.mp4").write_bytes(b"\0" * (1024 * 1024))
    (src / "b.mp4").write_bytes(b"\0" * (5 * 1024 * 1024))
    (src / "c.mp4").write_bytes(b"\0" * (1 * 1024 * 1024))
    dst = tmp_path / "out [HEVC]"
    _write_log(dst, [_row("a.mp4", 1.0, 0.5, dur=600.0, spd=2.0)])
    # each remaining file is 300 s regardless of its size
    _t, _box, meta = build_report(str(dst), src=str(src), duration_fn=lambda f: 300.0)
    assert meta["remaining_secs"] == 600.0        # 2 remaining \u00d7 300 s (size-independent)
    assert round(meta["eta"]) == 300              # 600 s / 2.0\u00d7 realtime


def test_failed_rows_surface(tmp_path):
    dst = tmp_path / "C [HEVC]"
    _write_log(dst, [
        _row("ok.mp4", 100.0, 40.0),
        _row("bad.mp4", 100.0, 0.0, status="ENCODE-FAIL"),
    ])
    _title, box, meta = build_report(str(dst))
    d = dict(box)
    assert meta["fails"] == 1
    assert meta["done_count"] == 1
    assert "ENCODE-FAIL" in d["Failed"]


def test_verify_row_added_when_report_present(tmp_path):
    dst = tmp_path / "C [HEVC]"
    _write_log(dst, [_row("1.mp4", 100.0, 40.0)])
    with (dst / "_slimv_verify_report.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["When", "RelPath", "SrcDur", "OutDur", "Delta", "OutExists", "DecodeErrors", "Verdict", "Reason"])
        w.writerow(["t", "1.mp4", 600, 600, 0, "yes", 0, "SAFE-TO-DELETE", "ok"])
    _title, box, _meta = build_report(str(dst))
    d = dict(box)
    assert d["Verify"] == f"1 / 1 SAFE-TO-DELETE {CHECK}"


def test_missing_log_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_report(str(tmp_path / "nope"))
