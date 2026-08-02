.. _slimv--user-manual:

slimv — user manual
===================

**Shrink video files without losing visible quality.**

``slimv`` is a small Python command-line toolkit that drives **ffmpeg/ffprobe** to:
inspect your hardware, analyze the videos on a disk, benchmark encoders on *your*
content, apply quality-preserving re-encode profiles, and verify the results
before you delete any source.

slimv never encodes video itself — it builds the right ffmpeg commands, runs them,
and interprets the results. The deep "why" behind every choice is in the
companion **``Understanding-and-Compressing-Video-Files-Guide.md``**.

--------------

Requirements
------------

- **Python 3.9+**
- **ffmpeg + ffprobe** on your ``PATH`` (with ``libx265``; ideally ``hevc_qsv``/
  ``hevc_nvenc`` for hardware encoding and ``libvmaf`` for the benchmark)
- One pip dependency: **``rich``** (installed automatically below)

Check ffmpeg is visible:

::

   ffmpeg -version

--------------

Install
-------

From inside the ``AV_kit`` folder:

.. code:: bash

   # option A — install as a command (recommended)
   pip install -e .
   slimv --help

   # option B — run without installing
   pip install rich
   python -m slimv --help

Both give you the same commands; the manual uses ``slimv …`` (use ``python -m slimv …``
if you didn't install).

--------------

Commands
--------

+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| Command                                       | What it does                                                                                                                                        |
+===============================================+=====================================================================================================================================================+
| ``slimv hwcheck``                             | List GPUs + which encoders ffmpeg has; recommend one; explain how to confirm hardware is really used                                                |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| ``slimv profiles``                            | Show the encoding profiles and when to use each                                                                                                     |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| ``slimv analyze <path>``                      | Probe a file/folder (codec, resolution, bitrate, size) and recommend a profile + projected savings                                                  |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| ``slimv check <path>``                        | Health scan: report each file's codec, find corrupted/unreadable files (full decode), and print stats                                               |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| ``slimv test <encoder>``                      | 5 s synthetic encode + full-decode check; reports hardware vs software                                                                              |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| ``slimv benchmark <file>``                    | Encode a 30 s sample with several profiles, score each with **VMAF**                                                                                |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| ``slimv encode <src> <dst> --profile <name>`` | Batch re-encode a tree (mirrored output), per-file verify + CSV log, resumable                                                                      |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| ``slimv verify <src> <dst>``                  | Confirm every output exists, matches length, decodes clean → marks sources ``SAFE-TO-DELETE``. ``<src>``/``<dst>`` may be folders **or a single     |
|                                               | file** (``slimv verify "src\66.mp4" "out\66.mp4"``) to check just one file without re-scanning a whole tree                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+

Typical workflow
~~~~~~~~~~~~~~~~

.. code:: bash

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
   #    -> delete only the sources marked SAFE-TO-DELETE

Worked example: a real course, end to end
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A complete real run — a **machine-learning video course** (273 videos) — showing
every step: inspect → test → read results → choose → encode → verify. This is the
same flow you'd use on any library.

**1. Inspect — what is it?**

.. code:: bash

   slimv analyze "D:\Courses\ML Foundations"

::

   273 video files, 59.53 GB · all 1280x720 H.264 · ~3–5 Mbps (some ~9.85)

Read: it's 720p H.264 (a re-encode target, not already HEVC), and the bitrate is high
for slide/lecture content — a strong candidate (see Guide §8F on why over-bitrated
static content shrinks so much).

   **🔴 RULE — never skip (or commit) a course on bitrate alone; always benchmark a sample first.**
   Bitrate does not predict compressibility — *content type* does. Static screen (schematic,
   console, code editor, slides, handwriting) crushes even at a **low** bitrate (a firewall-console course at 0.99 Mbps → 72%);
   motion (3D orbit/render, live camera, livestream) grows or keeps-original even at a **high** bitrate
   (a 3D-CAD screencast at ~1 Mbps → *grew 94%*). Same numbers, opposite results — only the benchmark knows. The one
   safe bitrate-only skip is a **verified duplicate**. (Full evidence table + rationale in the ledger's
   "RULE — never skip on bitrate alone".)

**2. Test on YOUR content — benchmark a representative file.** Pick a *hard* one (here,
an equation/handwriting lecture — the worst case for quality):

.. code:: bash

   slimv benchmark "D:\Courses\ML Foundations\99. Chain Rule Exercises.mp4"

::

          Benchmark (30s sample) — smallest first
     Profile    VMAF    Size(MB)   Speed×RT   HW
     balanced   91.80   1.57       1.11       no
     qsv        91.15   1.70       1.79       yes
     qsv-hq     91.80   2.65       1.76       yes
     quality    92.34   2.95       1.07       no
     nvenc      92.64   7.32       3.97       yes

**3. Read the results.** The 30 s source was ~36.9 MB, so every profile is ~90%+
smaller here. What the columns tell you:

- **VMAF** is fidelity vs a lossless reference — higher = closer to source. They all
  cluster **91–92.6**; on screen/text content **~92 is transparent in practice** (VMAF
  under-reads on text — see Guide §8C).
- **Size** is what you're buying with those VMAF points. ``nvenc`` is 4× bigger for +1.5
  VMAF you can't see — reject it. ``quality`` (CPU, CRF 20) is biggest of the rest.
- **HW** + **Speed**: ``qsv``/``qsv-hq`` run on the iGPU at ~1.8×, freeing the CPU.

**4. Choose a quality.** Two sensible picks:

- **``qsv`` (GQ24)** — smallest hardware option, VMAF 91.15. The default.
- **``qsv-hq`` (GQ22)** — VMAF 91.80 for modestly larger files. **Chosen here**, because
  the content is equation/handwriting-heavy and text *sharpness* is worth the few extra
  MB while still ~90% smaller. *(Match the choice to the content; for ordinary slides,
  ``qsv`` is plenty.)*

**5. Encode the whole tree** (resumable — safe to stop/restart; ``--keep-smaller``
protects the few light files from growing):

.. code:: bash

   slimv encode "D:\Courses\ML Foundations" "E:\Encoded\ML Foundations [HEVC]" --profile qsv-hq --keep-smaller

::

   [1/273] 1. Introduction.mp4 (18.7 MB)
   ...
   [9/273] 106. 7.6 Higher-Order Partial Derivatives.mp4 ...
      ENCODE-FAIL            ← a transient QSV "Invalid data" hiccup
   [10/273] 107. 7.7 Exercise.mp4 ...   ← keeps going; one bad file never stops the batch

Result so far: ~8.6 : 1, **≈88% smaller**. If a file transiently fails, just **re-run
the same command** — resume skips everything already done and re-attempts only the
missing file(s); the one above succeeded on retry. (For a file that fails QSV twice,
encode just that one with a CPU profile: ``slimv encode "<that file>" "<dst>" --profile balanced``.)

**6. Verify before deleting anything** (full-decode integrity + length match; resume is
on by default so re-runs are fast):

.. code:: bash

   slimv verify "D:\Courses\ML Foundations" "E:\Encoded\ML Foundations [HEVC]"

::

   [273/273] SAFE-TO-DELETE  ...
   SAFE-TO-DELETE: 273   KEEP-SOURCE: 0
   ALL VERIFIED — these sources are safe to remove.

Only now is it safe to delete (or stage) the originals. A ``--full`` flag forces a
complete re-decode if you ever want to re-scan for silent on-disk corruption.

--------------

Profiles
--------

All profiles keep resolution, frame rate, and pixel format unchanged, and
re-encode audio to AAC 128k (or **``--copy-audio``** to stream-copy it verbatim —
use when the source is already AAC at a fine bitrate, avoiding wasted CPU and a
needless lossy audio generation). **Lower CRF / quality number = higher quality =
bigger file.** The numbers are not comparable between codecs.

============ =============== ============================= ================== ================ ======================================================
Profile      Encoder         Quality                       Speed              Size             Use when
============ =============== ============================= ================== ================ ======================================================
``archive``  libx265 CRF18   Near-lossless                 Slow (CPU)         Largest H.265    Masters/archival, precious sources
``quality``  libx265 CRF20   Transparent + margin          Medium (CPU)       Larger           Detail/text-heavy, want safety margin
``balanced`` libx265 CRF23   Transparent                   Medium (CPU)       Small            General default (CPU), smallest CPU files
``small``    libx265 CRF26   Good (text may soften)        Slow (CPU)         Smallest (CPU)   Low-detail slides/talking-head
``qsv``      hevc_qsv GQ24   Transparent (~VMAF 92 screen) Fast (Intel iGPU)  Small            **Intel Quick Sync present — recommended all-rounder**
``nvenc``    hevc_nvenc CQ24 Transparent                   Very fast (NVIDIA) Small            NVIDIA GPU idle; big batches
``av1``      libsvtav1 CRF30 Transparent                   Slow (CPU)         Smallest overall Max compression, players support AV1
============ =============== ============================= ================== ================ ======================================================

..

   **Which to pick?** If you have an Intel iGPU, ``qsv`` is the sweet spot: near-x265
   quality, ~2× faster, and it runs on otherwise-idle hardware so your CPU and any
   discrete GPU stay free. Want the absolute smallest CPU-encoded files and have
   the time? ``balanced``. Always run ``benchmark`` once on your own content to confirm.

--------------

.. _choosing-the-engine-cpu--igpu--nvidia-and-switching-it:

Choosing the engine: CPU / iGPU / NVIDIA (and switching it)
-----------------------------------------------------------

slimv is **encoder-agnostic** — which engine does the work is just a choice, never a
hard requirement. The ``--profile`` you pick names an ffmpeg encoder, and that encoder
decides the engine:

============== ================================================= ============== ==============================
Engine         Profiles                                          ffmpeg encoder Needs
============== ================================================= ============== ==============================
**CPU**        ``archive``, ``quality``, ``balanced``, ``small`` libx265        nothing — runs anywhere
**CPU**        ``av1``                                           libsvtav1      an ffmpeg built with libsvtav1
**Intel iGPU** ``qsv``, ``qsv-hq``, ``qsv-720p``, ``qsv-480p``   hevc_qsv       an Intel Quick Sync iGPU
**NVIDIA GPU** ``nvenc``                                         hevc_nvenc     an NVIDIA GPU + driver
============== ================================================= ============== ==============================

**Switching engine — encode:** just change the profile.

.. code:: bash

   slimv encode SRC DST --profile qsv        # Intel iGPU (leaves CPU + NVIDIA free)
   slimv encode SRC DST --profile nvenc      # NVIDIA GPU (use when it's idle)
   slimv encode SRC DST --profile balanced   # CPU only (no GPU needed at all)

**Freeing the CPU — decode on the GPU too (``--hwdec``).** Even a hardware (``qsv``) encode
*decodes* the source on the **CPU** by default. If you're running other CPU-heavy work
(e.g. transcription) and want it undisturbed, move the decode onto a GPU:

.. code:: bash

   slimv encode SRC DST --profile qsv --hwdec qsv           # full iGPU decode→encode pipeline
   slimv encode SRC DST --profile qsv --hwdec qsv --preset slow   # + faster preset

``--hwdec qsv`` **roughly halved a real job's CPU** (main ffmpeg ~100% of a core → ~47%):
the heavy H.264 decode moves to the iGPU, while demux + AAC audio + frame-feeding stay on
the CPU. Much freer, not idle. Two caveats worth knowing (the *why* is in Guide §8H):

- **It does not speed up the encode.** Decode and encode pipeline in parallel; the encoder
  is the bottleneck, so moving the decode off the CPU frees the CPU but doesn't change
  throughput. For speed, use a lighter **``--preset``** (``slow``/``medium``) — that's the lever.
- **It needs a non-scaling profile** (``qsv``, not ``qsv-720p/480p``), and on a small/older
  iGPU the hardware frame pool is auto-sized to a Gen9-safe ``-extra_hw_frames 24`` (the
  default 8 starves the pipeline; large values exhaust iGPU memory). ``--hwdec cuda`` /
  ``d3d11va`` are also accepted.
- **Pair the decoder with the encoder's hardware.** ``--hwdec`` chooses the *decode*
  device; the ``--profile`` chooses the *encode* device — two independent picks. Keep
  them on the same GPU: ``--hwdec qsv`` with a ``qsv`` profile (both Intel), or
  ``--hwdec cuda`` with ``nvenc`` (both NVIDIA). Mismatching — e.g. ``--hwdec cuda``
  decoding on the NVIDIA card into a ``qsv-hq`` encode on the Intel iGPU — forces ffmpeg
  to download frames from one GPU to RAM and upload them to the other, which is slower
  and can break against the ``-hwaccel_output_format qsv`` pinning. slimv doesn't
  auto-detect the GPU; you select it with these two flags.
- **A hardware decoder is stricter than software.** On a rough/slightly-corrupt file it can
  stop early and truncate the output (where software decode limps through). The tell:
  ``verify`` flags a length mismatch on a source that plays fine. Fix: re-encode *that one
  file* **without ``--hwdec``** (software decode recovers the full content). So ``--hwdec`` is
  the right default; keep plain decode as the fallback for the occasional rough file.

**How much CPU does it actually save?** Measured with ffmpeg's ``-benchmark`` on the
same 90-second clip (``nvenc-hq``): plain **CPU decode used ~19 CPU-seconds**;
``--hwdec cuda`` cut that to **~6.5**, and — now that the CUDA path is **zero-copy**
(decoded frames stay in GPU memory, like the ``qsv`` path) — to **~3.6 CPU-seconds,
and ~2× faster** (no GPU↔RAM round-trip). The encode itself runs entirely on NVENC;
what's left on the CPU is demux/mux and frame-feeding — a fraction of a core, but
never fully idle.

**Running both GPUs at once.** Because NVENC is near-CPU-free and the Intel and
NVIDIA encoders are **independent hardware**, you can run an ``nvenc-hq`` job at the
*same time* as a ``qsv`` job — two ``slimv encode`` commands to different output
folders — and roughly **double your total throughput**. They share only the source
disk and a little CPU; neither GPU waits on the other. (Point them at *different*
output drives to avoid write contention.)

**Switching engine — verify:** the integrity pass decodes on the **CPU by default**
(safest for a deletion gate), but you can offload it to a GPU with ``--hwaccel``:

.. code:: bash

   slimv verify SRC DST                    # CPU software decode (default)
   slimv verify SRC DST --hwaccel qsv      # Intel iGPU decode (~4x faster here)
   slimv verify SRC DST --hwaccel cuda     # NVIDIA decode

Hardware decode is much faster, but a hardware decoder can report/conceal corruption
differently than software — so CPU stays the default for the gate; use ``--hwaccel``
when you want speed and trust the source path.

Measured decode-to-null of one ~15-minute 1080p HEVC file (all backends reported **0
errors** — so on clean files they agree, they just differ in speed):

================================== ======== =============================================================================
Backend                            Time     Note
================================== ======== =============================================================================
CPU (default, no flag)             147 s    safest; the deletion-gate default
``--hwaccel d3d11va``              219 s    generic D3D path — *slower* here, skip it
``--hwaccel cuda`` (NVIDIA)        102 s    good if the NVIDIA GPU is free
**``--hwaccel qsv`` (Intel iGPU)** **38 s** **~4× faster than CPU — the pick when the iGPU is your encode engine anyway**
================================== ======== =============================================================================

Pick the decoder for what's **free**: if you're encoding on the Intel iGPU and the
NVIDIA GPU is busy with other work, verify on the same iGPU (``--hwaccel qsv``). When the
NVIDIA GPU is idle, ``--hwaccel cuda`` also works well. On a headless/GPU-less box, omit
the flag and it decodes on the CPU.

**Pick the engine for what's free.** Encode on the Intel iGPU (``qsv``) while the CPU
and NVIDIA GPU stay busy with other work; verify on the same iGPU (``--hwaccel qsv``).
When the NVIDIA GPU frees up, switch to ``--profile nvenc`` + ``--hwaccel cuda``. On a
server with no GPU at all, use ``balanced``/``quality`` (CPU) and CPU verify — slimv runs
end-to-end, just slower.

**Caveat — requesting an engine the host doesn't have.** A profile is just a named
ffmpeg command that hard-codes a specific encoder (``qsv`` → ``-c:v hevc_qsv``, ``nvenc`` →
``-c:v hevc_nvenc``, ``balanced`` → ``-c:v libx265``, ``av1`` → ``-c:v libsvtav1``). That encoder
only exists if **both** the hardware **and** the ffmpeg build provide it: ``hevc_qsv``
needs an Intel Quick Sync iGPU, ``hevc_nvenc`` needs an NVIDIA GPU + driver, ``libsvtav1``
needs an ffmpeg compiled with it. If you ask for one that's absent — e.g. ``--profile qsv``
on a box with no Intel iGPU — ffmpeg can't initialise the encoder and the job **errors
out on the very first file** (you'll see something like ``Device creation failed`` /
``Cannot load hevc_qsv``), and the batch stops there.

**Why slimv doesn't silently fall back to another engine.** It would be easy to catch
that error and quietly re-run on, say, ``libx265`` (CPU) instead. slimv deliberately does
**not**, because a silent engine swap would change the output's **size, quality, and
speed** from what you asked for — on a tool whose entire purpose is *predictable*
size/quality, that's the worst kind of surprise (you'd discover it only later, by which
point a whole library might be encoded differently than intended, or sources deleted
against the wrong baseline). So slimv fails **loudly and immediately** — one clear ffmpeg
error you can act on — rather than substituting an engine behind your back. Choosing the
engine is a decision you make explicitly, not one the tool makes for you.

