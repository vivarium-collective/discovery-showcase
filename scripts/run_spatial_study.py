#!/usr/bin/env python
"""Run the spatial dFBA colony into the spatial-colony study and grade it through the engine.

Needs the `spatial` extra. Reproduces the run-backed spatial study: run spatio-flux's
spatial_many_dfba, emit colony observables, register the run, grade the behavior tests by code.
"""
from __future__ import annotations
import io, json
from pathlib import Path
import ruamel.yaml
from viva_discovery_showcase.spatial_run import run_spatial_colony
from discovery_engine.study.evaluator.outcomes import compute_outcomes

REPO = Path(__file__).resolve().parent.parent
STUDY = REPO / "workspace" / "studies" / "spatial-colony"


def main() -> int:
    r = run_spatial_colony(n_bins=10, n_steps=16, out_dir=STUDY, record=True)
    yaml = ruamel.yaml.YAML()
    doc = yaml.load((STUDY / "study.yaml").read_text())
    doc["runs"] = [{"name": r["run_id"], "composite": doc["baseline"][0]["composite"],
                    "params": {"n_bins": [10, 10]}, "store_path": r["run_id"]}]
    buf = io.StringIO(); yaml.dump(doc, buf); (STUDY / "study.yaml").write_text(buf.getvalue())
    out = compute_outcomes(STUDY, ws_root=REPO)
    print("run-backed spatial grade:", out)
    for run in yaml.load((STUDY / "study.yaml").read_text()).get("runs", []):
        for tn, co in (run.get("computed_outcomes") or {}).items():
            if isinstance(co, dict) and "result" in co:
                print(f"  {tn}: {co['result']}  ({co.get('detail')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
