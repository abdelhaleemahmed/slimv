==================
Command reference
==================

.. contents::
   :local:
   :depth: 2

The core ideas
==============

- **One verb each.** Investigation — ``hwcheck``, ``profiles``, ``analyze``,
  ``check``, ``test``, ``benchmark``, ``eyeball``, ``downscale-test``,
  ``recommend``; production — ``encode``; safety — ``verify``; housekeeping —
  ``rename``.
- **Read before you write.** Everything except ``encode`` (which produces video)
  and ``rename --apply`` (which renames files) is read-only investigation;
  ``verify`` never deletes.
- **Everything is logged.** ``encode`` and ``verify`` write CSV reports next to
  the output so a run is auditable after the fact.
- **Samples take seconds or minutes.** ``benchmark``, ``eyeball``,
  ``downscale-test``, ``recommend`` and ``analyze --measure`` accept
  ``--start``/``--length`` as ``90``, ``30s``, ``2m``, ``1m30s`` or ``1:30``.

Each command maps to a function in the :doc:`API <05-api>`; the headings below
link to the implementation.

hwcheck
=======

Show GPUs and which encoders ffmpeg exposes, recommend one, and explain how to
*confirm* a hardware encoder is genuinely being used. Implemented by
:func:`slimv.hardware.run`.

.. code-block:: bash

   slimv hwcheck

profiles
========

List the encoding :term:`profile` s with quality/speed/size and when to use
each. See :doc:`03-profiles` for the full catalog.

.. code-block:: bash

   slimv profiles

analyze
=======

Probe a file or a whole folder (codec, resolution, bitrate, size), summarize it,
and recommend a profile with a projected saving. Implemented by
:func:`slimv.analyze.run`.

.. code-block:: bash

   slimv analyze "C:\Videos\Course"
   slimv analyze "C:\Videos\Course" --measure                # project the REAL saving
   slimv analyze "C:\Videos\Course" --measure --sample-length 1m

By default the projected saving is a codec-based estimate (~45–60% for H.264).
``--measure`` instead sample-encodes a bitrate spread of the files and projects
the **actual** saving measured on this content; ``--sample-length`` sets each
sample's length (seconds or minutes).

check
=====

Health-scan a file or folder on its own: report each file's codec and
resolution, run a full decode to flag **corrupted/unreadable** files, and print
stats (totals, by-codec, by-resolution, healthy vs. problem counts). Unlike
``verify``, it needs no second tree; unlike ``analyze``, it adds an integrity
pass. Implemented by :func:`slimv.check.run`.

.. code-block:: bash

   slimv check "C:\Videos\Course"            # full decode of every file
   slimv check "C:\Videos\Course" --quick    # ffprobe only (fast; header check)
   slimv check "C:\Videos\Course" --list     # show every file, not just problems

Exit code is non-zero if any file is corrupt, so it works as a scripted gate.
slimv skips its own in-progress ``*.partial.mp4`` temp files, so scanning a
folder mid-conversion is safe.

test
====

Encode a 5-second synthetic clip with one encoder and fully decode it back, then
report whether it ran on **hardware** or fell back to **software**. Implemented
by :func:`slimv.sanity.run`.

.. code-block:: bash

   slimv test hevc_qsv
   slimv test libx265

benchmark
=========

Encode a short sample with several profiles and score each with :term:`VMAF`, so
you choose quality-vs-size on real footage. Implemented by
:func:`slimv.benchmark.run`.

.. code-block:: bash

   slimv benchmark "C:\Videos\Course\lesson1.mp4"
   slimv benchmark lesson1.mp4 --start 2m --length 30s

The benchmark extracts a *lossless* reference segment first and encodes from it,
so the VMAF comparison is frame-aligned and trustworthy. ``--start``/``--length``
take seconds or minutes (``90``, ``30s``, ``2m``, ``1m30s``, ``1:30``).

eyeball
=======

Encode the same sample with several profiles and write the clips — plus the
original segment — into a folder, so you can **watch** them side by side. VMAF
under-reads sharp screen text and handwriting, so for that content the eye is the
referee. Implemented by :func:`slimv.eyeball.run`.

.. code-block:: bash

   slimv eyeball "C:\Videos\Course\lesson1.mp4"
   slimv eyeball "C:\Videos\Course" --start 5m --length 20s --profiles qsv,qsv-hq

Pass a folder and it samples the largest file (usually a full lecture). Clips go
to ``./slimv_eyeball/<file>/`` by default (``--out`` to change) and the path is
printed at the end. Nothing is scored; nothing is deleted.

downscale-test
==============

slimv's profiles keep resolution; this command measures whether **downscaling**
(e.g. 1080p→720p) is worth it. It encodes a sample at native resolution and at
the target height, then scores the downscaled encode *fairly* — upscaled back to
native and VMAF'd against the native lossless reference (what a viewer on a
native-resolution screen actually sees). Implemented by
:func:`slimv.downscale.run`.

