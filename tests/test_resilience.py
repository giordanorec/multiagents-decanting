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


def _set_mode(root, mode, max_tokens_day=None):
    import re
    p = root / "multiagents-decanting.toml"
    txt = u.read_text(p).replace('mode = "subscription"', f'mode = "{mode}"')
    if max_tokens_day is not None:
        txt = re.sub(r"max_tokens_per_day\s*=\s*\d+",
                     f"max_tokens_per_day = {max_tokens_day}", txt)
    u.write_text(p, txt)


def test_guard_subscription_no_dollar_block(tmp_project):
    # assinatura (padrão): custo em $ NÃO bloqueia (não há $ de verdade)
    u.emit_span("model.call",
                {"agent.name": "pipeline-dev", "gen_ai.cost.estimate": 999.0},
                root=tmp_project)
    assert r.guard(tmp_project).allowed


def test_guard_paid_api_blocks_over_budget(tmp_project):
    _set_mode(tmp_project, "paid_api")
    u.emit_span("model.call",
                {"agent.name": "pipeline-dev", "gen_ai.cost.estimate": 999.0},
                root=tmp_project)
    g = r.guard(tmp_project)
    assert not g.allowed
    assert "API paga" in g.reason


def test_guard_token_cap_blocks(tmp_project):
    _set_mode(tmp_project, "subscription", max_tokens_day=1000)
    u.emit_span("model.call",
                {"agent.name": "x", "gen_ai.usage.input_tokens": 1200,
                 "gen_ai.usage.output_tokens": 500}, root=tmp_project)
    g = r.guard(tmp_project)
    assert not g.allowed
    assert "uso diário" in g.reason


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
    _set_mode(tmp_project, "paid_api")  # em paid_api o teto em $ trava
    u.emit_span("model.call",
                {"agent.name": "x", "gen_ai.cost.estimate": 999.0}, root=tmp_project)
    hook = tmp_project / ".claude" / "hooks" / "pre-budget-circuit.py"
    payload = {"tool_name": "Agent", "cwd": str(tmp_project),
               "tool_input": {"subagent_type": "mad:pipeline-dev"}}
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


def test_recent_failures_counts_tooluse_error(tmp_project):
    # circuit breaker ressuscitado: tool.use com outcome=error conta como falha
    for _ in range(3):
        u.emit_span("tool.use", {"agent.name": "pipeline-dev", "tool.name": "Bash",
                                 "tool.outcome": "error"}, root=tmp_project)
    assert r.recent_failures(tmp_project, 3600) >= 3
    g = r.guard(tmp_project)
    assert not g.allowed and "Circuit breaker" in g.reason
