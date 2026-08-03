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
     - hevc_nvenc CQ 36 + multipass/AQ
     - Transparent
     - Fast (NVIDIA) / small
     - **NVIDIA idle; want speed *and* small files. Dial with** ``--cq``.
   * - ``amf`` / ``amf-hq``
     - hevc_amf CQP 26 / 28
     - *Experimental* — unverified on AMD
     - Fast (AMD) / small
     - AMD Radeon; benchmark first (see *Hardware support*).
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

Hardware support: what runs on which card
=========================================

Each profile hard-codes one encoder, and that encoder only exists if **both** your
hardware **and** your ffmpeg build provide it. Here is exactly what runs where — no
guessing:

.. list-table:: Which built-in profiles run on which hardware
   :header-rows: 1
   :widths: 24 30 46

   * - Your hardware
     - Built-in profiles that run
     - Notes
   * - **Any CPU** (every machine)
     - ``archive`` ``quality`` ``balanced`` ``small`` (x265) · ``av1`` (SVT-AV1)
     - No GPU needed — the **universal fallback**. Slower, but the smallest files, and
       runs anywhere: AMD boxes, ARM, VMs, headless servers.
   * - **Intel** iGPU / Arc (Quick Sync)
     - ``qsv`` ``qsv-hq`` ``qsv-720p`` ``qsv-480p`` — plus all CPU profiles
     - HEVC Quick Sync needs **Skylake / 6th-gen (2015) or newer**, or an Arc dGPU.
       Older Intel → CPU profiles only.
   * - **NVIDIA** (HEVC NVENC)
     - ``nvenc`` ``nvenc-hq`` — plus all CPU profiles
     - Needs **Maxwell 2nd-gen (GTX 900-series) or newer**. Kepler / Maxwell-1st-gen
       have H.264-only NVENC → no ``hevc_nvenc``. ``nvenc-hq`` is tuned Pascal-safe;
       Turing+ can add more flags (see the GPU-generation caveat below).
   * - **AMD** Radeon
     - ``amf`` ``amf-hq`` (*experimental*) — plus all CPU profiles
     - HEVC via ``hevc_amf``. **Experimental: not yet verified on AMD hardware** — run
       ``slimv benchmark`` and tune the ``qp`` (below) before trusting a library. The
       CPU/AV1 profiles are the always-safe alternative.
   * - **Apple Silicon / other**
     - CPU profiles (``libx265`` / ``libsvtav1`` if your ffmpeg has them)
     - No VideoToolbox profile ships; the CPU profiles run regardless.

