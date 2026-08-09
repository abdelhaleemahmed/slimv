"""A locked .partial must never crash the batch (regression for the WinError 32
PermissionError that took down a whole 73-file run mid-encode)."""
import time
from pathlib import Path

from slimv.encode import _rm_partial, _finalize


def test_rm_partial_removes_existing(tmp_path):
    p = tmp_path / "x.mp4.partial.mp4"
    p.write_bytes(b"data")
    _rm_partial(p)
    assert not p.exists()


def test_rm_partial_tolerates_missing(tmp_path):
    _rm_partial(tmp_path / "never-created.partial.mp4")  # must not raise (missing_ok)


def test_rm_partial_persistent_lock_does_not_raise(tmp_path, monkeypatch):
    """The bug: a locked file made unlink() raise, crashing the whole run.
    Now it must retry and then return quietly."""
    p = tmp_path / "locked.partial.mp4"
    p.write_bytes(b"data")
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)  # no real waiting

    def boom(self, *a, **k):
        raise PermissionError(32, "The process cannot access the file")
    monkeypatch.setattr(Path, "unlink", boom)

    _rm_partial(p)  # must NOT raise


def test_finalize_renames_and_returns_true(tmp_path):
    tmp = tmp_path / "y.mp4.partial.mp4"
    tmp.write_bytes(b"done")
    out = tmp_path / "y.mp4"
    assert _finalize(tmp, out) is True
    assert out.exists() and not tmp.exists()


def test_finalize_persistent_lock_returns_false(tmp_path, monkeypatch):
    """A locked destination must signal failure to the caller (so it logs a
    per-file MOVE-FAIL and continues) rather than raising."""
    tmp = tmp_path / "z.mp4.partial.mp4"
    tmp.write_bytes(b"done")
    out = tmp_path / "z.mp4"
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)

    def boom(self, *a, **k):
        raise PermissionError(32, "locked")
    monkeypatch.setattr(Path, "replace", boom)

    assert _finalize(tmp, out) is False  # no crash; caller handles it
