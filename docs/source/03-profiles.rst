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
     - Very fast (NVIDIA) / small
     - NVIDIA GPU idle; big batches.
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
- **Smallest files matter more than speed?** ``balanced`` / ``quality`` (x265) or
  ``qsv`` (Intel) — more efficient per byte.

Numbers vary with content and GPU generation; run ``slimv benchmark`` on your own
footage to see your card's figures.

Optimizing NVENC for size instead of speed
------------------------------------------

NVENC's size dial is ``-cq`` (higher = smaller, like :term:`CRF` run backwards).
Note that ``--gq``/``--crf`` **don't apply to NVENC** — they target QSV's
``-global_quality`` and x265's ``-crf``, so slimv ignores them (with a warning) on
an NVENC profile. To make NVENC files smaller, define a variant in
``profiles.toml`` — raise ``-cq`` and add efficiency flags (multipass, spatial
adaptive-quantization, lookahead, extra B-frames):

.. code-block:: toml

   [nvenc-small]
   codec    = "hevc_nvenc"
   vargs    = ["-c:v","hevc_nvenc","-preset","p7","-tune","hq","-rc","vbr","-cq","30",
               "-multipass","fullres","-spatial_aq","1","-rc-lookahead","20","-bf","3","-tag:v","hvc1"]
   when     = "NVENC tuned for smaller files"
   hardware = true

Then ``slimv encode SRC DST --profile nvenc-small``. This *narrows* the gap, but a
fixed-function encoder still won't match a software one per byte. **So if smallest
size is the real goal, use** ``balanced`` / ``quality`` **(x265) or** ``qsv`` **—
not NVENC.** NVENC earns its place on *speed* (big batches, idle GPU), not size.
(A few flags like ``-temporal_aq`` / ``-b_ref_mode`` need a Turing-or-newer card;
the set above works on older GPUs too.)

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
