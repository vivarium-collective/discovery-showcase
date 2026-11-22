"""The real-agent run harness: filler contract + the 3-config ablation.

Requires the manifest->provider plumbing (PR #163). The real-agent config is exercised with
the filler's deterministic ``--self-test`` reasoner (a correct reasoner) so the whole
filler -> build_hook -> recovery wiring is validated without a live LLM.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("discovery_engine.benchmark.provider",
                    reason="needs discovery-engine manifest->provider plumbing (PR #163)")

from viva_discovery_showcase.ablation import observation_for, run_ablation

FILLER = str(Path(__file__).resolve().parent.parent / "scripts" / "agent_filler.py")


def test_observation_patterns_are_the_discrimination_signature():
    assert observation_for("substrate_exhaustion") == {"spike_regrowth": True, "remove_regrowth": False}
    assert observation_for("byproduct_inhibition") == {"spike_regrowth": False, "remove_regrowth": True}
    assert observation_for("density_cap") == {"spike_regrowth": False, "remove_regrowth": False}


def _run_filler(observation, *, self_test=True):
    env = dict(os.environ)
    if observation is None:
        env.pop("GROWTH_OBSERVATION", None)
    else:
        env["GROWTH_OBSERVATION"] = json.dumps(observation)
    args = [sys.executable, FILLER] + (["--self-test"] if self_test else [])
    out = subprocess.run(args, input="{}", capture_output=True, text=True, env=env)
    return json.loads(out.stdout)


def test_filler_infers_mechanism_from_evidence():
    assert _run_filler({"spike_regrowth": True, "remove_regrowth": False}) == {"implements": "substrate_exhaustion"}
    assert _run_filler({"spike_regrowth": False, "remove_regrowth": True}) == {"implements": "byproduct_inhibition"}
    assert _run_filler({"spike_regrowth": False, "remove_regrowth": False}) == {"implements": "density_cap"}


def test_filler_abstains_without_evidence():
    assert _run_filler(None) == {}  # no observation -> name no mechanism -> abstain


def test_ablation_oracle_recovers_and_floor_does_not():
    res = run_ablation(mechanism="byproduct_inhibition", seeds=(0, 1))
    assert set(res) == {"oracle", "deterministic_only"}
    assert res["oracle"]["recovered_rate"][0] == 1.0
    assert res["deterministic_only"]["recovered_rate"][0] == 0.0


def test_ablation_real_agent_recovers_with_correct_reasoner():
    # The self-test filler reasons correctly from the evidence -> the real-agent config recovers.
    res = run_ablation(mechanism="byproduct_inhibition", seeds=(0, 1),
                       real_filler_cmd=f"{sys.executable} {FILLER} --self-test")
    assert res["real_agent"]["recovered_rate"][0] == 1.0
    assert res["oracle"]["recovered_rate"][0] == 1.0
    assert res["deterministic_only"]["recovered_rate"][0] == 0.0
