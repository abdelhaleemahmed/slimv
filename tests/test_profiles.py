"""Invariants for the encoding-profile catalog."""
from slimv.profiles import PROFILES, ORDER, BENCH_DEFAULT


def test_keys_match_profile_name():
    for name, p in PROFILES.items():
        assert p.name == name


def test_every_profile_declares_its_codec_first():
    for p in PROFILES.values():
        assert p.vargs, f"{p.name} has empty vargs"
        assert p.vargs[0] == "-c:v"
        assert p.vargs[1] == p.codec


def test_order_references_only_real_profiles():
    for name in ORDER:
        assert name in PROFILES


def test_bench_default_is_a_subset():
    for name in BENCH_DEFAULT:
        assert name in PROFILES


def test_hardware_flag_matches_codec():
    # qsv/nvenc encoders are hardware; libx265 / libsvtav1 are CPU.
    for p in PROFILES.values():
        expected_hw = ("qsv" in p.codec) or ("nvenc" in p.codec)
        assert p.hardware == expected_hw, f"{p.name}: hardware flag vs codec {p.codec}"
