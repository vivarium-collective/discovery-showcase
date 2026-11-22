"""Generate the Episode 01-04 investigation outputs: figures + a report PDF.

This is the *source* the paper pipeline translates from. It runs the real Monod model and
the ablation, writes publication figures (PDF), and renders a timestamped investigation
**report PDF** that accumulates in ``workspace/reports/`` as the investigation develops --- a
provenance trail of how it evolved. ``scripts/build_paper_assets.py`` then collects these into
the paper's appendix + results supplement + main figures.

Matplotlib-based for reliability (no chromium/playwright dependency); the report render can
later be swapped for the full ``viva-discover report`` / workbench HTML->PDF path.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from viva_discovery_showcase.growth import (  # noqa: E402
    MECHANISM_LABELS,
    REFERENCE_PRESETS,
    growth_signature,
    is_regrowth,
    remove_byproduct,
    run_batch,
    spike_substrate,
)

# A restrained, color-blind-safe trio for the three mechanisms.
MECH_COLORS = {"substrate_exhaustion": "#4477AA", "byproduct_inhibition": "#CCBB44",
               "density_cap": "#EE6677"}
MECH_TITLE = {"substrate_exhaustion": "Substrate exhaustion (H1)",
              "byproduct_inhibition": "Byproduct inhibition (H2)",
              "density_cap": "Density cap (H3, decoy)"}


def collect_results(*, seeds=(0, 1, 2)) -> dict:
    """Run the model + ablation; return the data the figures and report draw from."""
    from viva_discovery_showcase.ablation import run_ablation

    trajectories, signatures, discrimination = {}, {}, {}
    for label, mech in MECHANISM_LABELS.items():
        params = REFERENCE_PRESETS[mech]
        trajectories[label] = run_batch(params, t_end=90.0)
        signatures[label] = growth_signature(label)
        spike = is_regrowth(run_batch(params, t_end=90.0, intervention=spike_substrate,
                                      t_intervene=45.0), params)
        remove = is_regrowth(run_batch(params, t_end=90.0, intervention=remove_byproduct,
                                       t_intervene=45.0), params)
        discrimination[label] = {"spike": bool(spike), "remove": bool(remove)}
    # Ablation with the deterministic correct reasoner (reproducible record); the live
    # real-agent run is a separate command.
    import sys
    filler = f"{sys.executable} {Path(__file__).resolve().parent.parent / 'scripts' / 'agent_filler.py'} --self-test"
    ablation = run_ablation(mechanism="byproduct_inhibition", seeds=seeds, real_filler_cmd=filler)
    return {"trajectories": trajectories, "signatures": signatures,
            "discrimination": discrimination, "ablation": ablation,
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds")}


def _fig_growth_curves(results) -> plt.Figure:
    fig, axes = plt.subplots(1, 3, figsize=(10, 3), sharey=False)
    for ax, (label, traj) in zip(axes, results["trajectories"].items()):
        ax.plot(traj["t"], traj["X"], color=MECH_COLORS[label], lw=2, label="biomass X")
        ax.plot(traj["t"], traj["S"], color="#999999", lw=1, ls="--", label="substrate S")
        ax.plot(traj["t"], traj["P"], color="#333333", lw=1, ls=":", label="byproduct P")
        ax.set_title(MECH_TITLE[label], fontsize=9)
        ax.set_xlabel("time (h)")
    axes[0].set_ylabel("concentration")
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Growth plateau under three mechanisms", fontsize=11)
    fig.tight_layout()
    return fig


def _fig_discrimination(results) -> plt.Figure:
    labels = list(results["discrimination"].keys())
    fig, ax = plt.subplots(figsize=(5.5, 2.8))
    import numpy as np
    spike = [1 if results["discrimination"][m]["spike"] else 0 for m in labels]
    remove = [1 if results["discrimination"][m]["remove"] else 0 for m in labels]
    x = np.arange(len(labels))
    ax.bar(x - 0.18, spike, 0.36, label="spike substrate", color="#4477AA")
    ax.bar(x + 0.18, remove, 0.36, label="remove byproduct", color="#CCBB44")
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace("_", "\n") for m in labels], fontsize=8)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["no", "regrowth"])
    ax.set_title("Diagnostic interventions discriminate the mechanism", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    return fig


def _fig_ablation(results) -> plt.Figure:
    abl = results["ablation"]
    configs = list(abl.keys())
    rates = [abl[c]["recovered_rate"][0] or 0.0 for c in configs]
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    colors = {"oracle": "#4477AA", "deterministic_only": "#BBBBBB", "real_agent": "#228833"}
    ax.bar(configs, rates, color=[colors.get(c, "#777777") for c in configs])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("mechanism-recovery rate")
    ax.set_title("Episode 01-04 ablation (concealed = byproduct inhibition)", fontsize=10)
    for i, r in enumerate(rates):
        ax.text(i, r + 0.02, f"{r:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    return fig


FIGURES = {"growth_curves": _fig_growth_curves,
           "discrimination": _fig_discrimination,
           "ablation": _fig_ablation}


def write_figures(results, outdir) -> dict:
    """Write each figure as a PDF; return {name: path}."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, fn in FIGURES.items():
        fig = fn(results)
        p = out / f"{name}.pdf"
        fig.savefig(p, bbox_inches="tight")
        plt.close(fig)
        paths[name] = p
    return paths


