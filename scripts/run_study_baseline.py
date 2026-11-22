#!/usr/bin/env python
"""Run the growth-plateau baseline through the engine and grade it run-backed.

Runs monod_batch (byproduct inhibition) into the study dir, emits a RunReader-readable parquet
store, registers the run, and grades the end-state behavior test via compute_outcomes, persisting
the earned grade into study.yaml. The bulky run store + runs.db are gitignored; this script
regenerates them (the graded computed_outcomes stay in study.yaml).
"""
from __future__ import annotations
import io
from pathlib import Path
import ruamel.yaml
from viva_discovery_showcase.baseline_run import run_baseline
from discovery_engine.study.evaluator.outcomes import compute_outcomes

REPO = Path(__file__).resolve().parent.parent
STUDY = REPO / "workspace" / "studies" / "growth-plateau"


def main() -> int:
    r = run_baseline("byproduct_inhibition", out_dir=STUDY, record=True)
    yaml = ruamel.yaml.YAML()
    doc = yaml.load((STUDY / "study.yaml").read_text())
    doc["runs"] = [{"name": r["run_id"], "composite": doc["baseline"][0]["composite"],
                    "params": {"mechanism": "byproduct_inhibition"}, "store_path": r["run_id"]}]
    buf = io.StringIO(); yaml.dump(doc, buf); (STUDY / "study.yaml").write_text(buf.getvalue())
    out = compute_outcomes(STUDY, ws_root=REPO)
    print("run-backed grade:", out)
    for run in yaml.load((STUDY / "study.yaml").read_text()).get("runs", []):
        for tn, co in (run.get("computed_outcomes") or {}).items():
            if isinstance(co, dict) and "result" in co:
                print(f"  {tn}: {co['result']}  ({co.get('detail')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
