"""Testes de resiliência — budget enforcement e circuit breaker (CA-040..044)."""
import subprocess
import sys
from pathlib import Path

import _utils as u
import resilience as r

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    assert r.retry(flaky, attempts=3, initial_ms=1, sleep=lambda _: None) == "ok"
    assert calls["n"] == 3


def test_retry_reraises_after_exhaustion():
    def always():
        raise RuntimeError("nope")

    try:
        r.retry(always, attempts=2, initial_ms=1, sleep=lambda _: None)
        assert False
    except RuntimeError:
        pass


def test_guard_allows_under_budget(tmp_project):
    g = r.guard(tmp_project)
    assert g.allowed


def test_guard_blocks_over_budget(tmp_project):
    # estoura o teto (web => budget 50 default; ml fixture usa default 50)
    u.emit_span("model.call",
                {"agent.name": "pipeline-dev", "gen_ai.cost.estimate": 999.0},
                root=tmp_project)
    g = r.guard(tmp_project)
    assert not g.allowed
    assert "Teto diário" in g.reason


def test_guard_circuit_breaker_opens(tmp_project):
    # config default: circuit_breaker_failures = 3
    for _ in range(3):
        u.emit_span("agent.error", {"agent.name": "pipeline-dev",
                                    "error.type": "timeout"}, root=tmp_project)
    g = r.guard(tmp_project)
    assert not g.allowed
    assert "Circuit breaker" in g.reason


def test_warning_threshold(tmp_project):
    assert r.warning(tmp_project) is None
    u.emit_span("model.call",
                {"agent.name": "x", "gen_ai.cost.estimate": 45.0}, root=tmp_project)
    w = r.warning(tmp_project)
    assert w and "Budget" in w


def test_budget_hook_blocks_over_budget(tmp_project):
    import json
    u.emit_span("model.call",
                {"agent.name": "x", "gen_ai.cost.estimate": 999.0}, root=tmp_project)
    hook = tmp_project / ".claude" / "hooks" / "pre-budget-circuit.py"
    payload = {"tool_name": "Agent", "cwd": str(tmp_project),
               "tool_input": {"subagent_type": "multiagents-decanting:pipeline-dev"}}
    res = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                         text=True, cwd=str(tmp_project), capture_output=True)
    assert res.returncode == 2
    assert "BLOQUEADO" in res.stderr


def test_budget_hook_allows_non_agent_tool(tmp_project):
    import json
    hook = tmp_project / ".claude" / "hooks" / "pre-budget-circuit.py"
    payload = {"tool_name": "Read", "cwd": str(tmp_project)}
    res = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                         text=True, cwd=str(tmp_project), capture_output=True)
    assert res.returncode == 0
