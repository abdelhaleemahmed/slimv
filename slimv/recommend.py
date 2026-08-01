"""`slimv recommend <file>` — slimv's analysis mode: run the benchmark, then
apply a decision rule to pick the best profile automatically and print the exact
``encode`` command to run.

This automates the judgement made by hand in the case study (see the docs):
hold quality first, then prefer the smallest file — but when a
hardware encoder reaches effectively the same quality at a competitive size and
is much faster, take it, because it frees the CPU and any discrete GPU.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ffmpeg
from .benchmark import measure, results_table, Result
from .console import console
from .profiles import PROFILES


@dataclass
class Decision:
    winner: str
    reason: str
    smallest: str
    acceptable: list[str]


def decide(results: list[Result], min_vmaf: float = 90.0, vmaf_tol: float = 2.0,
           size_slack: float = 0.15, speed_factor: float = 1.5) -> Decision:
    """Pick the best profile from measured results.

    The rule, in order:

    1. **Quality gate.** A profile is *acceptable* only if its VMAF is within
       ``vmaf_tol`` of the best score AND at or above ``min_vmaf``. (With no VMAF
       data, every profile is treated as acceptable and the choice falls to size
       and speed.)
    2. **Smallest by default.** Among acceptable profiles, the smallest file
       wins — the "smaller is better, never at quality's expense" rule.
    3. **Hardware tie-break.** If a hardware-accelerated acceptable profile is
       within ``size_slack`` of the smallest and at least ``speed_factor`` times
       faster, it wins instead: the quality is indistinguishable, the size cost
       is small, and it runs on otherwise-idle silicon.

    Args:
        results: Measured profiles from :func:`slimv.benchmark.measure`.
        min_vmaf: Absolute quality floor.
        vmaf_tol: How far below the best VMAF still counts as transparent.
        size_slack: Fractional size headroom a hardware encoder may use and
            still win the tie-break (0.15 = up to 15% larger than the smallest).
        speed_factor: How much faster a hardware encoder must be to win it.

    Returns:
        A :class:`Decision` naming the winner and the reasoning.
    """
    scored = [r for r in results if r.vmaf is not None]
    if scored:
        best = max(r.vmaf for r in scored)
        acceptable = [r for r in scored
                      if r.vmaf >= best - vmaf_tol and r.vmaf >= min_vmaf]
        if acceptable:
            quality_note = (f"all within {vmaf_tol:.1f} VMAF of the best "
                            f"({best:.2f}) and ≥ {min_vmaf:.0f}")
        else:
            # NOTHING clears the absolute floor. This is typical for line-art /
            # text / equation / screen content, where VMAF reads several points
            # low even when it looks fine. Do NOT fall back to "highest VMAF"
            # (that picks a bloated encoder for a tiny, possibly-meaningless
            # gain). Instead drop the floor, keep the *relative* tolerance, take
            # the smallest in that band, and tell the user to verify by eye.
            acceptable = [r for r in scored if r.vmaf >= best - vmaf_tol]
            quality_note = (f"NONE cleared the {min_vmaf:.0f} VMAF floor "
                            f"(best {best:.2f}) — likely line-art/text content "
                            f"where VMAF under-reads; chose the smallest within "
                            f"{vmaf_tol:.1f} of the best. VERIFY BY EYE.")
    else:
        # No VMAF available: cannot judge quality, so consider everything and
        # lean on size/speed, but say so.
        acceptable = list(results)
        quality_note = "no VMAF available — chose on size/speed only (verify quality by eye)"

    smallest = min(acceptable, key=lambda r: r.size_mb)
    winner = smallest
    reason = f"smallest acceptable file ({smallest.size_mb:.2f} MB); {quality_note}"

    # hardware tie-break
    hw_candidates = [
        r for r in acceptable
        if r.hardware
        and r.size_mb <= smallest.size_mb * (1 + size_slack)
        and r.speed_xrt >= smallest.speed_xrt * speed_factor
        and r.profile != smallest.profile
    ]
    if hw_candidates:
        # fastest qualifying hardware encoder
        hw = max(hw_candidates, key=lambda r: r.speed_xrt)
        pct = (hw.size_mb / smallest.size_mb - 1) * 100
        reason = (
            f"hardware encoder at effectively the same quality, "
            f"{hw.speed_xrt / smallest.speed_xrt:.1f}× faster than the smallest "
            f"({smallest.profile}) for only {pct:+.0f}% size — runs on idle "
            f"silicon, frees CPU/GPU; {quality_note}"
        )
        winner = hw

    return Decision(
        winner=winner.profile,
        reason=reason,
        smallest=smallest.profile,
        acceptable=[r.profile for r in acceptable],
    )


def run(file: str, start: int = 60, length: int = 30, out: str | None = None,
        min_vmaf: float = 90.0, vmaf_tol: float = 2.0) -> int:
    """Benchmark ``file`` and print the recommended profile + encode command."""
    try:
        results = measure(file, start=start, length=length)
    except FileNotFoundError:
        console.print(f"[red]File not found:[/red] {file}")
        return 1
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    console.print(results_table(results, length))
    d = decide(results, min_vmaf=min_vmaf, vmaf_tol=vmaf_tol)
    win = next(r for r in results if r.profile == d.winner)

    console.print(
        f"\n[bold green]Recommended profile: {d.winner}[/bold green]  "
        f"[dim]({PROFILES[d.winner].codec})[/dim]"
    )
    vmaf_str = "n/a" if win.vmaf is None else f"{win.vmaf:.2f}"
    console.print(
        f"  VMAF {vmaf_str} · {win.size_mb:.2f} MB · {win.speed_xrt:.2f}×RT"
    )
    console.print(f"  Why: {d.reason}")
    if d.winner != d.smallest:
        console.print(f"  [dim](Smallest overall was '{d.smallest}'; "
                      f"chose '{d.winner}' for the speed/hardware win.)[/dim]")
    console.print(f"  [dim]Acceptable on quality: {', '.join(d.acceptable)}[/dim]")

    # ready-to-run encode command
    src = Path(file)
    src_dir = src.parent
    dst = out or str(src_dir) + "_slimv"
    console.print("\n[bold]To convert the whole folder with this choice:[/bold]")
    console.print(f'  slimv encode "{src_dir}" "{dst}" --profile {d.winner}')
    console.print("[dim]Then verify before deleting sources:  "
                  f'slimv verify "{src_dir}" "{dst}"[/dim]')
    return 0
