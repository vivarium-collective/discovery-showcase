#!/usr/bin/env python
"""Run a bias-isolated discovery-engine investigation; record transcript + run record.

  python scripts/run_isolated_investigation.py                         # live claude -p
  python scripts/run_isolated_investigation.py --filler "python scripts/isolated_filler.py --self-test"
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from viva_discovery_showcase.isolated_run import run_isolated

REPO = Path(__file__).resolve().parent.parent
RESOURCES = REPO / "workspace" / "references" / "expert" / "growth-limitation"
OUT = REPO / "workspace" / "reports" / "isolated-runs"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mechanism", default="byproduct_inhibition",
                    choices=["substrate_exhaustion", "byproduct_inhibition", "density_cap"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--filler", default=None, help="$VIVA_FILLER_CMD (default: isolated_filler via claude -p)")
    a = ap.parse_args()
    filler = a.filler or f"{sys.executable} {REPO / 'scripts' / 'isolated_filler.py'}"
    rec = run_isolated(mechanism=a.mechanism, resources_dir=RESOURCES, filler_cmd=filler,
                       out_dir=OUT, seed=a.seed)
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
