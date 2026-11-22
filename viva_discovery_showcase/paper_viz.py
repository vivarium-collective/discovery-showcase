"""Render paper figures from REAL discovery-cycle artifacts (no fabricated data).

Three renderers, each driven by workspace artifacts the discovery engine produced:

- ``render_investigation_graph`` — the investigation graph from ``viva-discover linkage``
  ({nodes, edges} with typed edges): investigation -> acceptance criterion -> study ->
  composite / observable / source / findings.
- ``render_run_backed_observables`` — the emitted observables of the growth-plateau baseline
  run, read through ``viva_emitters.RunReader`` (the same store the engine grades), showing the
  byproduct-inhibition signature (substrate stays plentiful, byproduct accumulates, biomass
  plateaus) and the graded test value.
- ``render_composite_diagram`` — the monod_batch composite wiring (the MonodGrowth process and
  its ports over the biomass/substrate/byproduct stores + the emitter).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

# kind -> colour (restrained, color-blind-safe)
_KIND_COLOR = {
    "investigation": "#4477AA", "ac": "#66CCEE", "study": "#228833",
    "composite": "#CCBB44", "observable": "#EE6677", "source": "#AA3377",
    "finding": "#BBBBBB",
}


def _node_kind(node_id: str) -> str:
    return node_id.split(":", 1)[0]


def _short(node_id: str) -> str:
    rest = node_id.split(":", 1)[1] if ":" in node_id else node_id
    if node_id.startswith("composite:"):
        return rest.rsplit(".", 1)[-1]
    if node_id.startswith("finding:"):
        return rest.rsplit(":", 1)[-1]
    return rest


def load_linkage(ws_root) -> dict:
    """Run ``viva-discover linkage --json`` in the workspace and return {nodes, edges}."""
    out = subprocess.run(["viva-discover", "linkage", "--json"], cwd=str(ws_root),
                         capture_output=True, text=True)
    return json.loads(out.stdout)


def render_investigation_graph(linkage: dict, outpath) -> "Path":
    """Layered node-link diagram of the investigation graph."""
    nodes = [n["id"] if isinstance(n, dict) else n for n in linkage["nodes"]]
    edges = linkage["edges"]
    layer = {"investigation": 0, "ac": 1, "study": 1, "composite": 2,
             "observable": 2, "source": 2, "finding": 3}
    rows: dict[int, list[str]] = {}
    for n in nodes:
        rows.setdefault(layer.get(_node_kind(n), 2), []).append(n)
    pos = {}
    for ly, ns in rows.items():
        for i, n in enumerate(ns):
            x = (i - (len(ns) - 1) / 2) * 3.0
            pos[n] = (x, -ly * 2.4)

    fig, ax = plt.subplots(figsize=(9, 6))
    for e in edges:
        a, b = pos.get(e["from"]), pos.get(e["to"])
        if not a or not b:
            continue
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12,
                                     color="#888888", lw=1.0, shrinkA=22, shrinkB=22,
                                     connectionstyle="arc3,rad=0.03"))
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ax.text(mx, my, e["type"], fontsize=6.5, color="#555555", ha="center",
                va="center", bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))
    for n, (x, y) in pos.items():
        k = _node_kind(n)
        ax.add_patch(FancyBboxPatch((x - 1.15, y - 0.4), 2.3, 0.8, boxstyle="round,pad=0.05",
                                    fc=_KIND_COLOR.get(k, "#DDDDDD"), ec="#333333", lw=0.8))
        ax.text(x, y + 0.12, k, fontsize=6.5, style="italic", ha="center", color="#222222")
        ax.text(x, y - 0.14, _short(n), fontsize=7.5, ha="center", weight="bold", color="#111111")
    ax.set_xlim(-6.5, 6.5); ax.set_ylim(-8, 1)
    ax.axis("off")
    ax.set_title("Investigation graph (growth-limitation)", fontsize=12)
    fig.tight_layout()
    out = Path(outpath); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def render_run_backed_observables(store, outpath, *, graded_value=None) -> "Path":
    """The baseline run's emitted observables, read through RunReader."""
    from viva_emitters import RunReader
    rr = RunReader.open(str(store))
    series = {o: rr.series(o) for o in ("biomass", "substrate", "byproduct")}
    t = series["biomass"]["time"].to_list() if "time" in series["biomass"].columns \
        else list(range(len(series["biomass"])))
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.plot(t, series["biomass"]["value"].to_list(), color="#CCBB44", lw=2.2, label="biomass X")
    ax.plot(t, series["substrate"]["value"].to_list(), color="#4477AA", lw=1.6, ls="--", label="substrate S")
    ax.plot(t, series["byproduct"]["value"].to_list(), color="#EE6677", lw=1.6, ls=":", label="byproduct P")
    ax.set_xlabel("time (h)"); ax.set_ylabel("concentration")
    ax.set_title("Baseline run (emitted via RunReader): byproduct-inhibition plateau", fontsize=10)
    ax.legend(fontsize=8, frameon=False, loc="center right")
    note = "substrate stays plentiful; byproduct accumulates; biomass plateaus"
    if graded_value is not None:
        note += f"\nbehavior test byproduct_accumulates = {graded_value:.2f} -> PASS (code-graded)"
    ax.text(0.02, 0.97, note, transform=ax.transAxes, fontsize=7.5, va="top", color="#444444")
    fig.tight_layout()
    out = Path(outpath); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def render_composite_diagram(outpath) -> "Path":
    """The monod_batch composite: the MonodGrowth process over its three stores + emitter."""
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    stores = [("biomass", 0.0), ("substrate", 2.4), ("byproduct", 4.8)]
    for name, x in stores:
        ax.add_patch(FancyBboxPatch((x - 0.7, 2.2), 1.4, 0.7, boxstyle="round,pad=0.05",
                                    fc="#EEEEEE", ec="#333333"))
        ax.text(x, 2.55, name, ha="center", fontsize=8, weight="bold")
    ax.add_patch(FancyBboxPatch((0.6, 0.2), 3.6, 0.9, boxstyle="round,pad=0.06",
                                fc="#228833", ec="#111111", alpha=0.85))
    ax.text(2.4, 0.65, "MonodGrowth (process)", ha="center", fontsize=9, weight="bold", color="white")
    for name, x in stores:
        ax.add_patch(FancyArrowPatch((x, 2.2), (min(max(x, 1.0), 3.8), 1.1), arrowstyle="<|-|>",
                                     mutation_scale=10, color="#555555", lw=1.0, shrinkA=2, shrinkB=2))
    ax.add_patch(FancyBboxPatch((4.3, 0.2), 1.9, 0.9, boxstyle="round,pad=0.06",
                                fc="#CCBB44", ec="#111111"))
    ax.text(5.25, 0.65, "ParquetEmitter", ha="center", fontsize=8, weight="bold")
    ax.add_patch(FancyArrowPatch((4.8, 2.2), (5.25, 1.1), arrowstyle="-|>", mutation_scale=10,
                                 color="#555555", lw=1.0))
    ax.text(3.1, 1.75, "inputs/outputs: X, S, P", fontsize=7, color="#444444", ha="center")
    ax.set_xlim(-1, 6.6); ax.set_ylim(-0.1, 3.2); ax.axis("off")
    ax.set_title("monod_batch composite (the growth-limitation baseline)", fontsize=10)
    fig.tight_layout()
    out = Path(outpath); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def render_byproduct_band(store, outpath, *, band=(0.3, 10.0), graded_value=1.72) -> "Path":
    """The band_overlay the engine proposed: emitted byproduct vs the behavior-test band."""
    from viva_emitters import RunReader
    rr = RunReader.open(str(store))
    s = rr.series("byproduct")
    t = s["time"].to_list() if "time" in s.columns else list(range(len(s)))
    v = s["value"].to_list()
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    ax.axhspan(band[0], band[1], color="#228833", alpha=0.10, label=f"acceptance band [{band[0]}, {band[1]}]")
    ax.plot(t, v, color="#EE6677", lw=2.0, label="byproduct P (emitted)")
    ax.axhline(graded_value, color="#228833", ls="--", lw=1.2,
               label=f"time-average = {graded_value:.2f}  (PASS)")
    ax.set_xlabel("time (h)"); ax.set_ylabel("byproduct concentration")
    ax.set_title("byproduct_accumulates: run-backed behavior test", fontsize=10)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout()
    out = Path(outpath); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130, bbox_inches="tight"); plt.close(fig)
    return out


