"""Make the in-tree ``slimv`` package importable when running the tests without
installing (e.g. a fresh clone: ``pytest``). Harmless when slimv is installed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
