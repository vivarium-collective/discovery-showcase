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


def build_appendix(paper: Path) -> None:
    """Collect every record's report.pdf into the paper appendix + write appendix.tex."""
    dest = paper / "appendix_reports"
    dest.mkdir(parents=True, exist_ok=True)
    records = _records()
    lines = [
        r"\documentclass[10pt]{article}",
        r"\usepackage[letterpaper,margin=0.5in]{geometry}",
        r"\usepackage{pdfpages}",
        r"\begin{document}",
        r"\begin{center}{\Large\textbf{Appendix: Investigation development records}}\\[4pt]",
        r"A chronological record of the report PDFs each investigation generated as it developed.\end{center}",
    ]
    for d in records:
        ts = d.name
        shutil.copy2(d / "report.pdf", dest / f"report_{ts}.pdf")
        lines.append(r"\clearpage")
        lines.append(rf"\section*{{Record {ts}}}")
        lines.append(rf"\includepdf[pages=-,scale=0.92,pagecommand={{}}]{{appendix_reports/report_{ts}.pdf}}")
    lines.append(r"\end{document}")
    (paper / "appendix.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"appendix: {len(records)} record(s) -> {paper/'appendix.tex'}")


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
