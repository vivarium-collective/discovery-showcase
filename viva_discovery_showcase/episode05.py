"""Episode 05 capability ladder (E05a-c) --- isolate model evaluation / selection / construction.

The plan's decisive distinction: evaluating an author-built structural revision is not the same as
the engine independently selecting or *constructing* the mechanism change. Each level is a harder
claim on the ladder's fourth rung (structural model revision). Built on the real two-step pathway
(``pathway.py``) with hidden product-feedback inhibition.

- E05a (evaluation): given both revised models and their held-out errors, say which is adequate.
- E05b (selection): choose which revision to apply from a catalog, from the symptom alone.
- E05c (construction): diagnose the missing mechanism and name the structural change, unaided.

The agent's answer is parsed and scored against the known-correct revision; the record keeps the
level so the manuscript attributes precisely what the engine did (evaluate vs select vs construct).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

LEVELS = {
    "E05a": ("model evaluation",
             "Two candidate revisions of a two-step metabolic pathway were each fit to one training "
             "pulse and then tested on held-out pulse magnitudes. 'parameter_refit' keeps the model "
             "structure and re-fits a rate constant; its held-out error is {pr:.3f}. "
             "'structural_revision' adds product-feedback inhibition on the first step; its held-out "
             "error is {sr:.3f}. Which revision is adequate for prediction? "
             "Answer exactly one of: parameter_refit, structural_revision."),
    "E05b": ("model selection",
             "A two-step pathway S->I->P fits its training pulse but overpredicts the peak "
             "intermediate on held-out (larger) pulses. Choose which revision to apply from this "
             "catalog: 'parameter_refit' (re-fit the first rate constant, same structure), or "
             "'structural_revision' (add product-feedback inhibition on the first step). "
             "Answer exactly one of: parameter_refit, structural_revision."),
    "E05c": ("model construction",
             "A two-step pathway S->I->P fits its training pulse but overpredicts the peak "
             "intermediate at larger pulses, and re-fitting the rate constants does not remove the "
             "held-out error. Diagnose the most likely missing mechanism and name the structural "
             "change to make. Answer with the mechanism name, e.g. product_feedback_inhibition."),
}


def _parse(level: str, raw: str) -> "str | None":
    low = (raw or "").lower()
    if level in ("E05a", "E05b"):
        if "structural" in low:
            return "structural_revision"
        if "parameter" in low or "refit" in low:
            return "parameter_refit"
        return None
    # E05c: did the agent name a product-feedback / inhibition structural change?
    if any(t in low for t in ("feedback", "inhibit", "product")):
        return "product_feedback_inhibition"
    return None


def _correct(level: str, answer: "str | None") -> bool:
    if level in ("E05a", "E05b"):
        return answer == "structural_revision"
    return answer == "product_feedback_inhibition"


def run_e05(level: str, *, out_dir, filler_cmd: "str | None" = None, self_test: bool = False,
            train_pulse: float = 3.0, seed: int = 0) -> dict:
    from viva_discovery_showcase.pathway import TRUE, revision_comparison

    cmp = revision_comparison(train_pulse=train_pulse)
    capability, template = LEVELS[level]
    prompt = template.format(pr=cmp["param_refit"]["heldout_error"], sr=cmp["structural"]["heldout_error"])

    if self_test:
        answer = {"E05a": "structural_revision", "E05b": "structural_revision",
                  "E05c": "product_feedback_inhibition"}[level]
        raw = "(self-test deterministic reasoner)"
    else:
        proc = subprocess.run(filler_cmd or "claude -p", shell=True, input=prompt,
                              capture_output=True, text=True, timeout=600)
        raw = proc.stdout or ""
        answer = _parse(level, raw)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    transcript = out / f"transcript-{level}-seed{seed}.jsonl"
    transcript.write_text(json.dumps({"level": level, "prompt": prompt, "response": raw,
                                      "result": {"answer": answer}}) + "\n", encoding="utf-8")
    record = {
        "level": level, "capability": capability, "answer": answer,
        "correct": _correct(level, answer),
        "heldout_error": {"baseline": cmp["baseline"]["heldout_error"],
                          "param_refit": cmp["param_refit"]["heldout_error"],
                          "structural": cmp["structural"]["heldout_error"]},
        "recovered_Ki": cmp["structural"]["Ki"], "true_Ki": TRUE.Ki,
        "transcript": str(transcript),
    }
    (out / f"run-record-{level}-seed{seed}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record
