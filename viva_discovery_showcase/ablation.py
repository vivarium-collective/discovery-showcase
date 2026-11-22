"""Ablation harness for the growth-limitation benchmark (Episodes 01-04).

Runs the recovery loop under matched budget + seeds across three configs and aggregates
mechanism-recovery rate and held-out error with CIs (via the engine's ``matrix.aggregate``):

- ``oracle``             — faithful build hook (the deterministic perfect builder);
- ``deterministic_only`` — no acquire/build capability (the floor: cannot recover);
- ``real_agent``         — a real reasoning filler (``$VIVA_FILLER_CMD``) chooses the
  mechanism to build from the intervention evidence; recovery is earned, not fixed.

The real_agent config is included only when a filler command is supplied. The filler reads
the experimental observation from ``$GROWTH_OBSERVATION`` (written here per run); it never
sees the hidden-truth label.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from viva_discovery_showcase.growth import (
    MECHANISM_LABELS,
    REFERENCE_PRESETS,
    is_regrowth,
    remove_byproduct,
    run_batch,
    spike_substrate,
)


def observation_for(mechanism: str, *, seed: int = 0) -> dict:
    """The experimental observation the agent is shown: regrowth under each diagnostic arm
    (evaluator-only to generate; the agent sees only the two booleans, not the mechanism)."""
    params = REFERENCE_PRESETS[MECHANISM_LABELS[mechanism]]
    spike = is_regrowth(run_batch(params, t_end=90.0, intervention=spike_substrate,
                                  t_intervene=45.0, seed=seed), params)
    remove = is_regrowth(run_batch(params, t_end=90.0, intervention=remove_byproduct,
                                   t_intervene=45.0, seed=seed), params)
    return {"spike_regrowth": bool(spike), "remove_regrowth": bool(remove)}


def run_ablation(*, mechanism: str = "byproduct_inhibition", seeds=(0, 1, 2),
                 real_filler_cmd: Optional[str] = None) -> dict:
    """Run the 3-config ablation; return ``{config: {recovered_rate, heldout_error, n}}``.

    ``recovered_rate`` / ``heldout_error`` are ``(mean, ci_lo, ci_hi)`` tuples over seeds.
    """
    from discovery_engine.benchmark.matrix import aggregate
    from discovery_engine.benchmark.recovery_metrics import score_recovery
    from discovery_engine.benchmark.recovery_runner import (
        RECOVERY_CONFIGS, RecoveryConfig, run_recovery_benchmark)

    import viva_discovery_showcase.benchmark_provider as bp
    # Showcase real_build_hook (routes the filler's mechanism into our Monod-graded build);
    # the engine's own real_build_hook hardcodes the toy evaluator, so it is NOT reused here.
    from viva_discovery_showcase.benchmark_provider import real_build_hook

    def _oracle(ws, seed):
        b = bp.build(ws, mechanism=mechanism)
        cfg = RecoveryConfig("oracle", build_hook_factory=None)
        return run_recovery_benchmark(b.scenario, cfg, build_hook=b.build_hook,
                                      runner=b.runner), b.scenario.ground_truth

    def _deterministic(ws, seed):
        b = bp.build(ws, mechanism=mechanism)
        return run_recovery_benchmark(b.scenario, RECOVERY_CONFIGS["no_acquire"],
                                      runner=b.runner), b.scenario.ground_truth

    def _real_agent(ws, seed):
        b = bp.build(ws, mechanism=mechanism)
        prev = os.environ.get("GROWTH_OBSERVATION")
        os.environ["GROWTH_OBSERVATION"] = json.dumps(observation_for(mechanism, seed=seed))
        try:
            cfg = RecoveryConfig("real_agent", build_hook_factory=None)
            res = run_recovery_benchmark(b.scenario, cfg,
                                         build_hook=real_build_hook(real_filler_cmd),
                                         runner=b.runner)
        finally:
            if prev is None:
                os.environ.pop("GROWTH_OBSERVATION", None)
            else:
                os.environ["GROWTH_OBSERVATION"] = prev
        return res, b.scenario.ground_truth

    configs = {"oracle": _oracle, "deterministic_only": _deterministic}
    if real_filler_cmd:
        configs["real_agent"] = _real_agent

    out: dict = {}
    for name, fn in configs.items():
        recs = []
        for seed in seeds:
            with tempfile.TemporaryDirectory(prefix=f"ablation-{name}-") as td:
                res, gt = fn(Path(td), seed)
                recs.append(score_recovery(res, gt))
        errs = [r.held_out_error for r in recs if r.held_out_error is not None]
        out[name] = {
            "recovered_rate": aggregate([1.0 if r.mechanism_recovered else 0.0 for r in recs]),
            "heldout_error": aggregate(errs),
            "n": len(recs),
        }
    return out


def render(results: dict) -> str:
    """A compact table of the ablation results."""
    lines = [f"{'config':<20} {'recovered':>10} {'heldout_err':>14}  n"]
    for name, r in results.items():
        rec = r["recovered_rate"][0]
        err = r["heldout_error"][0]
        rec_s = f"{rec:.2f}" if rec is not None else "--"
        err_s = f"{err:.3f}" if err is not None else "--"
        lines.append(f"{name:<20} {rec_s:>10} {err_s:>14}  {r['n']}")
    return "\n".join(lines)
