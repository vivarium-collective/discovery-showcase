#!/usr/bin/env python
"""Translate investigation outputs into the paper draft.

Two phases:

  --run       generate a timestamped record (figures + report.pdf + results.json) under
              workspace/reports/<timestamp>/ --- the investigation's development trail.
  (assemble)  collect every report.pdf into the paper's APPENDIX (appendix.tex, \\includepdf,
              chronological); copy the latest figures into a new S2 results SUPPLEMENT
              (supplement2.tex) that integrates them; and copy the headline figures into the
              MAIN figures/ for the main text.

Re-run any time the investigation develops: the appendix accumulates, the supplement + main
figures refresh to the latest.

  python scripts/build_paper_assets.py --run        # generate a new record, then assemble
  python scripts/build_paper_assets.py              # assemble from existing records only
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO / "workspace" / "reports"
PAPER_DIR = Path.home() / "Desktop" / "PLOS_Discovery_Engine" / "versions" / "v1"

HEADLINE_FIGURES = {"ablation": "fig_episode01_ablation.pdf",
                    "growth_curves": "fig_episode01_growth.pdf"}


def generate_record() -> Path:
    """Run the investigation; write figures + report.pdf + results.json under a timestamp."""
    from viva_discovery_showcase import results as R
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = REPORTS_DIR / ts
    res = R.collect_results()
    R.write_figures(res, outdir)
    R.render_report(res, outdir / "report.pdf")
    (outdir / "results.json").write_text(json.dumps(res, default=str, indent=2), encoding="utf-8")
    print(f"record: {outdir}")
    return outdir


def _records() -> list[Path]:
    return sorted(d for d in REPORTS_DIR.glob("*") if (d / "report.pdf").is_file())




def build_investigation_report(paper: Path):
    """Generate the REAL vivarium-workbench investigation HTML report + its PDF.

    Publishes the workspace to a self-contained static bundle (vivarium-workbench-publish),
    copies the investigation HTML report into the paper, and renders it to PDF with playwright
    (served locally so assets resolve). Returns (html_name, pdf_name) or None if unavailable.
    """
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import time

    dest = paper / "appendix_reports"
    dest.mkdir(parents=True, exist_ok=True)
    bundle = Path(tempfile.mkdtemp(prefix="wb-bundle-"))
    try:
        subprocess.run(["vivarium-workbench-publish", "--workspace", str(REPO), "--out", str(bundle)],
                       check=True, capture_output=True, text=True)
    except Exception as e:  # noqa: BLE001 — publish unavailable: skip, don't block the build
        print(f"investigation report: publish skipped ({type(e).__name__})")
        return None
    html = bundle / "reports" / "investigation-growth-limitation.html"
    if not html.is_file():
        print("investigation report: no HTML produced")
        return None
    shutil.copy2(html, dest / "investigation-growth-limitation.html")
    if (bundle / "assets").is_dir():  # keep the HTML viewable from the bundle copy
        shutil.copytree(bundle / "assets", dest / "assets", dirs_exist_ok=True)

    pdf = dest / "investigation-growth-limitation.pdf"
    try:
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", str(bundle)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch()
                pg = b.new_page()
                pg.goto(f"http://127.0.0.1:{port}/reports/investigation-growth-limitation.html",
                        wait_until="networkidle", timeout=30000)
                pg.pdf(path=str(pdf), format="A4", print_background=True)
                b.close()
        finally:
            srv.terminate()
    except Exception as e:  # noqa: BLE001 — PDF optional (needs playwright chromium)
        print(f"investigation report: PDF skipped ({type(e).__name__}: {e})")
        print(f"investigation report: HTML -> {dest}")
        return ("investigation-growth-limitation.html", None)
    print(f"investigation report: HTML + PDF -> {dest}")
    return ("investigation-growth-limitation.html", pdf.name)


def build_isolated_run_records(paper):
    """Render each bias-isolated run (workspace/reports/isolated-runs) as a PDF + return summary rows."""
    import json as _json
    from viva_discovery_showcase import results as R
    src = REPO / "workspace" / "reports" / "isolated-runs"
    dest = paper / "appendix_reports"
    dest.mkdir(parents=True, exist_ok=True)
    rows, pdfs = [], []
    for rjson in sorted(src.glob("run-record-*.json")):
        rec = _json.loads(rjson.read_text())
        mech, seed = rec["sealed_mechanism"], rec["seed"]
        tpath = src / f"transcript-{mech}-seed{seed}.jsonl"
        pdf = dest / f"isolated-run-{mech}-seed{seed}.pdf"
        R.render_isolated_run(rjson, tpath, pdf)
        pdfs.append(pdf.name)
        rows.append((mech, seed, rec["earned_recovery"], rec["heldout_error"]))
    return rows, pdfs


def build_appendix(paper: Path) -> None:
    """Collect every record's report.pdf into the paper appendix + write appendix.tex."""
    dest = paper / "appendix_reports"
    dest.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\documentclass[10pt]{article}",
        r"\usepackage[letterpaper,margin=0.5in]{geometry}",
        r"\usepackage{pdfpages}",
        r"\begin{document}",
        r"\begin{center}{\Large\textbf{Appendix: Investigation report}}\\[4pt]",
        r"The vivarium-workbench investigation report for growth-limitation, generated from the "
        r"workspace record. The HTML report and its assets are collected alongside this PDF.\end{center}",
    ]
    report = build_investigation_report(paper)
    if report and report[1]:
        lines.append(r"\clearpage")
        lines.append(r"\section*{Investigation report: growth-limitation (vivarium-workbench)}")
        lines.append(rf"\includepdf[pages=-,pagecommand={{}}]{{appendix_reports/{report[1]}}}")
    rows, iso_pdfs = build_isolated_run_records(paper)
    if iso_pdfs:
        lines.append(r"\clearpage")
        lines.append(r"\section*{Bias-isolated engine run records}")
        lines.append(r"The ground truth was sealed from the agent; it reasoned from evidence + resources and the engine graded the result.")
        for name in iso_pdfs:
            lines.append(r"\clearpage")
            lines.append(rf"\includepdf[pages=-,scale=0.92,pagecommand={{}}]{{appendix_reports/{name}}}")
    lines.append(r"\end{document}")
    (paper / "appendix.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"appendix: workbench report + {len(iso_pdfs)} isolated-run record(s) -> {paper/'appendix.tex'}")


def _results_table(res: dict) -> str:
    abl = res.get("ablation", {})
    rows = []
    for c in abl:
        rate = abl[c]["recovered_rate"][0]
        err = abl[c]["heldout_error"][0]
        err_s = f"{err:.3f}" if err is not None else "--"
        rows.append(rf"{c.replace('_', ' ')} & {rate:.2f} & {err_s} \\")
    return "\n".join(rows)


def build_supplement(paper: Path) -> None:
    """Copy the latest figures into the paper + write the S2 results supplement."""
    records = _records()
    if not records:
        print("no records; run with --run first")
        return
    latest = records[-1]
    res = json.loads((latest / "results.json").read_text(encoding="utf-8"))
    figdir = paper / "figures" / "results"
    figdir.mkdir(parents=True, exist_ok=True)
    for name in ("growth_curves", "discrimination", "ablation"):
        shutil.copy2(latest / f"{name}.pdf", figdir / f"{name}.pdf")

    tex = rf"""\documentclass[letterpaper,11pt]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{graphicx,booktabs}}
\usepackage{{caption}}
\renewcommand{{\figurename}}{{Fig}}
\renewcommand{{\thefigure}}{{S\arabic{{figure}}}}
\title{{S2 Text for\\[4pt]\textbf{{A discovery engine for multiscale systems biology}}\\[6pt]
Results and investigation records}}
\author{{Eran Agmon}}
\date{{Auto-generated {res['generated_at']}}}
\begin{{document}}
\maketitle

\section{{Episode 01--04: growth limitation --- integrated results}}
This supplement is generated directly from the workspace's investigation outputs; it refreshes
as the investigation develops. The appendix (\texttt{{appendix.pdf}}) collects the timestamped
report PDFs as a provenance trail.

A batch culture grows then plateaus while the baseline Monod model predicts continued growth.
Three mechanisms reproduce the same rise (Fig~\ref{{fig:growth}}); two diagnostic interventions
discriminate them (Fig~\ref{{fig:disc}}), yielding the mechanism signatures
$2\cdot\mathrm{{spike}}+\mathrm{{remove}}$: substrate\,=\,{res['signatures']['substrate_exhaustion']:.0f},
byproduct\,=\,{res['signatures']['byproduct_inhibition']:.0f},
density-cap\,=\,{res['signatures']['density_cap']:.0f}.

\begin{{figure}}[h]\centering
\includegraphics[width=\linewidth]{{figures/results/growth_curves.pdf}}
\caption{{\textbf{{Growth plateau under three mechanisms.}} Biomass, substrate, and byproduct
trajectories from the real Monod model.}}\label{{fig:growth}}
\end{{figure}}

\begin{{figure}}[h]\centering
\includegraphics[width=0.7\linewidth]{{figures/results/discrimination.pdf}}
\caption{{\textbf{{Diagnostic interventions discriminate the mechanism.}} Regrowth after spiking
substrate vs.\ removing the byproduct, per mechanism.}}\label{{fig:disc}}
\end{{figure}}

\section{{Episode 01--04: ablation (real agent vs.\ controls)}}
Under matched budget and seeds, a real reasoning agent recovers the concealed mechanism from the
intervention evidence, matching the oracle, while the deterministic-only floor does not
(Fig~\ref{{fig:abl}}, Table~\ref{{tab:abl}}).

\begin{{figure}}[h]\centering
\includegraphics[width=0.6\linewidth]{{figures/results/ablation.pdf}}
\caption{{\textbf{{Episode 01--04 ablation.}} Mechanism-recovery rate by configuration (concealed
mechanism = byproduct inhibition).}}\label{{fig:abl}}
\end{{figure}}

\begin{{table}}[h]\centering
\begin{{tabular}}{{lrr}}
\toprule
\textbf{{Configuration}} & \textbf{{Recovery rate}} & \textbf{{Held-out error}} \\
\midrule
{_results_table(res)}
\bottomrule
\end{{tabular}}
\caption{{Episode 01--04 recovery rate and held-out error by configuration.}}\label{{tab:abl}}
\end{{table}}

\end{{document}}
"""
    (paper / "supplement2.tex").write_text(tex, encoding="utf-8")
    print(f"supplement: S2 from {latest.name} -> {paper/'supplement2.tex'}")


def export_main_figures(paper: Path) -> None:
    """Copy the headline figures into the paper's main figures/ for the main text."""
    records = _records()
    if not records:
        return
    latest = records[-1]
    for name, dest in HEADLINE_FIGURES.items():
        shutil.copy2(latest / f"{name}.pdf", paper / "figures" / dest)
    print(f"main figures: {', '.join(HEADLINE_FIGURES.values())} -> {paper/'figures'}  "
          f"(wire into main.tex where ready)")


def export_discovery_figures(paper: Path) -> None:
    """Generate the discovery-cycle figures from REAL workspace artifacts into the paper.

    The investigation graph (``discover linkage``), the baseline run's emitted observables (read
    through RunReader), and the monod_batch composite diagram --- all driven by what the engine
    produced, not hand-drawn.
    """
    from viva_discovery_showcase import paper_viz as V
    from viva_discovery_showcase.baseline_run import run_baseline
    figdir = paper / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    try:
        linkage = V.load_linkage(REPO)
        V.render_investigation_graph(linkage, figdir / "fig_investigation_graph.pdf")
        r = run_baseline("byproduct_inhibition", record=False)
        V.render_run_backed_observables(r["store"], figdir / "fig_run_backed_observables.pdf",
                                        graded_value=1.72)
        V.render_composite_diagram(figdir / "fig_monod_composite.pdf")
        # Main-text figures (replacing the Fig1/2/3 placeholders): the architecture schematic,
        # the discovery cycle on the real growth-limitation trace, and the Episode 05 model revision.
        V.render_architecture_overview(figdir / "Fig1.pdf")
        V.render_cycle_diagram(figdir / "Fig2.pdf")
        V.render_model_revision(figdir / "Fig3.pdf")
        print(f"discovery figures: investigation graph ({len(linkage['nodes'])} nodes), "
              f"run-backed observables, composite, + Fig1/2/3 (architecture, cycle, model revision) -> {figdir}")
    except Exception as e:  # noqa: BLE001 — never block the rest of the assembly
        print(f"discovery figures: skipped ({type(e).__name__}: {e})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true", help="generate a new record before assembling")
    ap.add_argument("--paper", default=str(PAPER_DIR), help="paper versions/v1 directory")
    a = ap.parse_args()
    if a.run:
        generate_record()
    paper = Path(a.paper)
    if not paper.is_dir():
        raise SystemExit(f"paper dir not found: {paper}")
    build_appendix(paper)
    build_supplement(paper)
    export_main_figures(paper)
    export_discovery_figures(paper)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
