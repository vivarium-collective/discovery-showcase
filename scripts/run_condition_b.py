#!/usr/bin/env python
"""Condition B: the agent designs the experiment (chooses discriminating interventions)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from viva_discovery_showcase.condition_b import run_condition_b
from viva_discovery_showcase.challenge import score_design_run

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "workspace" / "reports" / "condition-b"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true", help="deterministic optimal design")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    filler = f"{sys.executable} {REPO/'scripts'/'agent_filler.py'}" + (" --self-test" if a.self_test else "")
    rec = run_condition_b(filler_cmd=filler, out_dir=OUT, seed=a.seed)
    score = score_design_run(OUT, seed=a.seed)   # independent scoring
    print(json.dumps({"run": rec, "independent_score": score}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