**Don't guess — ask the tool.** ``slimv hwcheck`` lists your GPUs and exactly which
encoders your ffmpeg has (and recommends one); ``slimv profiles`` marks every profile
**available / not available** on this host. If you pick a profile whose encoder is
absent, slimv fails **loudly on the first file** rather than silently swapping engines
(see the manual's *"Why slimv doesn't silently fall back"*).

**Tuning ``amf`` (or adding any other encoder) — no code edit.** The shipped ``amf`` /
``amf-hq`` profiles use ``hevc_amf`` at a fixed ``qp`` (26 / 28). To change that ``qp``,
or to add an encoder with no built-in profile at all, drop a ``profiles.toml`` (see
*Customizing profiles* below) — a table named after a built-in **overrides** it:

.. code-block:: toml

   [amf]
   codec = "hevc_amf"
   vargs = ["-c:v", "hevc_amf", "-quality", "quality",
            "-rc", "cqp", "-qp_i", "24", "-qp_p", "24", "-tag:v", "hvc1"]

Then ``slimv encode SRC DST --profile amf``. The exact AMF options vary by ffmpeg build —
check ``ffmpeg -h encoder=hevc_amf`` — and AMF's quality-per-byte differs from QSV/NVENC,
so **run** ``slimv benchmark`` **on your own content** to find the ``qp`` that stays
transparent before committing to a library. (The same recipe covers ``h264_amf``,
``av1_qsv``, VideoToolbox, etc. — one ``[table]`` per encoder.)

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
  ``-spatial_aq`` (adaptive quantization) and ``-rc-lookahead``, at ``-cq 36``
  (the default, validated transparent on slide/screen content — see below);
- the **``--cq``** override — NVENC's size dial (higher = smaller). ``--gq``/``--crf``
  target QSV/x265 and are *ignored* on NVENC with a warning, so ``--cq`` is the one
  to use here.

**The two NVIDIA profiles at a glance** — same encoder, same GPU, only the
efficiency flags and CQ differ:

.. list-table::
   :header-rows: 1
   :widths: 16 46 38

   * - Profile
     - ffmpeg settings
     - Result
   * - ``nvenc``
     - ``-preset p7 -rc vbr -cq 24``
     - Fastest, but **large** — no efficiency features, and cq 24 over-spends bits.
   * - ``nvenc-hq``
     - ``-preset p7 -tune hq -rc vbr -cq 36 -multipass fullres -spatial_aq 1
       -rc-lookahead 20``
     - Two-pass + adaptive-quantization + lookahead at a leaner CQ → **smaller than
       the iGPU**, still transparent on slides/text, still fast.

Every ``nvenc-hq`` flag, in order:

- ``-c:v hevc_nvenc`` — encode H.265 on NVIDIA's hardware encoder (NVENC).
- ``-preset p7`` — NVENC's *effort* preset: **p1 (fastest) → p7 (best quality)**.
  p7 already asks for its best quality (analogous to x265's ``veryslow``).
- ``-tune hq`` — the **high-quality** tuning, as opposed to NVENC's low-latency
  tunings (``ll``/``ull``, meant for live streaming). It biases the encoder toward
  picture quality over latency — what you want for offline re-encoding.
- ``-rc vbr`` — **variable-bitrate** rate control; paired with ``-cq`` it means
  "hold this quality, vary the bitrate as the picture needs" (vs ``cbr`` = constant
  bitrate for streaming, or ``constqp`` = a fixed quantizer).
- ``-cq 36`` — the **quality/size dial** (higher = smaller, like CRF run backwards).
  The biggest lever: the default ``nvenc`` profile's ``cq 24`` chases quality the eye
  can't see; ``cq 36`` sheds it while staying transparent on slide/screen content.
  Lower it (e.g. ``--cq 33``) for motion-heavy / natural-video sources, where the eye
  is more sensitive (see the VMAF discussion in *Understanding video compression*).
- ``-multipass fullres`` — encode each frame **twice** (a full-resolution analysis
  pass, then the real pass) for smarter bit allocation → smaller at the same quality.
- ``-spatial_aq 1`` — **spatial adaptive quantization**: spend fewer bits on flat
  areas and more on detailed ones, matching where the eye actually looks.
- ``-rc-lookahead 20`` — let the rate controller **look ahead 20 frames** before
  deciding how many bits to spend, so it plans for what's coming.
- ``-tag:v hvc1`` — a container tag so Apple/QuickTime players recognize the HEVC
  stream (without it, some players show a black screen).

.. code-block:: bash

   slimv encode SRC DST --profile nvenc-hq            # tuned, cq 36 (default)
   slimv encode SRC DST --profile nvenc-hq --cq 33    # a touch higher quality (motion)
   slimv encode SRC DST --profile nvenc-hq --cq 40    # smaller still

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
- **Tuning fixes it.** ``nvenc-hq`` (multipass + spatial-AQ + lookahead) at ``cq 32``
  dropped it to 54 MB; at its **default ``cq 36``** it reached **38.8 MB — smaller than
  the iGPU** — both still transparent. ``cq 36`` is the shipped default, chosen after a
  frame-accurate quality pass over a full course (below).
- **You keep the speed.** ~90 s versus the iGPU's ~30 min — about **19× faster** at
  matched-or-smaller size.
- **Eye-verified, not just VMAF.** The cq 36 output (smaller than the iGPU) was
  compared frame-for-frame against the source on its fine on-screen text — the
  first thing to soften under compression — and looked clean, confirming the score
  by eye.

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
