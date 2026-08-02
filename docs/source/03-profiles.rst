========
Profiles
========

.. contents::
   :local:
   :depth: 2

The core ideas
==============

- **A profile is a quality-preserving recipe.** It fixes the codec and
  rate-control; resolution, frame rate, and pixel format never change.
- **Lower number, higher quality.** :term:`CRF` (x265/AV1) and
  ``global_quality`` (QSV) / ``cq`` (NVENC) all run *backwards* — a lower value
  means better quality and a bigger file. The numbers are **not** comparable
  across codecs.
- **Audio is normalized.** Every profile re-encodes audio to AAC 128k —
  transparent for speech; raise it for music with ``--audio-kbps``.
- **Hardware profiles trade a little size for a lot of speed.** ``qsv`` and
  ``nvenc`` are ~2× faster and run on otherwise-idle silicon.

Pick a profile with :doc:`benchmark <02-commands>` on your own footage rather
than from the table alone; the catalog below is the starting point. The profile
data lives in :mod:`slimv.profiles`.

The catalog
===========

.. list-table::
   :header-rows: 1
   :widths: 12 22 22 18 26

   * - Profile
     - Encoder / setting
     - Quality
     - Speed / size
     - Use when
   * - ``archive``
     - libx265 CRF 18
     - Near-lossless (VMAF ~97+)
     - Slow (CPU) / largest H.265
     - Masters, archival, precious sources.
   * - ``quality``
     - libx265 CRF 20
     - Transparent + margin
     - Medium (CPU) / larger
     - Detail- or text-heavy footage; safety margin.
   * - ``balanced``
     - libx265 CRF 23
     - Transparent
     - Medium (CPU) / small
     - General default on CPU; smallest CPU-encoded files.
   * - ``small``
     - libx265 CRF 26
     - Good; fine text may soften
     - Slow (CPU) / smallest (CPU)
     - Low-detail slides / talking-head.
   * - ``qsv``
     - hevc_qsv GQ 24
     - Transparent (~VMAF 92 on screen)
     - Fast (Intel iGPU) / small
     - **Intel Quick Sync present — recommended all-rounder.**
   * - ``nvenc``
     - hevc_nvenc CQ 24
     - Transparent
     - Very fast (NVIDIA) / large
     - NVIDIA idle; max speed, size doesn't matter.
   * - ``nvenc-hq``
     - hevc_nvenc CQ 32 + multipass/AQ
     - Transparent
     - Fast (NVIDIA) / small
     - **NVIDIA idle; want speed *and* small files. Dial with** ``--cq``.
   * - ``av1``
     - libsvtav1 CRF 30
     - Transparent
     - Slow (CPU) / smallest overall
     - Max compression and players support AV1.

Choosing a profile
==================

If you have an Intel iGPU, ``qsv`` is the sweet spot: near-x265 quality, roughly
twice the speed, and it runs on hardware that is otherwise idle so your CPU and
any discrete GPU stay free. Want the absolute smallest CPU-encoded files and have
the time to spend? ``balanced``. Need a safety margin for fine on-screen text?
``quality``. Whatever the starting guess, run ``slimv benchmark`` on one
representative file to confirm the quality and size on *your* content before
committing to a long run.

NVENC acceleration, measured
============================

Hardware encoders trade a little size for a lot of speed. On a representative
**1080p H.264 lecture** (30 fps, ~3.4 Mbps), a 30-second ``slimv benchmark``
sample compared NVIDIA **NVENC** against the CPU x265 profiles, on an **NVIDIA
GeForce GTX 1050 Ti** (idle):

.. list-table::
   :header-rows: 1
   :widths: 26 12 16 26 12

   * - Profile
     - VMAF
     - Size (30 s)
     - Speed
     - Hardware
   * - ``balanced`` (x265 CRF 23)
     - 93.6
     - 5.3 MB
     - 0.65× realtime (~20 fps)
     - CPU
   * - ``quality`` (x265 CRF 20)
     - 94.3
     - 8.1 MB
     - 0.60× realtime (~18 fps)
     - CPU
   * - ``nvenc`` (hevc_nvenc CQ 24)
     - 94.8
     - 13.6 MB
     - **3.11× realtime (~93 fps)**
     - NVIDIA

**Reading the columns.** *VMAF* is picture quality versus a lossless reference —
higher is closer to the original; ~92+ is visually transparent for screen content
(see the VMAF note below). *Size* is the 30-second sample's output — a stand-in for
how small the full file lands. *Speed* is the encode rate relative to real-time
playback: ``3.11× realtime`` means it encodes 3.11 seconds of video per second
(~93 fps for 30 fps footage), while ``0.65×`` is *slower* than playback. *Hardware*
is which engine did the encode (GPU vs CPU).

**~5× faster, at equivalent quality.** NVENC encoded the sample at ~93 fps versus
~18–20 fps on the CPU — about five times quicker — while all three profiles land
within ~1.2 VMAF of each other (visually equivalent for this content).

**The trade-off is size.** NVENC's output is ~2.6× larger than ``balanced`` for
the same quality: a fixed-function encoder optimizes for speed, not per-byte
efficiency. So the choice is by goal:

- **Big batch, GPU idle, encode time matters?** ``nvenc`` — finish in a fraction
  of the time. Pair with ``--hwdec cuda`` for a full-NVIDIA decode→encode pipeline.
