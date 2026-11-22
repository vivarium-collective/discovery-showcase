#!/usr/bin/env python
"""Bias-isolated, resource-grounded, transcript-recording ``$VIVA_FILLER_CMD``.

A legitimate discovery-engine filler for a real run. It reasons from:
  - the **candidate model contracts** (each model DECLARES its mechanism + what to expect under
    the diagnostic interventions — the process contract is the channel the agent reads),
  - the **experimental evidence** in ``$RUN_OBSERVATION`` (the intervention regrowth results
    — what a real experiment would reveal), and
  - the **knowledge resources** in ``$RESOURCES_DIR`` (general background).

The agent is EXPECTED to read a model's mechanism from its contract; what stays sealed is the
**ground truth** — which model generated the observed data — which it earns by matching the
declared expectations against the evidence (contracts say what to expect; only evidence says
which model is operative). Every ``(request, prompt, response, result)`` is appended to
``$RUN_TRANSCRIPT`` (JSONL) so the controlled inputs + reasoning are recorded for the paper.
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


def _contracts() -> list[dict]:
    """The declared contracts of the candidate models (read from the process contract)."""
    try:
        from viva_discovery_showcase.growth import candidate_contracts
        return candidate_contracts()
    except Exception:
        return []


def _prompt(obs, resources, contracts) -> str:
    def yn(b):
        return "resumed growth" if b else "did NOT resume growth"
    contract_lines = "\n".join(
        f"  - {c['mechanism']}: {c['summary']}.\n"
        f"      declared expectation: spike substrate -> {c['expected_intervention_response']['spike_substrate']}; "
        f"remove byproduct -> {c['expected_intervention_response']['remove_byproduct']}."
        for c in contracts) or "  (no candidate contracts provided)"
    return (
        "You are diagnosing which candidate model explains why a microbial batch culture stopped "
        "growing. Each candidate model declares, in its process contract, its mechanism and what "
        "to expect under the diagnostic interventions. Read those contracts and match them to the "
        "observed evidence.\n\n"
        "=== Candidate model contracts (declared mechanism + expectations) ===\n"
        + contract_lines + "\n\n"
        "=== Background knowledge ===\n" + (resources or "(none provided)") + "\n\n"
        "=== Observed experimental evidence ===\n"
        "A batch culture grew then plateaued. Two diagnostic interventions were applied at the plateau:\n"
        f"  - Adding substrate: the culture {yn(obs['spike_regrowth'])}.\n"
        f"  - Removing the accumulated byproduct: the culture {yn(obs['remove_regrowth'])}.\n\n"
        "Which candidate's declared expectations does the evidence satisfy? That model is the one "
        f"that generated the data. Answer with only its mechanism name, one of {list(MECHANISMS)}."
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
    req_meta = {"request_id": req.get("id"), "kind": req.get("kind")}
    obs = _observation()
    self_test = "--self-test" in argv or os.environ.get("AGENT_FILLER_SELFTEST") == "1"

    if obs is None:
        # Contracts declare what to EXPECT; only evidence says which model is operative.
        # With no evidence, the agent cannot determine the answer -> abstain.
        _record({"ts": dt.datetime.now().isoformat(), **req_meta, "prompt": None,
                 "response": None, "result": {}, "note": "no evidence -> abstain (contracts alone are insufficient)"})
        print(json.dumps({}))
        return 0

    resources = _resources()
    contracts = _contracts()
    prompt = _prompt(obs, resources, contracts)
    if self_test:
        mech, raw = _self_test(obs), "(self-test deterministic reasoner)"
    else:
        raw = _backend(prompt)
        mech = next((m for m in MECHANISMS if m in raw.lower()), None)
    result = {"implements": mech} if mech else {}
    _record({"ts": dt.datetime.now().isoformat(), **req_meta,
             "candidate_contracts": [c["mechanism"] for c in contracts],
             "resources_chars": len(resources), "prompt": prompt, "response": raw, "result": result})
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
