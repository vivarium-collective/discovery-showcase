"""Challenge manifests + an INDEPENDENT scorer for isolated engine evaluation (M1 foundations).

A *challenge* is one scientific problem instance: a manifest fixes the goal, the allowlisted
resources, the budget, the agent, and a pointer to a SEALED ground truth before the engine runs.
The engine run never sees the sealed truth (it lives outside the ``--resources`` allowlist).

The scorer is *independent*: it re-derives the score from the run's raw artifacts (the transcript
and run record) plus the sealed truth, rather than trusting the engine's in-process grade --- and
it flags when the two disagree. That is the point the evaluation plan makes: a correct answer
reached through unregistered or leaked evidence must not score as a valid discovery.

Kept pure and import-light so the scorer can run as a separate process (``scripts/scorer.py``)
with read-only access to a run directory and the sealed truth.
"""
from __future__ import annotations

import json
from pathlib import Path

# --- Manifest schema + validator ---------------------------------------------
# A minimal strict schema: (key -> (required, type)). Nested keys use dotted paths.
_REQUIRED = {
    "challenge_id": str,
    "scientific_goal": str,
    "resources": dict,
    "interventions": list,
    "engine": dict,
    "budget": dict,
    "agent": dict,
    "prompt_id": str,
    "scoring": dict,
    "outputs": list,
}
_SCORING_REQUIRED = {"sealed_truth_ref": str, "scorer": str}
_BUDGET_REQUIRED = {"iterations", "simulations", "model_builds", "generation_calls"}


def validate_manifest(manifest: dict) -> list[str]:
    """Return a list of schema errors (empty = valid)."""
    errs: list[str] = []
    for key, typ in _REQUIRED.items():
        if key not in manifest:
            errs.append(f"missing required key: {key}")
        elif not isinstance(manifest[key], typ):
            errs.append(f"key {key!r} must be {typ.__name__}, got {type(manifest[key]).__name__}")
    sc = manifest.get("scoring")
    if isinstance(sc, dict):
        for k, t in _SCORING_REQUIRED.items():
            if k not in sc or not isinstance(sc[k], t):
                errs.append(f"scoring.{k} missing or not {t.__name__}")
    bud = manifest.get("budget")
    if isinstance(bud, dict):
        missing = _BUDGET_REQUIRED - set(bud)
        if missing:
            errs.append(f"budget missing keys: {sorted(missing)}")
    res = manifest.get("resources")
    if isinstance(res, dict) and "allowlist" not in res:
        errs.append("resources.allowlist is required")
    return errs


# --- Independent scoring ------------------------------------------------------
def _last_agent_answer(transcript_path: Path) -> "str | None":
    """The agent's final declared mechanism, read from the raw transcript (not the engine grade)."""
    if not transcript_path.is_file():
        return None
    answer = None
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        res = entry.get("result") or {}
        if isinstance(res, dict) and res.get("implements"):
            answer = res["implements"]
    return answer


def _truth_leaked(transcript_path: Path, true_mechanism: str) -> bool:
    """Integrity: did any prompt ASSERT the true mechanism as the answer (vs list it as a candidate)?"""
    if not transcript_path.is_file():
        return False
    low = transcript_path.read_text(encoding="utf-8").lower()
    leak_phrases = [f"the mechanism is {true_mechanism}", f"true mechanism is {true_mechanism}",
                    f"the answer is {true_mechanism}", f"operative mechanism: {true_mechanism}"]
    return any(p in low for p in leak_phrases)


def score_run(manifest: dict, sealed_truth: dict, run_dir: Path, *, seed: int = 0) -> dict:
    """Independently score one run against the sealed truth. Returns {scoring, integrity}."""
    run_dir = Path(run_dir)
    true_mech = sealed_truth["true_mechanism"]
    tpath = run_dir / f"transcript-{true_mech}-seed{seed}.jsonl"
    rpath = run_dir / f"run-record-{true_mech}-seed{seed}.json"

    agent_answer = _last_agent_answer(tpath)
    recovered = agent_answer == true_mech
    abstained = agent_answer is None

    # The engine's own (in-process) grade, for the agreement check.
    engine_recovered = None
    if rpath.is_file():
        try:
            engine_recovered = bool(json.loads(rpath.read_text()).get("earned_recovery"))
        except Exception:
            engine_recovered = None
    agrees = (engine_recovered is None) or (engine_recovered == recovered)

    leaked = _truth_leaked(tpath, true_mech)
    scoring = {
        "challenge_id": manifest.get("challenge_id"),
        "scorer": manifest.get("scoring", {}).get("scorer"),
        "inference": {"agent_answer": agent_answer, "true_mechanism": true_mech,
                      "recovered": bool(recovered), "abstained": bool(abstained)},
        "scored_independently": True,
    }
    integrity = {
        "truth_leaked_into_prompt": bool(leaked),
        "engine_grade_agrees_with_independent_score": bool(agrees),
        "engine_recovered": engine_recovered,
        "independent_recovered": bool(recovered),
        "hard_failures": [m for m, bad in
                          (("truth_leaked", leaked), ("engine_score_divergence", not agrees)) if bad],
    }
    return {"scoring": scoring, "integrity": integrity}
