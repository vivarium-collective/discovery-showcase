"""Fixture generator for the growth-limitation benchmark (Episodes 01-04).

Turns the hidden Monod reference generator (:mod:`viva_discovery_showcase.growth`)
into the concrete artifacts the engine's benchmark harness consumes:

- ``train_measurements.csv`` --- the baseline batch observation the agent sees
  (time, biomass, substrate, byproduct) showing growth then plateau;
- ``holdout_interventions.csv`` --- the held-out intervention responses used only
  to score prediction (spike-substrate / remove-byproduct / dilution), withheld
  from the agent at design time;
- ``hidden_truth.yaml`` --- evaluator-only: which mechanism actually caused the
  plateau and the generating parameters.

The agent is given the observation + the mis-specified baseline model; it must
design interventions and recover the mechanism. Scoring compares its predicted
intervention responses to ``holdout_interventions.csv`` and its named mechanism
to ``hidden_truth.yaml``.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Optional

from viva_discovery_showcase.growth import (
    REFERENCE_PRESETS,
    dilution_control,
    is_regrowth,
    remove_byproduct,
    run_batch,
    spike_substrate,
)

INTERVENTIONS = {
    "spike_substrate": spike_substrate,
    "remove_byproduct": remove_byproduct,
    "dilution_control": dilution_control,
}

# Observable columns the agent sees (biomass always; S and P are the lab assays).
OBSERVABLES = ("t", "X", "S", "P")


def make_observation(mechanism: str, *, seed: int = 0, noise: float = 0.03,
                     t_end: float = 60.0, sample_dt: float = 1.0) -> list[dict]:
    """The baseline observation: a batch run to plateau, sampled every ``sample_dt``."""
    params = REFERENCE_PRESETS[mechanism]
    traj = run_batch(params, t_end=t_end, noise=noise, seed=seed)
    rows = []
    last = -1.0
    for i, t in enumerate(traj["t"]):
        if t - last >= sample_dt - 1e-9:
            rows.append({"t": round(t, 3), "X": round(traj["X"][i], 6),
                         "S": round(traj["S"][i], 6), "P": round(traj["P"][i], 6)})
            last = t
    return rows


def evaluate_intervention(mechanism: str, intervention: str, *,
                          t_intervene: float = 45.0, seed: int = 0) -> dict:
    """Evaluator-only: run the hidden truth under one intervention, return outcome."""
    params = REFERENCE_PRESETS[mechanism]
    traj = run_batch(params, t_end=90.0, intervention=INTERVENTIONS[intervention],
                     t_intervene=t_intervene, seed=seed)
    return {
        "intervention": intervention,
        "regrowth": bool(is_regrowth(traj, params)),
        "final_X": round(traj["X"][-1], 6),
        "final_S": round(traj["S"][-1], 6),
        "final_P": round(traj["P"][-1], 6),
    }


def write_fixture(outdir: str | os.PathLike, mechanism: str, *, seed: int = 0) -> dict:
    """Write train/holdout CSVs + hidden_truth.yaml. Returns a summary dict."""
    if mechanism not in REFERENCE_PRESETS:
        raise ValueError(f"unknown mechanism {mechanism!r}; choose from {list(REFERENCE_PRESETS)}")
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    obs = make_observation(mechanism, seed=seed)
    with open(out / "train_measurements.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OBSERVABLES)
        w.writeheader()
        w.writerows(obs)

    holdout = [evaluate_intervention(mechanism, iv, seed=seed) for iv in INTERVENTIONS]
    with open(out / "holdout_interventions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["intervention", "regrowth", "final_X", "final_S", "final_P"])
        w.writeheader()
        w.writerows(holdout)

    truth = {"mechanism": mechanism, "parameters": {k: (None if v == float("inf") else v)
                                                    for k, v in REFERENCE_PRESETS[mechanism].items()}}
    # tiny YAML writer to avoid a hard yaml dep here
    lines = [f"mechanism: {mechanism}", "parameters:"]
    for k, v in truth["parameters"].items():
        lines.append(f"  {k}: {'null' if v is None else v}")
    (out / "hidden_truth.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"mechanism": mechanism, "n_train_rows": len(obs),
            "holdout": {h["intervention"]: h["regrowth"] for h in holdout},
            "outdir": str(out)}
