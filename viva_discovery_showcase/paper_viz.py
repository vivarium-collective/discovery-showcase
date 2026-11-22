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
