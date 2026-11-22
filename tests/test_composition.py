"""Episode 06: cross-scale composition — molecular feedback sets the population plateau."""
from viva_discovery_showcase.composition import coupled_run, cross_scale_readout


def test_molecular_feedback_sets_population_plateau():
    r = cross_scale_readout()
    pl = [row["plateau_biomass"] for row in r]
    # strong molecular feedback (low mol_Ki) -> high plateau; weak -> low: monotone decreasing
    assert all(pl[i] >= pl[i + 1] for i in range(len(pl) - 1))
    assert pl[0] / pl[-1] > 5.0                      # a real cross-scale effect, not noise
    # byproduct (the interface) rises as feedback weakens
    bp = [row["final_byproduct"] for row in r]
    assert all(bp[i] <= bp[i + 1] for i in range(len(bp) - 1))


def test_coupled_run_returns_trajectory_and_plateau():
    out = coupled_run(2.0)
    assert out["plateau_biomass"] > 0 and len(out["t"]) == len(out["X"]) == len(out["P"])
    assert out["mol_Ki"] == 2.0
