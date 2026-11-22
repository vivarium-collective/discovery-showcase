#!/usr/bin/env python
"""Run spatio-flux's spatial dFBA colony through the showcase core and render snapshots.

A real viva-ecosystem multiscale method (needs the ``spatial`` extra: ``uv pip install -e ".[spatial]"``).
``spatial_many_dfba`` runs its own dFBA (FBA metabolism) at every lattice site over local glucose,
acetate, and biomass, with diffusion between sites --- metabolism + space in one composite the
engine discovers (``discover_generators`` lists ``spatio_flux.composites.spatial.*``). This renders
field snapshots over time (glucose, biomass, acetate) into the paper figures.
"""
from __future__ import annotations

import argparse
import importlib
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

PAPER = Path.home() / "Desktop" / "PLOS_Discovery_Engine" / "versions" / "v1" / "figures"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bins", type=int, default=12, help="grid size (NxN)")
    ap.add_argument("--times", type=int, nargs="+", default=[0, 5, 10, 20])
    ap.add_argument("--out", default=str(PAPER / "fig_spatial_dfba.pdf"))
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from process_bigraph import Composite
    from spatio_flux.composites.spatial import spatial_many_dfba

    core = importlib.import_module("viva_discovery_showcase.core").build_core()
    comp = Composite({"state": spatial_many_dfba(core, n_bins=[a.bins, a.bins])}, core=core)

    def grab():
        f = comp.state["fields"]
        return {k: np.array(f[k], dtype=float) for k in ("glucose", "dissolved biomass", "acetate")}

    snaps, t_prev = {}, 0
    for t in a.times:
        if t > t_prev:
            comp.run(t - t_prev); t_prev = t
        snaps[t] = grab()

    rows = [("glucose", "Glucose (substrate)", "viridis"),
            ("dissolved biomass", "Biomass", "magma"),
            ("acetate", "Acetate (byproduct)", "cividis")]
    fig, axes = plt.subplots(len(rows), len(a.times), figsize=(2.2 * len(a.times), 2.2 * len(rows)))
    for r, (key, label, cmap) in enumerate(rows):
        vmax = max(snaps[t][key].max() for t in a.times) or 1.0
        for c, t in enumerate(a.times):
            ax = axes[r, c]
            ax.imshow(snaps[t][key], cmap=cmap, vmin=0, vmax=vmax, origin="upper")
            ax.set_xticks([]); ax.set_yticks([])
            if r == 0:
                ax.set_title(f"t={t}", fontsize=9)
            if c == 0:
                ax.set_ylabel(label, fontsize=9)
    fig.suptitle("Spatial dFBA colony (spatio-flux): metabolism + diffusion across a lattice", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight"); fig.savefig(out.with_suffix(".png"), dpi=120, bbox_inches="tight")
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
