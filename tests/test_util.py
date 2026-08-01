"""Tests for slimv.util helpers (size/duration formatting, file discovery)."""
from pathlib import Path

import pytest

from slimv.util import human_size, human_dur, iter_videos, output_path_for


def test_human_size_mb_and_gb():
    assert human_size(1024 * 1024) == "1.0 MB"
    assert human_size(500 * 1024 * 1024) == "500.0 MB"
    # 1.5 GiB -> GB branch
    assert human_size(int(1.5 * 1024 * 1024 * 1024)) == "1.50 GB"


def test_human_dur_formats():
    assert human_dur(None) == "n/a"
    assert human_dur(0) == "0:00"
    assert human_dur(59) == "0:59"
    assert human_dur(90) == "1:30"
    assert human_dur(3723) == "1:02:03"


def test_iter_videos_folder_filters_and_sorts(tmp_path):
    (tmp_path / "b.mkv").write_text("x")
    (tmp_path / "a.mp4").write_text("x")
    (tmp_path / "notes.txt").write_text("x")            # not a video
    (tmp_path / "half.mp4.partial.mp4").write_text("x")  # slimv temp — skipped
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "d.mp4").write_text("x")

    found = iter_videos(tmp_path)
    names = [p.name for p in found]
    assert names == ["a.mp4", "b.mkv", "d.mp4"]          # sorted, filtered
    assert "notes.txt" not in names
    assert all(not n.endswith(".partial.mp4") for n in names)


def test_iter_videos_single_file(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_text("x")
    assert iter_videos(f) == [f]


def test_iter_videos_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        iter_videos(tmp_path / "nope")


def test_output_path_for_mirrors_and_swaps_ext():
    root = Path("/src")
    dst = Path("/out")
    src = root / "a" / "b" / "lesson.mkv"
    got = output_path_for(src, root, dst, ext=".mp4")
    assert got == dst / "a" / "b" / "lesson.mp4"
