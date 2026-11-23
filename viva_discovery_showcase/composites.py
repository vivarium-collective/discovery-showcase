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
    out = {k: (_BIG if v == float("inf") else v) for k, v in preset.items()}
    out.setdefault("n_I", 1.0)  # only the byproduct preset sets a Hill coefficient; others: classic term
    return out


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


@composite_generator(
    name="pathway_pulse",
    description="Two-step metabolic pathway S->I->P with optional product-feedback inhibition, "
                "pulsed with substrate after equilibration. The peak intermediate I discriminates the "
                "feedback mechanism; used to grade the structural revision through the engine.",
    parameters={
        "model": {"type": "string", "default": "structural",
                  "description": "which model to run (true | baseline | refit | structural)"},
        "pulse": {"type": "float", "default": 5.0, "description": "substrate pulse magnitude (held-out)"},
        "train_pulse": {"type": "float", "default": 3.0, "description": "pulse the revisions were fit on"},
    },
    default_n_steps=40,
)
def pathway_pulse(core=None, *, model: str = "structural", pulse: float = 5.0,
                  train_pulse: float = 3.0, **_) -> dict:
    from viva_discovery_showcase.pathway import resolve_pathway
    m = resolve_pathway(model, train_pulse)
    return {
        "S": 2.0, "I": 0.0, "P": 0.0,
        "pathway": {
            "_type": "process",
            "address": "local:PathwayProcess",
            "config": {"k1": m.k1, "k2": m.k2, "Km1": m.Km1, "Km2": m.Km2,
                       "feedback": bool(m.feedback), "Ki": m.Ki, "n": m.n,
                       "pulse": float(pulse), "t_pulse": 8.0, "sub_dt": 0.02},
            "interval": 1.0,
            "inputs": {"S": ["S"], "I": ["I"], "P": ["P"], "global_time": ["global_time"]},
            "outputs": {"S": ["S"], "I": ["I"], "P": ["P"]},
        },
    }
