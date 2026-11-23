"""Run the metabolic-feedback pathway (and its structural revision) THROUGH the engine and grade it.

The main result is model-level (Fig~3): a structural revision that adds product feedback generalizes
on held-out substrate pulses where a parameter refit overfits. This executes that revision in a real
composite and grades it run-backed, closing the "re-grade through the engine" gap: run the chosen
model at a HELD-OUT pulse, take the peak of the intermediate I over the run, emit it as an observable
to a RunReader store, register the run; a behavior test then grades the peak against the band around
the true model's peak. The structural revision lands in the band; the refit and the unrevised baseline
do not.
"""
from __future__ import annotations

import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

_PARTITION_KEYS = ["experiment_id", "variant", "lineage_seed", "generation", "agent_id"]


def run_pathway(*, model: str = "structural", heldout_pulse: float = 7.0, train_pulse: float = 3.0,
                n_steps: int = 40, out_dir=None, record: bool = True) -> dict:
    import importlib
    from process_bigraph import Composite
    from viva_emitters import ParquetEmitter, RunReader
    from viva_discovery_showcase.composites import pathway_pulse

    core = importlib.import_module("viva_discovery_showcase.core").build_core()
    base = Path(out_dir or tempfile.mkdtemp(prefix="pathway-"))
    experiment_id = f"pathway-{model}"
    emit_cfg = {"emit": {"time": "float", "peak_intermediate": "float", "I": "float", "P": "float"},
                "out_dir": str(base), "batch_size": 8, "threaded": False,
                "partitioning_keys": _PARTITION_KEYS,
                "metadata": {"experiment_id": experiment_id, "variant": 0, "lineage_seed": 0,
                             "generation": 0, "agent_id": "0"}}
    emitter = ParquetEmitter(emit_cfg, core)

    comp = Composite({"state": pathway_pulse(core, model=model, pulse=heldout_pulse,
                                             train_pulse=train_pulse)}, core=core)
    # Phase 1: run the composite, record the intermediate trajectory.
    traj = []
    for _ in range(n_steps):
        comp.run(1)
        traj.append((float(comp.state["I"]), float(comp.state["P"])))
    peak = max(i for i, _ in traj)
    # Phase 2: emit the peak as a constant observable (so generation_average == the peak), alongside
    # the final I and P for the record.
    for i, (I, P) in enumerate(traj):
        emitter.update({"time": float(i), "peak_intermediate": peak, "I": I, "P": P})
    emitter.close(success=True)

    run_dir = base / experiment_id
    reader = RunReader.open(str(run_dir))
    peak_series = reader.series("peak_intermediate")["value"].to_list()
    endstate = {"peak_intermediate": peak_series[-1], "model": model, "heldout_pulse": heldout_pulse}

    runs_db = base / "runs.db"
    if record:
        from discovery_engine.study.run_registry import register_run
        register_run(runs_db, experiment_id, spec_id="pathway_pulse", status="complete",
                     params={"model": model, "pulse": heldout_pulse}, n_steps=n_steps,
                     emitter_path=str(run_dir))
    return {"store": str(run_dir), "run_id": experiment_id,
            "runs_db": str(runs_db) if record else None, "endstate": endstate}
