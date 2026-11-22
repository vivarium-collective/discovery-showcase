"""Bias-isolated engine run: earned recovery, recorded transcript, sealed ground truth."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
import pytest

pytest.importorskip("discovery_engine.benchmark.provider", reason="needs PR #163 plumbing")
from viva_discovery_showcase.isolated_run import run_isolated, transcript_mentions_sealed_mechanism

REPO = Path(__file__).resolve().parent.parent
RESOURCES = REPO / "workspace" / "references" / "expert" / "growth-limitation"
FILLER = f"{sys.executable} {REPO / 'scripts' / 'isolated_filler.py'} --self-test"


@pytest.mark.parametrize("mech", ["substrate_exhaustion", "byproduct_inhibition", "density_cap"])
def test_earned_recovery_is_bias_isolated_and_recorded(tmp_path, mech):
    rec = run_isolated(mechanism=mech, resources_dir=RESOURCES, filler_cmd=FILLER, out_dir=tmp_path, seed=0)
    assert rec["ran"] and rec["earned_recovery"]      # the agent EARNED it from the evidence
    assert rec["transcript_entries"] >= 1             # the reasoning was recorded for the paper
    assert not transcript_mentions_sealed_mechanism(rec["transcript"], mech)  # no answer leaked


def test_filler_ignores_a_mechanism_planted_in_the_request():
    # A request that CONTAINS the answer but provides NO evidence: a bias-isolated filler must
    # abstain, proving it reasons from the injected evidence and never reads the request's mechanism.
    env = {k: v for k, v in os.environ.items() if k != "RUN_OBSERVATION"}
    env["RESOURCES_DIR"] = str(RESOURCES)
    out = subprocess.run([sys.executable, str(REPO / "scripts" / "isolated_filler.py"), "--self-test"],
                         input=json.dumps({"id": "r1", "kind": "acquire_model",
                                           "mechanism": "byproduct_inhibition"}),
                         capture_output=True, text=True, env=env)
    assert json.loads(out.stdout) == {}               # abstained: did not leak the planted answer
