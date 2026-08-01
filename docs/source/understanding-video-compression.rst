.. _understanding--compressing-video-files-without-losing-quality:

Understanding & Compressing Video Files Without Losing Quality
==============================================================

A practical guide to reading what a video file actually *is*, understanding every
term in its technical profile, and re-encoding it to a much smaller size while
keeping the picture you care about.

Worked example throughout: an **IT-certification screencast course** —
**206 files, 37.75 GB, ~28 hours** of 1080p screen-recording video (the figures
in §7 reflect an early partial snapshot of 82 files before the full set was in
place).

--------------

Table of Contents
-----------------

**Part I — Practical: reading & shrinking video**

1. `The goal: smaller files, same quality <#1-the-goal>`__
2. `How to inspect a video file (ffprobe) <#2-how-to-inspect>`__
3. `The anatomy of a video file — every term explained <#3-anatomy>`__

   - Container · Video codec · Resolution · Pixel format · Frame rate · Video bitrate · Audio

4. `Decoding the specific values you'll see <#4-decoding-values>`__

   - H.264 (AVC) · yuv420p (8-bit) · AAC-LC, 192 kbps, stereo, 48 kHz

5. `Codecs for re-encoding: H.264 vs H.265 vs AV1 <#5-codecs>`__

   - `5B. Hardware vs software encoders: speed vs density (QSV, x265, AV1) <#5b-hw-vs-sw>`__

6. `CRF — the quality dial (22 vs 24 vs 26) <#6-crf>`__
7. `Reading our real screencast files (worked example) <#7-worked-example>`__
8. `The recommended command <#8-command>`__

   - `8B. Case study: choosing the encoder with VMAF (real measured run) <#8b-casestudy>`__
   - `8C. Reading a benchmark table: VMAF, global_quality, and the quality ladder <#8c-reading-a-table>`__
   - `8D. When a file won't shrink: Size = bitrate × duration <#8d-size-equation>`__
   - `8E. What determines encode speed <#8e-encode-speed>`__
   - `8F. A bad-encoding case study: over-bitrating static content (88% wasted) <#8f-overbitrating>`__
   - `8G. When an encode suddenly fails: memory commit, not free RAM <#8g-commit>`__
   - `8H. Moving decode to the GPU: freeing the CPU (and why it doesn't speed things up) <#8h-gpu-decode>`__
   - `8I. Worked example: re-encoding a new course, command by command <#8i-new-course>`__

9. `Quick reference cheat-sheet <#9-cheatsheet>`__

**Part II — Going deeper: how it all works**
10. `Containers in depth: the rise and fall of AVI <#10-avi>`__
11. `Inside the box: how containers are built (RIFF / atoms / EBML) <#11-container-internals>`__
12. `Below the container: the video stream itself (NAL, I/P/B, GOP) <#12-video-stream>`__

**Appendices**

- `A. Abbreviations & glossary <#appendix-a>`__
- `B. Further reading: books, tools & source code <#appendix-b>`__
- `C. The big-picture path: from CRT to AV1 <#appendix-c>`__
- `D. Roadmap: topics to write next <#appendix-d>`__

--------------

.. _1-the-goal-smaller-files-same-quality:

1. The goal: smaller files, same quality
----------------------------------------

A video can be made smaller two completely different ways:

- **Throw away picture** — lower the resolution (1080p → 720p), drop frames, or
  crush the quality. The file shrinks but it *looks worse*. ❌
- **Encode smarter** — keep the resolution, frame rate, and visual quality
  exactly, but store the same picture using a more efficient **codec**. The file
  shrinks and looks the same. ✅

This guide is entirely about the second approach. The single biggest lever is
**switching from an old codec (H.264) to a modern one (H.265)**, which can cut
screen-recording video by 50–80% with no visible difference.

   **Why screen recordings shrink so dramatically:** most of the screen doesn't
   change between frames (a slide sits still for 20 seconds). Modern codecs only
   store *what changed*, so static content costs almost nothing.

--------------

.. _2-how-to-inspect-a-video-file-ffprobe:

2. How to inspect a video file (ffprobe)
----------------------------------------

``ffprobe`` (ships with ffmpeg) tells you everything about a file. The command:

.. code:: bash

   ffprobe -v error -show_entries \
     format=duration,bit_rate:stream=codec_type,codec_name,profile,width,height,r_frame_rate,bit_rate,pix_fmt,sample_rate,channels \
     -of default "video.mp4"

Typical output (one of our screencast files):

::

   [STREAM]                 <- the VIDEO stream
   codec_name=h264
   profile=High
   codec_type=video
   width=1920
   height=1080
   pix_fmt=yuv420p
   bit_rate=3064827
   [/STREAM]
   [STREAM]                 <- the AUDIO stream
   codec_name=aac
   profile=LC
   codec_type=audio
   sample_rate=48000
   channels=2
   bit_rate=192001
   [/STREAM]
   [FORMAT]                 <- the file as a whole
   duration=1079.030944
   bit_rate=3262918
   [/FORMAT]

Every number above is explained in the next two sections.

--------------

.. _3-the-anatomy-of-a-video-file--every-term-explained:

3. The anatomy of a video file — every term explained
-----------------------------------------------------

A video file has three layers: the **container** (the box), the **streams**
inside it (video + audio), and the properties of each stream.

Container
~~~~~~~~~

The **file wrapper / box** — what the ``.mp4``, ``.mkv``, ``.avi``, ``.mov``, ``.ts``
extension refers to. It holds the video stream, the audio stream, subtitles, and
metadata together, and keeps them in sync.

**Key idea: the container is not the quality.** An ``.mp4`` and an ``.mkv`` can hold
the *exact same* video and look identical — they're just different boxes.
Containers differ in what they're *allowed* to hold and how widely they play:

========= =================== ========================================================================================================
Container Best for            Notes
========= =================== ========================================================================================================
**MP4**   Universal playback  Plays everywhere (phones, TVs, browsers). Can't hold some exotic codecs.
**MKV**   Flexibility         Holds anything (any codec, multiple audio/subtitle tracks). Slightly less universal on hardware players.
**TS**    Streaming/broadcast Resilient to corruption; larger overhead.
========= =================== ========================================================================================================

For these screencast videos we keep **MP4** — universal and holds H.265 fine.

Video codec
~~~~~~~~~~~

The **compression method** used to encode the moving picture — the single most
important factor for file size. Examples: **H.264, H.265, AV1, VP9**. This is
*not* the same as the container: an MP4 file usually contains H.264 *or* H.265
video. Switching the codec (re-encoding) is how we shrink the file.

Resolution
~~~~~~~~~~

The **pixel dimensions** of the picture: ``width × height``. ``1920×1080`` = "1080p"
or "Full HD". More pixels = sharper but bigger. We **keep resolution unchanged**
— downscaling is the thing we're deliberately *not* doing.

========== ===============
Resolution Name
========== ===============
3840×2160  4K / UHD
1920×1080  1080p / Full HD
1280×720   720p / HD
640×480    480p / SD
========== ===============

Pixel format
~~~~~~~~~~~~

**How color is stored per pixel.** Written like ``yuv420p``. It encodes two things:

- **Color model + chroma subsampling** (``yuv420``, ``yuv444``, …) — how much color
  detail is kept vs. the brightness detail. See §4.
- **Bit depth** (``p`` = 8-bit, ``p10le`` = 10-bit) — how many shades per color
  channel. 8-bit = 16.7M colors; 10-bit = ~1B (smoother gradients).

Frame rate
~~~~~~~~~~

**How many still images play per second**, written ``r_frame_rate=24000/1001``
(a fraction — divide it: 24000 ÷ 1001 = **23.976 fps**). Common values: 23.976
(film), 25 (PAL), 30, 60. Higher = smoother motion but more data. We keep it
unchanged.

   Why the weird fraction? ``24000/1001`` is the exact NTSC film rate. ffprobe
   reports the precise ratio rather than rounding to "24".

Video bitrate
~~~~~~~~~~~~~

**Bitrate is how many bits the video spends per second of playback** — the data
rate of the stream, and the direct driver of both size and quality *for a given
codec*. Reported in bits/sec: ``bit_rate=3064827`` = **~3.06 Mbps** (megabits per
second). Units: **kbps** = thousands of bits/sec, **Mbps** = millions.

**The analog parallel.** Bitrate is the digital cousin of *bandwidth* /
*data rate*. An analog TV channel occupied so many MHz of bandwidth to carry its
picture; a digital stream occupies so many Mbps of data rate to carry its
picture. More information per second = a wider pipe.

**Why it drives file size — the equation.** Size is just *rate × time*, exactly
like distance = speed × time:

   **Size ≈ bitrate × duration.**

- Worked example: 2.42 Mbps × 80 min × 60 s/min = 11,616 Mb ÷ 8 ≈ **1.45 GB** —
  why an 80-minute tutorial is huge even at a modest rate (see §8D).
- Unit bridge: **8 bits = 1 byte**, so **Mbps ÷ 8 = MB/s**. A 2.5 Mbps stream
  writes ~0.31 MB to disk every second.

**What bitrate buys you.** For a fixed codec + resolution + content, bitrate is
the **dial between quality and size**:

- More bits/sec → more detail preserved → bigger file.
- Fewer bits/sec → the encoder discards more → smaller file, eventually visible
  artifacts.
- The whole game (CRF / ``global_quality``, §6) is to **spend the fewest bits per
  second that still look transparent**.
- And the codec itself matters: a **modern codec reaches the same quality at a far
  lower bitrate** — H.265 at ~1 Mbps can look like H.264 at ~3 Mbps. That is the
  whole reason re-encoding to H.265 shrinks files.

**Three bitrates you'll see in ``ffprobe``:**

1. **Video stream bitrate** — bits/sec for the picture (the big one).
2. **Audio stream bitrate** — bits/sec for sound (e.g. 128 kbps).
3. **Overall / FORMAT bitrate** — video + audio + container overhead; the number
   usually quoted for "the file's bitrate."

**CBR vs VBR (constant vs variable).**

- **CBR** — the same bits/sec every second. Predictable; used in broadcast.
- **VBR** — spends **more bits on hard seconds** (motion, fine detail) and
  **fewer on easy ones** (a static slide). Modern quality-based encoding
  (CRF / ``global_quality``) is VBR — which is *why* a screencast of still slides
  compresses so dramatically: the easy seconds cost almost nothing. The single
  number you then see quoted is the **average** bitrate over the whole file.

..

   **Takeaway.** When this guide says "transparent at the lowest bitrate" (§8B/§8C)
   or "already-lean at 2.5 Mbps" (§8D), *bitrate* is the quantity being measured —
   the per-second data cost of the video, and the term that, multiplied by
   duration, gives the file size.

Audio
~~~~~

The sound stream, with its own codec and properties. From our file:
``aac``, ``LC``, ``sample_rate=48000``, ``channels=2``, ``bit_rate=192001``. Decoded in §4.

--------------

.. _4-decoding-the-specific-values-youll-see:

4. Decoding the specific values you'll see
------------------------------------------

.. _h264-also-called-avc:

``H.264`` (also called **AVC**)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **most common video codec in the world** (~2003). "H.264" is the standard's
name; "AVC" (Advanced Video Coding) is the same thing. Plays on literally
everything. It's excellent — but ~20 years old, so newer codecs beat it on
efficiency. **``profile=High``** just means it's using the full, modern H.264
feature set (normal for HD video). *This is what our source files are encoded in,
and what we're upgrading away from.*

``yuv420p`` (standard 8-bit color)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **default pixel format for almost all video**. Breaking it down:

- **yuv** — color is stored as **brightness (Y)** separate from **two color
  channels (U, V)**, instead of Red/Green/Blue. The eye is far more sensitive to
  brightness than color, so this split lets the codec save data on color.
- **420** — **chroma subsampling**. Full brightness detail is kept, but color
  detail is stored at **¼ resolution** (shared across 2×2 pixel blocks). You
  almost never notice on photographic/video content.
- **p** — **planar, 8-bit** per channel (256 levels each → 16.7M colors).

..

   **When 420 is noticeable:** tiny, high-contrast **colored text** (e.g. red
   text on black in a terminal) can look slightly fuzzy because its color edges
   get subsampled. For pure screen recordings of code/terminals, ``yuv444p`` (full
   color detail) is sharper — but it's bigger and less compatible. For these
   these screencast videos (mostly slides + talking head, already shot in 420), keeping
   **yuv420p** is the right call.

=============== ============== ==============================================
Pixel format    Color detail   Use
=============== ============== ==============================================
``yuv420p``     ¼ (subsampled) Standard — video, slides, talking head
``yuv444p``     Full           Sharpest colored text; bigger, less compatible
``yuv420p10le`` ¼, 10-bit      Smoother gradients (HDR / high-end)
=============== ============== ==============================================

``AAC-LC, 192 kbps, stereo, 48 kHz``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **audio** stream, fully decoded:

- **AAC** — Advanced Audio Coding, the standard modern audio codec (successor to
  MP3). **LC** = "Low Complexity," the normal everyday AAC profile.
- **192 kbps** — audio bitrate. Transparent for music; **generous for speech**.
  Voice narration is fine at 96–128 kbps, so this is a small extra place to save.
- **stereo** (``channels=2``) — two channels (left/right). Narration is often
  effectively mono, but stereo is harmless.
- **48 kHz** (``sample_rate=48000``) — samples per second, i.e. audio "resolution."
  48 kHz is the video-standard rate (CD audio is 44.1 kHz). Leave it as-is.

--------------

