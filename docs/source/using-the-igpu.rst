.. _using-the-integrated-gpu-intel-igpu--a-practical-guide:

Using the Integrated GPU (Intel iGPU) — a practical guide
=========================================================

What the integrated GPU is, where to find it, what it can do beyond drawing the
desktop, and how to reach it from a shell, from C, and from Python. Written
against a real machine — an **Intel Core i7-7700HQ laptop with Intel HD Graphics
630** — but the concepts apply to any Intel iGPU.

   Companion to *Understanding & Compressing Video Files* — the video-encode parts
   here are the hardware side of the ``hevc_qsv`` / Quick Sync work in that guide.

--------------

Table of Contents
-----------------

1.  `What an iGPU actually is <#1-what>`__
2.  `Your hardware, identified <#2-yours>`__
3.  `Where to find and inspect it <#3-inspect>`__
4.  `What it can do (the four jobs) <#4-jobs>`__
5.  `Can it accelerate an Android emulator? <#5-android>`__
6.  `Accessing it from a shell script <#6-shell>`__
7.  `Accessing it from C <#7-c>`__
8.  `Accessing it from Python <#8-python>`__
9.  `GPU compute explained: OpenCL, oneAPI, and OpenCV-GPU <#9-gpgpu>`__
10. `Enabling GPU compute: the Intel driver and Compute Runtime (NEO) <#9-runtime>`__
11. `Resources <#10-resources>`__

--------------

.. _1-what-an-igpu-actually-is:

1. What an iGPU actually is
---------------------------

An **integrated GPU (iGPU)** is a graphics processor built **onto the same chip
(die) as the CPU**, sharing the same package and — crucially — the **same system
RAM** instead of having its own dedicated video memory. A **discrete GPU (dGPU)**
like an NVIDIA card is a separate board with its own GDDR memory on a PCIe slot.

Trade-offs that follow from "on the CPU die, shares RAM":

+----------------------+----------------------+----------------------+
|                      | iGPU                 | Discrete GPU         |
+======================+======================+======================+
| Memory               | Shares system RAM    | Own dedicated VRAM   |
|                      | (UMA — Unified       |                      |
|                      | Memory Architecture) |                      |
+----------------------+----------------------+----------------------+
| Power                | Very low (watts)     | High (tens–hundreds  |
|                      |                      | of watts)            |
+----------------------+----------------------+----------------------+
| Raw 3D power         | Modest               | High                 |
+----------------------+----------------------+----------------------+
| Fixed-function media | **Excellent** (Quick | Good (NVENC/NVDEC)   |
| (encode/decode)      | Sync)                |                      |
+----------------------+----------------------+----------------------+
| Cost                 | "Free" (in the CPU)  | Separate purchase    |
+----------------------+----------------------+----------------------+
| Data transfer cost   | Near-zero (same RAM) | Must cross PCIe      |
+----------------------+----------------------+----------------------+

The key insight for *your* work: an iGPU's **fixed-function media engine** (Intel
calls it **Quick Sync Video**) is a dedicated block of silicon for video
encode/decode that is separate from both the CPU cores and the GPU's 3D shaders.
It is why ``hevc_qsv`` can re-encode video while your CPU sits at ~0% — the work is
on that block, not the cores.

--------------

.. _2-your-hardware-identified:

2. Your hardware, identified
----------------------------

+-----------------+------------------------+------------------------+
| Property        | Value                  | Meaning                |
+=================+========================+========================+
| iGPU            | **Intel HD Graphics    | Gen 9.5 graphics,      |
|                 | 630**                  | "GT2" tier             |
+-----------------+------------------------+------------------------+
| In CPU          | **Core i7-7700HQ**     | Kaby Lake, 4 cores / 8 |
|                 |                        | threads, mobile        |
|                 |                        | (laptop)               |
+-----------------+------------------------+------------------------+
| Execution Units | **24 EUs**             | the iGPU's shader      |
|                 |                        | cores; ~350 MHz base,  |
|                 |                        | ~1.1 GHz max           |
+-----------------+------------------------+------------------------+
| Memory          | **Shared (UMA)**       | no dedicated VRAM;     |
|                 |                        | borrows system RAM     |
|                 |                        | dynamically (the "1    |
|                 |                        | GB" Windows reports is |
|                 |                        | a reserved slice, not  |
|                 |                        | a hard limit)          |
+-----------------+------------------------+------------------------+
| Driver          | 31.0.101.2135 (2025)   | a recent driver for a  |
|                 |                        | 2017-era part — good   |
+-----------------+------------------------+------------------------+
| Display         | 1920×1080              | it is also driving     |
|                 |                        | your screen            |
+-----------------+------------------------+------------------------+

**Media capabilities of HD 630 (Quick Sync, Gen 9.5):**

============ ================= ================
Codec        Decode            Encode
============ ================= ================
H.264 / AVC  ✅                ✅ (8-bit)
H.265 / HEVC ✅ (Main, Main10) ✅ (Main, 8-bit)
VP9          ✅ (8-bit)        ❌
MPEG-2       ✅                ✅
MJPEG        ✅                ✅
**AV1**      ❌                ❌
============ ================= ================

..

   **Caveat — ffmpeg lists more than the chip can do.** ``ffmpeg -encoders`` shows
   ``av1_qsv`` on this machine, but **HD 630 has no AV1 hardware** (AV1 Quick Sync
   arrived with Gen 12 / Arc). The encoder is in the *ffmpeg build*, not the
   *silicon* — calling ``av1_qsv`` here fails at runtime. Only trust ``h264_qsv``,
   ``hevc_qsv``, ``mjpeg_qsv``, ``mpeg2_qsv`` on this GPU. This is exactly why slimv's
   ``slimv test <encoder>`` exists: it proves a hardware path actually runs before
   you rely on it.