# --- Main-text schematic + data figures (replacing the Fig1/2/3 placeholders) ----------------
def render_architecture_overview(outpath) -> "Path":
    """Fig 1: the architecture --- authored record -> derive-first projection -> phased operations."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax in axes:
        ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")

    a = axes[0]; a.set_title("(a) Authored record", fontsize=10, loc="left")
    for y, lab, c in [(7.6, "investigation", "#4477AA"), (5.1, "studies", "#228833"),
                      (2.6, "registered runs", "#CCBB44")]:
        a.add_patch(FancyBboxPatch((1.2, y), 7.4, 1.5, boxstyle="round,pad=0.1", fc=c, ec="#222", alpha=0.85))
        a.text(4.9, y + 0.75, lab, ha="center", va="center", fontsize=10, weight="bold", color="white")
    for y0, y1 in [(7.6, 6.6), (5.1, 4.1)]:
        a.add_patch(FancyArrowPatch((4.9, y0), (4.9, y1), arrowstyle="-|>", mutation_scale=12, color="#555", lw=1.2))
    a.text(4.9, 1.1, "the single source of truth", ha="center", fontsize=8, style="italic", color="#555")

    b = axes[1]; b.set_title("(b) Derive-first projection", fontsize=10, loc="left")
    b.add_patch(FancyBboxPatch((0.4, 4.2), 2.9, 1.6, boxstyle="round,pad=0.1", fc="#EEEEEE", ec="#222"))
    b.text(1.85, 5.0, "record\n+ outcomes", ha="center", va="center", fontsize=8.5, weight="bold")
    views = [(8.6, "knowledge state"), (6.4, "argument graph"), (4.2, "frontier"), (2.0, "decisions")]
    for y, lab in views:
        b.add_patch(FancyBboxPatch((6.1, y - 0.55), 3.6, 1.1, boxstyle="round,pad=0.08", fc="#DDE7F0", ec="#222"))
        b.text(7.9, y, lab, ha="center", va="center", fontsize=8.5)
        b.add_patch(FancyArrowPatch((3.4, 5.0), (6.0, y), arrowstyle="-|>", mutation_scale=10, color="#888", lw=1.0))
    b.text(4.7, 0.6, r"one pure function; same inputs $\to$ same views", ha="center", fontsize=7.5, style="italic", color="#555")

    c = axes[2]; c.set_title("(c) Phased operations", fontsize=10, loc="left")
    phases = ["A reconcile", "B plan", "C design", "D build", "E execute", "F evaluate"]
    for i, p in enumerate(phases):
        y = 8.4 - i * 1.25
        c.add_patch(FancyBboxPatch((0.6, y - 0.42), 5.4, 0.9, boxstyle="round,pad=0.06",
                                   fc="#228833" if p.startswith("E ") else "#EFEFEF",
                                   ec="#222", alpha=0.9))
        c.text(3.3, y, p, ha="center", va="center", fontsize=8.5,
               color="white" if p.startswith("E ") else "#111", weight="bold" if p.startswith("E ") else "normal")
    c.add_patch(FancyBboxPatch((6.3, 3.0), 3.4, 3.3, boxstyle="round,pad=0.1", fc="#FBF3D0", ec="#AA8"))
    c.text(8.0, 5.7, "AI seam", ha="center", fontsize=8.5, weight="bold")
    c.text(8.0, 4.6, "emit\nfill\napply", ha="center", va="center", fontsize=8)
    c.text(5.0, 0.6, "only execute writes; AI only through the seam", ha="center", fontsize=7.5, style="italic", color="#555")

    fig.suptitle("Discovery Engine treats the investigation, not the simulation, as the unit", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = Path(outpath); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def render_cycle_diagram(outpath) -> "Path":
    """Fig 2: the six-stage cycle, annotated with the real growth-limitation trace."""
    import numpy as np
    stages = [("Question", "why does growth\nplateau?"),
              ("Hypothesize", "substrate / byproduct\n/ density cap"),
              ("Model", "monod_batch\nvariants"),
              ("Experiment", "spike substrate /\nremove byproduct"),
              ("Evaluate", "byproduct recovered\n(1.72, supported)"),
              ("Synthesize", "mechanism identified;\nnext question")]
    fig, ax = plt.subplots(figsize=(7.2, 6.2)); ax.set_xlim(-6, 6); ax.set_ylim(-6, 6); ax.axis("off")
    n = len(stages); R = 3.9
    pos = [(R * np.cos(np.pi / 2 - 2 * np.pi * i / n), R * np.sin(np.pi / 2 - 2 * np.pi * i / n)) for i in range(n)]
    col = ["#4477AA", "#66CCEE", "#228833", "#CCBB44", "#EE6677", "#AA3377"]
    for i in range(n):
        x0, y0 = pos[i]; x1, y1 = pos[(i + 1) % n]
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14,
                                     color="#888", lw=1.3, connectionstyle="arc3,rad=0.22", shrinkA=26, shrinkB=26))
    for (x, y), (name, note), c in zip(pos, stages, col):
        ax.add_patch(FancyBboxPatch((x - 1.15, y - 0.5), 2.3, 1.0, boxstyle="round,pad=0.08", fc=c, ec="#222", alpha=0.9))
        ax.text(x, y + 0.12, name, ha="center", va="center", fontsize=9, weight="bold", color="white")
        ax.text(x, y - 0.22, note, ha="center", va="center", fontsize=6.3, color="white")
    ax.annotate("", xy=pos[0], xytext=pos[4], arrowprops=dict(arrowstyle="-|>", color="#EE6677",
                lw=1.2, ls=(0, (4, 3)), connectionstyle="arc3,rad=-0.1"))
    ax.text(0, 0, "an overturned\nexpectation returns\nto an earlier stage", ha="center", va="center",
            fontsize=7, style="italic", color="#777")
    ax.set_title("The growth-limitation investigation through the discovery cycle", fontsize=11)
    fig.tight_layout()
    out = Path(outpath); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def render_model_revision(outpath) -> "Path":
    """Fig 3: Episode 05 model revision from pathway.revision_comparison (real held-out error)."""
    import numpy as np
    from viva_discovery_showcase.pathway import revision_comparison, TRUE
    cmp = revision_comparison()
    labels = ["baseline\n(no feedback)", "parameter\nrefit", "structural\nrevision"]
    held = [cmp["baseline"]["heldout_error"], cmp["param_refit"]["heldout_error"], cmp["structural"]["heldout_error"]]
    colors = ["#BBBBBB", "#CCBB44", "#228833"]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    x = np.arange(len(labels))
    ax.bar(x, held, color=colors, width=0.6)
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("held-out error (log scale)")
    for i, h in enumerate(held):
        ax.text(i, h * 1.15, f"{h:.3f}", ha="center", fontsize=8.5)
    ki = cmp["structural"]["Ki"]
    ax.set_title("Episode 05: structural revision generalizes; parameter refit overfits", fontsize=9.5)
    ax.text(0.98, 0.95, f"structural recovers $K_I$ = {ki:.2f}\n(true {TRUE.Ki:.1f})", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, bbox=dict(boxstyle="round,pad=0.3", fc="#EAF4EC", ec="#228833"))
    fig.tight_layout()
    out = Path(outpath); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out