.. _5-codecs-for-re-encoding-h264-vs-h265-vs-av1:

5. Codecs for re-encoding: H.264 vs H.265 vs AV1
------------------------------------------------

This is the choice that actually shrinks the file. Same picture, more efficient
storage:

================ ==== ================================ =============== =================================
Codec            Age  Efficiency vs H.264              Encode speed    Playback support
================ ==== ================================ =============== =================================
**H.264 / AVC**  2003 baseline                         fast            **everything**
**H.265 / HEVC** 2013 **~50% smaller** at same quality slower          modern PCs, phones, TVs, browsers
**AV1**          2018 ~60%+ smaller                    **much** slower newer devices only
================ ==== ================================ =============== =================================

- **H.265 (HEVC)** is the **sweet spot** for this job: roughly half the size of
  H.264 at the same quality, while still playing in VLC, MPC-HC, modern browsers,
  and most phones/TVs from the last several years. The ffmpeg encoder is
  ``libx265``.
- **AV1** compresses a bit more but encodes *dramatically* slower and has weaker
  hardware playback — overkill for an 11-hour PC-watched course.
- **Re-encoding H.264 → H.264** only saves ~25–40% (you're just lowering the
  quality of an old codec). H.265 is the real win.

..

   **Codec ≠ container.** We're changing the **codec** (H.264→H.265) but keeping
   the **container** (.mp4). The file is still an ``.mp4``; what's *inside* is now
   H.265.

--------------

.. _5b-hardware-vs-software-encoders-speed-vs-density:

5B. Hardware vs software encoders: speed vs *density*
-----------------------------------------------------

§5 was about the **codec** — the *standard* (H.264 / H.265 / AV1), i.e. the rulebook
for how compressed video is written. This section is about the **encoder** — the
*program or silicon* that actually produces that codec. **The same codec can be
produced by very different encoders, and they are not equal.** Choosing the encoder is
a real decision (in slimv it's the ``--profile``), and it's the difference between a file
that's merely *smaller* and one that's *as small as it can be*.

The formats, quickly (recap)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **H.264 / AVC** — the old universal standard. Plays everywhere; bulky.
- **H.265 / HEVC** — the modern standard, ~\ **50% smaller** than H.264 at the same
  quality. What 4K Netflix and modern Blu-rays use.
- **AV1** — the newest, royalty-free standard, ~\ **30% smaller than HEVC** again. Where
  YouTube/Netflix are heading to cut bandwidth.

Those percentages are the *ceiling* the format allows. Whether you actually reach it
depends on the **encoder**.

Two ways to make the same HEVC: silicon vs software
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

=========== ================================================= ==============================================
\           **QSV (hardware)**                                **libx265 (software)**
=========== ================================================= ==============================================
Runs on     a fixed-function block inside the Intel **iGPU**  the **CPU** (general-purpose)
Designed to do *one* job — HEVC math — at real-time speed     do *anything*, including exhaustive search
Speed       very fast (≥ real-time, ~0% CPU)                  slow (minutes/file, pegs the CPU)
Density     **less dense** — bigger file for the same quality **denser** — smaller file for the same quality
Flexibility logic is baked into the wires; can't change       can try hundreds of strategies per block
=========== ================================================= ==============================================

A useful mental model: **QSV is an assembly-line worker; libx265 is a craftsman.**

What "exhaustive rate-distortion search" and "density" mean
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When an encoder hits a block of pixels it asks: *"If I throw away this much data, how
much visual damage results — and is it worth the bits saved?"* That trade-off (rate =
bits vs distortion = visible damage) is **rate-distortion optimization**.

- **libx265 (CPU)** has the time to try **hundreds** of ways to encode that one block
  — different partitionings, motion vectors, prediction modes — score each on
  size-vs-damage, and keep the best. That exhaustive search is why its output is
  **dense**: nearly every byte is *earning its keep*.
- **QSV (iGPU)** has roughly **1/100th of a second** per block, because its job is to
  sustain 60 fps in real time. It uses fast, "good-enough" shortcuts and moves on.

The consequence: **to reach the same visual quality, QSV must spend more bits** to cover
for the shortcuts it skipped. Its files are **less dense — bigger for the same look.**
That's not a defect; it's the deliberate trade of a real-time encoder.

Why a hardware encoder "keeps" already-lean files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is exactly why, with slimv's ``--keep-smaller`` (§8), a hardware profile leaves many
already-lean files untouched. Picture a source lecture already encoded at a modest
bitrate. Ask QSV to re-encode it at transparent quality and — because of its lower
density — it may need *more* bits than the original to hold that quality. slimv sees the
re-encode came out **bigger**, so it keeps the original. QSV didn't "fail"; the file was
simply already efficient enough that a real-time encoder can't beat it.

A **software** encoder (libx265) *could* often still beat that same file — its exhaustive
search can hold the same quality at a lower bitrate — but it would take **minutes per
file instead of seconds**.

.. _so-what-would-compress-more--and-at-what-cost:

So what would compress *more* — and at what cost?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **``libx265`` (CPU), e.g. ``balanced`` (CRF 23) or ``small`` (CRF 26)** — denser than QSV,
   so it shrinks some of the lean files QSV keeps → a higher overall %. **Cost:** CPU-
   bound and far slower, and it competes with anything else using your CPU (e.g. a
   transcription job).
2. **AV1** — the densest at *low* bitrates (the very regime lean lectures live in),
   typically ~20–30% smaller than HEVC. It would give the **best size** result — **but**
   an older (Gen9-era) iGPU has **no AV1 hardware encode**, and forcing AV1 onto the CPU
   runs **10–50× slower than real-time** (a multi-hour course → over a day, CPU maxed,
   machine unusable for anything else). Only practical with a newer AV1-capable GPU
   (Intel Arc / recent NVIDIA/AMD) or an ffmpeg built with ``libsvtav1`` and time to burn.
3. **Push the hardware encoder harder** — raise the quality number (e.g. QSV
   ``--gq 28``) so it emits smaller files that beat more originals. But that's **trading
   quality for size**, not gaining efficiency — the shortcuts are still there, you're
   just accepting more damage.

The ceiling on already-lean material (worked illustration)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A real example from a batch (mixed-bitrate programming course, ~1 Mbps median, 1080p):

- Of the files re-encoded, QSV shrank them **~47%** — a great result where there was fat.
- But **about two-thirds of the files were already lean** and got **kept-original** (QSV
  couldn't beat them), so the **blended saving was only ~18%.**

The lesson isn't "use a better encoder" — it's that **already-efficient sources have
little fat to give, whatever the encoder.** libx265 might lift that 18% somewhat by
beating more of the lean files, but you'd pay hours of CPU time for a modest extra slice,
and you'd be trading away some of the quality headroom those files still have.

There's also a **benchmarking lesson** here: a single sample can mislead. Benchmarking one
*high-bitrate* file from that course predicted ~47% for the whole thing — but the course
was mostly *lean* files, so the real blended result was far lower. **For a mixed-bitrate
library, sample several files across the bitrate range, not one.**

Bottom line
~~~~~~~~~~~

- **QSV / hardware** = best **speed-for-quality**; runs on idle iGPU silicon, leaves CPU
  and discrete GPU free. The right default for large batches.
- **libx265 / software** = best **size-for-quality**, at the cost of time and CPU.
- **AV1** = best size of all for low-bitrate content, but only sane on AV1-capable
  hardware.
- For a library that's **already lean**, the ceiling is low regardless — pick the encoder
  by what you value (throughput vs. last-few-percent) and what hardware is free.

--------------

.. _6-crf--the-quality-dial-22-vs-24-vs-26:

6. CRF — the quality dial (22 vs 24 vs 26)
------------------------------------------

**CRF = Constant Rate Factor.** It's how you tell the encoder *"keep this much
visual quality, and use whatever bitrate that takes."* This is the right way to
re-encode: you target **quality**, not a fixed size, so the encoder spends bits
only where the picture needs them (lots on motion, almost none on a static
slide).

**The scale is backwards from what you'd expect: lower CRF = higher quality =
bigger file.**

========== ========================================== ======== ==================================================
CRF (x265) Quality                                    Size     When to use
========== ========================================== ======== ==================================================
**18–20**  Near-transparent, archival                 Largest  Maximum safety margin
**22**     Visually lossless, generous headroom       Larger   Important fine detail / safety
**24**     Visually lossless for screencasts ✅       Medium   **Recommended for training video with sharp text**
**26**     Excellent; tiny text *may* soften slightly Smaller  Fine if you don't read tiny terminal text
**28+**    Visible softening begins                   Smallest Not recommended for reading material
========== ========================================== ======== ==================================================

Notes:

- **CRF is not comparable across codecs.** x265 CRF 24 ≈ x264 CRF ~21 in quality;
  the numbers don't transfer. (This guide's CRF values are all for **x265**.)
- **``-preset``** is a separate dial = how *hard the encoder works* (compression
  efficiency vs. time): ``ultrafast … medium … slow … veryslow``. **Slower preset =
  smaller file at the same CRF/quality**, just takes longer. ``slow`` is a good
  balance for a batch job.
- Why CRF 24 over 26 *here*: training video is full of **small terminal/code
  text**, the first thing to soften under compression. CRF 24 gives that text
  extra headroom for a hair more size — worth it for material you *read*.

--------------

.. _7-reading-our-real-screencast-files-worked-example:

7. Reading our real screencast files (worked example)
-----------------------------------------------------

What ``ffprobe`` told us about the course, fully interpreted:

============= ================================ ==========================================
Property      Value                            What it means
============= ================================ ==========================================
Container     **MP4**                          Standard box; we keep it
Video codec   **H.264 High**                   Old efficient codec → **upgrade to H.265**
Resolution    **1920×1080**                    1080p; **keep as-is**
Pixel format  **yuv420p**                      Standard 8-bit color; keep
Frame rate    **23.976 fps**                   (24000/1001); keep
Video bitrate **~3.0 Mbps** (1.2–4.3 range)    Old-codec bitrate; H.265 needs far less
Audio         **AAC-LC 192k stereo 48 kHz**    Fine; could trim to 128k for speech
Set total     **82 files · 14.54 GB · 11.5 h** 
============= ================================ ==========================================

**Measured test** (2-min sample, one file, x265 CRF 26):

========= ========= =============
\         Source    H.265 CRF 26
========= ========= =============
Bitrate   3.26 Mbps **0.53 Mbps**
Reduction —         **84%**
========= ========= =============

Projected whole-set result: **~3–5 GB** (down from 14.5 GB) at **CRF 24**, with
no visible quality loss — a **65–80% reduction**.

   ⚠️ **Corrupt-file note:** one file (``24. Configure Browser Security\4. Digital Certificates.mp4``) reports **"moov atom not found"** — the download finished
   incomplete. The ``moov atom`` is the MP4's index/table-of-contents; without it
   the file won't play or re-encode. Usually **unrecoverable → re-download that
   one lesson.**

--------------

.. _8-the-recommended-command:

8. The recommended command
--------------------------

Single file:

.. code:: bash

   ffmpeg -i "input.mp4" \
     -c:v libx265 -crf 24 -preset slow \
     -c:a aac -b:a 128k \
     "output.mp4"

- ``-c:v libx265`` — encode video with H.265.
- ``-crf 24`` — visually-lossless quality for screencasts with sharp text.
- ``-preset slow`` — good compression-vs-time balance.
- ``-c:a aac -b:a 128k`` — re-encode audio to 128 kbps AAC (plenty for speech).
- Keeps resolution, frame rate, and pixel format unchanged.

**Verify after encoding** (durations should match within ~1 second):

.. code:: bash

   ffprobe -v error -show_entries format=duration -of csv=p=0 "input.mp4"
   ffprobe -v error -show_entries format=duration -of csv=p=0 "output.mp4"

**Workflow:** convert in small batches (e.g. 5 files at a time), spot-check the
output quality, then continue — so a wrong setting is caught early, not after
11 hours of encoding.

--------------

.. _8b-case-study-choosing-the-encoder-with-vmaf-real-measured-run:

8B. Case study: choosing the encoder with VMAF (real measured run)
------------------------------------------------------------------

This is the decision we actually faced on the 206-file screencast course, and how we
settled it with numbers instead of guesswork. It doubles as a **template for
measuring encode quality objectively** — reuse it whenever you must justify a
codec/setting choice.

The situation
~~~~~~~~~~~~~

- ~28 hours of 1080p H.264 screen-recording to re-encode to H.265.
- **CPU x265** gives the best quality-per-byte but is slow on this machine
  (~0.3–0.6× realtime → **days**).
- An **NVIDIA GTX 1050 Ti** was present but **busy** (99% used by another task) —
  off-limits.
- An **Intel HD 630 iGPU** sat idle, and ffmpeg had **``hevc_qsv``** (Quick Sync
  hardware HEVC) available — separate silicon, wouldn't touch CPU or NVIDIA.
- The rule from the owner: **don't lose quality (don't waste the content); among
  options that hold quality, pick the smallest file.**

To decide objectively we needed a **quality number**, not opinions — so we used
**VMAF** (Netflix's perceptual metric; ~95+ ≈ visually transparent, but see the
caveat below).

How we measured it (reusable method)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The trick to a *trustworthy* VMAF number is **frame-perfect alignment** between
the encoded clip and the reference. Comparing a re-encode against the original
file directly is fragile — input-seek (``-ss`` before ``-i``) snaps to keyframes, so
the two can drift by a few frames and tank the score (you'll see ``VMAF min = 0``
on misaligned frames). The clean recipe:

