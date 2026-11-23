"""The structural revision runs through the engine and grades run-backed; refit/baseline do not."""
from pathlib import Path
import pytest, yaml
from viva_discovery_showcase.pathway_run import run_pathway
from discovery_engine.study.evaluator.outcomes import compute_outcomes


def _peak(model):
    return run_pathway(model=model, heldout_pulse=7.0, record=False)["endstate"]["peak_intermediate"]


def test_structural_revision_generalizes_refit_overfits():
    # On a held-out pulse, the structural revision matches the true peak; refit + baseline do not.
    assert abs(_peak("structural") - 0.895) < 0.08      # generalizes (true 0.895)
    assert _peak("refit") > 0.98                          # overfits (out of band, high)
    assert _peak("baseline") > 1.5                        # unrevised overshoots badly


def test_structural_revision_grades_supported_through_engine(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sd = tmp_path / "workspace" / "studies" / "pathway-revision"; sd.mkdir(parents=True)
    (tmp_path / "workspace.yaml").write_text("name: t\n")
    r = run_pathway(model="structural", heldout_pulse=7.0, out_dir=sd, record=True)
    study = {"schema_version": 4, "name": "pathway-revision",
             "baseline": [{"name": "b", "composite": "viva_discovery_showcase.composites.pathway_pulse",
                           "params": {"model": "structural", "pulse": 7.0}}],
             "behavior_tests": [{"name": "generalizes_heldout",
                                 "measure": {"kind": "generation_average", "path": "peak_intermediate"},
                                 "pass_if": {"op": "range", "low": 0.80, "high": 0.98}}],
             "runs": [{"name": r["run_id"], "store_path": r["run_id"]}]}
    (sd / "study.yaml").write_text(yaml.safe_dump(study))
    out = compute_outcomes(sd, ws_root=tmp_path)
    assert out["runs_evaluated"] == 1 and out["tests_code"] == 1
    co = yaml.safe_load((sd / "study.yaml").read_text())["runs"][0]["computed_outcomes"]["generalizes_heldout"]
    assert co["result"] == "PASS" and co["evaluated_by"] == "code"
