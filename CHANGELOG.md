# Changelog

All notable changes to slimv are recorded here. Versions follow
`MAJOR.MINOR.PATCH`.

## [Unreleased]

### Docs
- **Landing page**: reworked the "What it does" block into a fuller **Features**
  section (6 cards) and refreshed the command list to include ``report`` and
  ``verify-report``.
- Added a worked example — **"a source whose audio isn't AAC"** — to the compression
  guide (and a ``--copy-audio`` caveat in the command reference): WMA/PCM/Vorbis can't
  stream-copy into ``.mp4``, so omit ``--copy-audio`` and let it re-encode to AAC.
  Uses a ``wmv3`` course that needs both CPU decode *and* AAC audio.
- Expanded the legacy-codec coverage in the compression guide with **"MPEG-4, the
  bigger picture"** (the family: Part 2 vs Part 10/H.264, object-based coding) and
  **"Two more legacy codecs you'll still meet"** — **WMV3** (Windows Media 9 / VC-1
  ancestor) and **VP8** (WebM). Both include the practical note that NVDEC/QSV don't
  reliably decode them, so re-encode with CPU decode (no ``--hwdec``).
- New **"The codec inside: MPEG-4 ASP (DivX & Xvid)"** section in the compression
  guide (the AVI chapter) — the history (DivX ;-) → Xvid → eclipsed by H.264), a
  DivX-vs-Xvid comparison, the technical comparison vs H.264, how to spot it
  (``mpeg4`` / DIVX/XVID FourCC), and the two re-encode gotchas: NVDEC/QSV can't
  hardware-decode it (ffmpeg falls back to software), and old ``.avi`` duration
  metadata is often inflated — which looks like truncation but isn't, and which
  ``verify`` reconciles by frame count.

## [0.3.1] — 2026-08-09

### Changed
- **`report` now prints an `Output` row** (the destination folder) alongside `Source`,
  so a course report shows both paths at a glance — matching `verify-report`.

### Added
- **`slimv verify-report <dst>` — live verify progress.** A house box for a running
  (or finished) `verify`: files verified / total, the file currently being checked,
  verify speed (files/min + × realtime), an ETA (from the remaining files' real
  durations), and safe / corrupted counts, with source + output paths. Reads the
  reports a verify writes incrementally — the canonical `_slimv_verify_report.csv`
  **and** `_verify*.csv` shard files — so it works mid-run during a parallel
  (sharded) verify. **`--list-corrupted`** prints the full path of every file that
  failed verification (decode errors / length mismatch) instead of the box, so bad
  files are easy to act on. Read-only. Regression-tested.

## [0.3.0] — 2026-08-09

### Added
- **`slimv report <dst>` — one-call course summary.** Rolls an encode run's
  `_slimv_encode_log.csv` into the house vertical box (a **full-width title
  banner** over `label │ value` rows): files done / total, total source size →
  output size, saved % + reclaim + ratio, average speed, **when it started**,
  **elapsed wall-clock so far**, an ETA, and the source path. Pass **`--src <folder>`** and it counts the whole source tree, so
  mid-run it reports the **total** file count and size and **projects the final
  ("expected") output size** from the compression achieved so far; figures it
  projects are marked with `~`. The **ETA sums the real durations of the files
  still to encode** (probed concurrently) divided by the measured average speed —
  not a bitrate guess — falling back to a size estimate only for a file ffprobe
  can't read. Adds a `Verify` row when a
  `_slimv_verify_report.csv` is present and a `Failed` row when any file didn't
  produce an output. De-duplicates the log by file (a re-encoded or
  fail-then-succeed file counts once, by its latest status). Read-only.
  Regression-tested.

### Changed
- **`verify` is now resumable, interruptible, and shardable.** The report is
  rewritten atomically after **every file** (not just at the end), so a run you
  Ctrl-C — or one killed by a sleep/restart — can be re-run and it **skips
  everything already verified**, continuing where it left off. New
  **`--skip`/`--limit`** slice the file list and **`--report PATH`** sends a run's
  report to its own file, so two processes can verify different slices in parallel
  without clobbering each other (verify is decode-bound, so parallel shards can
  finish sooner — unlike encode, where one stream already saturates the GPU).
  Regression-tested.

### Fixed
- **A locked `.partial` no longer crashes the whole batch.** After an `ENCODE-FAIL`, a
  freshly-written `.partial` could still be held by the exiting ffmpeg (or an AV
  scanner), so the cleanup `unlink()` raised `PermissionError` (WinError 32) and took
  down the entire run mid-encode. All five `.partial` filesystem ops (pre-clear, the
  three cleanup paths, and the finalize rename) are now **lock-tolerant**: they retry
  briefly, then either continue quietly (cleanup) or log a per-file `MOVE-FAIL` and move
  on (finalize) — one locked file never stops the batch. Regression-tested.

## [0.2.2] — 2026-08-03

### Added
- **`amf` / `amf-hq` profiles** — AMD hardware HEVC via `hevc_amf`. **Experimental: not
  yet verified on AMD hardware by the maintainer.** The wiring is unit-tested, but the
  actual encode/quality needs confirming on a real Radeon — run `slimv benchmark`, adjust
  the `qp` via `profiles.toml`, and please report results.

### Docs
- New **"Hardware support: what runs on which card"** matrix in the profiles page: which
  built-in profiles run on Intel / NVIDIA / AMD / CPU, the GPU-generation floors (HEVC
  QSV = Skylake+, HEVC NVENC = Maxwell-2nd-gen+), and the `profiles.toml` recipe for AMD
  and other encoders without a built-in profile.

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