.. code:: bash

   # 1) Extract a short, LOSSLESS reference segment (ffv1). Encoding FROM this
   #    guarantees the distorted and reference clips share identical frame timing.
   ffmpeg -ss 180 -t 30 -i source.mp4 -an -c:v ffv1 -level 3 ref.mkv

   # 2) Encode that reference with each candidate setting, e.g.:
   ffmpeg -i ref.mkv -c:v libx265   -crf 24 -preset medium    -an x265_med.mp4
   ffmpeg -i ref.mkv -c:v hevc_qsv  -global_quality 24 -preset veryslow -an qsv.mp4

   # 3) Score each encode vs the lossless reference. Read VMAF straight from
   #    stderr (no log file -> avoids Windows path-escaping headaches in the filtergraph):
   ffmpeg -i x265_med.mp4 -i ref.mkv -lavfi "[0:v][1:v]libvmaf=n_threads=8" -f null -
   #    => "[Parsed_libvmaf_0 ...] VMAF score: 92.07"

..

   **Two gotchas we hit, so you don't:** (a) libvmaf's ``log_path`` option chokes on
   a Windows ``C:\…`` path inside the ``-lavfi`` string (the ``:`` is a filter-option
   separator) — reading the score from stderr sidesteps it entirely. (b) On
   Windows, PowerShell's ``Set-Location`` does **not** change the working directory
   that a child ``ffmpeg`` inherits, so a *relative* ``log_path`` lands in the wrong
   folder. Use absolute paths and read stderr.

The results (30 s frame-aligned clip; VMAF vs lossless reference)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

============================ ===== =========== ================== =============================================
Method                       VMAF  Size        Speed              Notes
============================ ===== =========== ================== =============================================
**Intel QSV** veryslow, GQ24 91.82 2.43 MB     **1.35× realtime** Runs on idle Intel iGPU — frees CPU + NVIDIA
**x265 medium** CRF24        92.07 **2.20 MB** 0.62×              Smallest file; full CPU
x265 slow CRF24              92.31 2.51 MB     0.31×              Bigger *and* slower than medium — no win here
x265 medium CRF20            92.54 3.71 MB     0.58×              +69% size for +0.5 VMAF — wasteful, rejected
============================ ===== =========== ================== =============================================

Key findings
~~~~~~~~~~~~

1. **Quality was effectively identical across all of them** — within **0.7 VMAF**
   (91.8–92.5). None "wastes" the content; the difference is imperceptible.
2. **CRF 24 was the right quality level.** Dropping to CRF 20 added **69% size for
   half a VMAF point** — proof we were on a *plateau* where extra bitrate buys
   nothing visible. The "smaller is better" rule kills CRF 20. (This plateau is
   the practical meaning of "visually transparent": once more bits stop moving the
   needle, you're done.)
3. **``slow`` lost to ``medium`` here** — it produced a *bigger* file at the same
   quality on this content, so the extra encode time bought nothing. Always
   measure; preset folklore ("slower = always better") isn't a law.
4. So the real choice was just **x265 medium** (smallest, slower, full CPU) vs
   **Intel QSV** (~10% bigger, but **2× faster**, on the idle iGPU, leaving CPU +
   NVIDIA free).

The decision
~~~~~~~~~~~~

We chose **Intel QSV** (``hevc_qsv -preset veryslow -global_quality 24``): quality
within 0.25 VMAF of the best, file size within ~10% of the smallest, but **twice
as fast** and entirely on otherwise-idle hardware — so the owner's GPU task and
CPU stayed free. When hardware is idle and the quality gap is imperceptible, the
practical win (speed + freed resources) outweighs a 10% size difference. Had the
iGPU been absent or the quality gap real, x265 medium would have won.

Verifying the hardware encoder is *actually* being used
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After choosing a hardware encoder, **confirm it's really running on the GPU and
not silently falling back to software** — a fallback would quietly cost you the
speed you switched for. This turned out to be non-obvious on the Intel HD 630,
because the usual GPU meter lies.

**The trap:** Task Manager → GPU → **Video Encode** graph, and the matching
performance counter, **both read 0%** on this iGPU *even while QSV is encoding*.
On the older Intel **oneVPL/MFX media path**, the fixed-function HEVC encoder
isn't reliably attributed to the process in Windows' WDDM "GPU Engine" accounting.
The engine is working; Windows just doesn't surface that path. (The same counters
*do* correctly show NVIDIA's ``cuda``/``nvenc`` engines — it's specifically this Intel
QSV path that under-reports.) So **a flat Video Encode graph is not proof of
anything** on this hardware.

**The two reliable proofs instead:**

1. **Ask ffmpeg directly** — run with ``-v verbose`` and read the one-time startup line:

   .. code:: bash

      ffmpeg -v verbose -i in.mp4 -c:v hevc_qsv -global_quality 24 out.mp4
      # look for:
      #   Initialized an internal MFX session using HARDWARE accelerated implementation

   If it instead says *software implementation*, QSV failed to get the GPU and
   fell back — fix the driver/device before committing to a long run.

2. **Watch the CPU** — a hardware encode leaves ``ffmpeg.exe`` at **~0% CPU** while
   the output file grows steadily. A software encode pegs several cores. In our
   run, ffmpeg sat at ~0% CPU writing ~1.9 MB/s — unmistakably offloaded.

+----------------------------------------------------------------------------+------------------------------------+-------------------------------------------------------------------------------+
| How to check                                                               | Reliable on HD 630?                | What to look for                                                              |
+============================================================================+====================================+===============================================================================+
| ffmpeg ``-v verbose`` startup line                                         | ✅ best                            | "hardware accelerated implementation"                                         |
+----------------------------------------------------------------------------+------------------------------------+-------------------------------------------------------------------------------+
| ``ffmpeg.exe`` CPU % (Task Manager → Details)                              | ✅ best                            | ~0% while output grows                                                        |
+----------------------------------------------------------------------------+------------------------------------+-------------------------------------------------------------------------------+
| Task Manager → GPU → *Video Encode* graph                                  | ⚠️ unreliable here                 | may stay flat though working                                                  |
+----------------------------------------------------------------------------+------------------------------------+-------------------------------------------------------------------------------+
| ``Get-Counter '\GPU Engine(*engtype_VideoEncode)\Utilization Percentage'`` | ⚠️ reads 0 for this QSV path       | works for NVENC, not HD 630 QSV                                               |
+----------------------------------------------------------------------------+------------------------------------+-------------------------------------------------------------------------------+
| GPU-Z "Video Engine Load" sensor                                           | ✅ **confirmed working on HD 630** | third-party, live gauge — reads the driver's own sensors, so it sees the QSV  |
|                                                                            |                                    | media engine that Windows' per-process counters miss                          |
+----------------------------------------------------------------------------+------------------------------------+-------------------------------------------------------------------------------+

..

   **Why GPU-Z works when Task Manager doesn't:** GPU-Z polls the GPU driver's
   **hardware sensors** directly (engine clocks, per-engine load), rather than
   relying on Windows' WDDM per-process accounting. On this machine, with QSV
   encoding, Task Manager's Video Encode graph stayed flat while **GPU-Z showed the
   Intel GPU loaded** — a clean demonstration that the fixed-function encoder was
   busy and the OS-level counter was simply blind to it. When in doubt, a
   sensor-reading tool (GPU-Z, HWiNFO) beats the OS utilization graph.

   **Rule of thumb:** trust the **encoder's own log** and the **CPU draw**, not the
   GPU utilization graph. "Output is growing while CPU stays near zero" is the
   clearest sign a fixed-function hardware encoder is doing the work — regardless
   of what the GPU meter claims. The principle generalizes: NVENC, AMD AMF, and
   Apple VideoToolbox can all be confirmed the same way (verbose log + low CPU),
   since per-process GPU-encode accounting is inconsistent across vendors and OS
   versions.

..

   **VMAF caveat for screen content:** VMAF was trained on natural video, and it
   tends to *under-rate* screen recordings with sharp text/line art — so ~92 here
   corresponds to "visually transparent in practice," not "visibly flawed." For
   text-heavy material, always confirm with your own eyes on a couple of clips, not
   the score alone. (For a dedicated screen-content metric, see the roadmap's
   note on quality measurement in Appendix D.)

--------------

.. _8c-reading-a-benchmark-table-vmaf-global_quality-and-the-quality-ladder:

8C. Reading a benchmark table: VMAF, global_quality, and the quality ladder
---------------------------------------------------------------------------

When you run a quality comparison, you get a small table like the one below.
Every column and abbreviation in it matters, because this is the table you read
to *choose a setting*. This is a real example from a hard piece of camera
footage (an Arduino tutorial — talking head plus close-up hardware demo), where
the easy default turned out **not** to be good enough and we had to read the
numbers carefully.

::

   ┌─────────────┬───────┬────────────┐
   │   Setting   │ VMAF  │ Size (30s) │
   ├─────────────┼───────┼────────────┤
   │ qsv GQ20    │ 91.85 │ 9.28 MB    │
   │ qsv GQ22    │ 91.29 │ 7.30 MB    │
   │ qsv GQ24    │ 90.35 │ 5.76 MB    │
   │ nvenc (ref) │ 90.46 │ 16.37 MB   │
   └─────────────┴───────┴────────────┘

The columns
~~~~~~~~~~~

- **Setting** — the encoder plus its quality knob being tested. Every row here
  produces **H.265 (HEVC)** video; they differ only in *how* (which encoder) and
  at *what quality target*.
- **VMAF** — **Video Multi-method Assessment Fusion**, a perceptual quality
  score (0–100) developed by Netflix. It compares the *encoded* clip against the
  *original* and estimates how close to the original a human would judge it.

  - Higher = better.
  - ~95+ = "visually transparent" for normal camera video (you can't tell it
    from the source).
  - For screen/text content it reads a few points lower than perception, so ~92
    there is already transparent.
  - The number is measured against a **lossless reference of a 30-second
    sample**, so every row is scored on the exact same footage, frame-for-frame
    — that is what makes the comparison fair.

- **Size (30s)** — how many megabytes that setting produced for the same
  30-second sample. It is a 30s slice, not the whole file, so the numbers are
  small and purely for *comparison* — lower = smaller files when applied to the
  full video.

The abbreviations in the "Setting" column
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **qsv** = **Quick Sync Video** — Intel's *hardware* video encoder built into
  the iGPU (e.g. the Intel HD 630). It does the H.265 encoding on dedicated
  silicon, leaving the CPU and any NVIDIA card free.
- **GQ** = **global_quality** — QSV's quality dial (its equivalent of CRF). It
  works **backwards**, like CRF:

  - Lower GQ number = higher quality = bigger file.
  - So GQ20 is higher quality than GQ22, which is higher than GQ24.
  - The numbers are **not** comparable to CRF or to other encoders' numbers —
    only within QSV.

- **nvenc** = **NVIDIA's hardware encoder**. **"(ref)"** = reference row —
  included only for comparison, not a candidate (here the card was busy with
  another task, and as the table shows, it is inefficient for this job).

What the table is actually telling us
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read it as a **quality ladder for QSV**, with nvenc as a yardstick:

======== ===== ======== ==========================================
Setting  VMAF  Size     Reading
======== ===== ======== ==========================================
qsv GQ20 91.85 9.28 MB  highest quality, biggest
qsv GQ22 91.29 7.30 MB  slightly less quality, 21% smaller
qsv GQ24 90.35 5.76 MB  smallest, but quality dips toward the edge
nvenc    90.46 16.37 MB same quality as GQ24 but ~3× bigger
======== ===== ======== ==========================================

Three conclusions we drew from it:

1. **nvenc is wasteful here** — it needs 16.37 MB to reach VMAF 90.46, while qsv
   GQ24 reaches the *same* quality (90.35) in 5.76 MB. So nvenc was correctly
   rejected. (NVENC on older GPUs is bitrate-inefficient at these settings; it
   buys speed, not size.)
2. **GQ20 → GQ22 is nearly free quality-wise** — going from GQ22 to GQ20 buys
   only **+0.56 VMAF** (imperceptible) but costs **+27% size** (9.28 vs 7.30).
   That is the "wasteful" trade to avoid → GQ20 rejected.
3. **GQ24 is on the edge** — on this (middle) sample it is 90.35, but on a harder
   scene sampled elsewhere in the same file it dropped to **88.10**. GQ22's extra
   headroom keeps even hard scenes safely ~91, so it stays transparent
   everywhere.

→ **GQ22 is the sweet spot: transparent with margin, small, and still on the
fast idle iGPU.**

   **The lesson for harder footage.** The easy screencast default (QSV at GQ24,
   see §8B) was *not* good enough for real camera footage — its quality dipped
   below transparent on hard scenes, and a naive "pick whatever clears the bar"
   rule could even flip the choice to the bloated nvenc row. Bumping the QSV
   quality one notch (GQ24 → GQ22) fixed it without giving up the hardware-speed
   win. The general principle: **match the quality target to the content** —
   static slides tolerate a more aggressive setting than detailed, moving camera
   footage. Always benchmark on a *representative, hard* sample, not just an easy
   one, and ideally sample more than one scene because VMAF varies scene to scene
   within a single file.

The three ideas under this whole table — *VMAF as a transparency score*,
*GQ/CRF running backwards*, and *reading a ladder to find the knee where more
bits stop buying visible quality* — are the entire basis for choosing an encode
setting. Everything else is detail.

--------------

.. _8d-when-a-file-wont-shrink-size--bitrate--duration:

8D. When a file won't shrink: Size ≈ bitrate × duration
-------------------------------------------------------

