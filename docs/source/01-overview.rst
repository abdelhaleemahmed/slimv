==========================
Overview and installation
==========================

.. contents::
   :local:
   :depth: 2

The core ideas
==============

- **What slimv is.** A Python 3.9+ CLI that wraps :term:`ffmpeg` and ``ffprobe``
  to shrink video without visible quality loss.
- **What it needs.** ffmpeg + ffprobe on your ``PATH`` (ideally with ``libx265``,
  ``hevc_qsv``/``hevc_nvenc`` for hardware encoding, and ``libvmaf`` for the
  benchmark), and one Python dependency, :term:`rich`.
- **How you run it.** ``slimv <command>`` after installing, or
  ``python -m slimv <command>`` without installing.
- **What it does not do.** It does not re-implement a codec; it generates ffmpeg
  command lines, runs them, and reads back sizes, durations, and quality scores.

slimv exists because the same question comes up for every video library: *how do
I make these smaller without making them look worse?* The rest of this page gets
it installed; :doc:`02-commands` covers what each command does.

What slimv is
=============

slimv answers a single question with data instead of guesswork: for *this*
footage, on *this* machine, which encoder and setting give the smallest file at
visually transparent quality? It detects the encoders ffmpeg exposes, classifies
the videos on disk, measures candidate encodes with :term:`VMAF`, and then runs
the chosen :term:`profile` over a whole tree — verifying every output before you
trust it.

Requirements
============

- **Python 3.9 or newer.** Developed and tested on 3.13. (Only custom
  ``profiles.toml`` overrides need 3.11+, for the standard-library ``tomllib``;
  everything else runs on 3.9.)
- **The** :term:`rich` **library** — slimv's only Python dependency, installed
  automatically with the package.
- **ffmpeg and ffprobe on the** ``PATH`` — slimv shells out to them for
  everything. Confirm with::

      ffmpeg -version

  Use a reasonably recent build — **ffmpeg 5.0 or newer** (6.x/7.x recommended
  for the best Quick Sync and VMAF support; developed against 7.1). The standard
  "full" builds (e.g. gyan.dev, BtbN) already include everything in the table
  below. Which feature each part of slimv needs:

  .. list-table::
     :header-rows: 1
     :widths: 22 40 38

     * - ffmpeg feature
       - Needed for
       - Required?
     * - ``libx265``
       - CPU H.265 profiles (``balanced``, ``quality``, ``archive``, ``small``)
       - The universal fallback — present in every full build.
     * - ``hevc_qsv``
       - ``qsv`` / ``qsv-hq`` profiles and ``--hwdec qsv`` / ``--hwaccel qsv``
       - Optional — Intel iGPU (Quick Sync) hardware encode/decode.
     * - ``hevc_nvenc``
       - the ``nvenc`` profile
       - Optional — NVIDIA GPU (NVENC).
     * - ``libsvtav1``
       - the ``av1`` profile
       - Optional — only if you encode to AV1.
     * - ``libvmaf``
       - VMAF scores in ``benchmark`` / ``recommend`` / ``eyeball`` / ``downscale-test``
       - Optional but recommended — those commands still run without it, just
         without the quality column.
     * - ``ffv1``, ``aac``
       - lossless sample references; AAC audio re-encode
       - Native to ffmpeg — always present, nothing to install.

  After installing, run ``slimv hwcheck`` to see exactly which encoders your
  ffmpeg exposes and which GPUs are available.

.. note:: Where the encoders come from — you don't pip-install them

   ``libx265``, ``hevc_qsv``, ``hevc_nvenc``, ``libsvtav1``, ``libvmaf``,
   ``ffv1`` and ``aac`` are **not** Python packages and are **not** installed
   separately — they are **compiled into the ffmpeg build**. Download one
   "full" ffmpeg build (gyan.dev or BtbN on Windows; your distro's ``ffmpeg``
   on Linux) and it bundles them all. slimv's *only* pip dependency is
   :term:`rich`.

