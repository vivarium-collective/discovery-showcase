#!/usr/bin/env python
"""Export each investigation's graph as an SVG (+ PNG) from the canonical workspace YAML.

The workbench renders the investigation graph as an interactive bigraph-loom view; for the paper we
want the same structure as a static vector figure. This reads the real investigation + study specs
(the canonical ``workspace/investigations/<slug>/investigation.yaml`` and member
``workspace/studies/<slug>/study.yaml``) and draws the graph with graphviz:

    investigation -> study -> hypothesis/AC -> model version (baseline composite) -> behavior test -> verdict

Behavior-test nodes are coloured by their graded outcome (PASS/FAIL, from ``computed_outcomes`` when a
run has been graded). Needs graphviz (`brew install graphviz` + `uv pip install graphviz`).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
PAPER = Path.home() / "Desktop" / "PLOS_Discovery_Engine" / "versions" / "v1" / "figures"

_PALETTE = {  # colourblind-safe, light-mode
    "investigation": ("#1b2a4a", "#ffffff"), "study": ("#2a6f97", "#ffffff"),
    "hypothesis": ("#e9ecef", "#1b2a4a"), "model": ("#5a189a", "#ffffff"),
    "verdict_supported": ("#2d6a4f", "#ffffff"), "verdict_other": ("#9d4e15", "#ffffff"),
    "test_pass": ("#d8f3dc", "#1b4332"), "test_fail": ("#ffccd5", "#6a040f"),
    "test_ungraded": ("#f1f3f5", "#495057"),
}


def _node(dot, nid, label, kind):
    fill, font = _PALETTE.get(kind, ("#f1f3f5", "#212529"))
    shape = {"investigation": "box", "study": "box", "model": "component"}.get(kind, "box")
    style = "rounded,filled" if shape == "box" else "filled"
    dot.node(nid, label, shape=shape, style=style, fillcolor=fill, fontcolor=font,
             fontname="Helvetica", fontsize="10")


def _graded_tests(study: dict) -> dict[str, str]:
    """test name -> PASS/FAIL/'' from the first run's computed_outcomes."""
    out: dict[str, str] = {}
    for run in study.get("runs", []) or []:
        for tn, co in (run.get("computed_outcomes") or {}).items():
            if isinstance(co, dict) and "result" in co:
                out[tn] = co["result"]
    return out


def export_one(slug: str, out_dir: Path) -> Path:
    import graphviz

    inv = yaml.safe_load((REPO / "workspace" / "investigations" / slug / "investigation.yaml").read_text())
    dot = graphviz.Digraph(f"inv_{slug}", graph_attr={"rankdir": "LR", "bgcolor": "transparent",
                                                       "splines": "spline", "nodesep": "0.3", "ranksep": "0.55"})
    inv_id = f"inv/{slug}"
    _node(dot, inv_id, f"investigation\n{slug}", "investigation")
    hyps = {h["id"]: h for h in inv.get("hypotheses", []) or []}

    for study_slug in inv.get("studies", []) or []:
        sp = REPO / "workspace" / "studies" / study_slug / "study.yaml"
        if not sp.exists():
            continue
        study = yaml.safe_load(sp.read_text())
        sid = f"study/{study_slug}"
        _node(dot, sid, f"study\n{study_slug}", "study")
        dot.edge(inv_id, sid, color="#1b2a4a")

        # hypothesis the study tests (via acceptance_criteria)
        for ac in inv.get("acceptance_criteria", []) or []:
            if ac.get("study") == study_slug:
                hid = f"hyp/{study_slug}"
                stmt = (inv.get("hypotheses") or [{}])[0].get("statement", ac.get("statement", ""))
                _node(dot, hid, "hypothesis\n" + _wrap(stmt, 34), "hypothesis")
                dot.edge(hid, sid, label="tested by", color="#868e96", fontsize="8", fontname="Helvetica")

        # model version: the baseline composite (the real method)
        base = (study.get("baseline") or [{}])[0]
        comp = base.get("composite", "")
        if comp:
            mid = f"model/{study_slug}"
            _node(dot, mid, "model\n" + comp.split(".")[-1], "model")
            dot.edge(sid, mid, label="runs", color="#5a189a", fontsize="8", fontname="Helvetica")

            graded = _graded_tests(study)
            for bt in study.get("behavior_tests", []) or []:
                name = bt.get("name", "?")
                res = graded.get(name, "")
                kind = {"PASS": "test_pass", "FAIL": "test_fail"}.get(res, "test_ungraded")
                tid = f"test/{study_slug}/{name}"
                _node(dot, tid, f"test\n{name}" + (f"\n{res}" if res else ""), kind)
                dot.edge(mid, tid, label="graded", color="#adb5bd", fontsize="8", fontname="Helvetica")

                verdict = study.get("verdict", "")
                if verdict:
                    vid = f"verdict/{study_slug}"
                    vk = "verdict_supported" if verdict == "supported" else "verdict_other"
                    _node(dot, vid, f"verdict\n{verdict}", vk)
                    dot.edge(tid, vid, color="#495057")

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"fig_invgraph_{slug.replace('-', '_')}"
    for fmt in ("svg", "png", "pdf"):  # svg = the workbench-style export deliverable; pdf = paper embed
        dot.render(str(stem), format=fmt, cleanup=True)
    print(f"saved {stem}.svg (+ .png, .pdf)")
    return stem.with_suffix(".svg")


def _wrap(s: str, n: int) -> str:
    words, line, out = str(s).split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = f"{line} {w}".strip()
    out.append(line)
    return "\\n".join(out[:4])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--investigations", nargs="+",
                    default=["spatial-metabolism", "agent-based-colony", "growth-limitation"])
    ap.add_argument("--out", default=str(PAPER))
    a = ap.parse_args()
    for slug in a.investigations:
        try:
            export_one(slug, Path(a.out))
        except Exception as e:  # noqa: BLE001
            print(f"{slug}: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
