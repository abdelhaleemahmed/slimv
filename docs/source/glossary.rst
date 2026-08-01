========
Glossary
========

.. glossary::

   ffmpeg
      The open-source media framework slimv drives to do all encoding,
      decoding, and measurement. ``ffprobe`` (shipped with it) reports a file's
      streams and properties.

   profile
      A named, quality-preserving encode recipe in slimv — a codec plus its
      rate-control settings (e.g. ``qsv``, ``balanced``). Resolution, frame
      rate, and pixel format are never changed. Defined in
      :mod:`slimv.profiles`.

   CRF
      Constant Rate Factor — the quality dial for x265/AV1. It targets a
      constant visual quality and lets the bitrate vary. Lower value = higher
      quality = bigger file. CRF numbers are not comparable between codecs.

   VMAF
      Video Multi-Method Assessment Fusion — Netflix's perceptual quality
      metric. Higher is better; ~95+ is visually transparent for natural video.
      For screen/text content VMAF reads lower than perception, so ~92 there is
      effectively transparent.

   QSV
      Intel Quick Sync Video — the fixed-function media engine on Intel iGPUs.
      slimv's ``qsv`` profile uses ``hevc_qsv`` to encode H.265 on this engine,
      freeing the CPU and any discrete GPU.

   NVENC
      NVIDIA's hardware video encoder. slimv's ``nvenc`` profile uses
      ``hevc_nvenc`` for very fast H.265 encoding on an NVIDIA GPU.

   autodoc
      The Sphinx extension that generates the :doc:`API reference <05-api>`
      directly from the ``slimv`` package's docstrings, keeping documentation
      and code in sync.

   rich
      The Python library slimv uses for colored, formatted terminal output
      (tables, status lines). slimv's only third-party runtime dependency.
