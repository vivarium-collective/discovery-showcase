"""Bias-isolated engine run for the growth-limitation investigation (prototype).

Runs the discovery engine's recovery loop on a SEALED concealed mechanism. The agent (the
isolated filler) is given only the experimental evidence (intervention regrowth) + the knowledge
resources, never the mechanism; the engine grades its inference against the sealed truth, so a
recovery is EARNED, not authored. Everything the agent saw and produced is recorded to a
transcript, and a run record captures the controlled inputs + the earned outcome --- the paper's
documentation of a legitimate run.

This is the showcase-side prototype; the reusable parts (sealed evidence injection, resource
grounding, transcript recording, filler sandboxing) are intended to lift into discovery-engine.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from viva_discovery_showcase.ablation import observation_for


def run_isolated(*, mechanism: str = "byproduct_inhibition", resources_dir, filler_cmd: str,
                 out_dir, seed: int = 0) -> dict:
    """One bias-isolated run on a sealed ``mechanism``. Returns the run record."""
    from discovery_engine.benchmark.recovery_metrics import score_recovery
    from discovery_engine.benchmark.recovery_runner import RecoveryConfig, run_recovery_benchmark

    import viva_discovery_showcase.benchmark_provider as bp

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    transcript = out / f"transcript-{mechanism}-seed{seed}.jsonl"
    if transcript.exists():
        transcript.unlink()

    # Evaluator-only: derive the experimental evidence the agent is shown (the intervention
    # regrowth pattern). The mechanism label itself is NEVER passed to the filler.
    evidence = observation_for(mechanism, seed=seed)

    ws = Path(tempfile.mkdtemp(prefix="isolated-"))
    bundle = bp.build(ws, mechanism=mechanism)

    # Inject the controlled inputs into the filler's environment (sealed: only evidence +
    # resources + transcript path; no mechanism, no ground-truth path).
    keys = {"RUN_OBSERVATION": json.dumps(evidence),
            "RESOURCES_DIR": str(Path(resources_dir).resolve()),
            "RUN_TRANSCRIPT": str(transcript)}
    prev = {k: os.environ.get(k) for k in keys}
    os.environ.update(keys)
    try:
        cfg = RecoveryConfig("real_agent_isolated", build_hook_factory=None)
        result = run_recovery_benchmark(bundle.scenario, cfg,
                                        build_hook=bp.real_build_hook(filler_cmd),
                                        runner=bundle.runner)
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    metrics = score_recovery(result, bundle.scenario.ground_truth)
    transcript_entries = []
    if transcript.exists():
        transcript_entries = [json.loads(line) for line in transcript.read_text().splitlines() if line.strip()]
    record = {
        "investigation": "growth-limitation",
        "sealed_mechanism": mechanism,          # evaluator-only; not shown to the agent
        "seed": seed,
        "evidence_shown_to_agent": evidence,    # the regrowth pattern (legitimate experimental result)
        "resources_dir": str(resources_dir),
        "filler_cmd": filler_cmd,
        "earned_recovery": bool(metrics.mechanism_recovered),
        "heldout_error": metrics.held_out_error,
        "ran": metrics.ran,
        "transcript": str(transcript),
        "transcript_entries": len(transcript_entries),
    }
    (out / f"run-record-{mechanism}-seed{seed}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def transcript_mentions_sealed_mechanism(transcript_path, mechanism: str) -> bool:
    """Isolation audit: did any prompt sent to the agent assert the sealed mechanism as the
    answer? (The candidate list naming all mechanisms is fine; stating the operative one is not.)"""
    text = Path(transcript_path).read_text(encoding="utf-8") if Path(transcript_path).exists() else ""
    leak_phrases = [f"the mechanism is {mechanism}", f"operative mechanism: {mechanism}",
                    f"true mechanism is {mechanism}", f"caused by {mechanism}"]
    low = text.lower()
    return any(p in low for p in leak_phrases)
