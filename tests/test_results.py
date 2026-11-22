"""The results generator produces figures + a report PDF from real runs."""
from viva_discovery_showcase import results as R


def test_figures_and_report_pdf(tmp_path):
    res = R.collect_results(seeds=(0,))
    assert res["signatures"]["byproduct_inhibition"] == 1.0
    figs = R.write_figures(res, tmp_path)
    assert set(figs) == {"growth_curves", "discrimination", "ablation"}
    assert all(p.is_file() and p.stat().st_size > 0 for p in figs.values())
    rep = R.render_report(res, tmp_path / "report.pdf")
    assert rep.is_file() and rep.stat().st_size > 1000