--------------

.. _3-where-to-find-and-inspect-it:

3. Where to find and inspect it
-------------------------------

.. _windows--gui:

Windows — GUI
~~~~~~~~~~~~~

- **Device Manager** → *Display adapters* → "Intel(R) HD Graphics 630". Right-click
  → *Properties* → *Driver* tab for version/date.
- **Task Manager** → *Performance* → *GPU* (each adapter is listed). The engine
  graphs (3D / Copy / Video Decode / Video Encode) are *unreliable for Quick Sync
  encode* on this generation — see §8B of the video guide.
- **dxdiag** (run it: ``dxdiag``) → *Display* tab: chip, memory, driver, DirectX
  feature levels.
- **GPU-Z** / **HWiNFO** (third-party, recommended): read the driver's own
  sensors — clocks, per-engine "Video Engine Load", temperature. These *do* show
  Quick Sync activity when Task Manager doesn't.

.. _windows--command-line:

Windows — command line
~~~~~~~~~~~~~~~~~~~~~~

.. code:: powershell

   # identity, driver, memory, current resolution
   Get-CimInstance Win32_VideoController |
     Select-Object Name, DriverVersion, DriverDate,
       @{n='VRAM_MB';e={[math]::Round($_.AdapterRAM/1MB)}},
       CurrentHorizontalResolution, CurrentVerticalResolution | Format-List

   # what hardware accel paths ffmpeg can use
   ffmpeg -hide_banner -hwaccels

.. _linux-for-reference--dual-boot:

Linux (for reference / dual-boot)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   lspci | grep -iE 'vga|display'                 # see the device
   sudo apt install vainfo intel-gpu-tools clinfo  # the inspection trio
   vainfo                                          # VA-API: list decode/encode entrypoints
   sudo intel_gpu_top                              # live per-engine load (render/blitter/video)
   clinfo                                          # OpenCL devices + capabilities
   ls -l /dev/dri                                  # card0 / renderD128 — the kernel device nodes

--------------

.. _4-what-it-can-do-the-four-jobs:

4. What it can do (the four jobs)
---------------------------------

An iGPU does four distinct kinds of work, on different parts of the silicon:

1. **Display / desktop** — scanning the framebuffer out to the panel. Always on;
   it is literally driving your 1920×1080 screen.
2. **3D / graphics rendering** — OpenGL, Vulkan, Direct3D. Games, the Windows
   compositor, GPU-accelerated browsers, **and the Android emulator's screen**
   (§5). Runs on the 24 EUs.
3. **Fixed-function media (Quick Sync)** — hardware video **encode/decode**,
   separate from the EUs. This is the ``hevc_qsv`` path. Also accelerates video
   *playback* in players/browsers (saves battery).
4. **GPGPU compute** — general math on the EUs via **OpenCL** or **oneAPI /
   Level Zero**: image processing, OpenCV filters, simple ML, ffmpeg OpenCL
   filters. (On this machine the *runtime* for this is not yet installed — see
   §8.)

You have already been using job #3 (Quick Sync) all through the video work. The
sections below show how to reach jobs #2–#4 yourself.

--------------

.. _5-can-it-accelerate-an-android-emulator:

5. Can it accelerate an Android emulator?
-----------------------------------------

**Yes — but be precise about which acceleration**, because two completely
different mechanisms get muddled under the word.

A fast Android emulator needs **two** things, and they use different hardware:

.. _a-cpu-virtualization--the-big-speed-win-not-the-igpu:

(a) CPU virtualization — the big speed win (NOT the iGPU)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The emulator runs an **x86/x86-64 Android image** as a virtual machine. To run
that VM at near-native speed it needs the CPU's **hardware virtualization
(Intel VT-x)**, via a hypervisor:

- **HAXM** (Intel Hardware Accelerated Execution Manager) — the classic one.
- **WHPX** (Windows Hypervisor Platform) — used when **Hyper-V is on**.
- **AEHD** (Android Emulator Hypervisor Driver) — the newer HAXM replacement.

..

   **On your machine specifically:** ``HypervisorPresent = True`` — Hyper-V is
   running. That means **HAXM cannot be used** (Hyper-V owns VT-x); the emulator
   must use **WHPX**. The WMI flag ``VirtualizationFirmwareEnabled = False`` is a
   *side effect* of Hyper-V abstracting VT-x, not a sign virtualization is off —
   VT-x is enabled in your BIOS (Hyper-V requires it). Enable in Windows:
   *"Windows Features" → Windows Hypervisor Platform + Hyper-V*, then in Android
   Studio the emulator picks WHPX automatically.

This is what makes the emulator usable. It is **CPU**, not GPU.

.. _b-gpu-rendering--where-the-igpu-does-help:

(b) GPU rendering — where the iGPU *does* help
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The emulated device's screen (its OpenGL ES drawing) is rendered by the **host
GPU**. In Android Studio: *Device Manager → edit AVD → Emulated Performance →
Graphics*:

- **Hardware - GLES 2.0/3.0** → renders on the **host GPU (your HD 630)** via
  **ANGLE**, which translates Android's OpenGL ES to Direct3D 11 on Windows.
  Smooth UI, low CPU. **This is the iGPU accelerating the emulator.**
- **Software - GLES** → renders on the CPU (SwiftShader). Use only if the GPU
  path glitches.
- **Auto** → let the emulator choose.

So the honest picture for your laptop: **VT-x (via WHPX) makes the emulator
fast; the HD 630 makes its graphics smooth.** Set Graphics = *Hardware* and the
iGPU is doing job #2 for the emulator. (If you ever add a discrete GPU, Windows
*Graphics settings* lets you pin ``qemu-system-*.exe`` to a specific GPU.)

