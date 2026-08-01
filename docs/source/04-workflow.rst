==================
The full workflow
==================

.. contents::
   :local:
   :depth: 2

The core ideas
==============

- **Investigate, then commit.** Look at the hardware, look at the library,
  prove the setting on a sample — *then* run the batch.
- **Encode in small batches and spot-check.** A wrong setting is cheap to catch
  on five files and expensive to discover after a thousand.
- **Verify before you delete.** The originals stay until ``verify`` proves each
  output is complete, length-matched, and decodable.
- **Trust the encoder log, not the GPU graph.** Some hardware paths under-report
  in the OS; confirm hardware use from ffmpeg itself and from CPU draw.

The recipe below is the same one used to convert a 206-file H.264 course to
H.265 at ~60% size reduction with zero visible loss.

Step by step
============

.. code-block:: bash

   # 1. What hardware/encoders do I have?
   slimv hwcheck

   # 2. What's in this library, and what should I do?
   slimv analyze "C:\Videos\MyCourse"

   # 3. Prove the quality/size on MY content before committing
   slimv benchmark "C:\Videos\MyCourse\lesson1.mp4"

   # 4. Re-encode the whole tree (resumable; safe to stop/restart)
   slimv encode "C:\Videos\MyCourse" "C:\Videos\MyCourse_slimv" --profile qsv

   # 5. Confirm everything converted correctly BEFORE deleting originals
   slimv verify "C:\Videos\MyCourse" "C:\Videos\MyCourse_slimv"
   #    -> delete only the sources whose row says SAFE-TO-DELETE

Confirming hardware encoding is really happening
================================================

GPU utilization graphs can read 0% even while a hardware encoder is busy
(notably Intel :term:`QSV` on older iGPUs, where the OS does not attribute the
media-engine path per process). Do not trust the graph. Trust instead:

#. ``slimv test <encoder>`` — prints ``HARDWARE`` / ``SOFTWARE`` from ffmpeg's
   own startup log.
#. ``ffmpeg.exe`` sitting at ~0% CPU while the output file keeps growing.
#. A sensor tool (GPU-Z / HWiNFO) "Video Engine Load", which reads the driver
   directly rather than the OS per-process accounting.

The deletion safety gate
========================

``verify`` is what makes deleting originals safe. For each source it checks three
things and only passes a file when all three hold:

#. **Completeness** — a converted file exists at the mirrored path.
#. **Length match** — converted duration equals the original within tolerance.
#. **Integrity** — a *full decode* of the converted file reports zero errors.

Files that pass are marked ``SAFE-TO-DELETE``; anything else is ``KEEP-SOURCE``
with the reason (missing, length mismatch, or decode errors). The command writes
the verdicts to ``_slimv_verify_report.csv`` and **never deletes anything
itself** — the decision stays yours. Delete only the originals whose row says
``SAFE-TO-DELETE``.

Watching a long run
===================

``encode`` is resumable: if it is interrupted, re-running the same command skips
the files already done and continues. Keep an eye on free disk space on the
output drive — H.265 output is typically 40–55% of an H.264 source, but a
high-motion title can run larger. Deleting verified sources as modules complete
keeps space comfortable on a tight drive.
