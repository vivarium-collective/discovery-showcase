"""Episode 06 --- cross-scale composition (rung 5, at the model level).

Two mechanistic models at different scales, coupled through one explicit interface, with a
quantitative cross-scale readout:

- molecular: a metabolic module produces an inhibitory byproduct ``P`` at a rate set by its own
  product feedback (strength ``mol_Ki``) --- the mechanism Episode 05 diagnosed;
- population: ``MonodGrowth``-style growth, inhibited by that same byproduct ``P``.

The interface is the shared byproduct ``P``. The cross-scale readout is the population's plateau
biomass as a function of the *molecular* feedback strength: strong molecular feedback (low
``mol_Ki``) caps ``P`` early, so growth is barely inhibited and the plateau is high; weak feedback
(high ``mol_Ki``) lets ``P`` accumulate, inhibiting growth and lowering the plateau. One number at
the molecular scale thus predicts a population-scale outcome.

This is a model-level composition (two coupled models, one interface, a measured cross-scale
readout); executing it as a typed process-bigraph composite through the engine is the remaining
step, as for Episode 05.
"""
from __future__ import annotations


def coupled_run(mol_Ki: float, *, t_end: float = 150.0, dt: float = 0.1,
                mu_max: float = 0.5, K_S: float = 0.5, Y_XS: float = 20.0,
                growth_K_I: float = 0.4, k_prod: float = 0.05, n: float = 4.0,
                X0: float = 0.05, S0: float = 50.0) -> dict:
    """Integrate the coupled molecular-population system; return the trajectory + plateau biomass."""
    X, S, P = X0, S0, 0.0
    ts, Xs, Ps = [], [], []
    t = 0.0
    steps = int(round(t_end / dt))
    for _ in range(steps + 1):
        # molecular: byproduct production per unit biomass, shut down by product feedback (mol_Ki)
        feedback = mol_Ki ** n / (mol_Ki ** n + max(P, 0.0) ** n)
        # population: Monod growth inhibited by the shared byproduct P
        mu = mu_max * (S / (K_S + S)) * (growth_K_I / (growth_K_I + max(P, 0.0)))
        dX = mu * X
        dS = -(1.0 / Y_XS) * mu * X
        dP = k_prod * feedback * X                      # produced by metabolic activity
        ts.append(t); Xs.append(X); Ps.append(P)
        X = max(X + dt * dX, 0.0)
        S = max(S + dt * dS, 0.0)
        P = max(P + dt * dP, 0.0)
        t += dt
    return {"t": ts, "X": Xs, "P": Ps, "plateau_biomass": Xs[-1], "final_byproduct": Ps[-1],
            "mol_Ki": mol_Ki}


def cross_scale_readout(mol_Kis=(0.25, 0.5, 1.0, 2.0, 4.0, 8.0)) -> list[dict]:
    """Plateau biomass vs molecular feedback strength --- the cross-scale readout."""
    return [{"mol_Ki": k, "plateau_biomass": coupled_run(k)["plateau_biomass"],
             "final_byproduct": coupled_run(k)["final_byproduct"]} for k in mol_Kis]
