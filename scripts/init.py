"""
init.py — scaffold determinístico de um projeto multiagents-decanting.

A conversa de Discovery é conduzida pelo slash command /mad-init (LLM).
Aqui fica só o que é puro filesystem: criar estrutura, copiar templates,
substituir {{variáveis}}, registrar agentes. Idempotente onde seguro; nunca
sobrescreve memória/docs existentes sem aviso.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_VERSION = "1.0.0"

# tipo de projeto -> agentes sugeridos (spec 07, passo 11)
TYPE_AGENTS = {
    "ml":        ["arquiteto", "pipeline-dev", "qa-tester", "dba"],
    "web":       ["arquiteto", "pipeline-dev", "frontend-dev", "qa-tester"],
    "cli":       ["arquiteto", "pipeline-dev", "qa-tester", "docs-writer"],
    "jogo":      ["arquiteto", "pipeline-dev", "qa-tester", "asset-designer"],
    "documento": ["arquiteto", "docs-writer"],
    "outro":     ["arquiteto", "pipeline-dev", "qa-tester"],
}

MEMORY_FILES = ["identity.md", "dossier.md", "decisions.md", "handoff.md",
                "state.md", "lessons.md", "trust.json"]

# diretórios estáticos copiados do plugin para o projeto
# (hooks vão só para .claude/hooks, tratado à parte — não duplicar)
COPY_TREES = ["dashboard", "bin", "locale"]
COPY_SCRIPTS = ["mad.py", "init.py", "doctor.py", "inspect_agent.py",
                "dashboard_server.py", "resilience.py", "notify.py",
                "a2a.py", "voice.py", "workflow.py", "mad_phase.py",
                "mad_init.py", "migrate_v1_3.py", "_utils.py"]


def _subst(text: str, mapping: dict) -> str:
    for k, v in mapping.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def _copy_tree(src: Path, dst: Path):
    if not src.is_dir():
        return
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def _agent_template_path(agent: str) -> Path:
    specific = PLUGIN_ROOT / "agents" / f"{agent}.md"
    if specific.is_file():
        return specific
    return PLUGIN_ROOT / "templates" / "agents" / "_template.md"


def _scaffold_memory(target: Path, agent: str, project: str) -> list[str]:
    """Cria memory/<agent>/ a partir dos templates. Retorna arquivos criados."""
    created = []
    mem_dir = target / "memory" / agent
    (mem_dir / "playbooks").mkdir(parents=True, exist_ok=True)
    mapping = {"agente": agent, "projeto": project,
               "iso_timestamp": u.iso_now(),
               "papel_curto": "", "path_1": "", "path_2": "",
               "fora_1": "", "fora_2": "", "restricao_1": "", "regra_1": "",
               "objetivo_curto": "", "motivacao_negocio": "", "usuarios": "",
               "area_1": "", "area_2": "", "descricao": "",
               "lista_decisoes_pertinentes": "", "convencao_1": "",
               "convencao_2": "", "outro_agente": "", "relacao": ""}
    tpl_dir = PLUGIN_ROOT / "templates" / "memory"
    for fname in MEMORY_FILES:
        dst = mem_dir / fname
        if dst.is_file():
            continue  # nunca sobrescreve memória existente
        src = tpl_dir / fname
        content = u.read_text(src) if src.is_file() else ""
        u.write_text(dst, _subst(content, mapping))
        created.append(f"memory/{agent}/{fname}")
    return created


def _register_agent(target: Path, agent: str) -> str | None:
    """Copia agents/<role>.md -> .claude/agents/<role>.md. Retorna path ou None."""
    dst = target / ".claude" / "agents" / f"{agent}.md"
    if dst.is_file():
        return None
    src = _agent_template_path(agent)
    if not src.is_file():
        return None
    content = u.read_text(src)
    if "_template" in src.name:
        content = _subst(content, {"agente": agent, "papel": agent})
    u.write_text(dst, content)
    return f".claude/agents/{agent}.md"


def enable_agent(agent: str, target: Path | None = None, project: str | None = None) -> int:
    target = target or Path.cwd()
    project = project or target.name
    if (target / "memory" / agent).is_dir():
        print(u.c(f"▲ {agent} já habilitado (memory/{agent}/ existe).", "yellow"))
        return 1
    created = _scaffold_memory(target, agent, project)
    reg = _register_agent(target, agent)
    if reg:
        created.append(reg)
    print(u.c(f"✓ {agent} habilitado.", "green"))
    for c in created:
        print(f"    + {c}")
    print(f"  Pronto pra ser invocado via Agent tool: "
          f"subagent_type=\"mad:{agent}\"")
    u.emit_span("agent.enabled", {"agent.name": agent}, root=target)
    return 0


def run(name=None, project_type="outro", agents=None, budget_usd=50.0,
        target: Path | None = None) -> int:
    target = target or Path.cwd()
    project = name or target.name

    if (target / u.CONFIG_FILENAME).is_file():
        print(u.c("▲ Projeto já inicializado (multiagents-decanting.toml existe).", "yellow"))
        print("  Use /mad-dashboard ou /mad-doctor.")
        return 1

    agents = agents or TYPE_AGENTS.get(project_type, TYPE_AGENTS["outro"])
    if "arquiteto" not in agents:
        agents = ["arquiteto"] + agents

    # --- estrutura base ---
    for d in ["docs", "specs", "reports", "memory", "logs/otel", "status",
              ".claude/agents", ".claude/hooks"]:
        (target / d).mkdir(parents=True, exist_ok=True)

    # --- copia árvores estáticas ---
    for tree in COPY_TREES:
        _copy_tree(PLUGIN_ROOT / tree, target / tree)
    # hooks vão também pra .claude/hooks (onde Claude Code lê)
    _copy_tree(PLUGIN_ROOT / "hooks", target / ".claude" / "hooks")
    # scripts
    (target / "scripts").mkdir(exist_ok=True)
    for s in COPY_SCRIPTS:
        src = PLUGIN_ROOT / "scripts" / s
        if src.is_file():
            shutil.copy2(src, target / "scripts" / s)

    # --- docs e CLAUDE.md a partir de templates ---
    mapping = {
        "projeto": project, "descricao_curta": "", "linguagem_principal": "",
        "frameworks": "", "infra": "", "convencao_1": "", "convencao_2": "",
        "en|pt": "pt", "objetivo_curto": "", "iso_timestamp": u.iso_now(),
    }
    tpl_claude = PLUGIN_ROOT / "templates" / "CLAUDE.md"
    if tpl_claude.is_file() and not (target / "CLAUDE.md").is_file():
        u.write_text(target / "CLAUDE.md", _subst(u.read_text(tpl_claude), mapping))
    tpl_docs = PLUGIN_ROOT / "templates" / "docs"
    if tpl_docs.is_dir():
        for f in tpl_docs.glob("*.md"):
            dst = target / "docs" / f.name
            if not dst.is_file():
                u.write_text(dst, _subst(u.read_text(f), mapping))
    # spec template
    tpl_spec = PLUGIN_ROOT / "templates" / "specs" / "_template.md"
    if tpl_spec.is_file():
        u.write_text(target / "specs" / "_template.md", u.read_text(tpl_spec))

    # --- toml ---
    _write_toml(target, budget_usd)

    # --- wiring dos hooks em .claude/settings.json ---
    _write_hooks_settings(target)

    # --- agentes ---
    all_created = []
    for ag in agents:
        if (target / "memory" / ag).is_dir():
            continue
        all_created += _scaffold_memory(target, ag, project)
        reg = _register_agent(target, ag)
        if reg:
            all_created.append(reg)

    # --- workflow state machine (v1.3): cria .mad/workflow_state.json ---
    _init_workflow_state(target, project, agents)

    u.emit_span("project.init",
                {"project.name": project, "project.type": project_type,
                 "agents": agents}, root=target)

    print(u.c(f"\n✓ Projeto '{project}' inicializado (modo decanting nativo).", "green", "bold"))
    print(f"  Tipo: {project_type}")
    print(f"  Agentes habilitados: {', '.join(agents)}")
    print(f"  {len(all_created)} arquivos criados em memory/ e .claude/agents/")
    print(u.c("\n  Próximo passo:", "bold"))
    print("    /mad-dashboard   → abre o dashboard local")
    print("    /mad-doctor      → verifica saúde")
    print("    Descreva sua primeira feature e o Arquiteto coordena.")
    return 0


def hooks_config() -> dict:
    """Config de hooks Claude Code apontando para .claude/hooks/ do projeto.

    Comandos usam ${CLAUDE_PROJECT_DIR}. Os .sh exigem bash (Git Bash no
    Windows); os .py exigem python3 acessível — ambos já são pré-requisitos do
    plugin. Ver docs/DECISOES.md.
    """
    h = "${CLAUDE_PROJECT_DIR}/.claude/hooks"
    sh = lambda f: {"type": "command", "command": f'bash "{h}/{f}"'}
    py = lambda f: {"type": "command", "command": f'python3 "{h}/{f}"'}
    return {
        "SessionStart": [
            {"hooks": [
                py("session-start-inject-state.py"),
                py("session-start-dashboard.py"),
            ]},
        ],
        "UserPromptSubmit": [
            {"hooks": [py("prompt-arquiteto-activity.py")]},
        ],
        "PreToolUse": [
            # workflow gate PRIMEIRO (bloqueia despacho fora de estado)
            {"matcher": "*", "hooks": [py("pre-workflow-gate.py")]},
            {"matcher": "Bash", "hooks": [
                sh("pre-guardrail-force-push.sh"),
                sh("pre-guardrail-rm-rf.sh"),
                sh("pre-guardrail-secret-commit.sh"),
            ]},
            {"matcher": "Edit|Write|MultiEdit", "hooks": [
                sh("pre-guardrail-identity-change.sh"),
            ]},
            {"matcher": "Agent|Task", "hooks": [
                py("pre-budget-circuit.py"),
            ]},
        ],
        "PostToolUse": [
            {"matcher": "*", "hooks": [py("post-otel-emit.py")]},
            {"matcher": "Agent|Task", "hooks": [
                py("post-trust-update.py"),
                py("post-decanting-update-state.py"),
            ]},
        ],
        "SessionEnd": [
            {"hooks": [py("session-end-decant-check.py")]},
        ],
    }


def _init_workflow_state(target: Path, project: str, agents: list[str]):
    """Cria .mad/workflow_state.json na fase DISCOVERY (bootstrap concluído
    pelo próprio init). Idempotente: não sobrescreve estado existente."""
    if (target / ".mad" / "workflow_state.json").is_file():
        return
    try:
        import workflow as wf
    except Exception:
        return
    (target / ".mad").mkdir(parents=True, exist_ok=True)
    data = wf.initial_state(project)
    now = u.iso_now()
    data["team_enabled"] = [{"role": a, "enabled_at": now} for a in agents]
    # bootstrap → discovery (init fez o bootstrap: estrutura, toml, identity)
    data["current_phase"] = "DISCOVERY"
    data["phase_entered_at"] = now
    data["phase_transitions"] = [{
        "from": "BOOTSTRAP", "to": "DISCOVERY", "at": now, "by": "init",
        "gates_checked": ["gate_bootstrap_done"],
        "evidence": {"created_by": "mad-init"},
    }]
    st = wf.WorkflowState(target, data)
    st.save()
    wf.log_event(target, "init", project=project, agents=agents)


def _write_hooks_settings(target: Path):
    """Mescla a config de hooks em .claude/settings.json (preserva o resto)."""
    settings_path = target / ".claude" / "settings.json"
    settings = u.read_json(settings_path, {}) or {}
    settings["hooks"] = hooks_config()
    u.write_json(settings_path, settings)


def _write_toml(target: Path, budget_usd: float):
    tpl = PLUGIN_ROOT / "templates" / "multiagents-decanting.toml"
    if tpl.is_file():
        content = u.read_text(tpl)
        content = content.replace("max_cost_per_day_usd = 50.0",
                                  f"max_cost_per_day_usd = {budget_usd}")
        u.write_text(target / u.CONFIG_FILENAME, content)
    else:  # fallback mínimo
        u.write_text(target / u.CONFIG_FILENAME,
                     f'[plugin]\nversion = "{PLUGIN_VERSION}"\n\n'
                     f'[budget]\nmax_cost_per_day_usd = {budget_usd}\n')


if __name__ == "__main__":
    sys.exit(run())