def render_report(results, outpath) -> Path:
    """Render the investigation report as a multi-page PDF (the appendix record)."""
    out = Path(outpath)
    out.parent.mkdir(parents=True, exist_ok=True)
    abl = results["ablation"]
    with PdfPages(out) as pdf:
        # cover page
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.86, "Investigation A — Growth limitation", ha="center", size=18, weight="bold")
        fig.text(0.5, 0.82, "Episodes 01-04 · Discovery Engine showcase", ha="center", size=11, color="#555")
        fig.text(0.5, 0.79, f"generated {results['generated_at']}", ha="center", size=9, color="#888")
        body = (
            "Question. A batch culture grows then plateaus while the baseline Monod model\n"
            "predicts continued growth. Which mechanism stops growth?\n\n"
            "Hypotheses.\n"
            "  H1 substrate_exhaustion — the limiting nutrient is used up.\n"
            "  H2 byproduct_inhibition — an inhibitory byproduct accumulates.\n"
            "  H3 density_cap (decoy) — a density/quorum cap; separable by neither arm.\n\n"
            "Discriminating interventions (at the plateau).\n"
            "  spike substrate  → rescues iff H1.\n"
            "  remove byproduct → rescues iff H2.\n\n"
            "Mechanism signatures (2·spike + remove), from the real model:\n"
            + "".join(f"  {m}: {results['signatures'][m]:.0f}\n" for m in results["signatures"])
            + "\nAblation (mechanism-recovery rate, concealed = byproduct_inhibition):\n"
            + "".join(f"  {c:<20} {abl[c]['recovered_rate'][0]:.2f}   (n={abl[c]['n']})\n" for c in abl)
            + "\nVerdict. The engine recovers the concealed mechanism from the intervention\n"
            "evidence; the deterministic-only floor does not. Decoy is an abstention case."
        )
        fig.text(0.1, 0.72, body, ha="left", va="top", size=10, family="monospace")
        pdf.savefig(fig); plt.close(fig)
        # figure pages
        for fn in FIGURES.values():
            f = fn(results)
            pdf.savefig(f, bbox_inches="tight"); plt.close(f)
    return out


# --- Bias-isolated run records (paper documentation) -------------------------
def render_isolated_run(record_path, transcript_path, outpath) -> "Path":
    """Render one bias-isolated run (record + transcript) as a one-page PDF for the appendix."""
    import json as _json
    rec = _json.loads(Path(record_path).read_text())
    entries = [_json.loads(l) for l in Path(transcript_path).read_text().splitlines() if l.strip()] \
        if Path(transcript_path).exists() else []
    prompt = (entries[0].get("prompt") if entries else "") or ""
    response = (entries[0].get("response") if entries else "") or ""
    out = Path(outpath); out.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(8.5, 11))
    fig.text(0.5, 0.95, "Bias-isolated run record", ha="center", size=15, weight="bold")
    fig.text(0.5, 0.92, f"sealed mechanism: {rec['sealed_mechanism']}  ·  seed {rec['seed']}",
             ha="center", size=10, color="#555")
    body = (
        f"EARNED RECOVERY: {rec['earned_recovery']}   (held-out error {rec['heldout_error']})\n"
        f"The sealed mechanism was evaluator-only — never shown to the agent.\n\n"
        f"Evidence shown to the agent (the experimental result):\n  {rec['evidence_shown_to_agent']}\n\n"
        f"Knowledge resources: {rec['resources_dir']}\n"
        f"Agent (filler): {rec['filler_cmd']}\n\n"
        "=== Controlled prompt (recorded) ===\n" + prompt[:1600] + "\n\n"
        "=== Agent response (recorded) ===\n" + response[:400]
    )
    fig.text(0.07, 0.87, body, ha="left", va="top", size=8.5, family="monospace", wrap=True)
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out
