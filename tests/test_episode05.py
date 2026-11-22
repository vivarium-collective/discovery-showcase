"""Episode 05 ladder: evaluate/select/construct a model revision (self-test correctness)."""
import pytest
from viva_discovery_showcase.episode05 import run_e05, LEVELS


@pytest.mark.parametrize("level", list(LEVELS))
def test_self_test_reaches_the_structural_revision(tmp_path, level):
    rec = run_e05(level, out_dir=tmp_path, self_test=True)
    assert rec["correct"]
    assert rec["capability"] in ("model evaluation", "model selection", "model construction")


def test_record_attributes_the_level_and_keeps_heldout(tmp_path):
    rec = run_e05("E05c", out_dir=tmp_path, self_test=True)
    assert rec["level"] == "E05c" and rec["capability"] == "model construction"
    assert rec["heldout_error"]["structural"] < rec["heldout_error"]["param_refit"]
    assert abs(rec["recovered_Ki"] - rec["true_Ki"]) < 0.2
