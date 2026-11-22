#!/usr/bin/env python
"""Run N live trials of Conditions B, C and Episode 05c; aggregate success rates (for the paper's n)."""
from __future__ import annotations
import sys, tempfile, json
from pathlib import Path
from viva_discovery_showcase.condition_b import run_condition_b
from viva_discovery_showcase.condition_c import run_condition_c
from viva_discovery_showcase.episode05 import run_e05

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "workspace" / "references" / "expert" / "growth-limitation"
AGENT = f"{sys.executable} {REPO/'scripts'/'agent_filler.py'}"
INTERP = f"{sys.executable} {REPO/'scripts'/'isolated_filler.py'}"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="trials-"))
    b_full = b_min = c_rec = e05c = 0
    for i in range(N):
        b = run_condition_b(filler_cmd=AGENT, out_dir=tmp / f"b{i}", seed=i)
        b_full += b["fully_discriminating"]; b_min += b["is_minimal_optimal"]
        c = run_condition_c(sealed_mechanism="byproduct_inhibition", design_filler_cmd=AGENT,
                            interpret_filler_cmd=INTERP, resources_dir=RES, out_dir=tmp / f"c{i}", seed=i)
        c_rec += c["recovered"]
        e = run_e05("E05c", out_dir=tmp / f"e{i}", filler_cmd="claude -p", seed=i)
        e05c += e["correct"]
    out = {"n": N,
           "condition_B_fully_discriminating": f"{b_full}/{N}",
           "condition_B_minimal_optimal": f"{b_min}/{N}",
           "condition_C_closed_loop_recovered": f"{c_rec}/{N}",
           "E05c_construction_correct": f"{e05c}/{N}"}
    print(json.dumps(out, indent=2))
    (REPO / "workspace" / "reports" / "trials-summary.json").write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
