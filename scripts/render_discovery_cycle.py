#!/usr/bin/env python
"""Render the discovery-cycle visual grammar on a real investigation.

The six scientific stages --- Question, Hypothesize, Model, Experiment, Evaluate, Synthesize --- are
the interpretive structure of the paper, distinct from the engine's execution phases A--F, its four
controller responsibilities, and the emit--fill--apply boundary. This draws the cycle as a ring and
annotates each stage with what the growth-limitation investigation actually does there and the engine
record it writes, so the investigation --- not a single simulation --- is the visible unit of progress.
The arrow from Synthesize back to Question shows the cycle reopening with a new question.
"""
from __future__ import annotations

import argparse
from pathlib import Path

PAPER = Path.home() / "Desktop" / "PLOS_Discovery_Engine" / "versions" / "v1" / "figures"

STAGES = [
    ("Question", "Why does the batch\nculture stop growing?", "opens a frontier item"),
    ("Hypothesize", "three mechanisms:\nsubstrate exhaustion,\nbyproduct inhibition,\ndensity cap", "typed hypotheses\n+ predictions"),
    ("Model", "monod_batch composite\n(MonodGrowth process)", "content-addressed\nmodel version"),
    ("Experiment", "two diagnostic interventions:\nspike substrate,\nremove byproduct", "sanctioned runs,\nregistered"),
    ("Evaluate", "byproduct accumulates\n(graded by code);\nagent recovers mechanism", "verdict earned\nfrom the run"),
    ("Synthesize", "plateau is byproduct\ninhibition; does it hold\nacross scales?", "finding + a new\nquestion"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(PAPER / "fig_discovery_cycle.pdf"))
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    n = len(STAGES)
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    ax.set_xlim(-1.45, 1.45); ax.set_ylim(-1.35, 1.35); ax.axis("off")
    R = 1.0
    ang = [np.pi / 2 - 2 * np.pi * i / n for i in range(n)]  # clockwise from top
    pos = [(R * np.cos(t), R * np.sin(t)) for t in ang]
    cyc = ["#1b2a4a", "#2a6f97", "#5a189a", "#2a9d8f", "#2d6a4f", "#9d4e15"]

    # arrows between consecutive stages (the cycle)
    for i in range(n):
        x0, y0 = pos[i]; x1, y1 = pos[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L = np.hypot(dx, dy); ux, uy = dx / L, dy / L
        closing = (i == n - 1)
        a_patch = FancyArrowPatch((x0 + 0.26 * ux, y0 + 0.26 * uy), (x1 - 0.26 * ux, y1 - 0.26 * uy),
                                  connectionstyle="arc3,rad=-0.18", arrowstyle="-|>", mutation_scale=16,
                                  lw=1.6, color="#bc4749" if closing else "#adb5bd",
                                  linestyle="--" if closing else "-", zorder=1)
        ax.add_patch(a_patch)

    for (name, content, record), (x, y), c in zip(STAGES, pos, cyc):
        ax.add_patch(plt.Circle((x, y), 0.235, color=c, zorder=3))
        ax.text(x, y, name, ha="center", va="center", color="white", fontsize=9.5,
                fontweight="bold", zorder=4)
        # content box, pushed radially outward
        rx, ry = x * 1.0, y * 1.0
        ox, oy = x / max(abs(x), abs(y), 0.4), y / max(abs(x), abs(y), 0.4)
        tx, ty = x + 0.34 * np.sign(x if abs(x) > 0.2 else 1), y + 0.34 * np.sign(y if abs(y) > 0.2 else 1)
        ha = "left" if x > 0.2 else ("right" if x < -0.2 else "center")
        ax.text(x * 1.34, y * 1.42, content, ha=ha if abs(x) > 0.2 else "center",
                va="center", fontsize=7.2, color="#212529", zorder=4)
        ax.text(x * 1.34, y * 1.42, "", zorder=4)

    ax.text(0, 0.12, "discovery", ha="center", va="center", fontsize=12, color="#495057", fontweight="bold")
    ax.text(0, -0.12, "cycle", ha="center", va="center", fontsize=12, color="#495057", fontweight="bold")
    ax.text(0, -1.27, "the engine writes a typed record at every stage; Synthesize reopens the cycle (dashed)",
            ha="center", va="center", fontsize=7.5, color="#868e96", style="italic")
    fig.tight_layout()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight"); fig.savefig(out.with_suffix(".png"), dpi=130, bbox_inches="tight")
    print(f"saved {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
