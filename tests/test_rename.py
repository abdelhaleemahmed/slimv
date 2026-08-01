"""Tests for the slimv.rename engine (dry-run default, safety, options)."""
from slimv.rename import run, _clean


def _touch(folder, *names):
    for n in names:
        (folder / n).write_text("x")


def test_clean_trims_and_collapses():
    assert _clean("01 Intro - ", tidy=True) == "01 Intro"
    assert _clean("a  b", tidy=True) == "a b"
    assert _clean("01 Intro - ", tidy=False) == "01 Intro - "


def test_dry_run_changes_nothing(tmp_path):
    _touch(tmp_path, "01 Intro-site.mp4")
    rc = run(str(tmp_path), "-site", apply=False)
    assert rc == 0
    assert (tmp_path / "01 Intro-site.mp4").exists()          # untouched
    assert not (tmp_path / "01 Intro.mp4").exists()


def test_apply_renames_and_preserves_extension(tmp_path):
    _touch(tmp_path, "01 Intro-site.mp4", "02 Setup-site.mkv", "keep.mp4")
    rc = run(str(tmp_path), "-site", apply=True)
    assert rc == 0
    assert (tmp_path / "01 Intro.mp4").exists()
    assert (tmp_path / "02 Setup.mkv").exists()               # extension kept
    assert not (tmp_path / "01 Intro-site.mp4").exists()
    assert (tmp_path / "keep.mp4").exists()                   # non-match untouched


def test_tidy_trims_leftover_separators(tmp_path):
    _touch(tmp_path, "01 Intro - site.com.mp4")
    run(str(tmp_path), "site.com", tidy=True, apply=True)
    assert (tmp_path / "01 Intro.mp4").exists()


def test_collision_is_skipped(tmp_path):
    _touch(tmp_path, "a-x.mp4", "a.mp4")
    run(str(tmp_path), "-x", apply=True)
    # target "a.mp4" already exists -> the rename is skipped, both survive
    assert (tmp_path / "a-x.mp4").exists()
    assert (tmp_path / "a.mp4").exists()


def test_empty_result_is_skipped(tmp_path):
    _touch(tmp_path, "site.mp4")           # stem == the removed text -> empty
    run(str(tmp_path), "site", apply=True)
    assert (tmp_path / "site.mp4").exists()


def test_ext_filter(tmp_path):
    _touch(tmp_path, "a-x.mp4", "a-x.txt")
    run(str(tmp_path), "-x", exts=[".mp4"], apply=True)
    assert (tmp_path / "a.mp4").exists()
    assert (tmp_path / "a-x.txt").exists()  # wrong ext, untouched


def test_ignore_case(tmp_path):
    _touch(tmp_path, "aSITEb.mp4")
    run(str(tmp_path), "site", ignore_case=True, apply=True)
    assert (tmp_path / "ab.mp4").exists()


def test_recursive_flag(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    _touch(sub, "deep-x.mp4")
    # non-recursive: leaves sub-folder files alone
    run(str(tmp_path), "-x", apply=True)
    assert (sub / "deep-x.mp4").exists()
    # recursive: renames it
    run(str(tmp_path), "-x", recursive=True, apply=True)
    assert (sub / "deep.mp4").exists()


def test_not_a_folder_returns_2(tmp_path):
    f = tmp_path / "afile.mp4"
    f.write_text("x")
    assert run(str(f), "-x") == 2
