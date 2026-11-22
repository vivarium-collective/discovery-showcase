"""Condition B: the agent designs the experiment; independent design scoring."""
import sys
from pathlib import Path
from viva_discovery_showcase.condition_b import run_condition_b
from viva_discovery_showcase.challenge import score_design_run

REPO = Path(__file__).resolve().parent.parent
FILLER = f"{sys.executable} {REPO/'scripts'/'agent_filler.py'} --self-test"


def test_agent_designs_a_fully_discriminating_minimal_experiment(tmp_path):
    rec = run_condition_b(filler_cmd=FILLER, out_dir=tmp_path, seed=0)
    assert rec["fully_discriminating"] and rec["is_minimal_optimal"]
    assert rec["avoided_decoy"] and rec["cost"] == 2
    assert set(rec["chosen_interventions"]) == {"spike_substrate", "remove_byproduct"}


def test_independent_design_score_agrees(tmp_path):
    run_condition_b(filler_cmd=FILLER, out_dir=tmp_path, seed=0)
    out = score_design_run(tmp_path, seed=0)
    assert out["scoring"]["discrimination"] == 1.0 and out["scoring"]["minimal_optimal"]
    assert out["integrity"]["run_claim_agrees_with_independent_score"]
    assert out["integrity"]["hard_failures"] == []