Two safeguards make this a non-issue in practice:

- **Check first:** ``slimv profiles`` marks every profile **available / not available**
  for the current host (it queries ``ffmpeg -encoders``), and ``slimv hwcheck`` lists your
  GPUs/encoders and recommends one. Run either before a big batch on a new machine.
- **Auto modes are already safe:** ``slimv recommend`` and ``slimv benchmark`` only test the
  encoders that exist on the host, so they never recommend something that can't run.

So the failure mode is loud and immediate (a clear ffmpeg error on the first file), not
a silent wrong-engine surprise — and a 5-second ``slimv profiles`` avoids it entirely.

--------------

Customizing profiles (no code edits)
------------------------------------

You never have to edit Python to add or change a profile. Two ways:

**1. Ad-hoc overrides on the command line** — for a one-off tweak:

.. code:: bash

   slimv encode SRC DST --profile qsv --gq 22       # change QSV quality on the fly
   slimv encode SRC DST --profile balanced --crf 22 # change x265 CRF
   slimv encode SRC DST --profile qsv --scale 720   # downscale to 720p (keeps aspect)
   slimv encode SRC DST --profile qsv --preset slow # change the encoder preset

``--gq`` (QSV global_quality) and ``--crf`` (x265/AV1) are the quality dials (lower =
higher quality). ``--scale H`` sets height and keeps aspect ratio. If an override
doesn't apply to the chosen profile's codec (e.g. ``--crf`` on a QSV profile),
slimv warns and ignores it.

