# slimv — shrink video, keep the quality

**slimv** is a small Python command-line toolkit that drives `ffmpeg`/`ffprobe`
to inspect your hardware, analyze the videos on a disk, benchmark encoders on
*your* content, apply quality-preserving re-encode profiles, and verify the
results before you delete any source.

slimv never encodes video itself — it builds the right ffmpeg commands, runs
them, and interprets the results.

## Install

```bash
pip install slimv
```

Or into a virtual environment (recommended — isolates slimv + `rich`):

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell  (Linux/macOS: source .venv/bin/activate)
pip install dist/slimv-0.2.0-py3-none-any.whl      # wheel
# ...or editable from the source tree, with the test extra:
pip install -e ".[test]"
slimv --version
```

ffmpeg/ffprobe are **not** pip packages — they come from your system ffmpeg
build (see Requirements), so they're available inside the venv with no extra step.

**Requirements:** Python ≥ 3.9 and a recent **ffmpeg/ffprobe** on your `PATH`
(5.0+; 6.x/7.x recommended). `libx265` covers CPU H.265; for hardware encoding
your build needs `hevc_qsv` (Intel) or `hevc_nvenc` (NVIDIA); `libvmaf` enables
VMAF scoring; `libsvtav1` is only needed for the `av1` profile. Run
`slimv hwcheck` to see what your ffmpeg exposes. `rich` installs automatically.

## Quick start

```bash
slimv hwcheck                       # show GPUs / available encoders
slimv profiles                      # list the encoding profiles
slimv analyze  "D:\Courses"         # scan a library, estimate savings
slimv benchmark "clip.mp4"          # try encoders on your own content, score with VMAF
slimv encode  "SRC" "OUT" --profile qsv-hq --copy-audio --keep-smaller
slimv verify  "SRC" "OUT" --hwaccel qsv        # confirm before deleting anything
```

The console entry point `slimv` and `python -m slimv` are equivalent.

## Commands

| Command | What it does |
| --- | --- |
| `hwcheck` | Show GPUs/encoders and how to confirm hardware use |
| `profiles` | List encoding profiles with explanations |
| `analyze` | Scan a folder and estimate reclaimable space (`--measure` projects the real saving from samples) |
| `benchmark` | Encode a short sample several ways and score each with VMAF |
| `eyeball` | Write the original + each profile's sample clip to a folder, to watch and compare |
| `downscale-test` | Measure the size *and* quality cost of downscaling (e.g. 1080p→720p) |
| `recommend` | Benchmark, then auto-pick the best profile and print the encode command |
| `encode` | Re-encode with a quality-preserving profile |
| `verify` | Confirm every output exists, matches length, and decodes cleanly |
| `rename` | Bulk-remove a text fragment from filenames (dry-run by default) |

Sample-based commands (`benchmark`, `eyeball`, `downscale-test`, `recommend`,
`analyze --measure`) take `--start`/`--length` in **seconds or minutes** —
`90`, `30s`, `2m`, `1m30s`, or `1:30`.

## Core ideas

- **One tool, ffmpeg underneath.** slimv orchestrates; ffmpeg encodes.
- **Quality first, then size.** Every profile keeps resolution, frame rate, and
  pixel format — the goal is *visually transparent* output at the smallest size.
- **Measure on your own content.** `benchmark` scores real samples with VMAF, so
  the choice is data, not folklore.
- **Never delete a good source for a broken copy.** `verify` gates the delete.

## Documentation

Full docs (guides, command reference, profiles, case study) are built with
Sphinx under `docs/`. Build them with:

```bash
cd docs && python -m sphinx -b html source _build/html
```

## Tests

A fast, ffmpeg-free unit suite covers the deterministic logic (duration parsing,
the rename engine, profile-catalog invariants, the `recommend` decision rule, the
verify-filter regexes, and the CLI parser):

```bash
pip install -e ".[test]"    # or: pip install pytest
pytest
```

The suite needs no GPU, no video files, and no ffmpeg — it runs anywhere in
about a second. Encoding paths (`encode`, `benchmark`, `eyeball`,
`downscale-test`, `verify`) are exercised manually against real media.

## License

MIT
