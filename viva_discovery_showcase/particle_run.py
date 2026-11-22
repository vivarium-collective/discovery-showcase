"""Run the agent-based particle+dFBA colony (spatio-flux) and emit scalar colony summaries.

A second real multiscale method class, distinct from the continuum spatial dFBA: here each particle
carries its OWN flux-balance metabolism, moves by Brownian motion through a diffusing field, grows
mass, and divides past a threshold. ``br_particles_dfba`` is the composite the engine discovers.

Like ``spatial_run``, this runs the composite step by step, reduces the particle population to
colony-scale scalars each step (particle count, total biomass), and emits them to a
RunReader-readable store so the run grades run-backed through the engine. Needs the ``spatial`` extra.
"""
from __future__ import annotations

import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

_PARTITION_KEYS = ["experiment_id", "variant", "lineage_seed", "generation", "agent_id"]


def run_particle_colony(*, n_steps: int = 16, seed: int = 0, out_dir=None, record: bool = True) -> dict:
    import importlib
    import numpy as np
    from process_bigraph import Composite
    from viva_emitters import ParquetEmitter, RunReader
    from spatio_flux.composites.particles import br_particles_dfba

    np.random.seed(seed)
    core = importlib.import_module("viva_discovery_showcase.core").build_core()
    base = Path(out_dir or tempfile.mkdtemp(prefix="particle-"))
    experiment_id = "particle-colony"
    emit_cfg = {"emit": {"time": "float", "n_particles": "float", "total_mass": "float"},
                "out_dir": str(base), "batch_size": 8, "threaded": False,
                "partitioning_keys": _PARTITION_KEYS,
                "metadata": {"experiment_id": experiment_id, "variant": 0, "lineage_seed": seed,
                             "generation": 0, "agent_id": "0"}}
    emitter = ParquetEmitter(emit_cfg, core)

    gen = br_particles_dfba(core)  # returns a full {state, schema} doc, not a flat state
    comp = Composite(gen if "state" in gen else {"state": gen}, core=core)
    for i in range(n_steps + 1):
        parts = comp.state.get("particles", {})
        masses = [float(p.get("mass", 0.0)) for p in parts.values()] if hasattr(parts, "values") else []
        emitter.update({"time": float(i), "n_particles": float(len(parts)),
                        "total_mass": float(sum(masses))})
        if i < n_steps:
            comp.run(1)
    emitter.close(success=True)

    run_dir = base / experiment_id
    reader = RunReader.open(str(run_dir))

    def _series(obs):
        return reader.series(obs)["value"].to_list()
    npart = _series("n_particles"); mass = _series("total_mass")
    endstate = {"n_particles_final": npart[-1], "n_particles_start": npart[0],
                "total_mass_final": mass[-1],
                "total_mass_growth": mass[-1] / mass[0] if mass[0] else float("nan")}

    runs_db = base / "runs.db"
    if record:
        from discovery_engine.study.run_registry import register_run
        register_run(runs_db, experiment_id, spec_id="br_particles_dfba", status="complete",
                     params={"n_steps": n_steps, "seed": seed}, n_steps=n_steps, emitter_path=str(run_dir))
    return {"store": str(run_dir), "run_id": experiment_id,
            "runs_db": str(runs_db) if record else None, "endstate": endstate}