**2. A ``profiles.toml`` file** — for persistent custom or overridden profiles.
slimv merges it over the built-ins. Search order (later wins):

================= =============================================================================================
Location          Path
================= =============================================================================================
user config dir   ``%APPDATA%\slimv\profiles.toml`` (Windows) · ``~/.config/slimv/profiles.toml`` (Linux/macOS)
current directory ``./profiles.toml``
explicit          whatever ``$SLIMV_PROFILES`` points at
================= =============================================================================================

Each ``[table]`` is one profile; ``codec`` and ``vargs`` are required. Adding a table
with a built-in's name **overrides** that built-in. See **``profiles.toml.example``**
for a ready-to-copy template:

.. code:: toml

   [qsv-21]
   codec    = "hevc_qsv"
   vargs    = ["-c:v","hevc_qsv","-preset","veryslow","-global_quality","21","-tag:v","hvc1"]
   when     = "a touch above qsv-hq"
   hardware = true

``slimv profiles`` then lists your custom profiles alongside the built-ins.

--------------

Confirming hardware encoding is *really* happening
--------------------------------------------------

GPU utilization graphs can read 0% even while a hardware encoder is busy (notably
Intel QSV on older iGPUs, where Windows doesn't attribute the media-engine path
per process). Don't trust the graph — trust:

