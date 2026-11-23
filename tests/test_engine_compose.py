"""The engine's capability router reuses real ecosystem composites and builds genuine gaps,
once the showcase vocabulary is registered."""
from pathlib import Path
import pytest, yaml
pytest.importorskip("spatio_flux", reason="needs the spatial extra for composites to resolve")
from discovery_engine.phases import model_architect as ma
from viva_discovery_showcase.vocabulary import register_showcase_vocabulary

REPO = Path(__file__).resolve().parent.parent


def _routes(mechs):
    register_showcase_vocabulary()
    studies = {sd.parent.name: yaml.safe_load(sd.read_text())
               for sd in (REPO / "workspace" / "studies").glob("*/study.yaml")}
    catalog = ma.build_catalog(studies, ws_root=REPO)
    req = ma.ModelBuildRequest(question_id="t", required_mechanisms=mechs)
    return ma.choose_acquisition_route(req, catalog), catalog


def test_reuse_fires_on_real_ecosystem_composite():
    routes, _ = _routes(["flux_balance_metabolism", "spatial_reaction_diffusion"])
    for m in ("flux_balance_metabolism", "spatial_reaction_diffusion"):
        assert routes[m]["route"] == ma.REUSE
        comp = routes[m]["component"]
        assert comp and comp.startswith("spatio_flux")           # a real ecosystem composite
        assert ma.resolve_composite(comp, REPO)["resolves"]      # and it actually imports


def test_novel_mechanism_routes_to_build_with_coupling_checks():
    routes, catalog = _routes(["flux_balance_metabolism", "cell_division"])
    assert routes["cell_division"]["route"] == ma.BUILD
    assert routes["cell_division"]["component"] is None
    issues = ma.validate_coupling(routes, catalog)
    assert any("cell_division" in i and "before coupling" in i for i in issues)


def test_assembled_model_version_is_content_addressed():
    routes, _ = _routes(["flux_balance_metabolism", "cell_division"])
    mv = ma.model_version(ma.routes_composite(routes), {})
    mid = mv.get("id") if isinstance(mv, dict) else mv
    assert str(mid).startswith("mv:")