Sometimes a re-encode barely shrinks a file — or even makes it bigger (which is
why slimv has ``--keep-smaller``). When that happens, this case study is the lens
to understand why, and what your real options are. It comes from the Arduino
YouTube set, where two files stood out as much larger than the rest.

   **🔴 RULE — never judge "will it shrink?" by bitrate alone. Always benchmark a sample.**
   Bitrate measures *size*, not *compressibility*. What decides how much HEVC can reclaim is
   **content type**: *static* screen (schematic, console, code editor, slides, handwriting)
   compresses enormously even at a **low** bitrate, while *motion* (3D orbit/render, live camera,
   livestream, packet-capture scroll) barely compresses even at a **high** one. Real proof from
   our batches: **a firewall-console course at 0.99 Mbps → 72% saved**, but a **3D-CAD screencast at ~1.0 Mbps → grew 94%**;
   **a 3D-animation course at 2.2 Mbps** *looked* like a motion dud yet hit **60%**. Same numbers, opposite
   results — so extract a 60–180 s mid-file sample, encode it at your target quality, and decide by
   the **measured saved %**. The only safe bitrate-only skip is a **verified duplicate** you already
   hold. (Evidence table + method: ledger → "RULE — never skip on bitrate alone".)

Why the big files were big: they're long, not bloated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

=========== ======= ======== ========= =======
File        Size    Duration Bitrate   Res
=========== ======= ======== ========= =======
Tutorial 51 1.05 GB 57 min   2.55 Mbps 1080p30
Tutorial 59 1.38 GB 80 min   2.42 Mbps 1080p30
=========== ======= ======== ========= =======

The governing relationship is:

   **Size ≈ bitrate × duration.**

A file's size is just how many bits per second it spends, times how many seconds
it runs. These two are not high-bitrate — 2.5 Mbps for 1080p is already lean —
they are simply **long** (57 and 80 minutes). There is no "fat" to trim
losslessly, which is exactly why a transparent-quality re-encode (QSV GQ22) only
shaves ~15–20% off them: the source was already close to as small as 1080p at
that quality gets.

This is the general case for **already-compressed** video (anything off YouTube,
streaming, or a previous sensible encode): the bitrate is already near the
quality target, so re-encoding at the *same* quality and resolution cannot find
much to remove. Contrast the screencast course (§8B) — those were ~3 Mbps of
*mostly static slides*, hugely over-budget for their content, so H.265 cut 64%.
Content, bitrate, and duration together decide how much room there is.

The honest rule
~~~~~~~~~~~~~~~

   For **already-compressed, moderate-bitrate, long** video, you **cannot** get a
   big size reduction while keeping *both* full resolution *and* full quality.
   Something has to give.

Your levers, least to most impactful:

================================= ============== =========================== ============================
Lever                             Size effect    Cost                        Verdict (for tutorials)
================================= ============== =========================== ============================
Audio bitrate trim                tiny (~50 MB)  none audible                free, minor
Quality target (lower, e.g. GQ26) modest more    slight quality loss         against a quality-first rule
**Downscale 1080p → 720p**        **~halves it** softer if viewed fullscreen **the big, reliable lever**
Drop frame rate                   none here      —                           already 30fps, no gain
Trim dead air / intros            varies         editing, not encoding       manual
================================= ============== =========================== ============================

Walking the ``Size ≈ bitrate × duration`` equation tells you which lever can move a
given file:

- **Duration** is fixed (it's the content — you can't cut it without editing).
- **Bitrate** is the product of *resolution × quality × content complexity*. With
  quality held (transparent) and content fixed, the only remaining knob is
  **resolution**.

So **the one lever that actually moves a long 1080p file is resolution.**
Dropping 1080p → 720p cuts the pixel count to ~44%, which roughly **halves** the
file. For instructional video (talking head plus hardware/screen close-ups,
usually watched in a window rather than on a 4K TV) 720p is often visually fine —
the thing to check is whether on-screen **text/code** stays readable, since that
is what suffers first when you scale down.

Practical takeaway
~~~~~~~~~~~~~~~~~~

When a file resists shrinking, don't fight the encoder — read the equation:

1. Is it big because of **high bitrate** (over-budget for its content)? → a
   transparent re-encode will shrink it well; you're done.
2. Is it big because of **long duration at a sane bitrate**? → re-encoding won't
   help much; your real choice is **downscale resolution** (720p/480p) or accept
   the size. (slimv's resolution-scaling profiles, e.g. ``qsv-720p``, exist for
   exactly this.)
3. Either way, keep ``--keep-smaller`` on so an unhelpful re-encode never makes
   things worse.

--------------

.. _8e-what-determines-encode-speed:

8E. What determines encode speed
--------------------------------

If §8D is the back-of-the-envelope rule for *file size*, this is its twin for
*encode time* — how fast a given encoder churns through your footage, and why the
same chip and the same profile can run at very different speeds on two different
sets. The real example: with the **same hardware encoder (Intel Quick Sync) and
nearly the same profile**, one course encoded at **~1.0–1.4× realtime** and
another at **~1.9× realtime**. The difference was almost entirely the source
**resolution**.

The dominant factor: resolution (the pixel math)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A hardware encoder's media engine has a roughly **fixed throughput in pixels per
second**. So speed scales with how many pixels are in each frame:

========== ============ =============
Resolution Pixels/frame Relative work
========== ============ =============
4K / 2160p 8,294,400    4.0×
1080p      2,073,600    1.0×
**720p**   **921,600**  **0.44×**
480p       ~409,920     ~0.20×
========== ============ =============

720p is only **~44% of the pixels** of 1080p, so at the same frame rate the
engine gets through frames roughly **2.25× faster**. That is exactly why the 720p
course ran ~1.9× while the 1080p one ran ~1.0–1.4× — the numbers line up. (It is
not quite the full 2.25× because there is fixed per-frame overhead, and the
encoder does more than just push pixels.) The same logic in reverse: feed it 4K
and it runs ~4× *slower* than 1080p.

The secondary factors (smaller effect)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Content complexity** — static lectures (a presenter, slides, slow
  handwriting) encode faster than busy camera footage with lots of motion and
  detail: lighter motion-estimation and mode decisions. Even a fixed-function
  encoder finishes simple scenes quicker.
- **Quality target** — a higher quality (lower CRF / global_quality) is a touch
  more work than a lower one. Minor on hardware.
- **Preset / effort** — slower presets (x265 ``slow``/``veryslow``; QSV ``veryslow``)
  search harder and run slower for smaller files. This is the dial you trade
  *time* for *compression* with (see §6).
- **System contention** — even with a hardware encoder, the **decode** side of a
  transcode runs on the CPU (the source must be decoded before re-encoding), so a
  busy machine encodes slower.
- **CPU vs hardware encoder** — a CPU encoder (x265) is far more sensitive to
  resolution and preset than a fixed-function hardware encoder, and is typically
  several times slower at the same quality (that is the whole reason to use Quick
  Sync — see §8B).

The rule of thumb
~~~~~~~~~~~~~~~~~

   **Encode time ≈ pixels-per-frame × frame-count ÷ engine-throughput.**

Resolution first, then motion/complexity, then your quality target and preset.
It is the encode-time twin of ``Size ≈ bitrate × duration`` (§8D): one predicts how
*big* the result is, the other how *long* it takes to make. Together they let you
estimate a whole job before you start it — e.g. "12 hours of 720p at ~1.9× ≈ 6–7
hours of encoding, landing near 4 GB."

--------------

.. _8f-a-bad-encoding-case-study-over-bitrating-static-content-88-wasted:

8F. A bad-encoding case study: over-bitrating static content (88% wasted)
-------------------------------------------------------------------------

§8D was *"some files barely shrink."* This is the **opposite and far more common**
mistake: a file that shrinks **enormously** because the original was wildly
over-bitrated. It's worth dwelling on, because it's a mistake people make every day
when **producing** video — and once you see it you can avoid it.

The case
~~~~~~~~

A 273-video **machine-learning course** — slides, a
talking head, screen-shared code, and handwritten equations. Source: **720p H.264,
59.53 GB**, averaging **~3–5 Mbps** (some lectures ~9.85 Mbps). Re-encoded to H.265
(``qsv-hq``, global_quality 22):

===================== ======== ====== ===========================
\                     Source   Output Ratio
===================== ======== ====== ===========================
Whole course          59.53 GB ~7 GB  **~8.6 : 1 (≈88% smaller)**
High-bitrate lectures —        —      90–93% smaller
Light intro clip      19 MB    14 MB  barely moved
===================== ======== ====== ===========================

And the quality held: VMAF measured **~91.8 vs a lossless reference on the hardest
content** (handwriting/equations) — transparent in practice. We watched the early
outputs; they look great. **The 88% that left was waste, not detail.**

.. _why-it-was-so-wasteful--three-things-stacked:

Why it was so wasteful — three things stacked
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **The bitrate was sized for motion video, but the content barely moves.** A slide
   sitting still for 30 seconds, or a talking head, has almost no change between
   frames. Paying 4 Mbps for that is like mailing an empty box in a freight
   container. (This is the transmitter-era lesson too: you allocate channel bandwidth
   to the *information* in the signal — a still test card needs almost none.)

2. **Static content is absurdly compressible — and the original encoder didn't
   exploit it.** Codecs store *differences* between frames (the I/P/B story, §12).
   When nothing moves, P- and B-frames cost almost nothing. The re-encode's own x265
   stats make it vivid:

   ::

      frame I:  Avg QP 21.5   kb/s 10754   ← full pictures: expensive, but rare
      frame P:  Avg QP 26.4   kb/s  1184   ← changes from before: cheap
      frame B:  Avg QP 30.1   kb/s   134   ← the bulk of frames — almost free

   The B-frames — most of the video — ride at **~134 kb/s**. The source was charging
   thousands of kb/s for those same near-identical frames. The bits had nowhere
   useful to go; they encoded *noise and redundancy*.

3. **A quality target beats a fixed bitrate.** The source looks like it used a roughly
   **constant high bitrate** regardless of scene complexity (the same fat rate for a
   static slide as for the busiest frame). Re-encoding with **CRF / global_quality**
   (a *quality* target) spends bits only where the eye needs them — so the static
   majority collapses while the hard frames still get what they need. H.264→H.265
   (§5, ~30–50%) then compounds the win.

Why this beat the math courses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Great Courses math shelf was 720p at **~2 Mbps** (already fairly lean) → ~50–60%
saved. This course was \**~3–5 Mbps for similarly static content*\* → ~88%. The rule:

   **The fatter and more static the source, the bigger the safe gain.** Over-bitrated
   low-motion video is the single most reclaimable kind of file there is.

How to avoid this when *creating* video
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're the one encoding (lectures, screencasts, tutorials, conference talks):

- **Encode by quality, not a fixed bitrate.** Use **CRF** (x264/x265) or
  **global_quality** (QSV), not a flat high CBR. Let the encoder spend bits on motion
  and save them on stillness. Good starting points for *screen/slide* content:
  **x264 CRF ~20–23**, **x265 CRF ~23–26** — then check by eye.
- **Match the codec to the job.** Ship in **H.265 or AV1** for anything
  bandwidth-sensitive; H.264 only when you need maximum device compatibility.
- **Don't over-resolve or over-frame-rate.** Slides don't need 60 fps — **30 (or even
  24)** is plenty, and **720p** is fine for screen-share/talking-head. Both multiply
  into bitrate (``Size ≈ bitrate × duration``, §8D).
- **Use longer GOPs / let scene-cut detection work** for static content — a held slide
  should be one keyframe plus cheap deltas, not frequent full refreshes.
- **Two-pass only buys you accuracy at a target size** — if you don't *need* a size
  target, CRF is simpler and usually better.
- **Verify before you ship:** a quick **VMAF** check (§8B) against the source tells you
  if you've gone too low; for screen/text content ~92+ is effectively transparent.

Do these and your *source* lands near where our *re-encode* did — and nobody has to
reclaim 88% of it later.

--------------

.. _8g-when-an-encode-suddenly-fails-its-usually-memory-commit-not-free-ram:

8G. When an encode suddenly fails: it's usually memory *commit*, not free RAM
-----------------------------------------------------------------------------

A batch that ran perfectly for dozens of files can suddenly start failing **every**
file. This section is the field guide to why — because the obvious diagnosis ("I have
free RAM, so it's not memory") is the wrong one, and it cost real time to untangle.

The symptom
~~~~~~~~~~~

A hardware (QSV) encode is humming along, then:

::

   [hevc_qsv] Error submitting video frame to the encoder
   [hevc_qsv] Error encoding a frame: Invalid data found when processing input

…on file after file — a **cascade**, where before it was fine. And if you try to launch
anything, you may see the tell-tale:

::

   The paging file is too small for this operation to complete.

The trap: "free RAM" is the wrong gauge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check free physical RAM and it may look fine — several GB free. So you conclude it's not
memory and go hunting for a GPU/driver fault. **Wrong metric.** Windows (and every OS)
limits not just *resident* memory but **committed** memory.

The real gauge: commit charge vs commit limit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Commit limit** = physical RAM **+** the page file. On a 32 GB box with a 32 GB page
  file, that's a **64 GB** ceiling on *promised* memory.
- **Commit charge** = the total memory all processes have *reserved* (committed),
  whether or not it's currently resident in RAM.

When **commit charge nears the commit limit**, the next allocation fails — **even with
physical RAM free** — because the OS won't promise memory it couldn't back with RAM+page
file. That's precisely what "paging file too small" means: not "the file is undersized"
so much as "committed memory has hit the ceiling."

A real reading from the failure:

::

   Commit limit:  63.9 GB   (32 GB RAM + 32 GB page file)
   Committed:     62.5 GB
   Free commit:    1.4 GB   ← the actual problem
   Free RAM:       7.2 GB   ← the red herring

7 GB of RAM was free, but only **1.4 GB of commit** remained — and a 1080p QSV encode
needs to *commit* a couple of GB for its frame buffers/surfaces. It couldn't, so frame
submission failed on every file.

Why a *hardware* encoder is the first casualty
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QSV allocates GPU-visible surface memory up front for its pipeline. Under commit
starvation those allocations are the ones that fail — hence the ``Error submitting video frame`` / ``Invalid data`` cascade. It looks like a codec or driver fault; it's actually the
encoder being denied memory it's allowed to *ask* for.

Who's really eating the commit (not who you'd guess)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The culprits are rarely the obvious "heavy" app. In the real case:

