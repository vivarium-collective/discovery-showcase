"""Run the spatial dFBA colony (spatio-flux) and emit scalar colony summaries for grading.

The spatial composite emits 2-D fields; a behavior test needs scalars. This runs
``spatial_many_dfba`` step by step, reduces the fields to colony-scale observables each step
(total biomass, total acetate byproduct, occupied fraction), and emits those to a
hive-partitioned parquet store the engine's ``RunReader`` reads --- so the spatial run is graded
run-backed, through the same path as the well-mixed studies.

Needs the ``spatial`` extra (cobra, spatio-flux). The reduction is the molecule->population->space
link: the acetate the metabolism secretes, summed over the lattice, is the spatial byproduct load.
"""
from __future__ import annotations

import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

_PARTITION_KEYS = ["experiment_id", "variant", "lineage_seed", "generation", "agent_id"]


def run_spatial_colony(*, n_bins: int = 10, n_steps: int = 20, out_dir=None, record: bool = True) -> dict:
    import importlib
    import numpy as np
    from process_bigraph import Composite
    from viva_emitters import ParquetEmitter, RunReader
    from spatio_flux.composites.spatial import spatial_many_dfba

    core = importlib.import_module("viva_discovery_showcase.core").build_core()
    base = Path(out_dir or tempfile.mkdtemp(prefix="spatial-"))
    experiment_id = "spatial-colony"
    emit_cfg = {"emit": {"time": "float", "total_biomass": "float", "total_acetate": "float",
                         "occupied_fraction": "float"},
                "out_dir": str(base), "batch_size": 8, "threaded": False,
                "partitioning_keys": _PARTITION_KEYS,
                "metadata": {"experiment_id": experiment_id, "variant": 0, "lineage_seed": 0,
                             "generation": 0, "agent_id": "0"}}
    emitter = ParquetEmitter(emit_cfg, core)

    comp = Composite({"state": spatial_many_dfba(core, n_bins=[n_bins, n_bins])}, core=core)
    for i in range(n_steps + 1):
        f = comp.state["fields"]
        bm = np.array(f["dissolved biomass"], dtype=float)
        ac = np.array(f["acetate"], dtype=float)
        emitter.update({"time": float(i), "total_biomass": float(bm.sum()),
                        "total_acetate": float(ac.sum()),
                        "occupied_fraction": float((bm > 0.05).mean())})
        if i < n_steps:
            comp.run(1)
    emitter.close(success=True)

    run_dir = base / experiment_id
    reader = RunReader.open(str(run_dir))

    def _series(obs):
        return reader.series(obs)["value"].to_list()
    tb = _series("total_biomass"); ta = _series("total_acetate")
    endstate = {"total_biomass_final": tb[-1], "total_biomass_growth": tb[-1] / tb[0] if tb[0] else float("nan"),
                "total_acetate_final": ta[-1], "occupied_fraction_final": _series("occupied_fraction")[-1]}

    run_id = experiment_id
    runs_db = base / "runs.db"
    if record:
        from discovery_engine.study.run_registry import register_run
        register_run(runs_db, run_id, spec_id="spatial_many_dfba", status="complete",
                     params={"n_bins": n_bins, "n_steps": n_steps}, n_steps=n_steps,
                     emitter_path=str(run_dir))
    return {"store": str(run_dir), "run_id": run_id, "runs_db": str(runs_db) if record else None,
            "endstate": endstate}
