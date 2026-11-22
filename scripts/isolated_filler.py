#!/usr/bin/env python
"""Bias-isolated, resource-grounded, transcript-recording ``$VIVA_FILLER_CMD``.

A legitimate discovery-engine filler for a real run. It reasons ONLY from:
  - the **experimental evidence** in ``$RUN_OBSERVATION`` (the intervention regrowth results
    — what a real experiment would reveal), and
  - the **knowledge resources** in ``$RESOURCES_DIR`` (general background: candidate mechanisms
    and how interventions discriminate — NOT which mechanism is operative).

It NEVER reads the sealed ground truth (the hidden mechanism, the reference parameters): the
generation request on stdin is used only for its ``id``/``kind``, never for any mechanism it
might carry. Every ``(request, prompt, response, result)`` is appended to ``$RUN_TRANSCRIPT``
(JSONL) so the controlled inputs and the agent's reasoning are recorded for the paper.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

MECHANISMS = ("substrate_exhaustion", "byproduct_inhibition", "density_cap")


def _resources() -> str:
    d = os.environ.get("RESOURCES_DIR")
    if not d or not Path(d).is_dir():
        return ""
    return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(Path(d).glob("*.md")))


def _observation():
    raw = os.environ.get("RUN_OBSERVATION")
    if not raw:
        return None
    try:
        obs = json.loads(Path(raw).read_text()) if os.path.isfile(raw) else json.loads(raw)
        return {"spike_regrowth": bool(obs["spike_regrowth"]), "remove_regrowth": bool(obs["remove_regrowth"])}
    except Exception:
        return None


def _prompt(obs, resources) -> str:
    def yn(b):
        return "resumed growth" if b else "did NOT resume growth"
    return (
        "You are diagnosing why a microbial batch culture stopped growing. Use ONLY the "
        "background knowledge and the experimental evidence below.\n\n"
        "=== Background knowledge ===\n" + (resources or "(none provided)") + "\n\n"
        "=== Experimental evidence ===\n"
        "A batch culture grew then plateaued. Two diagnostic interventions were applied at the plateau:\n"
        f"  - Adding substrate: the culture {yn(obs['spike_regrowth'])}.\n"
        f"  - Removing the accumulated byproduct: the culture {yn(obs['remove_regrowth'])}.\n\n"
        "Name the single mechanism that stopped growth, reasoning from the evidence and background. "
        f"Choose exactly one of {list(MECHANISMS)}. Answer with only the mechanism name."
    )


def _record(entry: dict) -> None:
    tp = os.environ.get("RUN_TRANSCRIPT")
    if not tp:
        return
    Path(tp).parent.mkdir(parents=True, exist_ok=True)
    with open(tp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _backend(prompt: str) -> str:
    cmd = os.environ.get("AGENT_BACKEND_CMD", "claude -p")
    try:
        proc = subprocess.run(cmd, shell=True, input=prompt, capture_output=True, text=True, timeout=600)
        return proc.stdout or ""
    except Exception:
        return ""


def _self_test(obs) -> str | None:
    s, r = obs["spike_regrowth"], obs["remove_regrowth"]
    if s and not r:
        return "substrate_exhaustion"
    if r and not s:
        return "byproduct_inhibition"
    if not s and not r:
        return "density_cap"
    return None


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        req = json.loads(sys.stdin.read() or "{}")
    except Exception:
        req = {}
    req_meta = {"request_id": req.get("id"), "kind": req.get("kind")}  # id/kind only; never the mechanism
    obs = _observation()
    self_test = "--self-test" in argv or os.environ.get("AGENT_FILLER_SELFTEST") == "1"

    if obs is None:
        _record({"ts": dt.datetime.now().isoformat(), **req_meta, "prompt": None,
                 "response": None, "result": {}, "note": "no evidence -> abstain"})
        print(json.dumps({}))
        return 0

    resources = _resources()
    prompt = _prompt(obs, resources)
    if self_test:
        mech, raw = _self_test(obs), "(self-test deterministic reasoner)"
    else:
        raw = _backend(prompt)
        mech = next((m for m in MECHANISMS if m in raw.lower()), None)
    result = {"implements": mech} if mech else {}
    _record({"ts": dt.datetime.now().isoformat(), **req_meta,
             "resources_chars": len(resources), "prompt": prompt, "response": raw, "result": result})
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