- **Web browsers dominate** — Chrome across ~80 helper processes and Firefox across ~20
  had committed \**~25 GB between them*\*. Browsers commit far more than their *resident*
  footprint suggests.
- A background **transcription job** (ML model) held several GB.
- The **VMs everyone suspected first were tiny** (~1.7 GB total) — a complete red herring.

**Lesson: rank by commit, not by resident RAM or by which app "feels" heavy.**

How to diagnose (the commands that matter)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Commit limit / free commit (PowerShell):
  ``Get-CimInstance Win32_OperatingSystem | select FreeVirtualMemory, TotalVirtualMemory``
  (these are *virtual* = commit, in KB), or watch **Task Manager → Performance → Memory →
  "Committed 62.5/63.9 GB"**, or **Resource Monitor → Memory → "Commit Charge."**
- Rank committers: ``Get-Process | Sort-Object PM -Descending`` (PM = pagefile/commit), or
  ``Win32_Process``'s ``PrivatePageCount``. Do **not** rank by working set (resident) — that
  hides browser commit.

The fix
~~~~~~~

1. **Free commit** — close browser windows/tabs and any big background job. This is the
   fastest lever; closing most of a browser can return 10+ GB of commit instantly.
2. **Raise the page file** — if commit is chronically tight, increase the page file size
   (System → Advanced → Performance → Virtual memory). A bigger page file raises the
   commit *limit* so encodes fit even under load. (System change; a reboot may apply it.)
3. **Reboot** — frees all commit and resets driver state; the heaviest option.

Why this isn't a disaster
~~~~~~~~~~~~~~~~~~~~~~~~~

A good batch encoder is **resumable**. slimv logs each file and skips completed ones on
re-run, so the moment you free commit you just restart the job: the done files are kept,
and the failed ones re-encode on a now-healthy engine. No progress is lost — the failures
were the environment starving the encoder, not damage to any file.

   **One-line takeaway:** if a hardware encode starts failing every file — especially with
   *"paging file too small"* — check **commit charge**, not free RAM, and free commit
   (usually by closing browsers) before blaming the GPU.

--------------

.. _8h-moving-decode-to-the-gpu-freeing-the-cpu-and-why-it-doesnt-speed-things-up:

8H. Moving decode to the GPU: freeing the CPU (and why it doesn't speed things up)
----------------------------------------------------------------------------------

A hardware (QSV) encode has **two** stages, and by default they run on **different**
engines:

::

   source .mp4  ──►  DECODE (H.264 → raw frames)  ──►  ENCODE (raw → H.265)  ──►  output
                     ↑ CPU (software), by default        ↑ iGPU (hardware, hevc_qsv)

So even a "hardware" encode is quietly using the **CPU** — for the *decode* half. On a
busy machine (say a transcription job running alongside), that CPU decode competes with
your other work. The obvious idea: move the decode onto the iGPU too, so the CPU is free.
slimv does this with ``--hwdec qsv``. But the results teach two non-obvious lessons.

.. _lesson-1--gpu-decode-frees-the-cpu-but-does-not-speed-up-the-encode:

Lesson 1 — GPU decode frees the CPU, but does **not** speed up the encode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measured on a real 1080p job, decoding the same 60 s on the CPU vs. on the iGPU:

============================ ========================
Decode on…                   Encode time (60 s clip)
============================ ========================
CPU (software)               119.5 s
**iGPU** (full GPU pipeline) 118.4 s — **~0% faster**
============================ ========================

Why no speedup? Because decode and encode run as a **pipeline** — the decoder feeds the
encoder *while* the encoder works; they overlap. Throughput is set by the **slower**
stage, and here that's the **encoder** (QSV at ``-preset veryslow``), not the decode. Moving
the *faster*, non-bottleneck stage (decode) to a different engine doesn't change the
bottleneck — it's a mild case of Amdahl's law. What it **does** do is take the *decode*
off the CPU. Measured, the main ffmpeg process dropped from **~100% of a CPU core to
~47%** — because the heavy H.264 software decode moved to the iGPU, while **demux, AAC
audio encoding, and frame-feeding stay on the CPU**. So it's not literally idle, but the
CPU is **roughly half freed** — enough to keep a parallel transcription job running
comfortably. **That** was the real goal, and it worked; the speed was never going to come
from here.

.. _what-still-runs-on-the-cpu--and-why-it-cant-move-to-the-igpu:

What still runs on the CPU — and why it can't move to the iGPU
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Even with ``--hwdec``, a transcode still uses ~half a core. That's **not** the video decode
(that's on the iGPU now) — it's the stages the iGPU's media block *cannot* do:

================ ======================================================== ============================================
Stage            What it does                                             Where it can run
================ ======================================================== ============================================
**Demux**        Parse the ``.mp4``/``.mkv`` container, split out packets **CPU only** — no GPU parses containers
**Decode**       compressed packets → raw frames                          iGPU ✅ (what ``--hwdec`` moved)
**Encode**       raw frames → H.265                                       iGPU ✅ (``hevc_qsv``)
**Audio encode** audio → AAC                                              **CPU only** — the iGPU has no audio encoder
**Mux / feed**   interleave output, feed frames GPU↔CPU                   CPU (light)
================ ======================================================== ============================================

The iGPU's fixed-function media block does exactly two jobs — **video decode and video
encode.** Demuxing (container parsing) and audio encoding are *not* video-engine work and
have **no GPU path in any encoder** — so that floor is irreducible. There is no "GPU
demux" to turn on.

**But one part of that floor is often pure waste: re-encoding audio that's already fine.**
By default slimv re-encodes audio to AAC 128k for universality (so an MP3/AC3/PCM source
comes out consistent). But when the **source audio is already AAC at a sane bitrate** —
e.g. many such courses ship **AAC 128k**, exactly the target — re-encoding it to AAC 128k
buys **nothing**: same format, same bitrate, and it *loses* a little quality (audio
re-encode is lossy, so AAC→AAC is a needless extra generation) while spending CPU. The fix
is to **stream-copy** the audio (``slimv encode … --copy-audio``, i.e. ffmpeg ``-c:a copy``):
byte-identical audio out, zero CPU for audio, no quality loss. Demux still stays on the CPU
(it must), but that's tiny. **Rule of thumb: re-encode audio only to change it (different
codec, or lower bitrate); if it's already what you want, copy it.**

.. _can-demux-run-on-a-gpu-nvidia-or-any-no--and-heres-why:

Can demux run on a GPU (NVIDIA, or any)? No — and here's why
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A natural follow-up: if decode and encode moved to the iGPU, why not **demux** too — maybe
on the NVIDIA card? The answer is that **demux is a CPU task by nature; no GPU (NVIDIA
included) can meaningfully do it.** The *why* is more interesting than "just because."

**What demux actually is.** Demuxing = **parsing the container** (``.mp4``/``.mkv``): read the
file, walk the box/atom (or EBML) tree, follow byte offsets in the index (``moov``/``cues``),
pull out the compressed packets, read their timestamps, and interleave streams. It's
**serial, branch-heavy, pointer-chasing control flow, and I/O-bound** — you must read box N
to even know where box N+1 begins. (The exact structures — MP4 boxes/atoms, MKV EBML
elements, AVI RIFF chunks — are dissected in §11.)

**Why that's the opposite of what a GPU is good at.** A GPU is a **SIMD / throughput**
machine — thousands of cores doing the **same** math on **parallel** data (pixel blocks,
matrices). Demux has:

- **No data parallelism** — it's inherently sequential (you can't parse packet 500 before
  you've parsed the header chain that leads to it).
- **Heavy branching** — variable-length fields, format quirks, conditionals everywhere.
  GPUs choke on divergent branches (a warp of cores must all take the same path or stall).
- **I/O-bound, not compute-bound** — it's mostly moving bytes with almost no arithmetic. A
  GPU offers nothing for that, and you'd have to copy the file into VRAM first — pure
  overhead for zero compute gain.

So it isn't that nobody built "GPU demux" — it's that it would be **slower** on a GPU than
on a CPU.

**The hardware reality (and the NVIDIA part specifically).** GPU media engines — **NVIDIA
NVDEC/NVENC** and **Intel QSV** alike — are fixed-function blocks that do **only video
decode and encode**. They take an already-**demuxed elementary bitstream** (packets / NAL
units, §12) as input; they have **no container-parsing unit at all.** So even "decode on
the NVIDIA GPU" still requires the **CPU to demux first** and feed NVDEC the packets. The
pipeline everywhere — ffmpeg, VLC, browsers, hardware players, even NVIDIA's own DALI
data-loading library — is: **CPU demux → GPU decode.** Switching from Intel QSV to NVIDIA
NVDEC would move *nothing* off the CPU for demux (and here the NVIDIA card is busy with
other work anyway).

**So the residual CPU floor is real.** That remaining ~quarter-core is **demux + moving
packets/surfaces + muxing the output** — all inherently CPU/memory work with no GPU path.
It's already about as low as it goes. The only things that trim it further are unrelated to
GPUs (faster NVMe storage cuts I/O wait; we already removed the audio-encode chunk with
``--copy-audio``).

**Bottom line:** decode and encode → GPU (done). **Demux → CPU, permanently, on any brand
of GPU.** It's an architecture mismatch (serial/branchy/I-O-bound vs. parallel-math
silicon) plus a missing hardware unit — not a feature someone forgot to ship.

.. _lesson-2--the-full-gpu-pipeline-is-finicky-on-a-constrained-igpu:

Lesson 2 — the full-GPU pipeline is finicky on a constrained iGPU
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keeping frames GPU-resident (``-hwaccel qsv -hwaccel_output_format qsv``) means the decoder
and encoder share a **fixed pool of hardware frame buffers** in iGPU memory — and an
older iGPU (Gen9) has little memory, shared with the whole system. That pool size is a
Goldilocks problem:

================================= ======================================================================================================================
Frame pool (``-extra_hw_frames``) Result
================================= ======================================================================================================================
default (8 → pool of 32)          works at ``veryslow``, but **starves** under faster presets: ``Failed to allocate a qsv/nv12 frame from a fixed pool``
**24**                            **the sweet spot — clean, no errors, faster presets OK**
64                                **GPU out-of-memory**: ``Could not create the texture (8007000e)`` — asked for more surface memory than the iGPU has
================================= ======================================================================================================================

Too few buffers and the pipeline stalls waiting for a free frame; too many and you exceed
the iGPU's slice of memory. The workable window is narrow, and it's hardware-specific — a
newer iGPU (Arc) or a discrete GPU with its own VRAM has far more headroom and rarely hits
this.

.. _lesson-3--the-speed-lever-is-the-preset-not-the-decode-location:

Lesson 3 — the speed lever is the **preset**, not the decode location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since the *encoder* is the bottleneck, that's where speed comes from. Dropping QSV from
``-preset veryslow`` to ``-preset slow`` (a lighter rate-distortion search, §5B) took the same
job from **0.46× to 1.57× real-time — ~3× faster — at near-identical size** (veryslow buys
only a few percent). Combined with ``--hwdec qsv``, the result was **both** goals at once:
**CPU-free and ~3× faster.**

One caveat: a hardware decoder is *stricter* than software
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Moving decode to the GPU has a subtle downside on **rough or slightly-corrupt files**: a
hardware decoder is less tolerant than the software one, and can **bail out earlier** at a
bad region — truncating the output — where software decode limps through. A real example:
a lecture whose source had a corrupt/rough tail. Decoded on the iGPU (``--hwdec qsv``) the
encode stopped at **873 s**; decoded in **software** it reached **939 s** — the file's true
end. So the GPU-decoded output silently lost the last ~66 s.

The tell-tale: **verify flags a length mismatch on a source that plays fine.** The fix is
to re-encode *that one file* **without ``--hwdec``** — software decode is more forgiving and
recovers the full content. (Separately, some sources carry **bogus inflated metadata** —
claiming, say, 1420 s / 42,619 frames when the video really ends at 939 s / 28,190 — and
verify can't auto-clear those, because both its reference points, source duration *and*
source frame count, are the lying metadata; confirm the output decodes clean and holds the
real frames, then accept manually.)

So ``--hwdec`` is the right default for clean sources (most of them); keep plain software
decode as the fallback for the occasional rough file.

Putting it together
~~~~~~~~~~~~~~~~~~~

- **Want the CPU free** (other work running)? → ``--hwdec qsv`` — moves decode to the iGPU.
  Doesn't speed the encode, but idles the CPU. (Needs a non-scaling profile; needs the
  frame-pool sweet spot on a small iGPU.)