- **Smallest files matter more than speed?** ``balanced`` / ``quality`` (x265),
  ``qsv`` (Intel), or a **tuned** ``nvenc-hq`` (below) — the default ``nvenc`` is
  the least efficient per byte.

Numbers vary with content and GPU generation; run ``slimv benchmark`` on your own
footage to see your card's figures.

Optimizing NVENC for size: ``nvenc-hq`` and ``--cq``
----------------------------------------------------

The default ``nvenc`` profile aims for more quality than the eye needs (``cq 24``)
and uses none of NVENC's efficiency features, so its files come out large. Two
built-in fixes:

- the **``nvenc-hq``** profile — adds ``-multipass fullres`` (two-pass),
  ``-spatial_aq`` (adaptive quantization) and ``-rc-lookahead``, at ``-cq 32``;
- the **``--cq``** override — NVENC's size dial (higher = smaller). ``--gq``/``--crf``
  target QSV/x265 and are *ignored* on NVENC with a warning, so ``--cq`` is the one
  to use here.

.. code-block:: bash

   slimv encode SRC DST --profile nvenc-hq            # tuned, cq 32
   slimv encode SRC DST --profile nvenc-hq --cq 36    # smaller still

The measured before/after is in the next section.

.. note:: GPU-generation caveat

   ``-multipass``, ``-spatial_aq`` and ``-rc-lookahead`` work on older cards (tested
   on a Pascal GTX 1050 Ti). **HEVC B-frames (``-bf``), ``-temporal_aq`` and
   ``-b_ref_mode`` need a Turing-or-newer GPU** — they fail to open the encoder on
   Pascal, so ``nvenc-hq`` omits them. On a newer card, adding them via
   ``profiles.toml`` shrinks NVENC further.

Same file, four ways: the default trap and the tuned fix
--------------------------------------------------------

The **same 1080p H.264 lecture** (~18 min, ~600 kbps) encoded several ways — Intel
Quick Sync (``qsv-hq``), the default NVIDIA ``nvenc``, and the tuned ``nvenc-hq``
(all NVIDIA runs used ``--hwdec cuda`` for a full-GPU pipeline):

.. list-table::
   :header-rows: 1
   :widths: 28 14 14 12 22

   * - Encode
     - Size
     - vs source
     - VMAF
     - Time
   * - source (H.264)
     - 81.7 MB
     - —
     - —
     - —
   * - ``qsv-hq`` (Intel iGPU)
     - 47.9 MB
     - −41 %
     - 96.4
     - ~30 min
   * - default ``nvenc``
     - 95.4 MB
     - **+17 % (larger!)**
     - 97.1
     - **65 s**
   * - ``nvenc-hq`` cq 32
     - 54.2 MB
     - −34 %
     - 95.5
     - 93 s
   * - ``nvenc-hq`` cq 36
     - **38.8 MB**
     - **−52 %**
     - 94.1
     - 90 s

The story in three steps:

- **The default NVENC is the trap** — ~28× faster than QSV, but its file came out
  *larger than the source* (it targets VMAF 97, spending bits the eye can't see,
  with no efficiency features). Under ``--keep-smaller`` it would be **rejected** —
  saving nothing.
- **Tuning fixes it.** ``nvenc-hq`` (multipass + spatial-AQ + lookahead, cq 32)
  dropped it to 54 MB; ``--cq 36`` reached **38.8 MB — smaller than the iGPU** — both
  still transparent.
- **You keep the speed.** ~90 s versus the iGPU's ~30 min — about **19× faster** at
  matched-or-smaller size.

So "QSV for size, NVENC for speed" holds *only for the default profile*: **tuned
NVENC gives you both.** Always ``benchmark`` your own content — the right ``--cq``
depends on it.

Customizing profiles (no code edits)
====================================

You don't edit Python to change a profile. Two ways:

- **Ad-hoc overrides** on ``encode`` for a one-off:

  .. code-block:: bash

     slimv encode SRC DST --profile qsv --gq 22       # QSV quality dial
     slimv encode SRC DST --profile balanced --crf 22 # x265 CRF dial
     slimv encode SRC DST --profile qsv --scale 720   # downscale (keeps aspect)
     slimv encode SRC DST --profile qsv --preset slow # encoder preset

  An override that doesn't fit the chosen profile's codec (e.g. ``--crf`` on a
  QSV profile) is warned about and ignored.

- **A** ``profiles.toml`` **file** for persistent custom/overridden profiles,
  merged over the built-ins. Searched (later wins): the user config dir
  (``%APPDATA%\slimv\`` or ``~/.config/slimv/``), the current directory, then
  ``$SLIMV_PROFILES``. Each ``[table]`` is one profile (``codec`` and ``vargs``
  required); a table named after a built-in overrides it. See
  ``profiles.toml.example`` for a template.

  .. code-block:: toml

     [qsv-21]
     codec    = "hevc_qsv"
     vargs    = ["-c:v","hevc_qsv","-preset","veryslow","-global_quality","21","-tag:v","hvc1"]
     when     = "a touch above qsv-hq"
     hardware = true

A note on VMAF for screen content
=================================

:term:`VMAF` was trained on natural video and tends to *under-rate* screen
recordings with sharp text and line art. A score around 92 on a screencast
corresponds to "visually transparent in practice," not "visibly flawed." For
text-heavy material, confirm with your own eyes on a couple of clips rather than
trusting the number alone.
