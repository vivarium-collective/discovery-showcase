#!/usr/bin/env python
"""Show the discovery engine COMPOSING a model from the real ecosystem-method catalog.

Not a pre-built composite handed to a runner: here the engine is given a set of required mechanisms
and, using its own capability router (``discovery_engine.phases.model_architect``), triages each one
across **reuse / wrap / build** against the catalog derived from the real study arms (dynamic FBA,
spatial reaction-diffusion, agent-based particles, Monod growth). It reuses a real ecosystem
composite where one provides the mechanism, flags an adapter where the match is partial, and routes a
genuine gap to BUILD with the coupling checks it must pass first — then emits a content-addressed
model version for the assembled composite.

Run from the workspace root (needs the `spatial` extra for the composites to resolve):
    python scripts/engine_compose_demo.py
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from discovery_engine.phases import model_architect as ma
from viva_discovery_showcase.vocabulary import register_showcase_vocabulary

REPO = Path(__file__).resolve().parent.parent
# A model the engine must assemble for a spatial, dividing, metabolising colony: some mechanisms the
# ecosystem already provides, some it must build.
REQUIRED = ["flux_balance_metabolism", "spatial_reaction_diffusion", "metabolite_exchange",
            "cell_division", "chemotaxis"]


def main() -> int:
    register_showcase_vocabulary()
    studies = {sd.parent.name: yaml.safe_load(sd.read_text())
               for sd in (REPO / "workspace" / "studies").glob("*/study.yaml")}
    catalog = ma.build_catalog(studies, ws_root=REPO)
    req = ma.ModelBuildRequest(question_id="compose-demo", required_mechanisms=REQUIRED)
    routes = ma.choose_acquisition_route(req, catalog)
    tag = {ma.REUSE: "REUSE", ma.WRAP: "WRAP ", ma.BUILD: "BUILD"}

    print(f"catalog: {len(catalog)} real ecosystem composites "
          f"({', '.join(c['id'] for c in catalog)})\n")
    print("the engine triages each required mechanism:")
    for mech in REQUIRED:
        r = routes[mech]
        route, comp = r["route"], r.get("component")
        chosen = comp.split(".")[-1] if comp else "—"
        runnable = ""
        if comp:
            runnable = " [resolves ✓]" if ma.resolve_composite(comp, REPO).get("resolves") else " [resolves ✗]"
        print(f"  [{tag.get(route, route)}] {mech:<27} -> {chosen}{runnable}")
        print(f"            {r['rationale']}")

    issues = ma.validate_coupling(routes, catalog)
    if issues:
        print("\ncoupling checks (the engine's own validate_coupling):")
        for iss in issues:
            print(f"  ⚑ {iss}")

    composite = ma.routes_composite(routes)
    mv = ma.model_version(composite, {})
    print(f"\nassembled model version: {mv.get('id') if isinstance(mv, dict) else mv}")
    print(f"  composite spec: {composite}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
