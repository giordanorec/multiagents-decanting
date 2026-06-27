"""Testes dos hooks reais — guardrails (CA-030..033), OTel emit, decant check."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import _utils as u

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOKS = PLUGIN_ROOT / "hooks"
HAS_BASH = shutil.which("bash") is not None


def _run_sh(hook: str, payload: dict, cwd: Path, env_extra=None):
    env = {"PATH": __import__("os").environ.get("PATH", "")}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOKS / hook)],
        input=json.dumps(payload), text=True, cwd=str(cwd),
        capture_output=True, env=env,
    )


def _run_py(hook: str, payload: dict, cwd: Path):
    return subprocess.run(
        [sys.executable, str(cwd / ".claude" / "hooks" / hook)],
        input=json.dumps(payload), text=True, cwd=str(cwd),
        capture_output=True,
    )


# ---------------- guardrails ----------------
@pytest.mark.skipif(not HAS_BASH, reason="bash indisponível")
def test_force_push_blocked(tmp_project):
    r = _run_sh("pre-guardrail-force-push.sh",
                {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}},
                tmp_project)
    assert r.returncode == 2


@pytest.mark.skipif(not HAS_BASH, reason="bash indisponível")
def test_force_push_benign_allowed(tmp_project):
    r = _run_sh("pre-guardrail-force-push.sh",
                {"tool_name": "Bash", "tool_input": {"command": "git push origin minha-feature"}},
                tmp_project)
    assert r.returncode == 0


@pytest.mark.skipif(not HAS_BASH, reason="bash indisponível")
def test_rm_rf_outside_blocked(tmp_project):
    r = _run_sh("pre-guardrail-rm-rf.sh",
                {"tool_name": "Bash", "tool_input": {"command": "rm -rf /etc"}},
                tmp_project)
    assert r.returncode == 2


@pytest.mark.skipif(not HAS_BASH, reason="bash indisponível")
def test_rm_rf_inside_allowed(tmp_project):
    (tmp_project / "build").mkdir(exist_ok=True)
    r = _run_sh("pre-guardrail-rm-rf.sh",
                {"tool_name": "Bash", "tool_input": {"command": "rm -rf ./build"}},
                tmp_project)
    assert r.returncode == 0


@pytest.mark.skipif(not HAS_BASH, reason="bash indisponível")
def test_identity_change_blocked(tmp_project):
    r = _run_sh("pre-guardrail-identity-change.sh",
                {"tool_name": "Write", "tool_input": {"file_path": "memory/qa-tester/identity.md"}},
                tmp_project)
    assert r.returncode == 2


@pytest.mark.skipif(not HAS_BASH, reason="bash indisponível")
def test_identity_change_allowed_with_flag(tmp_project):
    r = _run_sh("pre-guardrail-identity-change.sh",
                {"tool_name": "Write", "tool_input": {"file_path": "memory/qa-tester/identity.md"}},
                tmp_project, env_extra={"DECANTING_ALLOW_IDENTITY_CHANGE": "1"})
    assert r.returncode == 0


@pytest.mark.skipif(not HAS_BASH, reason="bash indisponível")
def test_identity_change_other_file_allowed(tmp_project):
    r = _run_sh("pre-guardrail-identity-change.sh",
                {"tool_name": "Write", "tool_input": {"file_path": "memory/qa-tester/handoff.md"}},
                tmp_project)
    assert r.returncode == 0


# ---------------- telemetria / safety ----------------
def test_otel_hook_emits_span(tmp_project):
    _run_py("post-otel-emit.py",
            {"tool_name": "Read", "tool_input": {"file_path": "x.py"}, "agent": {"name": "pipeline-dev"}},
            tmp_project)
    files = list((tmp_project / "logs" / "otel").glob("*.jsonl"))
    assert files, "nenhum span emitido pelo hook OTel"
    text = files[0].read_text(encoding="utf-8")
    assert "tool.use" in text


def test_session_end_penalizes_missing_decant(tmp_project):
    # agente começou e nunca decantou
    u.emit_span("agent.start", {"agent.name": "pipeline-dev"}, root=tmp_project)
    before = u.read_json(tmp_project / "memory" / "pipeline-dev" / "trust.json", {})["score"]
    _run_py("session-end-decant-check.py", {}, tmp_project)
    after = u.read_json(tmp_project / "memory" / "pipeline-dev" / "trust.json", {})["score"]
    assert after <= before  # penaliza (ou mantém se já tratado), nunca sobe


# ---------------- wiring ----------------
def test_init_writes_hook_settings(tmp_project):
    settings = u.read_json(tmp_project / ".claude" / "settings.json", {})
    assert "hooks" in settings
    assert "PreToolUse" in settings["hooks"]
    assert "PostToolUse" in settings["hooks"]
    assert "SessionEnd" in settings["hooks"]
    # otel emit em PostToolUse *
    post = settings["hooks"]["PostToolUse"]
    assert any("post-otel-emit.py" in h["command"]
               for grp in post for h in grp["hooks"])
