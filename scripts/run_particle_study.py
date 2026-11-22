#!/usr/bin/env python
"""Run the agent-based particle+dFBA colony into the particle-colony study and grade it.

Needs the `spatial` extra. Reproduces the run-backed particle study: run spatio-flux's
br_particles_dfba, emit colony observables, register the run, grade the behavior tests by code.
"""
from __future__ import annotations
import io
from pathlib import Path
import ruamel.yaml
from viva_discovery_showcase.particle_run import run_particle_colony
from discovery_engine.study.evaluator.outcomes import compute_outcomes

REPO = Path(__file__).resolve().parent.parent
STUDY = REPO / "workspace" / "studies" / "particle-colony"


def main() -> int:
    r = run_particle_colony(n_steps=18, seed=0, out_dir=STUDY, record=True)
    yaml = ruamel.yaml.YAML()
    doc = yaml.load((STUDY / "study.yaml").read_text())
    doc["runs"] = [{"name": r["run_id"], "composite": doc["baseline"][0]["composite"],
                    "params": {}, "store_path": r["run_id"]}]
    buf = io.StringIO(); yaml.dump(doc, buf); (STUDY / "study.yaml").write_text(buf.getvalue())
    print("run-backed particle grade:", compute_outcomes(STUDY, ws_root=REPO))
    for run in yaml.load((STUDY / "study.yaml").read_text()).get("runs", []):
        for tn, co in (run.get("computed_outcomes") or {}).items():
            if isinstance(co, dict) and "result" in co:
                print(f"  {tn}: {co['result']}  ({co.get('detail')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
