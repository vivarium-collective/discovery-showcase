"""Episode 03 — intervention design: choose the perturbation that discriminates.

Episodes 01-04 so far hand the agent both intervention results. The real scientific step is
*design*: given the competing hypotheses and each one's predicted response to the candidate
interventions, choose the intervention(s) that best separate the hypotheses, under a cost
budget --- before running anything.

This module encodes the predicted-response matrix and a discrimination score, and the filler
(``agent_filler.py --design``) chooses the set. A good design reaches full discrimination with
the fewest interventions; a confounded or single-arm choice leaves hypotheses indistinguishable.
"""
from __future__ import annotations

import itertools

# Predicted qualitative response (regrowth?) of each hypothesis to each intervention,
# derived from the mechanisms (what the agent reasons over at design time, before running).
PREDICTED_RESPONSES = {
    "substrate_exhaustion": {"spike_substrate": True,  "remove_byproduct": False, "dilution_control": False},
    "byproduct_inhibition": {"spike_substrate": False, "remove_byproduct": True,  "dilution_control": True},
    "density_cap":          {"spike_substrate": False, "remove_byproduct": False, "dilution_control": True},
}
HYPOTHESES = tuple(PREDICTED_RESPONSES)
INTERVENTIONS = ("spike_substrate", "remove_byproduct", "dilution_control")


def _signature(hypothesis: str, interventions) -> tuple:
    return tuple(PREDICTED_RESPONSES[hypothesis][i] for i in interventions)


def discrimination_score(interventions) -> float:
    """Fraction of hypothesis pairs the chosen interventions distinguish (1.0 = all separated)."""
    interventions = [i for i in interventions if i in INTERVENTIONS]
    pairs = list(itertools.combinations(HYPOTHESES, 2))
    if not interventions:
        return 0.0
    distinguished = sum(1 for a, b in pairs if _signature(a, interventions) != _signature(b, interventions))
    return distinguished / len(pairs)


def optimal_design() -> list[str]:
    """The smallest intervention set that fully discriminates the hypotheses (greedy)."""
    chosen: list[str] = []
    remaining = list(INTERVENTIONS)
    while discrimination_score(chosen) < 1.0 and remaining:
        # add the intervention that most increases discrimination (ties: declared order)
        best = max(remaining, key=lambda i: discrimination_score(chosen + [i]))
        chosen.append(best)
        remaining.remove(best)
    return chosen


def design_prompt() -> str:
    rows = "\n".join(
        f"  {h}: " + ", ".join(f"{i}={'regrowth' if PREDICTED_RESPONSES[h][i] else 'no'}" for i in INTERVENTIONS)
        for h in HYPOTHESES)
    return (
        "A batch culture plateaued. Three hypotheses explain it, with these PREDICTED responses "
        "to candidate interventions:\n" + rows + "\n\n"
        "Choose the smallest set of interventions to actually run so that, whatever the outcome, "
        "the three hypotheses are fully distinguished. Answer as a JSON list of intervention names, "
        f"from {list(INTERVENTIONS)}."
    )


def score_design(interventions) -> dict:
    """Design quality: discrimination achieved and cost (number of interventions)."""
    return {"interventions": list(interventions),
            "discrimination": discrimination_score(interventions),
            "cost": len([i for i in interventions if i in INTERVENTIONS]),
            "fully_discriminates": discrimination_score(interventions) >= 1.0}