- **Want it faster**? → a lighter **preset** (``slow``/``medium``), the real throughput lever.
- They're **independent knobs** — decode *location* (which engine, CPU load) vs. encoder
  *effort* (preset, speed). Set each for what you actually need.

..

   **Takeaway:** in a pipeline, optimise the **bottleneck**. Moving a non-bottleneck stage
   (decode) to another engine changes *who does the work*, not *how fast it finishes* — use
   it to free a resource (the CPU), and use the **preset** to change the speed.

--------------

.. _8i-worked-example-re-encoding-a-new-course-command-by-command:

8I. Worked example: re-encoding a new course, command by command
----------------------------------------------------------------

The complete flow for a **brand-new course**, every command shown, using a real one —
a **calculus course** *(part 1: limits and continuity)* (226 files, 42.03 GB, 720p H.264,
AAC 128k audio). The same five steps work for any library: **inspect → (test) → encode →
verify → reclaim.**

.. _step-0--the-command-were-building-toward:

Step 0 — the command we're building toward
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a screen/lecture course on this machine (Intel iGPU, and we want the CPU free), the
settings are:

::

   --profile qsv-hq     H.265 on the iGPU, global_quality 22 (crisp text; §8C)
   --hwdec qsv          decode on the iGPU too, so the CPU stays free (§8H)
   --copy-audio         source is already AAC 128k → copy it, don't re-encode (§8H)
   --keep-smaller       if a file wouldn't shrink, keep the original (§8D)

The rest of the steps justify each of those choices.

.. _step-1--inspect-what-is-this-course:

Step 1 — inspect: what is this course?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   slimv analyze "D:\Courses\Calculus 1 - Limits and Continuity"

::

   226 files · 42.03 GB · 1280x720 H.264 · median ~1.83 Mbps · audio AAC 128k

Read it: **720p H.264 at ~1.83 Mbps.** For static math/handwriting that's **over-bitrated**
(§8F) — lots of reclaimable fat, so it's a strong candidate. The audio is **already AAC
128k** — exactly what we'd re-encode *to*, so we'll ``--copy-audio`` it (§8H). H.264 → H.265
is the real win (§5).

.. _step-2--optional-prove-it-on-your-own-content:

Step 2 — (optional) prove it on your own content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Not sure of the profile or the gain? Benchmark one representative lecture — VMAF vs a
lossless reference, several profiles at once:

.. code:: bash

   slimv benchmark "D:\Courses\Calculus 1 - Limits and Continuity\12 A hard limit.mp4"

::

   Profile    VMAF    Size(MB)   Speed   HW
   qsv        94.9    1.7        1.8x    iGPU
   qsv-hq     95.7    2.2        1.8x    iGPU     <- chosen: sharp equation text
   balanced   95.6    2.3        0.7x    CPU
   quality    96.4    3.3        0.7x    CPU

All profiles are transparent (~95 VMAF); we pick **``qsv-hq``** because the content is
equation/handwriting-heavy and text sharpness is worth a few MB. (``slimv recommend`` does
this *and* prints the ready-to-run encode command.)

.. _step-3--encode-the-whole-tree:

Step 3 — encode the whole tree
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   slimv encode ^
     "D:\Courses\Calculus 1 - Limits and Continuity" ^
     "E:\Encoded\Calculus 1 - Limits and Continuity [HEVC]" ^
     --profile qsv-hq --hwdec qsv --copy-audio --keep-smaller

::

   decode on qsv (CPU-free): -hwaccel qsv -hwaccel_output_format qsv -extra_hw_frames 24
   Encoding 226 of 226 file(s) with profile 'qsv-hq' (-c:v hevc_qsv -preset veryslow -global_quality 22 -tag:v hvc1)
   [1/226] 1 - Introduction\1 -Introduction.mp4 (150.6 MB)
      -> 33.9 MB (77% smaller) [OK]
   ...

It **mirrors the source tree** under the output folder, writes a per-file
``_slimv_encode_log.csv``, and is **resumable** — stop and re-run the exact same command and
it skips everything already done. If a file transiently fails, just re-run (resume retries
it; for the rare rough file, re-run that one without ``--hwdec`` — §8H).

**Actual result on this course (measured 2026-07-18):** **42.03 GB → 9.61 GB — 77.1% smaller
(~32.4 GB reclaimed), 4.4× smaller.** All **226/226 files encoded on the first pass — 0
transient fails, 0 stragglers, 0 errors**, running ~1.6–1.9× real-time on the iGPU with the
CPU free. That's right in the series' 74–80% band and a touch above the ~75% we'd have
guessed from the ~1.83 Mbps 720p input — static equation/handwriting content is the most
reclaimable kind (§8F).

.. _step-4--verify-before-deleting-anything:

Step 4 — verify before deleting anything
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   slimv verify ^
     "D:\Courses\Calculus 1 - Limits and Continuity" ^
     "E:\Encoded\Calculus 1 - Limits and Continuity [HEVC]" ^
     --hwaccel qsv

::

   [226/226] SAFE-TO-DELETE  ...
   SAFE-TO-DELETE: 226   KEEP-SOURCE: 0
   ALL VERIFIED — these sources are safe to remove.

For **every** file this confirms the output exists, matches length (or the frames match —
it's smart about VFR and bogus source metadata, §12), and **decodes clean**. ``--hwaccel qsv`` runs the check on the iGPU (~4× faster); a hardware-decode error is re-confirmed on
the CPU before it's trusted. Only files marked **``SAFE-TO-DELETE``** are proven redundant.

.. _step-5--reclaim-the-space:

Step 5 — reclaim the space
~~~~~~~~~~~~~~~~~~~~~~~~~~

Only now delete or stage the originals — and only the ones marked ``SAFE-TO-DELETE``:

.. code:: powershell

   # e.g. move the verified sources to a holding folder to eyeball before deleting
   Move-Item "D:\Courses\Calculus 1 - Limits and Continuity" "E:\Safe_to_delete\"

That's the whole loop. Record the result in the conversion ledger (dedup key, source→output
size, % saved, verify verdict) so the course isn't re-encoded later.

--------------

.. _9-quick-reference-cheat-sheet:

9. Quick reference cheat-sheet
------------------------------

**Reading a file:**

- **Container** = the box (``.mp4``/``.mkv``) — not the quality.
- **Codec** = the compression (H.264/H.265) — *this* is the quality/size driver.
- **Resolution** = pixels (1920×1080). **Frame rate** = images/sec (23.976).
- **Bitrate** = bits/sec → size; lower in a modern codec = same look, smaller file.
- **Pixel format** ``yuv420p`` = standard 8-bit, color stored at ¼ detail.
- **Audio** ``AAC-LC 192k stereo 48kHz`` = standard sound; 128k is plenty for speech.

**Shrinking it (same quality):**

- Switch codec **H.264 → H.265** (``-c:v libx265``). ~50%+ smaller.
- Use **CRF** for quality-based sizing. **Lower = better/bigger.**

  - CRF **22** = safety margin · **24** = recommended · **26** = smaller, text may soften.

- Use **``-preset slow``** for better compression.
- **Keep** resolution, frame rate, pixel format. Don't downscale.

**Golden rules:**

- Container is not quality. Codec is.
- CRF is backwards: lower number = higher quality.
- CRF numbers don't transfer between codecs.
- Convert in small batches and verify before committing to the whole set.

--------------

.. _part-ii--going-deeper-how-it-all-works:

Part II — Going deeper: how it all works
========================================

Part I is everything you need to *do the job*. Part II is for understanding
*why* it works — the history of containers, how they're built byte-by-byte, and
what actually happens inside a compressed video stream. None of it is required to
convert files, but it's where the real understanding lives.

--------------

.. _10-containers-in-depth-the-rise-and-fall-of-avi:

10. Containers in depth: the rise and fall of AVI
-------------------------------------------------

We said in §3 that a **container is the box** and the **codec is the
compression**. The clearest way to feel that distinction is the story of **AVI**,
which dominated for two decades and then almost vanished.

What AVI is
~~~~~~~~~~~

**AVI = Audio Video Interleave.** Microsoft introduced it in **1992** as part of
*Video for Windows*. It is a **container, not a codec** — it doesn't compress
anything itself; it just stores a video stream, an audio stream, and metadata
together. The same ``.avi`` file might hold any of:

::

   movie.avi
   ├── MPEG-4 video + MP3 audio
   ├── DivX  video  + AC3 audio
   └── Xvid  video  + PCM audio

Why "Interleave"?
~~~~~~~~~~~~~~~~~

In the early '90s, drives and CPUs were slow. Rather than storing all the video
then all the audio, AVI **interleaves** them in small alternating chunks so a
player can read a little video, a little audio, and keep them in sync:

::

   video frame · audio samples · video frame · audio samples · …

Hence *Audio Video* **Interleave**.

Why it became so popular
~~~~~~~~~~~~~~~~~~~~~~~~

- **Simple** to implement and **universally supported** — every player opened AVI.
- **Flexible** — held many codecs (DivX, Xvid, MJPEG, MPEG-4, even early H.264).
- **Low CPU** — important for 1990s/2000s hardware.

You'll remember filenames like ``Matrix.DivX.avi`` or ``Movie.Xvid.avi`` — these were
everywhere on Video CDs and early downloads.

Why it faded
~~~~~~~~~~~~

As video modernized, AVI's 1992 design showed its age:

========================= ==================================================================================
Limitation                The problem
========================= ==================================================================================
**Subtitles**             Almost no standard support for soft subtitles, fonts, styling
**Streaming**             Designed pre-Internet; no real seeking / progressive download / adaptive streaming
**Multiple audio tracks** Handles English/French/commentary tracks poorly
**File size**             Original 32-bit offsets capped files near **2–4 GB**; extensions were awkward
**Variable frame rate**   Assumes constant frame rate; struggles with phone VFR footage
**B-frames**              Predates modern H.264/H.265 frame structures (see §12) — doesn't fit them cleanly
**Metadata**              Little support for chapters, tags, cover art, HDR, language info
========================= ==================================================================================

What replaced it
~~~~~~~~~~~~~~~~

========= =============== ======================================================================================
Container Origin          Strength
========= =============== ======================================================================================
**MP4**   MPEG-4          Universal; great for H.264/H.265 + AAC. Used by phones, cameras, YouTube, Netflix
**MKV**   Matroska        Maximum flexibility: any codec, many audio/subtitle tracks, chapters, HDR, attachments
**MOV**   Apple QuickTime Heavy use in video production
**WebM**  Google          Web streaming; pairs with VP9 / AV1
========= =============== ======================================================================================

Is AVI dead?
~~~~~~~~~~~~

Not entirely — you still meet it in old camcorders, CCTV/MJPEG recorders, legacy
industrial gear, and 1990s–2000s archives. But for **new** content the world
moved to:

::

   MP4 + H.264 + AAC      (universal)
   MKV + H.265 + AAC      (flexible, efficient)
   MP4 + AV1  + Opus      (newest, most efficient)

..

   **Analogy.** Containers are like shipping containers. AVI (1992) is a reliable,
   simple 1990s pickup truck. MP4/MKV are modern cargo ships — they carry far more
   kinds of cargo, navigate (seek/stream) better, and fit today's infrastructure.

--------------

.. _11-inside-the-box-how-containers-are-built:

11. Inside the box: how containers are built
--------------------------------------------

A container is just a **binary file format that organizes data into sections** so
a player can find each piece quickly. A typical file holds a video stream, an
audio stream, subtitles, metadata, chapters, and an index. The three big families
each use a different "filing system":

::

   AVI → RIFF chunks      MP4 → boxes (atoms)      MKV → EBML elements

.. _111-avi--riff-chunks:

11.1 AVI — RIFF chunks
~~~~~~~~~~~~~~~~~~~~~~

AVI is built on Microsoft's **RIFF (Resource Interchange File Format)**.
Everything inside is a **chunk**, and every chunk has the same shape:

::

   +--------+
   | ID     |  4 bytes   (e.g. "00dc" = video data, "01wb" = audio)
   +--------+
   | Size   |  4 bytes   (how many bytes of data follow)
   +--------+
   | Data   |  the bytes
   +--------+

A whole AVI file:

::

   RIFF
   ├── hdrl   (header)
   ├── strl   (stream information)
   ├── movi   (the actual media)
   │     ├── 00dc  video frame
   │     ├── 01wb  audio
   │     ├── 00dc  video frame
   │     └── 01wb  audio
   └── idx1   (index)

**Why this design limited AVI:** the **index (``idx1``) sits at the end** of the
file. So to seek or stream you need the end first — which makes streaming hard and
interrupted downloads painful. RIFF also simply has no place for subtitles,
chapters, HDR metadata, or multiple audio tracks.

.. _112-mp4--boxes-atoms:

11.2 MP4 — boxes (atoms)
~~~~~~~~~~~~~~~~~~~~~~~~

MP4 descends from Apple's QuickTime MOV. Instead of flat chunks it uses nested
**boxes** (also called **atoms**), each:

::

   +--------+
   | Size   |
   +--------+
   | Type   |   (e.g. "ftyp", "mdat", "moov")
   +--------+
   | Data   |   (may contain *more* boxes — boxes nest like folders)
   +--------+

The three top-level boxes that matter:

======== ============== =====================================================
Box      Meaning        Holds
======== ============== =====================================================
**ftyp** File type      "I am an MP4" (e.g. ``major_brand = mp42``)
**mdat** Media data     The actual video + audio frames (usually huge)
**moov** Movie metadata Duration, frame rate, codec info, indexes, timestamps
======== ============== =====================================================

Inside ``moov`` is a tree:

