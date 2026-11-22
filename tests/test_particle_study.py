"""The agent-based particle+dFBA colony study grades run-backed (code) through the engine."""
from pathlib import Path
import pytest, yaml
pytest.importorskip("spatio_flux", reason="needs the spatial extra (cobra, spatio-flux)")
pytest.importorskip("cobra")
from viva_discovery_showcase.particle_run import run_particle_colony
from discovery_engine.study.evaluator.outcomes import compute_outcomes


def test_particle_colony_grows_and_proliferates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sd = tmp_path / "workspace" / "studies" / "particle-colony"; sd.mkdir(parents=True)
    (tmp_path / "workspace.yaml").write_text("name: t\n")
    r = run_particle_colony(n_steps=14, seed=0, out_dir=sd, record=True)
    assert r["endstate"]["total_mass_growth"] > 1.0       # biomass grows via metabolism
    assert r["endstate"]["n_particles_final"] >= r["endstate"]["n_particles_start"]  # proliferation
    study = {"schema_version": 4, "name": "particle-colony",
             "baseline": [{"name": "b", "composite": "spatio_flux.composites.particles.br_particles_dfba",
                           "params": {}}],
             "behavior_tests": [{"name": "biomass_grows",
                                 "measure": {"kind": "generation_average", "path": "total_mass"},
                                 "pass_if": {"op": "range", "low": 0.1, "high": 1000.0}}],
             "runs": [{"name": r["run_id"], "store_path": r["run_id"]}]}
    (sd / "study.yaml").write_text(yaml.safe_dump(study))
    out = compute_outcomes(sd, ws_root=tmp_path)
    assert out["runs_evaluated"] == 1 and out["tests_code"] == 1
    co = yaml.safe_load((sd / "study.yaml").read_text())["runs"][0]["computed_outcomes"]["biomass_grows"]
    assert co["result"] == "PASS" and co["evaluated_by"] == "code"
