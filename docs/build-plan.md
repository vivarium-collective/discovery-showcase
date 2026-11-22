# discovery-showcase — build plan

This workspace builds the **example-led development program** for the Discovery Engine paper
(*A discovery engine for multiscale systems biology*). It is where the ten episodes are actually
implemented, run through the public `discover` / vivarium-workbench workflow, and reported.

- **Full scientific spec** (episodes, hypotheses, bands, benchmark contract, evaluation, waves):
  `~/Desktop/PLOS_Discovery_Engine/SIMULATION_PLAN.md` (the source for the paper's **S2 Text**).
- **This doc** is the execution-side plan: how each episode maps onto workspace artifacts and the
  order we build them.

## Pinned dependencies (most-recent)

- `viva-discovery-engine` → git **@main** (not the PyPI 0.7.5 release) so the showcase tracks the
  latest engine: `Budget`, `discover investigate --goal`, typed stop reasons.
- `vivarium-workbench` → git **@main**.
- `viva-superpowers` → git @main (0.30.0).

See `pyproject.toml` `[tool.uv.sources]`. Re-lock with `uv lock`; install with `uv sync --extra dev`.

## The guardrail (non-negotiable)

An episode is **done** only when the engine produces its scientific artifacts through the public
workflow (`discover …`, the workbench), with a recorded decision trace and **no bespoke script doing
the core reasoning**. A failure to complete an episode that way is a **development requirement** on
the engine/workbench — logged, not patched with a hidden manual decision.

## Episode → workspace artifact mapping

| Episode | Investigation (`workspace/investigations/`) | Studies (`workspace/studies/`) | Composite / simulator |
|---|---|---|---|
| 01–04 growth limitation | `A-growth-limitation` | `growth-plateau-{question,hypotheses,experiment,evaluate}` | Monod + substrate + waste ODE (spatio-flux `MonodKinetics`) |
| 05 model revision | `B-metabolic-feedback` | `two-step-pathway-revision` | process-bigraph ODE pathway |
| 06 polarity | `C-cell-polarity` | `gtpase-cap-composition` | GTPase ODE + Smoldyn / VCell-FV + membrane |
| 07 mitochondria | `D-mito-stress` | `fission-fusion-topology` | graph-rewrite + metabolic step |
| 08 cooperation | `E-cell-cooperation` | `two-celltype-exchange-*` | two-cell-type exchange + diffusion |
| 09 multicellular transition | `F-multicellular-transition` | `cooperation-selects-adhesion` | spatial cells + adhesion/inheritance rewrite |
| 10 lumen | `G-lumen-formation` | `lumen-selection-multicycle` | CompuCell3D (CPM) + basement membrane |

## First build target — Wave 0 + Investigation A (Episodes 01–04)

**Decisions locked:** microbial Monod backbone (not E. coli / not gut microbiome); hidden synthetic
ground truth first; H3 decoy **in** (abstention test); interventions = spike-substrate +
remove-byproduct + dilution control.

### Wave 0 — benchmark harness
- [ ] Shared **benchmark manifest** schema for an episode (question, hypotheses, model + catalog,
  reference/hidden-truth provenance, intervention space, observables+units, budget, pre-registered
  scoring, held-out, expected artifacts).
- [ ] Pinned run stores + scoring + trace export, runnable **without** the workbench UI.
- **Exit gate:** a benchmark is reproducible headless.

### Wave 1 — Investigation A (Episodes 01–04)
- [ ] `viva_discovery_showcase` process(es): a Monod batch model `mu(S,P)=mu_max·S/(K_S+S)·K_I/(K_I+P)`
  with substrate depletion + toggleable product inhibition → the **hidden reference generator**
  (H1: K_I→∞; H2: finite K_I; H3 decoy: a pH/gas/quorum cap).
- [ ] The **mis-specified baseline** (pure Monod, no plateau mechanism) → the discrepancy source.
- [ ] Investigation `A-growth-limitation` + the four episode studies, authored via `/viva:study`
  (claim, baseline+variants, interventions, readouts, behavior tests with grounded bands).
- [ ] Interventions as declared perturbations: spike-substrate (S↑, P fixed), remove-byproduct
  (P↓, S held), dilution control.
- [ ] Run `discover investigate A-growth-limitation` with a deployed agent filler; controls =
  oracle filler + deterministic-only; multiple seeds; one injected technical-failure run.
- **Exit gate:** one complete **real-agent** growth investigation with a trace, correct abstention
  on the H3/ambiguous case, and clean ablations — the paper's *minimum publishable* result.

### Then
Waves 2–5 (Episodes 05 → 10) per the full plan, each gated as in `SIMULATION_PLAN.md` §6.

## Open items to resolve before Wave 1 code
1. Literature anchors for the Monod / product-inhibition constants (decision bands).
2. Which deployed model is the real agent filler; oracle-filler parity harness.
3. Confirm `spatio-flux` `MonodKinetics` exposes a product-inhibition term, or add one in
   `viva_discovery_showcase`.
