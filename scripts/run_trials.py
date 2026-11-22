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


def _try(fn):
    """Run one trial, returning the record or None on any failure (live backend can hang/error)."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        print(f"  trial failed: {type(e).__name__}", flush=True)
        return None


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="trials-"))
    b_done = b_full = b_min = c_done = c_rec = e_done = e05c = 0
    summary_path = REPO / "workspace" / "reports" / "trials-summary.json"
    for i in range(N):
        b = _try(lambda: run_condition_b(filler_cmd=AGENT, out_dir=tmp / f"b{i}", seed=i))
        if b:
            b_done += 1; b_full += b["fully_discriminating"]; b_min += b["is_minimal_optimal"]
        c = _try(lambda: run_condition_c(sealed_mechanism="byproduct_inhibition", design_filler_cmd=AGENT,
                                         interpret_filler_cmd=INTERP, resources_dir=RES, out_dir=tmp / f"c{i}", seed=i))
        if c:
            c_done += 1; c_rec += c["recovered"]
        e = _try(lambda: run_e05("E05c", out_dir=tmp / f"e{i}", filler_cmd="claude -p", seed=i))
        if e:
            e_done += 1; e05c += e["correct"]
        # write the partial summary after every trial, so a later hang never loses progress
        out = {"attempted": i + 1, "of": N,
               "condition_B_fully_discriminating": f"{b_full}/{b_done}",
               "condition_B_minimal_optimal": f"{b_min}/{b_done}",
               "condition_C_closed_loop_recovered": f"{c_rec}/{c_done}",
               "E05c_construction_correct": f"{e05c}/{e_done}"}
        summary_path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
