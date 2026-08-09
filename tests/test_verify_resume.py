"""Tests for verify's resume (skip already-verified), --skip/--limit sharding,
and --report override. ffmpeg is stubbed so the suite stays ffmpeg-free."""
import csv

import pytest

from slimv import verify


@pytest.fixture
def stub_ffmpeg(monkeypatch):
    """Every file decodes cleanly and both src/out report the same duration → all
    files land SAFE-TO-DELETE without touching a real ffmpeg."""
    monkeypatch.setattr(verify.ffmpeg, "require_tools", lambda: None)
    monkeypatch.setattr(verify.ffmpeg, "duration", lambda p: 100.0)
    monkeypatch.setattr(verify.ffmpeg, "decode_errors", lambda p, hwaccel=None: 0)


def _make_tree(tmp_path, n):
    """A source tree of n files with matching .mp4 outputs; returns (src, dst)."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    for i in range(n):
        (src / f"{i:02d}.mp4").write_bytes(b"s")
        (dst / f"{i:02d}.mp4").write_bytes(b"o")
    return src, dst


def _report_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_limit_verifies_only_a_slice(stub_ffmpeg, tmp_path):
    src, dst = _make_tree(tmp_path, 5)
    rc = verify.run(str(src), str(dst), limit=2)
    rows = _report_rows(dst / "_slimv_verify_report.csv")
    assert rc == 0
    assert len(rows) == 2                       # only the first two written
    assert {r["RelPath"] for r in rows} == {"00.mp4", "01.mp4"}


def test_skip_offsets_the_slice(stub_ffmpeg, tmp_path):
    src, dst = _make_tree(tmp_path, 5)
    verify.run(str(src), str(dst), skip=3)
    rows = _report_rows(dst / "_slimv_verify_report.csv")
    assert {r["RelPath"] for r in rows} == {"03.mp4", "04.mp4"}


def test_report_written_incrementally_survives_interrupt(stub_ffmpeg, tmp_path, monkeypatch):
    """Simulate an interrupt after the 2nd file: the report must already hold those
    two rows (proving per-file persistence), and a resume completes the rest and
    reuses the two already done."""
    src, dst = _make_tree(tmp_path, 4)
    real_write = verify._write_report
    calls = {"n": 0}

    def boom(report, known):
        real_write(report, known)               # persist this file first...
        calls["n"] += 1
        if calls["n"] == 2:
            raise KeyboardInterrupt              # ...then die, like a Ctrl-C

    monkeypatch.setattr(verify, "_write_report", boom)
    with pytest.raises(KeyboardInterrupt):
        verify.run(str(src), str(dst))
    rows = _report_rows(dst / "_slimv_verify_report.csv")
    assert len(rows) == 2                        # the two done files are on disk

    monkeypatch.setattr(verify, "_write_report", real_write)  # "re-run" cleanly
    reused_seen = {}
    orig = verify._verify_one

    def spy(f, out, kept, tol, quick, hw, prev):
        row, hit = orig(f, out, kept, tol, quick, hw, prev)
        reused_seen[f.name] = hit
        return row, hit

    monkeypatch.setattr(verify, "_verify_one", spy)
    rc = verify.run(str(src), str(dst))
    rows = _report_rows(dst / "_slimv_verify_report.csv")
    assert rc == 0
    assert len(rows) == 4                        # all four now recorded
    # the first two were already verified → reused from cache on the resume
    assert reused_seen["00.mp4"] is True and reused_seen["01.mp4"] is True
    assert reused_seen["02.mp4"] is False and reused_seen["03.mp4"] is False


def test_report_override_keeps_default_untouched(stub_ffmpeg, tmp_path):
    src, dst = _make_tree(tmp_path, 3)
    custom = tmp_path / "shard_a.csv"
    verify.run(str(src), str(dst), limit=1, report_path=str(custom))
    assert custom.exists()
    assert not (dst / "_slimv_verify_report.csv").exists()   # default not clobbered
    assert len(_report_rows(custom)) == 1


def test_full_ignores_cache(stub_ffmpeg, tmp_path, monkeypatch):
    src, dst = _make_tree(tmp_path, 3)
    verify.run(str(src), str(dst))               # seed the cache
    seen = []
    orig = verify._verify_one

    def spy(f, out, kept, tol, quick, hw, prev):
        seen.append(prev)                        # prev is None when resume is off
        return orig(f, out, kept, tol, quick, hw, prev)

    monkeypatch.setattr(verify, "_verify_one", spy)
    verify.run(str(src), str(dst), resume=False)
    assert all(p is None for p in seen)          # --full passes no prior verdicts
