#!/usr/bin/env python
"""Strict validation of a challenge manifest. Exit 0 = valid, 1 = errors."""
from __future__ import annotations
import sys
from pathlib import Path
import yaml
from viva_discovery_showcase.challenge import validate_manifest


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: validate_manifest.py <manifest.yaml>"); return 2
    manifest = yaml.safe_load(Path(argv[0]).read_text())
    errs = validate_manifest(manifest)
    if errs:
        print(f"INVALID: {len(errs)} error(s)")
        for e in errs:
            print("  -", e)
        return 1
    print(f"valid: {manifest['challenge_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