Hardware acceleration (optional)
--------------------------------

The hardware encoders also need the **GPU vendor's driver/runtime** installed,
on top of an ffmpeg that exposes them:

- **Intel Quick Sync** (``hevc_qsv``, ``--hwdec qsv``, ``--hwaccel qsv``) — install
  the **Intel Graphics Driver** (full package); it provides the **oneVPL / Media
  SDK** media runtime that Quick Sync rides on. Full walkthrough in
  :doc:`using-the-igpu`.
- **NVIDIA NVENC** (the ``nvenc`` profile) — install the **NVIDIA GPU driver**.

None of this is required to *use* slimv — it runs CPU-only on ``libx265`` out of
the box; the GPU drivers just make it faster and free the CPU.

.. warning:: Windows + Intel Quick Sync — a long-run gotcha we hit

   On long QSV batches, ffmpeg can fail with ``Cannot allocate memory`` that is
   **not** an iGPU limit but Windows **commit-charge** pressure. The repeat
   offender is Intel's own telemetry service — **``esrv.exe`` / ``esrv_svc``**
   ("System Usage Report" / Computing Improvement Program) — which can leak
   15–21 GB of commit. **Killing it doesn't help (it restarts); uninstalling it**
   restored headroom. A bigger page file is counter-productive when the goal is to
   free disk. Details in :doc:`slimv-manual` and :doc:`understanding-video-compression`
   (commit charge vs. the commit limit).

Installation
============

slimv is a standard Python package. Pick whichever fits your situation:

.. code-block:: bash

   # option A — install a built artifact (wheel or source distribution)
   pip install slimv-0.2.0-py3-none-any.whl     # wheel
   pip install slimv-0.2.0.tar.gz               # source distribution

   # option B — editable install from the source tree (for development)
   pip install -e .

   # option C — run without installing (only needs rich)
   pip install rich
   python -m slimv --help

All three give the same commands. This documentation uses ``slimv …``;
substitute ``python -m slimv …`` if you did not install the command.

Recommended: install into a virtual environment
------------------------------------------------

A venv keeps slimv and its one Python dependency (``rich``) isolated from your
system Python. Full steps:

.. code-block:: bash

   # 1. create and activate a virtual environment
   python -m venv .venv

   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Windows (cmd):
   .venv\Scripts\activate.bat
   # Linux / macOS:
   source .venv/bin/activate

   # 2. install slimv — this pulls in rich automatically
   pip install slimv-0.2.0-py3-none-any.whl        # a built wheel
   #   ...or from the source tree, editable, with the test extra:
   pip install -e ".[test]"

   # 3. verify
   slimv --version
   slimv hwcheck        # confirms ffmpeg is found and which encoders are visible

``pip`` installs only slimv and ``rich``. **ffmpeg/ffprobe are not Python
packages and are not installed by pip** — they come from your system ffmpeg
build (see **Requirements** above), so they remain available inside the venv
without any extra step. To leave the environment later, run ``deactivate``.

Building the distributable artifacts
------------------------------------

The ``.whl`` and ``.tar.gz`` above are produced from the source tree with the
standard build front-end:

.. code-block:: bash

   pip install build            # one-time
   python -m build              # writes dist/slimv-<version>-py3-none-any.whl
                                #    and dist/slimv-<version>.tar.gz

Packaging metadata (name, version, entry point, dependencies, author, MIT
license) lives in ``pyproject.toml``; the ``LICENSE`` file is bundled into both
artifacts automatically.

A first look
============

Three commands tell you almost everything before you encode anything:

.. code-block:: bash

   slimv hwcheck                  # what encoders/GPUs do I have?
   slimv analyze "C:\Videos\Course"   # what's in this library, and what should I do?
   slimv benchmark "C:\Videos\Course\lesson1.mp4"   # prove quality/size on my content

From there, :doc:`04-workflow` walks the full encode-and-verify recipe.
