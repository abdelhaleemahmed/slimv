"""slimv command-line interface."""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .console import console, make_table
from .ffmpeg import ToolError, has_encoder
from .profiles import PROFILES, ORDER
from .util import parse_duration


def duration_arg(text: str) -> int:
    """argparse type: accept a duration in seconds or minutes (90, 30s, 2m,
    1m30s, 1:30)."""
    try:
        return parse_duration(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))


_DUR_HELP = "accepts seconds or minutes: 90, 30s, 2m, 1m30s, or 1:30"


def _show_profiles() -> int:
    console.print(
        "[bold cyan]slimv encoding profiles[/bold cyan]\n"
        "[dim]All keep resolution/framerate/pixel-format; audio -> AAC 128k. "
        "Lower CRF/quality number = higher quality = bigger file.[/dim]\n"
    )
    for key in ORDER:
        p = PROFILES[key]
        avail = "[green]available[/green]" if has_encoder(p.codec) else "[red]not available[/red]"
        console.print(f"[bold]{key}[/bold]  [dim]({p.codec})[/dim]  {avail}")
        console.print(f"    quality: {p.quality}")
        console.print(f"    speed  : {p.speed}    size: {p.size}")
        console.print(f"    use    : {p.when}")
        console.print(f"    ffmpeg : [dim]{' '.join(p.vargs)}[/dim]\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slimv",
        description="slimv — shrink video files without losing visible quality "
                    "(an ffmpeg-driven analysis & re-encoding toolkit).",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"slimv {__version__} By:Ahmed Abdelhaleem Email: ahmedhal@gmail.com")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("hwcheck", help="show GPUs/encoders and how to confirm hardware use")
    sub.add_parser("profiles", help="list the encoding profiles with explanations")

    a = sub.add_parser("analyze", help="inspect a file/folder and recommend a profile")
    a.add_argument("path", help="video file or folder (searched recursively)")
    a.add_argument("--measure", action="store_true",
                   help="sample-encode a spread of files and project the REAL saving "
                        "on this content (instead of a fixed estimate)")
    a.add_argument("--sample-length", dest="sample_length", type=duration_arg, default=30,
                   metavar="DUR", help=f"per-sample length for --measure ({_DUR_HELP})")

    c = sub.add_parser("check", help="health scan: codecs, corrupted files, stats")
    c.add_argument("path", help="video file or folder (searched recursively)")
    c.add_argument("--quick", action="store_true",
                   help="ffprobe only; skip the full-decode integrity pass")
    c.add_argument("--list", dest="list_all", action="store_true",
                   help="list every file, not just problems")

    t = sub.add_parser("test", help="encode+decode sanity test for one encoder")
    t.add_argument("encoder", help="encoder name, e.g. hevc_qsv, libx265, hevc_nvenc")

    b = sub.add_parser("benchmark", help="VMAF quality/size comparison on a sample")
    b.add_argument("file", help="a representative video file")
    b.add_argument("--start", type=duration_arg, default=60, metavar="DUR",
                   help=f"sample start (default 60s; {_DUR_HELP})")
    b.add_argument("--length", type=duration_arg, default=30, metavar="DUR",
                   help=f"sample length (default 30s; {_DUR_HELP})")

    ey = sub.add_parser("eyeball", help="write original+profile sample clips to a folder to watch")
    ey.add_argument("path", help="a video file, or a folder (samples its largest file)")
    ey.add_argument("--start", type=duration_arg, default=60, metavar="DUR",
                    help=f"sample start (default 60s; {_DUR_HELP})")
    ey.add_argument("--length", type=duration_arg, default=30, metavar="DUR",
                    help=f"sample length (default 30s; {_DUR_HELP})")
    ey.add_argument("--out", default=None,
                    help="output folder for the clips (default: ./slimv_eyeball/<file>)")
    ey.add_argument("--profiles", default=None,
                    help="comma-separated profile names (default: the practical candidates)")

    ds = sub.add_parser("downscale-test", help="measure the size + quality cost of downscaling")
    ds.add_argument("file", help="a representative video file")
    ds.add_argument("--scale", type=int, default=720, help="target height, e.g. 720 (default 720)")
    ds.add_argument("--profile", default="qsv-hq", help="encode profile to test (default qsv-hq)")
    ds.add_argument("--start", type=duration_arg, default=60, metavar="DUR",
                    help=f"sample start (default 60s; {_DUR_HELP})")
    ds.add_argument("--length", type=duration_arg, default=30, metavar="DUR",
                    help=f"sample length (default 30s; {_DUR_HELP})")
    ds.add_argument("--out", default=None,
                    help="output folder for the clips (default: ./slimv_downscale/<file>)")

    rn = sub.add_parser("rename", help="bulk-remove a text fragment from filenames (dry-run by default)")
    rn.add_argument("folder", help="folder to scan")
    rn.add_argument("text", help="exact text to remove from each filename")
    rn.add_argument("-r", "--recursive", action="store_true", help="include sub-folders")
    rn.add_argument("--ext", action="append", default=[], metavar="EXT",
                    help="only these extensions (repeatable), e.g. --ext .mp4")
    rn.add_argument("--ignore-case", dest="ignore_case", action="store_true",
                    help="match the text case-insensitively")
    rn.add_argument("--tidy", action="store_true",
                    help="collapse double spaces and trim stray -_. left behind")
    rn.add_argument("--apply", action="store_true", help="actually rename (default: dry-run)")

    rc = sub.add_parser("recommend", help="analysis mode: benchmark, then pick the best profile")
    rc.add_argument("file", help="a representative video file")
    rc.add_argument("--start", type=duration_arg, default=60, metavar="DUR",
                    help=f"sample start (default 60s; {_DUR_HELP})")
    rc.add_argument("--length", type=duration_arg, default=30, metavar="DUR",
                    help=f"sample length (default 30s; {_DUR_HELP})")
    rc.add_argument("--out", default=None, help="destination folder to print in the encode command")
    rc.add_argument("--min-vmaf", type=float, default=90.0, help="quality floor (default 90)")
    rc.add_argument("--vmaf-tol", type=float, default=2.0,
                    help="VMAF gap from the best still counted as transparent (default 2.0)")

    e = sub.add_parser("encode", help="batch re-encode a tree (mirrored, verified, logged)")
    e.add_argument("src", help="source folder")
    e.add_argument("dst", help="destination folder (mirrors source tree)")
    e.add_argument("--profile", default="qsv", help="profile name (default: qsv)")
    e.add_argument("--skip", type=int, default=0, help="skip the first N files")
    e.add_argument("--limit", type=int, default=None, help="encode at most N files")
    e.add_argument("--audio-kbps", type=int, default=128, help="AAC audio bitrate (default 128)")
    e.add_argument("--keep-smaller", action="store_true",
                   help="if a re-encode isn't smaller than its source, keep the original instead")
    e.add_argument("--gq", type=int, default=None,
                   help="override global_quality (QSV profiles); lower = higher quality")
    e.add_argument("--crf", type=int, default=None,
                   help="override CRF (x265/AV1 profiles); lower = higher quality")
    e.add_argument("--preset", default=None, help="override the encoder preset")
    e.add_argument("--scale", type=int, default=None,
                   help="downscale to this height, e.g. --scale 720 (keeps aspect)")
    e.add_argument("--hwdec", default=None,
                   help="decode the source on a GPU instead of the CPU, freeing the CPU "
                        "for other work: 'qsv' (Intel iGPU, full GPU pipeline), 'cuda', "
                        "'d3d11va'. Note: does not speed up an encode-bound job — it frees "
                        "the CPU. Use with non-scaling profiles.")
    e.add_argument("--copy-audio", dest="copy_audio", action="store_true",
                   help="copy the source audio stream instead of re-encoding to AAC. Use "
                        "when the source audio is already AAC at a fine bitrate — avoids "
                        "wasted CPU and a needless lossy re-encode (identical audio out).")

    v = sub.add_parser("verify", help="confirm outputs are complete & intact before deleting sources")
    v.add_argument("src", help="source folder, OR a single source file")
    v.add_argument("dst", help="destination folder, OR (when src is a file) the output "
                              "file path or a folder to look in")
    v.add_argument("--tol", type=float, default=1.0, help="duration tolerance seconds (default 1.0)")
    v.add_argument("--quick", action="store_true", help="skip the full-decode integrity pass")
    v.add_argument("--full", action="store_true",
                   help="force a complete re-verify, ignoring cached verdicts "
                        "(default: reuse unchanged outputs that already passed)")
    v.add_argument("--hwaccel", default=None,
                   help="hardware decoder for the integrity pass, e.g. 'qsv' (Intel iGPU, "
                        "~4x faster), 'cuda' (NVIDIA), 'd3d11va'. Default: CPU software decode "
                        "(safest for the deletion gate)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "hwcheck":
            from . import hardware
            return hardware.run()
        if args.command == "profiles":
            return _show_profiles()
        if args.command == "analyze":
            from . import analyze
            return analyze.run(args.path, measure=args.measure,
                               sample_length=args.sample_length)
        if args.command == "check":
            from . import check
            return check.run(args.path, quick=args.quick, list_all=args.list_all)
        if args.command == "test":
            from . import sanity
            return sanity.run(args.encoder)
        if args.command == "benchmark":
            from . import benchmark
            return benchmark.run(args.file, start=args.start, length=args.length)
        if args.command == "eyeball":
            from . import eyeball
            profs = [p.strip() for p in args.profiles.split(",")] if args.profiles else None
            return eyeball.run(args.path, start=args.start, length=args.length,
                               out=args.out, profiles=profs)
        if args.command == "downscale-test":
            from . import downscale
            return downscale.run(args.file, start=args.start, length=args.length,
                                 scale=args.scale, profile=args.profile, out=args.out)
        if args.command == "rename":
            from . import rename
            return rename.run(args.folder, args.text, recursive=args.recursive,
                              exts=args.ext, ignore_case=args.ignore_case,
                              tidy=args.tidy, apply=args.apply)
        if args.command == "recommend":
            from . import recommend
            return recommend.run(args.file, start=args.start, length=args.length,
                                 out=args.out, min_vmaf=args.min_vmaf, vmaf_tol=args.vmaf_tol)
        if args.command == "encode":
            from . import encode
            return encode.run(args.src, args.dst, args.profile,
                              skip=args.skip, limit=args.limit, audio_kbps=args.audio_kbps,
                              keep_smaller=args.keep_smaller,
                              gq=args.gq, crf=args.crf, preset=args.preset, scale=args.scale,
                              hwdec=args.hwdec, copy_audio=args.copy_audio)
        if args.command == "verify":
            from . import verify
            return verify.run(args.src, args.dst, tol=args.tol, quick=args.quick,
                              resume=not args.full, hwaccel=args.hwaccel)
    except ToolError as exc:
        console.print(f"[red]{exc}[/red]")
        return 3
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        return 130

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