.. code-block:: bash

   slimv downscale-test "C:\Videos\Course\lesson1.mp4"                # 720p by default
   slimv downscale-test lesson1.mp4 --scale 900 --profile qsv-hq --length 20s

The table shows VMAF-vs-native and projected full-file size for each variant, so
you can weigh the size win against the quality cost. Clips are left on disk to
eyeball — in ``./slimv_downscale/<file>/`` by default (``--out`` to change), and
the path is printed at the end.

recommend
=========

Run the benchmark, then apply a decision rule to **pick the best profile
automatically** and print the exact ``encode`` command. Holds quality first,
then prefers the smallest file — but takes a hardware encoder when it reaches
effectively the same quality at a competitive size, because it frees the CPU.
Implemented by :func:`slimv.recommend.run`.

.. code-block:: bash

   slimv recommend "C:\Videos\Course\lesson1.mp4" --out "C:\Encoded\Course"
   slimv recommend lesson1.mp4 --min-vmaf 90 --length 30s

Options: ``--start``/``--length`` (sample window, seconds or minutes),
``--out`` (destination printed in the encode command), ``--min-vmaf`` (quality
floor, default 90), ``--vmaf-tol`` (VMAF gap from the best still treated as
transparent, default 2.0).

encode
======

Batch re-encode a source tree into a mirrored output tree, verifying duration and
writing a CSV log. Resumable — files whose output already exists are skipped.
Implemented by :func:`slimv.encode.run`.

.. code-block:: bash

   slimv encode "C:\Videos\Course" "C:\Videos\Course_slimv" --profile qsv
   slimv encode SRC DST --profile qsv-hq --hwdec qsv --copy-audio --keep-smaller

Output goes to ``DST`` mirroring the source folder structure; originals are
untouched. A per-file log lands at ``DST/_slimv_encode_log.csv``.

Options:

- ``--profile`` (default ``qsv``) — the encoding :term:`profile` (see :doc:`03-profiles`).
- ``--keep-smaller`` — if a re-encode isn't smaller than its source, keep the
  original (protects already-lean files from growing).
- ``--copy-audio`` — copy the source audio stream instead of re-encoding to AAC;
  use when the source is already AAC at a fine bitrate (avoids a needless re-encode).
- ``--hwdec`` — decode the source on a GPU (``qsv``/``cuda``/``d3d11va``) to free
  the CPU. Use with non-scaling profiles; it frees the CPU, it does not speed up
  an encode-bound job.
- ``--scale`` — downscale to this height, e.g. ``--scale 720`` (keeps aspect).
  Measure the cost first with ``downscale-test``.
- ``--gq`` / ``--crf`` / ``--preset`` — override the profile's quality/preset
  (QSV ``global_quality`` / x265·AV1 ``CRF`` / encoder preset; lower number = higher quality).
- ``--audio-kbps`` (default 128) — AAC bitrate when audio *is* re-encoded.
- ``--skip`` / ``--limit`` — skip the first N files / encode at most N (handy for
  testing settings on a subset first).

verify
======

The deletion safety gate. For every source it confirms the converted file
exists, matches the original length, and decodes with zero errors — marking each
``SAFE-TO-DELETE`` or ``KEEP-SOURCE``. Read-only; it never deletes anything.
Implemented by :func:`slimv.verify.run`.

.. code-block:: bash

   slimv verify "C:\Videos\Course" "C:\Videos\Course_slimv"
   slimv verify SRC DST --hwaccel qsv     # run the integrity pass on the iGPU

A report is written to ``DST/_slimv_verify_report.csv`` with a verdict and reason
per file. Only delete originals whose row says ``SAFE-TO-DELETE``.

Options:

- ``--hwaccel`` — hardware decoder for the integrity pass (``qsv``/``cuda``/``d3d11va``);
  ~4× faster. Default is CPU software decode — the safest choice for a deletion gate,
  and any hardware-decode error is re-confirmed on the CPU before it's trusted.
- ``--quick`` — skip the full-decode integrity pass (existence + duration only).
- ``--full`` — force a complete re-verify, ignoring cached verdicts (default reuses
  unchanged outputs that already passed).
- ``--tol`` (default 1.0) — duration tolerance, in seconds.

rename
======

Bulk-remove a text fragment from filenames — e.g. strip a site tag that prefixes
every downloaded lesson — keeping the rest of the name and the extension.
**Dry-run by default**: it prints the ``old -> new`` changes and renames nothing
until ``--apply``. Implemented by :func:`slimv.rename.run`.

.. code-block:: bash

   slimv rename "C:\Courses\MyCourse" "[SomeSite.com] - "           # preview
   slimv rename "C:\Courses\MyCourse" "[SomeSite.com] - " --tidy --apply

Options: ``-r``/``--recursive``, ``--ext`` (repeatable, e.g. ``--ext .mp4``),
``--ignore-case``, ``--tidy`` (collapse leftover double-spaces and trim stray
``-_.``), ``--apply``. Collisions and would-be-empty names are skipped, never
forced. If the text to remove **starts with a dash**, put ``--`` before the
arguments: ``slimv rename -- FOLDER "-tag"``.
