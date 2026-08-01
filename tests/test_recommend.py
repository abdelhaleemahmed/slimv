"""Tests for the recommend decision rule (pure, no ffmpeg)."""
from slimv.benchmark import Result
from slimv.recommend import decide


def test_smallest_acceptable_wins_without_hw_advantage():
    results = [
        Result("balanced", 95.0, 1.00, 0.5, hardware=False),   # smallest
        Result("qsv", 94.5, 1.05, 0.6, hardware=True),         # only 1.2x faster -> no tie-break
    ]
    d = decide(results, min_vmaf=90, vmaf_tol=2.0)
    assert d.smallest == "balanced"
    assert d.winner == "balanced"


def test_hardware_tiebreak_wins_when_close_and_fast():
    results = [
        Result("balanced", 95.0, 1.00, 0.5, hardware=False),
        Result("qsv", 94.5, 1.10, 1.0, hardware=True),         # <=15% larger, 2x faster
    ]
    d = decide(results, min_vmaf=90, vmaf_tol=2.0)
    assert d.smallest == "balanced"
    assert d.winner == "qsv"


def test_quality_gate_excludes_low_vmaf():
    results = [
        Result("balanced", 95.0, 1.0, 0.5, hardware=False),
        Result("tiny", 80.0, 0.3, 0.5, hardware=False),        # below floor and tolerance
    ]
    d = decide(results, min_vmaf=90, vmaf_tol=2.0)
    assert "tiny" not in d.acceptable
    assert d.winner == "balanced"


def test_below_floor_fallback_picks_smallest_and_warns():
    results = [
        Result("a", 88.0, 1.0, 0.5, hardware=False),
        Result("b", 87.5, 0.8, 0.5, hardware=False),
    ]
    d = decide(results, min_vmaf=90, vmaf_tol=2.0)   # nothing clears 90
    assert d.winner == "b"                            # smallest within tolerance
    assert "VERIFY BY EYE" in d.reason


def test_no_vmaf_uses_size_only():
    results = [
        Result("a", None, 1.0, 0.5, hardware=False),
        Result("b", None, 0.8, 0.5, hardware=False),
    ]
    d = decide(results)
    assert d.winner == "b"
    assert "no VMAF" in d.reason