::

   moov
   ├── mvhd            (movie header)
   └── trak            (one per track)
       ├── tkhd        (track header)
       └── mdia
           └── minf
               └── stbl   (sample table — the index)

**Fast Start.** By default ``moov`` can land *after* ``mdat``, so a player must
download to near the end before it can begin. The fix — used by YouTube and
streaming — is to move ``moov`` to the **front**:

::

   ftyp · moov · mdat      ← player knows everything immediately; can seek before download finishes

(ffmpeg does this with ``-movflags +faststart``.)

.. _113-mkv--ebml-elements:

11.3 MKV — EBML elements
~~~~~~~~~~~~~~~~~~~~~~~~

MKV = **Matroska Video**, built on **EBML (Extensible Binary Meta Language)** —
essentially **binary XML**. Where XML writes:

.. code:: xml

   <movie> <video/> <audio/> </movie>

EBML stores the same nesting in binary, each element being:

::

   ID · Length · Value        (e.g. TrackType, Length=1, Value=Video)

A Matroska file's top level:

::

   EBML Header
   Segment
   ├── SeekHead     (index of where things are)
   ├── Info         (duration, title…)
   ├── Tracks       (Track 1 = H.265 video, Track 2 = AAC audio, Track 3 = subs…)
   ├── Chapters
   ├── Attachments  (fonts, cover art — why anime subs can ship styled fonts)
   ├── Tags
   └── Cluster      (the actual media packets: video frame, audio frame, …)

**Why MKV is so capable:** EBML is **self-describing** — a player can **skip
unknown elements** it doesn't understand. New features can be added without
breaking old players. That extensibility is exactly what AVI lacked.

.. _114-side-by-side:

11.4 Side-by-side
~~~~~~~~~~~~~~~~~

======================= =========== ============= =============
Feature                 AVI         MP4           MKV
======================= =========== ============= =============
Internal format         RIFF chunks Boxes (atoms) EBML elements
Year                    1992        1999          2002
Tree structure          Limited     Yes           Yes
Streaming               Poor        Excellent     Good
Multiple audio tracks   Limited     Good          Excellent
Subtitles               Poor        Good          Excellent
Chapters                Poor        Good          Excellent
Attachments (fonts/art) No          No            Yes
Extensibility           Limited     Good          Excellent
======================= =========== ============= =============

.. _115-what-a-player-actually-does:

11.5 What a player actually does
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Whatever the container, a player (VLC, ffmpeg) does roughly this — and notice the
container itself **never decodes anything**; the **codec** does:

::

   Open file
     → Read container structure
     → Locate streams
     → Pass video packets → video decoder
     → Pass audio packets → audio decoder
     → Synchronize timestamps
     → Display image + play sound

--------------

.. _12-below-the-container-the-video-stream-itself:

12. Below the container: the video stream itself
------------------------------------------------

This is the layer *beneath* the container — where the actual compression happens.
If you have a CRT/analog-TV background, you already understand the core insight,
because modern codecs are, in large part, sophisticated ways of exploiting **how
humans perceive moving images** — the same thing television engineers spent
decades learning.

The layers, top to bottom
~~~~~~~~~~~~~~~~~~~~~~~~~

::

   MKV container
   ├── H.264/H.265 video stream
   │     └── NAL units → SPS · PPS · IDR frame · P-frames · B-frames · SEI
   ├── AAC audio stream
   └── subtitles

The container only *stores* these pieces. The **codec understands them.**

.. _from-crt-to-codec--the-shared-idea:

From CRT to codec — the shared idea
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A CRT paints a picture with an electron beam scanning line by line, and TV
engineers learned a principle that underpins all modern compression:

   **The human eye notices changes far more than absolute values.**

Every technique below is an application of that idea.

.. _frame-types--storing-differences-not-pictures:

Frame types — storing *differences*, not pictures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Storing every frame as a full image would be enormous. Instead codecs store
mostly *differences* between frames:

=========== ============= ========================================================================= ===============
Frame       Name          What it stores                                                            Typical size
=========== ============= ========================================================================= ===============
**I-frame** Intra         A **complete** picture (like a JPEG), decodable on its own                large (~300 KB)
**P-frame** Predictive    Only the **changes from an earlier frame** (e.g. "the car moved 5 px")    small (~20 KB)
**B-frame** Bidirectional Changes referencing **both a past and a future** frame — best compression smallest
=========== ============= ========================================================================= ===============

Dependencies:

::

   I → P → P → P            (P depends on what came before)
   I → P ← B → P            (B looks both backward and forward)

A common displayed sequence: ``I B B P B B P``.

Display order vs decode order: PTS, DTS, and the muxer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Look at that sequence again: ``I B B P B B P``. A **B-frame references a future frame**
(line 1110 above), so the decoder has a chicken-and-egg problem — it can't build the
first ``B`` until it already has the ``P`` that comes *after* it. The fix: the codec
**stores and decodes frames in a different order than it displays them.**

