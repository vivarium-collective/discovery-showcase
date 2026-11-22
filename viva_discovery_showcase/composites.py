"""Composite generators for the showcase workspace (rendered in the workbench catalog).

``monod_batch`` wires the ``MonodGrowth`` process to biomass/substrate/byproduct stores --- the
baseline composite the growth-limitation study runs. Registered via ``@composite_generator`` so
``discover_generators()`` (and the dashboard catalog) find it.
"""
from __future__ import annotations

from process_bigraph.composite_generator import composite_generator

from viva_discovery_showcase.growth import MECHANISM_LABELS, REFERENCE_PRESETS

_BIG = 1e12  # finite stand-in for "off" (K_I / X_cap); REFERENCE_PRESETS use inf


def _params(mechanism: str) -> dict:
    preset = REFERENCE_PRESETS[MECHANISM_LABELS.get(mechanism, mechanism)]
    return {k: (_BIG if v == float("inf") else v) for k, v in preset.items()}


@composite_generator(
    name="monod_batch",
    description="Well-mixed Monod batch culture: MonodGrowth on biomass/substrate/byproduct, "
                "with toggleable product inhibition and density cap (the growth-limitation baseline).",
    parameters={"mechanism": {"type": "string", "default": "byproduct_inhibition",
                              "description": "plateau mechanism preset "
                                             "(substrate_exhaustion | byproduct_inhibition | density_cap)"}},
    default_n_steps=90,
)
def monod_batch(core=None, *, mechanism: str = "byproduct_inhibition", **_) -> dict:
    p = _params(mechanism)
    return {
        "biomass": p["X0"],
        "substrate": p["S0"],
        "byproduct": 0.0,
        "monod_growth": {
            "_type": "process",
            "address": "local:MonodGrowth",
            "config": {k: p[k] for k in ("mu_max", "K_S", "Y_XS", "Y_PX", "K_I", "n_I", "X_cap")},
            "interval": 1.0,
            "inputs": {"biomass": ["biomass"], "substrate": ["substrate"], "byproduct": ["byproduct"]},
            "outputs": {"biomass": ["biomass"], "substrate": ["substrate"], "byproduct": ["byproduct"]},
        },
    }