1. **``slimv test <encoder>``** → prints ``HARDWARE`` / ``SOFTWARE`` from ffmpeg's own log.
2. **``ffmpeg.exe`` at ~0% CPU** while the output file grows.
3. **GPU-Z / HWiNFO** "Video Engine Load" sensor (reads the driver directly).

Full explanation in §8B of the guide.

--------------

.. _output--logs:

Output & logs
-------------

- **Encode** writes to a mirrored tree under ``<dst>`` (originals untouched) and a
  per-file ``_slimv_encode_log.csv`` (sizes, % reduction, durations, OK/WARN).
- **Verify** writes ``_slimv_verify_report.csv`` with a ``SAFE-TO-DELETE`` /
  ``KEEP-SOURCE`` verdict (+ reason) per file. It is **read-only** — it never
  deletes anything; deletion stays your decision.

--------------

How ``verify`` decides (the deletion safety gate)
-------------------------------------------------

``verify`` is the gate you cross before deleting an original. For every source it runs
three checks, cheapest first, and only a file that passes **all** is ``SAFE-TO-DELETE``:

1. **Output exists?** — the converted file is present (or, for a not-smaller file, its
   kept-original copy). Missing → ``KEEP-SOURCE``.
2. **Right length?** — source vs output duration within ``--tol`` (default 1.0 s).
3. **Decodes clean?** — a full frame-by-frame decode with **0 real errors** (``--hwaccel``
   can run this on a GPU; CPU is the default — see *Choosing the engine*).

