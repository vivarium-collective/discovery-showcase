# Spec: run a workspace-supplied benchmark through the engine

**Goal.** Let `viva-discover benchmark` run a *workspace's* benchmark (e.g.
discovery-showcase's growth-limitation / Episode 01-04), driven by the workspace's
benchmark manifest and a real simulator (`MonodGrowth`), reusing the engine's
proposal + recovery tracks, oracle/real-LLM fillers, budget, and scoring.

**Who implements what.** The *engine* exposes the manifest→provider→run plumbing;
the *workspace* implements the provider (scenario authoring + build_hook + runner)
against its real models. The showcase side is ready to write as soon as the hook
exists.

## What exists today (discovery-engine @main, read Nov 22)

- `benchmark/manifest.py` — `Manifest.from_dict` validates against
  `schemas/benchmark-manifest.schema.json` and exposes `.name`, `.registry()`
  (allowed_skills ∩ registered), `.to_budget()`. **`fixture` is parsed but never
  resolved** — `reference_model` / `candidate_model` / `evidence` / `holdout` are
  inert.
- `benchmark/runner.py::run_benchmark(scenario, config, oracle=None)` — proposal
  track; takes a `Scenario(ws_root, inv_slug, ground_truth)` built by the
  hardcoded `scenario.build_scenario(tmp_path)`.
- `benchmark/recovery_runner.py::run_recovery_benchmark(scenario, config, build_hook=None)`
  — recovery track; takes a `RecoveryScenario` from the hardcoded
  `recovery_scenario.build_recovery_scenario(tmp_path)`. Drives the real loop:
  `load_cycle_inputs → _cycle_with_evidence → accept_capability_gap →
  advance_cycle(autonomous=True, build_hook=hook, runner=recovery_run.benchmark_runner(), max_runs=4)`.
- The two **injection points are already generic** in `advance_cycle`:
  - `build_hook(gap: dict, ws_root) -> dict` — materializes the built study
    (the engine never builds itself).
  - `runner(command, ws_root, *, worktree=None, **kw) -> {ok, returncode, run_id, tail}`
    — stands in for `vivarium-workbench run study <slug>`.
- **Toy-ness:** the default `recovery_run.benchmark_runner()` is a no-op (registers
  an empty run), and grading is store-less (`recovery_model.STORELESS_EVALUATOR_SRC`
  reads the built study's `implements:` string). So the bundled benchmark never
  runs a real simulator.
- The `benchmark` CLI is hardwired to the metabolic-regulator scenario; it has no
  `--manifest` / `--workspace` / `--scenario`.

## Requested engine change (3 parts)

### 1. A workspace benchmark **provider** protocol
Let a manifest name a workspace-implemented provider, resolved by import, e.g. add
an (optional, schema-allowed) `fixture.provider`:

```yaml
fixture:
  provider: "viva_discovery_showcase.benchmark_provider:build"   # "module:callable"
  oracle_visibility: evaluator_only
```

The provider returns a bundle the tracks can consume:

```python
@dataclass
class BenchmarkProvider:
    build_scenario: Callable[[Path], Scenario | RecoveryScenario]  # authors inv+study under ws_root
    ground_truth: GroundTruth                                      # concealed/decoy mechanism, band, observable
    build_hook: Callable[[dict, Any], dict]                        # builds the REAL candidate composite
    runner: Callable                                               # runs the REAL composite (not the no-op)
    oracle: Callable | None = None                                 # optional non-default proposal filler
```

(Equivalently: resolve `reference_model`/`candidate_model` addresses directly to
callables and wrap them — but a single provider entry point is cleaner and keeps
the scenario authoring in the workspace.)

### 2. A public manifest-driven entry + CLI
```python
# discovery_engine/benchmark/*
def run_manifest_benchmark(manifest, provider, *, recovery=False, real_llm=False, ws_root=None) -> Result: ...
```
CLI:
```
viva-discover benchmark --manifest <path> [--workspace <ws>] [--recovery] [--real-llm]
```
It loads+validates the manifest, imports the provider, builds the scenario under
`ws_root`, and drives the existing proposal/recovery runners with the provider's
`build_hook`/`runner`/`oracle`, the manifest's `budget`/`allowed_skills`, and scores
on the manifest's `metrics` + `stop_conditions`. The deterministic oracle/hook stay
the default for the **bundled** benchmark; a workspace provider overrides them.

### 3. Real-simulator grading (not store-less)
When the provider supplies a real `runner` (one that executes the candidate composite
via `vivarium-workbench run study`), grade through the engine's normal
`compute_outcomes` over the real `runs.db`, **not** the store-less `implements:`
reader. The runner contract is already
`runner(command, ws_root, *, worktree=None, **kw) -> {ok, returncode, run_id, tail}`;
the ask is to (a) not hardcode the toy runner/evaluator when a provider is present,
and (b) document that contract so workspaces can implement it.

## What the showcase will implement (provider side, ready to go)

- `benchmark_provider:build` returning: a scenario that authors investigation
  `A-growth-limitation` + the Episode 01-04 study (baseline = mis-specified Monod,
  raising the plateau anomaly); `GroundTruth` with the hidden mechanism ∈
  {substrate, byproduct, decoy}, the regrowth band, observable `mu_regrow`; a
  `build_hook` that builds a real `MonodGrowth` composite with the proposed
  mechanism toggled on; a `runner` that runs that composite (real `runs.db`).
- Fixture data already generated by `viva_discovery_showcase.benchmark_data`
  (train/holdout CSVs + evaluator-only `hidden_truth.yaml`); manifest at
  `benchmarks/growth_limitation/manifest.yaml` (schema-validated).

The decoy mechanism is the **abstention** instance — separable by neither
diagnostic arm — which exercises `irreducible_ambiguity` / correct-abstention
scoring.
```
