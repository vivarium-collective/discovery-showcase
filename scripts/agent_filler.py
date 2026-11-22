#!/usr/bin/env python
"""`$VIVA_FILLER_CMD` filler for the growth-limitation benchmark (Episodes 01-04).

The discovery engine shells out to this command on the build side of the recovery loop
(`recovery_build.real_build_hook`): it receives the capability gap as JSON on stdin and
must print JSON naming the mechanism to implement --- `{"implements": "<mechanism>"}`.

**Reasons from evidence, not the answer key.** The gap happens to carry the concealed
mechanism (the engine needs it for coverage), but a real agent must not peek at it. This
filler deliberately IGNORES the gap's mechanism and instead reads the *experimental
observation* --- the regrowth pattern under the two diagnostic interventions --- from
`$GROWTH_OBSERVATION` (a JSON path or inline JSON: `{"spike_regrowth": bool,
"remove_regrowth": bool}`), and infers which mechanism explains the plateau:

    spike rescues, remove does not  -> substrate_exhaustion
    remove rescues, spike does not  -> byproduct_inhibition
    neither rescues                 -> density_cap   (or abstain)

Backends:
- default: a real reasoning agent via `$AGENT_BACKEND_CMD` (e.g. `claude -p`), given the
  observation + hypotheses as a prompt; its free-text answer is matched to a mechanism.
- `--self-test` (or `$AGENT_FILLER_SELFTEST=1`): a deterministic correct reasoner, for
  wiring tests and as a "perfect reasoner" reference. No LLM call.

If no observation is available, the filler names no mechanism (prints `{}`): the engine
then leaves the gap needs_author and nothing is built --- an honest **abstention**.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

MECHANISMS = ("substrate_exhaustion", "byproduct_inhibition", "density_cap")


def _load_observation() -> dict | None:
    raw = os.environ.get("GROWTH_OBSERVATION")
    if not raw:
        return None
    try:
        if os.path.isfile(raw):
            raw = open(raw, encoding="utf-8").read()
        obs = json.loads(raw)
        return {"spike_regrowth": bool(obs["spike_regrowth"]),
                "remove_regrowth": bool(obs["remove_regrowth"])}
    except Exception:
        return None


def _infer_deterministic(obs: dict) -> str | None:
    spike, remove = obs["spike_regrowth"], obs["remove_regrowth"]
    if spike and not remove:
        return "substrate_exhaustion"
    if remove and not spike:
        return "byproduct_inhibition"
    if not spike and not remove:
        return "density_cap"
    return None  # both rescued -> ambiguous -> abstain


def _prompt(obs: dict) -> str:
    def yn(b):
        return "resumed growth" if b else "did NOT resume growth"
    return (
        "A microbial batch culture grew exponentially, then stopped (plateaued) while the "
        "baseline growth model predicted continued growth. Two diagnostic interventions were "
        "applied at the plateau:\n"
        f"  - Adding fresh substrate: the culture {yn(obs['spike_regrowth'])}.\n"
        f"  - Removing the accumulated byproduct: the culture {yn(obs['remove_regrowth'])}.\n\n"
        "Which single mechanism best explains the plateau? Choose exactly one:\n"
        "  - substrate_exhaustion (adding substrate rescues; removing byproduct does not)\n"
        "  - byproduct_inhibition (removing byproduct rescues; adding substrate does not)\n"
        "  - density_cap (neither rescues)\n"
        "Answer with only the mechanism name."
    )


def _match_mechanism(text: str) -> str | None:
    low = (text or "").lower()
    for m in MECHANISMS:
        if m in low:
            return m
    return None


def _ask_backend(obs: dict) -> str | None:
    cmd = os.environ.get("AGENT_BACKEND_CMD", "claude -p")
    try:
        proc = subprocess.run(cmd, shell=True, input=_prompt(obs),
                              capture_output=True, text=True, timeout=600)
    except Exception:
        return None
    return _match_mechanism(proc.stdout)


def _ask_backend_design() -> list:
    from viva_discovery_showcase.design import INTERVENTIONS, design_prompt
    cmd = os.environ.get("AGENT_BACKEND_CMD", "claude -p")
    try:
        proc = subprocess.run(cmd, shell=True, input=design_prompt(),
                              capture_output=True, text=True, timeout=600)
    except Exception:
        return []
    low = (proc.stdout or "").lower()
    return [i for i in INTERVENTIONS if i in low]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    self_test = "--self-test" in argv or os.environ.get("AGENT_FILLER_SELFTEST") == "1"

    if "--design" in argv:
        # Episode 03: choose the discriminating interventions (before running anything).
        _ = sys.stdin.read()
        from viva_discovery_showcase.design import optimal_design
        chosen = optimal_design() if self_test else _ask_backend_design()
        print(json.dumps({"interventions": chosen}))
        return 0

    _ = sys.stdin.read()  # drain the gap/request JSON (contract; not used for the answer)
    obs = _load_observation()
    if obs is None:
        print(json.dumps({}))  # no evidence -> name no mechanism -> abstain
        return 0
    mech = _infer_deterministic(obs) if self_test else _ask_backend(obs)
    print(json.dumps({"implements": mech} if mech else {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
