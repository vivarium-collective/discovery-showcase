"""Discovery-engine benchmark provider for the growth-limitation benchmark (Episodes 01-04).

Implements the ``fixture.provider`` contract added by discovery-engine PR #163: the engine
calls ``build(ws_root) -> BenchmarkProviderBundle`` and drives its real recovery loop
(``capability_gap -> accept -> build_hook -> advance_cycle(runner) -> grade``) against our
scenario and hooks. The built model's plateau mechanism is graded by the ``growth_recovery``
evaluator (``evaluators.py``), which runs the REAL Monod model.

This is the workspace side: all biological specifics live here; the engine stays domain-free.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from discovery_engine.benchmark import recovery_run
from discovery_engine.benchmark.provider import BenchmarkProviderBundle
from discovery_engine.benchmark.recovery_scenario import RecoveryScenario
from discovery_engine.benchmark.scenario import GroundTruth
from discovery_engine.investigation.import_ import investigations_dir, studies_dir
from discovery_engine.study import evaluator as se

from viva_discovery_showcase.evaluators import KIND
from viva_discovery_showcase.growth import growth_signature

# Three competing plateau mechanisms (public labels). The decoy pairing supplies a
# wrong-but-plausible alternative for the negative control.
MECHANISMS = ("substrate_exhaustion", "byproduct_inhibition", "density_cap")
DECOY = {
    "substrate_exhaustion": "byproduct_inhibition",
    "byproduct_inhibition": "substrate_exhaustion",
    "density_cap": "byproduct_inhibition",
}


def _built_slug(mechanism: str) -> str:
    return "built-" + (re.sub(r"[^a-z0-9]+", "-", mechanism.lower()).strip("-") or "mechanism")


def _band(mechanism: str) -> dict:
    """Acceptance band centred on the mechanism's real-model signature (+/- 0.5)."""
    s = growth_signature(mechanism)
    return {"op": "range", "low": s - 0.5, "high": s + 0.5}


def build_hook(implemented_mechanism: str):
    """A ``build_hook(gap, ws_root) -> dict`` materializing the recovered-mechanism study:
    a composite covering the gap's declared mechanism, the ``growth_recovery`` behavior test
    + finding, and ``implements:`` recording what was actually built (faithful or decoy)."""
    def hook(gap: dict, ws_root) -> dict:
        declared = gap["mechanism"]
        topic = declared.replace("_", " ")
        composite = "recovered." + "".join(w.capitalize() for w in topic.split())
        slug = _built_slug(declared)
        sd = studies_dir(ws_root) / slug
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "study.yaml").write_text(yaml.safe_dump({
            "schema_version": 4,
            "name": slug,
            "topic": topic,
            "baseline": [{"composite": composite}],
            "implements": implemented_mechanism,
            "observables": [],
            "behavior_tests": [{
                "name": "recover",
                "measure": {"kind": KIND, "study": slug},   # store-less; names the study to read implements: from
                "pass_if": _band(declared),                 # band around the DECLARED (concealed) mechanism
            }],
            "findings": [{
                "id": "f-recover",
                "statement": None,
                "evidence": {"measure": "recover", "from_test": "recover"},
            }],
        }), encoding="utf-8")
        for ip in sorted(investigations_dir(ws_root).glob("*/investigation.yaml")):
            d = yaml.safe_load(ip.read_text(encoding="utf-8")) or {}
            d["studies"] = sorted(set(d.get("studies") or []) | {slug})
            ip.write_text(yaml.safe_dump(d), encoding="utf-8")
        return {"status": "built", "process": composite, "gap_id": gap["id"],
                "detail": f"built {composite} implementing {implemented_mechanism!r}"}
    return hook


def build(ws_root, *, mechanism: str = "byproduct_inhibition", name: str = "growth-limitation",
          implements: str | None = None) -> BenchmarkProviderBundle:
    """Author the growth-limitation scenario under ``ws_root`` and return the provider bundle.

    ``mechanism`` is the hidden (concealed) plateau mechanism the engine must recover; the
    engine's loop raises a capability gap for it, the ``build_hook`` builds it (faithful by
    default; pass ``implements`` to force a decoy build), and the ``growth_recovery`` evaluator
    grades the built model's real-model signature against the band.
    """
    se.clear_workspace_evaluator_cache()
    ws = Path(ws_root)
    (ws / "workspace.yaml").write_text(
        "name: discovery-showcase\npackage_path: viva_discovery_showcase\n", encoding="utf-8")

    inv = investigations_dir(ws) / name
    inv.mkdir(parents=True, exist_ok=True)
    (inv / "investigation.yaml").write_text(yaml.safe_dump({
        "name": name, "slug": name, "studies": ["s1"],
        "required_mechanisms": [mechanism],
    }), encoding="utf-8")

    sd = studies_dir(ws) / "s1"
    sd.mkdir(parents=True, exist_ok=True)
    # The gap-trigger study: a batch culture whose baseline predicts continued growth but
    # observes a plateau. The baseline composite is unresolvable (top pkg importable, module
    # not), so it stays needs_build and never runs; the built study is materialized by the hook.
    (sd / "study.yaml").write_text(yaml.safe_dump({
        "schema_version": 4,
        "name": "s1",
        "topic": "growth plateau",
        "required_mechanisms": [mechanism],
        "builds": [mechanism],
        "baseline": [{"composite": "json.nonexistent_mod.GrowthComposite"}],
    }), encoding="utf-8")

    true_sig = growth_signature(mechanism)
    ground_truth = GroundTruth(
        observable="growth_signature", base_value=-1.0, true_value=true_sig,
        band=_band(mechanism), concealed_mechanism=mechanism, correct_composite="",
        decoy_mechanism=DECOY.get(mechanism, "substrate_exhaustion"))
    scenario = RecoveryScenario(ws, name, "s1", ground_truth, KIND)

    return BenchmarkProviderBundle(
        scenario=scenario,
        build_hook=build_hook(implements or mechanism),
        runner=recovery_run.benchmark_runner())
