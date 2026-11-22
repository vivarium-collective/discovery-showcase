#!/usr/bin/env python
"""Condition C: closed loop (design -> execute -> evaluate) on the growth challenge."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml
from viva_discovery_showcase.condition_c import run_condition_c
from viva_discovery_showcase.challenge import score_loop_run

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "workspace" / "references" / "expert" / "growth-limitation"
OUT = REPO / "workspace" / "reports" / "condition-c"
MANIFEST = REPO / "challenges" / "growth-plateau-H2-001" / "manifest.yaml"
SEALED = REPO / "challenges" / "growth-plateau-H2-001" / ".sealed" / "truth.yaml"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    st = " --self-test" if a.self_test else ""
    design = f"{sys.executable} {REPO/'scripts'/'agent_filler.py'}{st}"
    interp = f"{sys.executable} {REPO/'scripts'/'isolated_filler.py'}{st}"
    rec = run_condition_c(sealed_mechanism="byproduct_inhibition", design_filler_cmd=design,
                          interpret_filler_cmd=interp, resources_dir=RES, out_dir=OUT, seed=a.seed)
    score = score_loop_run(yaml.safe_load(MANIFEST.read_text()), yaml.safe_load(SEALED.read_text()),
                           OUT, seed=a.seed)
    print(json.dumps({"run": rec, "independent_score": score}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
