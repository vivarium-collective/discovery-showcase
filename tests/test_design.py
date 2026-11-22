"""Episode 03 — intervention design: the agent chooses a discriminating perturbation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from viva_discovery_showcase.design import (
    discrimination_score,
    optimal_design,
    score_design,
)

FILLER = str(Path(__file__).resolve().parent.parent / "scripts" / "agent_filler.py")


def test_discrimination_score_separates_hypotheses():
    # a single arm cannot separate all three; the right pair can
    assert discrimination_score(["spike_substrate"]) < 1.0
    assert discrimination_score(["dilution_control"]) < 1.0           # confounded
    assert discrimination_score(["spike_substrate", "remove_byproduct"]) == 1.0
    assert discrimination_score([]) == 0.0


def test_optimal_design_is_minimal_and_full():
    chosen = optimal_design()
    s = score_design(chosen)
    assert s["fully_discriminates"] is True
    assert s["cost"] == 2            # two interventions suffice; three is wasteful


def test_filler_design_mode_self_test_chooses_full_discriminating_set():
    out = subprocess.run([sys.executable, FILLER, "--design", "--self-test"],
                         input="{}", capture_output=True, text=True)
    chosen = json.loads(out.stdout)["interventions"]
    assert discrimination_score(chosen) == 1.0
    assert len(chosen) == 2
