#!/usr/bin/env python
"""Episode 05 ladder: evaluate (E05a) / select (E05b) / construct (E05c) a model revision."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from viva_discovery_showcase.episode05 import run_e05, LEVELS

OUT = Path(__file__).resolve().parent.parent / "workspace" / "reports" / "episode05"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--level", choices=list(LEVELS), default=None, help="one level (default: all)")
    a = ap.parse_args()
    levels = [a.level] if a.level else list(LEVELS)
    for lvl in levels:
        rec = run_e05(lvl, out_dir=OUT, self_test=a.self_test)
        print(f"{lvl} ({rec['capability']}): answer={rec['answer']} correct={rec['correct']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
