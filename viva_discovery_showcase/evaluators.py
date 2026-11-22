"""Workspace evaluator hook for the discovery engine.

The engine loads ``<package_path>.evaluators.register_evaluators`` for a workspace and
calls a registered evaluator to grade a behavior test of that ``measure.kind``. Our
``growth_recovery`` evaluator is ``@storeless``: it re-derives its value by running the
REAL Monod model for the built study's *implemented* mechanism, so grading reflects the
model's actual behavior (not a mechanism string, not a config name).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from discovery_engine.study.evaluator import storeless

from viva_discovery_showcase.growth import growth_signature

KIND = "growth_recovery"


def _implemented_mechanism(ws_root, study):
    """The mechanism the build hook ACTUALLY implemented, read from the built study's
    ``implements:`` field on disk. ``study`` is the slug named in the test's
    ``measure.study``. Returns None when the study or field is absent."""
    if ws_root is None or not study:
        return None
    path = Path(ws_root) / "studies" / str(study) / "study.yaml"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None
    impl = doc.get("implements")
    return str(impl) if impl else None


@storeless
def _growth_recover(test, reader, ws_root):
    """Grade the recovered plateau mechanism by its real-model signature vs the band."""
    measure = test.get("measure") or {}
    mech = _implemented_mechanism(ws_root, measure.get("study"))
    if not mech:
        return {"result": "SKIP", "evaluated_by": "code", "measured_value": None,
                "status": "needs_rerun",
                "detail": "no built study named by measure.study with an implements: field"}
    value = growth_signature(mech)
    pass_if = test.get("pass_if") or {}
    lo, hi = pass_if.get("low"), pass_if.get("high")
    in_band = (lo is None or value >= lo) and (hi is None or value <= hi)
    return {"result": "PASS" if in_band else "FAIL", "evaluated_by": "code",
            "measured_value": value,
            "status": "supported" if in_band else "contradicts",
            "detail": "growth_signature(%r) = %.1f" % (mech, value)}


def register_evaluators(registry):
    """Register this workspace's measure-kind evaluators into the engine's grader."""
    registry[KIND] = _growth_recover
