#!/usr/bin/env python
"""Run the growth-limitation ablation (Episodes 01-04) and print the results table.

Examples:
  python scripts/run_ablation.py                      # oracle + deterministic_only floor
  python scripts/run_ablation.py --real-agent "python scripts/agent_filler.py"            # real agent via $AGENT_BACKEND_CMD (claude -p)
  python scripts/run_ablation.py --real-agent "python scripts/agent_filler.py --self-test"  # wiring check (deterministic reasoner)
"""
from __future__ import annotations

import argparse

from viva_discovery_showcase.ablation import render, run_ablation


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mechanism", default="byproduct_inhibition",
                    choices=["substrate_exhaustion", "byproduct_inhibition", "density_cap"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--real-agent", dest="real", default=None,
                    help="$VIVA_FILLER_CMD for the real-agent config (omit to skip it)")
    a = ap.parse_args()
    results = run_ablation(mechanism=a.mechanism, seeds=tuple(a.seeds), real_filler_cmd=a.real)
    print(f"growth-limitation ablation — concealed mechanism: {a.mechanism}, seeds={a.seeds}\n")
    print(render(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
