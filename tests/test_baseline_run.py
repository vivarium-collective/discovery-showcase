"""Run-backed baseline: monod_batch emits real observables; the end-state grades the mechanism."""
from __future__ import annotations
from pathlib import Path
import pytest

pytest.importorskip("viva_emitters")
pytest.importorskip("duckdb")
from viva_discovery_showcase.baseline_run import run_baseline, classify_endstate


@pytest.mark.parametrize("mech", ["substrate_exhaustion", "byproduct_inhibition", "density_cap"])
def test_emitted_endstate_grades_the_mechanism(tmp_path, mech):
    r = run_baseline(mech, out_dir=tmp_path / mech, n_steps=90, record=True)
    # the run was recorded (run-backed) ...
    assert Path(r["runs_db"]).is_file()
    # ... and the mechanism read back from the EMITTED end-state is correct
    assert classify_endstate(r["endstate"]) == mech


def test_endstate_observables_are_distinct_across_mechanisms(tmp_path):
    frac = {m: run_baseline(m, out_dir=tmp_path / m, record=False)["endstate"]["residual_substrate_fraction"]
            for m in ("substrate_exhaustion", "byproduct_inhibition", "density_cap")}
    # substrate exhaustion consumes its substrate; the others leave it plentiful
    assert frac["substrate_exhaustion"] < 0.3
    assert frac["byproduct_inhibition"] > 0.7 and frac["density_cap"] > 0.7
