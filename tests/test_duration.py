"""Tests for slimv.util.parse_duration and the CLI duration argument."""
import argparse

import pytest

from slimv.util import parse_duration
from slimv.cli import duration_arg


@pytest.mark.parametrize("text,expected", [
    (45, 45),
    (45.0, 45),
    ("90", 90),
    ("90.4", 90),          # rounds
    ("30s", 30),
    ("2m", 120),
    ("1m30s", 90),
    ("1h5m", 3900),
    ("1h", 3600),
    ("1.5m", 90),          # fractional minutes
    ("0.1m", 6),
    ("1:30", 90),          # mm:ss
    ("0:59", 59),
    ("1:02:03", 3723),     # hh:mm:ss
    ("  2m  ", 120),       # surrounding whitespace
    ("2M", 120),           # case-insensitive
])
def test_parse_duration_ok(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("bad", ["", "bogus", "1x", "m", "s", "1:2:3:4", "::", -5])
def test_parse_duration_rejects(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)


def test_duration_arg_wraps_valueerror_as_argparse():
    assert duration_arg("2m") == 120
    with pytest.raises(argparse.ArgumentTypeError):
        duration_arg("nonsense")
