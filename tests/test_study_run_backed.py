"""The growth-plateau end-state behavior test grades run-backed (code), via RunReader."""
from __future__ import annotations
from pathlib import Path
import pytest
import yaml

pytest.importorskip("viva_emitters")
pytest.importorskip("duckdb")
from viva_discovery_showcase.baseline_run import run_baseline
from discovery_engine.study.evaluator.outcomes import compute_outcomes


def test_end_state_test_grades_code_passing(tmp_path):
    sd = tmp_path / "workspace" / "studies" / "s"
    sd.mkdir(parents=True)
    (tmp_path / "workspace.yaml").write_text("name: t\n")  # ws marker for evaluator loading
    r = run_baseline("byproduct_inhibition", out_dir=sd, record=True)
    study = {
        "schema_version": 4, "name": "s",
        "baseline": [{"name": "b", "composite": "viva_discovery_showcase.composites.monod_batch",
                      "params": {"mechanism": "byproduct_inhibition"}}],
        "behavior_tests": [{"name": "byproduct_accumulates",
                            "measure": {"kind": "generation_average", "path": "byproduct"},
                            "pass_if": {"op": "range", "low": 0.3, "high": 10.0}}],
        "runs": [{"name": r["run_id"], "store_path": r["run_id"]}],
    }
    (sd / "study.yaml").write_text(yaml.safe_dump(study))
    out = compute_outcomes(sd, ws_root=tmp_path)
    assert out["runs_evaluated"] == 1 and out["tests_code"] == 1  # graded by CODE, run-backed
    doc = yaml.safe_load((sd / "study.yaml").read_text())
    co = doc["runs"][0]["computed_outcomes"]["byproduct_accumulates"]
    assert co["result"] == "PASS" and co["evaluated_by"] == "code"