Because a naïve version of those checks throws **false alarms** on perfectly good files,
verify has four deliberate exceptions — each a lesson learned from real batches:

+-------------------------------------------------------------------------------------+------------------------+-------------------------------------------------------------------------------------+
| Situation                                                                           | Naïve verdict          | What verify actually does                                                           |
+=====================================================================================+========================+=====================================================================================+
| **Kept-original** (``--keep-smaller`` kept the source because the re-encode wasn't  | "converted MISSING"    | Recognises the kept copy *is* the output and verifies it →                          |
| smaller)                                                                            |                        | ``ok (kept original — not smaller)``                                                |
+-------------------------------------------------------------------------------------+------------------------+-------------------------------------------------------------------------------------+
| **Benign muxer warning** (a one-off *non-monotonic DTS* from sloppy source          | "decode errors (1)"    | Filters that muxer line out — it's not frame corruption → clean                     |
| timestamps)                                                                         |                        |                                                                                     |
+-------------------------------------------------------------------------------------+------------------------+-------------------------------------------------------------------------------------+
| **Copied-through audio complaints** (with ``--copy-audio`` the audio is a byte-copy | "decode errors (1121)" | The integrity gate decodes **video only** (``-an``) and filters audio-decoder lines |
| of the source, so its AAC quirks — e.g. ``env_facs_q 255 is invalid`` — reappear in |                        | + ``Last message repeated`` trailers. Copied audio isn't re-encoded → nothing to    |
| the output)                                                                         |                        | verify there; only *video* corruption counts. (Fixed after Precalc 3/4 + English B2 |
|                                                                                     |                        | false positives.)                                                                   |
+-------------------------------------------------------------------------------------+------------------------+-------------------------------------------------------------------------------------+
| **VFR duration drift** (variable-frame-rate source re-encodes to the **same         | "length mismatch"      | Compares **frame counts**; if they match and it decodes clean →                     |
| frames** but a slightly different reported *duration*, so Δ exceeds ``--tol``)      |                        | ``ok (VFR: N frames match, duration drift Δ)``                                      |
+-------------------------------------------------------------------------------------+------------------------+-------------------------------------------------------------------------------------+
| **Bogus/inflated source metadata** (source *claims* more duration+frames than it    | "length mismatch"      | When the fast metadata frame-counts also disagree, falls back to an **authoritative |
| actually holds — e.g. 500 s / 15,027 when the video really ends at 316 s / 9,480;   |                        | decoded frame count** (``nb_read_frames``); if the *real* frames match →            |
| the file plays fine)                                                                |                        | ``ok (N real frames match; source metadata inflated)``. Genuine truncation (real    |
|                                                                                     |                        | frames differ) still fails.                                                         |
+-------------------------------------------------------------------------------------+------------------------+-------------------------------------------------------------------------------------+

