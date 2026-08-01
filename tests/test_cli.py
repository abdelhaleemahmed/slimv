"""Tests for the argument parser: every command wired, durations parsed."""
import argparse

import pytest

from slimv.cli import build_parser, duration_arg


EXPECTED_COMMANDS = {
    "hwcheck", "profiles", "analyze", "check", "test", "benchmark",
    "eyeball", "downscale-test", "recommend", "encode", "verify", "rename",
}


def _subparser_choices(parser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


def test_all_commands_registered():
    parser = build_parser()
    assert EXPECTED_COMMANDS <= _subparser_choices(parser)


def test_duration_flags_parse_minutes():
    parser = build_parser()
    ns = parser.parse_args(["benchmark", "clip.mp4", "--start", "0m", "--length", "2m"])
    assert ns.start == 0
    assert ns.length == 120


def test_analyze_measure_flags():
    parser = build_parser()
    ns = parser.parse_args(["analyze", "folder", "--measure", "--sample-length", "1m"])
    assert ns.measure is True
    assert ns.sample_length == 60


def test_rename_positionals_and_flags():
    parser = build_parser()
    ns = parser.parse_args(["rename", "folder", "-tag", "--tidy", "--apply"]) \
        if False else parser.parse_args(["rename", "--tidy", "--apply", "--", "folder", "-tag"])
    assert ns.folder == "folder"
    assert ns.text == "-tag"
    assert ns.tidy and ns.apply


def test_bad_duration_is_rejected():
    with pytest.raises(argparse.ArgumentTypeError):
        duration_arg("not-a-time")
