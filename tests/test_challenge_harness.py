"""Challenge manifest validation + independent scoring (M1 foundations)."""
import json
from pathlib import Path
import yaml
from viva_discovery_showcase.challenge import validate_manifest, score_run

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "challenges" / "growth-plateau-H2-001" / "manifest.yaml"
SEALED = REPO / "challenges" / "growth-plateau-H2-001" / ".sealed" / "truth.yaml"


def test_real_manifest_is_valid():
    assert validate_manifest(yaml.safe_load(MANIFEST.read_text())) == []


def test_validator_catches_missing_and_mistyped():
    errs = validate_manifest({"challenge_id": 7, "budget": {"iterations": 1}})
    assert any("challenge_id" in e for e in errs)
    assert any("budget missing keys" in e for e in errs)
    assert any("scientific_goal" in e for e in errs)


def _write_run(rd, mech, *, agent_answer, engine_recovered, prompt="candidates: substrate, byproduct, density"):
    rd.mkdir(parents=True, exist_ok=True)
    (rd / f"transcript-{mech}-seed0.jsonl").write_text(
        json.dumps({"kind": "capability_gap", "prompt": prompt,
                    "result": ({"implements": agent_answer} if agent_answer else {})}) + "\n")
    (rd / f"run-record-{mech}-seed0.json").write_text(json.dumps({"earned_recovery": engine_recovered}))


def test_independent_scorer_recovers_and_agrees(tmp_path):
    m = yaml.safe_load(MANIFEST.read_text()); s = yaml.safe_load(SEALED.read_text())
    rd = tmp_path / "runs"; _write_run(rd, "byproduct_inhibition", agent_answer="byproduct_inhibition", engine_recovered=True)
    out = score_run(m, s, rd)
    assert out["scoring"]["inference"]["recovered"] is True
    assert out["integrity"]["engine_grade_agrees_with_independent_score"] is True
    assert out["integrity"]["hard_failures"] == []


def test_scorer_flags_engine_divergence(tmp_path):
    # engine claims recovered, but the raw transcript answer is WRONG -> independent score catches it
    m = yaml.safe_load(MANIFEST.read_text()); s = yaml.safe_load(SEALED.read_text())
    rd = tmp_path / "runs"; _write_run(rd, "byproduct_inhibition", agent_answer="substrate_exhaustion", engine_recovered=True)
    out = score_run(m, s, rd)
    assert out["scoring"]["inference"]["recovered"] is False
    assert "engine_score_divergence" in out["integrity"]["hard_failures"]


def test_scorer_detects_truth_leak(tmp_path):
    m = yaml.safe_load(MANIFEST.read_text()); s = yaml.safe_load(SEALED.read_text())
    rd = tmp_path / "runs"
    _write_run(rd, "byproduct_inhibition", agent_answer="byproduct_inhibition", engine_recovered=True,
               prompt="the mechanism is byproduct_inhibition")
    out = score_run(m, s, rd)
    assert out["integrity"]["truth_leaked_into_prompt"] is True
    assert "truth_leaked" in out["integrity"]["hard_failures"]
