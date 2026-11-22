"""Episode 05 — model revision: structural revision beats parameter refit on held-out."""
from __future__ import annotations

from viva_discovery_showcase.pathway import (
    BASELINE,
    TRUE,
    heldout_error,
    parameter_refit,
    peak_intermediate,
    revision_comparison,
    structural_revision,
)


def test_baseline_misses_the_pulse_response():
    # with no feedback, the intermediate overshoots more than the true (feedback) system
    assert peak_intermediate(BASELINE, pulse=5.0) > peak_intermediate(TRUE, pulse=5.0)


def test_both_revisions_fit_the_training_pulse():
    train = 3.0
    assert heldout_error(parameter_refit(train), (train,)) < 0.05
    assert heldout_error(structural_revision(train), (train,)) < 0.05


def test_structural_beats_parameter_refit_on_heldout():
    r = revision_comparison(train_pulse=3.0, heldout=(1.0, 5.0, 7.0))
    # both match training; only the structural revision generalizes
    assert r["structural"]["heldout_error"] < r["param_refit"]["heldout_error"]
    # and the structural revision is a real improvement over the baseline
    assert r["structural"]["heldout_error"] < r["baseline"]["heldout_error"]


def test_structural_recovers_the_true_mechanism_constant():
    # fitting Ki on the training pulse recovers (near) the true feedback constant
    s = structural_revision(3.0)
    assert abs(s.Ki - TRUE.Ki) < 1.0
