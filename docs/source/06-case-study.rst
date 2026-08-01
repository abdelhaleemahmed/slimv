==========================================
Case study: a 206-file course, 38 GB to 14
==========================================

.. contents::
   :local:
   :depth: 2

The core ideas
==============

- **Real numbers, one real library.** A 206-lesson screen-recording video course
  (IT-certification training), **37.75 GB** of 1080p H.264, re-encoded to H.265
  and verified end to end.
- **~64% smaller, zero visible loss.** The result was **13.71 GB** — the same
  picture, a third of the bytes — confirmed both by eye and by :term:`VMAF`.
- **The encoder was chosen with data.** A :doc:`benchmark <02-commands>` on one
  representative lesson picked Intel :term:`QSV` over CPU x265: near-identical
  quality, ~2× faster, and entirely on the idle iGPU.
- **Nothing was deleted on faith.** Every one of the 206 outputs was
  full-decoded and length-checked before any source was considered removable —
  **206/206 SAFE-TO-DELETE, 0 errors.**

This chapter is the worked example behind the rest of the documentation: the same
:doc:`commands <02-commands>`, :doc:`profiles <03-profiles>`, and
:doc:`workflow <04-workflow>`, applied to one concrete job with the tool's actual
output shown.

What was on disk
================

The starting library, as reported by ``slimv check`` / ``slimv analyze``:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Files
     - 206 lessons
   * - Total size
     - 37.75 GB
   * - Container / codec
     - MP4 / H.264 (AVC), High profile
   * - Resolution
     - 1920×1080 (all files)
   * - Frame rate
     - 23.976 fps
   * - Video bitrate
     - ~3.0 Mbps average
   * - Audio
     - AAC-LC, stereo, 48 kHz
   * - Total runtime
     - ~22.5 hours

A screen-recording course like this is an ideal candidate: mostly static slides
and terminal demos, which a modern codec compresses dramatically, plus 1080p
detail worth preserving exactly.

Choosing the encoder
====================

The machine had an Intel HD 630 iGPU (idle), an NVIDIA GTX 1050 Ti (busy with
another task), and a multi-core CPU. ``slimv benchmark`` encoded a 30-second
lossless reference several ways and scored each with VMAF:

.. list-table::
   :header-rows: 1
   :widths: 28 14 14 18 26

   * - Method
     - VMAF
     - Size
     - Speed
     - Notes
   * - Intel QSV, GQ 24
     - 91.82
     - 2.43 MB
     - 1.35× realtime
     - Idle iGPU; frees CPU + NVIDIA
   * - x265 medium, CRF 24
     - 92.07
     - 2.20 MB
     - 0.62×
     - Smallest; full CPU
   * - x265 slow, CRF 24
     - 92.31
     - 2.51 MB
     - 0.31×
     - Bigger *and* slower than medium
   * - x265 medium, CRF 20
     - 92.54
     - 3.71 MB
     - 0.58×
     - +69% size for +0.5 VMAF — rejected

All four sat within **0.7 VMAF** of each other — visually identical. The choice
was therefore not about quality but about speed and freed resources:
**Intel QSV** won. It runs on hardware that was otherwise idle, so the CPU and
the busy NVIDIA card stayed free, at a file size within ~10% of the smallest.

.. note::

   VMAF was trained on natural video and under-rates sharp screen text, so ~92
   here is "visually transparent in practice." The choice was confirmed by
   watching real clips, not by the score alone — see :doc:`03-profiles`.

The conversion
==============

The whole tree was re-encoded with the ``qsv`` profile, output mirrored into a
sibling ``..._H265`` folder, originals untouched:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Result
     - Value
   * - Files converted
     - **206 / 206** (0 failures in the encode log)
   * - Output codec
     - H.265 (HEVC), 1920×1080 (unchanged)
   * - Output size
     - **13.71 GB** (from 37.75 GB)
   * - Reduction
     - **~64% smaller**
   * - Encoder
     - ``hevc_qsv`` on the Intel iGPU (CPU + NVIDIA free throughout)

Confirming the iGPU did the work
--------------------------------

Windows' Task Manager *Video Encode* graph read 0% the whole time — a known
quirk of the Intel :term:`QSV` media path, not a sign it was idle. Three reliable
checks confirmed the hardware encoder was genuinely running (see
:doc:`04-workflow`):

#. ffmpeg's own ``-v verbose`` log: *"Initialized an internal MFX session using
   hardware accelerated implementation."*
#. ``ffmpeg.exe`` sat at ~0% CPU while the output grew at ~1.9 MB/s.
#. GPU-Z's "Video Engine Load" sensor showed the Intel GPU loaded.

Verifying before deleting
=========================

Re-encoding is only safe to act on once the output is proven intact.
``slimv verify`` full-decoded every output file and compared its duration to the
source — the deletion safety gate from :doc:`04-workflow`:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Check
     - Result
   * - SAFE-TO-DELETE
     - **206 / 206**
   * - KEEP-SOURCE
     - 0
   * - Decode errors (full decode)
     - **0** across all 206
   * - Max duration delta
     - **0.05 s** (essentially frame-exact)

slimv's verdict: *"ALL VERIFIED — these sources are safe to remove."* Only with
that result in hand were the 37.75 GB of originals safe to reclaim. The full
audit trail lives in two CSVs next to the output: the per-file encode log and the
``_slimv_verify_report.csv``.

What this demonstrates
======================

The job exercised the whole tool in order — ``analyze`` and ``check`` to see what
was on disk, ``benchmark`` to choose the encoder on real footage, ``encode`` to
convert, and ``verify`` to make deletion safe — and it is the reason slimv has
the shape it does. Every command in :doc:`02-commands` earned its place on a real
library: the size win came from the right :term:`profile`, the confidence came
from VMAF plus a full-decode pass, and the safety came from never trusting a
build's "success" message over an actual decode.
