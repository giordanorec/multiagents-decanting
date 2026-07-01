"""v1.3 — state machine, gates, enforcement (decide_tool), hooks, comandos, migração."""
import json
import subprocess
import sys
from pathlib import Path

import _utils as u
import workflow as wf

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _advance_to_loop(root):
    """Leva um projeto recém-init (DISCOVERY) até LOOP com F-001 ativa."""
    u.write_text(root / "docs" / "00_OBJETIVO.md", "x" * 250)
    u.append_text(root / "docs" / "DECISOES.md",
                  "\n## 2026-06-30 — a\n## 2026-06-30 — b\n## 2026-06-30 — c\n")
    u.write_text(root / "docs" / "BACKLOG_V1.md", "# Backlog\n- F-001 — scaffold\n- F-002 — schema\n")
    st = wf.WorkflowState.load(root)
    assert st.advance_phase()[0]           # DISCOVERY -> ESPEC_V1
    st = wf.WorkflowState.load(root)
    assert st.advance_phase()[0]           # ESPEC_V1 -> SETUP_TIME
    st = wf.WorkflowState.load(root)
    assert st.advance_phase()[0]           # SETUP_TIME -> LOOP_FEATURES
    return wf.WorkflowState.load(root)


# ---- init cria estado ----
def test_init_creates_workflow_state(tmp_project):
    p = tmp_project / ".mad" / "workflow_state.json"
    assert p.is_file()
    d = u.read_json(p, {})
    assert d["current_phase"] == "DISCOVERY"   # bootstrap feito pelo init
    assert any(t["role"] == "arquiteto" for t in d["team_enabled"])


# ---- gates ----
def test_gate_discovery_blocks_then_passes(tmp_project):
    ok, msg = wf.gate_discovery_done(tmp_project)
    assert not ok
    u.write_text(tmp_project / "docs" / "00_OBJETIVO.md", "x" * 250)
    u.append_text(tmp_project / "docs" / "DECISOES.md",
                  "\n## 2026-06-30 — a\n## 2026-06-30 — b\n## 2026-06-30 — c\n")
    ok, msg = wf.gate_discovery_done(tmp_project)
    assert ok, msg


def test_gate_espec_requires_backlog(tmp_project):
    ok, _ = wf.gate_espec_done(tmp_project)
    assert not ok
    u.write_text(tmp_project / "docs" / "BACKLOG_V1.md", "- F-001 — x\n")
    assert wf.gate_espec_done(tmp_project)[0]


# ---- enforcement (o coração) ----
def test_agent_blocked_in_discovery(tmp_project):
    st = wf.WorkflowState.load(tmp_project)
    allow, reason, _ = st.decide_tool("Agent", {"subagent_type": "mad:pipeline-dev"})
    assert not allow and "DISCOVERY" in reason


def test_read_allowed_in_discovery(tmp_project):
    st = wf.WorkflowState.load(tmp_project)
    assert st.decide_tool("Read", {})[0]


def test_loop_agent_gating_full(tmp_project):
    st = _advance_to_loop(tmp_project)
    # F-001 ativa em spec_pendente -> Agent bloqueia
    assert not st.decide_tool("Agent", {})[0]
    # escreve spec + valida
    st.feature["agent_assigned"] = "pipeline-dev"
    st.save()
    u.write_text(tmp_project / "specs" / "feature-001-scaffold.md",
                 "objetivo: x\ncritério de aceite: y\nblast_radius: reversivel_baixo\nespecialista: pipeline-dev\n")
    st = wf.WorkflowState.load(tmp_project)
    st.feature["agent_assigned"] = "pipeline-dev"
    st.set_subphase("spec_validada", by="arquiteto")
    # spec_validada -> Agent bloqueia (sem aprovação humana)
    assert not st.decide_tool("Agent", {"subagent_type": "mad:pipeline-dev"})[0]
    # aprovação humana -> executando
    wf.log_event(tmp_project, "approve_spec", feature="F-001", by="human")
    st.set_subphase("executando", by="human")
    # agora libera o especialista certo, bloqueia o errado
    assert st.decide_tool("Agent", {"subagent_type": "mad:pipeline-dev"})[0]
    assert not st.decide_tool("Agent", {"subagent_type": "mad:qa-tester"})[0]


def test_catastrophic_bash_blocked(tmp_project):
    st = wf.WorkflowState.load(tmp_project)
    allow, reason, _ = st.decide_tool("Bash", {"command": "git push --force main"})
    assert not allow