::

   Display order (what you watch):   I  B  B  P
   Decode order  (what's in the file): I  P  B  B   ← P decoded first, so the B's have their reference

To keep these two orders straight, **every frame carries two timestamps**:

======= ======================= ===================================== =================================================================================
Stamp   Name                    Answers                               Must it always increase?
======= ======================= ===================================== =================================================================================
**PTS** Presentation Time Stamp *When do I* **display** *this frame?* No — it legitimately jumps around (B-frames shown between frames decoded later)
**DTS** Decode Time Stamp       *When do I* **decode** *this frame?*  **Yes** — decoding marches strictly forward; you can't decode "backwards in time"
======= ======================= ===================================== =================================================================================

So PTS may zig-zag, but **DTS must be monotonic** — each frame's DTS strictly greater
than the last. (For an I/P-only stream with no B-frames, decode order = display order and
PTS = DTS; the two only diverge once B-frames appear.)

**Where the muxer comes in.** Recall the container from §11 — it interleaves the encoded
video and audio packets into one file. The component that does that weaving is the
**muxer** (multiplexer); the **demuxer** unpicks it on playback. This is the same idea as
multiplexing several signals onto one carrier in the transmitter era — one transport, many
streams, each tagged so the receiver can separate and re-time them. Crucially, the muxer
**never touches the pictures** — it only arranges already-encoded packets and writes their
PTS/DTS. So a muxer complaint is always about *timing/packaging*, never about image data.

**Non-monotonic DTS — a real example from our own encodes.** When verifying the re-encoded
*Understanding Calculus II* course, ffmpeg printed, once per file, near the start:

::

   [null @ ...] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 17 >= 17

Read literally: *"the new packet's DTS (17) is not greater than the previous one (17)"* —
two packets claimed the **same** decode time, so DTS failed to increase. It's harmless here,
for three reasons:

- It comes from the **``[null]`` muxer, not the decoder** — the pictures all decoded fine;
  only the timestamp bookkeeping had one duplicate, which ffmpeg fixes by nudging the stamp
  forward one tick.
- The source was **``.flv``** — an old Flash container notorious for loose, approximate
  timestamps; occasionally two packets get stamped the same millisecond, and that quirk
  rides along into the re-encode.
- It fired **once, at the very start**, with **no** ``corrupt``, ``concealing``, or decoder-error
  lines anywhere — so no frame data is damaged. The worst theoretical effect is a single-tick
  A/V-sync wobble at that instant, which is imperceptible.

The practical lesson for tooling: an integrity check must **distinguish a real decode error
(corrupt frames) from a benign muxer timestamp warning.** Counting the DTS line as
"corruption" produces false alarms — exactly the bug we fixed in slimv's ``verify`` step.

Group Of Pictures (GOP)
~~~~~~~~~~~~~~~~~~~~~~~

A **GOP (Group Of Pictures)** is one I-frame and all the P/B-frames that depend on
it before the next I-frame:

::

   Long  GOP:  I B B P B B P B B P …   → smaller files, slower seeking
   Short GOP:  I P I P I P             → larger files, easier editing

.. _motion-compensation--block-sizes:

Motion compensation & block sizes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a car shifts right between frames, the codec doesn't redraw it — it stores
*"move this block +2 pixels"* (a **motion vector**) plus any small leftover
difference. Much of H.264's complexity lives here. Pictures are divided into
blocks for this:

- **H.264** → **macroblocks**, 16×16 pixels.
- **H.265** → **Coding Tree Units (CTUs)**, up to 64×64 — bigger blocks compress
  large uniform areas far better.

The compression pipeline (where quality is actually lost)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After prediction, a **residual** (the prediction error) remains. It's then:

1. **Transform** — a DCT-like transform converts the residual into low- and
   high-frequency components (same idea as JPEG).
2. **Quantization** — high-frequency detail the eye barely notices is discarded.
   **This is the lossy step** — and exactly what **CRF** (§6) controls.
3. **Entropy coding** — what's left is packed losslessly. H.264 uses **CAVLC** or
   **CABAC** (*Context-Adaptive Binary Arithmetic Coding*); CABAC's efficiency is
   a big reason H.264 compresses so well.

.. _nal-units--how-the-stream-is-packaged:

NAL units — how the stream is packaged
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Everything in H.264/H.265 is wrapped into **NAL units** (*Network Abstraction
Layer*) — think of them as packets, each with a small header + payload. The key
types:

========= ============================= =======================================================================================================================
NAL type  Name                          Contains
========= ============================= =======================================================================================================================
**SPS**   Sequence Parameter Set        **Global** info: resolution, frame rate, profile, level, bit depth. *Without it the decoder can't interpret any frame.*
**PPS**   Picture Parameter Set         Picture-level settings: entropy mode, reference frames, quantization
**SEI**   Supplemental Enhancement Info Optional extras: HDR metadata, captions, timing
**Slice** —                             A piece of a frame; each frame is split into one or more slices, each → NAL unit(s)
**IDR**   Instantaneous Decoder Refresh A special I-frame after which all older references can be discarded — **seeking jumps to IDR frames**
========= ============================= =======================================================================================================================

A typical stream on the wire:

::

   SPS · PPS · IDR · P · B · B · P · B · B · P · IDR · P · B · B · …

.. _what-h265-hevc-improved-over-h264:

What H.265 (HEVC) improved over H.264
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **CTUs** up to 64×64 (vs fixed 16×16 macroblocks)
- **Quarter-pixel** motion accuracy and better motion vectors
- **35 intra-prediction modes** (vs ~9)
- Larger reference lists, improved CABAC
- **Parallel tools** (tiles, wavefront) for multi-core encoding/decoding

**Net result: ~30–50% smaller files than H.264 at the same quality** — the exact
saving we measured on the screencast course in §7.

The full ffmpeg path
~~~~~~~~~~~~~~~~~~~~

::

   MKV (demux) → H.264/H.265 stream → NAL units → decoder → frames → RGB conversion → display

--------------

.. _appendix-a--abbreviations--glossary:

Appendix A — Abbreviations & glossary
-------------------------------------

**Containers & file formats**
\| Term \| Stands for / meaning \|
\|------\|----------------------\|
\| **AVI** \| Audio Video Interleave — Microsoft container (1992) \|
\| **RIFF** \| Resource Interchange File Format — the chunk format AVI is built on \|
\| **MP4** \| MPEG-4 Part 14 container; built from **boxes/atoms** \|
\| **MOV** \| Apple QuickTime container (MP4's ancestor) \|
\| **MKV** \| Matroska Video container; built on **EBML** \|
\| **EBML** \| Extensible Binary Meta Language — "binary XML," the basis of MKV \|
\| **WebM** \| Web-oriented subset of Matroska (VP9/AV1 + Opus) \|
\| **TS** \| Transport Stream — broadcast/streaming container \|
\| **atom / box** \| A nested section inside an MP4/MOV file \|
\| **ftyp / mdat / moov** \| MP4 boxes: file-type / media-data / metadata-and-index \|
\| **faststart** \| Moving ``moov`` to the file's front for instant streaming \|
\| **Muxer / Demuxer** \| Multiplexer — interleaves encoded video/audio packets into one container (and writes their PTS/DTS); demuxer reverses it on playback. Never touches the pictures themselves \|

**Codecs**
\| Term \| Stands for / meaning \|
\|------\|----------------------\|
\| **Codec** \| Coder–decoder: the compression method (≠ container) \|
\| **H.264 / AVC** \| Advanced Video Coding (2003) — the universal codec \|
\| **H.265 / HEVC** \| High Efficiency Video Coding (2013) — ~50% smaller than H.264 \|
\| **AV1** \| Open codec (2018) — most efficient, slowest to encode \|
\| **VP9 / VP8** \| Google codecs (web/WebM) \|
\| **DivX / Xvid** \| Early MPEG-4 codecs common in old AVI files \|
\| **MJPEG** \| Motion JPEG — each frame a standalone JPEG \|
\| **libx264 / libx265** \| ffmpeg's H.264 / H.265 encoders \|

**Inside the video stream**
\| Term \| Stands for / meaning \|
\|------\|----------------------\|
\| **NAL** \| Network Abstraction Layer — the "packets" a stream is split into \|
\| **I-frame** \| Intra frame — a complete, standalone picture \|
\| **P-frame** \| Predictive frame — changes from an earlier frame \|
\| **B-frame** \| Bidirectional frame — changes from past *and* future frames \|
\| **PTS** \| Presentation Time Stamp — *when to display* a frame \|
\| **DTS** \| Decode Time Stamp — *when to decode* a frame; must increase monotonically \|
\| **Monotonic DTS** \| The rule that each frame's DTS is strictly greater than the last; a "non-monotonic dts" warning means two packets shared a decode time (benign muxer timing complaint, not corruption) \|
\| **IDR** \| Instantaneous Decoder Refresh — special I-frame; seek target \|
\| **GOP** \| Group Of Pictures — one I-frame and its dependent frames \|
\| **SPS** \| Sequence Parameter Set — global stream info (resolution, fps, profile…) \|
\| **PPS** \| Picture Parameter Set — picture-level encoding settings \|
\| **SEI** \| Supplemental Enhancement Information — optional (HDR, captions, timing) \|
\| **Macroblock** \| H.264's 16×16 processing block \|
\| **CTU** \| Coding Tree Unit — H.265's block, up to 64×64 \|
\| **Motion vector** \| "This block moved by X,Y" — the heart of inter-frame compression \|
\| **DCT** \| Discrete Cosine Transform — frequency transform of the residual \|
\| **Quantization** \| Discarding hard-to-see detail — the lossy step (what CRF tunes) \|
\| **CAVLC / CABAC** \| H.264 entropy coders; CABAC = Context-Adaptive Binary Arithmetic Coding \|
\| **Residual** \| The leftover prediction error that gets transformed & quantized \|
\| **Profile / Level** \| Feature set (e.g. High) / capability ceiling (e.g. 4.1) of a stream \|

**Quality, color & audio**
\| Term \| Stands for / meaning \|
\|------\|----------------------\|
\| **CRF** \| Constant Rate Factor — quality-based encoding dial (lower = better) \|
\| **Bitrate** \| Bits per second spent on a stream (drives size) \|
\| **VFR / CFR** \| Variable / Constant Frame Rate \|
\| **fps** \| Frames per second \|
\| **YUV / YCbCr** \| Color stored as brightness (Y) + two color channels \|
\| **Chroma subsampling** \| Storing color at lower resolution than brightness (e.g. 4:2:0) \|
\| **yuv420p / yuv444p** \| 8-bit color at ¼ / full color detail \|
\| **Bit depth** \| Shades per channel (8-bit = 256, 10-bit = 1024) \|
\| **HDR** \| High Dynamic Range \|
\| **AAC / AAC-LC** \| Advanced Audio Coding / its Low-Complexity profile \|
\| **Opus** \| Modern low-latency audio codec (pairs with AV1/WebM) \|
\| **Sample rate** \| Audio samples per second (e.g. 48 kHz) \|
\| **kbps / Mbps** \| Kilo- / Mega-bits per second \|

--------------

.. _appendix-b--further-reading-books-tools--source-code:

Appendix B — Further reading: books, tools & source code
--------------------------------------------------------

.. _books--fundamentals-analog--digital:

Books — fundamentals (analog → digital)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Charles Poynton — Digital Video and HD: Algorithms and Interfaces** — the
  best bridge from analog TV to digital video; ideal with a CRT background.
- **Keith Jack — Video Demystified** — legendary reference covering NTSC, PAL,
  CRT, MPEG, HDTV, and compression. Excellent transition book.
- **A. Murat Tekalp — Digital Video Processing** — graduate-level, deep math.

.. _books--compression--codecs:

Books — compression / codecs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Iain E. Richardson — The H.264 Advanced Video Compression Standard** —
  arguably the best single H.264 book: NAL units, SPS/PPS, CABAC, motion
  compensation, profiles & levels.
- **Sze, Budagavi & Sullivan (eds.) — High Efficiency Video Coding (HEVC):
  Algorithms and Architectures** — the H.265 equivalent.
- **Sayood — Introduction to Data Compression** — Huffman, arithmetic coding,
  JPEG, MPEG, CABAC.

.. _books--image-processing--vision:

Books — image processing & vision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Gonzalez & Woods — Digital Image Processing** — the classic.
- **Szeliski — Computer Vision: Algorithms and Applications** — excellent, free
  online.

.. _books--systems-programming-to-read-the-source:

Books — systems programming (to read the source)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Robert Love — Linux System Programming**
- **Stevens & Rago — Advanced Programming in the UNIX Environment**

.. _tools--for-inspecting--dissecting-files:

Tools — for inspecting & dissecting files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

==================== ================================================================
Tool                 Use
==================== ================================================================
**MediaInfo**        Fast, detailed read-out of any media file
**ffprobe** (ffmpeg) Scriptable stream/format inspection (used throughout this guide)
**GPAC / MP4Box**    Dissect and rewrite MP4 box structure
**MKVToolNix**       Inspect/edit Matroska files
**VLC**              Plays everything; good for codec/stream info
==================== ================================================================

.. _source-code--most-valuable-of-all-for-a-systems-programmer:

Source code — most valuable of all for a systems programmer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **FFmpeg** — study ``libavformat/`` (containers/demuxers), ``libavcodec/``
  (codecs), ``libswscale/`` (color conversion).
- **x264** — a masterpiece of C; real-world NAL units, CABAC, motion estimation,
  transforms.
- **x265** — the HEVC equivalent.

--------------

.. _appendix-c--the-big-picture-path-from-crt-to-av1:

Appendix C — The big-picture path: from CRT to AV1
--------------------------------------------------

For someone coming from CRT/analog television, the most rewarding way to see this
whole field is as one continuous lineage. Modern codecs are the culmination of
nearly a century of television engineering, information theory, signal processing,
and computer science:

::

   CRT
    → Analog TV
    → Sampling theory
    → YCbCr (brightness/color separation)
    → JPEG (the still-image transform + quantization)
    → MPEG-1
    → MPEG-2
    → H.264 (AVC)
    → H.265 (HEVC)
    → AV1

Each step reuses the one before: JPEG's DCT becomes the codec's transform stage;
YCbCr and chroma subsampling come straight from how analog TV economized
bandwidth; motion compensation generalizes the TV insight that *change matters
more than absolute value*. The line from vacuum tubes and electron beams runs
unbroken to Netflix and 8K HDR streaming.

--------------

.. _appendix-d--roadmap-topics-to-write-next:

Appendix D — Roadmap: topics to write next
------------------------------------------

A running list of topics to grow this (and the companion SWF guide) into a full
**audio/video reference**. Each is a one-line hook; we'll expand them later. Many
deliberately start from **analog radio/TV transmission and CRT receivers** — that
heritage is the natural on-ramp to almost everything digital.

From the transmitter/receiver era (analog foundations)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **How a CRT actually draws a frame** — electron gun, deflection yokes, raster
  scan, persistence of vision, and why "fields" exist.
- **Interlaced vs progressive (``i`` vs ``p``)** — why 1080\ **i** was invented for
  CRT bandwidth, what a "field" is, and why deinterlacing is needed today.
- **NTSC / PAL / SECAM** — the three analog color systems, their frame rates
  (29.97 vs 25), and *why* 29.97 (the color-subcarrier story) — the origin of
  today's 23.976/29.97 oddities.
- **Composite, S-Video, component, RGB/SCART** — how the luma/chroma signal was
  carried, and how that maps to YUV/YCbCr in digital.
- **The analog TV channel** — VSB modulation, the 6/7/8 MHz channel, audio FM
  subcarrier, and how bandwidth limits shaped resolution.
- **Radio fundamentals** — AM vs FM, modulation, the broadcast chain from studio
  to transmitter to receiver; the bridge to digital radio.
- **Sampling theory & Nyquist** — turning a continuous signal into samples; the
  single most important idea connecting analog to digital.
- **Analog → digital TV switchover** — ATSC, DVB-T/T2, ISDB; how OFDM and
  MPEG-2/H.264 replaced the analog raster over the air.

.. _color--signal-science:

Color & signal science
~~~~~~~~~~~~~~~~~~~~~~

- **YCbCr / YUV in depth** — the math of the brightness/color split and gamma.
- **Chroma subsampling 4:4:4 / 4:2:2 / 4:2:0** — what the ratios mean, with
  side-by-side text-sharpness examples.
- **Color spaces & gamut** — Rec.601 vs Rec.709 vs Rec.2020, and the dreaded
  "washed-out colors" bug from mismatched tags.
- **HDR** — HDR10, HDR10+, Dolby Vision, HLG; what PQ/transfer functions do.
- **Bit depth & banding** — why 10-bit fixes gradients even for SDR.

Containers (extending Part II)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **WebM / MOV / TS / MXF / OGG** — each container's niche, deep-dived.
- **Fragmented MP4 & streaming containers** — DASH/HLS segments, CMAF.
- **Subtitle & caption formats** — SRT, ASS/SSA, WebVTT, PGS, CEA-608/708.

Video codecs (extending §12)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **MPEG-1 & MPEG-2** — the VCD/DVD/broadcast workhorses, in detail.
- **VP8/VP9 and AV1 internals** — the open-codec lineage and how AV1 works.
- **Intra-prediction modes** — how I-frames predict from neighboring blocks.
- **Rate control deep-dive** — CRF vs CBR vs VBR vs 2-pass, and when to use each.
- **Profiles, levels & tiers** — what they cap and why playback fails on TVs.
- **Hardware encoding/decoding** — NVENC, Quick Sync, AMF, VideoToolbox: speed
  vs quality trade-offs.

Audio (a whole companion track)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Digital audio fundamentals** — PCM, sample rate, bit depth, dynamic range.
- **Lossy audio codecs** — MP3, AAC, Opus, Vorbis, AC-3/E-AC-3, DTS compared.
- **Lossless audio** — FLAC, ALAC, WavPack, and when lossless is worth it.
- **Channels & surround** — mono/stereo/5.1/7.1/Atmos, downmixing.
- **Loudness & normalization** — LUFS, EBU R128, the "loudness war."

.. _delivery-tooling--quality:

Delivery, tooling & quality
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Streaming protocols** — HLS vs DASH, adaptive bitrate, the manifest/segment
  model.
- **Measuring quality objectively** — PSNR, SSIM, and especially **VMAF**.
- **Practical ffmpeg recipes** — trimming, concatenating, batch scripts,
  hardware accel, two-pass, faststart, remuxing without re-encoding.
- **Remux vs transcode** — changing the container *without* touching quality.
- **Archival & preservation** — choosing formats that will still open in 30 years
  (ties back to the AVI lesson in §10).

.. _engineering-deep-dives-ee--c--digital-design--networking-track:

Engineering deep-dives (EE / C / digital-design / networking track)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*For readers with an electronics, systems-programming, and digital-design
background who want the layer below the abstractions.*

**DSP & information theory (the math under the codec)**

- **Sampling, Nyquist & reconstruction** — aliasing, anti-alias filtering, and the
  ADC/DAC chain from sensor to bitstream.
- **The DCT from scratch** — deriving it, why cosines, fast DCT algorithms, and
  how it differs from the FFT.
- **Quantization & rate–distortion theory** — the R-D curve, Lagrangian
  optimization (the ``λ`` an encoder actually minimizes), and why CRF works.
- **Entropy coding internals** — Huffman vs arithmetic vs **CABAC**; building a
  toy arithmetic coder in C.
- **Information theory foundations** — Shannon entropy, source coding theorem, and
  the theoretical limits a codec chases.
- **Digital filters** — FIR/IIR, the filters behind scaling, deinterlacing, and
  loop/deblocking filters in H.264/H.265.

**Hardware & digital design (the silicon side)**

- **How codecs map to hardware** — pipelining the encode/decode stages, the
  motion-estimation bottleneck, and parallelism (tiles, wavefronts, slices).
- **Fixed-point vs floating-point** — why codecs are specified in integer math for
  bit-exact decoding across implementations.
- **FPGA/ASIC video pipelines** — block diagram of a hardware decoder; line
  buffers, frame buffers, and memory-bandwidth as the real limit.
- **Capture & display silicon** — image sensors, the ISP pipeline, HDMI/DisplayPort
  signaling, and where it echoes the old analog scan-out.
- **ADC/DAC & PLLs** — the mixed-signal front end that replaced the analog
  receiver, tied back to your transmitter/receiver work.

**Systems programming with C (build/inspect it yourself)**

- **Writing a minimal H.264 parser in C** — splitting NAL units, reading SPS/PPS,
  walking a real bitstream byte by byte.
- **Programming the FFmpeg libraries** — ``libavformat``/``libavcodec``/``libswscale``
  APIs: demux → decode → scale → encode, with real C code.
- **Zero-copy & performance** — buffer management, planar vs packed pixel layout,
  cache behavior, and **SIMD** (SSE/AVX/NEON) in hot loops.
- **A from-scratch container parser** — read an MP4's box tree (or an MKV's EBML)
  in C, mirroring §11.

**Networking & real-time delivery**

- **RTP / RTSP / SRTP** — how live video is packetized over UDP; timestamps and
  the RTCP feedback loop.
- **Jitter buffers & packet-loss concealment** — surviving an imperfect network
  (the digital descendant of analog noise tolerance).
- **WebRTC** — the full real-time stack: ICE/STUN/TURN, SRTP, congestion control.
- **Adaptive streaming under the hood** — HLS/DASH segmenting, ABR algorithms,
  and buffer-based vs throughput-based switching.
- **Transport & congestion** — TCP vs UDP vs **QUIC** for media, and why each is
  chosen.
- **Broadcast digital transport** — MPEG-TS packets, PCR/PTS/DTS clocking,
  OFDM/QAM modulation in DVB/ATSC — the direct digital heir to your analog
  transmitter background.

..

   Suggested split as this grows: keep **this** doc as the video/codec/container
   reference, spin out a dedicated **audio formats** companion, and possibly a
   third **analog-broadcast-to-digital** piece that uses your radio/TV and
   electronics-engineering background as its spine. The engineering deep-dives
   above could even become a fourth, more hands-on **"build/inspect it in C"**
   volume.
