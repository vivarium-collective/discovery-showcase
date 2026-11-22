"""Condition C: closed loop design->execute->evaluate; independent scoring."""
import sys
from pathlib import Path
import yaml
from viva_discovery_showcase.condition_c import run_condition_c
from viva_discovery_showcase.challenge import score_loop_run

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "workspace" / "references" / "expert" / "growth-limitation"
MANIFEST = REPO / "challenges" / "growth-plateau-H2-001" / "manifest.yaml"
SEALED = REPO / "challenges" / "growth-plateau-H2-001" / ".sealed" / "truth.yaml"
DESIGN = f"{sys.executable} {REPO/'scripts'/'agent_filler.py'} --self-test"
INTERP = f"{sys.executable} {REPO/'scripts'/'isolated_filler.py'} --self-test"


def test_closed_loop_designs_executes_and_recovers(tmp_path):
    rec = run_condition_c(sealed_mechanism="byproduct_inhibition", design_filler_cmd=DESIGN,
                          interpret_filler_cmd=INTERP, resources_dir=RES, out_dir=tmp_path, seed=0)
    assert rec["design_sufficient"] and rec["recovered"] and rec["loop_closed"]
    assert set(rec["chosen_interventions"]) == {"spike_substrate", "remove_byproduct"}


def test_independent_loop_score_agrees(tmp_path):
    run_condition_c(sealed_mechanism="byproduct_inhibition", design_filler_cmd=DESIGN,
                    interpret_filler_cmd=INTERP, resources_dir=RES, out_dir=tmp_path, seed=0)
    out = score_loop_run(yaml.safe_load(MANIFEST.read_text()), yaml.safe_load(SEALED.read_text()), tmp_path, seed=0)
    assert out["scoring"]["recovered"] and out["scoring"]["closed_loop"]
    assert out["integrity"]["run_claim_agrees_with_independent_score"]
    assert out["integrity"]["hard_failures"] == []
