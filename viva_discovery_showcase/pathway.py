"""Episode 05 — model revision (Investigation B): parameter vs. structural inadequacy.

A two-step metabolic pathway S -> I -> P. The hidden TRUE system has product-feedback
inhibition on the first step; the baseline model omits it. The baseline can be calibrated to
match steady-state flux, but it misses the response to a substrate PULSE (the intermediate I
overshoots without feedback damping). The scientific question: is the discrepancy a wrong
PARAMETER or a missing MECHANISM?

Two revisions under matched calibration (each fit to one training pulse):
  - parameter refit: keep the no-feedback structure, re-fit k1 to the training pulse;
  - structural:      add product-feedback inhibition, fit its constant to the training pulse.

The decisive readout is HELD-OUT: a structural revision generalizes to unseen pulse magnitudes,
a parameter refit overfits the one it was tuned on. ``structural`` beats ``param_refit`` on
held-out error --- and a structural change that merely overfits training is rejected.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pathway:
    k1: float = 1.0
    k2: float = 0.6
    Km1: float = 1.0
    Km2: float = 1.0
    feedback: bool = False
    Ki: float = 2.0
    n: float = 2.0


TRUE = Pathway(feedback=True, Ki=2.0, n=2.0)          # hidden truth: product feedback
BASELINE = Pathway(feedback=False)                    # candidate: no feedback


def _rates(S, I, P, m: Pathway):
    inhib = 1.0
    if m.feedback:
        inhib = m.Ki ** m.n / (m.Ki ** m.n + max(P, 0.0) ** m.n)
    v1 = m.k1 * (S / (m.Km1 + S)) * inhib if (m.Km1 + S) > 0 else 0.0
    v2 = m.k2 * (I / (m.Km2 + I)) if (m.Km2 + I) > 0 else 0.0
    return -v1, v1 - v2, v2


def _step(S, I, P, m, dt):
    k1 = _rates(S, I, P, m)
    k2 = _rates(S + 0.5 * dt * k1[0], I + 0.5 * dt * k1[1], P + 0.5 * dt * k1[2], m)
    k3 = _rates(S + 0.5 * dt * k2[0], I + 0.5 * dt * k2[1], P + 0.5 * dt * k2[2], m)
    k4 = _rates(S + dt * k3[0], I + dt * k3[1], P + dt * k3[2], m)
    S += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
    I += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    P += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
    return max(S, 0.0), max(I, 0.0), max(P, 0.0)


def peak_intermediate(m: Pathway, *, S0: float = 2.0, pulse: float = 0.0,
                      t_pulse: float = 8.0, t_end: float = 40.0, dt: float = 0.02) -> float:
    """Max intermediate I after a substrate pulse (the overshoot feedback damps)."""
    S, I, P = S0, 0.0, 0.0
    peak, t, applied = 0.0, 0.0, False
    for _ in range(int(t_end / dt) + 1):
        if not applied and t >= t_pulse:
            S += pulse
            applied = True
        S, I, P = _step(S, I, P, m, dt)
        if applied:
            peak = max(peak, I)
        t += dt
    return peak


def _fit_scalar(make_model, lo, hi, pulse, *, steps=40):
    """Coarse 1-D fit: value in [lo, hi] minimizing |peak_I(model) - peak_I(TRUE)| at ``pulse``."""
    target = peak_intermediate(TRUE, pulse=pulse)
    best, best_err = lo, float("inf")
    for i in range(steps + 1):
        x = lo + (hi - lo) * i / steps
        err = abs(peak_intermediate(make_model(x), pulse=pulse) - target)
        if err < best_err:
            best, best_err = x, err
    return best


def parameter_refit(train_pulse: float) -> Pathway:
    """Keep the no-feedback structure; re-fit k1 to the training pulse."""
    scale = _fit_scalar(lambda s: Pathway(k1=BASELINE.k1 * s, feedback=False), 0.2, 1.5, train_pulse)
    return Pathway(k1=BASELINE.k1 * scale, feedback=False)


def structural_revision(train_pulse: float) -> Pathway:
    """Add product-feedback inhibition; fit its constant Ki to the training pulse."""
    Ki = _fit_scalar(lambda ki: Pathway(feedback=True, Ki=ki, n=2.0), 0.5, 6.0, train_pulse)
    return Pathway(feedback=True, Ki=Ki, n=2.0)


def heldout_error(model: Pathway, pulses) -> float:
    """Mean |peak_I(model) - peak_I(TRUE)| over held-out pulse magnitudes."""
    errs = [abs(peak_intermediate(model, pulse=p) - peak_intermediate(TRUE, pulse=p)) for p in pulses]
    return sum(errs) / len(errs)


def revision_comparison(*, train_pulse: float = 3.0, heldout=(1.0, 5.0, 7.0)) -> dict:
    """Fit both revisions on the training pulse; compare held-out error. Structural should win."""
    refit = parameter_refit(train_pulse)
    struct = structural_revision(train_pulse)
    return {
        "baseline": {"heldout_error": heldout_error(BASELINE, heldout)},
        "param_refit": {"Ki": None, "k1": refit.k1,
                        "train_error": heldout_error(refit, (train_pulse,)),
                        "heldout_error": heldout_error(refit, heldout)},
        "structural": {"Ki": struct.Ki, "k1": struct.k1,
                       "train_error": heldout_error(struct, (train_pulse,)),
                       "heldout_error": heldout_error(struct, heldout)},
    }
