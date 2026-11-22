"""The spatial dFBA colony study grades run-backed (code) through the engine."""
from pathlib import Path
import pytest, yaml
pytest.importorskip("spatio_flux", reason="needs the spatial extra (cobra, spatio-flux)")
pytest.importorskip("cobra")
from viva_discovery_showcase.spatial_run import run_spatial_colony
from discovery_engine.study.evaluator.outcomes import compute_outcomes


def test_spatial_colony_grows_and_accumulates_byproduct(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sd = tmp_path / "workspace" / "studies" / "spatial-colony"; sd.mkdir(parents=True)
    (tmp_path / "workspace.yaml").write_text("name: t\n")
    r = run_spatial_colony(n_bins=6, n_steps=8, out_dir=sd, record=True)
    assert r["endstate"]["total_biomass_growth"] > 1.0        # the colony grows
    assert r["endstate"]["total_acetate_final"] > 0.0         # acetate accumulates in space
    study = {"schema_version": 4, "name": "spatial-colony",
             "baseline": [{"name": "b", "composite": "spatio_flux.composites.spatial.spatial_many_dfba",
                           "params": {"n_bins": [6, 6]}}],
             "behavior_tests": [{"name": "colony_grows",
                                 "measure": {"kind": "generation_average", "path": "total_biomass"},
                                 "pass_if": {"op": "range", "low": 0.1, "high": 1000.0}}],
             "runs": [{"name": r["run_id"], "store_path": r["run_id"]}]}
    (sd / "study.yaml").write_text(yaml.safe_dump(study))
    out = compute_outcomes(sd, ws_root=tmp_path)
    assert out["runs_evaluated"] == 1 and out["tests_code"] == 1
    co = yaml.safe_load((sd / "study.yaml").read_text())["runs"][0]["computed_outcomes"]["colony_grows"]
    assert co["result"] == "PASS" and co["evaluated_by"] == "code"
