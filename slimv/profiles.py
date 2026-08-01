"""Encoding profile catalog.

Every profile is a *quality-preserving* recipe: resolution, frame rate and pixel
format are left untouched; only the codec/efficiency change. Audio is always
re-encoded to AAC 128k (transparent for speech; raise for music).

Rate-control note: for CRF (x265/AV1) and global_quality (QSV) / cq (NVENC),
LOWER number = higher quality = bigger file. The numbers are NOT comparable
across codecs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


@dataclass(frozen=True)
class Profile:
    name: str
    codec: str          # the ffmpeg encoder this profile needs
    vargs: list[str]    # video-side ffmpeg arguments
    quality: str
    speed: str
    size: str
    when: str
    hardware: bool = False


_BUILTIN: dict[str, Profile] = {
    "archive": Profile(
        "archive", "libx265",
        ["-c:v", "libx265", "-crf", "18", "-preset", "slow", "-tag:v", "hvc1"],
        quality="Near-lossless (VMAF ~97+)", speed="Slow (CPU)", size="Largest of the H.265 set",
        when="Masters / archival; precious sources; you have time and disk.",
    ),
    "quality": Profile(
        "quality", "libx265",
        ["-c:v", "libx265", "-crf", "20", "-preset", "medium", "-tag:v", "hvc1"],
        quality="Visually transparent, extra headroom", speed="Medium (CPU)", size="Larger",
        when="Detail- or text-heavy content where you want a safety margin.",
    ),
    "balanced": Profile(
        "balanced", "libx265",
        ["-c:v", "libx265", "-crf", "23", "-preset", "medium", "-tag:v", "hvc1"],
        quality="Visually transparent for most content", speed="Medium (CPU)", size="Small",
        when="Default for general video when you have CPU time and want the smallest CPU-encoded file.",
    ),
    "small": Profile(
        "small", "libx265",
        ["-c:v", "libx265", "-crf", "26", "-preset", "slow", "-tag:v", "hvc1"],
        quality="Good; fine text may soften slightly", speed="Slow (CPU)", size="Smallest (CPU)",
        when="Low-detail talking-head / slide content where maximum shrink matters.",
    ),
    "qsv": Profile(
        "qsv", "hevc_qsv",
        ["-c:v", "hevc_qsv", "-preset", "veryslow", "-global_quality", "24", "-tag:v", "hvc1"],
        quality="Visually transparent (VMAF ~92 on screen content)",
        speed="Fast (Intel iGPU)", size="Small",
        when="Intel Quick Sync present: ~2x speed on the idle iGPU, CPU + NVIDIA stay free. Great all-rounder for slides/screencasts.",
        hardware=True,
    ),
    "qsv-hq": Profile(
        "qsv-hq", "hevc_qsv",
        ["-c:v", "hevc_qsv", "-preset", "veryslow", "-global_quality", "22", "-tag:v", "hvc1"],
        quality="Transparent with margin (~VMAF 91+ even on hard camera footage)",
        speed="Fast (Intel iGPU)", size="Small (a bit larger than qsv)",
        when="Intel Quick Sync on HARDER content (real camera footage, motion, detail) where plain qsv dips below ~90. Keeps the hardware speed; adds quality headroom.",
        hardware=True,
    ),
    "qsv-720p": Profile(
        "qsv-720p", "hevc_qsv",
        ["-c:v", "hevc_qsv", "-preset", "veryslow", "-global_quality", "24",
         "-vf", "scale=-2:720", "-tag:v", "hvc1"],
        quality="Transparent at 720p (downscaled from 1080p)",
        speed="Fast (Intel iGPU)", size="~Half of a 1080p re-encode",
        when="Long, already-compressed 1080p that won't shrink at full resolution (see the Size=bitrate×duration rule). Trades sharpness for a real size cut; great for tutorials watched in a window.",
        hardware=True,
    ),
    "qsv-480p": Profile(
        "qsv-480p", "hevc_qsv",
        ["-c:v", "hevc_qsv", "-preset", "veryslow", "-global_quality", "24",
         "-vf", "scale=-2:480", "-tag:v", "hvc1"],
        quality="Acceptable at 480p (SD; downscaled)",
        speed="Fast (Intel iGPU)", size="Smallest practical (SD)",
        when="Maximum shrink when small-screen / archival viewing is fine and on-screen text is large. Check that code/terminal text stays legible before bulk use.",
        hardware=True,
    ),
    "nvenc": Profile(
        "nvenc", "hevc_nvenc",
        ["-c:v", "hevc_nvenc", "-preset", "p7", "-rc", "vbr", "-cq", "24", "-tag:v", "hvc1"],
        quality="Visually transparent", speed="Very fast (NVIDIA GPU)",
        size="Small (slightly larger than x265)",
        when="NVIDIA GPU present and idle; fastest option for large batches.",
        hardware=True,
    ),
    "av1": Profile(
        "av1", "libsvtav1",
        ["-c:v", "libsvtav1", "-crf", "30", "-preset", "6", "-pix_fmt", "yuv420p"],
        quality="Visually transparent", speed="Slow (CPU)",
        size="Smallest overall (~10-20% < H.265)",
        when="Maximum compression and players support AV1; willing to trade encode time.",
    ),
}

# Built-in display / iteration order.
_BUILTIN_ORDER = ["archive", "quality", "balanced", "small", "qsv", "qsv-hq",
                  "qsv-720p", "qsv-480p", "nvenc", "av1"]

# Profiles benchmark tries by default (the practical contenders).
BENCH_DEFAULT = ["qsv", "qsv-hq", "balanced", "quality", "nvenc"]


# ---------------------------------------------------------------------------
#  User-defined profiles (no code edits needed)
#
#  slimv merges an optional `profiles.toml` over the built-ins, so you can ADD
#  new profiles or OVERRIDE built-in ones without touching this file. Search
#  order (later wins): the user config dir, then the current directory, then
#  whatever $SLIMV_PROFILES points at.
#
#  TOML schema — one table per profile:
#      [my-profile]
#      codec = "hevc_qsv"                 # required: the ffmpeg encoder used
#      vargs = ["-c:v","hevc_qsv","-preset","veryslow","-global_quality","21","-tag:v","hvc1"]  # required
#      quality  = "..."   # optional metadata shown by `slimv profiles`
#      speed    = "..."
#      size     = "..."
#      when     = "..."
#      hardware = true     # optional
# ---------------------------------------------------------------------------

def _config_candidates() -> list[Path]:
    paths = []
    # user config dir
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            paths.append(Path(base) / "slimv" / "profiles.toml")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        paths.append(Path(base) / "slimv" / "profiles.toml")
    # current working directory
    paths.append(Path.cwd() / "profiles.toml")
    # explicit override
    env = os.environ.get("SLIMV_PROFILES")
    if env:
        paths.append(Path(env))
    return paths


def _profile_from_toml(name: str, body: dict) -> Profile:
    if "codec" not in body or "vargs" not in body:
        raise ValueError(f"profile '{name}' must define both 'codec' and 'vargs'")
    return Profile(
        name=name,
        codec=str(body["codec"]),
        vargs=[str(x) for x in body["vargs"]],
        quality=str(body.get("quality", "(user-defined)")),
        speed=str(body.get("speed", "")),
        size=str(body.get("size", "")),
        when=str(body.get("when", "User-defined profile.")),
        hardware=bool(body.get("hardware", False)),
    )


def _load_merged() -> tuple[dict[str, Profile], list[str]]:
    """Built-in profiles merged with any user profiles.toml files."""
    profiles = dict(_BUILTIN)
    order = list(_BUILTIN_ORDER)
    if tomllib is None:
        return profiles, order
    for path in _config_candidates():
        try:
            if not path.is_file():
                continue
            with path.open("rb") as fh:
                data = tomllib.load(fh)
        except Exception:
            # a broken/unreadable profiles.toml must never crash slimv
            continue
        for name, body in data.items():
            if not isinstance(body, dict):
                continue
            try:
                profiles[name] = _profile_from_toml(name, body)
            except ValueError:
                continue
            if name not in order:
                order.append(name)
    return profiles, order


PROFILES, ORDER = _load_merged()


def apply_overrides(profile: Profile, *, gq: int | None = None,
                    crf: int | None = None, preset: str | None = None,
                    scale: int | None = None) -> tuple[Profile, list[str]]:
    """Apply ad-hoc CLI overrides to a profile's vargs.

    - gq      -> set the value after ``-global_quality`` (QSV)
    - crf     -> set the value after ``-crf`` (x265 / AV1)
    - preset  -> set the value after ``-preset``
    - scale   -> set ``-vf scale=-2:<height>`` (replacing any existing -vf)

    Returns ``(new_profile, warnings)``. A warning is recorded when an override's
    target flag isn't present for that codec (e.g. ``--crf`` on a QSV profile),
    so the caller can surface it. If no overrides are given, returns the profile
    unchanged with an empty warning list.
    """
    if gq is None and crf is None and preset is None and scale is None:
        return profile, []

    v = list(profile.vargs)
    warnings: list[str] = []

    def set_after(flag: str, value: str) -> bool:
        if flag in v:
            v[v.index(flag) + 1] = value
            return True
        return False

    if gq is not None and not set_after("-global_quality", str(gq)):
        warnings.append(f"--gq ignored (no -global_quality in profile '{profile.name}')")
    if crf is not None and not set_after("-crf", str(crf)):
        warnings.append(f"--crf ignored (no -crf in profile '{profile.name}')")
    if preset is not None and not set_after("-preset", str(preset)):
        warnings.append(f"--preset ignored (no -preset in profile '{profile.name}')")
    if scale is not None:
        if "-vf" in v:
            v[v.index("-vf") + 1] = f"scale=-2:{scale}"
        else:
            v += ["-vf", f"scale=-2:{scale}"]

    return replace(profile, vargs=v), warnings
