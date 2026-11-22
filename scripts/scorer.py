#!/usr/bin/env python
"""Independent scorer — a SEPARATE process that reads the sealed truth the engine cannot.

  python scripts/scorer.py --manifest challenges/<id>/manifest.yaml --run-dir <dir> [--out <dir>]

Re-derives the score from the run's raw artifacts (transcript + run record) and the sealed truth,
and flags disagreement with the engine's in-process grade. Writes scoring.json + integrity-report.json
to --out (default: <run-dir>/../scoring/<challenge_id>), OUTSIDE the engine's writable workspace.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml
from viva_discovery_showcase.challenge import score_run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    mpath = Path(a.manifest)
    manifest = yaml.safe_load(mpath.read_text())
    sealed = yaml.safe_load((mpath.parent / manifest["scoring"]["sealed_truth_ref"]).read_text())
    result = score_run(manifest, sealed, Path(a.run_dir), seed=a.seed)
    out = Path(a.out) if a.out else Path(a.run_dir).parent / "scoring" / manifest["challenge_id"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "scoring.json").write_text(json.dumps(result["scoring"], indent=2))
    (out / "integrity-report.json").write_text(json.dumps(result["integrity"], indent=2))
    print(json.dumps(result, indent=2))
    return 0 if not result["integrity"]["hard_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
