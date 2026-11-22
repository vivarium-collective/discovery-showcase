"""Monod batch-growth model for Investigation A (Episodes 01-04).

This is the *simulated system* for the growth-limitation benchmark: a generic
microbial batch culture with biomass ``X``, limiting substrate ``S``, and an
inhibitory byproduct ``P``. One parameterized model generates all three hidden
"truths" the engine must discriminate --- it is the ground-truth generator, not
the agent's reasoning (which goes through the discovery engine).

The growth rate couples a Monod substrate term, a product-inhibition term, and a
logistic density cap (the decoy mechanism)::

    mu(S, P, X) = mu_max * S/(K_S + S) * K_I/(K_I + P) * max(0, 1 - X/X_cap)
    dX/dt =  mu * X
    dS/dt = -(1/Y_XS) * mu * X
    dP/dt =  Y_PX     * mu * X

Which term causes the plateau is set by the parameters (``REFERENCE_PRESETS``):

- **substrate** (H1): inhibition off (K_I -> inf), no cap -> plateau when S -> 0.
- **byproduct** (H2): finite K_I, substrate kept plentiful -> plateau when P -> K_I.
- **decoy** (H3): finite X_cap, no inhibition, no byproduct -> plateau when X -> X_cap.

The discriminating interventions (applied at the plateau) separate them:

              | spike-substrate | remove-byproduct
    H1 substrate |   regrowth      |      no
    H2 byproduct |     no          |   regrowth
    H3 decoy     |     no          |      no        <- neither separates -> abstain

``MonodGrowth`` is the process-bigraph ``Process`` (auto-registered via
``build_core``); ``run_batch`` is a standalone integrator used to generate
benchmark data and to verify the model's behavior in tests.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Optional

from process_bigraph import Process

INF = float("inf")

# --- Hidden-truth parameter presets -----------------------------------------
# Each produces a growth plateau by a different mechanism. Shared kinetics:
# mu_max = 0.5 /h, K_S = 0.5 g/L, X0 = 0.05 g/L.
_BASE = {"mu_max": 0.5, "K_S": 0.5, "X0": 0.05}

REFERENCE_PRESETS: dict[str, dict[str, float]] = {
    # H1: substrate-limited. Inhibition off, no density cap. S runs out.
    "substrate": {**_BASE, "S0": 5.0, "Y_XS": 0.5, "Y_PX": 0.2, "K_I": INF, "X_cap": INF},
    # H2: byproduct-inhibited. Substrate kept plentiful (large S0, high Y_XS so
    # little S is consumed); P accumulates past K_I with a sharp Hill knee
    # (n_I) so growth stops hard while S remains saturating.
    "byproduct": {**_BASE, "S0": 50.0, "Y_XS": 5.0, "Y_PX": 1.0, "K_I": 1.0, "n_I": 8.0, "X_cap": INF},
    # H3 (decoy): density/quorum cap. Substrate plentiful, no byproduct, no
    # inhibition; growth stops at X_cap. The two interventions cannot separate it.
    "decoy": {**_BASE, "S0": 50.0, "Y_XS": 5.0, "Y_PX": 0.0, "K_I": INF, "X_cap": 1.0},
}


def growth_rate(X: float, S: float, P: float, params: dict) -> float:
    """Instantaneous specific growth rate mu(S, P, X) >= 0."""
    mu_max = params["mu_max"]
    K_S = params["K_S"]
    K_I = params.get("K_I", INF)
    X_cap = params.get("X_cap", INF)
    n_I = params.get("n_I", 1.0)
    mu = mu_max * (S / (K_S + S)) if (K_S + S) > 0 else 0.0
    if math.isfinite(K_I):
        # Hill-form product inhibition: n_I > 1 gives a sharp plateau once P
        # crosses K_I (so a saturated-substrate plateau is a true stop, not a
        # slow asymptote). n_I = 1 recovers the classic Monod inhibition term.
        mu *= K_I ** n_I / (K_I ** n_I + max(P, 0.0) ** n_I)
    if math.isfinite(X_cap):
        mu *= max(0.0, 1.0 - X / X_cap)
    return max(mu, 0.0)


def _derivs(X: float, S: float, P: float, params: dict) -> tuple[float, float, float]:
    mu = growth_rate(X, S, P, params)
    dX = mu * X
    dS = -(1.0 / params["Y_XS"]) * mu * X
    dP = params.get("Y_PX", 0.0) * mu * X
    return dX, dS, dP


def _rk4_step(X, S, P, params, dt):
    k1 = _derivs(X, S, P, params)
    k2 = _derivs(X + 0.5 * dt * k1[0], S + 0.5 * dt * k1[1], P + 0.5 * dt * k1[2], params)
    k3 = _derivs(X + 0.5 * dt * k2[0], S + 0.5 * dt * k2[1], P + 0.5 * dt * k2[2], params)
    k4 = _derivs(X + dt * k3[0], S + dt * k3[1], P + dt * k3[2], params)
    X += dt / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
    S += dt / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    P += dt / 6.0 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
    return max(X, 0.0), max(S, 0.0), max(P, 0.0)


# --- Interventions (declared perturbations applied at a time) ----------------
def spike_substrate(state: dict, amount: float = 10.0) -> dict:
    """Add substrate, leaving byproduct untouched. Rescues iff substrate-limited."""
    return {**state, "S": state["S"] + amount}


def remove_byproduct(state: dict, keep: float = 0.0) -> dict:
    """Remove the accumulated byproduct, holding substrate. Rescues iff inhibited."""
    return {**state, "P": state["P"] * keep}


def dilution_control(state: dict, factor: float = 0.5) -> dict:
    """Matched-handling control: scale X, S, P together (partial fresh medium)."""
    return {k: state[k] * factor for k in ("X", "S", "P")}


def run_batch(
    params: dict,
    *,
    t_end: float = 60.0,
    dt: float = 0.05,
    intervention: Optional[Callable[[dict], dict]] = None,
    t_intervene: Optional[float] = None,
    noise: float = 0.0,
    seed: int = 0,
) -> dict:
    """Integrate the batch culture, optionally applying one intervention at a time.

    Returns a trajectory dict with lists ``t, X, S, P`` (and the applied
    intervention time). ``noise`` adds multiplicative lognormal measurement noise
    to the recorded X (deterministic per ``seed``).
    """
    import random

    rng = random.Random(seed)
    X, S, P = params["X0"], params["S0"], 0.0
    ts, Xs, Ss, Ps = [], [], [], []
    applied = False
    t = 0.0
    n = int(round(t_end / dt))
    for i in range(n + 1):
        if intervention is not None and t_intervene is not None and not applied and t >= t_intervene:
            st = intervention({"X": X, "S": S, "P": P})
            X, S, P = st["X"], st["S"], st["P"]
            applied = True
        obsX = X * math.exp(rng.gauss(0.0, noise)) if noise > 0 else X
        ts.append(t); Xs.append(obsX); Ss.append(S); Ps.append(P)
        X, S, P = _rk4_step(X, S, P, params, dt)
        t += dt
    return {"t": ts, "X": Xs, "S": Ss, "P": Ps, "t_intervene": t_intervene}


# --- Mechanism signature (for the discovery-engine benchmark provider) -------
# Public mechanism labels (what a hypothesis/model proposes) -> reference preset.
MECHANISM_LABELS = {
    "substrate_exhaustion": "substrate",
    "byproduct_inhibition": "byproduct",
    "density_cap": "decoy",
}
# Accept either the public mechanism name or the preset name in process_contract.
MECHANISM_LABELS_INV = {v: k for k, v in MECHANISM_LABELS.items()}
MECHANISM_LABELS_INV.update({k: k for k in MECHANISM_LABELS})


# --- Process contract: a model DECLARES its mechanism + expectations ---------
# The legitimate channel by which a model tells an agent what it implements and
# what to expect under the diagnostic interventions. The agent READS this to
# reason about a candidate model --- it is NOT the sealed ground truth (which
# model generated the observed data); that is earned by matching the declared
# expectations against evidence.
MECHANISM_SUMMARY = {
    "substrate_exhaustion": "growth stops when the limiting substrate is exhausted",
    "byproduct_inhibition": "growth stops when an inhibitory byproduct accumulates past K_I "
                            "while substrate remains plentiful",
    "density_cap": "growth stops at a density/quorum cap, with substrate plentiful and no "
                   "inhibitory byproduct",
}
MECHANISM_EXPECTATIONS = {
    "substrate_exhaustion": {"spike_substrate": "regrowth", "remove_byproduct": "no regrowth"},
    "byproduct_inhibition": {"spike_substrate": "no regrowth", "remove_byproduct": "regrowth"},
    "density_cap": {"spike_substrate": "no regrowth", "remove_byproduct": "no regrowth"},
}


def mechanism_from_config(config: dict) -> str:
    """Which plateau mechanism a MonodGrowth config implements (the binding term)."""
    K_I = config.get("K_I", INF)
    X_cap = config.get("X_cap", INF)
    if math.isfinite(K_I) and K_I < 1e11:
        return "byproduct_inhibition"
    if math.isfinite(X_cap) and X_cap < 1e11:
        return "density_cap"
    return "substrate_exhaustion"


def process_contract(mechanism: str) -> dict:
    """A model's DECLARED contract: what it implements + what to expect under the
    diagnostic interventions. The channel the agent reads (not the sealed truth)."""
    mech = MECHANISM_LABELS_INV.get(mechanism, mechanism)
    if mech not in MECHANISM_EXPECTATIONS:
        raise KeyError(f"unknown mechanism: {mechanism}")
    return {
        "mechanism": mech,
        "summary": MECHANISM_SUMMARY[mech],
        "expected_intervention_response": MECHANISM_EXPECTATIONS[mech],
    }


def candidate_contracts() -> list[dict]:
    """The declared contracts of all candidate models (what the agent reasons over)."""
    return [process_contract(m) for m in MECHANISM_EXPECTATIONS]


def growth_signature(label: str, *, seed: int = 0) -> float:
    """A scalar fingerprint of a plateau mechanism: ``2*spike_rescues + remove_rescues``.

    Computed by running the REAL model under the two diagnostic interventions:
    substrate-exhaustion -> (spike rescues, remove does not) -> 2;
    byproduct-inhibition -> (remove rescues, spike does not) -> 1;
    density-cap          -> (neither) -> 0. Distinct per mechanism, so a band around one
    value identifies it. An unknown label returns -1 (never in any mechanism's band).
    """
    mech = MECHANISM_LABELS.get(label, label)
    if mech not in REFERENCE_PRESETS:
        return -1.0
    params = REFERENCE_PRESETS[mech]
    spike = is_regrowth(run_batch(params, t_end=90.0, intervention=spike_substrate,
                                  t_intervene=45.0, seed=seed), params)
    remove = is_regrowth(run_batch(params, t_end=90.0, intervention=remove_byproduct,
                                   t_intervene=45.0, seed=seed), params)
    return 2.0 * int(spike) + 1.0 * int(remove)


def max_growth_rate(traj: dict, t_from: Optional[float] = None) -> float:
    """Max observed specific growth rate d(ln X)/dt after ``t_from`` (default: all)."""
    t, X = traj["t"], traj["X"]
    best = 0.0
    for i in range(1, len(t)):
        if t_from is not None and t[i] < t_from:
            continue
        if X[i - 1] > 1e-9 and X[i] > 0:
            rate = (math.log(X[i]) - math.log(X[i - 1])) / (t[i] - t[i - 1])
            best = max(best, rate)
    return best


def is_regrowth(traj: dict, params: dict, *, frac: float = 0.3) -> bool:
    """Did growth resume after the intervention? mu_regrow > frac * mu_max."""
    t_iv = traj.get("t_intervene")
    if t_iv is None:
        return False
    # look a short settling window past the intervention
    return max_growth_rate(traj, t_from=t_iv + 1.0) > frac * params["mu_max"]


# --- process-bigraph Process -------------------------------------------------
class MonodGrowth(Process):
    """Well-mixed Monod batch growth with product inhibition and a density cap.

    Ports (all ``float``): ``biomass`` (X), ``substrate`` (S), ``byproduct`` (P).
    Emits the updated absolute concentrations each interval. Config carries the
    kinetic parameters; the operative plateau mechanism is whichever term binds
    first, set by those parameters (see ``REFERENCE_PRESETS``).
    """

    config_schema = {
        "mu_max": {"_type": "float", "_default": 0.5},
        "K_S": {"_type": "float", "_default": 0.5},
        "Y_XS": {"_type": "float", "_default": 0.5},
        "Y_PX": {"_type": "float", "_default": 0.2},
        "K_I": {"_type": "float", "_default": 1e12},   # ~inf => inhibition off
        "n_I": {"_type": "float", "_default": 1.0},     # inhibition Hill coefficient
        "X_cap": {"_type": "float", "_default": 1e12},  # ~inf => cap off
        "sub_dt": {"_type": "float", "_default": 0.05},  # internal integration step
    }

    def inputs(self):
        return {"biomass": "float", "substrate": "float", "byproduct": "float"}

    def outputs(self):
        return {
            "biomass": "overwrite[float]",
            "substrate": "overwrite[float]",
            "byproduct": "overwrite[float]",
        }

    def describe(self) -> dict:
        """The process contract: ports + the DECLARED mechanism and expectations this
        configuration implements. An agent reads this to reason about the model."""
        mech = mechanism_from_config(self.config)
        return {
            "name": "MonodGrowth",
            "ports": {"biomass": "float (X)", "substrate": "float (S)", "byproduct": "float (P)"},
            "contract": process_contract(mech),
        }

    def update(self, state, interval):
        params = {k: self.config[k] for k in ("mu_max", "K_S", "Y_XS", "Y_PX", "K_I", "n_I", "X_cap")}
        X, S, P = float(state["biomass"]), float(state["substrate"]), float(state["byproduct"])
        dt = min(self.config["sub_dt"], interval)
        steps = max(1, int(round(interval / dt)))
        dt = interval / steps
        for _ in range(steps):
            X, S, P = _rk4_step(X, S, P, params, dt)
        return {"biomass": X, "substrate": S, "byproduct": P}
