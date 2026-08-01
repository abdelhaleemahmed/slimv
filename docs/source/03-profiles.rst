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
