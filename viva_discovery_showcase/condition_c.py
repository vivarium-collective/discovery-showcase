"""Condition C --- closed loop (rung 3+): design -> execute -> evaluate in one run.

The agent first CHOOSES the interventions (Condition B), those interventions are executed, and the
agent then INTERPRETS the outcomes of its OWN chosen experiment to identify the mechanism. Unlike
Condition A (interpret supplied outcomes) or B (design only), the evidence the agent reasons from
is the evidence its own experiment produced --- no supplied outcomes, no hidden script.

Honesty: recovery is credited only when the agent's design is actually sufficient to discriminate
(it chose both the substrate and byproduct interventions). A design that cannot discriminate yields
an inadequate experiment --- a valid negative result, not a recovery.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def run_condition_c(*, sealed_mechanism: str, design_filler_cmd: str, interpret_filler_cmd: str,
                    resources_dir, out_dir, seed: int = 0) -> dict:
    from viva_discovery_showcase.ablation import observation_for
    from viva_discovery_showcase.condition_b import run_condition_b

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. DESIGN: the agent chooses interventions, with no outcomes yet.
    design = run_condition_b(filler_cmd=design_filler_cmd, out_dir=out / "design", seed=seed)
    chosen = design["chosen_interventions"]
    sufficient = ("spike_substrate" in chosen) and ("remove_byproduct" in chosen)

    # 2. EXECUTE: the sealed mechanism's true outcomes; expose only the interventions the agent chose.
    truth = observation_for(sealed_mechanism, seed=seed)       # {spike_regrowth, remove_regrowth}
    exposed = {}
    if "spike_substrate" in chosen:
        exposed["spike_regrowth"] = truth["spike_regrowth"]
    if "remove_byproduct" in chosen:
        exposed["remove_regrowth"] = truth["remove_regrowth"]

    # 3. INTERPRET: the agent infers the mechanism from its OWN experiment's outcomes.
    transcript = out / f"transcript-{sealed_mechanism}-seed{seed}.jsonl"
    env = dict(os.environ)
    env["RUN_OBSERVATION"] = json.dumps({"spike_regrowth": bool(exposed.get("spike_regrowth", False)),
                                         "remove_regrowth": bool(exposed.get("remove_regrowth", False))})
    env["RESOURCES_DIR"] = str(Path(resources_dir).resolve())
    env["RUN_TRANSCRIPT"] = str(transcript)
    proc = subprocess.run(interpret_filler_cmd, shell=True, input="{}", capture_output=True,
                          text=True, env=env, timeout=600)
    try:
        answer = json.loads(proc.stdout or "{}").get("implements")
    except Exception:
        answer = None

    recovered = bool(sufficient and answer == sealed_mechanism)
    record = {
        "condition": "C", "sealed_mechanism": sealed_mechanism, "seed": seed,
        "chosen_interventions": chosen,
        "design_discrimination": design["discrimination"],
        "design_minimal": design["is_minimal_optimal"],
        "design_sufficient": bool(sufficient),
        "exposed_outcomes": exposed,
        "agent_answer": answer,
        "recovered": recovered,
        "loop_closed": bool(chosen) and (answer is not None or not sufficient),
        "transcript": str(transcript),
    }
    (out / f"run-record-{sealed_mechanism}-seed{seed}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record
