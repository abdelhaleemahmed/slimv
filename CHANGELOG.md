# Changelog

All notable changes to slimv are recorded here. Versions follow
`MAJOR.MINOR.PATCH`.

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