# ---- hook real (subprocess) ----
def test_pre_workflow_hook_blocks_agent(tmp_project):
    hook = tmp_project / ".claude" / "hooks" / "pre-workflow-gate.py"
    payload = {"tool_name": "Agent", "tool_input": {"subagent_type": "mad:pipeline-dev"},
               "cwd": str(tmp_project)}
    r = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                       text=True, cwd=str(tmp_project), capture_output=True)
    assert r.returncode == 2
    assert "BLOQUEADA" in r.stderr


def test_pre_workflow_hook_allows_read(tmp_project):
    hook = tmp_project / ".claude" / "hooks" / "pre-workflow-gate.py"
    payload = {"tool_name": "Read", "tool_input": {}, "cwd": str(tmp_project)}
    r = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                       text=True, cwd=str(tmp_project), capture_output=True)
    assert r.returncode == 0


def test_session_start_hook_injects(tmp_project):
    hook = tmp_project / ".claude" / "hooks" / "session-start-inject-state.py"
    r = subprocess.run([sys.executable, str(hook)], text=True, cwd=str(tmp_project),
                       capture_output=True, env={"CLAUDE_PROJECT_DIR": str(tmp_project),
                                                 "PATH": __import__("os").environ.get("PATH", "")})
    assert "ESTADO DO WORKFLOW MAD" in r.stdout
    assert "DISCOVERY" in r.stdout


# ---- comandos ----
def test_mad_phase_approve_spec(tmp_project):
    st = _advance_to_loop(tmp_project)
    st.feature["agent_assigned"] = "pipeline-dev"
    st.set_subphase("spec_validada", by="arquiteto")
    r = subprocess.run([sys.executable, str(tmp_project / "scripts" / "mad_phase.py"),
                        "approve-spec", "F-001"], cwd=str(tmp_project), capture_output=True, text=True)
    assert r.returncode == 0
    st2 = wf.WorkflowState.load(tmp_project)
    assert st2.subphase == "executando"
    assert st2.feature["approvals"]["spec_approved_by_human"]


def test_rework_requires_note(tmp_project):
    _advance_to_loop(tmp_project)
    r = subprocess.run([sys.executable, str(tmp_project / "scripts" / "mad_phase.py"),
                        "rework", "F-001"], cwd=str(tmp_project), capture_output=True, text=True)
    assert r.returncode == 2  # sem --note


# ---- migração ----
def test_infer_phase_discovery(tmp_project):
    import migrate_v1_3
    phase, conf, _ = migrate_v1_3.infer_phase(tmp_project)
    assert phase == "DISCOVERY"


# ---- cascata /mad-init (T-INIT) ----
def test_cascade_resume(tmp_project):
    import mad_init
    d = mad_init.detect(tmp_project)
    assert d["action"] == "resume"
    assert d["phase"] == "DISCOVERY"


def test_cascade_new(tmp_path):
    import mad_init
    assert mad_init.detect(tmp_path)["action"] == "new"


def test_cascade_migrate(tmp_path):
    import mad_init
    (tmp_path / "multiagents-decanting.toml").write_text("[plugin]\nversion='1.2.0'\n")
    assert mad_init.detect(tmp_path)["action"] == "migrate"


def test_cascade_adopt(tmp_path):
    import mad_init
    dp = tmp_path / "docs_projeto"
    dp.mkdir()
    (dp / "a.md").write_text("x" * 800)
    (dp / "b.md").write_text("y" * 800)
    d = mad_init.detect(tmp_path)
    assert d["action"] == "adopt"
    assert d["inferred_phase"] in ("DISCOVERY", "ESPEC_V1")


def test_cascade_exclusive(tmp_project):
    # tem .mad E parece v1.2 (toml) → passo 1 (resume) vence
    import mad_init
    assert mad_init.detect(tmp_project)["action"] == "resume"


def test_adopt_creates_state(tmp_path, monkeypatch):
    import mad_init
    monkeypatch.chdir(tmp_path)
    dp = tmp_path / "docs_projeto"; dp.mkdir()
    (dp / "a.md").write_text("x" * 800)
    (dp / "b.md").write_text("y" * 800)
    rc = mad_init.adopt(tmp_path, "DISCOVERY")
    assert rc == 0
    st = wf.WorkflowState.load(tmp_path)
    assert st.phase == "DISCOVERY"
    assert (tmp_path / ".claude" / "hooks" / "pre-workflow-gate.py").is_file()


# ---- log ----
def test_log_sanitizes_secret(tmp_project):
    wf.log_event(tmp_project, "test", payload="api_key=SECRETVALUE12345")
    text = u.read_text(tmp_project / "logs" / "workflow.jsonl")
    assert "SECRETVALUE12345" not in text
    assert "REDACTED" in text
