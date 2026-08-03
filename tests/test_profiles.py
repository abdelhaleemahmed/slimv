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
    # Hardware encoders are ffmpeg's vendor blocks (hevc_qsv / hevc_nvenc / hevc_amf,
    # ...); the CPU encoders are all 'lib*' (libx265 / libx264 / libsvtav1). Deriving
    # from that keeps this correct for any future hardware encoder without edits.
    for p in PROFILES.values():
        expected_hw = not p.codec.startswith("lib")
        assert p.hardware == expected_hw, f"{p.name}: hardware flag vs codec {p.codec}"


def test_amf_profiles_present_and_well_formed():
    for name in ("amf", "amf-hq"):
        assert name in PROFILES, f"{name} missing from PROFILES"
        p = PROFILES[name]
        assert p.codec == "hevc_amf"
        assert p.hardware is True
        assert name in ORDER, f"{name} not in ORDER"
        # ships the QuickTime tag like the other HEVC profiles
        assert "-tag:v" in p.vargs and "hvc1" in p.vargs
