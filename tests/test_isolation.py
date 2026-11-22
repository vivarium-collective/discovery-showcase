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


def test_contracts_alone_do_not_determine_the_answer_without_evidence():
    # The agent MAY read candidate contracts (they declare each model's mechanism + what to
    # expect). But a contract says what to EXPECT, not which model is operative — only evidence
    # adjudicates. With no evidence, the agent must abstain even though it has every contract.
    env = {k: v for k, v in os.environ.items() if k != "RUN_OBSERVATION"}
    env["RESOURCES_DIR"] = str(RESOURCES)
    out = subprocess.run([sys.executable, str(REPO / "scripts" / "isolated_filler.py"), "--self-test"],
                         input=json.dumps({"id": "r1", "kind": "acquire_model"}),
                         capture_output=True, text=True, env=env)
    assert json.loads(out.stdout) == {}               # abstains: contracts are insufficient without evidence


def test_candidate_contracts_declare_mechanism_and_expectations():
    # The process contract is the channel the agent reads: it must declare the mechanism AND the
    # expected intervention response for every candidate.
    from viva_discovery_showcase.growth import candidate_contracts
    cs = {c["mechanism"]: c for c in candidate_contracts()}
    assert set(cs) == {"substrate_exhaustion", "byproduct_inhibition", "density_cap"}
    assert cs["byproduct_inhibition"]["expected_intervention_response"] == \
        {"spike_substrate": "no regrowth", "remove_byproduct": "regrowth"}
