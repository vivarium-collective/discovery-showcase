"""Run the monod_batch baseline, emit real observables, record the run, read the end-state.

A *run-backed* measurement, as opposed to the store-less re-derivation: the composite actually
runs and emits biomass/substrate/byproduct to a parquet store (``viva_emitters.ParquetEmitter``);
the plateau end-state (residual substrate fraction, final byproduct) is read back from that
emitted data and discriminates the mechanism. This is the real run a behavior test grades
against. ``record_run`` registers it in a per-study ``runs.db`` so the engine's run registry
sees it.

Remaining integration (bounded): the ParquetEmitter writes a flat ``history/*.pq`` layout; the
engine's ``viva_emitters.RunReader`` globs a hive-partitioned layout, which needs the workbench's
run metadata (experiment_id / generation). Until that is wired, we read the end-state directly
with duckdb (same files), so grading is honest and run-backed even though it does not yet flow
through ``RunReader``.
"""
from __future__ import annotations

import importlib
import tempfile
import warnings
from pathlib import Path


def run_baseline(mechanism: str = "byproduct_inhibition", *, out_dir=None,
                 n_steps: int = 90, record: bool = True) -> dict:
    """Run monod_batch for ``mechanism``, emit to parquet, record the run, return the end-state."""
    warnings.filterwarnings("ignore")
    import duckdb
    from process_bigraph import Composite
    from viva_emitters import ParquetEmitter

    from viva_discovery_showcase.composites import monod_batch

    core = importlib.import_module("viva_discovery_showcase.core").build_core()
    store = Path(out_dir or tempfile.mkdtemp(prefix=f"monod-{mechanism}-"))
    doc = monod_batch(core, mechanism=mechanism)
    doc["emitter"] = {
        "_type": "step", "address": "local:ParquetEmitter",
        "config": {"emit": {"biomass": "float", "substrate": "float", "byproduct": "float"},
                   "out_dir": str(store), "batch_size": 10, "threaded": False},
        "inputs": {"biomass": ["biomass"], "substrate": ["substrate"], "byproduct": ["byproduct"]},
    }
    comp = Composite({"state": doc}, core=core)
    comp.run(n_steps)
    ParquetEmitter.flush_all_in_composite(comp, success=True)

    hist = str(store / "default" / "history" / "*.pq")
    con = duckdb.connect()
    cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{hist}')").fetchall()]
    tcol = "global_time" if "global_time" in cols else cols[0]
    S_last, P_last, X_last = con.execute(
        f"SELECT substrate, byproduct, biomass FROM read_parquet('{hist}') ORDER BY {tcol} DESC LIMIT 1").fetchone()
    S_first = con.execute(
        f"SELECT substrate FROM read_parquet('{hist}') ORDER BY {tcol} ASC LIMIT 1").fetchone()[0]
    endstate = {
        "residual_substrate_fraction": (S_last / S_first) if S_first else float("nan"),
        "final_byproduct": float(P_last),
        "final_biomass": float(X_last),
    }

    run_id = f"baseline-{mechanism}"
    runs_db = store / "runs.db"
    if record:
        from discovery_engine.study.run_registry import register_run
        register_run(runs_db, run_id, spec_id="monod_batch", status="complete",
                     params={"mechanism": mechanism}, n_steps=n_steps,
                     emitter_path=str(store / "default"))
    return {"mechanism": mechanism, "store": str(store), "run_id": run_id,
            "runs_db": str(runs_db) if record else None, "endstate": endstate}


def classify_endstate(endstate: dict) -> str:
    """The mechanism implied by the emitted plateau end-state (the behavior-test grade)."""
    if endstate["residual_substrate_fraction"] < 0.3:
        return "substrate_exhaustion"
    if endstate["final_byproduct"] > 0.5:
        return "byproduct_inhibition"
    return "density_cap"