Command-line check / launch:

.. code:: powershell

   # is acceleration available, and which hypervisor?
   & "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -accel-check
   # force the GPU rendering mode when launching an AVD
   & "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd Pixel_6 -gpu host

(``-gpu host`` = use the host iGPU; ``-gpu swiftshader_indirect`` = CPU fallback.)

--------------

.. _6-accessing-it-from-a-shell-script:

6. Accessing it from a shell script
-----------------------------------

You don't program the iGPU directly from a shell — you call tools that use it.

**Video encode/decode (Quick Sync) via ffmpeg** — the workhorse:

.. code:: bash

   # hardware-DECODE + hardware-ENCODE, staying on the GPU end to end
   ffmpeg -hwaccel qsv -c:v h264_qsv -i input.mp4 \
          -c:v hevc_qsv -global_quality 22 -look_ahead 1 output.mp4

   # verify the path is really hardware (look for "hardware accelerated implementation")
   ffmpeg -v verbose -i input.mp4 -c:v hevc_qsv -t 3 -f null - 2>&1 | grep -i mfx

**Inspect capabilities from a script:**

.. code:: bash

   ffmpeg -hide_banner -hwaccels                 # qsv, dxva2, d3d11va, ...
   ffmpeg -hide_banner -encoders | grep qsv      # which QSV encoders the build has

**PowerShell — query the device, gate a script on it:**

.. code:: powershell

   $g = Get-CimInstance Win32_VideoController | Where-Object Name -like '*Intel*'
   if ($g) { "iGPU present: $($g.Name), driver $($g.DriverVersion)" }

**Linux — VA-API is the shell-level handle to the same engine:**

.. code:: bash

   vainfo                                          # entrypoints (VAEntrypointEncSlice = encode)
   ffmpeg -hwaccel vaapi -vaapi_device /dev/dri/renderD128 \
          -i in.mp4 -c:v hevc_vaapi -qp 22 out.mp4

This is exactly the layer slimv operates at: it shells out to ffmpeg's ``qsv``
encoders and reads back the results.

--------------

.. _7-accessing-it-from-c:

7. Accessing it from C
----------------------

There are three native entry points, one per job:

.. _a-video--intel-onevpl-formerly-media-sdk:

(a) Video — Intel **oneVPL** (formerly Media SDK)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The C API for Quick Sync encode/decode/transcode. ffmpeg's ``qsv`` is built on it.

.. code:: c

   #include <vpl/mfx.h>            /* oneVPL dispatcher */
   mfxLoader  loader  = MFXLoad();
   mfxSession session = NULL;
   /* request a hardware (not software) implementation */
   mfxConfig cfg = MFXCreateConfig(loader);
   mfxVariant impl = { .Type = MFX_VARIANT_TYPE_U32, .Data.U32 = MFX_IMPL_TYPE_HARDWARE };
   MFXSetConfigFilterProperty(cfg, (const mfxU8 *)"mfxImplDescription.Impl", impl);
   MFXCreateSession(loader, 0, &session);
   /* ... configure mfxVideoParam (codec, resolution, target quality), then
      MFXVideoENCODE_Init / EncodeFrameAsync in a loop ... */

- Install: **Intel oneVPL** (part of oneAPI Base Toolkit, or the standalone
  ``libvpl``/``onevpl`` package).
- Build (Linux): ``gcc enc.c -lvpl -o enc``. Windows: link ``vpl.lib`` (MSVC) — or
  under your **MSYS2 UCRT64**, ``gcc enc.c $(pkg-config --cflags --libs vpl)``.

.. _b-compute--opencl-or-oneapi--level-zero:

(b) Compute — **OpenCL** or **oneAPI / Level Zero**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

General math on the 24 EUs.

.. code:: c

   #include <CL/cl.h>             /* OpenCL 1.2/2.1 headers */
   cl_platform_id   plat;  clGetPlatformIDs(1, &plat, NULL);
   cl_device_id     dev;   clGetDeviceIDs(plat, CL_DEVICE_TYPE_GPU, 1, &dev, NULL);
   cl_context       ctx  = clCreateContext(NULL, 1, &dev, NULL, NULL, NULL);
   /* build a kernel string with clCreateProgramWithSource, enqueue on a command
      queue — the GPU runs your kernel across its EUs in parallel. */

- Link: ``gcc compute.c -lOpenCL -o compute``.
- **Runtime requirement (your machine):** the OpenCL *loader* (``OpenCL.dll``) is
  present but the **Intel GPU runtime (``igdrcl64.dll``) is not installed**, so
  ``clGetDeviceIDs(...GPU...)`` will find no GPU device yet. Install the
  **Intel Graphics driver (full package)** or the **Intel Compute Runtime
  (NEO)** to get it; then the iGPU appears as an OpenCL device.
- Modern alternative: **oneAPI Level Zero** (``ze_loader.dll`` *is* present) or
  **SYCL/DPC++** (``sycl`` in the oneAPI toolkit) — same EUs, newer model.

.. _c-graphics--direct3d-1112-vulkan-opengl:

(c) Graphics — Direct3D 11/12, Vulkan, OpenGL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a device on the Intel adapter and render. ``ID3D11Device`` /
``vkCreateDevice`` (pick the Intel ``VkPhysicalDevice``) / WGL. This is the job the
Android emulator uses via ANGLE.

--------------

.. _8-accessing-it-from-python:

8. Accessing it from Python
---------------------------

.. _a-video--call-ffmpegs-qsv-simplest-what-slimv-does:

(a) Video — call ffmpeg's QSV (simplest, what slimv does)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   import subprocess
   subprocess.run([
       "ffmpeg", "-y", "-i", "in.mp4",
       "-c:v", "hevc_qsv", "-global_quality", "22", "-tag:v", "hvc1",
       "out.mp4",
   ], check=True)

This is the practical, robust route — no GPU bindings to install, ffmpeg handles
the oneVPL plumbing. (It's the whole basis of slimv.)

.. _b-compute--pyopencl:

(b) Compute — **PyOpenCL**
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   import pyopencl as cl
   ctx   = cl.create_some_context()      # pick the Intel GPU device
   queue = cl.CommandQueue(ctx)
   prg = cl.Program(ctx, """
     __kernel void scale(__global float *a, float k){ int i=get_global_id(0); a[i]*=k; }
   """).build()
   # upload a buffer, run prg.scale across N work-items on the EUs, read back

``pip install pyopencl``. Needs the same Intel GPU OpenCL **runtime** as §7(b) —
without ``igdrcl64.dll`` PyOpenCL will only see the CPU, not the iGPU.

.. _c-intel-native-compute--dpctl--numba-dpex-oneapi:

(c) Intel-native compute — **dpctl / numba-dpex (oneAPI)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   import dpctl
   print([d.name for d in dpctl.get_devices()])   # lists the Level-Zero GPU device

``pip install dpctl`` (from Intel's channel). Uses the Level Zero loader already on
your machine; pairs with ``numba-dpex`` to write GPU kernels in Python.

.. _d-imagevision--opencv-with-opencl-transparent-api:

(d) Image/vision — **OpenCV with OpenCL (Transparent API)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   import cv2
   img = cv2.UMat(cv2.imread("frame.png"))   # UMat -> runs on the GPU via OpenCL
   blur = cv2.GaussianBlur(img, (21, 21), 0) # executes on the iGPU if OpenCL is up
   cv2.imwrite("out.png", blur.get())
   print("OpenCL available:", cv2.ocl.haveOpenCL())

..

   **Bottom line for compute on this laptop:** the *loaders* are present
   (``OpenCL.dll``, ``ze_loader.dll``) but the Intel GPU *runtime* isn't, so OpenCL/
   oneAPI won't see the HD 630 until you install the Intel Graphics full driver or
   the Compute Runtime. **Video (Quick Sync) needs none of that** — it works today
   through ffmpeg, which is why it was the right tool for the encoding job.

--------------

.. _9-gpu-compute-explained-opencl-oneapi-and-opencv-gpu:

9. GPU compute explained: OpenCL, oneAPI, and OpenCV-GPU
--------------------------------------------------------

Job #4 from §4 — **GPGPU compute** — deserves its own explanation, because the
three names that keep coming up (OpenCL, oneAPI, OpenCV-GPU) are layers in the
same space, at different levels. None of this is video encoding; that is the
separate fixed-function Quick Sync block (§4, job #3). This is about running
*general math* on the GPU's shader cores.

The big idea: GPGPU
~~~~~~~~~~~~~~~~~~~

A GPU has **many simple cores** (your HD 630 has 24 EUs, each running several
threads); a CPU has **a few powerful cores**. For work that applies **the same
operation to lots of data** (every pixel, every array element), the GPU does
thousands at once. It is **SIMD / data-parallel** taken to an extreme — the same
idea as a CPU vector unit, but with far more lanes.

The cost of that power: you express the work as a **kernel** (a small function
that runs once per data element), the framework launches it across all the GPU's
lanes, and you move data to and from GPU memory. OpenCL, oneAPI, and OpenCV-GPU
are three ways to do exactly that, at different levels of abstraction.

.. _1-opencl--the-open-cross-vendor-standard:

1. OpenCL — the open, cross-vendor standard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **What:** "Open Computing Language" — a Khronos open standard for parallel
  compute across **any** vendor (Intel, AMD, NVIDIA, even CPUs/FPGAs).

- **How it feels:** you write **kernels in a C dialect** (OpenCL C); a host
  program (C/C++/Python) compiles them *at runtime* for whatever device is
  present, then enqueues them.

  .. code:: c

     __kernel void add(__global float* a, __global float* b, __global float* c) {
         int i = get_global_id(0);   /* "which element am I?" */
         c[i] = a[i] + b[i];         /* runs once per element, in parallel */
     }

- **Think of it as:** the **portable assembly** of GPU compute — verbose and
  low-level, but it runs everywhere. Mature and ubiquitous.

- This is the layer that is **broken on this HD 630 right now** (the GPU OpenCL
  ICD did not register — see §10).

.. _2-oneapi--intels-modern-stack-sycl--dpc--level-zero:

2. oneAPI — Intel's modern stack (SYCL / DPC++ / Level Zero)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Intel's answer to "OpenCL is clunky." Three pieces you will hear:

- **SYCL / DPC++** — **single-source C++**: host code and kernels in *one* modern
  C++ file, no separate kernel language. Much nicer than OpenCL; compiled by
  ``icpx``/``gcc``. The high-level, productive layer.

  .. code:: cpp

     q.parallel_for(N, [=](auto i){ c[i] = a[i] + b[i]; });  // a GPU kernel, in C++

- **Level Zero** — the **low-level driver API** underneath (OpenCL's runtime
  equivalent, but newer and leaner). This is the ``ze_intel_gpu64.dll`` that **is**
  installed on this machine — the reason it is the recommended fallback when
  OpenCL will not register.

- **oneAPI** — the umbrella: SYCL + Level Zero + a stack of optimized libraries
  (oneMKL math, oneDNN deep learning, etc.).

- **Why it matters here:** it is the *current*, vendor-blessed path for Intel
  GPUs, and its driver layer (Level Zero) is present even though OpenCL is not —
  so it is the most likely way to actually use the HD 630 for compute.

.. _3-opencv-gpu--not-a-compute-api-but-a-consumer-of-one:

3. OpenCV-GPU — not a compute API, but a *consumer* of one
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **What:** OpenCV is the standard **computer-vision / image-processing** library
  (``cv2`` in Python, C++ underneath). "OpenCV-GPU" = OpenCV running its operations
  **on the GPU via OpenCL** under the hood.

- **How:** its **Transparent API** — wrap an image in a ``UMat`` instead of a
  ``Mat``, and operations (blur, resize, edge-detect, color convert, optical
  flow…) execute on the GPU automatically *if* OpenCL is available.

  .. code:: python

     img   = cv2.UMat(cv2.imread("frame.png"))   # UMat -> GPU
     edges = cv2.Canny(img, 100, 200)            # runs on the iGPU via OpenCL

- **So:** OpenCV-GPU **rides on OpenCL** — meaning on this machine it currently
  falls back to CPU (OpenCL has no GPU). It is an *application* of #1, not a
  separate stack.

How they relate (the layer picture)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

   Your code (image filter, ML, simulation)
           │
      ┌────┴───────────────┬───────────────────┐
   OpenCV-GPU          your OpenCL          your SYCL/oneAPI
   (uses OpenCL)        kernels              (C++ single-source)
      │                    │                     │
      └──── OpenCL runtime ─┘            Level-Zero runtime
                   │                            │
               Intel GPU driver (NEO) ──────────┘
                   │
             Intel HD 630 (the 24 EUs)

What you actually use this for
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Not video encoding (that is the separate Quick Sync block). GPGPU is for:

- **Image / video processing** — filters, scaling, color, denoise, optical flow
  (OpenCV, or ffmpeg's OpenCL filters).
- **Signal / array math** — FFTs, convolutions, matrix ops over big arrays.
- **Light ML / inference** — small neural nets, embeddings.
- **Simulation** — anything data-parallel (particle systems, cellular automata).

Bottom line for this HD 630
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **OpenCL** = the broken-right-now path (GPU ICD unregistered).
- **oneAPI / Level Zero** = the path that *might* work (its driver is installed) —
  the one worth testing next.
- **OpenCV-GPU** = depends on OpenCL, so it follows whatever OpenCL does.
- And again: **none of this touches video / Quick Sync**, which works regardless.

oneAPI and Level Zero, in depth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The two names get used loosely, so to be precise: **oneAPI is the whole
ecosystem; Level Zero is one specific, low-level API inside it.** Mapped to
concepts you already know (OpenCL, the CUDA driver API):

.. _oneapi--the-umbrella:

oneAPI — the umbrella
^^^^^^^^^^^^^^^^^^^^^

oneAPI is Intel's **open, cross-architecture programming platform**: the goal is
*one* codebase that targets CPUs, GPUs, FPGAs, and other accelerators — across
vendors, not just Intel. It is three things at once:

1. **An open specification** (governed by the UXL Foundation now) — anyone can
   implement it.
2. **A programming model** — write the code once, run on different hardware.
3. **A concrete toolkit** (Intel oneAPI Base Toolkit) — compiler, libraries,
   profilers.

Its components:

+----------------------+----------------------+----------------------+
| Layer                | What it is           | Analogy              |
+======================+======================+======================+
| **SYCL / DPC++**     | The **high-level     | CUDA C++ / the CUDA  |
|                      | language** —         | runtime API          |
|                      | single-source modern |                      |
|                      | C++ for host +       |                      |
|                      | kernels. DPC++ is    |                      |
|                      | Intel's SYCL         |                      |
|                      | compiler (``icpx``). |                      |
+----------------------+----------------------+----------------------+
| **oneAPI libraries** | Drop-in optimized    | cuBLAS, cuDNN, etc.  |
|                      | libs: **oneMKL**     |                      |
|                      | (math/BLAS/FFT),     |                      |
|                      | **oneDNN** (deep     |                      |
|                      | learning),           |                      |
|                      | **oneTBB**           |                      |
|                      | (threading),         |                      |
|                      | **oneVPL** (video —  |                      |
|                      | the Quick Sync API   |                      |
|                      | you've used)         |                      |
+----------------------+----------------------+----------------------+
| **Level Zero**       | The **low-level      | the CUDA driver API  |
|                      | driver API**         | / OpenCL runtime     |
|                      | underneath it all    |                      |
+----------------------+----------------------+----------------------+

So **SYCL is the front door; Level Zero is the basement.** You normally write
SYCL (or just call a library), and *they* call Level Zero to drive the device.
But you can also call Level Zero directly when you need full control.

.. _level-zero--exactly-what-it-is:

Level Zero — exactly what it is
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Level Zero** (the API behind ``ze_loader.dll`` + the ``ze_intel_gpu64.dll`` driver
on this machine) is a **low-level, explicit, system-level interface to an
accelerator.** It is the modern replacement for the OpenCL runtime — leaner, more
explicit, and with capabilities OpenCL lacks.

"Low-level and explicit" means **you** manage almost everything (like the CUDA
driver API vs the runtime API):

- **Drivers & devices** — enumerate ``ze_driver_handle_t`` → ``ze_device_handle_t``
  (the HD 630), query properties.
- **Contexts** — a container for resources.
- **Command lists & command queues** — you *record* operations (kernel launches,
  copies) into a **command list**, then *submit* the list to a **queue**. OpenCL
  hides this; Level Zero exposes it, like Vulkan command buffers — closer to the
  metal, and it lets you build a list once and replay it cheaply.
- **Memory — USM (Unified Shared Memory)** — explicit pointer-based allocation in
  three flavours: **device** (fast, GPU-only), **host** (CPU RAM the GPU can
  reach), and **shared** (migrates between them automatically). No opaque
  ``cl_mem`` buffers; you get real C pointers. A big ergonomic win, and a natural
  fit on a shared-memory iGPU.
- **Modules & kernels** — load a compiled kernel binary (**SPIR-V**, a portable
  IR), get kernel handles, set args, launch over an N-dimensional grid.
- **Events, fences, barriers** — explicit synchronization between host and
  device, and between operations.

The flavour of it (pseudocode):

.. code:: c

   zeInit(0);
   zeDriverGet(&n, &driver);
   zeDeviceGet(driver, &n, &device);           // <- the HD 630
   zeContextCreate(driver, &desc, &ctx);
   zeCommandListCreate(ctx, device, &desc, &cl);   // record into this
   zeCommandListAppendLaunchKernel(cl, kernel, &grid, NULL, 0, NULL);
   zeCommandListClose(cl);
   zeCommandQueueExecuteCommandLists(queue, 1, &cl, fence);  // submit

Notice how much is **explicit** — that is the point. Level Zero is designed for
*runtimes and compilers* (SYCL sits on top of it) and for engineers who want
maximum control and lowest overhead. It also reaches **beyond compute into system
management** — power, telemetry, frequency, RAS — via its **"Sysman"** API,
making it far closer to a real driver than OpenCL ever was.

Where each sits (the stack)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   Your app
      │
      ├── SYCL / DPC++  (high-level C++)            ← most people write here
      ├── oneMKL / oneDNN / oneVPL (libraries)      ← or just call a library
      │        │
      └────────┴──► Level Zero  (low-level driver API)   ← or write here for control
                         │
                 ze_intel_gpu64.dll  (Intel L0 GPU driver)   ← installed on your box
                         │
                    Intel HD 630 (24 EUs)

.. _level-zero-vs-opencl-vs-cuda--the-one-line-mental-model:

Level Zero vs OpenCL vs CUDA — the one-line mental model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

+------------------+------------------------+------------------------+
|                  | Role                   | Comparable to          |
+==================+========================+========================+
| **OpenCL**       | older open standard;   | CUDA runtime-ish,      |
|                  | runtime + C kernels    | cross-vendor           |
+------------------+------------------------+------------------------+
| **SYCL / DPC++** | modern high-level C++  | CUDA C++               |
|                  | (oneAPI's language)    |                        |
+------------------+------------------------+------------------------+
| **Level Zero**   | modern **low-level**   | CUDA driver API /      |
|                  | driver API (oneAPI's   | Vulkan-for-compute     |
|                  | base)                  |                        |
+------------------+------------------------+------------------------+

Why this matters for this HD 630 specifically
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- The OpenCL **GPU** path is broken (ICD not registered — §10).
- But the **Level Zero GPU driver is installed and present** (``ze_intel_gpu64.dll``)
  and uses a *different* registration path than the crashing OpenCL ICD.
- So Level Zero — reached most easily from Python via **``dpctl``** (Intel's
  Data-Parallel Control library) — is the **most likely way to actually get the
  HD 630 doing compute**, even though OpenCL won't. The test:
  ``pip install dpctl`` → ``dpctl.get_devices()`` and look for a ``level_zero:gpu``
  entry.

..

   **Caveat for Gen9.** oneAPI's *newest* GPU support has moved toward Xe/Arc, so
   even Level Zero may or may not enumerate this 2017 part — which is exactly why
   the move is to **test it** rather than assume.

--------------

.. _10-enabling-gpu-compute-the-intel-driver-and-compute-runtime-neo:

10. Enabling GPU compute: the Intel driver and Compute Runtime (NEO)
--------------------------------------------------------------------

Quick Sync video works out of the box, but **GPGPU compute** (OpenCL, oneAPI,
OpenCV-on-GPU) needs a *runtime* that is not always installed — which is the case
on this machine. This section explains the moving parts, how to install them, and
how to confirm it worked.

The three layers (and which one you're missing)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GPU compute on Windows is a stack. Each layer has a different job:

+----------------+----------------+----------------+----------------+
| Layer          | File(s)        | Role           | On this        |
|                |                |                | machine        |
+================+================+================+================+
| **ICD loader** | ``OpenCL.dll`` | Vendor-neutral | ✅ present     |
|                |                | front door.    |                |
|                |                | Apps link      |                |
|                |                | this; it       |                |
|                |                | *forwards*     |                |
|                |                | calls to       |                |
|                |                | whatever       |                |
|                |                | vendor         |                |
|                |                | runtimes are   |                |
|                |                | registered.    |                |
|                |                | Ships with     |                |
|                |                | Windows.       |                |
+----------------+----------------+----------------+----------------+
| **Level-Zero   | ``z            | Same idea for  | ✅ present     |
| loader**       | e_loader.dll`` | the newer      |                |
|                |                | oneAPI /       |                |
|                |                | Level-Zero     |                |
|                |                | API.           |                |
+----------------+----------------+----------------+----------------+
| **Intel GPU    | ``             | The **actual   | ❌ **missing** |
| runtime        | igdrcl64.dll`` | driver** that  |                |
| (NEO)**        | (OpenCL) +     | turns          |                |
|                | ``ze_int       | Ope            |                |
|                | el_gpu64.dll`` | nCL/Level-Zero |                |
|                | (Level-Zero)   | calls into     |                |
|                |                | work on the    |                |
|                |                | iGPU's EUs.    |                |
+----------------+----------------+----------------+----------------+

The loaders are just switchboards — with no Intel **runtime** behind them, a
program asking for a GPU device gets *nothing* (it sees only the CPU, or no
device at all). The missing piece is **NEO**.

What "NEO" is
~~~~~~~~~~~~~

**NEO** is the open-source name of the **Intel Compute Runtime** — Intel's
implementation of **OpenCL** and **oneAPI Level Zero** for its GPUs. ("Compute
Runtime" = the official name; "NEO" = the project/repo name; people use them
interchangeably.) It is *not* the display driver and *not* the media (Quick Sync)
driver — it is specifically the **compute** driver. Source and releases:
https://github.com/intel/compute-runtime.

What "Intel Graphics full driver" means
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Intel ships its graphics software two ways:

- **Full driver package** — the complete **Intel Graphics Driver** (on newer
  hardware, the *Intel Arc & Iris Xe Graphics* installer; on older parts like
  HD 630, the legacy *Intel Graphics – Windows DCH Driver*). This bundles
  **everything**: the display driver, the **Quick Sync media driver**, **and the
  Compute Runtime (NEO)**. Installing this is the easiest way to get compute,
  because NEO comes with it.
- **OEM / Windows Update driver** — the cut-down version that laptop vendors and
  Windows Update push. It reliably includes display + media, but **sometimes
  omits or lags the compute runtime** — which is very likely why ``igdrcl64.dll``
  is absent here even though video works.

So you have two routes to enable compute:

1. **Install Intel's full Graphics Driver** (recommended) — gets display + media

   - compute in one package, kept in sync.

2. **Install only the standalone Compute Runtime (NEO)** — if you'd rather not
   touch the working display/media driver, drop in just the NEO release. (More
   surgical, but you manage its version yourself.)

..

   **Caveat for HD 630 (Gen 9.5):** it is older hardware. Recent NEO releases have
   dropped legacy Gen support, so the **latest** Compute Runtime may not include
   Gen 9. The **full legacy Intel Graphics DCH driver** for HD 630 is the safer
   bet — it carries the matching (older) compute runtime for this GPU. Check the
   NEO releases page for the last version listing "Gen9 / SKL-CFL" before using the
   standalone route.

Install (Windows)
~~~~~~~~~~~~~~~~~

**Route 1 — full driver (recommended):**

1. Identify the part on **Intel ARK** (i7-7700HQ → HD 630).
2. Download the **Intel Graphics – Windows DCH Driver** (this is the *legacy*
   package that supports **6th–10th Gen** Core graphics, i.e. HD 630 / 7th Gen):

   - **Download page:** https://www.intel.com/content/www/us/en/download/19344/intel-graphics-windows-dch-drivers.html
   - **Latest version:** **31.0.101.2141** (newest build on the legacy 7th–10th
     Gen branch; supersedes the **31.0.101.2135** currently installed on this
     machine — same branch, safe update, still carries Gen 9 compute support).
   - **Installer name:** ``gfx_win_101.xxxx.exe`` (e.g. ``gfx_win_101.2141.exe``) —
     the exact filename is shown on the page once you pick the version.
   - **HD 630 support hub** (older versions / release notes):
     https://www.intel.com/content/www/us/en/support/products/98909/graphics/processor-graphics/intel-hd-graphics-family/intel-hd-graphics-630.html

3. If the installer warns the OEM (laptop maker) customised your driver, you can
   still install Intel's generic DCH driver; reboot.

..

   **Why this one, not standalone NEO:** the latest standalone Compute Runtime
   releases **dropped Gen 9** support, so they may not see HD 630. This full DCH
   package bundles the matching (older) compute runtime for this GPU — it is the
   reliable way to get ``igdrcl64.dll`` + the Level-Zero driver onto a 7th-Gen part.

**Route 2 — standalone NEO:**

1. Go to https://github.com/intel/compute-runtime/releases.
2. Pick a release that still lists your generation; download the Windows zip.
3. Unpack and register the runtime per the release notes (it provides
   ``igdrcl64.dll`` + the Level-Zero GPU driver).

**Linux (for reference / dual-boot):**

.. code:: bash

   sudo apt install intel-opencl-icd    # NEO OpenCL runtime
   sudo apt install clinfo && clinfo    # should now list "Intel(R) Graphics [0x...]"
   # oneAPI Level-Zero GPU driver:
   sudo apt install intel-level-zero-gpu level-zero

Verify it worked
~~~~~~~~~~~~~~~~

After installing, confirm the **GPU** (not just the CPU) shows up as a compute
device:

.. code:: powershell

   # OpenCL — needs clinfo.exe (ships with some SDKs) OR use Python below
   clinfo            # look for a Device Type: GPU entry named "Intel(R) HD Graphics 630"

.. code:: python

   # Quick cross-check from Python (pip install pyopencl)
   import pyopencl as cl
   for p in cl.get_platforms():
       for d in p.get_devices():
           print(d.platform.name, "|", cl.device_type.to_string(d.type), "|", d.name)
   # success = a line with GPU | Intel(R) HD Graphics 630

.. code:: python

   # Or via OpenCV
   import cv2; print("OpenCL devices visible:", cv2.ocl.haveOpenCL())

Signs it's working: a **GPU**-type device named *Intel(R) HD Graphics 630*
appears; PyOpenCL/OpenCV see the GPU. If you still see only the CPU (or PyOpenCL
crashes), the GPU OpenCL ICD didn't register — see the next two notes.

   **Where the files actually live (DCH drivers).** Modern **DCH** Intel drivers
   do **not** drop the runtime into ``C:\Windows\System32``. They install it under
   ``C:\Windows\System32\DriverStore\FileRepository\iigd_dch.inf_amd64_*\`` (look
   for ``igdrcl64.dll`` = OpenCL GPU runtime, ``ze_intel_gpu64.dll`` = Level-Zero GPU
   driver) and register it via the registry. So **checking System32 gives a false
   negative.** Verify the right way instead:

   .. code:: powershell

      # is the GPU OpenCL runtime on disk?
      Get-ChildItem "$env:WINDIR\System32\DriverStore\FileRepository" -Recurse -Filter igdrcl64.dll
      # which OpenCL ICDs are REGISTERED (this is what apps actually load)?
      reg query "HKLM\SOFTWARE\Khronos\OpenCL\Vendors"

   You want the **GPU** runtime path listed under that registry key — not only an
   ``IntelOpenCL64.dll`` (that one is the **CPU** OpenCL runtime).

..

   **Real-world result on this machine (Gen9 HD 630, 2026-06).** Installing the
   full DCH driver placed **both** ``igdrcl64.dll`` and ``ze_intel_gpu64.dll`` in the
   DriverStore — but the **GPU OpenCL ICD was not auto-registered**: only the CPU
   runtime (``IntelOpenCL64.dll``) appeared under ``Khronos\OpenCL\Vendors``, and
   calling ``clGetPlatformIDs`` through it **crashed the loader** (``0xC0000005``
   access violation). **A reboot did not fix it** — verified by comparing the last
   boot time to the driver-file install time: the machine had already booted
   *after* the install, yet the GPU ICD was still unregistered. So on this Gen9
   part the current DCH driver genuinely does not wire up GPU OpenCL. Remaining
   options, in order of preference:

   1. **Use oneAPI Level-Zero instead of OpenCL** — the ``ze_intel_gpu64.dll``
      driver is present and is a *separate* stack from the crashing OpenCL ICD.
      Test: ``pip install dpctl`` then
      ``python -c "import dpctl; print(dpctl.get_devices())"`` — it may list the GPU
      even though OpenCL doesn't.
   2. **Register the GPU OpenCL ICD manually**: add a ``REG_DWORD = 0`` value named
      after the full path to the DriverStore ``igdrcl64.dll`` under
      ``HKLM\SOFTWARE\Khronos\OpenCL\Vendors`` (back up the key first). The *CPU* ICD
      (``IntelOpenCL64.dll``) currently crashes the loader, so you may also need to
      remove/disable that entry before enumeration can reach the GPU.
   3. Accept that **GPU compute isn't available** on this Gen9 + driver combo.

   **Check boot-vs-install before blaming a reboot:** compare
   ``(Get-CimInstance Win32_OperatingSystem).LastBootUpTime`` to the DriverStore
   ``igdrcl64.dll`` creation time. If you've already booted *after* the install,
   another reboot will not change the registration.

   The lesson: on older (Gen9) hardware, "the full driver installed" does **not**
   guarantee working GPU OpenCL — confirm with an actual device enumeration, and
   check boot-vs-install times before assuming a reboot will help.

   **Do you even need this?** Only for GPU **compute**. Everything slimv and the
   video work does is **Quick Sync media**, which uses a *different* driver that is
   already present — so none of this is required for encoding. Install it only if
   you want OpenCL/oneAPI/OpenCV-GPU or ffmpeg's OpenCL filters.

--------------

.. _11-resources:

11. Resources
-------------

**Identify your exact chip**

- **Intel ARK** — https://ark.intel.com — search "i7-7700HQ" or "HD Graphics
  630": specs, EU count, supported codecs, max resolution, feature dates.
- **Intel Graphics driver downloads** — legacy DCH package for 6th–10th Gen
  (HD 630): https://www.intel.com/content/www/us/en/download/19344/intel-graphics-windows-dch-drivers.html
  (latest **31.0.101.2141**, installer ``gfx_win_101.xxxx.exe``; the full package
  includes the OpenCL/Level-Zero runtime, not just display). Generic Download
  Center: https://www.intel.com/content/www/us/en/download-center/home.html.

**Quick Sync / video (C and tooling)**

- **oneVPL / libvpl** docs & source — https://github.com/intel/libvpl and the
  spec at https://intel.github.io/libvpl/.
- **ffmpeg QSV** wiki — https://trac.ffmpeg.org/wiki/Hardware/QuickSync.
- **VA-API** (Linux equivalent) — https://github.com/intel/libva,
  https://github.com/intel/media-driver.

**Compute (OpenCL / oneAPI)**

- **Intel Compute Runtime (NEO)** — https://github.com/intel/compute-runtime
  (the missing ``igdrcl64.dll`` lives here).
- **oneAPI / Level Zero** — https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html,
  spec at https://spec.oneapi.io/level-zero/latest/index.html.
- **PyOpenCL** docs — https://documen.tician.de/pyopencl/.

**Architecture / deep reading (your EE/systems angle)**

- Intel **"Graphics Architecture" programmer's reference manuals (PRMs)** for
  Gen 9 — open-source register-level docs:
  https://www.intel.com/content/www/us/en/docs/graphics-for-linux/developer-reference/1-0/programmer-reference-manuals.html.
- **Architecture of the Intel Processor Graphics** Gen9 whitepaper (Junkins) —
  searchable PDF; the canonical EU/slice/media-engine overview.

**Android emulator**

- **Configure hardware acceleration** —
  https://developer.android.com/studio/run/emulator-acceleration.
- **Emulator ``-gpu`` modes** —
  https://developer.android.com/studio/run/emulator-commandline.
- **WHPX vs HAXM vs AEHD** — the acceleration page above covers which to use when
  Hyper-V is present (your case → WHPX).

**Inspection tools**

- **GPU-Z** — https://www.techpowerup.com/gpuz/ · **HWiNFO** —
  https://www.hwinfo.com/.
- Linux: ``intel-gpu-tools`` (``intel_gpu_top``), ``vainfo``, ``clinfo``.