The through-line: verify distinguishes **content damage** (missing/short/corrupt frames —
a real ``KEEP-SOURCE``) from **timing/packaging artifacts** (same frames, cosmetic metadata
differences — safe). A truncated or corrupt output still fails loudly; a VFR re-encode or
a kept-original does not.

Other verify behaviour:

- **Resume is on by default** — unchanged, already-passed files are reused (fingerprinted
  by size+mtime), so re-runs only decode what's new or changed. ``--full`` forces a complete
  re-decode (e.g. to re-scan for silent on-disk bit-rot).
- **Single file or whole tree** — ``slimv verify SRC DST`` accepts folders or a single
  file path; a one-file check never overwrites a whole-folder report.

--------------

.. _monitoring-an-autonomous--chained-queue-run:

Monitoring an autonomous / chained queue run
--------------------------------------------

When you drive a long unattended run (a ``master_queue.ps1``-style script that logs
``ENCODE START/DONE``, ``VERIFY START/DONE``, ``STOPPED_DISK``, ``ABORT`` to one log), use
**one** milestone watcher — ``queue_watch.sh`` (in this repo):

.. code:: bash

   # via the Monitor tool, persistent — pass the run's log path (session-specific):
   bash /path/to/AV_kit/queue_watch.sh "<path-to>/master_queue.log"

