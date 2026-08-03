# Contributing to slimv

Thanks for your interest in improving slimv! It's a small, focused toolkit that
drives ffmpeg to shrink video without visible quality loss — contributions that
keep it that way are very welcome.

## Development setup

```bash
git clone https://github.com/abdelhaleemahmed/slimv.git
cd slimv
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1   |  Linux/macOS: source .venv/bin/activate
pip install -e ".[test]"
```

You also need **ffmpeg/ffprobe** on your `PATH` to run the tool itself (not
needed for the unit tests). See the docs' *Requirements* section.

## Running the tests

```bash
pytest
```

The unit suite is **fast and ffmpeg-free** — it covers the deterministic logic
(duration parsing, the rename engine, profile invariants, the recommend decision
rule, the verify-filter regexes, the CLI parser). Please add tests for any new
logic, and keep ffmpeg/GPU/real-media out of the unit tests (those paths are
verified manually / by integration).

## Building the docs

```bash
cd docs && python -m sphinx -b html source _build/html
```

Docs are reStructuredText under `docs/source/`. Keep the build **warning-free**.

## Guidelines

- **slimv orchestrates ffmpeg; it never re-implements a codec.** New features
  build ffmpeg command lines and interpret the results.
- **Quality first, then size** — profiles keep resolution/framerate/pixel format.
- Match the surrounding style (naming, docstrings, comment density).
- Update the docs and `CHANGELOG.md` when you change behavior.

## Pull requests

1. Branch from `main`.
2. Make sure `pytest` passes and the docs build cleanly.
3. Describe what changed and why. Small, focused PRs are easiest to review.

## Reporting bugs

Open an issue with your OS, Python version, `ffmpeg -version`, the exact command,
and the output. `slimv hwcheck` output helps for hardware-encoder issues.
