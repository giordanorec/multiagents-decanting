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


def test_gate_validated_rejects_unchecked(tmp_project):
    # BUG histórico: regex casava '- [ ]'. Não pode fechar com critério em aberto.
    d = tmp_project / "reports" / "feature-001"
    u.write_text(d / "arquiteto-merge.md", "# merge\n- [ ] critério 1\n- [ ] critério 2\n")
    ok, _ = wf.gate_arquiteto_validated(tmp_project, "F-001")
    assert not ok
    # com waiver justificado, passa
    u.write_text(d / "arquiteto-merge.md",
                 "# merge\n- [x] critério 1 — ok\n- [ ] critério 2\nWAIVER: item 2 fora do escopo desta feature.\n")
    ok, _ = wf.gate_arquiteto_validated(tmp_project, "F-001")
    assert ok
    # sem nenhum marcado, bloqueia
    u.write_text(d / "arquiteto-merge.md", "# merge\n- [ ] só isso\n")
    ok, _ = wf.gate_arquiteto_validated(tmp_project, "F-001")
    assert not ok


def test_gate_docs_synced_blocks_and_passes(tmp_project):
    st = _advance_to_loop(tmp_project)
    # sem o arquivo -> bloqueia
    ok, msg = wf.gate_docs_synced(tmp_project, "F-001")
    assert not ok and "docs-sync" in msg
    # com as 3 seções -> passa
    u.write_text(tmp_project / "reports" / "feature-001" / "docs-sync.md",
                 "# Doc-sync F-001\n## Spec as-built\nAtualizada, sem divergência.\n"
                 "## Docs vivos\ndocs/03_SCHEMA.md — adicionada tabela produtos.\n"
                 "## Decisão\nUsamos Decimal para preço em vez de float, para evitar erro de arredondamento.\n")
    ok, msg = wf.gate_docs_synced(tmp_project, "F-001")
    assert ok, msg


def test_close_blocked_without_docs_sync(tmp_project):
    st = _advance_to_loop(tmp_project)
    st.feature["agent_assigned"] = "pipeline-dev"
    st.feature["blast_radius"] = "reversivel_baixo"
    st.set_subphase("executando", by="t"); st.set_subphase("validando", by="t")
    u.write_text(tmp_project / "reports" / "feature-001" / "arquiteto-merge.md",
                 "# merge\n- [x] critério 1 — ok\n")
    # revisão independente presente (isola o gate de docs-sync)
    u.write_text(tmp_project / "reports" / "feature-001" / "qa-tester.md",
                 "revisei\nVEREDITO: aprovar\n")
    mp = str(tmp_project / "scripts" / "mad_phase.py")
    # sem docs-sync: next em validando NÃO fecha
    r = subprocess.run([sys.executable, mp, "next"], cwd=str(tmp_project),
                       capture_output=True, text=True)
    assert r.returncode == 1 and "doc" in (r.stdout + r.stderr).lower()
    assert wf.WorkflowState.load(tmp_project).subphase == "validando"
    # revisão independente (autor != verificador) + docs-sync: aí fecha
    u.write_text(tmp_project / "reports" / "feature-001" / "qa-tester.md",
                 "# Revisão QA\nRodei os critérios e testei o fluxo.\nVEREDITO: aprovar\n")
    u.write_text(tmp_project / "reports" / "feature-001" / "docs-sync.md",
                 "# Doc-sync\n## Spec as-built\nok, sem divergência do planejado.\n"
                 "## Docs vivos\nnenhum doc vivo afetado nesta feature de scaffold.\n"
                 "## Decisão\nEstrutura inicial criada conforme a arquitetura combinada.\n")
    r = subprocess.run([sys.executable, mp, "next"], cwd=str(tmp_project),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    st2 = wf.WorkflowState.load(tmp_project)
    assert any(x["id"] == "F-001" and x["status"] == "concluida"
               for x in st2.data["backlog_features"]), r.stdout + r.stderr


def test_gate_independent_review(tmp_project):
    st = _advance_to_loop(tmp_project)
    st.feature["agent_assigned"] = "pipeline-dev"
    st.save()
    d = tmp_project / "reports" / "feature-001"
    # relatório do PRÓPRIO autor não conta
    u.write_text(d / "pipeline-dev.md", "feito\nVEREDITO: aprovar\n")
    ok, _ = wf.gate_independent_review(tmp_project, "F-001")
    assert not ok
    # revisor diferente aprovando conta
    u.write_text(d / "qa-tester.md", "revisei\nVEREDITO: aprovar\n")
    ok, _ = wf.gate_independent_review(tmp_project, "F-001")
    assert ok


def test_gate_tests_green(tmp_project):
    # sem test_cmd configurado -> passa (nada a rodar)
    ok, _ = wf.gate_tests_green(tmp_project, "F-001")
    assert ok
    # com test_cmd configurado mas sem verify.json -> bloqueia
    p = tmp_project / "multiagents-decanting.toml"
    u.write_text(p, u.read_text(p).replace('test_cmd = ""', 'test_cmd = "true"'))
    ok, msg = wf.gate_tests_green(tmp_project, "F-001")
    assert not ok and "verify" in msg.lower()
    # com verify.json all_passed -> passa
    u.write_json(tmp_project / "reports" / "feature-001" / "verify.json",
                 {"all_passed": True, "results": [{"name": "test_cmd", "passed": True}]})
    ok, _ = wf.gate_tests_green(tmp_project, "F-001")
    assert ok


def test_state_backup_and_recovery(tmp_project):
    st = wf.WorkflowState.load(tmp_project)
    st.save()  # gera .bak a partir do estado atual
    bak = tmp_project / ".mad" / "workflow_state.json.bak"
    assert bak.is_file()
    # corrompe o principal -> load recupera do .bak
    (tmp_project / ".mad" / "workflow_state.json").write_text("{corrompido")
    st2 = wf.WorkflowState.load(tmp_project)
    assert st2.phase in wf.PHASES


def test_lock_owner_dead_detection(tmp_project):
    lock = tmp_project / ".mad" / "workflow_state.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    import json as _j, os as _o
    # PID vivo (este processo) no mesmo host -> não rouba
    lock.write_text(_j.dumps({"pid": _o.getpid(), "host": wf._hostname()}))
    assert wf._lock_owner_dead(lock) is False
    # PID morto -> rouba
    lock.write_text(_j.dumps({"pid": 2 ** 22, "host": wf._hostname()}))
    assert wf._lock_owner_dead(lock) is True


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


# ---- auto-spawn de especialistas do backlog (T-INIT-008..016) ----
def _adopt_dir_with_backlog(tmp_path, backlog_text):
    dp = tmp_path / "docs_projeto"
    dp.mkdir(parents=True, exist_ok=True)
    (dp / "a.md").write_text("x" * 800)
    (dp / "b.md").write_text("y" * 800)
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "BACKLOG_V1.md").write_text(backlog_text, encoding="utf-8")
    return tmp_path