It prints each **new** milestone line so you get pinged on encode/verify completions
and stop conditions, without polling by hand.

**🔴 Rule — one clean watcher, no ``grep``/``tail`` pile-up.** ``queue_watch.sh`` reads the log
with the bash built-in ``mapfile`` and matches with a ``case`` glob, so it spawns **no ``grep``
and no ``tail``** and runs as a single ~5 MB process (~0 CPU while sleeping). This exists
because a past run armed many ``tail -f | grep`` Monitor loops that **orphaned and accumulated
— 43 of them over ~11 days (171 MB, 4.4 CPU-hours of spinning)** — which added to system-RAM
pressure and made the QSV encoder fail with ``Cannot allocate memory``. So: **arm exactly one
watcher, ``TaskStop`` it when the run ends, and don't let them stack across runs.** If a run
throws ``Cannot allocate memory``, it's usually **commit-charge pressure, not iGPU hardware**
— check ``\Memory\% Committed Bytes In Use`` (not free RAM or working-set, which mislead). The
repeat offender is Intel's **``esrv.exe`` / ``esrv_svc``** ("System Usage Report" / Computing
Improvement Program telemetry), which leaks ~15-21 GB of commit. **Killing it doesn't help —
it auto-restarts and re-commits; UNINSTALL it** ("Intel Computing Improvement Program") — that
dropped commit 97%→65% in one run. Don't raise the page file to fix this (the whole point is
to *free* disk); reduce commit demand instead (uninstall esrv, close Chrome).

--------------

.. _notes--limits:

Notes & limits
--------------

- slimv shells out to ffmpeg; quality/speed are ffmpeg's. slimv adds the
  hardware detection, profile catalog, VMAF measurement, batch verification, and
  the safety gate.
- The benchmark needs ``libvmaf`` in your ffmpeg build; without it you still get
  sizes and speeds.
- Containers are forced to ``.mp4`` on output (HEVC/AV1 friendly, widely playable).
  Use a different container by editing the profile if you need MKV features.
- Cross-platform (Windows/Linux/macOS); GPU enumeration is best-effort per OS.
