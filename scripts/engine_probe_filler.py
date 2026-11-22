#!/usr/bin/env python
"""Measurement probe: record every GenerationRequest the engine emits, then abstain.

Captures what the engine ASKS (kind, target, produces, rationale, and the full context
— including whether it surfaces competing_predictions / contracts) to $ENGINE_TRANSCRIPT,
and returns {} so nothing is fabricated. Pure instrumentation of the engine's behavior.
"""
import json, os, sys, datetime
from pathlib import Path

req = json.loads(sys.stdin.read() or "{}")
tp = os.environ.get("ENGINE_TRANSCRIPT")
if tp:
    Path(tp).parent.mkdir(parents=True, exist_ok=True)
    with open(tp, "a") as f:
        f.write(json.dumps({"ts": datetime.datetime.now().isoformat(),
                            "kind": req.get("kind"), "target": req.get("target"),
                            "produces": req.get("produces"), "rationale": req.get("rationale"),
                            "context_keys": sorted((req.get("context") or {}).keys()),
                            "context": req.get("context")}) + "\n")
print(json.dumps({}))
