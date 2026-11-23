"""The autonomous investigate loop drives an investigation end to end: it selects actions,
emits typed generation requests with the goal threaded, respects the budget, and stops with a
typed reason — the probe filler abstains so nothing is fabricated."""
import json, os, subprocess, sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
pytest.importorskip("spatio_flux", reason="agent-based-colony baseline needs the spatial extra")


def _run(inv, goal, transcript):
    env = dict(os.environ)
    env["VIVA_FILLER_CMD"] = f"{sys.executable} {REPO/'scripts'/'engine_probe_filler.py'}"
    env["ENGINE_TRANSCRIPT"] = str(transcript)
    p = subprocess.run(["viva-discover", "investigate", inv, "--autonomous", "--goal", goal,
                        "--max-iterations", "4", "--generation-calls", "6", "--simulation-runs", "1"],
                       capture_output=True, text=True, env=env, cwd=REPO, timeout=180)
    out = p.stdout
    return json.loads(out[out.index("{"):out.rindex("}")+1])


def test_autonomous_loop_runs_with_typed_stop_and_goal(tmp_path):
    goal = "characterize how growth and division set the colony's final size"
    rec = _run("agent-based-colony", goal, tmp_path / "t.jsonl")
    assert rec["goal"] == goal                       # the goal is threaded through the loop
    assert isinstance(rec["stop_reason"], str) and rec["stop_reason"]   # a typed stop reason
    assert rec["decisions"] >= 1                      # it autonomously made decisions
    assert rec["applied"] == 0                        # probe filler abstains -> nothing fabricated


def test_autonomous_loop_emits_typed_generation_request(tmp_path):
    tp = tmp_path / "growth.jsonl"
    _run("growth-limitation", "discriminate the plateau mechanism and visualize it", tp)
    assert tp.exists()
    rows = [json.loads(l) for l in tp.read_text().splitlines()]
    assert rows, "the loop should emit at least one generation request"
    r = rows[0]
    assert r["kind"]                                  # a typed kind (e.g. author_tests)
    assert "goal" in (r.get("context_keys") or [])    # goal surfaced into the request context
