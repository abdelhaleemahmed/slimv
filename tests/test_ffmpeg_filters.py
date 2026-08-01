"""The verify integrity gate classifies ffmpeg stderr lines. These regexes decide
what counts as a real *video* decode error vs. a benign/audio line — the source of
past false KEEP-SOURCE verdicts. Test them directly (no ffmpeg needed)."""
from slimv.ffmpeg import _AUDIO_ERR_RE, _BENIGN_MUX_RE, _REPEAT_RE


def test_audio_lines_are_recognized():
    assert _AUDIO_ERR_RE.search("[aac @ 0x556] env_facs_q 255 is invalid")
    assert _AUDIO_ERR_RE.search("[mp3float @ 0x1] error while decoding")
    assert _AUDIO_ERR_RE.search("[ac3 @ 0x2] some complaint")
    assert _AUDIO_ERR_RE.search("env_facs_q 255 is invalid")   # bare SBR grumble


def test_real_video_error_is_not_classified_as_audio():
    # This MUST NOT match — a genuine video decode error has to be counted.
    assert not _AUDIO_ERR_RE.search("[hevc @ 0x9] Error while decoding stream")
    assert not _AUDIO_ERR_RE.search("[h264 @ 0x9] corrupted macroblock")


def test_benign_muxer_dts_warnings():
    assert _BENIGN_MUX_RE.search(
        "Application provided invalid, non monotonically increasing dts to muxer")
    assert _BENIGN_MUX_RE.search("Non-monotonous DTS in output stream")


def test_repeated_line_marker():
    assert _REPEAT_RE.search("    Last message repeated 7 times")
