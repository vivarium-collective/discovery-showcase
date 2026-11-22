"""The growth-limitation benchmark fixture + manifest are well-formed and correct.

Checks that (1) the generated fixture (train/holdout/hidden-truth) reproduces the
discrimination contract from the hidden generator, and (2) the manifest validates
against the engine's benchmark-manifest schema.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from viva_discovery_showcase.benchmark_data import write_fixture

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "benchmarks" / "growth_limitation" / "manifest.yaml"

# truth -> which interventions should show regrowth (the Episode 03/04 contract)
EXPECTED = {
    "substrate": {"spike_substrate": True, "remove_byproduct": False},
    "byproduct": {"spike_substrate": False, "remove_byproduct": True},
    "decoy": {"spike_substrate": False, "remove_byproduct": False},
}


@pytest.mark.parametrize("mech", ["substrate", "byproduct", "decoy"])
def test_fixture_reproduces_discrimination(tmp_path, mech):
    summary = write_fixture(tmp_path, mech)
    assert summary["mechanism"] == mech
    assert summary["holdout"]["spike_substrate"] is EXPECTED[mech]["spike_substrate"]
    assert summary["holdout"]["remove_byproduct"] is EXPECTED[mech]["remove_byproduct"]

    # train shows growth then plateau: last biomass well above the inoculum
    with open(tmp_path / "train_measurements.csv") as f:
        rows = list(csv.DictReader(f))
    assert float(rows[-1]["X"]) > 5 * float(rows[0]["X"])

    # hidden truth records the mechanism (evaluator-only)
    truth = (tmp_path / "hidden_truth.yaml").read_text()
    assert f"mechanism: {mech}" in truth


def test_decoy_is_the_abstention_instance(tmp_path):
    s = write_fixture(tmp_path, "decoy")
    # Neither DIAGNOSTIC arm separates the decoy -> abstention. (dilution_control
    # is the matched control and legitimately rescues it by lowering density.)
    assert s["holdout"]["spike_substrate"] is False
    assert s["holdout"]["remove_byproduct"] is False


def test_manifest_validates_against_engine_schema():
    yaml = pytest.importorskip("yaml")
    jsonschema = pytest.importorskip("jsonschema")
    import discovery_engine
    schema_path = Path(discovery_engine.__file__).parent / "schemas" / "benchmark-manifest.schema.json"
    schema = json.loads(schema_path.read_text())
    manifest = yaml.safe_load(MANIFEST.read_text())
    jsonschema.validate(manifest, schema)  # raises on any contract violation
    for key in ("id", "question", "fixture", "budget"):
        assert key in manifest
