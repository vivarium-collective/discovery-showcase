"""The growth-limitation benchmark provider drives the engine's real recovery loop.

Requires the manifest->provider plumbing from discovery-engine PR #163 (installed in the
dev venv). Skips cleanly if the engine build predates it.
"""
from __future__ import annotations

import pytest

pytest.importorskip("discovery_engine.benchmark.provider",
                    reason="needs discovery-engine manifest->provider plumbing (PR #163)")

from discovery_engine.benchmark.manifest import from_dict
from discovery_engine.benchmark.manifest_run import run_manifest_benchmark
from discovery_engine.benchmark.recovery_metrics import score_recovery
from discovery_engine.benchmark.recovery_runner import RecoveryConfig, run_recovery_benchmark

from viva_discovery_showcase import benchmark_provider as bp
from viva_discovery_showcase.growth import growth_signature


def test_mechanism_signatures_are_distinct():
    assert growth_signature("substrate_exhaustion") == 2.0
    assert growth_signature("byproduct_inhibition") == 1.0
    assert growth_signature("density_cap") == 0.0
    assert growth_signature("nonsense") == -1.0


def _manifest():
    return from_dict({
        "id": "growth-limitation",
        "question": "why does the batch culture stop growing?",
        "fixture": {"provider": "viva_discovery_showcase.benchmark_provider:build",
                    "oracle_visibility": "evaluator_only"},
        "allowed_skills": ["hypothesize", "critique"],
        "budget": {"simulation_runs": 4, "model_builds": 1, "generation_calls": 4},
    })


def test_faithful_build_recovers_the_mechanism(tmp_path):
    # Default concealed mechanism = byproduct_inhibition; faithful build -> in band.
    matrix = run_manifest_benchmark(_manifest(), tmp_path, recovery=True)
    (name, metrics), = matrix.items()
    assert name == "growth-limitation"
    assert metrics.ran is True
    assert metrics.mechanism_recovered is True
    assert metrics.held_out_error == 0.0  # built signature == concealed signature


@pytest.mark.parametrize("concealed", ["substrate_exhaustion", "byproduct_inhibition", "density_cap"])
def test_each_concealed_mechanism_recovers_when_built_faithfully(tmp_path, concealed):
    bundle = bp.build(tmp_path, mechanism=concealed)
    cfg = RecoveryConfig(name=f"growth-{concealed}", build_hook_factory=None)
    res = run_recovery_benchmark(bundle.scenario, cfg, build_hook=bundle.build_hook, runner=bundle.runner)
    assert score_recovery(res, bundle.scenario.ground_truth).mechanism_recovered is True


def test_decoy_build_does_not_recover(tmp_path):
    # Concealed = byproduct_inhibition, but build the WRONG mechanism -> out of band.
    bundle = bp.build(tmp_path, mechanism="byproduct_inhibition", implements="substrate_exhaustion")
    cfg = RecoveryConfig(name="growth-decoy", build_hook_factory=None)
    res = run_recovery_benchmark(bundle.scenario, cfg, build_hook=bundle.build_hook, runner=bundle.runner)
    assert score_recovery(res, bundle.scenario.ground_truth).mechanism_recovered is False
