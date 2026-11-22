"""Run the monod_batch baseline, emit real observables, record the run, read the end-state.

A *run-backed* measurement, as opposed to the store-less re-derivation: the composite actually
runs and emits biomass/substrate/byproduct to a hive-partitioned parquet store
(``viva_emitters.ParquetEmitter``) that the engine's ``viva_emitters.RunReader`` reads natively;
the plateau end-state (residual substrate fraction, final byproduct) is read back *through
RunReader* and discriminates the mechanism. ``register_run`` records it in a ``runs.db`` with the
``emitter_path`` the engine resolves, so a study's behavior test can grade this exact run.

The emitter is given the workbench run metadata the reader expects --- the hive partition keys
``experiment_id/variant/lineage_seed/generation/agent_id`` --- so the store lands at
``<base>/<experiment_id>/history/...`` and ``RunReader.open(<base>/<experiment_id>)`` resolves it.
"""
from __future__ import annotations

import importlib
import tempfile
import warnings
from pathlib import Path

# Hive partition metadata the engine's RunReader expects (single-generation batch run).
_PARTITION_KEYS = ["experiment_id", "variant", "lineage_seed", "generation", "agent_id"]


def _emit_metadata(experiment_id: str) -> dict:
    return {"experiment_id": experiment_id, "variant": 0, "lineage_seed": 0,
            "generation": 0, "agent_id": "0"}


def run_baseline(mechanism: str = "byproduct_inhibition", *, out_dir=None,
                 n_steps: int = 90, record: bool = True) -> dict:
    """Run monod_batch for ``mechanism``, emit to a RunReader-readable store, record, read end-state."""
    warnings.filterwarnings("ignore")
    from process_bigraph import Composite
    from viva_emitters import ParquetEmitter, RunReader

    from viva_discovery_showcase.composites import monod_batch

    core = importlib.import_module("viva_discovery_showcase.core").build_core()
    base = Path(out_dir or tempfile.mkdtemp(prefix=f"monod-{mechanism}-"))
    experiment_id = f"baseline-{mechanism}"
    doc = monod_batch(core, mechanism=mechanism)
    doc["emitter"] = {
        "_type": "step", "address": "local:ParquetEmitter",
        "config": {"emit": {"biomass": "float", "substrate": "float", "byproduct": "float", "time": "float"},
                   "out_dir": str(base), "batch_size": 10, "threaded": False,
                   "partitioning_keys": _PARTITION_KEYS, "metadata": _emit_metadata(experiment_id)},
        "inputs": {"biomass": ["biomass"], "substrate": ["substrate"],
                   "byproduct": ["byproduct"], "time": ["global_time"]},
    }
    comp = Composite({"state": doc}, core=core)
    comp.run(n_steps)
    ParquetEmitter.flush_all_in_composite(comp, success=True)

    run_dir = base / experiment_id
    reader = RunReader.open(str(run_dir))

    def _final(obs):
        return float(reader.series(obs)["value"].to_list()[-1])

    def _first(obs):
        return float(reader.series(obs)["value"].to_list()[0])

    S_first = _first("substrate")
    endstate = {
        "residual_substrate_fraction": (_final("substrate") / S_first) if S_first else float("nan"),
        "final_byproduct": _final("byproduct"),
        "final_biomass": _final("biomass"),
    }

    run_id = experiment_id
    runs_db = base / "runs.db"
    if record:
        from discovery_engine.study.run_registry import register_run
        register_run(runs_db, run_id, spec_id="monod_batch", status="complete",
                     params={"mechanism": mechanism}, n_steps=n_steps,
                     emitter_path=str(run_dir))
    return {"mechanism": mechanism, "store": str(run_dir), "run_id": run_id,
            "runs_db": str(runs_db) if record else None, "endstate": endstate}


def classify_endstate(endstate: dict) -> str:
    """The mechanism implied by the emitted plateau end-state (the behavior-test grade)."""
    if endstate["residual_substrate_fraction"] < 0.3:
        return "substrate_exhaustion"
    if endstate["final_byproduct"] > 0.5:
        return "byproduct_inhibition"
    return "density_cap"
