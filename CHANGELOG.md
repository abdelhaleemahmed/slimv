# Changelog

All notable changes to slimv are recorded here. Versions follow
`MAJOR.MINOR.PATCH`.

## [Unreleased]

## [0.2.1] — 2026-08-03

### Added
- **Per-file timing in the encode log** — `_slimv_encode_log.csv` gains `EncSec`
  (wall-clock encode time) and `SpeedxRT` (× realtime = `SrcDur / EncSec`) columns,
  and `encode` prints an end-of-run speed summary (avg / median / slowest / fastest
  × realtime, total encode time).
- **`--cq` override** for `encode` — NVENC's quality/size dial (higher = smaller);
  `--gq`/`--crf` target QSV/x265 and are ignored on NVENC.
- **Zero-copy CUDA decode** — `--hwdec cuda` now keeps decoded frames GPU-resident
  (`-hwaccel_output_format cuda`), like the QSV path. Measured ~3.6 vs ~6.5
  CPU-seconds per 90 s clip and ~2× faster than the old RAM round-trip.
- **`nvenc-hq` profile** — NVENC tuned for size (`-multipass fullres`,
  `-spatial_aq`, `-rc-lookahead`), **default `-cq 36`**. Measured on a Pascal GTX
  1050 Ti it cut a lecture from the default `nvenc`'s 95 MB to 39 MB (cq 36) — smaller
  than the iGPU, still transparent, and ~19× faster than the iGPU.

### Changed
- **`nvenc-hq` default CQ raised 32 → 36.** A frame-accurate VMAF + visual pass over a
  full slide-heavy course confirmed `cq 36` is visually lossless on screen/text content
  at 30–40 % smaller than the iGPU. Use `--cq 33` for motion-heavy sources.

### Docs
- New guide section explaining the encoders and quality dials (CRF /
  global_quality / CQ) and what NVENC's args mean.
- Measured NVENC-vs-iGPU comparisons and the CQ sweep in the profiles page;
  note that HEVC B-frames / `-temporal_aq` / `-b_ref_mode` require a Turing+ GPU.
- **VMAF ceiling on screen content**: documented that VMAF of an identical clip reads
  ~97.6 (not 100) on slides — read scores against that ceiling, and where VMAF *is*
  accurate (natural/motion video).

## [0.2.0] — 2026-08-01

### Added
- New commands: **`eyeball`** (write original + per-profile sample clips to a
  folder to compare by eye), **`downscale-test`** (measure the size *and* quality
  cost of downscaling), **`rename`** (bulk-remove text from filenames), and
  **`analyze --measure`** (sample-encode to project the real saving).
- Sample windows accept **seconds or minutes** on `benchmark`, `eyeball`,
  `downscale-test`, `recommend`, and `analyze --measure` — `90`, `30s`, `2m`,
  `1m30s`, or `1:30`.
- `LICENSE` (MIT) and author metadata; `--version` shows author/contact.
- A fast, ffmpeg-free **pytest** suite and `[test]` extra.
- Docs: virtual-environment install steps, a full ffmpeg feature/version table,
  and the Intel Quick Sync runtime + telemetry (`esrv`) gotcha.

### Changed
- Internal lossless references now use **`ffv1`** (native), removing the
  `libx264` dependency for `downscale-test`/`eyeball`.
- Documentation converted from Markdown to **reStructuredText** (uniform Sphinx
  source).

## [0.1.0] — initial

- Core commands: `hwcheck`, `profiles`, `analyze`, `check`, `test`, `benchmark`,
  `recommend`, `encode`, `verify`.
- Quality-preserving profile catalog (x265 / QSV / NVENC / AV1), VMAF
  benchmarking, and a full-decode verify gate before any source is deleted.
