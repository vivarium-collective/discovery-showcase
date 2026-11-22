"""Investigation A — the hidden Monod reference generator behaves correctly.

These tests pin the *simulated system*, not the engine's reasoning. They prove
that each hidden-truth preset (1) grows then plateaus, (2) plateaus by the
intended mechanism, and (3) responds to the two discriminating interventions
exactly as the Episode 03/04 benchmark requires --- including that the H3 decoy
is separated by *neither* intervention (the abstention case).
"""
from __future__ import annotations

import math

import pytest

from viva_discovery_showcase.growth import (
    MonodGrowth,
    REFERENCE_PRESETS,
    dilution_control,
    is_regrowth,
    max_growth_rate,
    remove_byproduct,
    run_batch,
    spike_substrate,
)

T_PLATEAU = 40.0  # by this time every preset has stopped growing


def _final(traj, key):
    return traj[key][-1]


@pytest.mark.parametrize("mech", ["substrate", "byproduct", "decoy"])
def test_grows_then_plateaus(mech):
    params = REFERENCE_PRESETS[mech]
    traj = run_batch(params, t_end=60.0)
    # grew substantially from the inoculum
    assert _final(traj, "X") > 5 * params["X0"]
    # and has stopped growing by the plateau time
    assert max_growth_rate(traj, t_from=T_PLATEAU) < 0.05 * params["mu_max"]


def test_plateau_mechanism_is_as_intended():
    sub = run_batch(REFERENCE_PRESETS["substrate"], t_end=60.0)
    byp = run_batch(REFERENCE_PRESETS["byproduct"], t_end=60.0)
    dec = run_batch(REFERENCE_PRESETS["decoy"], t_end=60.0)

    # H1: substrate is exhausted at plateau
    assert _final(sub, "S") < 0.05 * REFERENCE_PRESETS["substrate"]["S0"]
    # H2: substrate still plentiful, byproduct near its inhibition constant
    assert _final(byp, "S") > 0.5 * REFERENCE_PRESETS["byproduct"]["S0"]
    assert _final(byp, "P") > 0.5 * REFERENCE_PRESETS["byproduct"]["K_I"]
    # H3: substrate plentiful, byproduct ~0, biomass pinned at the density cap
    assert _final(dec, "S") > 0.5 * REFERENCE_PRESETS["decoy"]["S0"]
    assert _final(dec, "P") < 0.05
    assert _final(dec, "X") > 0.8 * REFERENCE_PRESETS["decoy"]["X_cap"]


# The discrimination contract: (truth) x (intervention) -> regrowth?
DISCRIMINATION = {
    "substrate": {"spike": True, "remove": False},
    "byproduct": {"spike": False, "remove": True},
    "decoy": {"spike": False, "remove": False},
}


@pytest.mark.parametrize("mech", ["substrate", "byproduct", "decoy"])
def test_intervention_discrimination_table(mech):
    params = REFERENCE_PRESETS[mech]
    spike = run_batch(params, t_end=90.0, intervention=spike_substrate, t_intervene=45.0)
    remove = run_batch(params, t_end=90.0, intervention=remove_byproduct, t_intervene=45.0)

    assert is_regrowth(spike, params) is DISCRIMINATION[mech]["spike"], (
        f"{mech}: spike-substrate regrowth should be {DISCRIMINATION[mech]['spike']}"
    )
    assert is_regrowth(remove, params) is DISCRIMINATION[mech]["remove"], (
        f"{mech}: remove-byproduct regrowth should be {DISCRIMINATION[mech]['remove']}"
    )


@pytest.mark.parametrize("mech", ["substrate", "byproduct", "decoy"])
def test_decoy_is_not_separable_by_the_two_arms(mech):
    """The two arms separate H1 vs H2, but H3 (decoy) triggers neither ->
    the engine must ABSTAIN rather than force a 2-way answer."""
    params = REFERENCE_PRESETS[mech]
    spike = run_batch(params, t_end=90.0, intervention=spike_substrate, t_intervene=45.0)
    remove = run_batch(params, t_end=90.0, intervention=remove_byproduct, t_intervene=45.0)
    separated = is_regrowth(spike, params) or is_regrowth(remove, params)
    assert separated == (mech != "decoy")


def test_monodgrowth_process_registers_and_runs():
    """The Process is discoverable via the workspace core and integrates one step."""
    from viva_discovery_showcase.core import build_core

    core = build_core()
    assert "MonodGrowth" in core.link_registry, "MonodGrowth not registered in workspace core"

    proc = MonodGrowth(config=dict(REFERENCE_PRESETS["substrate"]), core=core)
    out = proc.update({"biomass": 0.05, "substrate": 5.0, "byproduct": 0.0}, 1.0)
    assert out["biomass"] > 0.05  # grew over the interval
    assert out["substrate"] < 5.0  # consumed substrate