def test_backlog_parse_extracts_specialist(tmp_path):
    import mad_init
    bl = tmp_path / "b.md"
    bl.write_text("### F-001 — scaffold\n- **Especialista:** `pipeline-dev`\n- **Blast:** reversivel_baixo\n")
    feats = mad_init.parse_backlog_rich(bl)
    assert feats[0]["id"] == "F-001"
    assert feats[0]["agent"] == "pipeline-dev"


def test_autospawn_enables_and_skips_unknown(tmp_path, monkeypatch):
    import mad_init
    monkeypatch.chdir(tmp_path)
    _adopt_dir_with_backlog(tmp_path,
        "### F-001 — a\n- **Especialista:** `pipeline-dev`\n\n"
        "### F-002 — b\n- **Especialista:** `especialista-ficticio`\n")
    aut = mad_init.autospawn_from_backlog(tmp_path)
    assert "pipeline-dev" in aut["spawned"]
    assert "especialista-ficticio" in aut["skipped"]
    assert (tmp_path / ".claude" / "agents" / "pipeline-dev.md").is_file()
    # arquiteto sempre
    assert (tmp_path / ".claude" / "agents" / "arquiteto.md").is_file()


def test_enable_specialist_idempotent(tmp_path):
    import mad_init
    assert mad_init.enable_specialist(tmp_path, "qa-tester") is True
    assert mad_init.enable_specialist(tmp_path, "qa-tester") is False


def test_compute_final_phase_loop(tmp_path):
    import mad_init
    aut = {"backlog_found": True, "spawned": ["pipeline-dev"],
           "first_feature": {"id": "F-001"},
           "features": [{"id": "F-001", "status": "pendente"}]}
    assert mad_init.compute_final_phase("ESPEC_V1", aut) == "LOOP_FEATURES"


def test_compute_final_phase_pre_release(tmp_path):
    import mad_init
    aut = {"backlog_found": True, "spawned": [], "first_feature": None,
           "features": [{"id": "F-001", "status": "concluida"}]}
    assert mad_init.compute_final_phase("ESPEC_V1", aut) == "PRE_RELEASE"


def test_adopt_with_backlog_reaches_loop(tmp_path, monkeypatch):
    import mad_init
    monkeypatch.chdir(tmp_path)
    _adopt_dir_with_backlog(tmp_path,
        "### F-001 — scaffold\n- **Especialista:** `pipeline-dev`\n\n"
        "### F-002 — schema\n- **Especialista:** `dba`\n")
    rc = mad_init.adopt(tmp_path, "ESPEC_V1")
    assert rc == 0
    st = wf.WorkflowState.load(tmp_path)
    assert st.phase == "LOOP_FEATURES"
    assert st.feature and st.feature["id"] == "F-001"
    assert st.feature["agent_assigned"] == "pipeline-dev"


# ---- log ----
def test_log_sanitizes_secret(tmp_project):
    wf.log_event(tmp_project, "test", payload="api_key=SECRETVALUE12345")
    text = u.read_text(tmp_project / "logs" / "workflow.jsonl")
    assert "SECRETVALUE12345" not in text
    assert "REDACTED" in text


def test_audit_log_hash_chain(tmp_project):
    wf.log_event(tmp_project, "a", x=1)
    wf.log_event(tmp_project, "b", y=2)
    ok, msg = wf.verify_log_chain(tmp_project)
    assert ok, msg
    # adultera uma linha -> cadeia quebra
    logf = tmp_project / "logs" / "workflow.jsonl"
    import json as _j
    lines = logf.read_text().splitlines()
    ev = _j.loads(lines[0]); ev["x"] = 999
    lines[0] = _j.dumps(ev, ensure_ascii=False)
    logf.write_text("\n".join(lines) + "\n")
    ok, _ = wf.verify_log_chain(tmp_project)
    assert not ok
