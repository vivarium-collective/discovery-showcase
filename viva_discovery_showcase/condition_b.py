"""Condition B --- the agent DESIGNS the experiment (rung 3: informative experimental choice).

Unlike Condition A (interpret supplied intervention outcomes), here the agent is given the
candidate models' predicted-response matrix and the intervention menu, and must CHOOSE which
interventions to run --- before seeing any outcome. We score the design it picks: whether it
reaches full discrimination, how many interventions it spends, and whether it avoids the
confounded decoy (``dilution_control``, which cannot separate byproduct from density).

The agent's choice, not a supplied answer, is the result. The independent scorer
(``challenge.score_design_run``) re-derives the discrimination from the chosen set.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_condition_b(*, filler_cmd: str, out_dir, seed: int = 0) -> dict:
    """Ask the agent to choose discriminating interventions; score and record the design."""
    from viva_discovery_showcase.design import (
        INTERVENTIONS, design_prompt, discrimination_score, optimal_design, score_design,
    )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(f"{filler_cmd} --design", shell=True, capture_output=True, text=True, timeout=600)
    try:
        chosen_raw = json.loads(proc.stdout or "{}").get("interventions", [])
    except Exception:
        chosen_raw = []
    chosen = [i for i in chosen_raw if i in INTERVENTIONS]      # drop anything off the menu
    off_menu = [i for i in chosen_raw if i not in INTERVENTIONS]

    disc = discrimination_score(chosen)
    sd = score_design(chosen)
    optimal = optimal_design()

    transcript = out / f"transcript-design-seed{seed}.jsonl"
    transcript.write_text(json.dumps({
        "kind": "design", "prompt": design_prompt(), "response": proc.stdout,
        "result": {"interventions": chosen},
    }) + "\n", encoding="utf-8")

    record = {
        "condition": "B", "seed": seed,
        "chosen_interventions": chosen,
        "off_menu_interventions": off_menu,
        "discrimination": disc,                       # fraction of mechanism pairs separated
        "cost": sd.get("cost"),
        "fully_discriminating": disc >= 1.0,
        "is_minimal_optimal": set(chosen) == set(optimal),
        "avoided_decoy": "dilution_control" not in chosen,
        "optimal": optimal,
        "transcript": str(transcript),
    }
    (out / f"run-record-design-seed{seed}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record
