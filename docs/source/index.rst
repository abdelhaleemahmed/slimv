==========================================
slimv — shrink video, keep the quality
==========================================

**slimv** is a small Python command-line toolkit that drives
:term:`ffmpeg`/``ffprobe`` to inspect your hardware, analyze the videos on a
disk, benchmark encoders on *your* content, apply quality-preserving re-encode
:term:`profile` s, and verify the results before you delete any source.

slimv never encodes video itself — it builds the right ffmpeg commands, runs
them, and interprets the results. The deep "why" behind every choice lives in
the companion guide *Understanding & Compressing Video Files Without Losing
Quality*.

.. note::

   This documentation ships in **English and Arabic**. Use the 🌐 switcher in
   the sidebar to change language. The Arabic build renders right-to-left.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   01-overview
   02-commands
   03-profiles
   04-workflow
   06-case-study
   05-api
   glossary

.. toctree::
   :maxdepth: 2
   :caption: Guides & reference

   understanding-video-compression
   using-the-igpu
   slimv-manual
   strip-name

The core ideas
==============

- **One tool, ffmpeg underneath.** slimv orchestrates; ffmpeg encodes. You get
  hardware detection, a profile catalog, :term:`VMAF` measurement, batch
  verification, and a safe delete gate on top.
- **Quality first, then size.** Every profile keeps resolution, frame rate, and
  pixel format. The goal is *visually transparent* output at the smallest size,
  never a quality trade.
- **Measure on your own content.** :doc:`benchmark <02-commands>` encodes a short
  sample several ways and scores each with VMAF, so the choice is data, not
  folklore.
- **Hardware when it helps.** On an Intel iGPU, the ``qsv`` profile is ~2× faster
  and frees your CPU and discrete GPU — see :doc:`04-workflow`.
- **Never delete a good source for a broken copy.** :doc:`verify <02-commands>`
  confirms every output exists, matches length, and decodes cleanly before
  anything is removed.

Where to start: :doc:`01-overview` for install and concepts, :doc:`02-commands`
for the command reference, then :doc:`04-workflow` for the end-to-end recipe.

Features
========

- **Benchmark on your own content** — ``benchmark`` samples a clip and scores
  every candidate profile with :term:`VMAF`; ``analyze --measure`` projects the
  real saving; ``recommend`` picks the smallest profile that stays transparent.
- **Quality-preserving profile catalog** — built-in x265 / QSV / NVENC / AV1,
  with per-run overrides (``--crf`` / ``--gq`` / ``--cq`` / ``--preset`` /
  ``--scale``) and a ``profiles.toml`` for custom encoders.
- **Hardware acceleration, CPU kept free** — HEVC on Intel Quick Sync, NVIDIA
  NVENC, and AMD AMF (``hwcheck`` detects them), plus a zero-copy ``--hwdec``
  decode pipeline that keeps the CPU idle.
- **Batch encode a whole tree** — ``encode`` mirrors a folder, **resumes**
  (skips finished files), and logs every file (size, saved %, speed);
  ``--copy-audio`` and ``--keep-smaller`` fine-tune it.
- **Trust, then delete** — ``verify`` is a **resumable, shardable** delete-gate
  that confirms every output decodes cleanly before a source is removed;
  ``report`` and ``verify-report`` roll the logs into a live summary box (files,
  sizes, saved %, ratio, speed, ETA, and the source + output paths), with
  ``--list-corrupted`` to surface any bad files.
- **Housekeeping** — ``rename`` (dry-run bulk rename), ``check`` (health scan),
  and ``downscale-test`` / ``eyeball`` to measure or eyeball a change first.

See :doc:`02-commands` for the full command reference.

Indices
=======

* :ref:`genindex`
* :ref:`search`
