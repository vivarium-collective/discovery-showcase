"""The showcase's domain vocabulary for the discovery engine's capability router.

The engine's model architect (``discovery_engine.phases.model_architect``) ships NO domain
vocabulary by design: it routes a required mechanism to **reuse** / **wrap** / **build** by matching
the mechanism against each catalog component's capability signature, and a workspace supplies its own
synonym table via ``register_synonyms``. Without it, a mechanism matches only its own literal tokens,
so every real ecosystem method routes to WRAP at best and the engine can never *reuse* a composite it
already has.

This registers the showcase's mechanism -> synonym table so the router recognises the real
viva-ecosystem methods in the catalog (dynamic FBA, spatial reaction-diffusion, agent-based
populations, Monod growth) and reuses them, while genuinely novel mechanisms (cell division,
chemotaxis) still route to BUILD and fire a capability gap. Call ``register_showcase_vocabulary()``
once per process before ``build-model`` / the cycle.
"""
from __future__ import annotations

# Principled domain vocabulary — NOT reverse-engineered to force a route. Each mechanism lists the
# capability tokens that genuinely denote it; the router counts how many land in a component's
# signature (>=2 -> reuse, ==1 -> wrap, 0 -> build).
SHOWCASE_SYNONYMS: dict[str, tuple[str, ...]] = {
    "flux_balance_metabolism": ("dfba", "fba", "flux", "metabolic", "metabolism"),
    "dynamic_fba": ("dfba", "fba", "flux"),
    "spatial_reaction_diffusion": ("spatial", "diffusion", "lattice", "field", "many"),
    "metabolite_exchange": ("exchange", "transport", "flux"),
    "agent_based_population": ("particles", "particle", "agent", "brownian", "abm"),
    "monod_growth_kinetics": ("monod", "growth", "batch", "kinetics"),
    "byproduct_inhibition": ("byproduct", "inhibition", "acetate", "product"),
    "cell_division": ("division", "divide", "proliferation", "mitosis"),
    "chemotaxis": ("chemotaxis", "motility", "gradient"),
}


def register_showcase_vocabulary(*, replace: bool = False) -> dict[str, tuple[str, ...]]:
    """Register the showcase vocabulary with the engine's capability router. Idempotent."""
    from discovery_engine.phases.model_architect import register_synonyms

    register_synonyms(SHOWCASE_SYNONYMS, replace=replace)
    return SHOWCASE_SYNONYMS
